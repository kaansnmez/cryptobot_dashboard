from binance.client import Client
from binance.cm_futures import CMFutures
from binance.enums import *
import pandas as pd
import datetime,time
import numpy as np
import requests
import websocket
import json
import urllib.request
import os,sys
import streamlit as st



def read_account_info_fromtxt():
    config={'binance':{'api_key':"",
                       'api_secret':""}
            }
    config['binance']['api_key']=os.environ['api_key']
    config['binance']['api_key']=os.environ['api_secret']
    return config

config_dict=read_account_info_fromtxt()
api_key=config_dict['binance']['api_key']
api_secret=config_dict['binance']['api_secret']

def check_internet_connection(host='https://testnet.binancefuture.com'):
    try:
        urllib.request.urlopen(host)
        return True
    except:
        print("No Internet Connection")


def connect_binance(api_key,api_secret):
    client= Client(api_key,api_secret,testnet=True)
    client.API_TESTNET_URL='https://testnet.binancefuture.com/fapi'
    client.API_URL='https://testnet.binancefuture.com/fapi'
    return client

def connect_future_binance(api_key,api_secret):
    cm_futures_client = CMFutures(key=api_key, secret=api_secret,base_url='https://testnet.binancefuture.com')
    return cm_futures_client


def get_future_balance_assets(client):
    asssets_balance=client.futures_account_balance()
    assets=pd.DataFrame(asssets_balance)
    assets['balance']=assets['balance'].astype('float')
    assets=assets[assets['balance']>0.0]
    assets_df=pd.DataFrame(assets)
    return assets_df

def get_klines_data(symbol,interval="4h",UTC_OFFSET=3):
    loop_1=True
    while loop_1:
        try:
            url = 'https://api.binance.com/api/v3/klines'
            params = {
              'symbol': symbol,
              'interval': interval,
              'limit':1000  
              }
            klines_data=requests.get(url, params=params).json()
            klines_df=pd.DataFrame(klines_data,columns=['open_time','open','high','low','close','volume',
                                                        'close_time','quote_asset_volume','number_of_trades','taker_buy_base_volume',
                                                        'taker_buy_quote_volume','ignore'])
            klines_df['open_time']=(pd.to_datetime(klines_df['open_time'],unit='ms')+datetime.timedelta(hours=UTC_OFFSET)).astype(str)
            klines_df['close_time']=(pd.to_datetime(klines_df['close_time'],unit='ms')+datetime.timedelta(hours=UTC_OFFSET)).astype(str)
            for col in list(klines_df.columns[1:].drop('close_time')):
                klines_df[col]=klines_df[col].astype('float')
            loop_1=False
            return klines_df
        except:
            print('Error')
    

class stream_events_symbol():
    def __init__(self,symbol='btcusdt',interval='4h'):
        self.his_price=[0]
        self.symbol=symbol
        self.interval=interval
        self.klines_df=pd.DataFrame()
        self.json_data={}
        self.ws=None
        self.socket = 'wss://stream.binance.us:443/stream?streams={}@kline_{}'.format(self.symbol.lower(),self.interval.lower())
    def on_message(self,ws, message):
        
        threshold_price=30
        if check_internet_connection():
            cm_futures_client=connect_future_binance(api_key,api_secret)
            loop1=True
            while loop1:
                try:
                    json_data = json.loads(message)
                    columns=['open_time','close_time','symbol','interval','first_trade_id','last_trade_id','open','close','high','low','volume',
                             'number_of_trades','kline_closed?','quote_asset_volume','taker_buy_base_volume','taker_buy_quote_volume','ignore']
                    data = json_data['data']
                    klines_data=list(data['k'].values())
                    klines_data=np.reshape(klines_data, (17, 1)).T
                    self.klines_df=pd.DataFrame(klines_data,columns=columns)
                    self.klines_df=self.klines_df.drop(['symbol','interval','first_trade_id','last_trade_id'],axis=1)
                    self.klines_df['open_time']=pd.to_datetime(self.klines_df['open_time'],unit='ms')
                    self.klines_df['close_time']=pd.to_datetime(cm_futures_client.time()['serverTime'],unit='ms')+datetime.timedelta(hours=3)
                    sort_column=['open_time', 'open', 'close', 'high', 'low', 'volume','close_time',
                           'number_of_trades','kline_closed?', 'quote_asset_volume', 'taker_buy_base_volume',
                           'taker_buy_quote_volume', 'ignore']
                    for col in list(self.klines_df.columns[1:].drop(['close_time','kline_closed?'])):
                        self.klines_df[col]=self.klines_df[col].astype('float')
                    self.klines_df=self.klines_df[sort_column]
                    loop1=False
                    if (self.his_price[0]!=0):
                        if (self.klines_df['close']>(self.his_price[0]/threshold_price)):
                            loop1=True
                except:
                    print("Have problem in websocket data.")
    #def kline(self,json_message):
        
    #    return klines_df
    def on_error(self,ws, error):
        print(error)
    def on_close(self,ws, close_status_code, close_msg):
        print("### closed ###")
        self.ws.keep_running=False
    def on_open(self,ws):
        print("Opened connection")
    def run(self):
        self.ws = websocket.WebSocketApp(url=self.socket, on_open=self.on_open, on_message=self.on_message,on_error=self.on_error, on_close=self.on_close)
        self.ws.run_forever()
        
