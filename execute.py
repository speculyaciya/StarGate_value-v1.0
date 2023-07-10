from loguru import logger as global_logger
import sys
import random
import pandas as pd
import settings_execute as s
import datetime
import time
import copy
from OKX.OKX_class import okx
import execute_util
from address_util import zcl_address
from stargate import stargate

from stargate_settings import CHAIN_LIST as STARGATE_CHAIN_LIST, text
import ccxt
from decimal import Decimal
import check_fee
import ZBC
from approve import approve
from termcolor import cprint


go_okx = okx(iv_api_key    = s.OKX['api_key'],
             iv_api_secret = s.OKX['api_secret'],
             iv_password   = s.OKX['password'],
             iv_proxy      = s.OKX_PROXY
            )

def form_max_by_chain(chain, usd):
    usd   = Decimal(float(usd))
    chain = chain.upper()
    if (chain == 'ARBITRUM' or
        chain == 'OPTIMISM' or 
        chain == 'ETHEREUM' ):
       symbol = 'ETH/USDT'
    elif chain == 'BSC':
        symbol = 'BNB/USDT'
    elif chain == 'POLYGON':
        symbol = 'MATIC/USDT'
    elif chain == 'AVALANCHE':
        symbol = 'AVAX/USDT'
    elif chain == 'FANTOM':
        symbol = 'FTM/USDT'
    else:
        raise Exception
    
    exchange = ccxt.binance()
    response = exchange.fetch_ohlcv(symbol,limit=1)
    return float(usd) / response[0][3]

def save_csv(data_csv, index):
    time.sleep(1)
    new_data_csv = pd.read_csv(csv_path,keep_default_na=False)
    new_data_csv.loc[index] = data_csv.loc[index]
    new_data_csv.to_csv(csv_path, index=False)

