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
import csv
import gspread
from time import sleep

class out_format(BaseModel):
    Group_Name: str
    Variables: list[str]

class Similar:
    def __init__(self,key_index):

        data_key=self.read_json('./keyapi.json')
        self.list_key=data_key['list_key']
        self.client=genai.Client(api_key=self.list_key[key_index])
        self.name_model="gemini-1.5-flash"

        self.prompt=open("./similar/prompt/prompt.txt", "r", encoding="utf-8").read()

        self.system_prompt=open("./similar/prompt/system.txt", "r", encoding="utf-8").read()

    
    # Đọc file JSON
    def read_json(self,file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)  # Tải dữ liệu JSON
        return data

    def genai_similar(self,variable):
        response =self.client.models.generate_content(
            model=self.name_model,
            contents=[variable,self.prompt],
            config={
                "response_mime_type": "application/json",
                "response_schema": list[out_format],
                "system_instruction": {self.system_prompt}
                }
                )
        #xử lý đầu ra
        results=json.loads(response.text)
        results=pd.DataFrame(results)
        return results
    
    #duyệt qua từng biến sau đó tìm danh sách biến similar
    def run_v1(self,len_past):
        try:
            data=pd.read_excel('./similar/data_not_group.xlsx')
            #data=data[data['dataset']=="{'id': 'fundamental6', 'name': 'Company Fundamental Data for Equity'}"].reset_index(drop=True)
            data=data[['id','description','dataset','category','subcategory']]
            results=pd.DataFrame(columns=['Variables','Similar_variables'])

            for i in range(len_past,len(data)):
                variable=data.loc[[i]].to_json(orient="records", force_ascii=False, indent=2)
                result=self.genai_similar(variable)
                results=pd.concat([results,result])

                print(f'number id: {i}\n{result.to_json(orient="records", force_ascii=False, indent=2)}')
                sleep(10)
            return results
        except Exception as e:
            print('ERROR : ',e)
            return results
        
    #phân cụm các biến
    def run_v2(self):
        try:
            results=self.genai_similar(self.system_prompt)
            return results
        except Exception as e:
            print('ERROR : ',e)
            return results
        
if __name__=='__main__':
    key_index=0
    #while True:
    try:
        #results_past=pd.read_excel('./similar/results.xlsx')
        #len_past=len(results_past)
        results=Similar(key_index).run_v2()
        #results_past=pd.concat([results_past,results])
        results.to_excel("./similar/results.xlsx",index=False)

        key_index=(key_index+1)%7
        print(key_index)
    except Exception as e:
        print('ERROR : ',e)
        key_index=(key_index+1)%7