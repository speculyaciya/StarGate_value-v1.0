from web3 import Web3
import stargate_settings as s
from loguru import logger as global_logger
import copy
import time
import ZBC

class zcl_address:
    def __init__(self, name, private_key, proxy=''):
        global_logger.remove()
        self.logger = copy.deepcopy(global_logger)
        self.logger.add(
            fr'zcl_address.log',)
        self.name      = 'ZCL_ADDRESS'
        self.private_key   = private_key
        self.proxy         = proxy
        # Получаем данные
        _element = 'chain'
        chain_data = ZBC.search_setting_data_by_element(element_search = _element, value='Avalanche', list=s.CHAIN_LIST)
        if len(chain_data) == 0:
            self.logger.error(f'{name} | {self.name} | Ошибка при поиске информации {_element}')
            return False
        else:
            chain_data = chain_data[0]

        self.RPC_Avalanche = chain_data['rpc']
            
        # Получаем данные по токену
        _element = 'token'
        token_data = ZBC.search_setting_data_by_element(element_search = _element, value='USDC', list=chain_data['token_list'])
        if len(token_data) == 0:
            self.logger.error(f'{name} | {self.name} | Ошибка при поиске информации {_element}')
            return False
        else:
            token_data = token_data[0]

        self.Avalanche_USDC     = token_data['address']
        self.Avalanche_USDC_ABI = token_data['abi']

        _element = 'chain'
        chain_data = ZBC.search_setting_data_by_element(element_search=_element, value='Polygon', list=s.CHAIN_LIST)
        if len(chain_data) == 0:
            self.logger.error(f'{name} | {self.name} | Ошибка при поиске информации to_chain')
            return False
        else:
            chain_data = chain_data[0]

        self.RPC_Polygon = chain_data['rpc']
            
        # Получаем данные по токену
        _element = 'token'
        token_data = ZBC.search_setting_data_by_element(element_search = _element, value='USDC', list=chain_data['token_list'])
        if len(token_data) == 0:
            self.logger.error(f'{name} | {self.name} | Ошибка при поиске информации {_element}')
            return False
        else:
            token_data = token_data[0]

        self.Polygon_USDC     = token_data['address']
        self.Polygon_USDC_ABI = token_data['abi']

        _element = 'chain'
        chain_data = ZBC.search_setting_data_by_element(element_search=_element, value='Arbitrum', list=s.CHAIN_LIST)
        if len(chain_data) == 0:
            self.logger.error(f'{name} | {self.name} | Ошибка при поиске информации to_chain')
            return False
        else:
            chain_data = chain_data[0]

        self.RPC_Arbitrum = chain_data['rpc']
            
        # Получаем данные по токену
        _element = 'token'
        token_data = ZBC.search_setting_data_by_element(element_search = _element, value='USDC', list=chain_data['token_list'])
        if len(token_data) == 0:
            self.logger.error(f'{name} | {self.name} | Ошибка при поиске информации {_element}')
            return False
        else:
            token_data = token_data[0]

        self.Arbitrum_USDC     = token_data['address']
        self.Arbitrum_USDC_ABI = token_data['abi']

        _element = 'chain'
        chain_data = ZBC.search_setting_data_by_element(element_search=_element, value='Optimism', list=s.CHAIN_LIST)
        if len(chain_data) == 0:
            self.logger.error(f'{name} | {self.name} | Ошибка при поиске информации to_chain')
            return False
        else:
            chain_data = chain_data[0]

        self.RPC_Optimism = chain_data['rpc']
            
        # Получаем данные по токену
        _element = 'token'
        token_data = ZBC.search_setting_data_by_element(element_search = _element, value='USDC', list=chain_data['token_list'])
        if len(token_data) == 0:
            self.logger.error(f'{name} | {self.name} | Ошибка при поиске информации {_element}')
            return False
        else:
            token_data = token_data[0]

        self.Optimism_USDC     = token_data['address']
        self.Optimism_USDC_ABI = token_data['abi']

    def get_balance_USDC(self,chain):
        log_name = f'get_balance_USDC {chain}'
        if chain == 'Avalanche':
            RPC       = self.RPC_Avalanche
            TOKEN     = self.Avalanche_USDC
            TOKEN_ABI = self.Avalanche_USDC_ABI
        elif chain == 'Polygon':
            RPC       = self.RPC_Polygon
            TOKEN     = self.Polygon_USDC
            TOKEN_ABI = self.Polygon_USDC_ABI
        elif chain == 'Arbitrum':
            RPC       = self.RPC_Arbitrum
            TOKEN     = self.Arbitrum_USDC
            TOKEN_ABI = self.Arbitrum_USDC_ABI
        elif chain == 'Optimism':
            RPC       = self.RPC_Optimism
            TOKEN     = self.Optimism_USDC
            TOKEN_ABI = self.Optimism_USDC_ABI
        else:
            self.logger.error(f'{self.name} | {log_name} | Ошибка при выборе сети')
            return False,'',''

        try:
            w3_from = Web3(Web3.HTTPProvider(RPC, request_kwargs={"proxies":{'https' : self.proxy, 'http' : self.proxy }, 'timeout': 180}))
            if w3_from.is_connected() == True:
                account = w3_from.eth.account.from_key(self.private_key)
                address = account.address
            else:
                self.logger.error(f'{self.name} | {log_name} | Ошибка при connect RPC')
                return False,'',''
        
            contractTOKEN = w3_from.eth.contract(address=w3_from.to_checksum_address(TOKEN), abi=TOKEN_ABI)
            
            token_decimals   = contractTOKEN.functions.decimals().call()
            balance_of_token = contractTOKEN.functions.balanceOf(address).call()
            human_balance    = balance_of_token/ 10 ** token_decimals

            return True, balance_of_token, human_balance
        except Exception as Ex:
            self.logger.error(f'{self.name} | {address} | {log_name} | Ошибка при балансе {Ex}')
            return False,'',''
        
    def transfer(self, chain, amount, to_address):
        log_name = f'TRANSFER {chain}'
        if chain == 'Avalanche':
            RPC       = self.RPC_Avalanche
            TOKEN     = self.Avalanche_USDC
            TOKEN_ABI = self.Avalanche_USDC_ABI
        elif chain == 'Polygon':
            RPC       = self.RPC_Polygon
            TOKEN     = self.Polygon_USDC
            TOKEN_ABI = self.Polygon_USDC_ABI
        elif chain == 'Arbitrum':
            RPC       = self.RPC_Arbitrum
            TOKEN     = self.Arbitrum_USDC
            TOKEN_ABI = self.Arbitrum_USDC_ABI
        elif chain == 'Optimism':
            RPC       = self.RPC_Optimism
            TOKEN     = self.Optimism_USDC
            TOKEN_ABI = self.Optimism_USDC_ABI
        else:
            self.logger.error(f'{self.name} | {address} | {log_name} | Ошибка при выборе сети')
            return False
        
        try:
            w3_from = Web3(Web3.HTTPProvider(RPC, request_kwargs={"proxies":{'https' : self.proxy, 'http' : self.proxy }, 'timeout': 180}))
            if w3_from.is_connected() == True:
                account = w3_from.eth.account.from_key(self.private_key)
                address = account.address
            else:
                self.logger.error(f'{self.name} | {address} | {log_name} | Ошибка при connect RPC')
                return False
        
            contractTOKEN = w3_from.eth.contract(address=w3_from.to_checksum_address(TOKEN), abi=TOKEN_ABI)
            
            token_decimals   = contractTOKEN.functions.decimals().call()
            balance_of_token = contractTOKEN.functions.balanceOf(address).call()
            amountIn         = int(amount * 10 ** token_decimals)
            if amountIn > balance_of_token:
                self.logger.error(f'{self.name} | {address} | {log_name} | Баланс меньше чем нужно')
                return False
            
            transaction = contractTOKEN.functions.transfer(
                    Web3.to_checksum_address(to_address),
                    amountIn
                    ).build_transaction(
                        {
                        'from': address,
                        'value': 0,
                        'gasPrice': int(w3_from.eth.gas_price * 1.05),
                        'nonce': w3_from.eth.get_transaction_count(address)})
            signed_transaction = account.sign_transaction(transaction)
            transaction_hash = w3_from.eth.send_raw_transaction(signed_transaction.rawTransaction)
            self.logger.success(f'{self.name} | {address} | {log_name} | Подписали TRANSFER {transaction_hash.hex()}')
            status = ZBC.transaction_verification(self.name, transaction_hash, w3_from, log_name=log_name, text=f'TRANSFER', logger=self.logger)
            if status == False:
                self.logger.error(f'{self.name} | {address} | {log_name} | Ошибка при TRANSFER')
                return False
            return True
        except Exception as Ex:
            self.logger.error(f'{self.name} | {address} | {log_name} | Ошибка при балансе {Ex}')
            return False