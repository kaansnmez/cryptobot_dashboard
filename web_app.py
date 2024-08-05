import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import warnings
import requests
import time

#os.system('python main_3_streamlit.py')
#process = subprocess.Popen(["python", "main_3_streamlit.py"],shell=True,stdin=None,stdout=PIPE, stderr=PIPE)
#stdout, stderr = process.communicate()
#subprocess.call(['python', 'main_3_streamlit.py'])
#subprocess.run(["python","main_3_streamlit.py"])
#new_thread=threading.Thread(target=main_3_streamlit.main)


def get_data():
    data_dict={'RealTime':{'pairdata':{}
                          },
             'Historical':{'wt_history':{},
                         'kline_history':{},
                         'posdata':{},
                         'assets':{}}}
    for url in data_dict.keys():
        for key in data_dict[url].keys():
            
            headers = {
                      "Content-Type": "application/json"
                      }
            data=requests.get("http://0.0.0.0:5000/api/{}".format(key)).json()
            data_dict[url][key]=data
    return data_dict
def json_to_df(json_dict):
    for key in json_dict.keys():
        for sub_keys in key.keys():
            json_dict[key][sub_keys]=pd.DataFrame.from_dict(json_dict[key][sub_keys])
    return json_dict
def convert_json_decode_format(df):
    columns=['entry','close','close_real_data','qty','margin_size','profit','leverage']
    for x in columns: 
        try:
            df[x]=df[x].apply(lambda x : float(str(x).replace(',','.')))
        except:
            pass
    return df

@st.fragment(run_every="15 sec")
def candle_stick():
    contanier=st.columns((2,2))
    while True:
        try:
            kline_history=json_to_df(get_data())['Historical']['kline_history'].iloc[-99:,:]
            wt_history=json_to_df(get_data())['Historical']['wt_history'].iloc[-99:,:]
            break
        except:
            print("candle_stick is not ready")
            time.sleep(5)
    with contanier[0]:
        fig3 = go.Figure(data=[go.Candlestick(x=kline_history['close_time'],
                    open=kline_history['open'],
                    high=kline_history['high'],
                    low=kline_history['low'],
                    close=kline_history['close'])],layout={'dragmode': 'pan' })
        fig3.update_yaxes(fixedrange=False)
        fig3.update_layout(
            hoverlabel = dict(
                bgcolor = 'rgba(39,46,72,1)' #whatever format you want
                            ),
            title=dict(text="BTC / USDT 1d Interval CandleStick Chart"),
            legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="left",
                        
                        
                    ))
        st.plotly_chart(fig3,config={'scrollZoom':True,
                                    'modeBarButtonsToRemove':['zoom']})
    with contanier[1]:
        fig4=go.Figure(layout={'dragmode': 'pan' })
        fig4.add_trace(go.Scatter(x=kline_history['close_time'],
                                  y=wt_history['wt_1'],
                                  mode='lines+markers',
                                  name='wt_1')
                                  
                                  )
        fig4.add_trace(go.Scatter(x=kline_history['close_time'],
                                  y=wt_history['wt_2'],
                                  mode='lines+markers',
                                  name='wt_2')
                                  )
        fig4['data'][0]['line']['color']="green"
        fig4['data'][1]['line']['color']="red"
        fig4.update_yaxes(fixedrange=False)
        fig4.update_layout(
            hoverlabel = dict(
                bgcolor = 'rgba(39,46,72,1)' 
                            ),
            title=dict(text="WaveTrend Chart"),
            legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.05,
                        xanchor="left",
                        bgcolor='rgba(39,46,72,0)'
                        
                    ))
        st.plotly_chart(fig4,config={'scrollZoom':True,
                                    'modeBarButtonsToRemove':['zoom']})


    
    
