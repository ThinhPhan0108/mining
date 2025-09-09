import sys
import os
# Lấy đường dẫn thư mục cha
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# Thêm vào sys.path nếu chưa có
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import pandas as pd
import gspread
import json
from lark import Lark, Transformer, v_args
from lark import Transformer, Tree, Token


class Update:
    def __init__(self):
        gc=gspread.service_account('./apisheet.json')
        self.metrics_name=['Sharpe','Turnover', 'Fitness', 'Returns', 'Drawdown', 'Margin']

        #lấy dữ liệu 2 bản alpha
        data_1=self.get_data_alpha(gc,'Finding Alpha','Auto_alpha_demo',['Alpha']+self.metrics_name )
        data_2=self.get_data_alpha(gc,'Finding Alpha','Auto_alpha_demo_v2',['Alpha']+self.metrics_name)
        data_3=self.get_data_alpha(gc,'Auto Alpha','auto_alpha',['Alpha']+self.metrics_name)

        #xử lý dữ liệu
        self.data=self.processing_data_alpha(data_1,data_2,data_3,self.metrics_name)

        #kết nối grammar để phân tích công thức
        self.grammar = open("./optimize/grammar.txt", "r", encoding="utf-8").read()
        self.parser = Lark(self.grammar, parser='lalr')

        #đọc dữ liệu xếp hạn cũ
        self.opts_path='./optimize/rank/operators.csv'
        self.fields_path='./optimize/rank/fields.csv'
        self.df_opts_rank_history=pd.read_csv(self.opts_path)
        self.df_fields_rank_history=pd.read_csv(self.fields_path)
    
    def get_data_alpha(self,gc,sheetname,worksheet,columns):
        wks=gc.open(sheetname).worksheet(worksheet)
        data=pd.DataFrame(wks.get_all_records())
        data=data[columns]
        return data
    
    #xử lý data
    def processing_data_alpha(self,data_1,data_2,data_3,columns):
        #nối dọc
        data=pd.concat([data_1,data_2])
        data=pd.concat([data,data_3])
        #loại bỏ na
        data.dropna(inplace=True)

        #đổi kiểu dữ liệu
        for column in columns:
            data=data[data[column]!=''].copy() #loại bỏ ''
            data[column]=data[column].apply(lambda row: abs(float(str(row).replace(',','.').replace('%',''))/100))

        #xóa signal =
        data=data[~data['Alpha'].str.contains('signal =', na=False)]
        #xóa trùng lặp
        data.drop_duplicates(inplace=True)
        data.reset_index(drop=True,inplace=True)
        return data
    
    #xuất hàm và biến
    def extract(self,alpha):
        tree = self.parser.parse(alpha)
        filed_list = []
        operator_list=[]
        def visit(node):
            if isinstance(node, Tree):
                if node.data == "var":
                    # node.children = [Token("NAME", "var_name")]
                    var_name = node.children[0].value
                    filed_list.append(var_name)

                if node.data == "func_call":
                    # node.children = [Token("NAME", "var_name")]
                    operator_name = node.children[0].value
                    operator_list.append(operator_name)

                for child in node.children:
                    visit(child)
        visit(tree)
        results={"operators":operator_list, "fields":filed_list}
        return results
    
    #xử lý kết quả trích suất operator and fields
    def processing_extract(self,data):
        operators_results=[]
        fields_results=[]

        for index in range(len(data)):
            alpha=data.loc[index,'Alpha'] #lấy alpha
            print(alpha)
            metrics=list(data.iloc[index,1:]) #lấy các chỉ số sharpe, turnover,...
            try:
                #trích suất operator and fields
                opt_fields=self.extract(alpha) 
                
                opts=opt_fields.get('operators') #lấy opt
                fields=opt_fields.get('fields') #lấy fields
                
                #map với sharpe
                opts=[[opt]+metrics for opt in opts]
                fields=[[field]+metrics for field in fields]

                #thêm vào kết quả
                operators_results+=opts
                fields_results+=fields
            except:
                print("alpha bị lỗi là: ", alpha)
                pass
            
        #chuyển kết quả thành dataframe
        df_opts=pd.DataFrame(operators_results,columns=['operator']+self.metrics_name)
        df_fields=pd.DataFrame(fields_results,columns=['field']+self.metrics_name)
        return df_opts,df_fields
    
    def update_rank(self,database,data,left_on,right_on):
        database.drop(['Sharpe','Fitness'],axis=1,inplace=True)#xóa cột Sharpe và Fitness cũ trong database
        database=database.merge(data,left_on=left_on,right_on=right_on,how='outer')
        database.drop(right_on,axis=1,inplace=True) #loại bỏ cột right_on
        database[['Sharpe_mean','Fitness_mean']]=database.groupby('group')[['Sharpe','Fitness']].transform('mean')
        database['rank']=database['Sharpe']/database['Sharpe_mean']+database['Fitness']/database['Fitness_mean']
        return database
    
    def run(self)->None:
        #trích xuất field and operator và xử lý dữ liệu
        df_opts,df_fields=self.processing_extract(self.data)
        
        #lưu lại dữ liệu
        #df_opts.to_csv('./optimize/rank/operator_rank.csv',index=False)
        #df_fields.to_csv('./optimize/rank/field_rank.csv',index=False)
        
        #tính median của các operator và field
        df_opts_median=df_opts.groupby('operator')[['Sharpe','Fitness']].median().reset_index()
        df_fields_median=df_fields.groupby('field')[['Sharpe','Fitness']].median().reset_index()
        
        #cập nhật trọng số
        df_opts_rank_new=self.update_rank(self.df_opts_rank_history,df_opts_median,'name','operator')
        df_opts_rank_new.to_csv(self.opts_path,index=False)

        df_fields_rank_new=self.update_rank(self.df_fields_rank_history,df_fields_median,'id','field')
        df_fields_rank_new.to_csv(self.fields_path,index=False)

if __name__=='__main__':
    Update().run()