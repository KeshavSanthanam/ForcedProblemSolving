import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import keyboard
import PyPDF2
import time
import json
import sys
import os
from datetime import datetime, time as dt_time

# Configuration constants
CONFIG_FILE = "config.json"
RESPONSE_FILE = "user_responses.json"
QUESTIONS_DIR = "questions"
ANSWERS_DIR = "answers"
DEFAULT_CONFIG = {
    "activation_time": "06:00",
    "min_words": 10,
    "word_limit": 4,
    "allowed_config_window": [17, 23],
    "review_time": 10
}

def load_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return DEFAULT_CONFIG.copy()

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def save_response(answer_text, word_count, config, pdf_name):
    response_data = {
        "timestamp": datetime.now().isoformat(),
        "pdf_name": pdf_name,
        "word_count": word_count,
        "min_words_required": config['min_words'],
        "activation_time": config['activation_time'],
        "answer": answer_text
    }
    
    try:
        with open(RESPONSE_FILE, 'r') as f:
            existing_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        existing_data = []
    
    existing_data.append(response_data)
    
    with open(RESPONSE_FILE, 'w') as f:
        json.dump(existing_data, f, indent=2)

class PDFManager:
    def __init__(self):
        self.question_pdfs = []
        self.answer_pdfs = []
    
    def load_pdfs(self):
        # Load questions
        if not os.path.exists(QUESTIONS_DIR):
            os.makedirs(QUESTIONS_DIR)
        self.question_pdfs = self._load_pdf_folder(QUESTIONS_DIR)
        
        # Load answers
        if not os.path.exists(ANSWERS_DIR):
            os.makedirs(ANSWERS_DIR)
        self.answer_pdfs = self._load_pdf_folder(ANSWERS_DIR)
        
        return len(self.question_pdfs) > 0
    
    def _load_pdf_folder(self, folder):
        pdfs = []
        for filename in sorted(os.listdir(folder)):
            if filename.lower().endswith(".pdf"):
                file_path = os.path.join(folder, filename)
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    content = "\n".join([page.extract_text() for page in reader.pages])
                    pdfs.append({
                        "path": file_path,
                        "name": filename,
                        "content": content,
                        "viewed": False
                    })
        return pdfs

