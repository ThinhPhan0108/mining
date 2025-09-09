'''
Quy trình bắt đầu từ file document --> tạo Group_Hypothesis --> Tạo Sub Hypothesis --> Tạo biểu thức alpha --> simulate --> update sheet
'''
import sys
import os
# Lấy đường dẫn thư mục cha
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# Thêm vào sys.path nếu chưa có
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from google import genai
from google.genai import types
from pydantic import BaseModel
import pathlib
import json
import pandas as pd
import datetime
import gspread
from time import sleep
from worldquant import WorldQuant
#from optimize.optimize_v2 import Optimize 
import csv
from combine.combine_v2 import ComBine
import random

class genai_group_format(BaseModel):
    Group_Hypothesis: str
    Definition: str
    Examples: str

class genai_sub_format(BaseModel):
    Group_Hypothesis: str
    Sub_Hypothesis: str
    Description: str
    Expression: str
    Limitation: str

class genai_alpha_format(BaseModel):
    Group_Hypothesis: str
    Sub_Hypothesis: str
    Description: str
    Expression: str
    Limitation: str
    Expression_alpha: str

class genai_similar_alpha_format(BaseModel):
    Group_Hypothesis: str
    Sub_Hypothesis_new: str
    Description_new: str
    Expression_new: str
    Limitation: str
    Expression_alpha_new: str

