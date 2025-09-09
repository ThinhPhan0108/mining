import sys
import os
# Lấy đường dẫn thư mục cha
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# Thêm vào sys.path nếu chưa có
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from google import genai
from google.genai import types
from pydantic import BaseModel
import pathlib
import json
import pandas as pd
import datetime
import gspread
from time import sleep
from worldquant import WorldQuant
import csv
import random
import PyPDF2

class GenAI:
    def __init__(self, index_keya=1):
        self.date = datetime.datetime.now().strftime('%d-%m-%Y')
        self.process_name = 'version_2.2'
        
        data_key = self.read_json('./keyapi.json')
        self.list_key = data_key['list_key']

        self.client = genai.Client(api_key=self.list_key[index_keya])
        self.name_model = "gemini-2.5-flash"

        self.system_prompt = open("./genai_v3/prompt/system.txt", "r", encoding="utf-8").read()
        
        # Lưu trữ nội dung PDF đã đọc
        self.pdf_content = ""

    # Đọc file JSON
    def read_json(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)  # Tải dữ liệu JSON
        return data
    
    def extract_text_from_pdf(self, pdf_path):
        """
        Trích xuất văn bản từ file PDF
        """
        try:
            text = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Đọc từng trang
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() + "\n"
            
            return text.strip()
        except Exception as e:
            print(f"Lỗi khi đọc file PDF {pdf_path}: {str(e)}")
            return ""
    
    def load_pdf_files(self, pdf_paths):
        """
        Tải một hoặc nhiều file PDF và trích xuất nội dung
        pdf_paths: có thể là string (một file) hoặc list (nhiều file)
        """
        if isinstance(pdf_paths, str):
            pdf_paths = [pdf_paths]
        
        all_content = ""
        loaded_files = []
        
        for pdf_path in pdf_paths:
            if os.path.exists(pdf_path) and pdf_path.lower().endswith('.pdf'):
                content = self.extract_text_from_pdf(pdf_path)
                if content:
                    all_content += f"\n--- Nội dung từ file: {os.path.basename(pdf_path)} ---\n"
                    all_content += content + "\n"
                    loaded_files.append(os.path.basename(pdf_path))
                    print(f"✓ Đã tải file: {os.path.basename(pdf_path)}")
                else:
                    print(f"✗ Không thể đọc nội dung từ file: {os.path.basename(pdf_path)}")
            else:
                print(f"✗ File không tồn tại hoặc không phải PDF: {pdf_path}")
        
        if all_content:
            self.pdf_content = all_content
            print(f"\n📚 Đã tải thành công {len(loaded_files)} file PDF: {', '.join(loaded_files)}")
        else:
            print("\n⚠️ Không có file PDF nào được tải thành công")
        
        return len(loaded_files) > 0
    
    def clear_pdf_content(self):
        """
        Xóa nội dung PDF đã tải
        """
        self.pdf_content = ""
        print("🗑️ Đã xóa tất cả nội dung PDF")
    
    def genai_financial_ratios(self, prompt):
        """
        Xử lý prompt với hoặc không có nội dung PDF
        """
        # Nếu có nội dung PDF, thêm vào prompt
        if self.pdf_content:
            enhanced_prompt = f"""
Dựa trên nội dung tài liệu PDF được cung cấp dưới đây, hãy trả lời câu hỏi:

=== NỘI DUNG TÀI LIỆU ===
{self.pdf_content}

=== CÂU HỎI ===
{prompt}

Hãy trả lời dựa trên thông tin từ tài liệu. Nếu không tìm thấy thông tin liên quan trong tài liệu, hãy thông báo và trả lời dựa trên kiến thức chung.
"""
        else:
            enhanced_prompt = prompt
        
        response = self.client.models.generate_content(
            model=self.name_model,
            contents=enhanced_prompt,
            config={
                "system_instruction": self.system_prompt
            }
        )
        return response.text

def main():
    """
    Hàm chính để chạy chatbot với chức năng PDF
    """
    chatbot = GenAI(0)
    
    print("=" * 60)
    print("🤖 CHATBOT HỖ TRỢ ĐỌC PDF")
    print("=" * 60)
    print("📝 Lệnh có sẵn:")
    print("  - 'load pdf': Tải file PDF")
    print("  - 'clear pdf': Xóa tất cả PDF đã tải")
    print("  - 'status': Kiểm tra trạng thái PDF")
    print("  - 'exit' hoặc 'quit': Thoát chương trình")
    print("  - Hoặc nhập câu hỏi trực tiếp để chat")
    print("=" * 60)
    
    while True:
        user_input = input('\n💬 Bạn: ').strip()
        
        if user_input.lower() in ['exit', 'quit', 'thoát']:
            print("👋 Tạm biệt!")
            break
            
        elif user_input.lower() == 'load pdf':
            print("\n📁 Nhập đường dẫn file PDF (hoặc nhiều file, cách nhau bởi dấu ';'):")
            pdf_input = input("📂 Đường dẫn: ").strip()
            
            if pdf_input:
                # Xử lý nhiều file PDF
                pdf_paths = [path.strip() for path in pdf_input.split(';') if path.strip()]
                chatbot.load_pdf_files(pdf_paths)
            else:
                print("⚠️ Chưa nhập đường dẫn file")
                
        elif user_input.lower() == 'clear pdf':
            chatbot.clear_pdf_content()
            
        elif user_input.lower() == 'status':
            if chatbot.pdf_content:
                lines = chatbot.pdf_content.count('\n')
                chars = len(chatbot.pdf_content)
                print(f"📊 Trạng thái: Đã tải PDF ({lines} dòng, {chars} ký tự)")
            else:
                print("📊 Trạng thái: Chưa tải PDF nào")
                
        elif user_input:
            print("\n🤔 Đang xử lý...")
            try:
                response = chatbot.genai_financial_ratios(user_input)
                print(f"\n🤖 Bot: {response}")
            except Exception as e:
                print(f"❌ Lỗi: {str(e)}")
        else:
            print("⚠️ Vui lòng nhập câu hỏi hoặc lệnh")

if __name__ == '__main__':
    main()