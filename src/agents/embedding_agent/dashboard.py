import time
import json
import threading
import tkinter as tk
from tkinter import ttk
from confluent_kafka import Consumer, KafkaException

# --- THEME CONFIGURATION ---
THEME = {
    "bg_main": "#2b2b2b",
    "bg_container": "#323232",
    "bg_row": "#3c3f41",
    "text_main": "#ffffff",
    "text_sec": "#a9b7c6",
    "accent": "#4caf50",
    "error": "#ff6b6b",
    "font_header": ("Helvetica", 14, "bold"),
    "font_main": ("Helvetica", 10),
    "font_mono": ("Consolas", 10)
}

class Dashboard:
    def __init__(self, total_files, min_workers=6, title="System Pipeline"):
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry("800x600")
        self.root.attributes("-topmost", True) 
        self.root.configure(bg=THEME["bg_main"])
        
        self.total_files = total_files
        self.processed_count = 0
        self.start_time = time.time()
        
        self._setup_styles()
        self._setup_ui(title, min_workers)
        
        # Kafka Configuration
        self.kafka_conf = {
            'bootstrap.servers': 'localhost:9092',
            'group.id': 'dashboard-viewer-group',
            'auto.offset.reset': 'earliest'
        }
        self.running = True
        self.kafka_thread = threading.Thread(target=self._kafka_poll_loop, daemon=True)
        self.kafka_thread.start()

    def _setup_ui(self, title, min_workers):
        # --- HEADER ---
        self.header_frame = tk.Frame(self.root, bg=THEME["bg_main"], pady=10)
        self.header_frame.pack(fill="x")
        tk.Label(self.header_frame, text=title, font=THEME["font_header"], 
                 bg=THEME["bg_main"], fg=THEME["text_main"]).pack()
        
        self.content_frame = tk.Frame(self.root, bg=THEME["bg_main"])
        self.content_frame.pack(fill="both", expand=True)
        
        # VIEW: PROGRESS
        self.progress_container = tk.Frame(self.content_frame, bg=THEME["bg_main"])
        self.progress_container.pack(fill="both", expand=True)
        
        self.lbl_global = tk.Label(self.progress_container, text=f"Total Progress: 0/{self.total_files}", 
                                   font=THEME["font_main"], bg=THEME["bg_main"], fg=THEME["text_sec"])
        self.lbl_global.pack(pady=(0,5))
        
        self.pbar_global = ttk.Progressbar(self.progress_container, length=750, mode="determinate")
        self.pbar_global.pack(pady=(0, 15))
        self.pbar_global["maximum"] = self.total_files

        # Scrollable Workers
        self.worker_frame = tk.Frame(self.progress_container, bg=THEME["bg_container"])
        self.worker_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        self.canvas = tk.Canvas(self.worker_frame, bg=THEME["bg_container"], highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.worker_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=THEME["bg_container"])

        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        self.rows = {} # Map worker_id -> UI elements
        for i in range(min_workers): self.add_row(f"worker-{i}")
        
        self.lbl_stats = tk.Label(self.root, text="System: Waiting for Kafka...", font=THEME["font_mono"], 
                                  bg=THEME["bg_main"], fg=THEME["accent"], pady=10)
        self.lbl_stats.pack(side="bottom")

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Horizontal.TProgressbar", background=THEME["accent"], troughcolor="#555555")

    def add_row(self, worker_id):
        row_frame = tk.Frame(self.scrollable_frame, bg=THEME["bg_row"], pady=4, padx=5)
        row_frame.pack(fill="x", padx=2, pady=3)
        
        tk.Label(row_frame, text=worker_id[-3:], width=5, font=THEME["font_mono"], bg="#555", fg="white").pack(side="left", padx=(0, 10))
        
        lbl_status = tk.Label(row_frame, text="Idle", width=35, anchor="w", font=THEME["font_main"], 
                              bg=THEME["bg_row"], fg=THEME["text_main"])
        lbl_status.pack(side="left", fill="x", expand=True)
        
        pbar = ttk.Progressbar(row_frame, length=120, mode="determinate")
        pbar.pack(side="right", padx=10)
        
        self.rows[worker_id] = {'label': lbl_status, 'pbar': pbar}

    def _kafka_poll_loop(self):
        """Background thread for Kafka polling"""
        consumer = Consumer(self.kafka_conf)
        consumer.subscribe(['processed_content', 'standard_tasks'])
        
        try:
            while self.running:
                msg = consumer.poll(1.0)
                if msg is None: continue
                if msg.error(): continue
                
                data = json.loads(msg.value().decode('utf-8'))
                msg_type = data.get('type')
                
                # Schedule thread-safe UI updates
                if msg_type == "START":
                    self.root.after(0, self.set_worker_task, data['worker_id'], data['filename'], data['total'])
                elif msg_type == "PROGRESS":
                    self.root.after(0, self.update_worker_progress, data['worker_id'], data['current'])
                elif msg_type == "DONE":
                    self.processed_count += 1
                    self.root.after(0, self.update_global)
        finally:
            consumer.close()

    def set_worker_task(self, worker_id, filename, total_pages):
        if worker_id not in self.rows: self.add_row(worker_id)
        display_name = (filename[:37] + '..') if len(filename) > 40 else filename
        self.rows[worker_id]['label'].config(text=display_name, fg=THEME["text_main"])
        self.rows[worker_id]['pbar']['maximum'] = total_pages
        self.rows[worker_id]['pbar']['value'] = 0

    def update_worker_progress(self, worker_id, current_page):
        if worker_id in self.rows:
            self.rows[worker_id]['pbar']['value'] = current_page

    def update_global(self):
        self.pbar_global["value"] = self.processed_count
        pct = (self.processed_count / self.total_files) * 100 if self.total_files > 0 else 0
        
        elapsed = time.time() - self.start_time
        eta_str = "--:--"
        if self.processed_count > 0:
            rate = self.processed_count / elapsed
            remaining = self.total_files - self.processed_count
            eta_s = remaining / rate
            eta_str = f"{int(eta_s//60)}m {int(eta_s%60)}s"
        
        self.lbl_global.config(text=f"Total Progress: {self.processed_count}/{self.total_files} ({pct:.1f}%)   •   ETA: {eta_str}")
        self.lbl_stats.config(text=f"Live Monitoring via Kafka  |  Elapsed: {int(elapsed//60)}m", fg=THEME["accent"])

    def run(self):
        self.root.mainloop()
        self.running = False

if __name__ == "__main__":
    # Launch with your 737 total files
    dash = Dashboard(total_files=737)
    dash.run()