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

def save_response(answer_text, word_count, config):
    """Save response to JSON file with metadata"""
    response_data = {
        "timestamp": datetime.now().isoformat(),
        "word_count": word_count,
        "min_words_required": config['min_words'],
        "activation_time": config['activation_time'],
        "answer": answer_text
    }
    
    # Load existing data or create new list
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
        self.questions = []
        self.answers = []
    
    def load_pdf(self, is_answers=False):
        file_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if file_path:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = "\n".join([page.extract_text() for page in reader.pages])
                
            if is_answers:
                self.answers.append(text)
            else:
                self.questions.append(text)
            return text

class ProductivityLock:
    def __init__(self):
        self.config = load_config()
        self.root = tk.Tk()
        self.setup_gui()
        self.setup_security()
        self.last_word_time = time.time()
        self.previous_word_count = 0
        
    def setup_gui(self):
        self.root.attributes('-fullscreen', True)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Text input area
        self.text_area = tk.Text(self.root, wrap=tk.WORD)
        self.text_area.pack(expand=True, fill='both', padx=20, pady=20)
        
        # Word count display
        self.word_count_label = tk.Label(self.root, text="Words: 0/10", font=('Arial', 14))
        self.word_count_label.pack(side=tk.TOP, pady=5)
        
        # Close button
        self.close_button = tk.Button(
            self.root, 
            text="Submit and Close", 
            command=self.on_close,
            state=tk.DISABLED,
            bg='gray',
            font=('Arial', 12)
        )
        self.close_button.pack(side=tk.BOTTOM, pady=20)
        
    def setup_security(self):
        for key in ['alt', 'tab', 'win', 'ctrl']:
            keyboard.block_key(key)
            
        self.text_area.bind('<KeyPress>', self.check_typing_speed)
        self.text_area.bind('<Control-v>', lambda e: 'break')
        self.text_area.bind('<Control-c>', lambda e: 'break')
    
    def check_typing_speed(self, event):
        current_text = self.text_area.get("1.0", 'end-1c')
        current_words = current_text.split()
        current_word_count = len(current_words)
        
        # Update word count display
        self.word_count_label.config(text=f"Words: {current_word_count}/{self.config['min_words']}")
        
        # Enable/disable close button
        if current_word_count >= self.config['min_words']:
            self.close_button.config(state=tk.NORMAL, bg='green')
        else:
            self.close_button.config(state=tk.DISABLED, bg='gray')
        
        # Check word addition speed
        if current_word_count > self.previous_word_count:
            time_since_last_word = time.time() - self.last_word_time
            allowed_time = 1 / self.config['word_limit']
            
            if time_since_last_word < allowed_time:
                # Delete last word if typed too fast
                last_space = current_text.rfind(' ', 0, len(current_text)-1)
                if last_space != -1:
                    self.text_area.delete(f'1.0+{last_space}c', 'end')
                else:
                    self.text_area.delete('1.0', 'end')
                self.show_warning("Typing too fast! Maximum 3 words/second")
            
            self.last_word_time = time.time()
            self.previous_word_count = len(self.text_area.get("1.0", 'end-1c').split())
    
    def show_warning(self, message):
        warning = tk.Toplevel(self.root)
        warning.title("Warning")
        tk.Label(warning, text=message, fg='red', font=('Arial', 12)).pack(padx=20, pady=10)
        warning.after(2000, warning.destroy)
    
    def on_close(self):
        current_text = self.text_area.get("1.0", 'end-1c')
        current_word_count = len(current_text.split())
        
        if current_word_count >= self.config['min_words']:
            save_response(current_text, current_word_count, self.config)
            self.root.destroy()
        else:
            messagebox.showwarning("Incomplete", f"Minimum {self.config['min_words']} words required!")

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