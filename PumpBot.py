from binance.client import Client
from binance.enums import *
from binance.exceptions import *
import sys
import math
import json
import requests
import webbrowser
import time
import urllib
import os
import ssl
import time

# UTILS
def float_to_string(number, precision=10):
    return '{0:.{prec}f}'.format(
        number, prec=precision,
    ).rstrip('0').rstrip('.') or '0'

def log(information):
    currentTime = time.strftime("%H:%M:%S", time.localtime())
    logfile.writelines(str(currentTime) + " --- " + str(information) + "\n")

def marketSell(amountSell):
    order = client.order_market_sell(
        symbol=tradingPair,
        quantity=amountSell)
    log("Sold at market price.")
    print("Sold at market price")

# make log file
logfile = open("log.txt", "w+")

# read json file
try:
    f = open('keys.json', )
except FileNotFoundError:
    log("Keys.json not found.")
    sys.exit("Error. Keys.json not found. \nRemember to rename your keys.json.example to keys.json.")
    
log("Loading API keys.")
data = json.load(f)
apiKey = data['apiKey']
apiSecret = data['apiSecret']
if (apiKey == "") or (apiSecret == ""):
    log("API Keys Missing.")
    sys.exit("One or Both of you API Keys are missing.\n"
    "Please open the keys.json to include them.")

log("API keys successfully loaded.")
log("Loading config.json settings.")
f = open('config.json', )
data = json.load(f)
# loading config settings
quotedCoin = data['quotedCoin'].upper()
buyLimit = data['buyLimit']
percentOfWallet = float(data['percentOfWallet']) / 100
manualQuoted = float(data['manualQuoted'])
profitMargin = float(data['profitMargin']) / 100
stopLoss = float(data['stopLoss'])
currentVersion = float(data['currentVersion'])
endpoint = data['endpoint']
log("config.json settings successfully loaded.")

# check we have the latest version
ssl._create_default_https_context = ssl._create_unverified_context
url = 'https://raw.githubusercontent.com/fj317/PumpBot/master/config.json'
urllib.request.urlretrieve(url, 'version.json')
try:
    f = open('version.json', )
except FileNotFoundError:
    log("version.json not found. Quitting program.")
    print("Fatal error checking versions. Please try again\n")
    quit()
data = json.load(f)
f.close()
latestVersion = data['currentVersion']
os.remove("version.json")
if latestVersion > currentVersion:
    log("Current version {}. New version {}".format(currentVersion, latestVersion))
    print("\nNew version of the script found. Please download the new version...\n")
    time.sleep(3)

endpoints = {
    'default': 'https://api.binance.{}/api',
    'api1': 'https://api1.binance.{}/api',
    'api2': 'https://api2.binance.{}/api',
    'api3': 'https://api3.binance.{}/api'
}

try:
    Client.API_URL = endpoints[endpoint]
except Exception as d:
    print("Endpoint error. Using default endpoint instead")
    log("Endpoint error. Using default endpoint instead.")

# create binance Client
client = Client(apiKey, apiSecret)

# get all symbols with coinPair as quote
tickers = client.get_all_tickers()
symbols = []
for ticker in tickers:
    if quotedCoin in ticker["symbol"]: symbols.append(ticker["symbol"])

# cache average prices
log("Caching all quoted coin pairs.")
print("Caching all {} pairs average prices...\nThis can take a while. Please, be patient...\n".format(quotedCoin))
tickers = client.get_ticker()
averagePrices = []
for ticker in tickers:
    if quotedCoin in ticker['symbol']:
        averagePrices.append(dict(symbol=ticker['symbol'], wAvgPrice=ticker["weightedAvgPrice"]))

# getting btc conversion
response = requests.get('https://api.coindesk.com/v1/bpi/currentprice.json')
data = response.json()
in_USD = float((data['bpi']['USD']['rate_float']))
print("Sucessfully cached" + quotedCoin + "pairs!")
log("Sucessfully cached quoted coin pairs.")

# find amount of bitcoin to use
log("Getting quoted balance amount.")
try:
    QuotedBalance = float(client.get_asset_balance(asset=quotedCoin)['free'])
except (BinanceRequestException, BinanceAPIException):
    log("Error with getting balance.")
    sys.exit("Error with getting balance.")

# decide if use percentage or manual amount
if manualQuoted <= 0:
    AmountToSell = QuotedBalance * percentOfWallet
else:
    AmountToSell = manualQuoted

# nice user message
print(''' 
 ___                                ___           _   
(  _`\                             (  _`\        ( )_ 
| |_) ) _   _   ___ ___   _ _      | (_) )   _   | ,_)
| ,__/'( ) ( )/' _ ` _ `\( '_`\    |  _ <' /'_`\ | |  
| |    | (_) || ( ) ( ) || (_) )   | (_) )( (_) )| |_ 
(_)    `\___/'(_) (_) (_)| ,__/'   (____/'`\___/'`\__)
                         | |                          
                         (_)                          ''')
