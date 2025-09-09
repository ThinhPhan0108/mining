import sys
import os
# Lấy đường dẫn thư mục cha
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# Thêm vào sys.path nếu chưa có
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from lark import Lark, Transformer, v_args
from lark import Transformer, Tree, Token

import gspread
import pandas as pd
import ast
import json
from itertools import product
from worldquant import WorldQuant
import random

class RenameFields(Transformer):
    def __init__(self, rename_map):
        super().__init__()
        self.rename_map = rename_map
    def var(self, items):
        func_name=items[0]
        if func_name.value in self.rename_map:
            func_name = Token("NAME", self.rename_map[func_name.value])
        return Tree("var", [func_name])

class RenameOperators(Transformer):
    def __init__(self, map):
        '''
        map={'<old_name>':'<new_name>','group':'<group_name>','day':'<number_day>'}
        '''
        super().__init__()
        self.map = map
        self.day = map.get('day')
        self.group = map.get('group')

    def func_call(self, items):
        func_name = items[0]  # Token(NAME)
        old_name=func_name.value
        args = items[1]       # Tree("expr_list", [...])

        # Đổi tên toán tử nếu có trong map
        if isinstance(func_name, Token) and old_name in self.map: #kiểm tra old_name có nằm trong key của map không
            new_name = self.map[old_name]
            func_name = Token("NAME", new_name)

            # Xác định loại toán tử
            type_op = old_name.split('_')[0] if '_' in old_name else old_name

            # Thay đổi tham số theo loại toán tử
            if isinstance(args, Tree) and args.data == "arg_list" :
                if type_op == "ts" and len(args.children) >= 2 and self.day:
                    args.children[-1] = Token("NUMBER", self.day)
                elif type_op == "group" and len(args.children) >= 2 and self.group: 
                    args.children[-1] = Token("NAME", self.group)

        return Tree("func_call", [func_name, args])
    
