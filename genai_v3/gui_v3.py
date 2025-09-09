import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sys
import pandas as pd
import threading
import json
import webbrowser
import time
import pickle

# Lấy đường dẫn thư mục cha
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# Thêm vào sys.path nếu chưa có
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from optimize.optimize import Optimize
from worldquant import WorldQuant
from genai_v3.chatgenai import GenAI

class AlphaFindingTool:
    def __init__(self):
        self.root = tk.Tk()
        self.setup_window()
        self.setup_styles()
        
        # Initialize instances
        self.genai_instance = GenAI()
        self.new_alphas = []  # Generated alphas
        self.selected_alphas = []  # Selected alphas for simulation
        
        # Simulation control
        self.simulation_running = False
        self.simulation_paused = False
        self.current_simulation_index = 0
        self.simulation_thread = None
        
        # Initialize status_label as None
        self.status_label = None
        self.create_gui()
        
    def setup_window(self):
        """Cấu hình cửa sổ chính"""
        self.root.title("Alpha Finding & Analysis Tool")
        self.root.geometry("1200x800")
        self.root.configure(bg='#f5f5f5')
        
        # Set minimum size
        self.root.minsize(1000, 600)
        
    def setup_styles(self):
        """Thiết lập style đơn giản"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Simple colors
        self.colors = {
            'bg': '#f5f5f5',
            'white': '#ffffff',
            'gray': '#666666',
            'light_gray': '#e0e0e0',
            'blue': '#4a90e2',
            'green': '#5cb85c',
            'red': '#d9534f',
            'dark': '#333333',
            'orange': '#ff8c00',
            'purple': '#9c27b0'
        }
        
        # Notebook styles
        style.configure('Tab.TNotebook', 
                       background=self.colors['bg'],
                       borderwidth=1)
        style.configure('Tab.TNotebook.Tab',
                       background=self.colors['light_gray'],
                       foreground=self.colors['dark'],
                       padding=[15, 8],
                       font=('Arial', 10))
        style.map('Tab.TNotebook.Tab',
                  background=[('selected', self.colors['white']),
                             ('active', '#ddd')])

    def create_gui(self):
        """Tạo giao diện chính"""
        # Header đơn giản
        header = tk.Frame(self.root, bg=self.colors['blue'], height=50)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        title_label = tk.Label(header, text="Alpha Finding & Analysis Tool", 
                              bg=self.colors['blue'], fg='white', 
                              font=('Arial', 14, 'bold'))
        title_label.pack(pady=12)
        
        # Main content
        main_frame = tk.Frame(self.root, bg=self.colors['bg'])
        main_frame.pack(expand=True, fill='both', padx=10, pady=10)
        
        # Notebook
        self.notebook = ttk.Notebook(main_frame, style='Tab.TNotebook')
        self.notebook.pack(expand=True, fill="both")
        
        # Create tabs
        self.create_genai_tab()
        self.create_complete_search_tab()
        self.create_simulate_tab()
        self.create_account_tab()
        self.create_help_tab()
        
        # Status bar
        self.create_status_bar()
        
    def create_genai_tab(self):
        """Tab GenAI đơn giản"""
        tab1 = tk.Frame(self.notebook, bg=self.colors['white'])
        self.notebook.add(tab1, text="AI Assistant")
        
        # PDF Control Panel
        pdf_frame = tk.LabelFrame(tab1, text="PDF Management", 
                                 bg=self.colors['white'], 
                                 font=('Arial', 10, 'bold'))
        pdf_frame.pack(fill='x', padx=10, pady=10)
        
        pdf_buttons = tk.Frame(pdf_frame, bg=self.colors['white'])
        pdf_buttons.pack(fill='x', padx=10, pady=10)
        
        self.pdf_load_btn = tk.Button(pdf_buttons, text="Load PDF Files",
                                     command=self.load_pdf_files,
                                     bg=self.colors['blue'], fg='white',
                                     font=('Arial', 9),
                                     relief='flat', padx=15, pady=5)
        self.pdf_load_btn.pack(side='left', padx=5)
        
        self.pdf_clear_btn = tk.Button(pdf_buttons, text="Clear PDFs",
                                      command=self.clear_pdf_files,
                                      bg=self.colors['red'], fg='white',
                                      font=('Arial', 9),
                                      relief='flat', padx=15, pady=5)
        self.pdf_clear_btn.pack(side='left', padx=5)
        
        self.pdf_status_label = tk.Label(pdf_buttons, text="Status: No PDFs loaded",
                                        bg=self.colors['white'], fg=self.colors['gray'],
                                        font=('Arial', 9))
        self.pdf_status_label.pack(side='right', padx=10)
        
        # Chat area
        chat_frame = tk.LabelFrame(tab1, text="Chat", 
                                  bg=self.colors['white'],
                                  font=('Arial', 10, 'bold'))
        chat_frame.pack(expand=True, fill='both', padx=10, pady=10)
        
        # Chat history
        chat_container = tk.Frame(chat_frame, bg=self.colors['white'])
        chat_container.pack(expand=True, fill='both', padx=10, pady=10)
        
        self.chat_history = tk.Text(chat_container, wrap="word", state="disabled",
                                   bg='#f8f8f8', font=('Arial', 10),
                                   relief='solid', bd=1)
        self.chat_history.pack(side='left', expand=True, fill='both')
        
        chat_scrollbar = ttk.Scrollbar(chat_container, orient="vertical", 
                                      command=self.chat_history.yview)
        chat_scrollbar.pack(side='right', fill='y')
        self.chat_history.configure(yscrollcommand=chat_scrollbar.set)
        
        # Input area
        input_frame = tk.Frame(chat_frame, bg=self.colors['white'])
        input_frame.pack(fill='x', padx=10, pady=10)
        
        self.user_input = tk.Entry(input_frame, font=('Arial', 10),
                                  relief='solid', bd=1)
        self.user_input.pack(side='left', expand=True, fill='x', padx=(0, 10))
        
        send_button = tk.Button(input_frame, text="Send",
                               command=self.send_message_thread,
                               bg=self.colors['green'], fg='white',
                               font=('Arial', 10),
                               relief='flat', padx=20, pady=5)
        send_button.pack(side='right')
        
        # Bind Enter key
        self.user_input.bind("<Return>", lambda event: self.send_message_thread())

    def create_complete_search_tab(self):
        """Tab Complete Search - Enhanced with separated tables"""
        tab2 = tk.Frame(self.notebook, bg=self.colors['white'])
        self.notebook.add(tab2, text="Complete Search")
        
        # Main container with padding
        main_container = tk.Frame(tab2, bg=self.colors['white'])
        main_container.pack(expand=True, fill='both', padx=15, pady=15)
        
        # ========== INPUT SECTION ==========
        input_section = tk.LabelFrame(main_container, 
                                     text="Alpha Input & Search Options", 
                                     bg=self.colors['white'],
                                     font=('Arial', 11, 'bold'),
                                     fg=self.colors['dark'],
                                     relief='solid',
                                     bd=1,
                                     padx=5,
                                     pady=5)
        input_section.pack(fill='x', pady=(0, 5), expand=False)
        
        # Alpha input
        input_label_frame = tk.Frame(input_section, bg=self.colors['white'])
        input_label_frame.pack(fill='x', pady=(5, 10))
        
        tk.Label(input_label_frame, 
                text="Enter Alpha Formula:",
                bg=self.colors['white'], 
                font=('Arial', 10, 'bold'),
                fg=self.colors['dark']).pack(anchor='w')
        
        tk.Label(input_label_frame, 
                text="Example: rank(close/delay(close,1))",
                bg=self.colors['white'], 
                font=('Arial', 9, 'italic'),
                fg=self.colors['gray']).pack(anchor='w', pady=(2, 0))
        
        # Entry with better styling
        entry_frame = tk.Frame(input_section, bg=self.colors['white'])
        entry_frame.pack(fill='x', pady=(0, 15))
        
        self.entry_2 = tk.Entry(entry_frame, 
                               width=30,
                               font=('Consolas', 10),
                               relief='solid', 
                               bd=1,
                               bg='#f8f9fa',
                               highlightthickness=1,
                               highlightcolor=self.colors['blue'])
        self.entry_2.pack(fill='x', ipady=4)
        
        # Options section
        options_section = tk.LabelFrame(input_section,
                                       text="Generation Options",
                                       bg=self.colors['white'],
                                       font=('Arial', 10, 'bold'),
                                       fg=self.colors['dark'],
                                       relief='flat',
                                       bd=0)
        options_section.pack(fill='x')
        
        # Container for checkboxes
        checkbox_container = tk.Frame(options_section, bg=self.colors['white'])
        checkbox_container.pack(fill='x', padx=5, pady=5)
        
        # Checkboxes
        items = ["fields", "operator", "daily&group", "setting"]
        self.vars = {}
        
        # Create 2 rows for checkboxes
        row1 = tk.Frame(checkbox_container, bg=self.colors['white'])
        
        row2 = tk.Frame(checkbox_container, bg=self.colors['white'])
        
        
        for i, item in enumerate(items):
            var = tk.BooleanVar()
            chk = tk.Checkbutton(checkbox_container, 
                                text=item.title(),
                                variable=var,
                                bg=self.colors['white'], 
                                font=('Arial', 9))
            chk.pack(side='left', padx=10)  # Bố trí ngang, đơn giản
            self.vars[item] = var
        
        # Generate button
        generate_btn_frame = tk.Frame(input_section, bg=self.colors['white'])
        generate_btn_frame.pack(fill='x', pady=(10, 5))
        
        self.btn_ok = tk.Button(generate_btn_frame, 
                               text="Generate Variations",
                               command=self.run_enter_ok_in_thread,
                               bg='#007bff', 
                               fg='white',
                               font=('Arial', 10),
                               relief='flat', 
                               padx=15, 
                               pady=5,
                               cursor='hand2',
                               activebackground='#0056b3')
        self.btn_ok.pack(side='right')
        
        btn_clear = tk.Button(generate_btn_frame, 
                             text="Clear All",
                             command=self.remove_display,
                             bg='#dc3545', 
                             fg='white',
                             font=('Arial', 10),
                             relief='flat', 
                             padx=12, 
                             pady=5,
                             cursor='hand2',
                             activebackground='#c82333')
        btn_clear.pack(side="right", padx=(0, 5))
        
        self.progress_label = tk.Label(generate_btn_frame, 
                                      text="Ready to generate variations...",
                                      bg=self.colors['white'], 
                                      fg=self.colors['gray'],
                                      font=('Arial', 9))
        self.progress_label.pack(side='left')
        
        # ========== DUAL TABLE LAYOUT ==========
        tables_container = tk.Frame(main_container, bg=self.colors['white'])
        tables_container.pack(expand=True, fill='both')
        
        # ========== LEFT SIDE - GENERATED ALPHAS ==========
        left_panel = tk.LabelFrame(tables_container, 
                                  text="Generated Alpha Variations", 
                                  bg=self.colors['white'],
                                  font=('Arial', 11, 'bold'),
                                  fg=self.colors['dark'],
                                  relief='solid',
                                  bd=1,
                                  padx=5,
                                  pady=5)
        left_panel.pack(side='left', expand=False, fill='both', padx=(0, 5))
        left_panel.pack_propagate(False) # Ngăn panel co lại theo nội dung
        left_panel.config(width=700) # Đặt chiều rộng cố định
        
        # Generated alphas header
        gen_header = tk.Frame(left_panel, bg=self.colors['white'])
        gen_header.pack(fill='x', padx=5, pady=3)
        
        self.results_info_label = tk.Label(gen_header, 
                                          text="Generated: 0 variations", 
                                          bg=self.colors['white'], 
                                          fg=self.colors['gray'],
                                          font=('Arial', 9))
        self.results_info_label.pack(side='left')
        
        select_all_btn = tk.Button(gen_header, text="Select All",
                                  command=self.select_all_generated,
                                  bg=self.colors['blue'], fg='white',
                                  font=('Arial', 8),
                                  relief='flat', padx=10, pady=3)
        select_all_btn.pack(side='right', padx=5)
        
        # Generated alphas canvas
        gen_canvas_container = tk.Frame(left_panel, bg=self.colors['white'])
        gen_canvas_container.pack(expand=True, fill='both', padx=10, pady=(0, 10))
        
        self.canvas = tk.Canvas(gen_canvas_container, 
                               bg='#f8f9fa', 
                               relief='solid', 
                               bd=1,
                               highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        
        self.scrollbar = ttk.Scrollbar(gen_canvas_container, 
                                      orient="vertical", 
                                      command=self.canvas.yview)
        self.scrollbar.pack(side="right", fill="y")
        
        self.area_2 = tk.Frame(self.canvas, bg='#f8f9fa')
        self.canvas.create_window((0, 0), window=self.area_2, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Update scrollregion function
        def update_scrollregion(event=None):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        self.area_2.bind("<Configure>", update_scrollregion)
        
        # Mouse wheel scrolling
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def _bind_mousewheel(event):
            self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        def _unbind_mousewheel(event):
            self.canvas.unbind_all("<MouseWheel>")
        
        self.canvas.bind('<Enter>', _bind_mousewheel)
        self.canvas.bind('<Leave>', _unbind_mousewheel)
        
        # ========== RIGHT SIDE - SELECTED FOR SIMULATION ==========
        right_panel = tk.LabelFrame(tables_container, 
                                   text="Selected for Simulation", 
                                   bg=self.colors['white'],
                                   font=('Arial', 11, 'bold'),
                                   fg=self.colors['purple'],
                                   relief='solid',
                                   bd=1,
                                   padx=5,
                                   pady=5)
        right_panel.pack(side='right', expand=True, fill='both', padx=(5, 0))
        
        # Selected alphas header
        sel_header = tk.Frame(right_panel, bg=self.colors['white'])
        sel_header.pack(fill='x', padx=5, pady=3)
        
        self.selected_info_label = tk.Label(sel_header, 
                                           text="Selected: 0 alphas", 
                                           bg=self.colors['white'], 
                                           fg=self.colors['gray'],
                                           font=('Arial', 9))
        self.selected_info_label.pack(side='left')
        
        clear_selected_btn = tk.Button(sel_header, text="Clear Selected",
                                      command=self.clear_selected_alphas,
                                      bg=self.colors['red'], fg='white',
                                      font=('Arial', 8),
                                      relief='flat', padx=10, pady=3)
        clear_selected_btn.pack(side='right', padx=5)
        
        # Selected alphas canvas
        sel_canvas_container = tk.Frame(right_panel, bg=self.colors['white'])
        
        self.selected_canvas = tk.Canvas(sel_canvas_container, 
                                        bg='#f0f8ff', 
                                        relief='solid', 
                                        bd=1,
                                        highlightthickness=0)
        self.selected_canvas.pack(side="left", fill="both", expand=True)
        
        self.selected_scrollbar = ttk.Scrollbar(sel_canvas_container, 
                                               orient="vertical", 
                                               command=self.selected_canvas.yview)
        self.selected_scrollbar.pack(side="right", fill="y")
        
        self.selected_area = tk.Frame(self.selected_canvas, bg='#f0f8ff')
        self.selected_canvas.create_window((0, 0), window=self.selected_area, anchor="nw")
        self.selected_canvas.configure(yscrollcommand=self.selected_scrollbar.set)
        
        # Update scrollregion for selected
        def update_selected_scrollregion(event=None):
            self.selected_canvas.configure(scrollregion=self.selected_canvas.bbox("all"))
        
        self.selected_area.bind("<Configure>", update_selected_scrollregion)
        
        # Mouse wheel scrolling for selected
        def _on_selected_mousewheel(event):
            self.selected_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def _bind_selected_mousewheel(event):
            self.selected_canvas.bind_all("<MouseWheel>", _on_selected_mousewheel)
        
        def _unbind_selected_mousewheel(event):
            self.selected_canvas.unbind_all("<MouseWheel>")
        
        self.selected_canvas.bind('<Enter>', _bind_selected_mousewheel)
        self.selected_canvas.bind('<Leave>', _unbind_selected_mousewheel)
        
        # ========== SIMULATION CONTROL PANEL ==========
        sim_control_frame = tk.Frame(right_panel, bg=self.colors['white'])
        sim_control_frame.pack(side='bottom', fill='x', padx=10, pady=5)
        sel_canvas_container.pack(side='top', expand=True, fill='both', padx=10, pady=(0, 10))

        # Progress bar for simulation
        self.simulation_progress = ttk.Progressbar(sim_control_frame, 
                                                    mode='determinate')
        self.simulation_progress.pack(fill='x', pady=(0, 5))

        # Progress label
        self.sim_progress_label = tk.Label(sim_control_frame, 
                                            text="Ready for simulation",
                                            bg=self.colors['white'], 
                                            fg=self.colors['gray'],
                                            font=('Arial', 9))
        self.sim_progress_label.pack(fill='x', pady=(0, 5))

        # Control buttons
        sim_buttons = tk.Frame(sim_control_frame, bg=self.colors['white'])
        sim_buttons.pack(fill='x')

        self.btn_simulate = tk.Button(sim_buttons, 
                                    text="Start Simulation",
                                    command=self.start_simulation,
                                    bg='#28a745', 
                                    fg='white',
                                    font=('Arial', 9),
                                    relief='flat', 
                                    padx=12, 
                                    pady=4,
                                    cursor='hand2')
        self.btn_simulate.pack(side="left", padx=2)

        self.btn_pause = tk.Button(sim_buttons, 
                                    text="Pause",
                                    command=self.pause_simulation,
                                    bg=self.colors['orange'], 
                                    fg='white',
                                    font=('Arial', 9),
                                    relief='flat', 
                                    padx=12, 
                                    pady=4,
                                    cursor='hand2',
                                    state='disabled')
        self.btn_pause.pack(side="left", padx=2)

        self.btn_stop = tk.Button(sim_buttons, 
                                    text="Stop",
                                    command=self.stop_simulation,
                                    bg=self.colors['red'], 
                                    fg='white',
                                    font=('Arial', 9),
                                    relief='flat', 
                                    padx=12, 
                                    pady=4,
                                    cursor='hand2',
                                    state='disabled')
        self.btn_stop.pack(side="left", padx=2)
        
        # Initialize displays
        self.display_alphas()
        self.display_selected_alphas()
        
    def create_simulate_tab(self):
        """Tab Simulate đơn giản"""
        tab3 = tk.Frame(self.notebook, bg=self.colors['white'])
        self.notebook.add(tab3, text="Simulation Results")
        
        # Header
        header_frame = tk.LabelFrame(tab3, text="Simulation Data", 
                                    bg=self.colors['white'],
                                    font=('Arial', 10, 'bold'))
        header_frame.pack(fill='x', padx=10, pady=10)
        
        info_frame = tk.Frame(header_frame, bg=self.colors['white'])
        info_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Label(info_frame, 
                text="Auto-refresh: 30 seconds | Select multiple rows: Ctrl+Click",
                bg=self.colors['white'], fg=self.colors['gray'], 
                font=('Arial', 9)).pack(side='left')
        
        refresh_btn = tk.Button(info_frame, text="Refresh",
                               command=self.display_table,
                               bg=self.colors['blue'], fg='white',
                               font=('Arial', 9),
                               relief='flat', padx=15, pady=5)
        refresh_btn.pack(side='right')
        
        # Table container
        self.table_frame = tk.Frame(tab3, bg=self.colors['white'])
        self.table_frame.pack(expand=True, fill='both', padx=10, pady=10)
        
        # Action buttons
        action_frame = tk.Frame(tab3, bg=self.colors['white'])
        action_frame.pack(fill='x', padx=10, pady=10)
        
        btn_copy_all = tk.Button(action_frame, text="Copy All",
                                command=self.copy_all_data,
                                bg=self.colors['blue'], fg='white',
                                font=('Arial', 9),
                                relief='flat', padx=15, pady=5)
        btn_copy_all.pack(side='left', padx=5)
        
        btn_copy_selected = tk.Button(action_frame, text="Copy Selected",
                                     command=self.copy_selected_data,
                                     bg=self.colors['green'], fg='white',
                                     font=('Arial', 9),
                                     relief='flat', padx=15, pady=5)
        btn_copy_selected.pack(side='left', padx=5)
        
        btn_clear = tk.Button(action_frame, text="Clear Data",
                             command=self.remove_tree,
                             bg=self.colors['red'], fg='white',
                             font=('Arial', 9),
                             relief='flat', padx=15, pady=5)
        btn_clear.pack(side='right', padx=5)
        
        # Initialize table
        self.tree = None
        self.scrollbar_y = None
        self.scrollbar_x = None
        self.display_table()

    def create_account_tab(self):
        """Tab Account với WorldQuant authentication"""
        tab4 = tk.Frame(self.notebook, bg=self.colors['white'])
        self.notebook.add(tab4, text="Account")
        
        # WorldQuant Login Section
        login_frame = tk.LabelFrame(tab4, text="WorldQuant Brain Login", 
                                bg=self.colors['white'],
                                font=('Arial', 10, 'bold'))
        login_frame.pack(fill='x', padx=20, pady=20)
        
        login_content = tk.Frame(login_frame, bg=self.colors['white'])
        login_content.pack(fill='x', padx=20, pady=20)
        
        # Username
        tk.Label(login_content, text="Username:", bg=self.colors['white'],
                font=('Arial', 10), width=12, anchor='w').grid(row=0, column=0, sticky='w', pady=5)
        self.username_entry = tk.Entry(login_content, font=('Arial', 10), width=30)
        self.username_entry.grid(row=0, column=1, sticky='ew', padx=10, pady=5)
        
        # Password
        tk.Label(login_content, text="Password:", bg=self.colors['white'],
                font=('Arial', 10), width=12, anchor='w').grid(row=1, column=0, sticky='w', pady=5)
        self.password_entry = tk.Entry(login_content, font=('Arial', 10), width=30, show='*')
        self.password_entry.grid(row=1, column=1, sticky='ew', padx=10, pady=5)

        self.load_saved_credentials()

        def worldquant_login():
            credential={
                        "username":self.username_entry.get(),
                        "password":self.password_entry.get()
                        }
            print(credential)
            json.dump(credential, open("./credential.json", "w", encoding="utf-8"), ensure_ascii=False, indent=4)
            self.wq=WorldQuant()
            url_biometrics=self.wq.url_biometrics
            print(url_biometrics)

            # Hiển thị URL lên giao diện
            self.url_biometrics_label.config(text=f"Biometrics URL: {url_biometrics}")
            # Gắn sự kiện click để mở browser
            self.url_biometrics_label.bind(
                "<Button-1>", lambda e: webbrowser.open_new(url_biometrics)
            )

        def biometrics_completed():
            response = self.wq.sess.post(self.wq.url_biometrics)
            if response.status_code == 201:
                self.biometrics_status_label.config(text=f"Status: successfully") #hiện thị trạng thái
                # Lưu session
                with open("session.pkl", "wb") as f:
                    pickle.dump(self.wq.sess.cookies, f)
            else:
                self.biometrics_status_label.config(text=f"Status: unsuccessfully") #hiện thị trạng thái
                
        # Login button
        self.login_btn = tk.Button(login_content, text="Login to WorldQuant",
                                command=worldquant_login,
                                bg=self.colors['blue'], fg='white',
                                font=('Arial', 10),
                                relief='flat', padx=20, pady=5)
        self.login_btn.grid(row=3, column=1, sticky='w', padx=10, pady=10)
        
        # Label để hiển thị URL biometrics
        self.url_biometrics_label = tk.Label(login_content, text="", 
                                            bg=self.colors['white'], 
                                            fg="blue",
                                            cursor="hand2", 
                                            font=('Arial', 10, 'italic'),
                                            wraplength=400, justify="left")
        self.url_biometrics_label.grid(row=4, column=0, columnspan=2, sticky='w', pady=5)

        # Biometrics completed button
        self.biometrics_completed_btn = tk.Button(login_content, text="Biometrics Completed",
                                command=biometrics_completed,
                                bg=self.colors['blue'], fg='white',
                                font=('Arial', 10),
                                relief='flat', padx=20, pady=5)
        self.biometrics_completed_btn.grid(row=5, column=1, sticky='w', padx=10, pady=10)

        # Label để hiển thị status
        self.biometrics_status_label = tk.Label(login_content, text="", 
                                            bg=self.colors['white'], 
                                            fg="blue",
                                            font=('Arial', 10, 'italic'),
                                            wraplength=400, justify="left")
        self.biometrics_status_label.grid(row=6, column=0, columnspan=2, sticky='w', pady=5)
        
        # Configure grid weights
        login_content.columnconfigure(1, weight=1)
        
        # User info section
        info_frame = tk.LabelFrame(tab4, text="User Information", 
                                bg=self.colors['white'],
                                font=('Arial', 10, 'bold'))
        info_frame.pack(fill='x', padx=20, pady=20)
    
    def load_saved_credentials(self):
        """Load thông tin đăng nhập đã lưu"""
        try:
            with open('./credential.json', 'r') as f:
                creds = json.load(f)
                self.username_entry.insert(0, creds.get('username', ''))
                self.password_entry.insert(0, creds.get('password', ''))
                print("runed")
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Failed to load credentials: {e}")

    def create_status_bar(self):
        """Tạo status bar"""
        status_frame = tk.Frame(self.root, bg=self.colors['light_gray'], height=25)
        status_frame.pack(fill='x')
        status_frame.pack_propagate(False)
        
        self.status_label = tk.Label(status_frame, text="Ready", 
                                    bg=self.colors['light_gray'], fg=self.colors['dark'],
                                    font=('Arial', 9))
        self.status_label.pack(side='left', padx=10, pady=3)

    def create_help_tab(self):
            """Tab hướng dẫn sử dụng"""
            help_tab = tk.Frame(self.notebook, bg=self.colors['white'])
            self.notebook.add(help_tab, text="Help & Guide")

            main_container = tk.Frame(help_tab, bg=self.colors['white'])
            main_container.pack(expand=True, fill='both', padx=20, pady=20)

            title_label = tk.Label(main_container,
                                text="Alpha Finding Tool - User Guide",
                                bg=self.colors['white'],
                                font=('Arial', 16, 'bold'),
                                fg=self.colors['dark'])
            title_label.pack(pady=(0, 20))

            text_frame = tk.Frame(main_container, bg=self.colors['white'])
            text_frame.pack(expand=True, fill='both')

            help_text = tk.Text(text_frame, wrap="word", bg='#f8f9fa',
                                font=('Arial', 10), relief='solid', bd=1, padx=10, pady=10)
            help_text.pack(side='left', expand=True, fill='both')

            help_scroll = ttk.Scrollbar(text_frame, orient="vertical", command=help_text.yview)
            help_scroll.pack(side='right', fill='y')
            help_text.configure(yscrollcommand=help_scroll.set)

            help_content = """ALPHA FINDING TOOL - HƯỚNG DẪN SỬ DỤNG
    ═══════════════════════════════════════════════════════════════════
    TỔNG QUAN
    Tool này giúp bạn tạo và kiểm tra các công thức alpha trong WorldQuant Brain.

    CÁC TAB CHÍNH:
    1️ AI ASSISTANT
    • Load PDF files để AI có thể tham khảo
    • Chat với AI để được tư vấn về alpha và tài chính

    2️ COMPLETE SEARCH
    • Nhập công thức alpha cơ bản và tạo các biến thể
    • Chọn alpha để gửi đi mô phỏng (simulation)
    • Điều khiển quá trình simulation (Pause/Stop)

    3️ SIMULATION RESULTS
    • Xem kết quả simulation từ WorldQuant
    • Tự động làm mới sau mỗi 30 giây

    4️ ACCOUNT
    • Đăng nhập WorldQuant Brain
    • Hoàn thành xác thực sinh trắc học (biometrics)
    ═══════════════════════════════════════════════════════════════════
    QUY TRÌNH SỬ DỤNG:
    BƯỚC 1: Đăng nhập WorldQuant ở tab "Account".
    BƯỚC 2: Qua tab "Complete Search", nhập công thức và nhấn "Generate Variations".
    BƯỚC 3: Chọn các alpha muốn thử bằng nút "+" ở bảng bên trái. Chúng sẽ xuất hiện ở bảng "Selected for Simulation" bên phải.
    BƯỚC 4: Nhấn "Start Simulation" để bắt đầu.
    BƯỚC 5: Theo dõi tiến trình. Khi hoàn tất, tab "Simulation Results" sẽ tự động mở ra.
    ═══════════════════════════════════════════════════════════════════
    """
            help_text.insert("1.0", help_content)
            help_text.config(state="disabled")

    # ========== NEW METHODS FOR ALPHA SELECTION ==========
    def select_all_generated(self):
        """Select all generated alphas for simulation"""
        if not self.new_alphas:
            messagebox.showwarning("Warning", "No generated alphas to select")
            return
            
        for alpha in self.new_alphas:
            if alpha not in self.selected_alphas:
                self.selected_alphas.append(alpha)
        
        self.display_selected_alphas()
        self.update_selected_info()
        messagebox.showinfo("Success", f"Selected {len(self.new_alphas)} alphas for simulation")

    def add_to_selected(self, alpha):
        """Add alpha to selected list"""
        if alpha not in self.selected_alphas:
            self.selected_alphas.append(alpha)
            self.display_selected_alphas()
            self.update_selected_info()

    def remove_from_selected(self, alpha):
        """Remove alpha from selected list"""
        if alpha in self.selected_alphas:
            self.selected_alphas.remove(alpha)
            self.display_selected_alphas()
            self.update_selected_info()

    def clear_selected_alphas(self):
        """Clear all selected alphas"""
        if not self.selected_alphas:
            messagebox.showinfo("Info", "No selected alphas to clear")
            return
            
        result = messagebox.askyesno("Confirm", f"Clear all {len(self.selected_alphas)} selected alphas?")
        if result:
            self.selected_alphas.clear()
            self.display_selected_alphas()
            self.update_selected_info()

    def display_selected_alphas(self):
        """Display selected alphas in the right panel"""
        # Clear existing
        for widget in self.selected_area.winfo_children():
            widget.destroy()
        
        if not self.selected_alphas:
            # Empty state
            empty_container = tk.Frame(self.selected_area, bg='#f0f8ff')
            empty_container.pack(expand=True, fill='both', pady=50)
            
            empty_icon = tk.Label(empty_container, 
                                 text="⚡",
                                 bg='#f0f8ff', 
                                 font=('Arial', 32))
            empty_icon.pack()
            
            empty_label = tk.Label(empty_container, 
                                  text="No alphas selected",
                                  bg='#f0f8ff', 
                                  fg=self.colors['gray'],
                                  font=('Arial', 12, 'bold'))
            empty_label.pack(pady=(10, 5))
            
            empty_hint = tk.Label(empty_container, 
                                 text="Select alphas from the left panel\nto simulate them",
                                 bg='#f0f8ff', 
                                 fg=self.colors['gray'],
                                 font=('Arial', 10),
                                 justify='center')
            empty_hint.pack()
            
            self.update_selected_info()
            return
        
        # Header for selected list
        header_frame = tk.Frame(self.selected_area, bg='#e6f3ff', relief='solid', bd=1)
        header_frame.pack(fill='x', pady=(0, 1))
        
        tk.Label(header_frame, text="#", bg='#e6f3ff', font=('Arial', 9, 'bold'), 
                width=4).pack(side='left', padx=5, pady=3)
        tk.Label(header_frame, text="Selected Alpha Formula", bg='#e6f3ff', 
                font=('Arial', 9, 'bold')).pack(side='left', padx=10, pady=3)
        tk.Label(header_frame, text="Action", bg='#e6f3ff', 
                font=('Arial', 9, 'bold')).pack(side='right', padx=10, pady=3)
        
        # Display each selected alpha
        for i, selected_alpha in enumerate(self.selected_alphas):
            # Alternating colors
            row_bg = '#ffffff' if i % 2 == 0 else '#f0f8ff'
            border_color = '#cce7ff'
            
            row = tk.Frame(self.selected_area, bg=row_bg, relief='solid', bd=1,
                          highlightbackground=border_color)
            row.pack(fill="x", pady=1)
            
            # Hover effects
            def on_enter(event, frame=row):
                frame.config(bg='#e3f2fd')
                
            def on_leave(event, frame=row, original_bg=row_bg):
                frame.config(bg=original_bg)
                
            row.bind("<Enter>", on_enter)
            row.bind("<Leave>", on_leave)
            
            # Index with purple styling
            idx_frame = tk.Frame(row, bg=self.colors['purple'], width=50)
            idx_frame.pack(side='left', fill='y', padx=2, pady=2)
            idx_frame.pack_propagate(False)
            
            idx_label = tk.Label(idx_frame, 
                               text=f"{i+1:03d}", 
                               bg=self.colors['purple'], 
                               fg='white',
                               font=('Arial', 9, 'bold'))
            idx_label.pack(expand=True)
            
            # Alpha text container
            text_frame = tk.Frame(row, bg=row_bg)
            text_frame.pack(side="left", fill="x", expand=True, padx=10, pady=8)
            
            lbl = tk.Label(text_frame, 
                          text=selected_alpha,
                          anchor="w", 
                          bg=row_bg,
                          font=('Consolas', 9), 
                          wraplength=400,
                          justify='left')
            lbl.pack(fill='x')
            
            # Action buttons container
            actions_frame = tk.Frame(row, bg=row_bg)
            actions_frame.pack(side='right', padx=10, pady=5)
            
            # Remove button
            def confirm_remove(alpha=selected_alpha):
                if messagebox.askyesno("Confirm Remove", 
                                     f"Remove from simulation list?\n\n{alpha[:50]}..."):
                    self.remove_from_selected(alpha)
            
            remove_btn = tk.Button(actions_frame, 
                                 text="✖️",
                                 command=confirm_remove,
                                 bg='#dc3545', 
                                 fg='white',
                                 relief='flat', 
                                 width=3,
                                 height=1,
                                 font=('Arial', 8),
                                 cursor='hand2')
            remove_btn.pack(side='right', padx=1)
        
        self.update_selected_info()

    def update_selected_info(self):
        """Update selected alphas info"""
        count = len(self.selected_alphas)
        if count == 0:
            self.selected_info_label.config(text="Selected: 0 alphas", fg=self.colors['gray'])
        else:
            self.selected_info_label.config(text=f"Selected: {count} alphas", fg=self.colors['purple'])

# ========== SIMULATION CONTROL METHODS ==========
    def start_simulation(self):
        """Start simulation với progress tracking"""
        if not self.selected_alphas: # Dùng selected_alphas để khớp với UI của bạn
            messagebox.showwarning("Warning", "No alphas selected to simulate")
            return
                
        if not hasattr(self, 'wq') or self.wq is None:
            messagebox.showerror("Error", "Please login to WorldQuant first")
            return
            
        # Reset simulation state
        self.simulation_running = True
        self.simulation_paused = False
        self.current_simulation_index = 0
            
        # Update UI
        self.btn_simulate.config(text="Running...", state='disabled')
        self.btn_pause.config(state='normal', bg=self.colors['orange'])
        self.btn_stop.config(state='normal')
            
        # Setup progress
        self.simulation_progress.config(maximum=len(self.selected_alphas), value=0)
        self.update_simulation_progress(f"Starting simulation of {len(self.selected_alphas)} alphas...")
            
        # Start thread
        self.simulation_thread = threading.Thread(target=self.run_simulation, daemon=True)
        self.simulation_thread.start()

    def pause_simulation(self):
        """Pause/Resume simulation"""
        if not self.simulation_running: return

        if self.simulation_paused:
            self.simulation_paused = False
            self.btn_pause.config(text="Pause", bg=self.colors['orange'])
            self.update_simulation_progress(f"Resumed at {self.current_simulation_index + 1}/{len(self.selected_alphas)}")
        else:
            self.simulation_paused = True
            self.btn_pause.config(text="Resume", bg=self.colors['green'])
            self.update_simulation_progress(f"Paused at {self.current_simulation_index + 1}/{len(self.selected_alphas)}")

    def stop_simulation(self):
        """Stop simulation"""
        if messagebox.askyesno("Confirm", "Stop simulation? Progress will be lost."):
            self.simulation_running = False
            self.update_simulation_progress("Stopping simulation...")


    def run_simulation(self):
        """Run actual simulation với progress updates"""
        try:
            batch_size = 3
            total = len(self.selected_alphas)

            for i in range(0, total, batch_size):

                while self.simulation_paused and self.simulation_running:
                    time.sleep(3)

                if not self.simulation_running:
                    self.root.after(0, lambda: self.update_simulation_progress("Simulation stopped by user."))
                    break

                # Lấy batch 3 alpha
                batch = self.selected_alphas[i:i+batch_size]

                self.current_simulation_index = i

                self.root.after(
                    0,
                    lambda idx=i, total=total, b=batch: self.update_simulation_progress(
                        f"Simulating alphas {idx+1}-{min(idx+batch_size, total)}/{total}: {[a[:15]+'...' for a in b]}"
                    )
                )

                try:
                    # simulate nhiều alpha cùng lúc
                    self.wq.simulate(batch)

                    # update progress (tăng theo số alpha trong batch)
                    self.root.after(0, lambda v=min(i+batch_size, total): self.simulation_progress.config(value=v))
                    time.sleep(0.5)

                except Exception as e:
                    print(f"Error simulating batch starting at {i+1}: {e}")
                    continue

            if self.simulation_running:
                self.root.after(0, self.simulation_completed)
            else:
                self.root.after(0, self.reset_simulation_ui)

        except Exception as e:
            self.root.after(0, lambda: self.simulation_error(str(e)))


    def simulation_completed(self):
        """Handle completion"""
        self.update_simulation_progress(f"✅ Simulation completed successfully!")
        self.reset_simulation_ui()
        self.notebook.select(2)
        messagebox.showinfo("Complete", f"Simulated {len(self.selected_alphas)} alphas successfully!")

    def simulation_error(self, error_msg):
        """Handle errors"""
        self.update_simulation_progress(f"❌ Simulation failed: {error_msg}")
        self.reset_simulation_ui()
        messagebox.showerror("Error", f"Simulation failed: {error_msg}")

    def reset_simulation_ui(self):
        """Reset UI after simulation"""
        self.simulation_running = False
        self.simulation_paused = False
        self.btn_simulate.config(text="Start Simulation", state='normal')
        self.btn_pause.config(text="Pause", state='disabled', bg=self.colors['orange'])
        self.btn_stop.config(state='disabled')
        self.simulation_progress.config(value=0)

    def update_simulation_progress(self, message):
        """Update progress với timestamp"""
        timestamp = time.strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {message}"
        self.sim_progress_label.config(text=formatted_msg)
        print(formatted_msg)

    # ========== ENHANCED COMPLETE SEARCH METHODS ==========
    def remove_display(self):
        for widget in self.area_2.winfo_children():
            widget.destroy()
        self.new_alphas = []
        self.update_results_info()
        self.progress_label.config(text="Cleared all variations")

    def display_alphas(self):
        for widget in self.area_2.winfo_children():
            widget.destroy()
        
        if not self.new_alphas:  
            # Empty state
            empty_container = tk.Frame(self.area_2, bg='#f8f9fa')
            empty_container.pack(expand=True, fill='both', pady=50)
            
            empty_icon = tk.Label(empty_container, 
                                 text="📝",
                                 bg='#f8f9fa', 
                                 font=('Arial', 32))
            empty_icon.pack()
            
            empty_label = tk.Label(empty_container, 
                                  text="No variations generated yet",
                                  bg='#f8f9fa', 
                                  fg=self.colors['gray'],
                                  font=('Arial', 12, 'bold'))
            empty_label.pack(pady=(10, 5))
            
            empty_hint = tk.Label(empty_container, 
                                 text="Enter an alpha formula and click 'Generate Variations'",
                                 bg='#f8f9fa', 
                                 fg=self.colors['gray'],
                                 font=('Arial', 10))
            empty_hint.pack()
            
            self.update_results_info()  
            return
        
        # Header for the list
        header_frame = tk.Frame(self.area_2, bg='#e9ecef', relief='solid', bd=1)
        header_frame.pack(fill='x', pady=(0, 1))
        
        tk.Label(header_frame, text="#", bg='#e9ecef', font=('Arial', 9, 'bold'), 
                width=4).pack(side='left', padx=5, pady=3)
        tk.Label(header_frame, text="Alpha Formula", bg='#e9ecef', 
                font=('Arial', 9, 'bold')).pack(side='left', padx=10, pady=3)
        tk.Label(header_frame, text="Actions", bg='#e9ecef', 
                font=('Arial', 9, 'bold')).pack(side='right', padx=10, pady=3)
        
        # Display each alpha
        for i, new_alpha in enumerate(self.new_alphas):  
            # Alternating colors
            row_bg = '#ffffff' if i % 2 == 0 else '#f8f9fa'
            border_color = '#dee2e6'
            
            row = tk.Frame(self.area_2, bg=row_bg, relief='solid', bd=1,
                          highlightbackground=border_color)
            row.pack(fill="x", pady=1)
            
            # Hover effects
            def on_enter(event, frame=row):
                frame.config(bg='#e3f2fd')
                
            def on_leave(event, frame=row, original_bg=row_bg):
                frame.config(bg=original_bg)
                
            row.bind("<Enter>", on_enter)
            row.bind("<Leave>", on_leave)
            
            # Index with styling
            idx_frame = tk.Frame(row, bg='#6c757d', width=50)
            idx_frame.pack(side='left', fill='y', padx=2, pady=2)
            idx_frame.pack_propagate(False)
            
            idx_label = tk.Label(idx_frame, 
                               text=f"{i+1:03d}", 
                               bg='#6c757d', 
                               fg='white',
                               font=('Arial', 9, 'bold'))
            idx_label.pack(expand=True)
            
            # Alpha text container
            text_frame = tk.Frame(row, bg=row_bg)
            text_frame.pack(side="left", fill="x", expand=True, padx=10, pady=8)
            
            lbl = tk.Label(text_frame, 
                          text=new_alpha,
                          anchor="w", 
                          bg=row_bg,
                          font=('Consolas', 9), 
                          wraplength=400,
                          justify='left')
            lbl.pack(fill='x')
            
            # Action buttons container
            actions_frame = tk.Frame(row, bg=row_bg)
            actions_frame.pack(side='right', padx=10, pady=5)
            
            # Select for simulation button
            is_selected = new_alpha in self.selected_alphas
            select_text = "✓" if is_selected else "+"
            select_bg = self.colors['purple'] if is_selected else self.colors['green']
            
            def toggle_selection(alpha=new_alpha):
                if alpha in self.selected_alphas:
                    self.remove_from_selected(alpha)
                else:
                    self.add_to_selected(alpha)
                self.display_alphas()  # Refresh to update button states
            
            select_btn = tk.Button(actions_frame, 
                                 text=select_text,
                                 command=toggle_selection,
                                 bg=select_bg, 
                                 fg='white',
                                 relief='flat', 
                                 width=3,
                                 height=1,
                                 font=('Arial', 8),
                                 cursor='hand2')
            select_btn.pack(side='right', padx=1)
            
            # Edit button
            def start_edit(alpha=new_alpha, label=lbl, row=row, text_frame=text_frame):
                label.pack_forget()
                
                entry = tk.Entry(text_frame, font=('Consolas', 9),
                               relief='solid', bd=1, bg='#fff3cd')
                entry.insert(0, alpha)
                entry.pack(fill="x", expand=True)
                entry.focus()
                entry.select_range(0, tk.END)
                
                def save_edit(event=None):
                    new_value = entry.get()
                    idx = self.new_alphas.index(alpha)
                    self.new_alphas[idx] = new_value
                    
                    # Update selected list if this alpha was selected
                    if alpha in self.selected_alphas:
                        sel_idx = self.selected_alphas.index(alpha)
                        self.selected_alphas[sel_idx] = new_value
                        self.display_selected_alphas()
                    
                    self.display_alphas()
                
                entry.bind("<Return>", save_edit)
                entry.bind("<Escape>", lambda e: self.display_alphas())
                
                save_btn = tk.Button(actions_frame, 
                                   text="💾",
                                   command=save_edit,
                                   bg='#28a745', 
                                   fg='white',
                                   relief='flat', 
                                   width=3,
                                   height=1,
                                   font=('Arial', 8))
                save_btn.pack(side="right", padx=1)
            
            edit_btn = tk.Button(actions_frame, 
                               text="✏️",
                               command=start_edit,
                               bg='#17a2b8', 
                               fg='white',
                               relief='flat', 
                               width=3,
                               height=1,
                               font=('Arial', 8),
                               cursor='hand2')
            edit_btn.pack(side='right', padx=1)
            
            # Delete button
            def confirm_delete(alpha=new_alpha):
                if messagebox.askyesno("Confirm Delete", 
                                     f"Remove this alpha variation?\n\n{alpha[:50]}..."):
                    self.remove_alpha(alpha)
            
            delete_btn = tk.Button(actions_frame, 
                                 text="🗑️",
                                 command=confirm_delete,
                                 bg='#dc3545', 
                                 fg='white',
                                 relief='flat', 
                                 width=3,
                                 height=1,
                                 font=('Arial', 8),
                                 cursor='hand2')
            delete_btn.pack(side='right', padx=1)
        
        self.update_results_info()

    def remove_alpha(self, alpha):
        """Remove alpha from both generated and selected lists"""
        if alpha in self.new_alphas:
            self.new_alphas.remove(alpha)
            self.display_alphas()
            
        if alpha in self.selected_alphas:
            self.selected_alphas.remove(alpha)
            self.display_selected_alphas()
            
        self.progress_label.config(text=f"Removed 1 variation. Total: {len(self.new_alphas)}")

    def run_enter_ok_in_thread(self):
        """Generate alpha variations"""
        # Update UI
        self.btn_ok.config(text="⏳ Generating...", state='disabled')
        self.progress_label.config(text="Generating alpha variations...")
        
        def enter_ok():
            try:
                alpha = self.entry_2.get()
                option_items = [item for item, var in self.vars.items() if var.get()]
                
                if not alpha.strip():
                    self.root.after(0, lambda: messagebox.showwarning("Warning", "Please enter an alpha formula"))
                    return
                
                # Generate variations
                self.new_alphas = Optimize().complete_search(alpha, option_items)
                self.root.after(0, self.display_alphas)
                
                # Print statements for debugging
                print(f"Alpha: {alpha}")
                print(f"Options: {option_items}")  
                print(f"Results: {len(self.new_alphas)} variations generated")
                
                # Update progress
                self.root.after(0, lambda: self.progress_label.config(
                    text=f"✅ Generated {len(self.new_alphas)} variations successfully!"))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Generation failed: {str(e)}"))
                self.root.after(0, lambda: self.progress_label.config(text="❌ Generation failed"))
            finally:
                self.root.after(0, lambda: self.btn_ok.config(text="Generate Variations", state='normal'))
        
        threading.Thread(target=enter_ok, daemon=True).start()

    def update_results_info(self):
        """Update results info with better styling"""
        count = len(self.new_alphas)
        if count == 0:
            self.results_info_label.config(text="Generated: 0 variations", fg=self.colors['gray'])
        else:
            self.results_info_label.config(text=f"Generated: {count} variations", fg=self.colors['green'])

    # ========== GENAI METHODS ==========
    def load_pdf_files(self):
        """Load PDF files"""
        file_paths = filedialog.askopenfilenames(
            title="Select PDF files",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        
        if file_paths:
            try:
                self.pdf_load_btn.config(text="Loading...", state='disabled')
                success = self.genai_instance.load_pdf_files(list(file_paths))
                
                if success:
                    self.update_pdf_status(f"Loaded {len(file_paths)} PDFs")
                    messagebox.showinfo("Success", f"Successfully loaded {len(file_paths)} PDF file(s)")
                else:
                    self.update_pdf_status("Failed to load PDFs")
                    messagebox.showerror("Error", "Failed to load PDF files")
            except Exception as e:
                self.update_pdf_status("Error occurred")
                messagebox.showerror("Error", f"Error loading PDFs: {str(e)}")
            finally:
                self.pdf_load_btn.config(text="Load PDF Files", state='normal')

    def clear_pdf_files(self):
        """Clear PDF files"""
        try:
            self.genai_instance.clear_pdf_content()
            self.update_pdf_status("Status: No PDFs loaded")
            messagebox.showinfo("Info", "All PDF content cleared")
        except Exception as e:
            messagebox.showerror("Error", f"Error clearing PDFs: {str(e)}")

    def update_pdf_status(self, status_text):
        """Update PDF status"""
        self.pdf_status_label.config(text=status_text)

    def send_message_thread(self):
        """Send message to AI"""
        user_text = self.user_input.get().strip()
        if not user_text:
            return

        # Add user message
        self.chat_history.config(state="normal")
        self.chat_history.insert("end", f"You: {user_text}\n")
        self.chat_history.config(state="disabled")
        self.user_input.delete(0, "end")
        self.chat_history.see("end")

        def get_ai_response():
            try:
                # Show thinking
                self.chat_history.config(state="normal")
                self.chat_history.insert("end", "AI: Thinking...\n")
                self.chat_history.config(state="disabled")
                self.chat_history.see("end")
                
                response = self.genai_instance.genai_financial_ratios(user_text)
                
                # Update with response
                self.chat_history.config(state="normal")
                self.chat_history.delete("end-2l", "end-1l")
                self.chat_history.insert("end", f"AI: {response}\n\n")
                self.chat_history.config(state="disabled")
                self.chat_history.see("end")
                
            except Exception as e:
                self.chat_history.config(state="normal")
                self.chat_history.delete("end-2l", "end-1l")
                self.chat_history.insert("end", f"AI: Error - {str(e)}\n\n")
                self.chat_history.config(state="disabled")
                self.chat_history.see("end")

        threading.Thread(target=get_ai_response, daemon=True).start()

# ========== SIMULATION TABLE METHODS ==========
    def display_table(self):
        """Display simulation table"""
        # Clear existing
        if self.tree is not None:
            self.tree.destroy()
            if self.scrollbar_y: self.scrollbar_y.destroy()
            if self.scrollbar_x: self.scrollbar_x.destroy()

        try:
            data_alpha = pd.read_csv('./genai_v3/data_alpha.csv')

            columns = list(data_alpha.columns)
            
            # Create treeview
            self.tree = ttk.Treeview(self.table_frame, columns=columns, 
                                   show="headings", selectmode="extended")

            # Configure columns
            for col in columns:
                self.tree.heading(col, text=col, anchor="center")
                self.tree.column(col, anchor="center", width=120, minwidth=80)

            # Add data
            for _, row in data_alpha.iterrows():
                self.tree.insert("", "end", values=list(row))

            # Scrollbars
            self.scrollbar_y = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
            self.tree.configure(yscrollcommand=self.scrollbar_y.set)
            self.scrollbar_y.pack(side="right", fill="y")

            self.scrollbar_x = ttk.Scrollbar(self.table_frame, orient="horizontal", command=self.tree.xview)
            self.tree.configure(xscrollcommand=self.scrollbar_x.set)
            self.scrollbar_x.pack(side="bottom", fill="x")

            self.tree.pack(fill="both", expand=True)

        except FileNotFoundError:
            error_label = tk.Label(self.table_frame,
                                 text="Data file not found.\nPlease run a simulation first.",
                                 bg=self.colors['white'], fg=self.colors['red'],
                                 font=('Arial', 11), justify='center')
            error_label.pack(expand=True)
            
        except Exception as e:
            error_label = tk.Label(self.table_frame,
                                 text=f"Error loading data:\n{str(e)}",
                                 bg=self.colors['white'], fg=self.colors['red'],
                                 font=('Arial', 10), justify='center')
            error_label.pack(expand=True)

        # Schedule next refresh
        self.root.after(30000, self.display_table)

    def copy_all_data(self):
        """Copy all data"""
        try:
            data_alpha = pd.read_csv('./genai_v3/data_alpha.csv')
            copy_text = data_alpha.to_string(index=False)
            self.root.clipboard_clear()
            self.root.clipboard_append(copy_text)
            self.show_copy_message(f"Copied {len(data_alpha)} rows")
        except Exception as e:
            self.show_copy_message(f"Copy failed: {str(e)}")

    def copy_selected_data(self):
        """Copy selected data"""
        if not self.tree or not self.tree.selection():
            messagebox.showwarning("Warning", "Please select rows to copy")
            return
        
        try:
            selected_items = self.tree.selection()
            columns = list(self.tree['columns'])
            copy_text = '\t'.join(columns) + '\n'
            
            selected_data = []
            for item in selected_items:
                values = self.tree.item(item, 'values')
                selected_data.append('\t'.join(map(str, values)))
            
            copy_text += '\n'.join(selected_data)
            self.root.clipboard_clear()
            self.root.clipboard_append(copy_text)
            self.show_copy_message(f"Copied {len(selected_items)} selected rows")
        except Exception as e:
            self.show_copy_message(f"Copy failed: {str(e)}")

    def show_copy_message(self, message):
        """Show copy message"""
        msg_label = tk.Label(self.table_frame, text=message,
                           bg=self.colors['light_gray'], fg=self.colors['dark'],
                           font=("Arial", 10, "bold"),
                           relief='solid', bd=1, padx=15, pady=8)
        msg_label.place(relx=0.5, rely=0.1, anchor="center")
        self.root.after(2000, msg_label.destroy)

    def remove_tree(self):
        """Clear simulation data"""
        result = messagebox.askyesno("Confirm", 
                                   "Are you sure you want to clear all simulation data?")
        if result:
            try:
                # Clear CSV file
                data_alpha = pd.read_csv('./genai_v3/data_alpha.csv')
                data_alpha = data_alpha.iloc[0:0]  # Remove all rows
                data_alpha.to_csv('./genai_v3/data_alpha.csv', index=False)
                self.display_table()
                messagebox.showinfo("Success", "All simulation data cleared")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear data: {str(e)}")

    # ========== ACCOUNT METHODS ==========
    def save_settings(self):
        """Save settings"""
        try:
            messagebox.showinfo("Settings", "Settings saved successfully!")
            self.update_status("Settings saved")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")

    def reset_settings(self):
        """Reset settings"""
        result = messagebox.askyesno("Reset", "Reset all settings to default?")
        if result:
            messagebox.showinfo("Settings", "Settings reset to default!")
            self.update_status("Settings reset")

    def update_status(self, message):
        """Update status bar"""
        if self.status_label:
            self.status_label.config(text=message)

    def run(self):
        """Run the application"""
        try:
            self.update_status("Ready")
            self.root.mainloop()
        except Exception as e:
            messagebox.showerror("Error", f"Application error: {str(e)}")

# ========== MAIN EXECUTION ==========
def main():
    """Main function"""
    try:
        app = AlphaFindingTool()
        app.run()
    except Exception as e:
        print(f"Critical Error: {e}")
        try:
            messagebox.showerror("Startup Error", f"Failed to start:\n{str(e)}")
        except:
            print("Failed to show error dialog")

if __name__ == '__main__':
    main()


