# Local Development Workflow Guide

## 🎯 Workflow: Local Test → GitHub Push

### 1. Test Local Trước

```powershell
# Chạy dashboard local
streamlit run dashboard.py
```

**Kiểm tra:**
- ✅ Dashboard load được không?
- ✅ Các tính năng hoạt động?
- ✅ Không có lỗi?

---

### 2. Fix Lỗi Nếu Có

**Lỗi thường gặp:**

#### A. "No secrets found"
→ **Bình thường!** Local dùng `credentials.json`, không cần `secrets.toml`

#### B. "No data in sheet"
→ Chạy scripts để cào dữ liệu:

```powershell
# Cào dữ liệu giá (cần cho backtest)
python price.py --period 1m --interval 1D --mode historical

# Cào dữ liệu tài chính (cần cho báo cáo)
python finance.py
```

#### C. "Module not found"
→ Cài dependencies:

```powershell
pip install -r requirements.txt
```

---

### 3. Commit Changes

```powershell
# Xem file đã sửa
git status

# Add file
git add .

# Commit với message rõ ràng
git commit -m "fix: mô tả ngắn gọn"
```

---

### 4. Push Lên GitHub

```powershell
git push
```

**Kết quả:**
- ✅ Code lên GitHub
- ✅ Streamlit Cloud tự động redeploy (2-3 phút)
- ✅ GitHub Actions chạy workflows

---

## 🔧 Setup Local Environment

### Lần Đầu

```powershell
# Clone repo (nếu chưa có)
git clone https://github.com/vuonghtfast/stockvn.git
cd stockvn

# Tạo virtual environment
python -m venv venv
venv\Scripts\activate

# Cài dependencies
pip install -r requirements.txt

# Copy credentials
# Đặt credentials.json vào thư mục gốc

# Test
streamlit run dashboard.py
```

---

## 📊 Cấu Trúc Thư Mục

```
stockvn/
├── credentials.json          # Local only (KHÔNG push)
├── .env                       # Local only (KHÔNG push)
├── dashboard.py              # Main app
├── price.py                  # Cào giá
├── finance.py                # Cào tài chính
├── config.py                 # Config chung
├── requirements.txt          # Dependencies
├── .streamlit/
│   ├── config.toml          # Streamlit config (push)
│   └── secrets.toml         # Local secrets (KHÔNG push)
└── .github/
    └── workflows/           # GitHub Actions
```

---

## 🚀 Quick Commands

### Chạy Dashboard
```powershell
streamlit run dashboard.py
```

### Cào Dữ Liệu
```powershell
# Giá (1 tháng)
python price.py --period 1m --interval 1D

# Tài chính
python finance.py
```

### Git Workflow
```powershell
git add .
git commit -m "message"
git push
```

---

## 💡 Tips

1. **Luôn test local trước khi push**
2. **Commit thường xuyên** với message rõ ràng
3. **Dùng `.gitignore`** để không push credentials
4. **Monitor Streamlit Cloud** sau khi push
5. **Xem logs** nếu deploy lỗi

---

## 🐛 Debug Local

### Xem Logs
```powershell
# Streamlit logs hiện trong terminal
# Xem chi tiết lỗi
```

### Test Từng Phần
```python
# Test Google Sheets connection
from config import get_google_credentials
creds = get_google_credentials()
print("✅ Credentials OK")

# Test data fetch
from dashboard import fetch_ticker_list
tickers = fetch_ticker_list()
print(f"✅ Found {len(tickers)} tickers")
```

---

## ✅ Checklist Trước Khi Push

- [ ] Dashboard chạy được local
- [ ] Không có lỗi trong console
- [ ] Các tính năng hoạt động
- [ ] Code đã commit
- [ ] Message commit rõ ràng
- [ ] Đã test với vài mã khác nhau
- [ ] Ready to push!

---

## 🎯 Workflow Hoàn Chỉnh

```
1. Sửa code local
   ↓
2. Test: streamlit run dashboard.py
   ↓
3. Fix lỗi (nếu có)
   ↓
4. Test lại
   ↓
5. git add . && git commit -m "message"
   ↓
6. git push
   ↓
7. Đợi Streamlit Cloud redeploy
   ↓
8. Test trên cloud
   ↓
9. Done! ✅
```
