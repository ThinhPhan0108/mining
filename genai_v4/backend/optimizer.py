# backend/optimizer.py
import pandas as pd
import re
from itertools import product
import os # <-- THÊM THƯ VIỆN OS
import sys
# --- PHẦN 1: ĐỌC FILE CSV MỘT CÁCH CHÍNH XÁC ---
# Lấy đường dẫn thư mục cha
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# Thêm vào sys.path nếu chưa có
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Tạo đường dẫn đầy đủ đến các file CSV
fields_csv_path = './genai_v4/backend/fields.csv'
operators_csv_path = './genai_v4/backend/operators.csv'

try:
    # Đọc file CSV bằng đường dẫn đầy đủ
    fields_df = pd.read_csv(fields_csv_path)
    operators_df = pd.read_csv(operators_csv_path)
    print("Đã đọc thành công fields.csv và operator.csv bằng đường dẫn tuyệt đối.")
except FileNotFoundError:
    print(f"CẢNH BÁO: Không tìm thấy file fields.csv hoặc operator.csv tại '{parent_dir}'.")
    fields_df = pd.DataFrame(columns=['id', 'group']) 
    operators_df = pd.DataFrame(columns=['operator', 'group'])

# --- CÁC PHẦN CÒN LẠI GIỮ NGUYÊN NHƯ CŨ ---

# --- PHẦN 2: HÀM EXTRACT ---
def extract(expression):
    components = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*|\d+\.\d+|\d+|[^\w\s]', expression)
    
    valid_fields = fields_df['id'].tolist() if not fields_df.empty else []
    valid_operators = operators_df['operator'].tolist() if not operators_df.empty else []

    fields = [comp for comp in components if comp in valid_fields]
    operators = [comp for comp in components if comp in valid_operators]
    numbers = [comp for comp in components if re.match(r'^\d+\.?\d*$', comp)]
    
    return fields, operators, numbers, components

# --- PHẦN 3: LOGIC VÉT CẠN ---
def generate_replacements(options, fields, operators, numbers):
    replacement_map = {}

    if options.get('replace_fields') and not fields_df.empty:
        for field in set(fields):
            try:
                field_group = fields_df[fields_df['id'] == field]['group'].iloc[0]
                replacements = fields_df[fields_df['group'] == field_group]['id'].tolist()
                replacement_map[field] = replacements
            except IndexError:
                replacement_map[field] = [field]
    
    if options.get('replace_operators') and not operators_df.empty:
        for op in set(operators):
            try:
                op_group = operators_df[operators_df['operator'] == op]['group'].iloc[0]
                op_replacements = operators_df[operators_df['group'] == op_group]['operator'].tolist()
                replacement_map[op] = op_replacements
            except IndexError:
                replacement_map[op] = [op]

    if options.get('replace_day_group'):
        for num_str in set(numbers):
            try:
                num = int(num_str)
                replacements = sorted(list(set([
                    max(1, num - 5), max(1, num - 2), num, num + 2, num + 5
                ])))
                replacement_map[num_str] = [str(r) for r in replacements]
            except ValueError:
                replacement_map[num_str] = [num_str]
            
    return replacement_map

def exhaustive_search(alpha_expression, options):
    fields, operators, numbers, components = extract(alpha_expression)
    
    if not any(options.values()):
        return [alpha_expression]

    replacement_map = generate_replacements(options, fields, operators, numbers)
    
    component_options = [replacement_map.get(comp, [comp]) for comp in components]
        
    generated_alphas = set()
    
    for combination in product(*component_options):
        new_alpha = "".join(combination)
        generated_alphas.add(new_alpha)

    return list(generated_alphas)[:500]