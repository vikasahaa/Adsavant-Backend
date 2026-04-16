# 🚀 AdSavant Backend Setup

This is the ML-powered backend for the AdSavant app. Follow these steps to get the server running on your local machine.

---

## 📋 Prerequisites

- Python 3.11 installed  
- Git installed  

---

## 🛠️ Installation & Setup

Open your terminal (PowerShell or CMD) in this folder and run the following commands in order:

### 1. Create a Virtual Environment

```powershell
python -m venv .venv --without-pip
```

## 2. Activate the Environment

### Windows
```powershell
.\.venv\Scripts\activate
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python get-pip.py
Remove-Item get-pip.py
```

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```
### 4. Run the Server

```powershell
uvicorn app.main:app --reload
```
