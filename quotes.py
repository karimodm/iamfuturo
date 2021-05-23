#!/usr/bin/env python

import asyncio
import websockets
import datetime
import json
import re
import time
import threading
import logging

class Manipulator:
    async def process(self):
        try:
            async with websockets.connect(self.uri) as websocket:
                await websocket.send(self.sub)
                async for message in websocket:
                    if self.accessor(message):
                        await websocket.close()
        except Exception as error:
            logging.getLogger(self.__class__.__name__).error(error)

class Deribit(Manipulator):
    uri = 'wss://www.deribit.com/ws/api/v2/'
    #sub = '{"id":36,"method":"public/subscribe","params":{"channels":["ticker.BTC-28MAY21.100ms"]}}'

    def __init__(self, prefix = 'BTC', collect_timeout = 1):
        self.sub = {"id":1,"method":"public/subscribe","params":{"channels":[]}}
        today = datetime.date.today()
        increment = 0 
        for weeks in range(54):
            next_friday = today + datetime.timedelta( (4-today.weekday()) % 7 + increment)
            self.sub['params']['channels'].append("ticker." + next_friday.strftime(f"{prefix}-%d%b%y").replace(f"{prefix}-0", f"{prefix}-").upper() + ".100ms")
            increment = increment + 7
        self.prefix = prefix
        self.sub = json.dumps(self.sub)
        self.syms = []
        self.res = []
        self.tick = time.time()
        self.collect_timeout = collect_timeout

    def _determine_expiration(self, symbol):
        from datetime import datetime
        return datetime.strptime(symbol, f"{self.prefix}-%d%b%y")

    def accessor(self, obj):
        if time.time() - self.tick > self.collect_timeout:
            return True
        obj = json.loads(obj)
        try:
            fut = obj['params']['data']
            if fut['instrument_name'] in self.syms:
                return False
            self.syms.append(fut['instrument_name'])
            self.res.append({
                'source': 'Deribit',
                'symbol': fut['instrument_name'],
                'mark'  : fut['mark_price'],
                'last'  : fut['last_price'],
                'index' : fut['index_price'],
                'expir' : self._determine_expiration(fut['instrument_name'])
            })
        finally:
            return False

class Bybit(Manipulator):
    uri = 'wss://ws2.bybit.com/realtime' 
    #bybit_sub = '{"op":"subscribe","args":["public.notice","instrument_info.all","index_quote_20.100ms.BTCUSDM21"]}'

    def __init__(self, prefix = 'BTC'):
        self.prefix = prefix
        self.sub = {"op":"subscribe","args":["instrument_info.all"]}
        self.sub = json.dumps(self.sub)
        self.res = []

    def _determine_expiration(self, symbol):
        from datetime import datetime
        from dateutil.relativedelta import relativedelta, FR
        def switcher(symbol):
            match = re.match(self.prefix + 'USD([A-Z])(\d{2})', symbol)
            L = match[1]
            year = match[2]

            if      L == 'K': # March
                return datetime.strptime("0104" + year, "%d%m%y")
            elif    L == 'M': # June
                return datetime.strptime("0107" + year, "%d%m%y")
            elif    L == 'U': # September
                return datetime.strptime("0110" + year, "%d%m%y")
            elif    L == 'Z': # December
                return datetime.strptime("0101" + str(int(year) + 1), "%d%m%y")
            else:
                raise Exception("I do not understand this quarter letter!")

        return switcher(symbol) + relativedelta(days=-1, weekday=FR(-1))


    def accessor(self, obj):
        obj = json.loads(obj)
        try:
            inverse_futures = filter(lambda e: re.match(self.prefix + 'USD[A-Z]\d{2}', e['symbol']), obj['data'])
            self.res = []
            for fut in inverse_futures:
                self.res.append({
                    'source': 'Bybit',
                    'symbol': fut['symbol'],
                    'mark'  : float(fut['mark_price_e4']) / 10000,
                    'last'  : float(fut['last_price_e4']) / 10000,
                    'index' : float(fut['index_price_e4'])/ 10000,
                    'expir' : self._determine_expiration(fut['symbol'])
                })
            return True
        except KeyError:
            return False