def execute(data_csv, index):
    SYMBOL = 'USDC'
    row = data_csv.loc[index]
    prelog = f'{row["NAME"]} | {row["WALLET"]}'
    logger.info(f'Выполняется {prelog}')
    
    # OKX_OUT--------------------------------------------------------------------------------------------------------------------------------------------------------
    if row['OKX_OUT'] != 'DONE':

        logger.info(f'{prelog} | Вывод из OKX')

        check_balance = execute_util.check_okx_balance(symbol=SYMBOL, min_balance=0.001)
        if check_balance == False:
            logger.error(f'{prelog} | Нет необходимой суммы для вывода из OKX')
            return False

        chain_list = execute_util.fill_chain_list(symbol=SYMBOL)
        if len(chain_list) == 0:
            logger.error(f'{prelog} | Не нашли сети для вывода из OKX')
            return False

        # Fill amount--------------------------------------
        try:
            amount_range      = str(row[f'VALUE_RANGE']).split(',')
            amount_range_from = float(str(amount_range[0]).replace(' ', ''))
            amount_range_to   = float(str(amount_range[1]).replace(' ', ''))
            amount            = round(random.uniform(amount_range_from, amount_range_to), 2)
            logger.info(f'{prelog} | Выбрали {amount} {SYMBOL} для вывода из OKX')
        except:
            logger.error(f'{prelog} | Ошибка при поиске суммы VALUE_RANGE')
            return False
        # Fill network--------------------------------------
        chain_from_okx = ''
        find_fee = False
        try:
            for chain_fee_data in s.CHECK_FEE_LIST:
                for chain in chain_list:
                    if chain[0] != chain_fee_data['network_from']:
                        continue
                    # chain_fee_data = ZBC.search_setting_data_by_element(element_search = 'network_from', value=chain[0], list=s.CHECK_FEE_LIST)
                    result_fee, list_fee = check_fee.check_fee(name=row["NAME"],
                                                            wallet=row["WALLET"],
                                                            amount=amount,
                                                            network_from=chain_fee_data['network_from'],
                                                            network_to_list=chain_fee_data['network_to_list'],
                                                            token=SYMBOL,
                                                            )
                    if result_fee == True:
                        for fee in list_fee:
                            logger.info(f'{prelog} | Из {fee["network_from"]} в {fee["network_to"]} стоимость {fee["usdc_fee"]}$')
                            if fee["usdc_fee"] <= s.MAX_FEE:
                                chain_from       = chain[0]
                                chain_from_okx   = chain[1]
                                withdraw_fee_okx = chain[2]
                                find_fee         = True
                                logger.info(f'{prelog} | Вывод OKX из {chain_from}')
                                logger.info(f'{prelog} | Вывод {chain_from} для вывода из OKX, Cимвол {SYMBOL}, Сумма {amount}, Комиссия {withdraw_fee_okx}')
                                raise StopIteration
        except StopIteration:
            pass
        if find_fee != True:
            logger.warning(f'{prelog} | Не нашли сеть, где нормальный FEE, выходим')
            return False
        # Init wallet--------------------------------------
        lo_address = zcl_address(name=row["NAME"], private_key=row["PRIVATE_KEY"])
        result, balance_of_token, human_balance = lo_address.get_balance_USDC(chain=chain_from)
        if result == False:
            logger.error(f'{prelog} | Ошибка при поиске баланса в {chain_from}')
            return False
        else:
            logger.info(f'{prelog} | Баланс в {chain_from} = {human_balance}')
            from_balance_of_token_before = balance_of_token
            from_human_balance_before    = human_balance
        # OKX withdraw--------------------------------------
        if chain_from_okx == '':
            logger.error(f'{prelog} | Ошибка при выводе OKX, не нашли сеть для вывода')
            return False
        while True:
            try:
                result = go_okx.withdraw(address=row["WALLET"],
                                amount_to_withdrawal=float(amount)-float(withdraw_fee_okx),
                                network=chain_from_okx,
                                symbol_to_withdraw=SYMBOL,
                                withdraw_fee=withdraw_fee_okx)
                break
            except:
                print('впн тупит')
                time.sleep(10)
                continue
        if result == True:
            logger.success(f'{prelog} | Вывели {chain_from} = {amount}')

            while True:
                time.sleep(60)
                result, balance_of_token, human_balance = lo_address.get_balance_USDC(chain=chain_from)
                if result == False:
                    logger.warning(f'{prelog} | Ошибка при поиске баланса в {chain_from}')
                    continue
                else:
                    logger.info(f'{prelog} | Баланс в {chain_from} = {human_balance}')
                    from_balance_of_token_after = balance_of_token
                    from_human_balance_after    = human_balance

                if from_balance_of_token_before < from_balance_of_token_after:
                    logger.success(f'{prelog} | Получили в {chain_from}, {SYMBOL} = {from_human_balance_after}') 
                    data_csv.loc[index,'OKX_OUT'] = 'DONE'
                    data_csv.loc[index,'VALUE_STARGATE'] = round(Decimal(float(from_human_balance_after)) - Decimal(float(from_human_balance_before)),8)
                    data_csv.loc[index,'FROM'] = chain_from
                    save_csv(data_csv, index)
                    return True
        else:
            logger.error(f'{prelog} | Ошибка при выводе {chain_from} = {amount}')
            return False

    # STARGATE--------------------------------------------------------------------------------------------------------------------------------------------------------
    if int(row['TIMES']) > 0:
        chain_from      = row['FROM']
        amount_stargate = float(row['VALUE_STARGATE'])

        if chain_from == '':
            logger.error(f'{prelog} | Ошибка при чтении FROM')
            return False
        
        # if chain_to == '':
        #     logger.error(f'{prelog} | Ошибка при чтении TO')
        #     return False
        
        if amount_stargate == '':
            logger.error(f'{prelog} | Ошибка при чтении VALUE_STARGATE')
            return False
        
        logger.info(f'{prelog} | Делаем APPROVE {amount_stargate} {SYMBOL} {chain_from}')
        
        # Получаем данные
        _element = 'chain'
        from_data = ZBC.search_setting_data_by_element(element_search = _element, value=chain_from, list=STARGATE_CHAIN_LIST)
        if len(from_data) == 0:
            logger.error(f'{prelog} | Ошибка при поиске информации {_element}')
            return False
        else:
            from_data   = from_data[0]
            router_from = from_data['router']

        result_max_data, max_gas, max_value = execute_util.get_max_data(activity=f'APPROVE_{chain_from.upper()}')
        if result_max_data == False:
            logger.error(f'{prelog} | Ошибка при получении max_data APPROVE_{chain_from.upper()}')
            return False 

        result = approve(
            name            = row['NAME'],
            proxy           = '',
            private_key     = row['PRIVATE_KEY'],
            from_chain      = chain_from,
            token           = SYMBOL,
            amount          = amount_stargate,
            approve_address = router_from,
            max_gas         = form_max_by_chain(chain=chain_from, usd=max_gas), 
        )
        if result == False:
            logger.error(f'{prelog} | Ошибка при APPROVE {amount_stargate} {SYMBOL} {chain_from}')
            return False
        else:
            logger.success(f'{prelog} | Успешный APPROVE {amount_stargate} {SYMBOL} {chain_from}')
        
        logger.info(f'{prelog} | STARGATE {amount_stargate} {SYMBOL} {chain_from}')
        while True:
            # CHECK FEE--------------------------------------
            find_fee = False    
            try:
                for chain_fee_data in s.CHECK_FEE_LIST:
                    if chain_fee_data['network_from'] != chain_from:
                        continue
                    # chain_fee_data = ZBC.search_setting_data_by_element(element_search = 'network_from', value=chain_from, list=s.CHECK_FEE_LIST)
                    # chain_fee_data = chain_fee_data[0]
                    result_fee, list_fee = check_fee.check_fee(name=row["NAME"],
                                                            wallet=row["WALLET"],
                                                            amount=amount_stargate,
                                                            network_from=chain_fee_data['network_from'],
                                                            network_to_list=chain_fee_data['network_to_list'],
                                                            token=SYMBOL,
                                                            )
                    if result_fee == True:
                        for fee in list_fee:
                            logger.info(f'{prelog} | Из {fee["network_from"]} в {fee["network_to"]} стоимость {fee["usdc_fee"]}$')
                            if fee["usdc_fee"] <= s.MAX_FEE:
                                chain_from       = fee["network_from"]
                                chain_to         = fee["network_to"]
                                find_fee         = True
                                raise StopIteration
                    else:
                        logger.warning(f'{prelog} | Ошибка при поиске FEE, выходим')
                        return False   
            except StopIteration:
                pass

            if find_fee != True:
                logger.warning(f'{prelog} | Не нашли сеть, где нормальный FEE, выходим')
                time.sleep(10)
                continue
            
            if chain_from == '':
                logger.error(f'{prelog} | Ошибка при чтении FROM')
                time.sleep(10)
                continue
            
            if chain_to == '':
                logger.error(f'{prelog} | Ошибка при чтении TO')
                time.sleep(10)
                continue
            
            # init address---------------------------------------
            lo_address = zcl_address(name=row["NAME"],
                                    private_key=row["PRIVATE_KEY"])

            result, balance_of_token, human_balance = lo_address.get_balance_USDC(chain=chain_to)
            if result == False:
                logger.error(f'{prelog} | Ошибка при поиске баланса в {chain_to}')
                time.sleep(60)
                continue
            else:
                logger.info(f'{prelog} | Баланс в {chain_to} = {human_balance}')
                to_human_balance_before    = human_balance
            # STARGATE---------------------------------------
            result_max_data, max_gas, max_value = execute_util.get_max_data(activity=f'STARGATE_{chain_from.upper()}_{chain_to.upper()}')
            if result_max_data == False:
                logger.error(f'{prelog} | Ошибка при получении max_data STARGATE_{chain_from.upper()}_{chain_to.upper()}')
                time.sleep(10)
                continue
            logger.info(f'{prelog} | Запускаем STARGATE {amount_stargate} {SYMBOL} {chain_from} to {chain_to}')
            result = stargate(
                name         = row['NAME'],
                proxy        = '',
                private_key  = row['PRIVATE_KEY'],
                amount       = amount_stargate,
                from_chain   = chain_from, 
                to_chain     = chain_to, 
                from_token   = SYMBOL,
                to_token     = SYMBOL, 
                max_gas      = form_max_by_chain(chain=chain_from, usd=max_gas),
                max_value    = form_max_by_chain(chain=chain_from, usd=max_value),
                amountOutMin = amount_stargate - s.MAX_FEE,
            )
            if result == False:
                logger.error(f'{prelog} | Ошибка при STARGATE')
                return False
            elif result == 'BIG GAS' or result == 'BIG VALUE':
                logger.warning(f'{prelog} | Высокий газ или value STARGATE, выходим')
                time.sleep(10)
                continue
            elif result == 'BIG FEE':
                logger.warning(f'{prelog} | FEE больше, чем установлен в MAX_FEE')
                time.sleep(10)
                continue
            else:
                result, balance_of_token, human_balance = lo_address.get_balance_USDC(chain=chain_to)
                if result == False:
                    logger.error(f'{prelog} | Ошибка при поиске баланса в {chain_to}')
                    return False
                else:
                    logger.info(f'{prelog} | Баланс в {chain_to} = {human_balance}')
                    to_human_balance_after    = human_balance
                data_csv.loc[index,'TIMES'] = int(row['TIMES']) - 1
                data_csv.loc[index,'FROM'] = chain_to
                data_csv.loc[index,'VALUE_STARGATE'] = round(Decimal(float(to_human_balance_after)) - Decimal(float(to_human_balance_before)),8)
                save_csv(data_csv, index)
                logger.success(f'{prelog} | DONE STARGATE {amount_stargate} {SYMBOL} {chain_from} to {chain_to}')
                return True

    if row['OKX_IN'] != 'DONE':
        chain_from = row['FROM']
        amount     = float(row['VALUE_STARGATE'])
        to_wallet  = row['OKX_WALLET']

        if chain_from == '':
            logger.error(f'{prelog} | Ошибка при чтении FROM')
            return False

        if to_wallet == '':
            logger.error(f'{prelog} | Ошибка при чтении OKX_WALLET')
            return False
        
        if amount == '':
            logger.error(f'{prelog} | Ошибка при чтении VALUE_STARGATE')
            return False

        logger.info(f'{prelog} | OKX IN {amount} {SYMBOL} {chain_from}')

        lo_address = zcl_address(name=row["NAME"],
                                 private_key=row["PRIVATE_KEY"])
        transfer = lo_address.transfer(chain=chain_from,
                                       amount=amount,
                                       to_address=to_wallet)
        if transfer == False:
            logger.error(f'{prelog} | Ошибка отправки в OKX')
            return False
        
        time.sleep(60)
        while True:
            result, sum_withdraw = go_okx.subaccount_withdraw(symbol='USDC')
            if result == True and sum_withdraw != 0:
                break
            if result == False:
                logger.warning('Ошибка при выводе с субаккаунтов')
            time.sleep(30)

        data_csv.loc[index,'OKX_IN'] = 'DONE'
        data_csv.loc[index,'DO'] = 'DONE'
        save_csv(data_csv, index)
        logger.success(f'{prelog} | DONE OKX_IN')
        return True


