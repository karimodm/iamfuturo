#!/usr/bin/env python

import asyncio
import websockets
import datetime
import json
import re
import time
import threading

import ipdb

async def subscribe(manipulator):
    async with websockets.connect(manipulator.uri) as websocket:
        await websocket.send(manipulator.sub)
        async for message in websocket:
            if manipulator.accessor(message):
                await websocket.close()

class Deribit:
    uri = 'wss://www.deribit.com/ws/api/v2/'
    #sub = '{"id":36,"method":"public/subscribe","params":{"channels":["ticker.BTC-28MAY21.100ms"]}}'

    def __init__(self, collect_timeout = 1):
        self.sub = {"id":36,"method":"public/subscribe","params":{"channels":[]}}
        today = datetime.date.today()
        increment = 0 
        for weeks in range(54):
            next_friday = today + datetime.timedelta( (4-today.weekday()) % 7 + increment)
            self.sub['params']['channels'].append("ticker." + next_friday.strftime("BTC-%d%b%y").upper() + ".100ms")
            increment = increment + 7
        self.sub = json.dumps(self.sub)
        self.syms = []
        self.res = []
        self.tick = time.time()
        self.collect_timeout = collect_timeout

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
                'symbol': fut['instrument_name'],
                'mark'  : fut['mark_price'],
                'last'  : fut['last_price'],
                'index' : fut['index_price']
            })
        finally:
            return False

    async def process(self):
        async with websockets.connect(self.uri) as websocket:
            await websocket.send(self.sub)
            async for message in websocket:
                if self.accessor(message):
                    await websocket.close()

class Bybit:
    uri = 'wss://ws2.bybit.com/realtime' 
    #bybit_sub = '{"op":"subscribe","args":["public.notice","instrument_info.all","index_quote_20.100ms.BTCUSDM21"]}'

    def __init__(self):
        self.sub = {"op":"subscribe","args":["instrument_info.all"]}
        self.sub = json.dumps(self.sub)

    def accessor(self, obj):
        obj = json.loads(obj)
        try:
            inverse_futures = list(filter(lambda e: re.match('BTCUSD[A-Z]\d{2}', e['symbol']), obj['data']))
            res = []
            for fut in inverse_futures:
                res.append({
                    'symbol': fut['symbol'],
                    'mark'  : fut['mark_price_e4'],
                    'last'  : fut['last_price_e4'],
                    'index' : fut['index_price_e4']
                })
            self.res = res
            return True
        except KeyError:
            return False

    async def process(self):
        async with websockets.connect(self.uri) as websocket:
            await websocket.send(self.sub)
            async for message in websocket:
                if self.accessor(message):
                    await websocket.close()

class Binance:
    def __init__(self, collect_timeout = 5):
        from binance.client import Client
        from binance.websockets import BinanceFuturesSocketManager
        client = Client('', '')
        bfm = BinanceFuturesSocketManager(client)
        bfm.start_futures_markprice_socket(self.accessor)
        self.collect_timeout = collect_timeout
        self.bfm = bfm
        self.accessed = threading.Event()

    def accessor(self, obj):
        ipdb.set_trace()
        print(obj)
        return
        obj = json.loads(obj)
        try:
            inverse_futures = list(filter(lambda e: re.match('BTCUSD[A-Z]\d{2}', e['symbol']), obj['data']))
            res = []
            for fut in inverse_futures:
                res.append({
                    'symbol': fut['symbol'],
                    'mark'  : fut['mark_price_e4'],
                    'last'  : fut['last_price_e4'],
                    'index' : fut['index_price_e4']
                })
            self.res = res
            return True
        except KeyError:
            return False
        self.accessed.set()

    async def process(self):
        self.bfm.start()
        try:
            loop = asyncio.get_running_loop()
            await asyncio.wait_for(loop.run_in_executor(None, self.accessed.wait), self.collect_timeout)
        finally:
            self.bfm.reactor.callFromThread(self.bfm.reactor.stop)
            print(">>>> JOINED")
    

o = Binance()
#o = Deribit()

asyncio.get_event_loop().run_until_complete(
    o.process()
    #subscribe(bybit_uri, bybit_sub, bybit_accessor)
    #subscribe(binance_uri, binance_sub, binance_accessor)
)
print(o.res)

#o.bfm.start()

#print(o.res)
