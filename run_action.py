# DÁN TOÀN BỘ CODE NÀY VÀO FILE run_action.py

import os
import json
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from pydantic import BaseModel
from google import genai

# Import class WorldQuant của bạn
from worldquant import WorldQuant

# --- Các hàm tạo file từ secret (Giữ nguyên) ---
def tao_cac_file_can_thiet():
    """Tạo tất cả các file cần thiết (credential, keyapi, apisheet) từ GitHub Secrets."""
    print("Bắt đầu tạo các file cần thiết từ GitHub Secrets...")
    
    # Tạo credential.json
    username = os.getenv('WQ_USERNAME')
    password = os.getenv('WQ_PASSWORD')
    if not username or not password: raise ValueError("Lỗi: WQ_USERNAME hoặc WQ_PASSWORD không có trong secret.")
    with open('credential.json', 'w') as f: json.dump({"username": username, "password": password}, f)
    print("=> Đã tạo credential.json")

    # Tạo keyapi.json
    api_key = os.getenv('GENAI_API_KEY')
    if not api_key: raise ValueError("Lỗi: GENAI_API_KEY không có trong secret.")
    with open('keyapi.json', 'w') as f: json.dump({"list_key": [api_key, api_key, api_key, api_key]}, f)
    print("=> Đã tạo keyapi.json")

    # Tạo apisheet.json
    gcp_sa_key = os.getenv('GCP_SA_KEY')
    if not gcp_sa_key: raise ValueError("Lỗi: GCP_SA_KEY không có trong secret.")
    with open('apisheet.json', 'w') as f: f.write(gcp_sa_key)
    print("=> Đã tạo apisheet.json")

# --- Logic của GenAI được tích hợp trực tiếp vào đây ---

# Định dạng output mà AI cần trả về (lấy từ genai.py)
class financial_ratios_format(BaseModel):
    Indicator_Name: str
    Alpha_Idea: str
    Formula: str
    Important_Implementation_Notes: str

class format_of_format(BaseModel):
    Original_Formula: str
    WorldQuant_Standard_Formula: str

def tao_alpha_moi(so_luong=10):
    """
    Hàm này thay thế cho class GenAI, thực hiện việc gọi API để tạo alpha.
    """
    print("\nBắt đầu quy trình tạo alpha mới...")
    try:
        # Đọc key từ file vừa tạo
        with open('keyapi.json', 'r') as f: data_key = json.load(f)
        api_key = data_key['list_key'][0]
        client = genai.Client(api_key=api_key)
        name_model = "gemini-1.5-flash"

        # Đơn giản hóa prompt, không cần đọc từ file
        prompt_tao_y_tuong = """
        Dựa trên kiến thức của bạn về tài chính định lượng, hãy tạo ra 5 ý tưởng alpha mới lạ. 
        Mỗi ý tưởng cần có: Tên chỉ báo, Mô tả ý tưởng, Công thức toán học, và Lưu ý triển khai.
        Sử dụng các biến tài chính phổ biến như: 'returns', 'open', 'close', 'high', 'low', 'volume', 'vwap', 'market_cap', 'adv20'.
        Ví dụ: 'returns / adv20'.
        """
        
        prompt_chuan_hoa = """
        Chuyển đổi các công thức sau đây sang định dạng chuẩn của WorldQuant. 
        Hãy đảm bảo rằng các hàm như rank, scale, delay, ts_corr, ts_rank, ts_min, ts_max được sử dụng đúng cách.
        Ví dụ: 'rank(close)' hoặc 'scale(returns / adv20)'.
        """

        # BƯỚC 1: TẠO Ý TƯỞNG ALPHA
        print(" -> Bước 1: Gọi GenAI để tạo các ý tưởng alpha thô...")
        # SỬA LỖI: Đổi 'generation_config' thành 'config'
        response_ideas = client.models.generate_content(
            model=name_model,
            contents=[prompt_tao_y_tuong],
            config={
                "response_mime_type": "application/json",
                "response_schema": list[financial_ratios_format]
            }
        )
        ideas_df = pd.DataFrame(json.loads(response_ideas.text))
        if ideas_df.empty:
            print("   Lỗi: Không tạo được ý tưởng alpha nào.")
            return []
        print(f"   => Thành công! Tạo được {len(ideas_df)} ý tưởng.")

        # BƯỚC 2: CHUẨN HÓA CÔNG THỨC
        print(" -> Bước 2: Gọi GenAI để chuẩn hóa công thức sang định dạng WorldQuant...")
        # SỬA LỖI: Đổi 'generation_config' thành 'config'
        response_format = client.models.generate_content(
            model=name_model,
            contents=[ideas_df.to_json(orient="records", force_ascii=False), prompt_chuan_hoa],
            config={
                "response_mime_type": "application/json",
                "response_schema": list[format_of_format]
            }
        )
        format_df = pd.DataFrame(json.loads(response_format.text))
        if format_df.empty:
            print("   Lỗi: Không chuẩn hóa được công thức nào.")
            return []
        
        final_alphas = format_df['WorldQuant_Standard_Formula'].tolist()
        print(f"   => Thành công! Đã chuẩn hóa {len(final_alphas)} alpha.")
        return final_alphas[:so_luong]

    except Exception as e:
        print(f"Lỗi nghiêm trọng trong quá trình tạo alpha: {e}")
        # In thêm chi tiết lỗi nếu có từ API
        if hasattr(e, 'response'): print(f"Chi tiết response: {e.response.text}")
        return []