class Binance(Manipulator):
    uri = 'wss://dstream.binance.com/ws/rawstream' 

    def __init__(self, prefix = 'BTC'):
        self.prefix = prefix
        self.sub = { "method": "SUBSCRIBE", "params": [ prefix.lower() + "usd@markPrice@1s" ], "id": 1 }
        self.sub = json.dumps(self.sub)
        self.res = []

    def _determine_expiration(self, symbol):
        from datetime import datetime
        return datetime.strptime(symbol, f"{self.prefix}USD_%y%m%d")

    def accessor(self, obj):
        obj = json.loads(obj)
        try:
            delivery_futures = filter(lambda e: re.match(self.prefix + 'USD_\d{6}', e['s']), obj)
            res = []
            for fut in delivery_futures:
                res.append({
                    'source': 'Binance',
                    'symbol': fut['s'],
                    'mark'  : round(float(fut['p']), 2),
                    'last'  : None,
                    'index' : None,
                    'expir' : self._determine_expiration(fut['s'])
                })
            self.res = res
            return True
        except:
            return False

class BitMEX(Manipulator):
    uri = 'wss://www.bitmex.com/realtime'
    #{"table":"instrument","action":"update","data":[{"symbol":"XBTU21","openValue":368518057142,"fairBasis":965.78,"fairPrice":40542.96,"markPrice":40542.96,"indicativeSettlePrice":39577.18,"timestamp":"2021-05-20T06:13:45.000Z"}]}

    def __init__(self, collect_timeout = 2, prefix = 'BTC'):
        if prefix == 'BTC':
            self.prefix = 'XBT'
        else:
            self.prefix = prefix
        self.sub = {"op":"subscribe","args":["instrument"]}
        self.sub = json.dumps(self.sub)
        self.syms = []
        self.res = []
        self.tick = time.time()
        self.collect_timeout = collect_timeout

    def _determine_expiration(self, symbol):
        from datetime import datetime
        from dateutil.relativedelta import relativedelta, FR
        def switcher(symbol):
            match = re.match(self.prefix + '([A-Z])(\d{2})', symbol)
            L = match[1]
            year = match[2]

            if      L == 'K': # March
                return datetime.strptime("0104" + year, "%d%m%y")
            elif    L == 'M': # June
                return datetime.strptime("0107" + year, "%d%m%y")
            elif    L == 'U': # September
                return datetime.strptime("0110" + year, "%d%m%y")
            elif    L == 'Z': # December
                return datetime.strptime("0101" + str(int(year) + 1), "%d%m%y")
            else:
                raise Exception("I do not understand this quarter letter!")

        return switcher(symbol) + relativedelta(days=-1, weekday=FR(-1))


    def accessor(self, obj):
        if time.time() - self.tick > self.collect_timeout:
            return True
        obj = json.loads(obj)
        try:
            delivery_futures = filter(lambda e: re.match(self.prefix + '[A-Z]\d{2}', e['symbol']) and e['symbol'] not in self.syms, obj['data'])
            for fut in delivery_futures:
                self.res.append({
                    'source': 'BitMEX',
                    'symbol': fut['symbol'],
                    'mark'  : fut['fairPrice'],
                    'last'  : None,
                    'index' : fut['indicativeSettlePrice'],
                    'expir' : self._determine_expiration(fut['symbol'])
                })
                self.syms.append(fut['symbol'])
        finally:
            return False

def _get_or_create_eventloop():
    try:
        return asyncio.get_event_loop()
    except RuntimeError as ex:
        if "There is no current event loop in thread" in str(ex):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return asyncio.get_event_loop()

def get_future_data_from_source(manipulator: Manipulator):
    _get_or_create_eventloop().run_until_complete(
            manipulator.process()
    )
    return manipulator.res

def get_future_data(coin = 'BTC'):
    deribit = Deribit(prefix = coin)
    binance = Binance(prefix = coin)
    bybit = Bybit(prefix = coin)
    bitmex = BitMEX(prefix = coin)
    _get_or_create_eventloop().run_until_complete(
        asyncio.gather(
            deribit.process(), binance.process(), bybit.process(), bitmex.process()
        )
    )
    return { 'Deribit': deribit.res, 'Binance': binance.res, 'Bybit': bybit.res, 'BitMEX': bitmex.res }