if __name__ == '__main__':

    cprint(text, 'yellow')
    cprint('\n                         -------     subscribe to us : https://t.me/spekulyantcrypto     -------', 'yellow')

    cprint('                         -------                         coders                          -------')
    cprint('                         --------------  Gefest_forge:  https://t.me/gefest_forge --------------', 'green')
    cprint('                         --------------  Crypto-Selkie: https://t.me/tawer_crypt  --------------', 'green')
    cprint('                         -------    donate:  0x9d9D67FAF623a2D78A1eaa07579b7128fCD79dd9  -------', 'white')


    global_logger.remove()
    logger = copy.deepcopy(global_logger)
    logger.add(sys.stderr,
           format="<white>{time: MM/DD/YYYY HH:mm:ss}</white> | <level>"
           "{level: <8}</level> | <cyan>"
           "</cyan> <white>{message}</white>")
    logger.add('l0_value.log',
           format="<white>{time: MM/DD/YYYY HH:mm:ss}</white> | <level>"
           "{level: <8}</level> | <cyan>"
           "</cyan> <white>{message}</white>")

    csv_path = r'data.csv'
   
    while True:
        do_index_list = []
        data_csv = pd.read_csv(csv_path,keep_default_na=False)
        for index, row in data_csv.iterrows():
            if row['DO'] == 'X':
                do_index_list.append(index)
        if len(do_index_list) == 0:
            break
        execute_index = do_index_list[0]
        data_csv = execute(data_csv=data_csv, index=execute_index)
        wait_time = random.sample(s.WAIT_MIN,1)[0]
        nextTime = datetime.datetime.now() + datetime.timedelta(seconds=wait_time)
        logger.info(f'Следующий запуск {nextTime}')
        while True:
            if datetime.datetime.now() > nextTime:
                break
            time.sleep(5)