# --- Các hàm làm việc với Google Sheet (Giữ nguyên) ---
def ket_noi_google_sheet():
    print("\nĐang kết nối tới Google Sheets...")
    try:
        sheet_id = os.getenv('SHEET_ID')
        if not sheet_id: raise ValueError("Lỗi: SHEET_ID không có trong secret.")
        # Sử dụng file apisheet.json vừa được tạo
        gc = gspread.service_account(filename='./apisheet.json')
        spreadsheet = gc.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet('Results')
        print("=> Kết nối Google Sheets thành công.")
        return worksheet
    except Exception as e:
        print(f"Lỗi khi kết nối Google Sheets: {e}")
        return None

def lay_alpha_da_co(worksheet):
    print("\nĐọc lịch sử các alpha đã mô phỏng...")
    try:
        all_alphas = worksheet.col_values(1)
        existing_alphas = set(all_alphas[1:])
        print(f"=> Tìm thấy {len(existing_alphas)} alpha đã tồn tại.")
        return existing_alphas
    except Exception as e:
        print(f"Lỗi khi đọc lịch sử alpha: {e}")
        return set()

def ghi_ket_qua_len_google_sheet(worksheet, ket_qua_df):
    print("\nBắt đầu ghi kết quả lên Google Sheets...")
    if ket_qua_df.empty:
        print("Không có kết quả mới để ghi.")
        return
    try:
        data_to_append = ket_qua_df.values.tolist()
        worksheet.append_rows(data_to_append, value_input_option='USER_ENTERED')
        print(f"=> Đã ghi thành công {len(data_to_append)} dòng mới.")
    except Exception as e:
        print(f"Lỗi khi ghi kết quả: {e}")

# --- HÀM CHẠY CHÍNH ---
if __name__ == "__main__":
    try:
        # 1. Chuẩn bị môi trường
        tao_cac_file_can_thiet()

        # 2. Kết nối Google Sheet và đọc lịch sử
        results_ws = ket_noi_google_sheet()
        if not results_ws: exit(1)
        alpha_da_co = lay_alpha_da_co(results_ws)

        # 3. Tạo Alpha mới
        danh_sach_alpha_ung_vien = tao_alpha_moi(so_luong=10)
        if not danh_sach_alpha_ung_vien:
            print("\nKhông tạo được alpha mới. Kết thúc.")
            exit(0)
            
        # 4. Lọc bỏ alpha trùng lặp
        alpha_thuc_su_moi = [alpha for alpha in danh_sach_alpha_ung_vien if alpha and alpha not in alpha_da_co]
        print(f"\n=> Sau khi lọc, có {len(alpha_thuc_su_moi)} alpha thực sự mới cần mô phỏng.")
        print(alpha_thuc_su_moi)

        if not alpha_thuc_su_moi:
            print("\nKhông có alpha mới nào để chạy. Kết thúc chương trình.")
        else:
            # 5. Chạy mô phỏng
            print("\nBắt đầu khởi tạo WorldQuant và chạy mô phỏng hàng loạt...")
            wq = WorldQuant()
            ket_qua_list = wq.simulate(alpha_thuc_su_moi)
            
            # 6. Ghi kết quả
            if ket_qua_list:
                print("\n--- MÔ PHỎNG HOÀN TẤT ---")
                cols = ['expression','sharpe', 'turnover','fitness','returns','drawdown','margin',
                        'longCount','shortCount','weight','sub_univese','universe','delay',
                        'decay','neutralization','truncation','score','code']
                results_df = pd.DataFrame(ket_qua_list, columns=cols)
                print("Kết quả nhận được:")
                print(results_df)
                ghi_ket_qua_len_google_sheet(results_ws, results_df)
            else:
                print("\nKhông nhận được kết quả nào từ mô phỏng.")

    except Exception as e:
        print(f"\n!!! LỖI NGHIÊM TRỌNG TRONG QUY TRÌNH CHÍNH: {e}")
        exit(1)
    finally:
        # 7. Dọn dẹp
        print("\nBắt đầu dọn dẹp các file tạm...")
        for filename in ['credential.json', 'keyapi.json', 'apisheet.json']:
            if os.path.exists(filename):
                os.remove(filename)
                print(f"Đã xóa file {filename}.")
        print("Quy trình kết thúc.")