def change_leverage(client,symbol,leverage_val):
    global response
    global isolated
    status={}
    c=client.futures_account()
    for index in c['positions']:
        if index['symbol']==symbol:
            leverage=int(index['leverage'])
            isolated=index['isolated']
    if leverage != leverage_val:
        response = client.futures_change_leverage(symbol=symbol, leverage=leverage_val, recvWindow=6000)
        status['leverage']=leverage_val
    else:
        status['leverage']=leverage
    if isolated != True:
        isolated=client.futures_change_margin_type(symbol=symbol,marginType='ISOLATED')
        time.sleep(0.5)
        print(isolated)
    else:
        status['Isolated']=isolated
    return status

def precision_asset(client,symbol,leverage,trade_size=1):
    info = client.futures_exchange_info() 
    info = info['symbols']
    for x in range(len(info)):
        if info[x]['symbol'] == symbol:
             precision=int(info[x]['quantityPrecision'])
             for filt in info[x]['filters']:
                 if filt['filterType']=='MARKET_LOT_SIZE':
                     min_market_lot_size=float(filt['minQty'])
                 if filt['filterType']=='MIN_NOTIONAL':
                     notional=float(filt['notional'])
    
    
    price=float(client.futures_symbol_ticker(symbol=symbol)['price'])
    min_mark=max(min_market_lot_size,round((notional/price),precision))#min order amount
    min_mark_p=round(min_mark * price,2) #Min açılabilecek poz büyüklüğü $
    if trade_size==1: # trade_size default
        lot_size=1
    else:
        lot_size=trade_size/min_mark_p
    trade_size_in_dollars = round(lot_size*min_mark_p*leverage,2) #kaldıraç pozisyon büyüklüğü
    print("Min_buy_lot_price:",min_mark_p)
    order_amount = trade_size_in_dollars / price
    if order_amount<0.01:
        order_amount=0.01
    precise_order_amount = "{:0.0{}f}".format(order_amount, precision)
    return precise_order_amount,price


def new_order(client,symbol,side,quantity,price=None,type='MARKET',isIsolated=True):
    if type=='LIMIT':
        response = client.futures_create_order(
          symbol=symbol,
          side=side,
          type=type,
          quantity=quantity,
          price=price,
          timeInForce='GTC'
      )  
    else:
        response = client.futures_create_order(
            symbol=symbol,
            side=side,
            type=type,
            quantity=quantity,
            
        )
    return response

def all_margin_orders(client):
    while True:
        try:
            result=[symbol for symbol in client.futures_account()['positions'] if float(symbol['positionInitialMargin'])>0.0]
            if float(result[0]['positionAmt'])>0:
                result[0]['positionSide']='LONG'
            else:
                result[0]['positionSide']='SHORT'
            return result
        except:
            result=[]
            return result

def get_open_orders(client,pos):
    open_orders=[False]
    try:
        pos_side=client.futures_get_open_orders()[0]['side']
        if pos==pos_side:
            open_orders[0]=True
        else:
            open_orders[0]=False
    except:
        open_orders=[False]
    return open_orders

def get_order_book(client,symbol):
    order_book=client.futures_order_book(symbol=symbol)
    return order_book
