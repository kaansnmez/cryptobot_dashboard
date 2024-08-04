import binance_future_process
from binance_future_process import get_klines_data as kline
from binance_future_process import connect_future_binance
from binance_future_process import connect_binance
from binance_future_process import precision_asset
from binance_future_process import new_order
from binance_future_process import change_leverage
from binance_future_process import all_margin_orders
from binance_future_process import stream_events_symbol
from binance_future_process import get_open_orders
from binance_future_process import get_order_book
from binance_future_process import check_internet_connection
from binance_future_process import get_future_balance_assets
from binance_future_process import read_account_info_fromtxt

import time
import numpy as np
import pandas as pd
from bolinger_with_wavetrend import waveTrend
from bolinger_with_wavetrend import bolinger_strategies
from googleapiclient.discovery import build
from google.oauth2 import service_account
import datetime
import threading
import warnings
import api
import os,sys
import subprocess
import streamlit as st
warnings.filterwarnings("ignore")



def check_time(cm_futures_client):
    """
    Function return binance serverTime.
    Parameters
    ----------
    cm_futures_client : binance.cm_futures module Object
        

    Returns
    -------
    time_local_server : datetime
        

    """
    
    while True: 
        try:
            time_local_server=pd.to_datetime(cm_futures_client.time()['serverTime'],unit='ms')+datetime.timedelta(hours=UTC_OFFSET)
            break
        except:
            pass
    return time_local_server    
    
def check_position(client,pos):
    """
    Function is controlling which opened position data (short/long/none)

    Parameters
    ----------
    client : TYPE
        DESCRIPTION.
    pos : TYPE
        DESCRIPTION.

    Returns
    -------
    pos_opens : TYPE
        DESCRIPTION.

    """
    pos_opens=[False]
    try:
        for key,values in all_margin_orders(client)[0].items():
            if values=='BTCUSDT':
                if all_margin_orders(client)[0]['positionSide']==pos:
                    pos_opens[0]=True
            
        #if orders_opens==[]:
        #   orders_opens.append(False)
    except(ValueError,IndexError):
        pos_opens[0]=False
    return pos_opens
def pos_history_append_df(cm_futures_client,df,response,entry=np.nan,close=np.nan):
    """
    Açılan pozisyonun güncel verisi

    Parameters
    ----------
    cm_futures_client : TYPE
        DESCRIPTION.
    df : TYPE
        DESCRIPTION.
    response : TYPE
        DESCRIPTION.
    entry : TYPE, optional
        DESCRIPTION. The default is np.NaN.
    close : TYPE, optional
        DESCRIPTION. The default is np.NaN.

    Returns
    -------
    None.

    """
    global pos_df
    while True:
        try:
            time=check_time(cm_futures_client)
            symbol=response['symbol']
            side=response['side']
            lev=all_margin_orders(client)[0]['leverage']
            margin_size=all_margin_orders(client)[0]['initialMargin']
            pos_raw=[{'time':time,'symbol':symbol,'entry':entry,'side':side,'leverage':lev,'close':close,'margin_size':margin_size,'profit':np.NaN}]
            pos_df=pos_df.append(pos_raw,ignore_index=True)
            break
        except:
            pass
def calc_profit(pos_df,stream,streaming=False):
    """
    Function is calculating profit.

    Parameters
    ----------
    pos_df : TYPE
        DESCRIPTION.

    Returns
    -------
    int
        DESCRIPTION.

    """
    if streaming==True:
        short=check_position(client, 'SHORT')
        long=check_position(client, 'LONG')
        if (short[0]==False) & (long[0]==False):
            return None
        else:
            pos_side=pos_df.loc[len(pos_df)-1,'side']
            #pos_df.tail(1)['side'].values[0]
            entryPrice=pos_df.loc[len(pos_df)-1,'entry']
            mark_price=float(stream.klines_df['close'].values[0])
            qty=float(pos_df.loc[len(pos_df)-1,'qty'])
            profit=(mark_price-entryPrice)*(qty)
            if (short[0]==True) & (profit!=0.0): profit*=-1
            return profit
    else:
        try:
            pos_side=pos_df.loc[len(pos_df)-1,'side']
            entryPrice=pos_df.loc[len(pos_df)-1,'entry']
            qty=float(pos_df.loc[len(pos_df)-1,'qty'])
            closePrice=pos_df.loc[len(pos_df)-1,'close_real_data']
            lev=float(pos_df.loc[len(pos_df)-1,'leverage'])
            margin_size=float(pos_df.loc[len(pos_df)-1,'margin_size'])
            profit=(closePrice-entryPrice)*(qty)
            
            if (pos_side=='SELL') & (profit!=0.0): profit*=-1
            pos_df.loc[len(pos_df)-1,'profit']=profit
        except:
            return 1
    
