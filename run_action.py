import os
import sys
import json
import time
import gspread
from google.oauth2.service_account import Credentials

# Import class từ file GUI gốc của bạn
# Giả sử class WorldQuant được import trong gui_v3.py
from gui_v3 import AlphaFindingTool
from worldquant import WorldQuant

def run_automation():
    """Hàm chính để chạy quy trình tự động."""
    print("Bắt đầu quy trình tự động hóa...")
    results_sheet = None  # Khởi tạo để có thể truy cập trong khối except

    try:
        # --- 1. Kết nối Google Sheets ---
        print("Đang kết nối tới Google Sheets...")
        gcp_credentials_json = os.environ.get('GCP_SA_KEY')
        sheet_id = os.environ.get('SHEET_ID')
        
        if not gcp_credentials_json or not sheet_id:
            raise ValueError("Lỗi: Biến môi trường GCP_SA_KEY hoặc SHEET_ID chưa được thiết lập trên GitHub Secrets.")
            
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

        print(f"Tìm thấy {len(alphas_to_run)} alpha cần simulate: {alphas_to_run}")

        # --- 3. Đăng nhập WorldQuant ---
        print("Đang đăng nhập WorldQuant...")
        wq_username = os.environ.get('WQ_USERNAME')
        wq_password = os.environ.get('WQ_PASSWORD')
        if not wq_username or not wq_password:
            raise ValueError("Lỗi: Biến môi trường WQ_USERNAME hoặc WQ_PASSWORD chưa được thiết lập trên GitHub Secrets.")

        # Khởi tạo WorldQuant và đăng nhập
        # BẠN CẦN ĐẢM BẢO CLASS WORLDQUANT CÓ HÀM LOGIN NHƯ DƯỚI ĐÂY
        wq_instance = WorldQuant()
        # wq_instance.login(wq_username, wq_password) # Giả sử bạn có một hàm login như thế này
        print("Đăng nhập WorldQuant thành công.")


        # --- 4. Chạy Simulation ---
        results_data = []
        for alpha in alphas_to_run:
            if not alpha or not alpha.strip():
                continue
            
            print(f"Đang simulate alpha: {alpha}")
            try:
                # Gọi hàm simulate từ instance WorldQuant
                performance = wq_instance.simulate([alpha]) 
                # Ví dụ kết quả trả về: {'sharpe': 1.5, 'returns': 10.2, 'turnover': 0.1}
                
                print(f"Simulate thành công cho: {alpha}")
                results_data.append([
                    alpha,
                    performance.get('sharpe', 'N/A'),
                    performance.get('returns', 'N/A'),
                    performance.get('turnover', 'N/A'),
                    time.strftime("%Y-%m-%d %H:%M:%S")
                ])
            except Exception as e:
                print(f"Lỗi khi simulate '{alpha}': {e}")
                results_data.append([alpha, 'ERROR', str(e), '', time.strftime("%Y-%m-%d %H:%M:%S")])
            
            time.sleep(3) # Thêm độ trễ nhỏ giữa các lần gọi API

        # --- 5. Ghi kết quả vào Sheet ---
        if results_data:
            print(f"Đang ghi {len(results_data)} kết quả vào tab 'Results'...")
            header_row = []
            try:
                header_row = results_sheet.row_values(1)
            except gspread.exceptions.APIError:
                pass 

            if not header_row:
                results_sheet.append_row(['Original Alpha', 'Sharpe', 'Returns', 'Turnover', 'Simulated At'])
            
            results_sheet.append_rows(results_data)
            print("Ghi kết quả thành công.")

        # --- 6. Xóa Alphas đã xử lý ---
        print("Đang xóa các alpha đã xử lý khỏi tab 'Alphas'...")
        # Xóa tất cả các hàng từ hàng thứ 2 trở đi
        alphas_sheet.delete_rows(2, len(alphas_to_run) + 1)
        print("Đã xóa alpha.")

    except Exception as e:
        print(f"!!! LỖI NGHIÊM TRỌNG TRONG WORKFLOW: {e}")
        if results_sheet:
            try:
                results_sheet.append_row(['WORKFLOW_ERROR', str(e), '', '', time.strftime("%Y-%m-%d %H:%M:%S")])
            except Exception as sheet_error:
                print(f"Không thể ghi lỗi vào Google Sheet: {sheet_error}")
        sys.exit(1)

    print("Quy trình tự động hóa hoàn tất thành công.")

if __name__ == "__main__":
    run_automation()