class GenAI:
    def __init__(self,group_index_key=0,sub_index_key=0,alpha_index_key=0,similar_alpha_index_key=0):
        self.date=datetime.datetime.now().strftime('%d-%m-%Y')
        self.process_name='version_1.4'
        
        data_key=self.read_json('./keyapi.json')
        self.list_key=data_key['list_key']

        self.group_client=genai.Client(api_key=self.list_key[group_index_key])
        self.sub_client=genai.Client(api_key=self.list_key[sub_index_key])
        self.alpha_client=genai.Client(api_key=self.list_key[alpha_index_key])
        self.similar_alpha_client=genai.Client(api_key=self.list_key[similar_alpha_index_key])

        self.model_name="gemini-1.5-flash"

        self.group_prompt=open("./genai_v1_1/prompt/group_hypothesis_prompt.txt", "r", encoding="utf-8").read()

        self.sub_prompt=open("./genai_v1_1/prompt/sub_hypothesis_prompt.txt", "r", encoding="utf-8").read()
        #self.sub_system=open("./genai_v1_1/prompt/sub_hypothesis_system.txt", "r", encoding="utf-8").read()
        
        self.alpha_prompt=open("./genai_v1_1/prompt/alpha_prompt.txt", "r", encoding="utf-8").read()
        self.alpha_system=open("./genai_v1_1/prompt/alpha_system.txt", "r", encoding="utf-8").read()

        self.similar_alpha_prompt=open("./genai_v1_1/prompt/similar_alpha_prompt.txt", "r", encoding="utf-8").read()

        #truy cập gg sheet
        gc = gspread.service_account(filename='./apisheet.json')
        wks = gc.open("Auto Alpha").worksheet("auto_alpha_v2")
        self.wks=wks

        group_wks = gc.open("Auto Alpha").worksheet("group_hypothesis")
        self.group_wks=group_wks

        '''
        #dữ liệu lịch sử phản hồi
        response_history=wks.get_all_records()
        #chỉ lấy một số cột nhất định
        desired_columns = ['Group Hypothesis','Expression']
        response_history = [{col: row[col] for col in desired_columns if col in row} for row in response_history]

        self.response_history=pd.DataFrame(response_history)
        '''
        #hàm optimize 
        #self.optimize=Optimize()

    # Đọc file JSON
    def read_json(self,file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)  # Tải dữ liệu JSON
        return data
    
    def append_rows(self,result_simulate):
        try:
            self.wks.append_rows(result_simulate)
        except Exception as e:
            with open('./results.csv', mode='a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerows(result_simulate)
            print(f'ERROR GG SHEET {e}')

    def contents_prompt(self,file_path,df,prompt):
        if file_path:
            #đọc file pdf
            file = pathlib.Path(file_path)
            obj_file=types.Part.from_bytes(data=file.read_bytes(),mime_type='application/pdf',)
        if df is not None:
            text_json=df.to_json(orient="records", force_ascii=False, indent=2)
        
        if file_path and df is not None:
            contents=[obj_file,text_json,prompt]
        elif file_path and df is None:
            contents=[obj_file,prompt]
        elif not file_path and df is not None:
            contents=[text_json,prompt]
        else:
            contents=[prompt]

        return contents

    def genai_group_hypothesis(self,file_path=None,df_sub_hypothesis=None):
        '''
        file_path: đường dẫn đến tài liệu để mô hình lấy group hypothesis
        '''
        #tạo contents
        contents=self.contents_prompt(file_path,df_sub_hypothesis,self.group_prompt)

        response = self.group_client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config={
                "response_mime_type": "application/json",
                "response_schema": list[genai_group_format],
                }
                )
        #xử lý đầu ra
        results=json.loads(response.text)
        results=pd.DataFrame(results)
        return results
    
    
    def genai_sub_hypothesis(self,group_hypothesis,file_path=None):
        '''
        group_hypothesis: là 1 hàng trong df kết quả của genai_group_pdf
        file_path: đường dẫn đến tài liệu muốn mô hình đọc để kiếm sub_hypothesis
        '''

        '''
        #lọc response_history chỉ lấy cùng group với group_hypothesis
        group = group_hypothesis['Group_Hypothesis'].unique()
        response_history=self.response_history.loc[self.response_history['Group Hypothesis'].isin(group)]
        response_history=response_history.to_json(orient="records", force_ascii=False, indent=2)
        response_history=f"response_history:\n{response_history}"
        print(response_history)
        contents=self.contents_prompt(file_path,group_hypothesis,self.sub_prompt)+[response_history]
        '''
        contents=self.contents_prompt(file_path,group_hypothesis,self.sub_prompt)
        response = self.sub_client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config={
                "response_mime_type": "application/json",
                "response_schema": list[genai_sub_format],
                "system_instruction": {self.alpha_system}
                }
                )
        #xử lý đầu ra
        results=json.loads(response.text)
        results=pd.DataFrame(results)
        return results
    
    def genai_alpha(self,sub_hypothesis):
        contents=self.contents_prompt(None,sub_hypothesis,self.alpha_prompt)

        response = self.alpha_client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config={
                "response_mime_type": "application/json",
                "response_schema": list[genai_alpha_format],
                "system_instruction": {self.alpha_system}
                }
                )
        #xử lý đầu ra
        results=json.loads(response.text)
        results=pd.DataFrame(results)
        return results
    
    def genai_similar_alpha(self,df_alpha):
        contents=self.contents_prompt(None,df_alpha,self.similar_alpha_prompt)

        response = self.similar_alpha_client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config={
                "response_mime_type": "application/json",
                "response_schema": list[genai_similar_alpha_format],
                "system_instruction": {self.alpha_system}
                }
                )
        #xử lý đầu ra
        results=json.loads(response.text)
        results=pd.DataFrame(results)
        #đổi tên bỏ chữ new
        results.rename(columns={'Sub_Hypothesis_new':'Sub_Hypothesis',
                                'Description_new':'Description',
                                'Expression_new':'Expression',
                                'Expression_alpha_new':'Expression_alpha'},inplace=True)
        return results
    
    def run(self,file_pdf_path=None,file_sub_hypothesis_path=None):
        '''
        file_pdf_path: đường dẫn đến file tài liệu
        file_sub_hypothesis_path: đường dẫn đến file csv chứa sub hypothesis
        '''
        if file_pdf_path:
            file_name = os.path.basename(file_pdf_path)
        else:
            file_name=None

        #Kiểm tra và chuyển file_sub_hypothesis_path thành dataframe
        if file_sub_hypothesis_path:
            df_sub_hypothesis=pd.read_csv(file_sub_hypothesis_path)
            
        else:
            df_sub_hypothesis=None
            

        #create group hypothesis
        df_group_hypothesis=self.genai_group_hypothesis(file_pdf_path,df_sub_hypothesis)
        self.group_wks.append_rows(df_group_hypothesis.values.tolist())
        #in kết quả
        json_text=df_group_hypothesis.to_json(orient="records", force_ascii=False, indent=2)
        print('Group Hypothesis\n',json_text)
        print('-'*60)
        sleep(10)

        #create sub hypothesis
        for i in range(len(df_group_hypothesis)):
            print('Create sub hypothesis')
            try:
                group_hypothesis=df_group_hypothesis.loc[[i]]
                df_sub_hypothesis=self.genai_sub_hypothesis(group_hypothesis,file_pdf_path)
                sleep(10)
                #create alpha
                for j in range(len(df_sub_hypothesis)):
                    print('Create alpha')
                    sub_hypothesis=df_sub_hypothesis.loc[[j]]
                    df_alpha=self.genai_alpha(sub_hypothesis)

                    #in kết quả
                    json_text=df_alpha.to_json(orient="records", force_ascii=False, indent=2)
                    print(json_text)

                    expression_alpha=list(df_alpha['Expression_alpha'])
                    expression_alpha=expression_alpha[0] #lấy str

                    if expression_alpha != 'invalid':
                        #simulate alpha
                        results,check_simulate,sharpe,score=self.processing_simulate(expression_alpha,df_alpha,file_name)
                        self.append_rows([results]) #up kết quả lên sheet

                        '''#chạy optimize
                        if check_simulate and sharpe and sharpe > 0.3 and score and score >-100:
                            print('Optimize Alpha')
                            expression_alpha_optimize,_=self.optimize.run(expression_alpha,results)
                            results,check_simulate,sharpe,score=self.processing_simulate(expression_alpha_optimize,df_alpha,file_name)
                            self.append_rows([results+['version optimize']])'''
                                   
                        #chạy combine
                        if check_simulate and score and score >0 and sharpe >0.5:
                            print('Combine Alpha')
                            alpha=results[7]
                            setting=results[16]
                            ComBine().run(alpha,setting)
                        
                        #chạy similar
                        if check_simulate and score and score >0: #kiểm tra đồng thời tồn tại kết quả simulate,score và score >0
                           print('Create similar alpha')
                           df_similar_alpha=self.genai_similar_alpha(df_alpha) #nếu dương tiến hành chạy similar

                           #in kết quả
                           json_text=df_similar_alpha.to_json(orient="records", force_ascii=False, indent=2)
                           print(json_text)

                           #duyệt qua các alpha similar
                           for k in range(len(df_similar_alpha)):
                               similar_alpha=df_similar_alpha.loc[[k]]
                               expression_similar_alpha=list(similar_alpha['Expression_alpha']) #lấy biểu thức alpha
                               expression_similar_alpha=expression_similar_alpha[0]

                               results,check_simulate,sharpe,score=self.processing_simulate(expression_similar_alpha,similar_alpha,file_name)
                               self.append_rows([results]+['version similar'])

                               '''#chạy optimize
                               if check_simulate and sharpe and sharpe > 0.3 and score and score >-100:
                                   print('Optimize Alpha')
                                   expression_similar_alpha_optimize,_=self.optimize.run(expression_similar_alpha)
                                   results,check_simulate,sharpe,score=self.processing_simulate(expression_similar_alpha_optimize,similar_alpha,file_name)
                                   self.append_rows([results+['version optimize']])'''
                               
                               #chạy combine
                               if check_simulate and score and score >0 and sharpe >0.5:
                                   print('Combine Alpha')
                                   alpha=results[7]
                                   setting=results[16]
                                   ComBine().run(alpha,setting)
                    else:
                        results=[self.date, self.process_name, file_name]+df_alpha.values.tolist()[0]
                        self.append_rows([results])
                    sleep(10)
            except Exception as e:
                print(f'ERROR {e}')
                sleep(30)

    def processing_simulate(self,expression_alpha:str,df_alpha,file_name):
        result_simulate=wl.single_simulate(expression_alpha)
        #lấy sharpe
        sharpe=result_simulate[0]
        score=None #thiết lập score ban đầu

        #operators_and_fields=Optimize().extract(expression_alpha[0])
        #operators=str(operators_and_fields['operators'])
        #fields=str(operators_and_fields['fields'])
        
        #sharpe dương thì lưu còn âm thì đảo chiều giả thuyết
        if sharpe and sharpe >=0: #kiểm tra đồng thời sharpe tồn tại và sharpe dương
            sharpe=sharpe 
            score=result_simulate[11] #lấy score
            #chuyển kết quả lên gg sheet - auto_alpha là df --> [[]]; result_simulate là list --> []
            results=[self.date, self.process_name, file_name]+df_alpha.values.tolist()[0]+result_simulate
            
        
        elif sharpe and sharpe <0:
            sharpe=-sharpe 
            expression_alpha="-("+expression_alpha+")"
            df_alpha['Expression_alpha']=expression_alpha #cập nhật lại Expression_alpha trong alpha 
            
            result_simulate=wl.single_simulate(expression_alpha)
            score=result_simulate[11] #lấy score
            results=[self.date, self.process_name, file_name]+df_alpha.values.tolist()[0]+result_simulate
        
        else: #sharpe không tồn tại, có nghĩa là result_simulate trả ra [None]
            sharpe=None
            results=[self.date, self.process_name, file_name]+df_alpha.values.tolist()[0]
        
        #kiểm tra kết quả cuối cùng đã tồn tại kết quả simulate chưa
        if len(results)>9:
            check_simulate=True
        else:
            check_simulate=False
        return results,check_simulate,sharpe,score
                