class ReviewWindow(tk.Toplevel):
    def __init__(self, parent, pdf_manager, config):
        super().__init__(parent)
        self.pdf_manager = pdf_manager
        self.config = config
        self.all_pdfs = pdf_manager.question_pdfs + pdf_manager.answer_pdfs
        self.current_pdf_index = 0
        self.start_time = time.time()
        
        self.title("Review Answers")
        self.geometry("800x600")
        self.attributes('-fullscreen', True)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.setup_ui()
        self.show_current_pdf()
    
    def setup_ui(self):
        # Control frame
        self.control_frame = tk.Frame(self)
        self.control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.timer_label = tk.Label(self.control_frame, text="Time remaining: 10s", font=('Arial', 12))
        self.timer_label.pack(side=tk.LEFT)
        
        self.progress_label = tk.Label(self.control_frame, text="", font=('Arial', 12))
        self.progress_label.pack(side=tk.RIGHT)
        
        # PDF display
        self.pdf_frame = tk.Frame(self)
        self.pdf_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.pdf_title = tk.Label(self.pdf_frame, text="", font=('Arial', 14, 'bold'))
        self.pdf_title.pack(anchor=tk.W)
        
        self.pdf_content = tk.Text(self.pdf_frame, wrap=tk.WORD)
        self.pdf_content.pack(fill=tk.BOTH, expand=True)
        self.pdf_content.config(state=tk.DISABLED)
        
        # Navigation buttons
        self.nav_frame = tk.Frame(self)
        self.nav_frame.pack(pady=10)
        
        self.prev_btn = tk.Button(
            self.nav_frame,
            text="Previous",
            command=self.prev_pdf,
            state=tk.DISABLED
        )
        self.prev_btn.pack(side=tk.LEFT, padx=5)
        
        self.next_btn = tk.Button(
            self.nav_frame,
            text="Next",
            command=self.next_pdf,
            state=tk.DISABLED
        )
        self.next_btn.pack(side=tk.LEFT, padx=5)
        
        self.done_btn = tk.Button(
            self.nav_frame,
            text="Finish",
            command=self.destroy,
            state=tk.DISABLED
        )
        self.done_btn.pack(side=tk.LEFT, padx=5)
        
        # Start timer check
        self.after(1000, self.check_view_time)
    
    def show_current_pdf(self):
        self.start_time = time.time()
        current_pdf = self.all_pdfs[self.current_pdf_index]
        current_pdf['viewed'] = True
        
        self.pdf_title.config(text=f"Reviewing: {current_pdf['name']}")
        self.progress_label.config(text=f"{self.current_pdf_index + 1}/{len(self.all_pdfs)}")
        
        self.pdf_content.config(state=tk.NORMAL)
        self.pdf_content.delete(1.0, tk.END)
        self.pdf_content.insert(tk.END, current_pdf['content'])
        self.pdf_content.config(state=tk.DISABLED)
        
        # Update navigation buttons
        self.prev_btn.config(state=tk.NORMAL if self.current_pdf_index > 0 else tk.DISABLED)
        self.next_btn.config(state=tk.DISABLED)
        self.done_btn.config(state=tk.DISABLED)
    
    def check_view_time(self):
        elapsed = time.time() - self.start_time
        remaining = self.config['review_time'] - int(elapsed)
        self.timer_label.config(text=f"Time remaining: {remaining}s")
        
        if elapsed >= self.config['review_time']:
            self.next_btn.config(state=tk.NORMAL)
            self.done_btn.config(state=tk.NORMAL if self.all_viewed() else tk.DISABLED)
            self.timer_label.config(text="Ready to continue")
        else:
            self.after(1000, self.check_view_time)
    
    def all_viewed(self):
        return all(pdf['viewed'] for pdf in self.all_pdfs)
    
    def next_pdf(self):
        if self.current_pdf_index < len(self.all_pdfs) - 1:
            self.current_pdf_index += 1
            self.show_current_pdf()
            self.check_view_time()
    
    def prev_pdf(self):
        if self.current_pdf_index > 0:
            self.current_pdf_index -= 1
            self.show_current_pdf()
            self.check_view_time()
    
    def on_close(self):
        if self.all_viewed():
            self.destroy()
        else:
            messagebox.showwarning("Incomplete", "You must view all PDFs before closing!")