def append_strategy_df (stream,df_15m):
    """
    Function add last websocket data to kline last row

    Parameters
    ----------
    stream : TYPE
        DESCRIPTION.
    df_15m : TYPE
        DESCRIPTION.

    Returns
    -------
    df_15m : TYPE
        DESCRIPTION.

    """
    df_15m=df_15m.drop(df_15m.tail(1).index)
    df_15m=pd.concat([df_15m,stream.klines_df],axis=0,ignore_index=True)
    df_15m=df_15m.reset_index(drop=True)
    return df_15m

def check_order_book(client,symbol,pos):
    """
    This function checking to exchange order book and returning first value

    Parameters
    ----------
    client : TYPE
        DESCRIPTION.
    symbol : TYPE
        DESCRIPTION.
    pos : TYPE
        DESCRIPTION.

    Returns
    -------
    price : TYPE
        DESCRIPTION.

    """
    order_book=get_order_book(client,symbol)
    asks=order_book['asks'] # Sell book
    bids=order_book['bids'] # Buy book
    if pos=='SELL':
        price=bids[0][0]
    else:
        price=asks[0][0]
    return price
def wt_cross_accumulation_decision(df_15m,wt_signal,side='SELL',pos=False):
    """
    This function is reducing risk and protect budget from accumulation zone

    Parameters
    ----------
    df_15m : TYPE
        DESCRIPTION.
    wt_signal : TYPE
        DESCRIPTION.
    side : TYPE, optional
        DESCRIPTION. The default is 'SELL'.
    pos : TYPE, optional
        DESCRIPTION. The default is False.

    Returns
    -------
    bool
        DESCRIPTION.

    """
    #Buy veya sell işlemi alındıktan sonra eğer threshold değerine gelmeden pozisyon terse düştüğünde 
    #threshold yüzünden alım satım olmuyor bu yüzden sell için eğer 2 yi geçmiyor ise -2 yi geçerse threshold true yap
    #check_pos_short=check_position(client,pos='SHORT')
    #check_pos_long=check_position(client,pos='LONG')
    global wt_history
    time=df_15m.loc[len(df_15m)-1,'open_time']
    price=df_15m.loc[len(df_15m)-1,'close']
    pos_raw=[{'time':time,'price':price,'wt_cross':wt_signal,'position_open?':pos}]
    wt_history=wt_history.append(pos_raw,ignore_index=True)
    if (pos_df.index.size!=0) & (len(wt_history[wt_history['position_open?']==True])>3): 
        last_index=wt_history[wt_history['position_open?']==True].index.to_list()[-3]
        wt_history=wt_history.loc[last_index:len(wt_history)-1].reset_index(drop=True)
    if wt_history[wt_history['position_open?']==True].size==0:
        return True
    else:
        for i in range(len(wt_history['position_open?'])-1,-1,-1):
            if wt_history['position_open?'][i]==True:
                if side=='BUY':
                    threshold=-5.0
                    if wt_history.loc[i:len(wt_history)-1,'wt_cross'].min()<threshold:
                        return True
                    else:
                        if wt_history.loc[i:len(wt_history)-1,'wt_cross'].max()>1.75:
                            return True
                        return False

                else:    
                    threshold=5.0
                    if wt_history.loc[i:len(wt_history)-1,'wt_cross'].max()>threshold:
                        return True
                    else:
                        if wt_history.loc[i:len(wt_history)-1,'wt_cross'].min()<-1.75:
                            return True
                        return False
                    