if __name__ == '__main__':
    '''group_index_key=int(input('Nhập group_index_key (int): '))
    sub_index_key=int(input('Nhập sub_index_key (int): '))
    alpha_index_key=int(input('Nhập alpha_index_key (int): '))
    similar_alpha_index_key=int(input('Nhập similar_alpha_index_key (int): '))

    file_pdf_path=input('Nhập đường dẫn đến file tài liệu (nếu có): ')
    file_sub_hypothesis_path=input('Nhập đường dẫn đến file sub hypothesis csv (nếu có):')'''
    group_index_key=0
    sub_index_key=1
    alpha_index_key=2
    similar_alpha_index_key=3

    folder_path='./doc/all'
    list_file=os.listdir(folder_path) #danh sách file trong folder
    random_file=random.choice(list_file) #chọn ngẫu nhiên 1 file
    file_pdf_path=os.path.join(folder_path,random_file) #tạo đường dẫn đến file đó
    file_sub_hypothesis_path=None
    wl=WorldQuant()
    #while True:
    #    try:
    GenAI(group_index_key,sub_index_key,alpha_index_key,similar_alpha_index_key).run(file_pdf_path,file_sub_hypothesis_path)
    #    except Exception as e:
    #        print(f'ERROR OTHER {e}')
    #        sleep(60)