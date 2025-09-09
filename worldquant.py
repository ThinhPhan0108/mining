import requests
import json
from requests.auth import HTTPBasicAuth
from typing import List, Dict
import pandas as pd
from time import sleep
import time
from urllib.parse import urljoin
import os
import pickle

class WorldQuant:
    def __init__(self,credentials_path='./credential.json'):
        print("Initializing AlphaPolisher...")
        self.sess = requests.Session()
        self.credentials_path=credentials_path
        self.url_biometrics=''
        self.cookies_path='./session.pkl'
        self.setup_auth(credentials_path)

        #self.operators = self.get_operators()
        #self.data_fields=self.get_datafields()
        print("AlphaPolisher initialized successfully")
    
    def setup_auth(self, credentials_path: str) -> None:
        """Set up authentication with WorldQuant Brain."""
        print(f"Loading credentials from {credentials_path}")
        try:
            if os.path.exists(self.cookies_path): #kiểm tra xem có file cookies chưa
                print("Found saved session cookies, loading...")
                with open(self.cookies_path, "rb") as f:
                    cookies = pickle.load(f)
                    self.sess.cookies.update(cookies) #load lại session
                response=self.sess.get("https://api.worldquantbrain.com/authentication")
                print("Kiểm tra kết nối session đã lưu",response.status_code )
                if response.status_code == 200: #kiểm tra kết nối có thành công chưa
                    self.url_biometrics="Authentication successful"
                    return #nếu thành công thì out ra khỏi hàm
            
            #nếu chưa thành công thì đăng nhập 
            with open(credentials_path) as f:
                credentials = json.load(f)
                
            username, password = credentials['username'],credentials['password']
            self.sess.auth = HTTPBasicAuth(username, password)
            
            print("Authenticating with WorldQuant Brain...")
            response = self.sess.post('https://api.worldquantbrain.com/authentication')
            print(f"Authentication response status: {response.status_code}")
            print(f"Authentication response: {response.text[:500]}...")
            
            self.url_biometrics=self.biometrics(response)
            if self.url_biometrics:
                return
            
            if response.status_code != 201:
                raise Exception(f"Authentication failed: {response.text}")
            print("Authentication successful")

        except Exception as e:
            print(f"Authentication failed: {str(e)}")
            raise
    
    def biometrics(self,response):
        if response.status_code == requests.status_codes.codes.unauthorized:
            if response.headers["WWW-Authenticate"] == "persona":
                url_biometrics=urljoin(response.url,response.headers['Location'])
                #response=self.sess.post(urljoin(response.url,response.headers['Location']))
                return url_biometrics
            else:
                print("incorrect")

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
                    'decay': 5,
                    'neutralization': 'INDUSTRY',
                    'truncation': 0.05,
                    'pasteurization': 'ON',
                    'unitHandling': 'VERIFY',
                    'nanHandling': 'ON',
                    'language': 'FASTEXPR',
                    'visualization': False,
                },
                'regular': alpha}

            sim_data_list.append(simulation_data)
        return sim_data_list

    def simulate(self, alpha_data: list, worksheet, decay=5, truncation=0.05, neut="INDUSTRY", region='USA', universe='TOP3000'):
        """
        Chạy mô phỏng và ghi kết quả vào Google Sheet ngay khi có.
        """
        print(f"Bắt đầu mô phỏng và ghi实时 {len(alpha_data)} alpha với giới hạn 3 luồng.")
        
        sim_data_list = self.generate_sim_data(alpha_data, decay, truncation, region, universe, neut)
        
        pending_urls = {} 
        data_iterator = iter(sim_data_list)
        results_count = 0 # Đếm số kết quả đã ghi

        while True:
            # 1. GỬI YÊU CẦU MỚI NẾU CÒN CHỖ TRỐNG
            while len(pending_urls) < 3:
                sim_data = next(data_iterator, None)
                if sim_data is None:
                    break 

                try:
                    alpha_code = sim_data['regular']
                    print(f"   -> Đang gửi yêu cầu cho: '{alpha_code}'")
                    response = self.sess.post('https://api.worldquantbrain.com/simulations', json=sim_data)
                    
                    if response.status_code == 201:
                        location_url = response.headers.get('Location')
                        if location_url:
                            pending_urls[location_url] = alpha_code
                    else:
                        print(f"   LỖI khi gửi '{alpha_code}': {response.status_code} - {response.text}")
                except Exception as e:
                    print(f"   LỖI KẾT NỐI: {str(e)}")

            if not pending_urls:
                break

            # 2. KIỂM TRA VÀ GHI KẾT QUẢ NGAY LẬP TỨC
            completed_urls = []
            for url, alpha_code in pending_urls.items():
                try:
                    progress_response = self.sess.get(url)
                    if progress_response.status_code == 200:
                        progress = progress_response.json()
                        status = progress.get("status")

                        if status in ['COMPLETE', 'WARNING']:
                            print(f"   -> XONG: Alpha '{alpha_code}' đã hoàn thành.")
                            alpha_id = progress.get("alpha")
                            result = self.locate_alpha(alpha_id, get_corr_and_score=True)
                            
                            # **LOGIC MỚI: GHI KẾT QUẢ VÀO SHEET NGAY LẬP TỨC**
                            if result and worksheet:
                                try:
                                    worksheet.append_row(result, value_input_option='USER_ENTERED')
                                    print(f"   -> ĐÃ GHI KẾT QUẢ CỦA '{alpha_code}' VÀO GOOGLE SHEET.")
                                    results_count += 1
                                except Exception as sheet_error:
                                    print(f"   LỖI: Không thể ghi vào Google Sheet: {sheet_error}")
                            
                            completed_urls.append(url)
                            break 
                        
                        elif status in ["FAILED", "ERROR", "FAIL"]:
                            print(f"   -> THẤT BẠI: Alpha '{alpha_code}' đã bị lỗi.")
                            completed_urls.append(url)
                            break
                except Exception as e:
                    print(f"   Lỗi khi kiểm tra trạng thái của '{alpha_code}': {e}")
                    completed_urls.append(url)
                    break
            
            # 3. DỌN DẸP
            if completed_urls:
                for url in completed_urls:
                    if url in pending_urls:
                        del pending_urls[url]
            else:
                sleep(5)

        print(f"\nĐã mô phỏng xong. Tổng cộng đã ghi {results_count} kết quả vào Google Sheet.")
        # Hàm này không cần trả về kết quả nữa vì đã ghi trực tiếp
        return results_count
    
    #hiệu quả alpha    
    def locate_alpha(self, alpha_id,get_corr_and_score=True):
        alpha = self.sess.get("https://api.worldquantbrain.com/alphas/" + alpha_id)
        
        string = alpha.content.decode('utf-8')
        metrics = json.loads(string)
        
        #các chỉ số thông thường
        expression=metrics['regular']['code']
        #dateCreated = metrics["dateCreated"]
        sharpe = metrics["is"]["sharpe"]
        turnover = metrics["is"]["turnover"]
        fitness = metrics["is"]["fitness"]
        returns=metrics["is"]["returns"]
        drawdown=metrics["is"]["drawdown"]
        margin = metrics["is"]["margin"]
        longCount=metrics["is"]["longCount"]
        shortCount=metrics["is"]["shortCount"]

        weight=str(metrics['is']['checks'][4]['result'])
        sub_univese=str(metrics['is']['checks'][5]['result'])

        settings=metrics['settings']
        universe=str(settings['universe'])
        delay=str(settings['delay'])
        decay=str(settings['decay'])
        neutralization=str(settings['neutralization'])
        truncation=str(settings['truncation'])

        code=metrics["id"]

        triple = [expression,sharpe, turnover,fitness,returns,drawdown,margin,longCount,shortCount,weight,sub_univese,universe,delay,decay,neutralization,truncation]
        if sharpe and abs(sharpe) >0.3 and get_corr_and_score: #điều kiện để lấy corr và score 
            #triple+=self.get_corr(alpha_id)
            triple+=self.get_score(alpha_id)
            
            triple+=[code]
            print(f'results simulate: {triple}')
        else:
            triple+=[None]
            triple+=[code]
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
            performance_respone=self.sess.get(f'https://api.worldquantbrain.com/competitions/IQC2025S3/alphas/{alpha_id}/before-and-after-performance')
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
    
if __name__=="__main__":
    WorldQuant()