def short_pos_open(wt_signal,df_15m,stream,accumulation_decision):
    """
    Open short position

    Parameters
    ----------
    wt_signal : TYPE
        DESCRIPTION.
    df_15m : TYPE
        DESCRIPTION.
    stream : TYPE
        DESCRIPTION.
    accumulation_decision : TYPE
        DESCRIPTION.

    Returns
    -------
    None.

    """
    try:
        if (rem_signal[-1]!=2):
            check_pos_short=check_position(client,pos='SHORT')
            check_pos_long=check_position(client,pos='LONG')
            if (check_pos_short[0]==False):
                print("wt_cross:",wt_signal)
                print("accumulation: ",accumulation_decision)
                if (wt_signal<0.0) & accumulation_decision:
                    #log(cm_futures_client,df_15m,log=2) #loglar içeri
                    #signal_history_append_df(df_15m)
                    if (check_pos_long[0]==True):
                        print("--------LONG CLOSED------------")
                        order_price=check_order_book(client, symbol='BTCUSDT', pos='SELL')
                        still_open_qty=str(abs(float(all_margin_orders(client)[0]['positionAmt'])))
                        levereage=change_leverage(client,'BTCUSDT',20)
                        precsion_order_amount,price=precision_asset(client,'BTCUSDT',leverage=levereage['leverage'],trade_size=100)
                        response=new_order(client,symbol='BTCUSDT',side='SELL',type='LIMIT',price=order_price,quantity=still_open_qty)
                        time.sleep(0.5)
                        pos_df['close'].iloc[-1]=float(order_price)
                        pos_df['close_real_data'].iloc[-1]=float(stream.klines_df['close'][0])
                        calc_profit(pos_df,stream)
                        time.sleep(1)
                        save_df(pos_df,early=False)
                        
                    check_pos_short=check_position(client,pos='SHORT')
                    open_orders=get_open_orders(client, pos='SELL')
                    order_price=check_order_book(client, symbol='BTCUSDT', pos='SELL')
                    if (check_pos_short[0]==False) & (open_orders[0]!='SELL'):
                        print("--------SHORT OPENED------------")
                        levereage=change_leverage(client,'BTCUSDT',20)
                        precsion_order_amount,price=precision_asset(client,'BTCUSDT',leverage=levereage['leverage'],trade_size=100)
                        response=new_order(client,symbol='BTCUSDT',side='SELL',type='LIMIT',price=order_price,quantity=precsion_order_amount)
                        time.sleep(0.5)
                        pos_history_append_df(cm_futures_client,df_15m,response,entry=df_15m.tail(1)['close'].values[0])
                        wt_cross_accumulation_decision(df_15m,wt_signal,side='SELL',pos=True)
                        still_open_qty=str(abs(float(all_margin_orders(client)[0]['positionAmt'])))
                        pos_df['qty'].iloc[-1]=still_open_qty
                        time.sleep(1)
                        save_df(pos_df)
                        print(response)
    except:
        print("Something Wrong , Trying again.. ")
    
def long_pos_open(wt_signal,df_15m,stream,accumulation_decision):
    """
    Open long position

    Parameters
    ----------
    wt_signal : TYPE
        DESCRIPTION.
    df_15m : TYPE
        DESCRIPTION.
    stream : TYPE
        DESCRIPTION.
    accumulation_decision : TYPE
        DESCRIPTION.

    Returns
    -------
    None.

    """
    try:
        if (rem_signal[-1]!=1):
            check_pos_short=check_position(client,pos='SHORT')
            check_pos_long=check_position(client,pos='LONG')
            if (check_pos_long[0]==False):
                print("wt_cross:",wt_signal)
                print("accumulation: ",accumulation_decision)
                if (wt_signal>0.0) & accumulation_decision:
                   # log(cm_futures_client,df_15m,log=1)
                    #signal_history_append_df(df_15m)
                    if (check_pos_short[0]==True):
                        order_price=check_order_book(client, symbol='BTCUSDT', pos='BUY')
                        print("--------SHORT CLOSED------------")
                        still_open_qty=str(abs(float(all_margin_orders(client)[0]['positionAmt'])))
                        levereage=change_leverage(client,'BTCUSDT',20)
                        precsion_order_amount,price=precision_asset(client,'BTCUSDT',leverage=levereage['leverage'],trade_size=100)
                        response=new_order(client,symbol='BTCUSDT',side='BUY',type='LIMIT',price=order_price,quantity=still_open_qty)
                        time.sleep(0.5)
                        pos_df['qty'].iloc[-1]=still_open_qty
                        pos_df['close'].iloc[-1]=float(order_price)
                        pos_df['close_real_data'].iloc[-1]=float(stream.klines_df['close'][0])
                        calc_profit(pos_df,stream)
                        time.sleep(1)
                        save_df(pos_df,early=False)
                        
                    check_pos_long=check_position(client,pos='LONG')
                    open_orders=get_open_orders(client, pos='BUY')
                    order_price=check_order_book(client, symbol='BTCUSDT', pos='BUY')
                    #eğer decision olmazsa buraya wt at ve threshold u eğer işlem yoksa 2 al
                    if (check_pos_long[0]==False) & (open_orders[0]!='BUY'):
                        print("--------LONG OPENED------------")
                        levereage=change_leverage(client,'BTCUSDT',20)
                        precsion_order_amount,price=precision_asset(client,'BTCUSDT',leverage=levereage['leverage'],trade_size=100)
                        response=new_order(client,symbol='BTCUSDT',side='BUY',type='LIMIT',price=order_price,quantity=precsion_order_amount)
                        pos_history_append_df(cm_futures_client,df_15m,response,entry=df_15m.tail(1)['close'].values[0])
                        time.sleep(0.5)
                        wt_cross_accumulation_decision(df_15m,wt_signal,side='BUY',pos=True)
                        still_open_qty=str(abs(float(all_margin_orders(client)[0]['positionAmt'])))
                        pos_df['qty'].iloc[-1]=still_open_qty
                        time.sleep(1)
                        save_df(pos_df)
                        print(response)
    except:
        print("Something Wrong , Trying again.. ")
