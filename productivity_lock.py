import tkinter as tk
from tkinter import filedialog, messagebox
import keyboard
import PyPDF2
import time
import json
import sys
import os
from datetime import datetime, time as dt_time

CONFIG_FILE = "config.json"
RESPONSE_FILE = "user_responses.json"
QUESTIONS_DIR = "questions"
DEFAULT_CONFIG = {
    "activation_time": "06:00",
    "min_words": 10,
    "word_limit": 3,
    "allowed_config_window": [17, 23]
}

def load_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return DEFAULT_CONFIG.copy()

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

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
        self.pdfs = []
    
    def load_pdfs(self):
        if not os.path.exists(QUESTIONS_DIR):
            os.makedirs(QUESTIONS_DIR)
        
        self.pdfs = []
        for filename in os.listdir(QUESTIONS_DIR):
            if filename.lower().endswith(".pdf"):
                file_path = os.path.join(QUESTIONS_DIR, filename)
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    content = "\n".join([page.extract_text() for page in reader.pages])
                    self.pdfs.append({
                        "name": filename,
                        "content": content
                    })
        return self.pdfs

class ProductivityLock:
    def __init__(self):
        self.config = load_config()
        self.root = tk.Tk()
        self.pdf_manager = PDFManager()
        self.all_pdfs = self.pdf_manager.load_pdfs()
        
        if not self.all_pdfs:
            messagebox.showerror("Error", f"No PDFs found in {QUESTIONS_DIR} directory!")
            sys.exit()
            
        self.current_pdf_index = 0
        self.setup_gui()
        self.setup_security()
        self.last_word_time = time.time()
        self.previous_word_count = 0
        self.show_current_pdf()
        
    def setup_gui(self):
        self.root.attributes('-fullscreen', True)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # PDF display frame
        self.pdf_frame = tk.Frame(self.root)
        self.pdf_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.pdf_title = tk.Label(self.pdf_frame, text="", font=('Arial', 14, 'bold'))
        self.pdf_title.pack(anchor=tk.W)
        
        self.pdf_content = tk.Text(self.pdf_frame, wrap=tk.WORD, height=15)
        self.pdf_content.pack(fill=tk.BOTH, expand=True)
        self.pdf_content.config(state=tk.DISABLED)
        
        # Progress label
        self.progress_label = tk.Label(self.root, text="", font=('Arial', 12))
        self.progress_label.pack(pady=5)
        
        # Answer input area
        self.text_area = tk.Text(self.root, wrap=tk.WORD, height=10)
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Word count display
        self.word_count_label = tk.Label(self.root, text="Words: 0/10", font=('Arial', 14))
        self.word_count_label.pack(side=tk.TOP, pady=5)
        
        # Control buttons
        self.button_frame = tk.Frame(self.root)
        self.button_frame.pack(pady=10)
        
        self.close_button = tk.Button(
            self.button_frame,
            text="Submit and Continue",
            command=self.next_pdf,
            state=tk.DISABLED,
            bg='gray',
            font=('Arial', 12)
        )
        self.close_button.pack(side=tk.LEFT, padx=10)
        
    def setup_security(self):
        for key in ['alt', 'tab', 'win', 'ctrl']:
            keyboard.block_key(key)
            
        self.text_area.bind('<KeyPress>', self.check_typing_speed)
        self.text_area.bind('<Control-v>', lambda e: 'break')
        self.text_area.bind('<Control-c>', lambda e: 'break')
    
    def show_current_pdf(self):
        current_pdf = self.all_pdfs[self.current_pdf_index]
        self.pdf_title.config(text=f"Current Question: {current_pdf['name']}")
        
        self.pdf_content.config(state=tk.NORMAL)
        self.pdf_content.delete(1.0, tk.END)
        self.pdf_content.insert(tk.END, current_pdf['content'])
        self.pdf_content.config(state=tk.DISABLED)
        
        self.progress_label.config(
            text=f"Progress: {self.current_pdf_index + 1} of {len(self.all_pdfs)}"
        )
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
                self.show_warning("Typing too fast! Maximum 3 words/second")
            
            self.last_word_time = time.time()
            self.previous_word_count = len(self.text_area.get("1.0", 'end-1c').split())
    
    def update_word_count(self, count=None):
        if count is None:
            count = len(self.text_area.get("1.0", 'end-1c').split())
        self.word_count_label.config(
            text=f"Words: {count}/{self.config['min_words']}"
        )
        if count >= self.config['min_words']:
            self.close_button.config(state=tk.NORMAL, bg='green')
        else:
            self.close_button.config(state=tk.DISABLED, bg='gray')
    
    def show_warning(self, message):
        warning = tk.Toplevel(self.root)
        warning.title("Warning")
        tk.Label(warning, text=message, fg='red', font=('Arial', 12)).pack(padx=20, pady=10)
        warning.after(2000, warning.destroy)
    
    def next_pdf(self):
        current_text = self.text_area.get("1.0", 'end-1c')
        current_word_count = len(current_text.split())
        
        if current_word_count >= self.config['min_words']:
            save_response(
                current_text,
                current_word_count,
                self.config,
                self.all_pdfs[self.current_pdf_index]['name']
            )
            
            self.current_pdf_index += 1
            if self.current_pdf_index < len(self.all_pdfs):
                self.show_current_pdf()
                self.previous_word_count = 0
                self.last_word_time = time.time()
            else:
                messagebox.showinfo("Complete", "All questions answered!")
                self.root.destroy()
        else:
            messagebox.showwarning("Incomplete", f"Minimum {self.config['min_words']} words required!")
    
    def on_close(self):
        if messagebox.askyesno("Quit", "Are you sure you want to quit? Unsaved progress will be lost!"):
            self.root.destroy()

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
        app.root.mainloop()
    elif in_config_window(config):
        config_app = ConfigEditor()
        config_app.mainloop()
    else:
        sys.exit()