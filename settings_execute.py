WAIT_MIN = range(15, 20)

CHECK_FEE_LIST = [
    {
    'network_from':'Optimism', 
    'network_to_list':['Avalanche', 'Arbitrum', 'Polygon']
     },
    {
    'network_from':'Arbitrum', 
    'network_to_list':['Avalanche','Polygon', 'Optimism']
     },
    {
    'network_from':'Avalanche', 
    'network_to_list':['Arbitrum', 'Optimism', 'Polygon'] # 'Arbitrum', 'Polygon'
     },
    {
    'network_from':'Polygon',
    'network_to_list':['Arbitrum', 'Optimism','Avalanche'] # 'Arbitrum', 'Avalanche'
    },
]

MAX_FEE = 1 # максимальная комиссия за бридж, которая вычитается из суммы, которую вы бриджите (ex. при бридже 5000 USDC мин. комиссия - $0.16)

OKX = {
    'api_key': '', 
    'api_secret': '', 
    'password': '', 
}

OKX_PROXY = ''