# wait until coin input
print("\nInvesting amount for {}: {}".format(quotedCoin, float_to_string(AmountToSell)))
print("Investing amount in USD: {}".format(float_to_string((in_USD * AmountToSell), 2)))
log("Waiting for trading pair input.")
tradingPair = input("\nCoin pair: ").upper() + quotedCoin

# get price for coin
averagePrice = 0
for ticker in averagePrices:
    if ticker["symbol"] == tradingPair:
        averagePrice = ticker["wAvgPrice"]
# if average price fails then get the current price of the trading pair (backup in case average price fails)
if averagePrice == 0: averagePrice = float(client.get_avg_price(symbol=tradingPair)['price'])

log("Calculating amount of coin to buy.")
# calculate amount of coin to buy
amountOfCoin = AmountToSell / float(averagePrice)

log("Rounding amount of coin.")
# rounding the coin amount to the specified lot size
info = client.get_symbol_info(tradingPair)
minQty = float(info['filters'][2]['stepSize'])
amountOfCoin = float_to_string(amountOfCoin, int(- math.log10(minQty)))

# rounding price to correct dp
log("Rounding price for coin.")
minPrice = minQty = float(info['filters'][0]['tickSize'])
averagePrice = float(averagePrice) * buyLimit
averagePrice = float_to_string(averagePrice, int(- math.log10(minPrice)))

log("Attempt to create buy order.")
try:
    # buy order
    order = client.order_limit_buy(
        symbol=tradingPair,
        quantity=amountOfCoin,
        price=averagePrice)
except BinanceAPIException as e:
    print("A BinanceAPI error has occurred. Code = " + str(e.code))
    print(
        e.message + ". Please use https://github.com/binance/binance-spot-api-docs/blob/master/errors.md to find "
                    "greater details on error codes before raising an issue.")
    log("Binance API error has occured on buy order.")
    quit()
except Exception as d:
    print(d)
    print("An unknown error has occurred.")
    log("Unknown error has occured on buy order.")
    quit()

# waits until the buy order has been confirmed 
while order['status'] != "FILLED":
    print("Waiting for coin to buy...")

print('Buy order has been made!')
log("Buy order successfully made.")

# once finished waiting for buy order we can process the sell order
print('Processing sell order.')
log("Processing sell order.")

# once bought we can get info of order
log("Getting buy order information.")
coinOrderInfo = order["fills"][0]
coinPriceBought = float(coinOrderInfo['price'])
coinOrderQty = float(coinOrderInfo['qty'])

log("Calculate price to sell at and round.")
# find price to sell coins at
priceToSell = coinPriceBought * profitMargin
# rounding sell price to correct dp
roundedPriceToSell = float_to_string(priceToSell, int(- math.log10(minPrice)))

# get stop price
stopPrice = float_to_string(stopLoss * coinPriceBought, int(- math.log10(minPrice)))
log("Attempting to create sell order.")
try:
    # oco order (with stop loss)
    order = client.create_oco_order(
        symbol=tradingPair,
        quantity=coinOrderQty,
        side=SIDE_SELL,
        price=roundedPriceToSell,
        stopPrice=stopPrice,
        stopLimitPrice=stopPrice,
        stopLimitTimeInForce=TIME_IN_FORCE_GTC
    )
except BinanceAPIException as e:
    print("A BinanceAPI error has occurred. Code = " + str(e.code))
    print(
        e.message + " Please use https://github.com/binance/binance-spot-api-docs/blob/master/errors.md to find "
                    "greater details "
                    "on error codes before raising an issue.")
    log(e)
    log("Binance API error has occured on sell order.")
    print("Attempting to market sell.")
    marketSell(coinOrderQty)
    quit()
except Exception as d:
    print("An unknown error has occurred.")
    log(d)
    log("Unknown error has occured on sell order.")
    print("Attempting to market sell.")
    marketSell(coinOrderQty)
    quit()

print('Sell order has been made!')
log("Sell order successfully made.")
# open binance page to trading pair
webbrowser.open('https://www.binance.com/en/trade/' + tradingPair)

print("Waiting for sell order to be completed.")
while order['listOrderStatus'] != "ALL_DONE":
    pass
print("Sell order has been filled!")
log("Sell order has been filled.")

newQuotedBalance = float(client.get_asset_balance(asset=quotedCoin)['free'])
profit = newQuotedBalance - QuotedBalance
print("Profit made: " + str(profit))
log("Profit made: " + str(profit))

# wait for Enter to close
input("\nPress Enter to Exit...")

# close Log file and exit
logfile.close()
sys.exit()
