import sys
import os
# Lấy đường dẫn thư mục cha
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# Thêm vào sys.path nếu chưa có
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from worldquant import WorldQuant
import json
import gspread
from itertools import product,combinations
import ast
import datetime

class ComBine:
    def __init__(self):
        self.date=datetime.datetime.now().strftime('%d-%m-%Y')
        #kết nối với gg sheet
        gc=gspread.service_account('./apisheet.json')
        self.wks_combine=gc.open('Auto Alpha').worksheet('combine')
        self.wks_main_combine=gc.open('Auto Alpha').worksheet('main_combine')

        self.main_database=pd.DataFrame(self.wks_main_combine.get_all_records())
        self.main_database=self.main_database[1:]
        self.wl=WorldQuant()
    
    
    def get_code(self,alpha: str,setting: str):
        id=f'{alpha}_{setting}'
        if id in list(self.main_database['id']):
            print('alpha có trong database')
            condition=self.main_database['id']==id
            code=str(self.main_database[condition]['code'].values[0])
            return code
        
        else:
            print('apha không có trong database')
            result_simulate=self.wl.single_simulate(alpha)
            
            #lấy code và trích suất dữ liệu pl, turnover
            print('get P&L') 
            code=result_simulate[-1]
            pl=self.wl.get_pl(code)
            turnover=self.wl.get_turnover(code)
            data=pl.merge(turnover,how='inner',on=['date'])
            
            #lưu dữ liệu
            print('save data')
            data.to_csv(f'./combine/details/{code}.csv',index=False)
            self.wks_main_combine.append_rows([[self.date,id,alpha,setting,code]])
            return code

    def commbine_sharpe(self,df_pl):
        # Thông số
        mean_returns = np.mean(df_pl, axis=0)
        cov_matrix = np.cov(df_pl.T)
        risk_free_rate = 0.0

        def sharpe_ratio(w, mean_returns, cov_matrix, rf):
            port_return = np.dot(w, mean_returns)
            port_vol = np.sqrt(np.dot(w.T, np.dot(cov_matrix, w)))
            return - (port_return - rf) / port_vol *np.sqrt(252)  # dấu âm vì minimize

        # Ràng buộc tổng trọng số bằng 1
        constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}

        # Ràng buộc không âm và không vượt quá 1
        bounds = [(0, 1) for _ in range(len(mean_returns))]

        # Khởi tạo trọng số đều
        init_weights = [1. / len(mean_returns)] * len(mean_returns)

        # Tối ưu hóa
        result = minimize(sharpe_ratio, init_weights,
                        args=(mean_returns, cov_matrix, risk_free_rate),
                        method='SLSQP', bounds=bounds, constraints=constraints)

        optimal_weights = result.x
        optimal_sharpe = -result.fun

        optimal_weights=[round(weight,2) for weight in optimal_weights]
        optimal_sharpe=round(optimal_sharpe,2)
        return optimal_weights,optimal_sharpe
    
    '''def run_v1(self):
        for index in range(len(self.main_database),len(self.df_alpha_history)):
            alpha=self.df_alpha_history.loc[index,'Alpha']
            settings=self.df_alpha_history.loc[index,'settings']
            self.get_code(alpha,settings)'''

    def expression_combine(self,codes,weights):
        #lấy danh sách alpha và settings từ code
        alphas=[]
        settings=[]
        for code in codes:
            alphas += self.main_database.loc[self.main_database['code']==code,'alpha'].tolist()
            settings += self.main_database.loc[self.main_database['code']==code,'settings'].tolist()
        #chuyển chữ hoa trong settings thành thường
        #settings=[setting.lower() for setting in settings]

        alpha_combine=''
        #tiền xử lý công thức
        for index in range(len(alphas)):
            #lấy neutralization trong settings
            neutralization=ast.literal_eval(settings[index])  # Chuyển string thành dict
            neutralization=neutralization.get('neutralization')
            
            #tiến hành xử lý alpha
            #alpha=f'pre_alpha_{index} = group_neutralize({alphas[index]},{neutralization}); alpha_{index} = if_else(is_nan(pre_alpha_{index}),0,pre_alpha_{index}); '
            alpha = f'pre_alpha_{index} = group_neutralize({alphas[index]},{neutralization}); ' 
            alpha += f'mean_pre_alpha_{index} = group_mean(abs(pre_alpha_{index}),1,{neutralization}); '
            alpha += f'alpha_ratio_{index} = pre_alpha_{index}/ mean_pre_alpha_{index}; ' 
            alpha += f'alpha_{index} = if_else(is_nan(alpha_ratio_{index}),0,alpha_ratio_{index}); '

            alpha_combine +=alpha

        #điền trọng số
        for index in range(len(weights)):
            alpha=f'{weights[index]}*alpha_{index} + '
            alpha_combine += alpha

        #loại bỏ dấu cộng cuối cùng
        alpha_combine=alpha_combine[:-2]
        return alpha_combine
    
    def run_v2(self):
        codes=list(self.main_database['code'])
        map_codes=list(combinations(codes,2))
        
        #chạy tổ hợp code
        for code_1,code_2 in map_codes:
            try:
                pl_code1=pd.read_csv(f'./combine/details/{code_1}.csv')
                pl_code1=pl_code1[['date','returns']].iloc[:973] #chỉ lấy phần train

                pl_code2=pd.read_csv(f'./combine/details/{code_2}.csv')
                pl_code2=pl_code2[['date','returns']].iloc[:973] #chỉ lấy phần train

                pl=pl_code1.merge(pl_code2,how='inner',on=['date'])
                pl.drop(columns=['date'],inplace=True)
                
                #tiến hành tối ưu sharpe
                weights,sharpe_max=self.commbine_sharpe(pl)
                #tạo công thức combine
                alpha=self.expression_combine([code_1,code_2],weights)
                #simulate
                result_simulate=self.wl.single_simulate(alpha,neut="NONE")
                #xuất kết quả
                alpha_1=self.main_database[self.main_database['code']==code_1]['alpha'].values[0]
                alpha_2=self.main_database[self.main_database['code']==code_2]['alpha'].values[0]
                results=[self.date,alpha_1,alpha_2,str(weights),alpha,sharpe_max]+result_simulate
                print(results)
                self.wks_combine.append_rows([results])
            except Exception as e:
                self.wl=WorldQuant()
                print('ERROR ', e)
                continue

    def run(self,alpha,setting):
        code=self.get_code(alpha,setting) #lấy mã code
        codes=list(self.main_database['code']) #danh sách các alpha dùng để combine với code
        maps=product([code],codes)
        #chạy tổ hợp code
        for code_1,code_2 in maps:
            try:
                pl_code_1=pd.read_csv(f'./combine/details/{code_1}.csv')
                pl_code_1=pl_code_1[['date','returns']].iloc[:973] #chỉ lấy phần train

                pl_code_2=pd.read_csv(f'./combine/details/{code_2}.csv')
                pl_code_2=pl_code_2[['date','returns']].iloc[:973] #chỉ lấy phần train

                pl=pl_code_1.merge(pl_code_2,how='inner',on=['date'])
                pl.drop(columns=['date'],inplace=True)
                
                #tiến hành tối ưu sharpe
                weights,sharpe_max=self.commbine_sharpe(pl)
                #tạo công thức combine
                alpha_combine=self.expression_combine([code_1,code_2],weights)

                #simulate
                result_simulate=self.wl.single_simulate(alpha_combine,truncation=0.1 ,neut="MARKET")

                #xuất kết quả
                alpha_2=self.main_database[self.main_database['code']==code_2]['alpha'].values[0]
                results=[self.date,alpha,alpha_2,str(weights),alpha_combine,sharpe_max]+result_simulate
                self.wks_combine.append_rows([results])
                print(results)
                
            except Exception as e:
                self.wl=WorldQuant()
                print('ERROR ', e)
                continue


if __name__=='__main__':
    ComBine().run_v2()
    #a=ComBine().expression_combine(['0NRgx52','vpk6qza'],[0.5,0.5])
    #print(a)