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
import PyPDF2

class financial_ratios_format(BaseModel):
    Indicator_Name: str
    Alpha_Idea: str
    Formula: str
    Important_Implementation_Notes: str

class format_of_format(BaseModel):
    Original_Formula: str
    WorldQuant_Standard_Formula: str

class GenAI:
    def __init__(self,index_key=1,format_index_key=2,group_prompt='group_2'):
        self.date=datetime.datetime.now().strftime('%d-%m-%Y')
        self.process_name='version_2.2'
        
        data_key=self.read_json('./keyapi.json')
        self.list_key=data_key['list_key']

        self.client=genai.Client(api_key=self.list_key[index_key])
        self.format_client=genai.Client(api_key=self.list_key[format_index_key])
        self.name_model="gemini-2.5-flash"

        self.prompt=open(f"./genai_v3/prompt/{group_prompt}.txt", "r", encoding="utf-8").read()
        self.format_prompt=open("./genai_v3/prompt/format.txt", "r", encoding="utf-8").read()
        self.system_prompt=open("./genai_v3/prompt/system.txt", "r", encoding="utf-8").read()

        #truy cập gg sheet
        gc = gspread.service_account(filename='./apisheet.json')
        wks = gc.open("Plan - stage 3").worksheet("financial_ratios")
        self.wks=wks

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
            #file = pathlib.Path(file_path)
            #obj_file=types.Part.from_bytes(data=file.read_bytes(),mime_type='application/pdf',)

            with open(file_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                text_pdf = ""
                for page in reader.pages:
                    text_pdf += page.extract_text()

        if df is not None:
            text_df=df.to_json(orient="records", force_ascii=False, indent=2)
        
        if file_path and df is not None:
            contents=[text_pdf,text_df,prompt]
        elif file_path and df is None:
            contents=[text_pdf,prompt]
        elif not file_path and df is not None:
            contents=[text_df,prompt]
        else:
            contents=[prompt]

        return contents
    
    def genai_financial_ratios(self,variable,file_path=None):
        '''
        variable: là một df gồm id và description
        file_path: đường dẫn đến tài liệu muốn mô hình đọc để kiếm sub_hypothesis
        '''
        contents=self.contents_prompt(file_path,variable,self.prompt)
        
        response = self.client.models.generate_content(
            model=self.name_model,
            contents=contents,
            config={
                "response_mime_type": "application/json",
                "response_schema": list[financial_ratios_format],
                #"system_instruction": {self.system_prompt}
                }
                )
        #xử lý đầu ra
        results=json.loads(response.text)
        results=pd.DataFrame(results)
        return results
    
    def genai_format(self,financial_ratios):
        '''
        sub_hypothesis là 1 dataframe
        '''
        contents=self.contents_prompt(None,financial_ratios,self.format_prompt)

        response = self.format_client.models.generate_content(
            model=self.name_model,
            contents=contents,
            config={
                "response_mime_type": "application/json",
                "response_schema": list[format_of_format],
                "system_instruction": {self.system_prompt}
                }
                )
        #xử lý đầu ra
        results=json.loads(response.text)
        results=pd.DataFrame(results)
        return results
    
    def run(self,select_variable=None,type_dataset="{'id': 'analyst4', 'name': 'Analyst Estimate Data for Equity'}",auto='1'):
        print('Truy cập vào danh sách các biến')
        datafields=pd.read_excel('./datafields.xlsx')
        condition= (datafields['type']=='MATRIX')|(datafields['type']=='VECTOR')
        datafields=datafields[condition].sort_values(by=['alphaCount','userCount'],ascending=False,ignore_index=True)

        if select_variable:
            list_variable=[select_variable]
        else:    
            list_variable=datafields[datafields['dataset']==type_dataset]['id'].value_counts().index
        
        for i in list_variable:
            variable=datafields[datafields['id']==i][['id','description']]
            print(variable)
            results=self.genai_financial_ratios(variable)
            print(results.to_json(orient="records", force_ascii=False, indent=2))

            for j in range(len(results)):
                result = results.loc[[j]]
                df_format = self.genai_format(result)
                result['WorldQuant_Standard_Formula']=df_format['WorldQuant_Standard_Formula'].values
                formula=df_format['WorldQuant_Standard_Formula'].values[0]
                
                #chạy mô phỏng
                simulate_result = wq.single_simulate(formula)
                print(result)
                self.wks.append_rows([[None]+result.values.tolist()[0]+[None]])
                sleep(30)
    
if __name__ == '__main__':
    variable=input("Hãy chọn môt biến: ")
    wq=WorldQuant()
    GenAI(index_key=2,format_index_key=3,group_prompt='group_2').run(variable)