def connect_google_sheetapi():
    service_dict={}
    for key,value in os.environ:
        if (key!='api_key') & (key!='api_secret'):
            service_account[key]=value
    SERVICE_ACCOUNT_FILE = service_dict
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    creds = None
    creds = service_account.Credentials.from_service_account_info(SERVICE_ACCOUNT_FILE,scopes=SCOPES)
    service = build('sheets','v4',credentials=creds)
    return service

def get_df_from_google_sheet():
    SAMPLE_SPREADSHEED_ID = '1l10O7erT4XjHyKBKwR1KMwoxw0Dwi49uyL3cArJRGIc'
    service=connect_google_sheetapi()
    sheet = service.spreadsheets()
    result= sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEED_ID,
                               range="hs"
                               ).execute()
    raw_data=result['values']
    pos_df=pd.DataFrame(raw_data,columns=['time','symbol','side','entry','leverage','close','close_real_data','qty','margin_size','profit'])
    return pos_df

def save_df(df,early=True):
    """
    Saving posdf data to .csv file.

    Parameters
    ----------
    df : TYPE
        DESCRIPTION.

    Returns
    -------
    None.

    """
    SAMPLE_SPREADSHEED_ID = '1l10O7erT4XjHyKBKwR1KMwoxw0Dwi49uyL3cArJRGIc'
    service=connect_google_sheetapi()
    sheet = service.spreadsheets()
    columns=['entry','close','close_real_data','qty','margin_size','profit']
    raw_data=df.copy()
    for x in columns:
        raw_data.loc[raw_data.shape[0]-1,x]=round(float(raw_data.loc[raw_data.shape[0]-1,x]),3)
        raw_data.loc[raw_data.shape[0]-1,x]=str(raw_data.loc[raw_data.shape[0]-1,x]).replace('.',',')
    data_raw=raw_data.fillna('')
    data=[data_raw.loc[len(data_raw)-1].values.tolist()]
    data[0][0]=str(data[0][0])
    print(data)
    if early==False:
        result= sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEED_ID,
                                   range="hs"
                                   ).execute()
        last_len=len(result['values'])

        write=sheet.values().update(spreadsheetId=SAMPLE_SPREADSHEED_ID,
                                    range='hs!A{}:J{}'.format(last_len,last_len),
                                    valueInputOption="USER_ENTERED",
                                    body={"values":data}).execute()
    else:
        res= sheet.values().append(spreadsheetId=SAMPLE_SPREADSHEED_ID,
                                   range='hs!A1:J1',valueInputOption="USER_ENTERED",
                                   insertDataOption="INSERT_ROWS",body={"values":data}).execute()
        

def convert_json_decode_format(df):
    columns=['entry','close','close_real_data','qty','margin_size','profit','leverage']
    raw_df=df.fillna(0)
    for x in columns: 
        try:
            raw_df[x]=raw_df[x].apply(lambda x : float(str(x).replace(',','.')))
        except:
            pass
    return raw_df
    
