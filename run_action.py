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

    # Dựa theo logic trong GUI, BATCH_SIZE = 3
    BATCH_SIZE = 3
    SLEEP_TIME = 1  # Giảm thời gian chờ giữa các lô

    # Danh sách các cột header cho Google Sheet
    # BẠN HÃY KIỂM TRA LẠI THỨ TỰ NÀY LẦN CUỐI CHO ĐÚNG VỚI HÀM locate_alpha
    HEADERS = [
        'alpha', 'sharpe', 'turnover', 'fitness', 'returns', 'drawdown', 
        'margin', 'longCount', 'shortCount', 'weight', 'sub_universe', 
        'universe', 'delay', 'decay', 'neutralization', 'truncation', 
        'score', 'code'
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

        # --- 2. Đọc và Tạo Alphas ---
        records = alphas_sheet.get_all_records()
        if not records:
            print("Không có alpha nào trong tab 'Alphas' để xử lý. Kết thúc.")
            return
        
        print(f"Tìm thấy {len(records)} alpha GỐC cần xử lý.")
        optimizer = Optimize()
        all_generated_alphas = []

        for record in records:
            base_alpha = record.get('Alpha')
            options_str = record.get('Options', '')
            if not base_alpha: continue

            option_items = [opt.strip().lower() for opt in options_str.split(',')] if options_str else ["fields", "operator", "daily&group", "setting"]
            
            print(f"Đang tạo biến thể cho: '{base_alpha}' với options: {option_items}")
            generated_list = optimizer.complete_search(base_alpha, option_items)
            all_generated_alphas.extend(generated_list)
            print(f"-> Tạo thành công {len(generated_list)} biến thể.")
        
        total_alphas = len(all_generated_alphas)
        if total_alphas == 0:
            print("Không tạo được biến thể nào. Kết thúc.")
            alphas_sheet.delete_rows(2, len(records) + 1)
            return

        print(f"\nTổng cộng có {total_alphas} alpha sẽ được simulate theo từng lô {BATCH_SIZE} alpha.")

        # --- 3. Đăng nhập WorldQuant ---
        print("\nĐang đăng nhập WorldQuant...")
        wq_username = os.environ.get('WQ_USERNAME')
        wq_password = os.environ.get('WQ_PASSWORD')
        if not wq_username or not wq_password:
            raise ValueError("Lỗi: Biến môi trường WQ_USERNAME hoặc WQ_PASSWORD chưa được thiết lập.")
        
        credentials = {"username": wq_username, "password": wq_password}
        with open("credential.json", "w") as f: json.dump(credentials, f)
        
        wq_instance = WorldQuant()
        print("Đăng nhập WorldQuant thành công.")

        # --- 4. Chạy Simulation THEO LÔ ---
        results_data = []
        for i in range(0, total_alphas, BATCH_SIZE):
            batch = all_generated_alphas[i:i + BATCH_SIZE]
            print(f"[{i + 1}-{min(i + BATCH_SIZE, total_alphas)}/{total_alphas}] Đang simulate lô: {batch}")
            
            try:
                # Gọi simulate cho cả lô
                performance_batch_list = wq_instance.simulate(batch)
                
                if not performance_batch_list:
                    raise ValueError("Kết quả trả về cho lô rỗng.")
                
                print(f"-> Simulate lô thành công, nhận được {len(performance_batch_list)} kết quả.")

                # Lặp qua từng kết quả trong lô trả về
                for p in performance_batch_list:
                    if p and len(p) >= len(HEADERS):
                        # Cắt bớt kết quả để khớp với số lượng header
                        result_row = p[:len(HEADERS)] + [time.strftime("%Y-%m-%d %H:%M:%S")]
                        results_data.append(result_row)
                    else:
                        # Ghi nhận kết quả không hợp lệ nếu có
                        results_data.append([p[0] if p else 'Unknown Alpha'] + ['INVALID_RESULT_FORMAT'] * (len(HEADERS) - 1) + [time.strftime("%Y-%m-%d %H:%M:%S")])

            except Exception as e:
                print(f"-> Lỗi khi simulate lô bắt đầu bằng '{batch[0]}': {e}")
                for alpha in batch:
                    error_row = [alpha, 'BATCH_ERROR', str(e)] + [''] * (len(HEADERS) - 3) + ['', '', time.strftime("%Y-%m-%d %H:%M:%S")]
                    results_data.append(error_row)
            
            time.sleep(SLEEP_TIME)

        # --- 5 & 6. Ghi kết quả và Xóa Alphas GỐC ---
        if results_data:
            print(f"\nĐang ghi {len(results_data)} kết quả vào tab 'Results'...")
            header_row = []
            try: header_row = results_sheet.row_values(1)
            except gspread.exceptions.APIError: pass 
            if not header_row:
                results_sheet.append_row(HEADERS + ["Simulated At"])
            
            results_sheet.append_rows(results_data, value_input_option='USER_ENTERED')
            print("Ghi kết quả thành công.")

        print("Đang xóa các alpha GỐC đã xử lý khỏi tab 'Alphas'...")
        alphas_sheet.delete_rows(2, len(records) + 1)
        print("Đã xóa alpha.")

    except Exception as e:
        print(f"!!! LỖI NGHIÊM TRỌNG TRONG WORKFLOW: {e}")
        if results_sheet:
            try: results_sheet.append_row(['WORKFLOW_ERROR', str(e)] + [''] * (len(HEADERS) - 1) + [time.strftime("%Y-%m-%d %H:%M:%S")])
            except Exception as sheet_error: print(f"Không thể ghi lỗi vào Google Sheet: {sheet_error}")
        sys.exit(1)

    print("\nQuy trình tự động hóa hoàn tất thành công.")

if __name__ == "__main__":
    run_automation()
