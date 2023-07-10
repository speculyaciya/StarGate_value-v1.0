from execute import go_okx
import pandas as pd
import time

def check_okx_balance(symbol, min_balance):
    balance = go_okx.get_balance(symbol=symbol)
    if balance == None:
        return False
    if float(min_balance) <= float(balance):
        return True
    else:
        return False
    

def fill_chain_list(symbol):
    chains = []
    while True:
        try:
            chain_list = go_okx.get_withdraw_chains(symbol)
            break
        except:
            print('впн тупит')
            time.sleep(10)
            continue
    if chain_list == False:
        return chains
    for chain in chain_list:
        if chain[0] == 'Arbitrum One (Bridged)':
            name         = 'Arbitrum'
            network_name = chain[0]
            withdraw_fee = chain[1]
            withdraw_min = chain[2]
            chains.append([name,network_name, withdraw_fee, withdraw_min])
        if chain[0] == 'Avalanche C-Chain':
            name         = 'Avalanche'
            network_name = chain[0]
            withdraw_fee = chain[1]
            withdraw_min = chain[2]
            chains.append([name,network_name, withdraw_fee, withdraw_min])
        if chain[0] == 'Polygon':
            name         = 'Polygon'
            network_name = chain[0]
            withdraw_fee = chain[1]
            withdraw_min = chain[2]
            chains.append([name,network_name, withdraw_fee, withdraw_min])
        if chain[0] == 'Optimism':
            name         = 'Optimism'
            network_name = chain[0]
            withdraw_fee = chain[1]
            withdraw_min = chain[2]
            chains.append([name,network_name, withdraw_fee, withdraw_min])
    return chains

def get_chain_to_by_from(from_chain):
    if from_chain == 'Avalanche':
        return 'Polygon'
    if from_chain == 'Polygon':
        return 'Avalanche'

def get_max_data(activity):
    csv_path = 'max_setting.csv'
    data_csv = pd.read_csv(csv_path,keep_default_na=False)
    for index, row in data_csv.iterrows():
        if row['Activity'] == activity:
            return True, row['MAX_GAS'], row['MAX_VALUE']
    return False, '', ''