class Optimize:
    def __init__(self):
        #self.similar_fields=self.read_json('./optimize/similar_fields.json')
        #self.operator=self.read_json('./optimize/operator.json')
        self.df_rank_fields=pd.read_csv('./optimize/rank/fields.csv')
        self.df_rank_operators=pd.read_csv('./optimize/rank/operators.csv')
        self.days=['25','63','125','250','500']
        self.groups=['market','sector','industry','subindustry']
        
        self.grammar = open("./optimize/grammar.txt", "r", encoding="utf-8").read()
        self.parser = Lark(self.grammar, parser='lalr')

        #self.wl=WorldQuant()
        #gc = gspread.service_account(filename='./apisheet.json')
        #wks = gc.open("Auto Alpha").worksheet("optimize")
        #self.wks=wks
    
    # Đọc file JSON
    def read_json(self,file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)  # Tải dữ liệu JSON
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
    
    def gets(self,field_or_operator,option='field'):
        if option=='field':
            #lấy group
            condition=self.df_rank_fields['id']==field_or_operator
            group=self.df_rank_fields.loc[condition,'group'].iloc[0] #lấy group
            #lấy danh sách fields có trong group
            df_group_fields=self.df_rank_fields[self.df_rank_fields['group']==group] 
            df_group_fields.sort_values(by='rank',ascending=False,inplace=True) #sort từ cao xuống thấp
            list_group=list(df_group_fields['id']) #lấy danh sách fields

        elif option=='operator':
            #lấy group
            condition=self.df_rank_operators['name']==field_or_operator
            group=self.df_rank_operators.loc[condition,'group'].iloc[0] #lấy group
            #lấy danh sách operators có trong group
            df_group_operators=self.df_rank_operators[self.df_rank_operators['group']==group] 
            df_group_operators.sort_values(by='rank',ascending=False,inplace=True) #sort từ cao xuống thấp
            list_group=list(df_group_operators['name']) #lấy danh sách operators
        
        list_group.remove(field_or_operator) #xóa phần tử đầu vào ra khỏi danh sách
        #chọn 2 phần tử đầu tiên trong danh sách còn phần tử thứ 3 thì random --> mục đích nhằm giúp cho các biến tốt nhưng hiện tại rank chưa tốt có cơ hội tăng rank
    
        '''if len(list_group)>=3:
            result_1=list_group[0:2]
            result_2=[random.choice(list_group[2:])]
            results=result_1+result_2
        elif len(list_group) >=1:
            results=list_group
        else:
            results=None'''
        return list_group
    
    #optimize field
    def optimize_field(self,alpha,field):
        '''
        field: str
        '''
        tree = self.parser.parse(alpha)
        results=[]
        
        #xác định các field similar
        field_new_list=self.gets(field,option='field')
        print('list replace',field_new_list)

        if field_new_list: #kiểm tra xem field_new_list có tồn tại hay không
            #duyện qua từng cái
            for field_new in field_new_list:
                obj=self.map(field,field_new)[0] #tạo format để chuyển đổi --> vì đầu ra là danh sách 1 giá trị nên dùng [0] thay cho for
                tree_new=RenameFields(obj).transform(tree) #replace old --> new
                alpha_new=self.tree_to_expr(tree_new) #chuyển thành dạng biểu thức alpha
                results.append(alpha_new)
            return results
        else:
            return None
    
    def optimize_operator(self,alpha,operator):
        '''
        operator: str
        '''
        tree = self.parser.parse(alpha)
        results=[]

        #Xác định danh sách cần chuyển đổi
        op_new_list=self.gets(operator,option='operator')
        print('list replace',op_new_list)
        
        if op_new_list:
            for op_new in op_new_list:
                obj=self.map(operator,op_new)[0] #tạo danh sách format để chuyển đổi 
                tree_new=RenameOperators(obj).transform(tree) #replace
                alpha_new=self.tree_to_expr(tree_new) #chuyển thành biểu thức alpha
                results.append(alpha_new)                                
            return results
        else:
            return None
        
    def optimize_parameter(self,alpha,operator):
        '''
        operator: str
        '''
        tree = self.parser.parse(alpha)
        results=[]

        #Xác định danh sách cần chuyển đổi
        word= operator.split('_')[0] if '_' in operator else operator #lấy giá trị đầu tiên của toán tử (mụd đích lấy được ts và group)
        obj_list=self.map(operator,operator,word) #tạo danh sách format để chuyển đổi

        for obj in obj_list:
            tree_new=RenameOperators(obj).transform(tree) #replace
            alpha_new=self.tree_to_expr(tree_new) #chuyển thành biểu thức alpha
            results.append(alpha_new)
        return  results
    
    def opimize_turnover(self,alpha,simulate_result,decay):
        turnover=simulate_result[1] #lấy turnover
        
        if turnover < 0.2:
            return simulate_result,decay #nếu <0.2 thì break không cần tối ưu
        
        elif turnover > 0.7:
            decay+=15
        elif turnover > 0.5:
            decay+=10
        elif turnover > 0.2:
            decay+=5
        simulate_result=self.wl.single_simulate(alpha,decay=decay,get_corr_and_score=False)
        return simulate_result,decay
    
    def map(self,old,new,word=None):
        obj_list=[]
        if word=='ts':
            for day in self.days:
                obj_list.append({old:new,'day':day})
        elif word=='group':
            for group in self.groups:
                obj_list.append({old:new,'group':group})
        else:
            obj_list.append({old:new})
        return obj_list

    #chuyển đổi tree thành công thức
    def tree_to_expr(self,tree):
        if isinstance(tree, Token):
            return tree.value

        if tree.data == 'number':
            return tree.children[0].value

        if tree.data == 'var':
            return tree.children[0].value
        
        if tree.data == 'neg':
            return '-' + self.tree_to_expr(tree.children[0])

        if tree.data in ('add', 'subtract', 'multiply', 'divide','less','less_equal','greater','greater_equal'):
            left = self.tree_to_expr(tree.children[0])
            right = self.tree_to_expr(tree.children[1])
            op = {'add': '+', 'subtract': '-', 'multiply': '*', 'divide': '/','less':'<','less_equal':'<=','greater':'>','greater_equal':'>='}[tree.data]
            return f'({left} {op} {right})'

        if tree.data == 'func_call':
            func_name = tree.children[0].value
            args = self.tree_to_expr(tree.children[1])
            return f'{func_name}({args})'

        if tree.data == 'arg_list':
            return ', '.join(self.tree_to_expr(child) for child in tree.children)

        if tree.data == 'kwarg':
            key = self.tree_to_expr(tree.children[0])
            value = self.tree_to_expr(tree.children[1])
            return f'{key}={value}'

        # fallback: unknown node
        return tree.data

    def run(self,alpha,simulate_result,option_best='sharpe'):
        #results=[]
        #tree = self.parser.parse(alpha)
        fields_ops=self.extract(alpha)
        ops=fields_ops.get('operators')
        fields=fields_ops.get("fields")
        fields=list(set(fields)-set(self.groups)) #loại bỏ các giá trị group ra khỏi fields
        #lấy code
        code = simulate_result[-1]
        simulate_result=self.wl.locate_alpha(code,False) #vì không đảm bảo được simulate_result lúc đầu được truyền vào có đúng cấu trúc [sharpe,turnover,... ] hay không
        
        #tối ưu fields
        alpha,best_simulate_result=self.best_alpha(alpha,simulate_result,fields,optimize_type='field',option_best=option_best)
        print(alpha)
        #tối ưu operator
        alpha,best_simulate_result=self.best_alpha(alpha,best_simulate_result,ops,optimize_type='operator',option_best=option_best)
        print(alpha)
        #tối ưu parameter
        alpha,best_simulate_result=self.best_alpha(alpha,best_simulate_result,ops,optimize_type='parameter',option_best=option_best)
        print(alpha)
        
        #tối ưu turnover
        decay=0 #khởi tạo decay
        for i in range(0,3): #chạy 3 lần tối ưu
            best_simulate_result,decay=self.opimize_turnover(alpha,best_simulate_result,decay)
        
        return alpha,best_simulate_result
    
    def best_alpha(self,alpha,simulate_result,fields_or_operators_list,optimize_type='field',option_best='sharpe'):

        option={"sharpe":0,"fitness":2,"returns":3}
        index_option=option.get(option_best)
        #simulate alpha đầu tiên
        simulate_results=[simulate_result] #khới tạo phần tử đầu tiên

        for item in fields_or_operators_list:

            #chọn loại tối ưu
            if optimize_type=='field':
                alpha_optimize_list=self.optimize_field(alpha,item)
            elif optimize_type=='operator':
                alpha_optimize_list=self.optimize_operator(alpha,item)
            elif optimize_type=='parameter':
                alpha_optimize_list=self.optimize_parameter(alpha,item)

            if alpha_optimize_list:
                #duyện qua các alpha optimize
                for alpha_optimize in  alpha_optimize_list:
                    simulate_result=self.wl.single_simulate(alpha_optimize,get_corr_and_score=False)
                    simulate_results.append(simulate_result)
                    print('alpha: ',alpha_optimize)
                    print('results: ',simulate_result)
                    self.wks.append_rows([[alpha,alpha_optimize]+simulate_result])

                #lấy index alpha best theo tiêu chuẩn cần tối ưu -- result nếu result = [None] thì khi chọn khác sharpe vẫn xảy ra lỗi
                results_list_by_option=[ abs(result[index_option]) if result and result[index_option] else 0 for result in  simulate_results] #tạo danh sách giá trị tiêu chuẩn mục tiêu
                index_alpha_best=results_list_by_option.index(max(results_list_by_option)) #index của alpha best
                
                #gắn alpha tối ưu vào alpha và tiếp tục quy trình tối ưu field tiếp theo
                alpha_optimize_list=[alpha]+alpha_optimize_list #gắn alpha tối ưu cũ đầu tiên
                alpha=alpha_optimize_list[index_alpha_best] #lấy alpha tốt nhất

                simulate_results=[simulate_results[index_alpha_best]] #khởi tạo hiệu quả alpha tối ưu cho dòng for tiếp theo

        best_simulate_result=simulate_results[0] #hiệu suất alpha best
        print('alpha best', alpha) 
        print('results best', best_simulate_result) 
        return alpha,best_simulate_result
    
    #["fields", "operator", "daily&group", "setting"]
    def complete_search(self, alpha, option):
        fields_ops = self.extract(alpha)
        
        ops = fields_ops.get('operators')
        fields = fields_ops.get("fields")
        fields = list(set(fields) - set(self.groups))  # loại bỏ group
        
        results = []

        # ----- xử lý fields -----
        if "fields" in option:
            new_option = option.copy()
            new_option.remove("fields")

            temp_results = []
            for field in fields:
                res = self.optimize_field(alpha, field)
                if res is not None: #kiểm tra rỗng
                    temp_results += res

            results += temp_results

            if new_option:
                for alpha_next in temp_results:
                    results += self.complete_search(alpha_next, new_option)

        # ----- xử lý operator -----
        if "operator" in option:
            new_option = option.copy()
            new_option.remove("operator")

            temp_results = []
            for op in ops: 
                res = self.optimize_operator(alpha, op)
                if res is not None: #kiểm tra rỗng
                    temp_results += res

            results += temp_results

            if new_option:
                for alpha_next in temp_results:
                    results += self.complete_search(alpha_next, new_option)

        # ----- xử lý daily&group -----
        if "daily&group" in option:
            new_option = option.copy()
            new_option.remove("daily&group")

            temp_results = []
            for op in ops:
                temp_results += self.optimize_parameter(alpha, op)

            results += temp_results

            if new_option:
                for alpha_next in temp_results:
                    results += self.complete_search(alpha_next, new_option)

        return results

        
if __name__=='__main__':
    #chạy optimize
    opti=Optimize()
    alpha_list=opti.read_json('./optimize/alpha.json')
    alpha_list=alpha_list.get('Alpha')
    output=[]
    for alpha in alpha_list:
        alpha_optimize,simulate_result=opti.run(alpha)
        result=[alpha,alpha_optimize]+simulate_result
        
        #tiếng hành lưu
        #lưu đề phòng
        output.append(result)
        df_output=pd.DataFrame(output)
        df_output.to_csv('./optimize/optimize_results.csv')
        #lưu trên sheet
        try:
            opti.wks.append_rows([result])
        except Exception as e:
            print('ERROR GG SHEET', e)