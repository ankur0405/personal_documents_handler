import time
import tkinter as tk
from tkinter import ttk

class Dashboard:
    def __init__(self, total_files, min_workers, title="Processing"):
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry("650x500")
        self.root.attributes("-topmost", True) 
        self.root.configure(bg="white")
        
        # --- HEADER ---
        tk.Label(self.root, text=title, font=("Arial", 14, "bold"), bg="white", fg="black").pack(pady=10)
        
        # --- GLOBAL PROGRESS ---
        self.lbl_global = tk.Label(self.root, text=f"Total Progress: 0/{total_files} (0.0%)", font=("Arial", 11), bg="white", fg="black")
        self.lbl_global.pack(pady=2)
        
        self.pbar_global = ttk.Progressbar(self.root, length=600, mode="determinate")
        self.pbar_global.pack(pady=5)
        self.pbar_global["maximum"] = total_files
        
        # --- SCROLLABLE WORKER GRID ---
        tk.Label(self.root, text="Active Workers", font=("Arial", 10, "bold"), bg="white", fg="#555", pady=5).pack()
        
        self.container_frame = tk.Frame(self.root, bg="#eee")
        self.container_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.canvas = tk.Canvas(self.container_frame, bg="#eee")
        self.scrollbar = ttk.Scrollbar(self.container_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#eee")

        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Rows store: {'label': widget, 'pbar': widget, 'max_val': int}
        self.rows = []
        
        for i in range(min_workers):
            self.add_row(i)
            
        # --- FOOTER ---
        self.lbl_stats = tk.Label(self.root, text="Init...", font=("Courier", 10), bg="white", fg="#0000AA")
        self.lbl_stats.pack(pady=10)
        
        self.start_time = time.time()
        self.total_files = total_files
        self.root.update()

    def add_row(self, index):
        row_frame = tk.Frame(self.scrollable_frame, bg="white", pady=2)
        row_frame.pack(fill="x", padx=1, pady=1)
        
        tk.Label(row_frame, text=f"W-{index}", width=4, font=("Courier", 9, "bold"), bg="#ddd", fg="black").pack(side="left", padx=2)
        
        lbl_status = tk.Label(row_frame, text="Idle", width=30, anchor="w", font=("Arial", 9), bg="white", fg="black")
        lbl_status.pack(side="left", padx=5)
        
        pbar = ttk.Progressbar(row_frame, length=150, mode="determinate")
        pbar.pack(side="left", padx=5, fill="x", expand=True)
        
        self.rows.append({'label': lbl_status, 'pbar': pbar})
        self.root.update()

    def set_worker_task(self, index, filename, total_pages):
        """Called when a worker STARTS a file"""
        if 0 <= index < len(self.rows):
            if len(filename) > 28: filename = filename[:25] + "..."
            self.rows[index]['label'].config(text=filename)
            self.rows[index]['pbar']['maximum'] = total_pages
            self.rows[index]['pbar']['value'] = 0

    def update_worker_progress(self, index, current_page):
        """Called when a worker finishes a page"""
        if 0 <= index < len(self.rows):
            self.rows[index]['pbar']['value'] = current_page

    def update_global(self, current, cpu, ram, worker_count):
        self.pbar_global["value"] = current
        
        pct = (current / self.total_files) * 100
        
        elapsed = time.time() - self.start_time
        eta_str = "--:--"
        if current > 0 and elapsed > 5:
            rate = current / elapsed
            remaining = self.total_files - current
            if rate > 0:
                eta_s = remaining / rate
                eta_str = f"{int(eta_s//60)}m {int(eta_s%60)}s"
        
        self.lbl_global.config(text=f"Progress: {current}/{self.total_files} ({pct:.1f}%)  •  ETA: {eta_str}")
        self.lbl_stats.config(text=f"Workers: {worker_count}  |  CPU: {cpu}%  |  RAM: {ram:.1f}%")
        self.root.update()

    def close(self):
        self.root.destroy()