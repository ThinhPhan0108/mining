'''
Quy trình:
data fields --> select Variable --> Sub_hypothesis --> alpha --> simulate --> update sheet
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
import csv
import random

class genai_alpha_format(BaseModel):
    Variables_Used: list[str]
    Sub_Hypothesis: str
    Description: str
    Expression: str
    Expression_alpha: str

class genai_sub_format(BaseModel):
    Variables_Used: list[str]
    Sub_Hypothesis: str
    Description: str
    Expression: str

class genai_similar_alpha_format(BaseModel):
    Variables_Used: list[str]
    Sub_Hypothesis_new: str
    Description_new: str
    Expression_new: str
    Expression_alpha_new: str

class GenAI:
    def __init__(self,sub_index_key=0,alpha_index_key=0,similar_alpha_index_key=0):
        self.date=datetime.datetime.now().strftime('%d-%m-%Y')
        self.process_name='version_2.1'
        
        data_key=self.read_json('./keyapi.json')
        self.list_key=data_key['list_key']

        self.sub_client=genai.Client(api_key=self.list_key[sub_index_key])
        self.alpha_client=genai.Client(api_key=self.list_key[alpha_index_key])
        self.similar_alpha_client=genai.Client(api_key=self.list_key[similar_alpha_index_key])
        self.name_model="gemini-1.5-flash"

        self.sub_prompt=open("./genai_v2_1/prompt/sub_hypothesis_prompt.txt", "r", encoding="utf-8").read()
        #self.sub_system=open("./genai_v2/prompt/sub_hypothesis_system.txt", "r", encoding="utf-8").read()

        self.alpha_prompt=open("./genai_v2_1/prompt/alpha_prompt.txt", "r", encoding="utf-8").read()
        self.alpha_system=open("./genai_v2_1/prompt/alpha_system.txt", "r", encoding="utf-8").read()
        self.similar_alpha_prompt=open("./genai_v2_1/prompt/similar_alpha_prompt.txt", "r", encoding="utf-8").read()

        #truy cập gg sheet
        gc = gspread.service_account(filename='./apisheet.json')
        wks = gc.open("Auto Alpha").worksheet("auto_alpha")
        self.wks=wks

        '''#dữ liệu lịch sử phản hồi
        response_history=wks.get_all_records()
        #chỉ lấy một số cột nhất định
        desired_columns = ['Group Hypothesis','Sub Hypothesis','Description','Expression']
        response_history = [{col: row[col] for col in desired_columns if col in row} for row in response_history]

        self.response_history=f"response_history:\n{json.dumps(response_history, ensure_ascii=False, indent=2)}"'''
    
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

    def genai_sub_hypothesis(self,variable,file_path=None):
        '''
        variable: là một json gồm id và description
        file_path: đường dẫn đến tài liệu muốn mô hình đọc để kiếm sub_hypothesis
        '''
        #contents=self.contents_prompt(file_path,variable,self.sub_prompt)+[self.response_history]
        contents=self.contents_prompt(file_path,variable,self.sub_prompt)
        
        response = self.sub_client.models.generate_content(
            model=self.name_model,
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
    
    def genai_alpha(self,sub_hypothesis ):
        '''
        sub_hypothesis là 1 dataframe
        '''
        contents=self.contents_prompt(None,sub_hypothesis,self.alpha_prompt)

        response = self.alpha_client.models.generate_content(
            model=self.name_model,
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

    def run(self,file_pdf_path=None,type_category='dataset',number_drop=20):
        '''
        file_pdf_path: đường dẫn đến file tài liệu
        '''
        if file_pdf_path:
            file_name = os.path.basename(file_pdf_path)
        else:
            file_name=None

        #select variable
        print('Truy cập vào danh sách các biến')
        #datafields=wl.get_datafields()
        datafields=pd.read_excel('./datafields.xlsx')
        
        condition= (datafields['type']=='MATRIX')|(datafields['type']=='VECTOR')
        datafields=datafields[condition].sort_values(by=['alphaCount','userCount'],ascending=False,ignore_index=True)
        datafields=datafields.loc[number_drop:].reset_index(drop=True) # bỏ 20 biến thông dụng đầu 
        print(datafields)
        list_category= datafields[type_category].value_counts().index
        #create sub hypothesis
        for i in list_category:
            print('Create sub hypothesis')
            try:
                variable=datafields[datafields[type_category]==i]
                df_sub_hypothesis=self.genai_sub_hypothesis(variable,file_pdf_path)
                sleep(10)

                #create alpha
                for j in range(len(df_sub_hypothesis)):
                    sub_hypothesis=df_sub_hypothesis.loc[[j]]
                    print('Create alpha')
                    df_alpha=self.genai_alpha(sub_hypothesis)
                    df_alpha['Variables_Used']=df_alpha['Variables_Used'].astype(str)
                    #in kết quả
                    json_text=df_alpha.to_json(orient="records", force_ascii=False, indent=2)
                    print(json_text)

                    #simulate alpha
                    expression_alpha=list(df_alpha['Expression_alpha'])
                    expression_alpha=expression_alpha[0]
                    if expression_alpha!= 'invalid':
                        results,check_simulate,sharpe,score=self.processing_simulate(expression_alpha,df_alpha,file_name)
                        self.append_rows([results])

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
                               self.append_rows([results+['version similar']])
                    else:
                        results=[[self.date, self.process_name, file_name] +df_alpha.values.tolist()[0]]
                        self.append_rows(results)
                    sleep(10)
            except Exception as e:
                print(f'ERROR RUN {e}')
                sleep(30)

if __name__ == '__main__':
    '''sub_index_key=int(input('Nhập sub_index_key (int): '))
    alpha_index_key=int(input('Nhập alpha_index_key (int): '))

    option = input('Nhập type_category (0: id | 1: dataset | 2: subcategory | 3: category) :')
    category_json={'0':'id','1':'dataset','2':'subcategory','3':'category'}
    type_category=category_json.get(option)

    number_drop=int(input('Số lượng biến bỏ qua: '))
    file_pdf_path=input('Nhập đường dẫn đến file tài liệu (nếu có): ')'''
    sub_index_key=0
    alpha_index_key=1
    similar_alpha_index_key=2

    option='0'
    category_json={'0':'id','1':'dataset','2':'subcategory','3':'category'}
    type_category=category_json.get(option)
    number_drop=400

    folder_path='./doc/all'
    list_file=os.listdir(folder_path) #danh sách file trong folder
    random_file=random.choice(list_file) #chọn ngẫu nhiên 1 file
    file_pdf_path=os.path.join(folder_path,random_file) #tạo đường dẫn đến file đó
    file_pdf_path=None
    wl=WorldQuant()
    while True:
        try:
            GenAI(sub_index_key,alpha_index_key,similar_alpha_index_key).run(file_pdf_path,type_category,number_drop)
        except Exception as e:
            print(f'ERROR OTHER {e}')
            sleep(60)