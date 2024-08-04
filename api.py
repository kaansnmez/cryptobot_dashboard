from flask import Flask,jsonify
from flask import make_response
from flask import request
import os,signal,logging,json
import threading
import pandas as pd

class flsk():
    def __init__(self):
        self.api=0
        self.time=0
        self.kline_df=0
        self.kline_history=0
        self.wt1_signal=0
        self.wt2_signal=0
        self.pos_df=0
        self.profit=0
        self.assets=0
    def thread_function(self):
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        @self.api.route('/stopServer', methods=['POST'])
        def stopServer():
            func = request.environ.get('werkzeug.server.shutdown')
            if func is None:
                raise RuntimeError('Not running with the Werkzeug Server')
            func()
        @self.api.route('/api/assets',methods=['GET'])
        def assets():
            asset_name=['Balance_USDT','Margin_USDT']
            balance_r=[float(self.assets['balance']),float(self.assets['balance'])-float(self.assets['crossWalletBalance'])]
            self.assets_df=self.assets.append([self.assets.copy()],ignore_index=True)
            self.assets_df['asset_name']=asset_name
            self.assets_df['balance_r']=balance_r
            json_list = json.loads(json.dumps(list(self.assets_df.T.to_dict().values())))
            return json_list
            
        @self.api.route('/api/kline_history',methods=['GET'])
        def kline_history_data():
            
            kline_index=pd.DataFrame([i for i in range(len(self.kline_history))],columns=['index'])
            indexed_kline=pd.concat([kline_index,self.kline_history])
            json_list = json.loads(json.dumps(list(self.kline_history.T.to_dict().values())))
            return json_list
        @self.api.route('/api/wt_history',methods=['GET'])
        def wt_history_data():
            
            wt_index=pd.DataFrame([i for i in range(len(self.wt1_signal))])
            cross=self.wt1_signal-self.wt2_signal
            wt_cross=pd.DataFrame(cross)
            wt_sig=pd.concat([wt_index,self.wt1_signal,self.wt2_signal,wt_cross],axis=1)
            wt_sig.columns=['index','wt_1','wt_2','wt_cross']
            json_list = json.loads(json.dumps(list(wt_sig.T.to_dict().values())))
            return json_list
        @self.api.route('/api/pairdata', methods=['GET'])
        def get_pair_data():
            profit=pd.DataFrame([self.profit],columns=['profit'])
            klines_df=pd.concat([self.kline_df,profit],axis=1)
            
            pair_data={key:value.values[0] if klines_df[key].dtypes!='<M8[ns]' else str(value.values[0]) for key,value in klines_df.items()}
            return jsonify(pair_data)
        
        @self.api.route('/api/wtsignal', methods=['GET'])
        def wt_signal_data():
            
            cross=self.wt1_signal.values[-1]-self.wt2_signal.values[-1]
            data={'time':str(self.time.values[-1]),'wt_1':self.wt1_signal.values[-1],'wt_2':self.wt2_signal.values[-1],'wt_cross':cross}
            return jsonify(data)
        
        @self.api.route('/api/posdata', methods=['GET'])
        def pos_data():
        
            data=self.pos_df.to_dict(orient='records')
            return jsonify(data)
            
            
            
        
    def run(self):
        self.api = Flask("__main__")
        self.api.logger.disabled=False
        self.thread_function()
        self.api.run()
            
