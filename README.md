# Productivity Lock 🔒

A Windows app that forces you to complete PDF-based questions during set times. Blocks distractions and enforces typing discipline.

## Features
- 📁 Load PDF questions from `/questions`
- ⏳ Time-based activation
- ⌨️ Typing speed & word limits
- 📝 Saves responses to JSON
- 🔍 Mandatory answer review phase

## Install
```bash
pip install tkinter keyboard PyPDF2
```

# Usage 
```bash
# Build executable (requires pyinstaller):
pyinstaller --noconsole --onefile productivity_lock.py

# Run compiled version:
dist/productivity_lock.exe
```