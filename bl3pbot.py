# Simple bitcoin tradebot for Bitonic's trading platform Bl3p


import bl3papi
import json
import time


def formatResponse(j):
    dump = json.dumps(j, sort_keys=True, indent=4, separators=(',', ': '))
    jsonload = json.loads(dump)
    return jsonload


def formatEUR(eur):
    return eur * 100000


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


def getBalancesRaw():
    rawData = formatResponse(b.getBalances())
    return rawData


def printBalances():
    j = getBalancesRaw()
    btc = j['data']['wallets']['BTC']['balance']['display']
    eur = j['data']['wallets']['EUR']['balance']['display']
    btcAvailable = j['data']['wallets']['BTC']['available']['display']
    eurAvailable = j['data']['wallets']['EUR']['available']['display']
    print 'Total\n\t{}\n\t{}\n\nAvailable\n\t{}\n\t{}\n\n'.format(btc, eur, btcAvailable, eurAvailable)


def getAvailableBalance(currency):
    j = getBalancesRaw()
    if currency == 'euro':
        availableEurInt = j['data']['wallets']['EUR']['available']['value_int']
        return availableEurInt
    else:
        availableBtcInt = j['data']['wallets']['BTC']['available']['value_int']
        return availableBtcInt


def eurToSatoshi(limitPrice):
    available = int(getAvailableBalance('euro')) / 100000
    print 'available ', available
    satoshi = int(float(available) / float(limitPrice) * 100000000)
    return satoshi


def getOrderStatus(id):
    raw = b.orderInfo('BTCEUR', id)
    j = formatResponse(raw)
    return str(j['data']['status'])


def addOrder(order_type, order_amount, order_price):
    orderPlaced = False
    btc = float(order_amount) / float(100000000)
    print '[+] Placing order for {:.8} BTC at {:.2f} EUR\n'.format(btc, float(order_price))
    raw = b.addOrder('BTCEUR', order_type, order_amount, formatEUR(order_price))
    j = formatResponse(raw)
    print '\t{}'.format(j['result'])
    if str(j['result']) == 'success':
        orderId = j['data']['order_id']
        saveOrder(int(orderId))
        print '\tOrder id: {}\n'.format(currentOrder)
        orderPlaced = True
    return orderPlaced


def saveOrder(id):
    global currentOrder 
    currentOrder = id


def calculateTarget(buyPrice, profitPct):
    profitEUR = (buyPrice / 100) * profitPct
    return buyPrice + profitEUR


def calculateMaxPrice(boundary):
    high = int(ticker('high'))
    # print high
    maxPrice = int(high - ((high / 100) * boundary))
    return maxPrice


def trackOrderStatus(orderId, delay):
    print '[+] Tracking state for order {}\n'.format(orderId)
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


def waitForBuy(boundary, delay):
    print '[+] Waiting to buy...'
    waiting = True
    while waiting:
        ask = ticker('ask')
        maxPrice = calculateMaxPrice(boundary)
        print '\tLowest ask: {} Maximum to spend: {}'.format(ask, maxPrice)
        if maxPrice > ask:
            waiting = False
        else:
            time.sleep(delay)
    return ask

        

Bl3pApi = bl3papi.Bl3pApi

public_key = ""
secret_key = ""

b = Bl3pApi('https://api.bl3p.eu/1/', public_key, secret_key)

currentOrder = 0
profitPercentage = 2
highBoundary = 4
delay = 100

printBalances()

mainloop = True
while mainloop:
    buyPrice = waitForBuy(highBoundary, delay)
    spend = eurToSatoshi(buyPrice)
    if addOrder('bid', spend, buyPrice):
        trackOrderStatus(currentOrder, delay)
    targetPrice = calculateTarget(buyPrice, profitPercentage)
    # print targetPrice
    availableBTC = getAvailableBalance('btc')
    if addOrder('ask', availableBTC, targetPrice):
        trackOrderStatus(currentOrder, delay)

