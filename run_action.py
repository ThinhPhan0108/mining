import os
import sys
import json
import time
import gspread
from google.oauth2.service_account import Credentials

# Import các class cần thiết từ project của bạn
from worldquant import WorldQuant
from optimize.optimize import Optimize

def run_automation():
    print("Bắt đầu quy trình tự động hóa...")
    results_sheet = None

    HEADERS = [
        'alpha', 'sharpe', 'returns', 'turnover', 'fitness', 'drawdown', 
        'margin', 'longCount', 'shortCount', 'score', 'code'
    ]

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

        # =================== THAY ĐỔI 1: ĐỌC CẢ 2 CỘT A VÀ B ===================
        # Lấy tất cả dữ liệu từ sheet, bỏ qua hàng tiêu đề
        records = alphas_sheet.get_all_records()
        if not records:
            print("Không có alpha nào trong tab 'Alphas' để xử lý. Kết thúc.")
            return
        
        print(f"Tìm thấy {len(records)} alpha GỐC cần xử lý.")
        # =======================================================================

        # --- TÍNH NĂNG MỚI: GENERATE ALPHAS VỚI TÙY CHỌN RIÊNG ---
        print("\nBắt đầu tạo các biến thể alpha...")
        optimizer = Optimize()
        all_generated_alphas = []

        for record in records:
            base_alpha = record.get('Alpha')
            options_str = record.get('Options', '') # Lấy options, mặc định là chuỗi rỗng
            
            if not base_alpha or not base_alpha.strip():
                continue

            # =================== THAY ĐỔI 2: XỬ LÝ OPTIONS ===================
            # Chuyển chuỗi options thành một list. Ví dụ: "Fields, Operator" -> ["fields", "operator"]
            # Nếu không có options, mặc định dùng tất cả.
            if options_str and options_str.strip():
                option_items = [opt.strip().lower() for opt in options_str.split(',')]
            else:
                # Mặc định dùng tất cả nếu cột Options để trống
                option_items = ["fields", "operator", "daily&group", "setting"]
            # =================================================================
            
            print(f"Đang tạo biến thể cho: '{base_alpha}' với options: {option_items}")
            try:
                generated_list = optimizer.complete_search(base_alpha, option_items)
                all_generated_alphas.extend(generated_list)
                print(f"-> Tạo thành công {len(generated_list)} biến thể.")
            except Exception as e:
                print(f"-> Lỗi khi tạo biến thể cho '{base_alpha}': {e}")
        
        if not all_generated_alphas:
            print("Không tạo được biến thể nào. Kết thúc workflow.")
            alphas_sheet.delete_rows(2, len(records) + 1)
            return
            
        total_alphas = len(all_generated_alphas)
        print(f"\nTổng cộng có {total_alphas} alpha sẽ được simulate.")

        # --- 3. Đăng nhập WorldQuant ---
        print("\nĐang đăng nhập WorldQuant...")
        # ... (Phần này giữ nguyên) ...
        wq_username = os.environ.get('WQ_USERNAME')
        wq_password = os.environ.get('WQ_PASSWORD')
        if not wq_username or not wq_password:
            raise ValueError("Lỗi: Biện môi trường WQ_USERNAME hoặc WQ_PASSWORD chưa được thiết lập.")
        
        credentials = {"username": wq_username, "password": wq_password}
        with open("credential.json", "w") as f: json.dump(credentials, f)
        
        wq_instance = WorldQuant()
        print("Đăng nhập WorldQuant thành công.")

        # --- 4. Chạy Simulation ---
        results_data = []
        for i, alpha in enumerate(all_generated_alphas):
            print(f"[{i + 1}/{total_alphas}] Đang simulate alpha: {alpha}")
            try:
                performance_list = wq_instance.simulate([alpha])
                if not performance_list or not isinstance(performance_list, list) or not performance_list[0]:
                    raise ValueError("Kết quả trả về không hợp lệ hoặc rỗng.")
                p = performance_list[0]
                result_row = [
                    p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7],
                    p[8], p[9], p[10], time.strftime("%Y-%m-%d %H:%M:%S")
                ]
                results_data.append(result_row)
            except Exception as e:
                print(f"Lỗi khi simulate '{alpha}': {e}")
                error_row = [alpha, 'ERROR', str(e)] + [''] * (len(HEADERS) - 3) + [time.strftime("%Y-%m-%d %H:%M:%S")]
                results_data.append(error_row)
            time.sleep(3)

        # --- 5 & 6. Ghi kết quả và Xóa Alphas GỐC---
        if results_data:
            print(f"\nĐang ghi {len(results_data)} kết quả vào tab 'Results'...")
            header_row = []
            try: header_row = results_sheet.row_values(1)
            except gspread.exceptions.APIError: pass 
            if not header_row:
                results_sheet.append_row(HEADERS + ["Simulated At"])
            
            results_sheet.append_rows(results_data)
            print("Ghi kết quả thành công.")

        print("Đang xóa các alpha GỐC đã xử lý khỏi tab 'Alphas'...")
        alphas_sheet.delete_rows(2, len(records) + 1)
        print("Đã xóa alpha.")

    except Exception as e:
        print(f"!!! LỖI NGHIÊM TRỌNG TRONG WORKFLOW: {e}")
        if results_sheet:
            try: results_sheet.append_row(['WORKFLOW_ERROR', str(e)] + [''] * (len(HEADERS) - 2) + [time.strftime("%Y-%m-%d %H:%M:%S")])
            except Exception as sheet_error: print(f"Không thể ghi lỗi vào Google Sheet: {sheet_error}")
        sys.exit(1)

    print("\nQuy trình tự động hóa hoàn tất thành công.")

if __name__ == "__main__":
    run_automation()