base_df_1m=pd.DataFrame()
wt_history=pd.DataFrame(columns=['time','price','wt_cross','position_open?'])
#pos_df=pd.DataFrame(columns=['time','symbol','side','entry','leverage','close','close_real_data','qty','margin_size','profit'])
#pos_df=pd.read_csv("C:\\Users\\\kaan1\\OneDrive\\Masaüstü\\binance test bot\\pos_history_df_last.csv",names=['time','symbol','side','entry','leverage','close','close_real_data','qty','margin_size','profit'])
pos_df=convert_json_decode_format(get_df_from_google_sheet())

#pos_df['time']=pd.to_datetime(pos_df['time'])
#pos_df.to_csv("C:\\Users\\\kaan1\\OneDrive\\Masaüstü\\binance test bot\\pos_history_df_last.csv",index=False)
client=connect_binance(binance_future_process.api_key, binance_future_process.api_secret)
cm_futures_client=connect_future_binance(binance_future_process.api_key,binance_future_process.api_secret)


rem_wt=0
UTC_OFFSET=3
rem_signal=[np.nan]
rem_min=[np.nan]
app=api.flsk()
interval='15m'
rem_triger_time_dup=0
rem_triger_time=[0]

thread_list=[]

def run_stream():
    stream.run()
stream=stream_events_symbol(symbol='BtcUsdt',interval=interval)
#stream.ws.close()
thread = threading.Thread(target=run_stream,name="websocket")
thread_list.append(thread)

def rest_api():
    app.run() 
thread_api = threading.Thread(target=rest_api,name="api")
thread_list.append(thread_api)

def streamlit():
    subprocess.run(["streamlit", "run", r"web_app.py"])
st_thread=threading.Thread(target=streamlit,name="streamlit")
thread_list.append(st_thread)