class ProductivityLock(tk.Tk):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.pdf_manager = PDFManager()
        
        if not self.pdf_manager.load_pdfs():
            messagebox.showerror("Error", f"No PDFs found in {QUESTIONS_DIR} directory!")
            sys.exit()
            
        self.current_pdf_index = 0
        self.setup_ui()
        self.setup_security()
        self.last_word_time = time.time()
        self.previous_word_count = 0
        self.show_current_pdf()
    
    def setup_ui(self):
        self.attributes('-fullscreen', True)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # PDF display
        self.pdf_frame = tk.Frame(self)
        self.pdf_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.pdf_title = tk.Label(self.pdf_frame, text="", font=('Arial', 14, 'bold'))
        self.pdf_title.pack(anchor=tk.W)
        
        self.pdf_content = tk.Text(self.pdf_frame, wrap=tk.WORD, height=15)
        self.pdf_content.pack(fill=tk.BOTH, expand=True)
        self.pdf_content.config(state=tk.DISABLED)
        
        # Answer input
        self.text_area = tk.Text(self, wrap=tk.WORD, height=10)
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Word count
        self.word_count_label = tk.Label(self, text="Words: 0/10", font=('Arial', 14))
        self.word_count_label.pack()
        
        # Submit button
        self.submit_btn = tk.Button(
            self,
            text="Submit and Continue",
            command=self.next_pdf,
            state=tk.DISABLED,
            bg='gray'
        )
        self.submit_btn.pack(pady=10)
    
    def setup_security(self):
        for key in ['alt', 'tab', 'win', 'ctrl']:
            keyboard.block_key(key)
            
        self.text_area.bind('<KeyPress>', self.check_typing_speed)
        self.text_area.bind('<Control-v>', lambda e: 'break')
        self.text_area.bind('<Control-c>', lambda e: 'break')
    
    def show_current_pdf(self):
        current_pdf = self.pdf_manager.question_pdfs[self.current_pdf_index]
        self.pdf_title.config(text=f"Question: {current_pdf['name']}")
        
        self.pdf_content.config(state=tk.NORMAL)
        self.pdf_content.delete(1.0, tk.END)
        self.pdf_content.insert(tk.END, current_pdf['content'])
        self.pdf_content.config(state=tk.DISABLED)
        
        self.text_area.delete(1.0, tk.END)
        self.update_word_count()
    
    def check_typing_speed(self, event):
        current_text = self.text_area.get("1.0", 'end-1c')
        current_words = current_text.split()
        current_word_count = len(current_words)
        
        self.update_word_count(current_word_count)
        
        if current_word_count > self.previous_word_count:
            time_since_last_word = time.time() - self.last_word_time
            allowed_time = 1 / self.config['word_limit']
            
            if time_since_last_word < allowed_time:
                last_space = current_text.rfind(' ', 0, len(current_text)-1)
                if last_space != -1:
                    self.text_area.delete(f'1.0+{last_space}c', 'end')
                else:
                    self.text_area.delete('1.0', 'end')
                self.show_warning("Typing too fast! Maximum 4 words/second")
            
            self.last_word_time = time.time()
            self.previous_word_count = len(self.text_area.get("1.0", 'end-1c').split())
    
    def update_word_count(self, count=None):
        count = len(self.text_area.get("1.0", 'end-1c').split()) if count is None else count
        self.word_count_label.config(text=f"Words: {count}/{self.config['min_words']}")
        self.submit_btn.config(
            state=tk.NORMAL if count >= self.config['min_words'] else tk.DISABLED,
            bg='green' if count >= self.config['min_words'] else 'gray'
        )
    
    def next_pdf(self):
        if len(self.text_area.get("1.0", 'end-1c').split()) >= self.config['min_words']:
            save_response(
                self.text_area.get("1.0", 'end-1c'),
                self.previous_word_count,
                self.config,
                self.pdf_manager.question_pdfs[self.current_pdf_index]['name']
            )
            
            self.current_pdf_index += 1
            if self.current_pdf_index < len(self.pdf_manager.question_pdfs):
                self.show_current_pdf()
                self.previous_word_count = 0
                self.last_word_time = time.time()
            else:
                self.show_review_window()
                self.destroy()
    
    def show_review_window(self):
        ReviewWindow(self, self.pdf_manager, self.config)
    
    def show_warning(self, message):
        warning = tk.Toplevel(self)
        warning.title("Warning")
        tk.Label(warning, text=message, fg='red', font=('Arial', 12)).pack(padx=20, pady=10)
        warning.after(2000, warning.destroy)
    
    def on_close(self):
        if messagebox.askyesno("Quit", "Are you sure? Unsaved progress will be lost!"):
            self.destroy()

class ConfigEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.title("Configuration")
        self.geometry("300x200")
        
        tk.Label(self, text="Activation Time (HH:MM):").pack()
        self.time_entry = tk.Entry(self)
        self.time_entry.insert(0, self.config['activation_time'])
        self.time_entry.pack()
        
        tk.Label(self, text="Minimum Words:").pack()
        self.words_entry = tk.Entry(self)
        self.words_entry.insert(0, str(self.config['min_words']))
        self.words_entry.pack()
        
        tk.Button(self, text="Save", command=self.save_settings).pack(pady=10)
    
    def save_settings(self):
        try:
            datetime.strptime(self.time_entry.get(), "%H:%M")
            int(self.words_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid input format")
            return
        
        self.config['activation_time'] = self.time_entry.get()
        self.config['min_words'] = int(self.words_entry.get())
        save_config(self.config)
        self.destroy()

def should_activate(config):
    now = datetime.now().time()
    try:
        activation_time = datetime.strptime(config['activation_time'], "%H:%M").time()
    except ValueError:
        activation_time = dt_time(6, 0)
    return now >= activation_time

def in_config_window(config):
    current_hour = datetime.now().hour
    start, end = config['allowed_config_window']
    return start <= current_hour < end

if __name__ == "__main__":
    config = load_config()
    
    if should_activate(config):
        app = ProductivityLock()
        app.mainloop()
    elif in_config_window(config):
        config_app = ConfigEditor()
        config_app.mainloop()
    else:
        sys.exit()