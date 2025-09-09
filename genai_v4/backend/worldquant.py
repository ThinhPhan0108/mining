import requests
import json
from requests.auth import HTTPBasicAuth
from typing import List, Dict
import pandas as pd
from time import sleep
import time

class WorldQuant:
    def __init__(self,credentials_path='./credential.json'):
        print("Initializing AlphaPolisher...")
        self.sess = requests.Session()
        self.credentials_path=credentials_path
        self.setup_auth(credentials_path)
        #self.operators = self.get_operators()
        #self.data_fields=self.get_datafields()
        #self.inaccessible_ops = ["log_diff", "s_log_1p", "fraction", "quantile"]
        print("AlphaPolisher initialized successfully")
    
    def setup_auth(self, credentials_path: str) -> None:
        """Set up authentication with WorldQuant Brain."""
        print(f"Loading credentials from {credentials_path}")
        try:
            with open(credentials_path) as f:
                credentials = json.load(f)
            
            username, password = credentials['username'],credentials['password']
            self.sess.auth = HTTPBasicAuth(username, password)
            
            print("Authenticating with WorldQuant Brain...")
            response = self.sess.post('https://api.worldquantbrain.com/authentication')
            print(f"Authentication response status: {response.status_code}")
            print(f"Authentication response: {response.text[:500]}...")
            
            if response.status_code != 201:
                raise Exception(f"Authentication failed: {response.text}")
            print("Authentication successful")
        except Exception as e:
            print(f"Authentication failed: {str(e)}")
            raise

    def get_operators(self) -> Dict:
        """Fetch available operators from WorldQuant Brain API."""
        print("Fetching available operators...")
        try:
            response = self.sess.get('https://api.worldquantbrain.com/operators')
            print(f"Operators response status: {response.status_code}")
            
            if response.status_code == 200:
                operators = response.json()
                print(f"Successfully fetched {len(operators)} operators")
                print(f"Operators: {json.dumps(operators, indent=2)}")
                return pd.DataFrame(operators)
            else:
                print(f"Failed to fetch operators: {response.text}")
                return {}
        except Exception as e:
            print(f"Error fetching operators: {str(e)}")
            return {}
        
    def get_datafields(self,
        instrument_type: str = 'EQUITY',
        region: str = 'USA',
        delay: int = 1,
        universe: str = 'TOP3000',
        dataset_id: str = '',
        search: str = ''
    ):
        if len(search) == 0:
            url_template = "https://api.worldquantbrain.com/data-fields?" +\
                f"&instrumentType={instrument_type}" +\
                f"&region={region}&delay={str(delay)}&universe={universe}&dataset.id={dataset_id}&limit=50" +\
                "&offset={x}"
            count = self.sess.get(url_template.format(x=0)).json()['count'] 
            
        else:
            url_template = "https://api.worldquantbrain.com/data-fields?" +\
                f"&instrumentType={instrument_type}" +\
                f"&region={region}&delay={str(delay)}&universe={universe}&limit=50" +\
                f"&search={search}" +\
                "&offset={x}"
            count = 100
        
        datafields_list = []
        for x in range(0, count, 50):
            datafields = self.sess.get(url_template.format(x=x))
            datafields_list.append(datafields.json()['results'])
     
        datafields_list_flat = [item for sublist in datafields_list for item in sublist]
     
        datafields_df = pd.DataFrame(datafields_list_flat)
        return datafields_df
    
    def get_vec_fields(self, fields):

        #vec_ops = ["vec_avg", "vec_sum", "vec_ir", "vec_max", "vec_count","vec_skewness","vec_stddev", "vec_choose"]
        vec_ops=["vec_avg", "vec_sum"]
        vec_fields = []
     
        for field in fields:
            for vec_op in vec_ops:
                if vec_op == "vec_choose":
                    vec_fields.append("%s(%s, nth=-1)"%(vec_op, field))
                    vec_fields.append("%s(%s, nth=0)"%(vec_op, field))
                else:
                    vec_fields.append("%s(%s)"%(vec_op, field))
     
        return(vec_fields)
    
    def process_datafields(self, df, data_type):

        if data_type == "matrix":
            datafields = df[df['type'] == "MATRIX"]["id"].tolist()
        elif data_type == "vector":
            datafields = self.get_vec_fields(df[df['type'] == "VECTOR"]["id"].tolist())

        tb_fields = []
        for field in datafields:
            #tb_fields.append("winsorize(ts_backfill(%s, 120), std=4)"%field)
            tb_fields.append(field)
        return tb_fields
    
    def process_datafields_v2(self, df):
        mask_matrix = df['type'] == 'MATRIX'
        mask_vector = df['type'] == 'VECTOR'

        df.loc[mask_matrix, 'id'] = df.loc[mask_matrix, 'id'].apply(
            #lambda var: f"winsorize(ts_backfill({var}, 120), std=4)"
            lambda var: var
        )
        df.loc[mask_vector, 'id'] = df.loc[mask_vector, 'id'].apply(
            #lambda var: f"winsorize(ts_backfill(vec_avg({var}), 120), std=4)"
            lambda var: f"vec_avg({var})"
        )
        return df
    def generate_sim_data(self, alpha_list,decay,truncation, region, uni, neut):
        sim_data_list = []
        for alpha in alpha_list:
            simulation_data = {
                'type': 'REGULAR',
                'settings': {
                    'instrumentType': 'EQUITY',
                    'region': region,
                    'universe': uni,
                    'delay': 1,
                    'decay': decay,
                    'neutralization': neut,
                    'truncation': truncation,
                    'pasteurization': 'ON',
                    'unitHandling': 'VERIFY',
                    'nanHandling': 'OFF',
                    'language': 'FASTEXPR',
                    'visualization': False,
                },
                'regular': alpha}

            sim_data_list.append(simulation_data)
        return sim_data_list
    
    def flow_simulate(self,simulation_progress_url_list,results,number_flow):
        if len(simulation_progress_url_list)==number_flow:
            i=0
            while True:
                #lấy kết quả từ url và chuyển kết quả thành json
                simulation_progress=self.sess.get(simulation_progress_url_list[i])
                result=simulation_progress.json()
                #nếu kết quả ở trạng thái hoàn thành thì lưu kết quả và xóa url ra khỏi list, nếu không kiểm tra url tiếp theo trong list
                if result.get("status")=='COMPLETE':
                    results.append(result)
                    simulation_progress_url_list.pop(i)
                    print(f"Simulation complete: {result['regular']}")
                    break
                else:
                    i = (i + 1) % number_flow
                
                sleep(5)
            
            return simulation_progress_url_list,results
        else:
            return simulation_progress_url_list,results
    
    #simulate alpha
    def simulate(self, alpha_data: list,decay: int, truncation : float ,neut: str, region: str, universe: str) -> dict:
        """
        Run a single alpha simulation.
        
        """
        print(f"Starting single simulation for alpha")
        
        sim_data_list = self.generate_sim_data(alpha_data, decay,truncation ,region, universe, neut)
        results = []
        simulation_progress_url_list=[]
        for sim_data in sim_data_list:
            try:
                #gửi alpha lên worlquant để tiến hành simulation
                simulation_response = self.sess.post('https://api.worldquantbrain.com/simulations', 
                                                     json=sim_data)
                if simulation_response.status_code == 401:
                    print("Session expired, re-authenticating...")
                    self.setup_auth(self.credentials_path)
                    simulation_response = self.sess.post('https://api.worldquantbrain.com/simulations', 
                                                        json=sim_data)
                
                if simulation_response.status_code != 201:
                    print(f"Simulation API error: {simulation_response.text}")
                    continue
                #Lấy url chứa kết quả
                simulation_progress_url=simulation_response.headers.get('Location')
                if simulation_progress_url:
                    simulation_progress_url_list.append(simulation_progress_url)
                    simulation_progress_url_list,results=self.flow_simulate(simulation_progress_url_list,results,3)

                else :
                    print("No Location header in response")
                    continue
                
            except Exception as e:
                print(f"Error in simulation: {str(e)}")
                sleep(60)  # Short sleep on error
                self.setup_auth(self.credentials_path)
                continue
        #xử lý kết quả cuối cùng
        simulation_progress_url_list,results=self.flow_simulate(simulation_progress_url_list,results,2)
        simulation_progress_url_list,results=self.flow_simulate(simulation_progress_url_list,results,1)
        return results
    
    #simulate alpha
    def single_simulate(self, single_alpha: str,decay=0,truncation=0 ,neut="MARKET",region='USA',universe='TOP3000',get_corr_and_score=True) -> list:
        """
        Run a single alpha simulation.
        """
        print(f"Starting single simulation for alpha")
        
        sim_data_list = self.generate_sim_data([single_alpha], decay,truncation ,region, universe, neut)
        sim_data=sim_data_list[0]
        try:
            #gửi alpha lên worlquant để tiến hành simulation
            simulation_response = self.sess.post('https://api.worldquantbrain.com/simulations', 
                                                    json=sim_data)
            if simulation_response.status_code == 401:
                print("Session expired, re-authenticating...")
                self.setup_auth(self.credentials_path)
                simulation_response = self.sess.post('https://api.worldquantbrain.com/simulations', 
                                                    json=sim_data)
            
            if simulation_response.status_code != 201:
                print(f"Simulation API error: {simulation_response.text}")
                
            #Lấy url chứa kết quả
            simulation_progress_url=simulation_response.headers.get('Location')
            if simulation_progress_url: #kiểm tra đường dẫn có tồn tại hay không
                print(simulation_progress_url)

                while True: 
                    simulation_progress=self.sess.get(simulation_progress_url)
                    if simulation_progress.content: #kiểm tra kết quả có tồn tại hay không
                        simulation_progress=simulation_progress.json()
                    
                        if simulation_progress.get("detail")=="Incorrect authentication credentials.":
                            print('Incorrect authentication credentials.')
                            self.setup_auth(self.credentials_path)
                            result=self.single_simulate(single_alpha,decay ,neut, region, universe)
                            return result
                        
                        elif simulation_progress.get("status") in ['COMPLETE','WARNING']:
                            alpha_id=simulation_progress.get("alpha")
                            result=self.locate_alpha(alpha_id,get_corr_and_score)
                            return result
                        
                        elif simulation_progress.get("status") in ["FAILED", "ERROR","FAIL"]:
                            print(f'ERROR ALPHA {single_alpha}')
                            return [None]
                    sleep(10)
            else :
                print("No Location header in response")
                print("reconnecting")
                self.setup_auth(self.credentials_path)
                result=self.single_simulate(single_alpha,decay ,neut, region, universe)

        except Exception as e:
            print(f"Error in simulation: {str(e)}")
            sleep(60)  # Short sleep on error
            self.setup_auth(self.credentials_path)
            result=self.single_simulate(single_alpha,decay ,neut, region, universe)
            return result
    
    #hiệu quả alpha    
    def locate_alpha(self, alpha_id,get_corr_and_score=True):
        alpha = self.sess.get("https://api.worldquantbrain.com/alphas/" + alpha_id)
        
        string = alpha.content.decode('utf-8')
        metrics = json.loads(string)
        
        #các chỉ số thông thường
        #dateCreated = metrics["dateCreated"]
        sharpe = metrics["is"]["sharpe"]
        turnover = metrics["is"]["turnover"]
        fitness = metrics["is"]["fitness"]
        returns=metrics["is"]["returns"]
        drawdown=metrics["is"]["drawdown"]
        margin = metrics["is"]["margin"]
        settings=str(metrics['settings'])
        weight=str(metrics['is']['checks'][4])
        sub_univese=str(metrics['is']['checks'][5])
        code=metrics["id"]

        triple = [sharpe, turnover,fitness,returns,drawdown,margin,weight,sub_univese,settings]
        if sharpe and abs(sharpe) >0.3 and get_corr_and_score: #điều kiện để lấy corr và score 
            triple+=self.get_corr(alpha_id)
            triple+=self.get_score(alpha_id)
            triple+=[code]
            print(f'results simulate: {triple}')
        else:
            triple+=[None,None,None,code]
        triple = [ i if i != 'None' else None for i in triple]
        return triple

    def get_corr(self,alpha_id):
        start_time = time.time()
        timeout = 30  # giới hạn thời gian vòng lặp while

        #lấy corr
        while True:
            corr_respond=self.sess.get(f"https://api.worldquantbrain.com/alphas/{alpha_id}/correlations/self")
            corr=corr_respond.content.decode('utf-8')
            if corr: # kiểm tra corr có tồn tại không
                corr=json.loads(corr) #chuyển corr dạng str --> json

                if corr.get('min'): # kiểm tra min có tồn tại không
                    min_corr=corr['min']
                    max_corr=corr['max']
                    return [min_corr,max_corr]
                
            if time.time() - start_time > timeout:
                return [None,None]  # thoát nếu đã vượt quá 30 giây
            
            sleep(5)

    def get_score(self,alpha_id):
        start_time = time.time()
        timeout = 30  # giới hạn thời gian vòng lặp while
        # lấy score
        while True:
            performance_respone=self.sess.get(f'https://api.worldquantbrain.com/competitions/IQC2025S2/alphas/{alpha_id}/before-and-after-performance')
            performance = performance_respone.content.decode('utf-8')
            if performance: #kiểm tra performance có tồn tại không
                performance = json.loads(performance) #chuyển về dạng json

                if performance.get('score'): #kiểm tra score có tồn tại không
                    before_score=performance['score']['before']
                    after_score=performance['score']['after']
                    score=after_score-before_score
                    return [score]
            
            if time.time() - start_time > timeout:
                return [None]  # thoát nếu đã vượt quá 30 giây
            
            sleep(5)
        
    def get_pl(self,alpha_id):
        while True:
            pl_obj=self.sess.get(f'https://api.worldquantbrain.com/alphas/{alpha_id}/recordsets/pnl')
            if pl_obj.content:
                pl=pl_obj.json()
                pl=pl.get('records')
                pl=pd.DataFrame(pl,columns=['date','returns'])
                pl['returns']=pl['returns']-pl['returns'].shift(1)
                pl.dropna(inplace=True)
                return pl
            
    def get_turnover(self,alpha_id):
        while True:
            turnover_obj=self.sess.get(f'https://api.worldquantbrain.com/alphas/{alpha_id}/recordsets/turnover')
            if turnover_obj.content:
                turnover=turnover_obj.json()
                turnover=turnover.get('records')
                turnover=pd.DataFrame(turnover,columns=['date','turnover'])
                turnover.dropna(inplace=True)
                return turnover
    
