import os
import sys
import json
import time
import gspread
from google.oauth2.service_account import Credentials
from worldquant import WorldQuant

def run_automation():
    print("Bắt đầu quy trình tự động hóa...")
    results_sheet = None

    # Danh sách các cột header cho Google Sheet
    HEADERS = [
        'alpha', 'sharpe', 'returns', 'turnover', 'fitness', 'drawdown', 
        'margin', 'longCount', 'shortCount', 'pass_fail_status', 'another_status', 
        'universe', 'field_1', 'field_2', 'neutralization', 'field_3', 'field_4', 'code'
    ]

    try:
        # --- 1. Kết nối Google Sheets ---
        print("Đang kết nối tới Google Sheets...")
        # ... (Phần này giữ nguyên, không cần sửa) ...
        gcp_credentials_json = os.environ.get('GCP_SA_KEY')
        sheet_id = os.environ.get('SHEET_ID')
        if not gcp_credentials_json or not sheet_id:
            raise ValueError("Lỗi: Biến môi trường GCP_SA_KEY hoặc SHEET_ID chưa được thiết lập.")
        
        creds_dict = json.loads(gcp_credentials_json)
        scopes = ['https://www.googleapis.com/auth/spreadsheets']
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        
        spreadsheet = client.open_by_key(sheet_id)
        alphas_sheet = spreadsheet.worksheet("Alphas")
        results_sheet = spreadsheet.worksheet("Results")
        print("Kết nối Google Sheets thành công.")


        # --- 2. Đọc Alphas từ Sheet ---
        alphas_to_run = alphas_sheet.col_values(1)[1:]
        if not alphas_to_run:
            print("Không có alpha nào trong tab 'Alphas' để xử lý. Kết thúc.")
            return
        total_alphas = len(alphas_to_run)
        print(f"Tìm thấy {total_alphas} alpha cần simulate.")

        # --- 3. Đăng nhập WorldQuant ---
        # ... (Phần này giữ nguyên, không cần sửa) ...
        print("Đang đăng nhập WorldQuant...")
        wq_username = os.environ.get('WQ_USERNAME')
        wq_password = os.environ.get('WQ_PASSWORD')
        if not wq_username or not wq_password:
            raise ValueError("Lỗi: Biến môi trường WQ_USERNAME hoặc WQ_PASSWORD chưa được thiết lập.")
        
        credentials = {"username": wq_username, "password": wq_password}
        with open("credential.json", "w") as f:
            json.dump(credentials, f)
        
        wq_instance = WorldQuant()
        print("Đăng nhập WorldQuant thành công.")

        # --- 4. Chạy Simulation ---
        results_data = []
        # enumerate để lấy cả index (i) và giá trị (alpha)
        for i, alpha in enumerate(alphas_to_run):
            if not alpha or not alpha.strip():
                continue
            
            # =================== THÊM PRINT TIẾN TRÌNH ===================
            print(f"[{i + 1}/{total_alphas}] Đang simulate alpha: {alpha}")
            # =============================================================

            try:
                performance_list = wq_instance.simulate([alpha]) 
                
                # Kiểm tra kết quả trả về có hợp lệ không
                if not performance_list or not isinstance(performance_list, list) or not performance_list[0]:
                    raise ValueError("Kết quả trả về không hợp lệ hoặc rỗng.")
                
                # Lấy tuple kết quả từ trong list
                p = performance_list[0] 
                
                print(f"Simulate thành công cho: {alpha}")

                # =================== SỬA LỖI PERFORMANCE ===================
                # Xây dựng hàng kết quả bằng cách lấy theo vị trí (index) của tuple `p`
                # BẠN CẦN KIỂM TRA LẠI THỨ TỰ NÀY CÓ ĐÚNG VỚI DỮ LIỆU CỦA MÌNH KHÔNG
                result_row = [
                    p[0],  # alpha
                    p[1],  # sharpe
                    p[2],  # returns
                    p[3],  # turnover
                    p[4],  # fitness
                    p[5],  # drawdown
                    p[6],  # margin
                    p[7],  # longCount
                    p[8],  # shortCount
                    p[9],  # pass_fail_status
                    p[10], # another_status
                    p[11], # universe
                    p[12], # field_1
                    p[13], # field_2
                    p[14], # neutralization
                    p[15], # field_3
                    p[16], # field_4
                    p[17], # code
                    time.strftime("%Y-%m-%d %H:%M:%S")
                ]
                results_data.append(result_row)
                # ===========================================================

            except Exception as e:
                print(f"Lỗi khi simulate '{alpha}': {e}")
                error_row = [alpha] + ['ERROR'] * (len(HEADERS) -1) + [str(e), time.strftime("%Y-%m-%d %H:%M:%S")]
                results_data.append(error_row)
            
            time.sleep(3)

        # --- 5 & 6. Ghi kết quả và Xóa Alphas ---
        # ... (Phần này giữ nguyên, không cần sửa) ...
        if results_data:
            print(f"Đang ghi {len(results_data)} kết quả vào tab 'Results'...")
            header_row = []
            try: header_row = results_sheet.row_values(1)
            except gspread.exceptions.APIError: pass 
            if not header_row:
                results_sheet.append_row(HEADERS + ["Simulated At"])
            
            results_sheet.append_rows(results_data)
            print("Ghi kết quả thành công.")

        print("Đang xóa các alpha đã xử lý khỏi tab 'Alphas'...")
        alphas_sheet.delete_rows(2, len(alphas_to_run) + 1)
        print("Đã xóa alpha.")

    except Exception as e:
        print(f"!!! LỖI NGHIÊM TRỌNG TRONG WORKFLOW: {e}")
        if results_sheet:
            try: results_sheet.append_row(['WORKFLOW_ERROR', str(e)] + [''] * (len(HEADERS) - 2) + [time.strftime("%Y-%m-%d %H:%M:%S")])
            except Exception as sheet_error: print(f"Không thể ghi lỗi vào Google Sheet: {sheet_error}")
        sys.exit(1)

    print("Quy trình tự động hóa hoàn tất thành công.")

if __name__ == "__main__":
    run_automation()
