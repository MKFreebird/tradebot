# Simple bitcoin tradebot for Bitonic's trading platform Bl3p


import bl3papi
import json
import time


# Parse the raw JSON data 
# @param    j   raw JSON
def formatResponse(j):
    dump = json.dumps(j, sort_keys=True, indent=4, separators=(',', ': '))
    jsonload = json.loads(dump)
    return jsonload


# Format euro to exchange format
# @param    eur    float value euro's 
def formatEUR(eur):
    return eur * 100000


# Fetch current market prices
# @param    value   'last' 'bid' 'ask' 'high' 'low'
# @return   float value of specified ticker
def ticker(value):
    raw = b.getTicker()
    j = formatResponse(raw)
    last, bid, ask, high, low = j['last'], j['bid'], j['ask'], j['high'], j['low']
    # print 'Last  {} \nBid   {} \nAsk   {} \nHigh  {} \nLow   {}'.format(last, bid, ask, high, low)
    if value == 'last':
        return last
    elif value == 'bid':
        return bid
    elif value == 'ask':
        return ask
    elif value == 'high':
        return high
    elif value == 'low':
        return low
    else:
        return last, bid, ask, high, low


# Fetch raw JSON data with account balances
# @return raw JSON response from the exchange
def getBalancesRaw():
    rawData = formatResponse(b.getBalances())
    return rawData


# Display account balances
def printBalances():
    j = getBalancesRaw()
    btc = j['data']['wallets']['BTC']['balance']['display']
    eur = j['data']['wallets']['EUR']['balance']['display']
    btcAvailable = j['data']['wallets']['BTC']['available']['display']
    eurAvailable = j['data']['wallets']['EUR']['available']['display']
    print '[$] Account balances EUR/BTC'
    print '\n\tTotal\n\t\t{}\n\t\t{}\n\n\tAvailable\n\t\t{}\n\t\t{}\n\n'.format(btc, eur, btcAvailable, eurAvailable)


# Fetch the int value of the available account balance
# @param    currency    euro or btc
# @return   available account balance in euro or btc
def getAvailableBalance(currency):
    j = getBalancesRaw()
    if currency == 'euro':
        availableEurInt = j['data']['wallets']['EUR']['available']['value_int']
        return availableEurInt
    else:
        availableBtcInt = j['data']['wallets']['BTC']['available']['value_int']
        return availableBtcInt


# Convert available euro balance to satoshi at a given limitprice
# @param    limitPrice
# @return   int value of current euro balance in satoshi
def eurToSatoshi(limitPrice):
    available = int(getAvailableBalance('euro')) / 100000
    satoshi = int(float(available) / float(limitPrice) * 100000000)
    return satoshi


# Fetch orderstatus for a specific order
# @param    id  int value of the orderid
# @return   string value with orderstatus
def getOrderStatus(id):
    raw = b.orderInfo('BTCEUR', id)
    j = formatResponse(raw)
    return str(j['data']['status'])


# Place a marketorder
# @param    order_type  'bid' or 'ask'
# @param    order_amount Amount to spend
# @param    order_price Limit price of order
# @return   boolean value True if order placed
def addOrder(order_type, order_amount, order_price):
    orderPlaced = False
    btc = float(order_amount) / float(100000000)
    euroWorth = btc * order_price
    print '\n[+] Placing order for {:.8} BTC at {:.2f} EUR'.format(btc, float(order_price))
    print '[+] Order value: {:.8f} EUR\n'.format(euroWorth)
    raw = b.addOrder('BTCEUR', order_type, order_amount, int(formatEUR(order_price)))
    j = formatResponse(raw)
    print '\t{}'.format(j['result'])
    if str(j['result']) == 'success':
        orderId = j['data']['order_id']
        saveOrder(int(orderId))
        print '\tOrder id: {}\n'.format(currentOrder)
        orderPlaced = True
    elif str(j['result']) == 'error':
        print '\t{}'.format(j['data']['code'])
        print '\t{}'.format(j['data']['message'])
    return orderPlaced


# Save a specific order
# @param    id  int value orderid
def saveOrder(id):
    global currentOrder 
    currentOrder = id


# Calculate the target sell price
# @param    buyPrice    The price at buytime
# @param    profitPct   Float value of desired profit in %
# @return   int value of target sell price
def calculateTarget(buyPrice, profitPct):
    profitEUR = (buyPrice / 100) * profitPct
    target = int(buyPrice + profitEUR)
    return target


# Calculate the maximum buy price based on 24 hour high
# @param    boundary    Float value of percentage under 24h high
# @return   int value of maximum buy price
def calculateMaxPrice(boundary):
    high = int(ticker('high'))
    # print high
    maxPrice = int(high - ((high / 100) * boundary))
    return maxPrice


# Track the status of a specific order
# @param    orderId int value of the order id
# @param    delay   int value of time interval to check status in seconds
def trackOrderStatus(orderId, delay):
    print '[?] Tracking state for order {}\n'.format(orderId)
    pendingOrder = True
    last = ''
    while pendingOrder:
        status = getOrderStatus(currentOrder)
        if status != last:
            print '\tState:\t{}'.format(status)
            last = status
        if status != 'closed':
            time.sleep(delay)
        else:
            pendingOrder = False


# Wait for a good buy price
# @param    boundary    Float value of percentage under 24h high
# @param    delay   int value of time interval to check status in seconds
# @return   int value of current ask price
def waitForBuy(boundary, delay):
    print '[+] Waiting to buy...\n'
    waiting = True
    while waiting:
        ask = ticker('ask')
        maxPrice = calculateMaxPrice(boundary)
        print '\tLowest ask: {} Maximum buy price: {}'.format(ask, maxPrice)
        if maxPrice >= ask:
            waiting = False
        else:
            time.sleep(delay)
    return ask

        

Bl3pApi = bl3papi.Bl3pApi

public_key = ""
secret_key = ""

b = Bl3pApi('https://api.bl3p.eu/1/', public_key, secret_key)

currentOrder = 0
profitPercentage = 2.5
highBoundary = 3
delay = 30

printBalances()

mainloop = True
while mainloop:
    buyPrice = waitForBuy(highBoundary, delay)
    spend = eurToSatoshi(buyPrice)
    if addOrder('bid', spend, buyPrice):
        trackOrderStatus(currentOrder, delay)
    else:
        print '\n[-] Shutting down'
        break
    targetPrice = calculateTarget(buyPrice, profitPercentage)
    # print targetPrice
    availableBTC = getAvailableBalance('btc')
    if addOrder('ask', availableBTC, targetPrice):
        trackOrderStatus(currentOrder, delay)

