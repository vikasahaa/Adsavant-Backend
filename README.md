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
python -m venv .venv
```

## 2. Activate the Environment

### Windows
```powershell
.venv\Scripts\activate
```

### 3. Install Dependencies

```powershell
pip install numpy==1.26.4 scikit-learn==1.6.1
pip install -r requirements.txt
```
### 4. Run the Server

```powershell
uvicorn app.main:app --reload
```
