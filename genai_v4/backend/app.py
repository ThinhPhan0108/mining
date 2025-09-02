# backend/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import optimizer # Import module optimizer đã được sửa
import worldquant as wq # QUAN TRỌNG: Import file worldquant.py gốc của bạn

app = Flask(__name__)
CORS(app)

# --- TAB 1: AI GENERATE ALPHA ---
@app.route('/api/generate-alpha', methods=['POST'])
def generate_alpha():
    """API để tạo alpha từ text (giữ nguyên logic giả lập AI)."""
    data = request.json
    user_input = data.get('prompt', '')
    if "momentum" in user_input.lower():
        generated_alpha = "ts_rank(returns, 20)"
    else:
        generated_alpha = "rank(close - open)"
    return jsonify({"alpha": generated_alpha})

# --- TAB 2: EXHAUSTIVE SEARCH ---
@app.route('/api/exhaustive-search', methods=['POST'])
def run_exhaustive_search():
    """API để vét cạn, gọi đến hàm trong optimizer.py mới."""
    data = request.json
    base_alpha = data.get('alpha', '')
    options = data.get('options', {})

    if not base_alpha:
        return jsonify({"error": "Cần nhập biểu thức alpha gốc!"}), 400

    # Gọi hàm exhaustive_search đã được cập nhật
    generated_alphas = optimizer.exhaustive_search(base_alpha, options)

    return jsonify({"generated_alphas": generated_alphas})

# --- TAB 3: SIMULATE LIST ---
@app.route('/api/simulate-list', methods=['POST'])
def run_simulation():
    """
    API để simulate, SỬ DỤNG CÁC HÀM TỪ FILE worldquant.py GỐC CỦA BẠN.
    """
    data = request.json
    alpha_list = data.get('alphas', [])
    settings = data.get('settings', {})
    auth_info = data.get('auth', {})

    if not alpha_list:
        return jsonify({"error": "Danh sách alpha không được để trống!"}), 400
    if not auth_info.get('username'):
        return jsonify({"error": "Cần nhập thông tin đăng nhập!"}), 400

    try:
        print("Đang gọi hàm simulate_alpha_list_v2 từ file worldquant.py của bạn...")
        results = wq.simulate_alpha_list_v2(
            alphas=alpha_list,
            username=auth_info.get('username'),
            password=auth_info.get('password'),
            sheet_id=settings.get('sheetId'),
            region=settings.get('region', 'USA'),
            universe=settings.get('universe', 'TOP3000'),
            decay=settings.get('decay', 4)
        )
        # ===================================================

        # Giả sử hàm của bạn trả về một list các dictionary kết quả
        return jsonify({"results": results})

    except Exception as e:
        print(f"Lỗi xảy ra khi gọi hàm từ worldquant.py: {e}")
        return jsonify({"error": f"Lỗi server khi thực thi simulation: {e}"}), 500

# Serve static files from the frontend directory
app.static_folder = 'frontend'
app.template_folder = 'frontend'

@app.route('/')
def index():
    """Serve the index.html file."""
    return app.send_static_file('index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
