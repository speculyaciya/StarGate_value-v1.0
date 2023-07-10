import hmac, base64
import datetime
from loguru import logger as global_logger
import copy
import requests
import time
from decimal import Decimal
from termcolor import colored
import ccxt

class okx:
    def __init__(self, iv_api_key, iv_api_secret, iv_password, iv_proxy=''):
        global_logger.remove()
        self.logger = copy.deepcopy(global_logger)
        self.logger.add(
            fr'OKX.log',)
            # format="<white>{time: MM/DD/YYYY HH:mm:ss}</white> | <level>"
            # "{level: <8}</level> | <cyan>"
            # "</cyan> <white>{message}</white>")

        self.api_key    = iv_api_key
        self.api_secret = iv_api_secret
        self.password   = iv_password
        self.proxy      = { 'http': f'{iv_proxy}',
                            'https': f'{iv_proxy}',
                        }

        self.BASE_URL = 'https://www.okx.cab'

        self.name = 'okx'
        self.BASE_URL = 'https://www.okx.cab'

        self.exchange = getattr(ccxt, self.name)({
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'password': self.password,
            'enableRateLimit': True,
            'proxies': self.proxy,
            'options': {
                'defaultType': 'spot'
            }
        })

    def signature(self, timestamp: str, method: str, request_path: str, body: str = "" ) -> str:
        if not body:
            body = ""

        message = timestamp + method.upper() + request_path + body
        mac = hmac.new(
            bytes(self.api_secret, encoding="utf-8"),
            bytes(message, encoding="utf-8"),
            digestmod="sha256",
        )
        d = mac.digest()
        return base64.b64encode(d).decode("utf-8")
    
    def form_okx_data(self, request_path, method, body=''):
        dt_now = datetime.datetime.utcnow()
        ms = str(dt_now.microsecond).zfill(6)[:3]
        timestamp = f"{dt_now:%Y-%m-%dT%H:%M:%S}.{ms}Z"

        headers = {
            "Content-Type":"application/json",
            "OK-ACCESS-KEY":self.api_key,
            "OK-ACCESS-SIGN":self.signature(timestamp    = timestamp,
                                            method       = method,
                                            request_path = request_path,
                                            body         = body),
            "OK-ACCESS-TIMESTAMP":timestamp,
            "OK-ACCESS-PASSPHRASE":self.password,
            'x-simulated-trading':'0'
        }
        return headers
    
    def get_subaccount_list(self)->list:
        url_subaccount_list = '/api/v5/users/subaccount/list'
        method              = 'GET'

        try:
            headers = self.form_okx_data(request_path = url_subaccount_list,
                                         method       = method)
            list_sub = requests.get(f'{self.BASE_URL}{url_subaccount_list}', timeout=10, headers=headers, proxies=self.proxy) 
            if list_sub.status_code != 200:
                raise Exception(f'{list_sub.text}')
            list_sub = list_sub.json()
        except Exception as Ex:
           self.logger.error(f'Ошибка при получении субаккаунтов, {str(Ex)}')
           return False, ''
        return True, list_sub
    
    def subaccount_withdraw(self, symbol):
        sum_withdraw = float()
        result, list_sub = self.get_subaccount_list()
        if result == False:
           self.logger.error(f'Ошибка при выводе с субаккаунтов')
           return False, ''
        
        for sub_data in list_sub['data']:
            try:
                name_sub = sub_data['subAcct']
                headers = self.form_okx_data(request_path = f"/api/v5/asset/subaccount/balances?subAcct={name_sub}&ccy={symbol}",
                                            method       = 'GET')
                sub_balance = requests.get(f"https://www.okx.cab/api/v5/asset/subaccount/balances?subAcct={name_sub}&ccy={symbol}",timeout=10, headers=headers, proxies=self.proxy)
                sub_balance = sub_balance.json()
                sub_balance = sub_balance['data'][0]['bal']
                sum_withdraw = sum_withdraw + float(sub_balance)
                self.logger.info(f'{name_sub} | sub_balance : {sub_balance} {symbol}')
                if sub_balance == '0':
                    continue 
                body = {"ccy": f"{symbol}", "amt": str(sub_balance), "from": 6, "to": 6, "type": "2", "subAcct": name_sub}
                headers = self.form_okx_data(request_path = '/api/v5/asset/transfer',
                                             body         = str(body),
                                             method       = 'POST')
                transfer = requests.post("https://www.okx.cab/api/v5/asset/transfer",data=str(body), timeout=10, headers=headers, proxies=self.proxy)
                if transfer.status_code != 200:
                    raise Exception(f'{transfer.text}')
                transfer = transfer.json()
                time.sleep(1)
            except Exception as Ex:
                self.logger.error(f'{Ex}. sub_data : {sub_data}')
        return True, sum_withdraw
    
    def get_balance(self, symbol):
        try:
            headers = self.form_okx_data(request_path = f'/api/v5/asset/balances?ccy={symbol}',
                                         method       = 'GET')
            balance = requests.get(f'https://www.okx.cab/api/v5/asset/balances?ccy={symbol}', timeout=10, headers=headers, proxies=self.proxy)
            balance = balance.json()
            balance = balance["data"][0]["bal"]
            return balance
        except Exception as Ex:
            self.logger.error(f'Error get_balance : \n {Ex}')

    def get_withdraw_chains(self, symbol: str) -> list:
        chains = [] 
        try:
            while True:
                try:
                    coin_data = self.exchange.fetch_currencies()[symbol]
                    break
                except:
                    print('впн тупит в coin_data')
                    time.sleep(10)
                    continue

            if self.name == 'binance':
                for chain in coin_data['networks']:
                    if chain['withdrawEnable'] == True:
                        network_name = chain['network']
                        withdraw_fee = float(chain['withdrawFee'])
                        withdraw_min = float(chain['withdrawMin'])
                        chains.append([network_name, withdraw_fee, withdraw_min])
            else:
                for chain in coin_data['networks'].values():
                    if chain['withdraw'] == True:
                        network_name = chain['network']
                        if network_name == 'Avalanche X':
                            network_name = 'Avalanche X-Chain'
                        if network_name == 'Avalanche C':
                            network_name = 'Avalanche C-Chain'
                        withdraw_fee = float(chain['fee'])
                        withdraw_min = float(chain['limits']['withdraw']['min'])
                        chains.append([network_name, withdraw_fee, withdraw_min])
            return chains
        except KeyError as e:
            print(colored(f"Такого символа нет на бирже! Попробуйте ввести снова.", 'light_red'))
            return False
        except Exception as e:
            if 'Invalid API-key' in str(e) or 'Unmatched IP' in str(e):
                print(colored(f"Ошибка: Скорее всего, ваш текущий IP адрес не находится в белом списке на вывод средств или API-ключ истек!", 'light_red'))
            elif 'GET' in str(e):
                print(colored(f"Ошибка: Биржа временно недоступна, либо недоступна в вашей локации, либо ваш прокси нерабочий.", 'light_red'))
            else:
                print(colored(f"Неизвестная ошибка получения доступных сетей вывода: {e}", 'light_red'))
            return False
        
    def withdraw(self, address: str, amount_to_withdrawal: float, symbol_to_withdraw: str, network: str, withdraw_fee: float) -> None:
        try:
            self.exchange.withdraw(
                code=symbol_to_withdraw,
                amount=amount_to_withdrawal,
                address=address,
                tag=None, 
                params={
                    "toAddress": address,
                    "chain": f"{symbol_to_withdraw}-{network}",
                    "dest": 4,
                    "fee": withdraw_fee,
                    "pwd": '-',
                    "amt": amount_to_withdrawal,
                }
            )
            self.logger.success(f"{address} | Успешно выведено {amount_to_withdrawal} {symbol_to_withdraw}", 'light_green')
            return True
        except ccxt.InsufficientFunds as e:
            self.logger.error(colored(f'{address} | Ошибка: Недостаточно средств на балансе!', 'light_red'))
            return False
        except ccxt.ExchangeError as e:
            if 'not equal' in str(e) or 'not whitelisted' in str(e) or 'support-temp-addr' in str(e):
                self.logger.error(colored(f'{address} | Ошибка: Cкорее всего, ваш адрес не добавлен в белый список для вывода с биржи!', 'light_red'))
            elif 'not authorized' in str(e):
                self.logger.error(colored(f'{address} | Ошибка: Cкорее всего, ваш api-ключ истек или не имеет доступа к выводу средств!', 'light_red'))
            elif 'network is matched' in str(e):
                self.logger.error(colored(f'{address} | Ошибка: Адрес кошелька не подходит для данной сети!', 'light_red'))
            else:
                self.logger.error(colored(f'{address} | Ошибка вывода средств ({e})', 'light_red'))
            return False
        except Exception as e:
            self.logger.error(colored(f"{address} | Unknown error: {e}", 'light_red'))
            return False