def main():
    count=0
    global rem_triger_time
    global rem_triger_time_dup
    global rem_wt_cross
    global stream
    global thread
    rem_wt_cross=0
    rem_count=0
    rem_cross=[0]
    first_cross=True
    
    """
    def run_stream():
        stream.run()
    stream=stream_events_symbol(symbol='BtcUsdt',interval=interval)
    #stream.ws.close()
    thread = threading.Thread(target=run_stream,name="websocket")
    thread_list.append(thread)
    thread.start()
    time.sleep(5)
    
    def rest_api():
        app.run() 
    thread_api = threading.Thread(target=rest_api,name="api")
    thread_api.start()
    thread_list.append(thread_api)
    time.sleep(15)
    
    def streamlit():
        subprocess.run(["streamlit", "run", r"web_app.py"])
    st_thread=threading.Thread(target=streamlit,name="streamlit")
    thread_list.append(st_thread)
    st_thread.start()
    time.sleep(5)
    
    """
    def check_thread(thread_list,stream):
        thread_dict={"websocket":threading.Thread(target=run_stream,name="websocket"),
                     "api":threading.Thread(target=rest_api,name="api"),
                     "streamlit":threading.Thread(target=streamlit,name="streamlit")
                     }
        for index,thr in enumerate(thread_list):
            if thr.is_alive():
                continue
            else:
                print("{} thread is stopped unexpected. ".format(thr.name))
                if thr.name != 'websocket':
                    thread_dict[thr.name]._args[0].clear()
                thread_dict[thr.name].start()
                thread_list.pop(index)
                thread_list.append(thread_dict[thr.name])
                print("{} thread is started again..".format(thr.name))
                time.sleep(0.5)
    time.sleep(7)
    while True:
        if check_internet_connection():
            if thread.is_alive():
                check_thread(thread_list,stream)
                time_local_server=check_time(cm_futures_client)
                if (count%2==0) | (time_local_server.hour%4==0):
                    count=0
                    df_15m=kline(symbol='BTCUSDT',interval=interval)
                    count+=1
                    #stream.ws.close()  # Call this when you want to close
                    time.sleep(1)
                print("Live Threads: ",thread_list)
                while True:
                    try:
                        df_15m=append_strategy_df(stream, df_15m)
                        break
                    except:
                        pass
                time.sleep(0.25)
                wt1_15m,wt2_15m=waveTrend(df_15m)
                wt_signal=wt1_15m.values[-1]-wt2_15m.values[-1]
                print("remc div :",abs(rem_wt_cross-wt_signal))
                if (wt1_15m.loc[999]==-1) | ((abs(rem_wt_cross-wt_signal)>6) & (rem_wt_cross!=0)):
                    df_15m=kline(symbol='BTCUSDT',interval=interval)
                    time.sleep(0.25)
                    wt1_15m,wt2_15m=waveTrend(df_15m)
                rem_wt_cross=wt_signal
                time.sleep(0.25)
                BBbasis_15m,BBlower_15m,BBupper_15m=bolinger_strategies(df_15m)
                
                try:
                  
                    app.wt1_signal=wt1_15m
                    app.wt2_signal=wt2_15m
                    app.time=stream.klines_df['close_time']
                    app.kline_df=stream.klines_df
                    app.pos_df=pos_df
                    app.profit=calc_profit(pos_df,stream,streaming=True)
                    app.assets=get_future_balance_assets(client)
                    if (rem_triger_time[0]==0) | ((rem_triger_time[0]%2==0) & (rem_triger_time_dup !=rem_triger_time[0])):
                        app.kline_history=kline(symbol='BTCUSDT',interval='1d')
                    rem_triger_time_dup=rem_triger_time[0]
                    try:
                        rem_triger_time[0]=(pd.to_datetime(cm_futures_client.time()['serverTime'],unit='ms')+datetime.timedelta(hours=3)).minute
                    except:
                        pass
                    
                    
                except:
                    print("Have a problem for applying app data..")
                
                if (((rem_cross[0]<0) & (wt_signal>0)) | ((rem_cross[0]>0) & (wt_signal<0))) & (rem_count==0):
                    first_cross=True
                    rem_count+=1
                rem_cross[0]=wt_signal
                
                if first_cross==True:
                ## Natural Area Buy / Sell operations
                    if (df_15m.close.values[-1]<BBupper_15m.values[-1]) & (df_15m.close.values[-1]>BBlower_15m.values[-1]):
                        print("Bolinger Natural Area")
                        
                        if (wt_signal<0.0):
                            print("bearish area")
                            print("wt_cross:",wt_signal)
                            accumulation_decision=wt_cross_accumulation_decision(df_15m,wt_signal,side='SELL',pos=False)
                            short_pos_open(wt_signal,df_15m,stream,accumulation_decision)
                            
                        else:
                            if(wt_signal>0.0):
                                print("bullish area")
                                print("wt_cross:",wt_signal)
                                accumulation_decision=wt_cross_accumulation_decision(df_15m,wt_signal,side='BUY',pos=False)
                                long_pos_open(wt_signal,df_15m,stream,accumulation_decision)
                                
                        app.pos_df=pos_df
                        
                    ##Bollinger Upper Sell Operations     
                    else:
                        if df_15m.close.values[-1]>BBupper_15m.values[-1]:
                            print("Bolinger Upper area")
                            #if bolinger_with_wavetrend.obLevel2<wt1_15m.values[-1]:
                            print("wt_cross:",wt_signal)
    
                            print("sell signal")
                            accumulation_decision=wt_cross_accumulation_decision(df_15m,wt_signal,side='SELL',pos=False)
                            short_pos_open(wt_signal,df_15m,stream,accumulation_decision)
                                    
                                
                        ##Bollinger Lower Buy Operations       
                        else:
                            if df_15m.close.values[-1]<BBlower_15m.values[-1]:
                                print("Bolinger Lower area")
                                print("wt_cross:",wt_signal)
                                print("buy area")
                                accumulation_decision=wt_cross_accumulation_decision(df_15m,wt_signal,side='BUY',pos=False)
                                long_pos_open(wt_signal,df_15m,stream,accumulation_decision)
                                        
                                    #else: print("Waiting WaveTrend Buy Signal")
                        app.pos_df=pos_df
                else: 
                    print("Waiting First Buy/sell WaveTrend Cross")
                    print("WaveTrend: ",wt_signal)
                count+=1
            else:
                print("Socket is dead.") 
                stream.ws.close()
                thread.join()
                stream=stream_events_symbol(symbol='BtcUsdt',interval=interval)
                thread = threading.Thread(target=run_stream)
                thread.start()
                print("Starting again...")
                time.sleep(5)
if __name__=='__main__':
    for t in thread_list:
        t.start()
        time.sleep(10)
    main()
    
    
    
    #main()
    #cli.main_run(["web_app.py"])
    
    

