import numpy as np
import pandas as pd
import ta_py as ta


obLevel1=70 #Over bought level 2
obLevel2=55 #Over bought level 1
osLevel1=-70 #Over sold level 2
osLevel2=-55 #Over sold level 1

def hlc(df):
    df.high=df.high.astype(float)
    df.low=df.low.astype(float)
    df.close=df.close.astype(float)
    ap=(df.high+df.low+df.close)/3
    return ap

def ema(ap,n1):
    esa=ta.wma(ap,n1)
    while True:
        if len(esa)<len(ap):
            esa.insert(0, esa[0])
            
        else: break
    esa=pd.DataFrame(esa)[0]
    return esa
def sma(ap,n1):
    sma=ta.wma(ap,n1)
    while True:
        if len(sma)<len(ap):
            sma.insert(0, sma[0])
            
        else: break
    sma=pd.DataFrame(sma)[0]
    return sma
def waveTrend(df):
    n1=10 #Channel Length 15
    n2=21 # Average Length 42
    
    ap=hlc(df)
    esa=ema(ap,n1)
    d=ema(abs(ap-esa),n1)
    ci=(ap-esa)/(d*0.015)
    tci = ema(ci, n2)
    wt1 = tci
    wt2 = sma(wt1,4)
    wt_cross=wt1-wt2
    #calculate z-score
    mean_wt_cross=np.mean(wt_cross.values)
    std_wt_cross=np.std(wt_cross.values)
    z_score=(wt_cross.values-mean_wt_cross)/std_wt_cross
    if ((z_score[-1]>3)|(z_score[-1]<-3)):
        wt1.loc[999]=-1
        wt2.loc[999]=-1
        print("Above of Z-score limit :",z_score[-1])
        return wt1,wt2
    return wt1,wt2
def bolinger_strategies(df):
    
    #/////RSI
    RSIlength=10
    RSIoverSold=50
    RSIoverBought=50
    price=df.close.astype(float)
    vrsi=ta.rsi(price,RSIlength)
    
    #/////Bolinger Bands
    
    BBlength=20
    BBmult=2
    BBbasis= sma(price,BBlength) #Bolinger Bands SMA Basis line
    BBdev=BBmult*ta.std(price.values,BBlength)
    BBupper=BBbasis+BBdev # BB Upper line
    BBlower=BBbasis-BBdev # BB Lower Line
    
    return BBbasis,BBlower,BBupper



