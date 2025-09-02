import os
import sys
import json
import time
import gspread
from google.oauth2.service_account import Credentials
from worldquant import WorldQuant

def run_automation():
    """Hàm chính để chạy quy trình tự động."""
    print("Bắt đầu quy trình tự động hóa...")
    results_sheet = None

    # =================== THAY ĐỔI 1: ĐỊNH NGHĨA TẤT CẢ CÁC CỘT ===================
    # Liệt kê tất cả các cột bạn muốn ghi ra sheet theo đúng thứ tự
    HEADERS = [
        'alpha', 'sharpe', 'returns', 'turnover', 'fitness', 'drawdown', 
        'margin', 'longCount', 'shortCount', 'score', 'code' 
        # Thêm các cột cài đặt nếu cần, ví dụ: 'delay', 'decay'...
    ]
    # ===========================================================================

    try:
        # --- 1. Kết nối Google Sheets ---
        print("Đang kết nối tới Google Sheets...")
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
        print(f"Tìm thấy {len(alphas_to_run)} alpha cần simulate.")

        # --- 3. Đăng nhập WorldQuant ---
        print("Đang đăng nhập WorldQuant...")
        wq_username = os.environ.get('WQ_USERNAME')
        wq_password = os.environ.get('WQ_PASSWORD')
        if not wq_username or not wq_password:
            raise ValueError("Lỗi: Biến môi trường WQ_USERNAME hoặc WQ_PASSWORD chưa được thiết lập.")
        
        credentials = {"username": wq_username, "password": wq_password}
        with open("credential.json", "w") as f:
            json.dump(credentials, f)
        print("Đã tạo file credential.json tạm thời.")
        
        wq_instance = WorldQuant()
        print("Đăng nhập WorldQuant thành công.")

        # --- 4. Chạy Simulation ---
        results_data = []
        for alpha in alphas_to_run:
            if not alpha or not alpha.strip():
                continue
            
            print(f"Đang simulate alpha: {alpha}")
            try:
                # Giả sử hàm simulate trả về một dictionary
                performance = wq_instance.simulate([alpha]) 
                # Ví dụ: performance = {'sharpe': 1.5, 'returns': 10.2, ...}
                print(f"Simulate thành công cho: {alpha}")

                # =================== THAY ĐỔI 2: XỬ LÝ KẾT QUẢ DẠNG DICTIONARY ===================
                # Tạo một hàng kết quả theo đúng thứ tự của HEADERS
                result_row = [
                    performance.get('alpha', alpha), # Lấy alpha từ kết quả, nếu không có thì dùng alpha gốc
                    performance.get('sharpe', 'N/A'),
                    performance.get('returns', 'N/A'),
                    performance.get('turnover', 'N/A'),
                    performance.get('fitness', 'N/A'),
                    performance.get('drawdown', 'N/A'),
                    performance.get('margin', 'N/A'),
                    performance.get('longCount', 'N/A'),
                    performance.get('shortCount', 'N/A'),
                    performance.get('score', 'N/A'),
                    performance.get('code', 'N/A'),
                    time.strftime("%Y-%m-%d %H:%M:%S") # Thêm cột thời gian ở cuối
                ]
                results_data.append(result_row)
                # ===================================================================================

            except Exception as e:
                print(f"Lỗi khi simulate '{alpha}': {e}")
                # Ghi lỗi vào hàng tương ứng
                error_row = [alpha] + ['ERROR'] * (len(HEADERS) - 1) + [str(e), time.strftime("%Y-%m-%d %H:%M:%S")]
                results_data.append(error_row)
            
            time.sleep(3)

        # --- 5. Ghi kết quả vào Sheet ---
        if results_data:
            print(f"Đang ghi {len(results_data)} kết quả vào tab 'Results'...")
            header_row = []
            try:
                header_row = results_sheet.row_values(1)
            except gspread.exceptions.APIError:
                pass 

            # =================== THAY ĐỔI 3: GHI HEADER ĐẦY ĐỦ ===================
            if not header_row:
                # Ghi header đầy đủ cùng với cột thời gian
                results_sheet.append_row(HEADERS + ["Simulated At"])
            # ======================================================================
            
            results_sheet.append_rows(results_data)
            print("Ghi kết quả thành công.")

        # --- 6. Xóa Alphas đã xử lý ---
        print("Đang xóa các alpha đã xử lý khỏi tab 'Alphas'...")
        alphas_sheet.delete_rows(2, len(alphas_to_run) + 1)
        print("Đã xóa alpha.")

    except Exception as e:
        print(f"!!! LỖI NGHIÊM TRỌNG TRONG WORKFLOW: {e}")
        if results_sheet:
            try:
                results_sheet.append_row(['WORKFLOW_ERROR', str(e)] + [''] * (len(HEADERS) - 2) + [time.strftime("%Y-%m-%d %H:%M:%S")])
            except Exception as sheet_error:
                print(f"Không thể ghi lỗi vào Google Sheet: {sheet_error}")
        sys.exit(1)

    print("Quy trình tự động hóa hoàn tất thành công.")

if __name__ == "__main__":
    run_automation()