@st.fragment(run_every="10 sec")
def stream():
    contanier=st.columns((1,1,1.5,1))
    
    time.sleep(1)
    while True:
        try:
            data=get_data()['RealTime']['pairdata']
            print(data)
            assets=get_data()['Historical']['assets']
            print(assets)
            break
        except:
            print("stream is not ready")
            time.sleep(5)    
            
    data={k: 0 if v==None else v for k, v in data.items()}
    with contanier[0]:
        contanier[0].metric(
            label="Open Price",
            value=f"$ {data['open']} "
            
        )
        contanier[0].markdown("****")
        contanier[0].metric(
            label="Close Price",
            value=f"$ {data['close']} "
            
        )
        
    with contanier[1]:

        contanier[1].metric(
            label="High Price",
            value=f"$ {data['high']} "
            
        )
        contanier[1].markdown("***")
        contanier[1].metric(
            label="Low Price",
            value=f"$ {data['low']} "
            
        )
        
    with contanier[2]:
        fig2=go.Figure(data=[go.Pie(labels=assets['asset_name'], 
                              values=assets['balance_r'],
                              marker_colors=['rgb(1, 184, 170)','rgb(237, 111, 19)'],
                              hoverlabel = dict(namelength = -1))])
      
        fig2.update_traces(hoverinfo="label+value")
        fig2.update_layout(
            hoverlabel = dict(
                bgcolor = 'rgba(39,46,72,1)' #whatever format you want
                            ),
            title=dict(text="Account Balance Chart"),
            legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.05,
                        xanchor="left",
                        bgcolor='rgba(39,46,72,0)'
                
                    ))
        st.plotly_chart(fig2)
        
    with contanier[3]:

        contanier[3].metric(
            label="Profit",
            value=f"$ {round(data['profit'],3)} "
            
        )
        contanier[3].markdown("***")
        contanier[3].metric(
            label="Volume BTC",
            value=f"{data['volume']} "
            
        )
    
      
@st.fragment(run_every="1m")        
def historical_table():
    cont=st.columns((1,1,1,1))
    cont_2=st.columns((1,1,1))
    
    while True:
        try:
            posdata=json_to_df(get_data())['Historical']['posdata']    
            break
        except:
            print("historical_table is not ready")
            time.sleep(5)
    
    column_order=['time','symbol','side','entry','leverage','qty','margin_size','close','close_real_data','profit']
    posdata=posdata[column_order].sort_values('time',ascending=False).reset_index(drop=True)
    posdata=convert_json_decode_format(posdata)
    def highlight(s):
        if  np.isnan(s.profit):
            return ['background-color: rgb(247, 202, 24)']*len(s)
        elif s.profit < 0:
            return ['background-color: rgb(207, 0, 15)']*len(s)
        else :
            #(0, 177, 106);(0, 230, 64)
            return ['background-color: rgb(0, 230, 64)']*len(s)
    with cont[0]:
        cont[0].metric(
            label="Sum Of Profit",
            value=f"$ {round(posdata['profit'].sum(),3)} " )
    with cont[1]:
        cont[1].metric(
            label="Mean of Margin Size",
            value=f"$ {round(posdata['margin_size'].mean(),3)} ")
    with cont[2]:
        succes_rate=round((len([x for x in posdata['profit'] if x>0])/posdata.shape[0])*100,3)
        cont[2].metric(
            label="Succes Rate",
            value=f"% {round(succes_rate,3)} ")
    with cont[3]:
        mean_success=sum([x for x in posdata['profit'] if x>0])/len([x for x in posdata['profit'] if x>0])
        cont[3].metric(
            label="Average Succesfull Trading Gain",
            value=f"$ {round(mean_success,3)} ")
    with cont_2[0]:
        success=[x for x in posdata['profit'] if (x>0)]
        cont_2[0].metric(
            label="Maximum Profit",
            value=f"$ {round(max(success),3)}")
    with cont_2[1]:
        unsuccess=[x for x in posdata['profit'] if (x<0)]
        cont_2[1].metric(
            label="Max Lose",
            value=f" ${round(min(unsuccess),3)} ")
    with cont_2[2]:
        mean_unsuccess=sum([x for x in posdata['profit'] if x<0])/len([x for x in posdata['profit'] if x>0])
        cont_2[2].metric(
            label="Average Failed Trade loss",
            value=f"$ {round(mean_unsuccess,3)} ")
    table=st.columns(1)
    with table[0]:
        table[0].dataframe(posdata.style.apply(highlight,axis=1),use_container_width=True)
        
def web_app():
    warnings.filterwarnings('ignore')
    st.set_page_config(page_title="Dashboard", page_icon=":bar_chart:",layout="wide")
    st.title(":bar_chart: BTC 1d CryptoBot Dashboard :currency_exchange:")
    stream()
    with open("web_css.css")as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html = True)
    st.header("BTC Chart - Strategy :chart:", divider='orange')
    candle_stick()
    st.header("Trade History :money_with_wings:", divider='orange')
    historical_table()
    
if __name__=='__main__':
    web_app()
