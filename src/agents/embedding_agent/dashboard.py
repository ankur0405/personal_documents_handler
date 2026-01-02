import time
import tkinter as tk
from tkinter import ttk

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
    def __init__(self, total_files, min_workers, title="System Pipeline"):
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry("800x600")
        self.root.attributes("-topmost", True) 
        self.root.configure(bg=THEME["bg_main"])
        
        self._setup_styles()
        
        # --- HEADER ---
        self.header_frame = tk.Frame(self.root, bg=THEME["bg_main"], pady=10)
        self.header_frame.pack(fill="x")
        self.lbl_title = tk.Label(self.header_frame, text=title, font=THEME["font_header"], bg=THEME["bg_main"], fg=THEME["text_main"])
        self.lbl_title.pack()
        
        # --- CONTENT FRAME (Swappable) ---
        self.content_frame = tk.Frame(self.root, bg=THEME["bg_main"])
        self.content_frame.pack(fill="both", expand=True)
        
        # === VIEW 1: PROGRESS ===
        self.progress_container = tk.Frame(self.content_frame, bg=THEME["bg_main"])
        self.progress_container.pack(fill="both", expand=True)
        
        self.lbl_global = tk.Label(self.progress_container, text=f"Total Progress: 0/{total_files}", font=THEME["font_main"], bg=THEME["bg_main"], fg=THEME["text_sec"])
        self.lbl_global.pack(pady=(0,5))
        
        self.pbar_global = ttk.Progressbar(self.progress_container, length=750, mode="determinate", style="Horizontal.TProgressbar")
        self.pbar_global.pack(pady=(0, 15))
        self.pbar_global["maximum"] = total_files

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
        
        self.rows = []
        for i in range(min_workers): self.add_row(i)
        
        # --- FOOTER ---
        self.lbl_stats = tk.Label(self.root, text="System: Initializing...", font=THEME["font_mono"], bg=THEME["bg_main"], fg=THEME["accent"], pady=10)
        self.lbl_stats.pack(side="bottom")
        
        self.start_time = time.time()
        self.total_files = total_files
        self.root.update()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Horizontal.TProgressbar", background=THEME["accent"], troughcolor="#555555", bordercolor=THEME["bg_main"])
        
        # Treeview Styles (Dark Mode)
        style.configure("Treeview", 
                        background=THEME["bg_container"],
                        foreground=THEME["text_main"], 
                        fieldbackground=THEME["bg_container"],
                        rowheight=25)
        style.configure("Treeview.Heading", 
                        background="#444", 
                        foreground="white", 
                        font=("Helvetica", 10, "bold"))
        style.map("Treeview", background=[('selected', THEME["accent"])])

    def add_row(self, index):
        row_frame = tk.Frame(self.scrollable_frame, bg=THEME["bg_row"], pady=4, padx=5)
        row_frame.pack(fill="x", padx=2, pady=3)
        
        tk.Label(row_frame, text=f"W-{index:02d}", width=5, font=THEME["font_mono"], bg="#555", fg="white").pack(side="left", padx=(0, 10))
        
        lbl_status = tk.Label(row_frame, text="Idle", width=35, anchor="w", font=THEME["font_main"], bg=THEME["bg_row"], fg=THEME["text_main"])
        lbl_status.pack(side="left", fill="x", expand=True)
        
        pbar = ttk.Progressbar(row_frame, length=120, mode="determinate", style="Horizontal.TProgressbar")
        pbar.pack(side="right", padx=10)
        
        self.rows.append({'label': lbl_status, 'pbar': pbar})
        self.root.update()

    def set_worker_task(self, index, filename, total_pages):
        if 0 <= index < len(self.rows):
            if len(filename) > 40: filename = "..." + filename[-37:]
            self.rows[index]['label'].config(text=filename, fg=THEME["text_main"])
            self.rows[index]['pbar']['maximum'] = total_pages
            self.rows[index]['pbar']['value'] = 0

    def update_worker_progress(self, index, current_page):
        if 0 <= index < len(self.rows):
            self.rows[index]['pbar']['value'] = current_page

    def update_global(self, current, cpu, ram, worker_count):
        self.pbar_global["value"] = current
        pct = (current / self.total_files) * 100 if self.total_files > 0 else 0
        
        elapsed = time.time() - self.start_time
        eta_str = "--:--"
        if current > 0 and elapsed > 5:
            rate = current / elapsed
            remaining = self.total_files - current
            if rate > 0:
                eta_s = remaining / rate
                eta_str = f"{int(eta_s//60)}m {int(eta_s%60)}s"
        
        self.lbl_global.config(text=f"Total Progress: {current}/{self.total_files} ({pct:.1f}%)   •   ETA: {eta_str}")
        self.lbl_stats.config(text=f"Workers: {worker_count}  |  CPU: {cpu}%  |  RAM: {ram:.1f}%", fg=THEME["text_sec"])
        self.root.update()

    # --- REPORT MODE ---
    def show_report(self, failures):
        """Switches view to a failure grid report"""
        self.progress_container.destroy() # Remove progress bars
        self.lbl_stats.config(text=f"Final Report: {len(failures)} Failed Files", fg=THEME["error"])
        self.lbl_title.config(text="Processing Complete - Failure Report")
        
        # Container
        report_frame = tk.Frame(self.content_frame, bg=THEME["bg_main"], padx=10, pady=10)
        report_frame.pack(fill="both", expand=True)
        
        # Treeview (Grid)
        cols = ("Filename", "Reason", "Action", "Path")
        tree = ttk.Treeview(report_frame, columns=cols, show="headings", height=15)
        
        # Column Config
        tree.heading("Filename", text="File Name")
        tree.column("Filename", width=200)
        
        tree.heading("Reason", text="Failure Reason")
        tree.column("Reason", width=250)
        
        tree.heading("Action", text="Corrective Action")
        tree.column("Action", width=200)

        tree.heading("Path", text="Full Path")
        tree.column("Path", width=100) # Can be hidden or scrolled
        
        # Scrollbar
        vsb = ttk.Scrollbar(report_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        
        # Insert Data
        for f in failures:
            tree.insert("", "end", values=(f['filename'], f['error'], f['action'], f['path']))
            
        # Close Button
        btn_close = tk.Button(self.root, text="Close Report", bg="#444", fg="white", command=self.root.destroy)
        btn_close.pack(side="bottom", pady=15)
        
        # Switch to blocking loop so window stays open
        self.root.mainloop()

    def close(self):
        self.root.destroy()