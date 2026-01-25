# Quick Guide: Adding vnstock API Key to Local Environment

## ⚠️ IMPORTANT: Keep API Key Secret!

**DO NOT:**
- ❌ Share API key in chat/email
- ❌ Commit to GitHub
- ❌ Post in public forums

**API key is like a password - keep it private!**

---

## 📝 Steps to Add API Key Locally

### Step 1: Get Your API Key

You should have received it after registering at https://vnstocks.com/login

It looks like: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` (long string)

---

### Step 2: Add to `.env` File

Open file: `e:\Cao Phi\Code\stockvn\.env`

Add this line:
```
VNSTOCK_API_KEY=your_actual_api_key_here
```

**Example:**
```
# Google Sheets
SPREADSHEET_ID=1qD2kGp-DjdhjVBqpeBsCZNVcswQMGl4zZbQQk5aLwGrg

# vnstock API
VNSTOCK_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMTIzNDU2Nzg5MCIsImV4cCI6MTY3ODg4ODg4OH0.abcdefghijklmnopqrstuvwxyz123456
```

---

### Step 3: Save File

Save `.env` and close.

**Note:** `.env` is already in `.gitignore`, so it won't be pushed to GitHub ✅

---

### Step 4: Test

```powershell
# Test with price.py
python price.py --period 1w --interval 1D --tickers VNM

# You should see:
# [INFO] Using vnstock with API key (60 req/min)
```

If you see `[WARN] Using vnstock without API key`, the API key wasn't loaded correctly.

---

## 🐛 Troubleshooting

### API Key Not Working?

1. **Check `.env` format:**
   - No spaces around `=`
   - No quotes around key
   - Correct: `VNSTOCK_API_KEY=abc123`
   - Wrong: `VNSTOCK_API_KEY = "abc123"`

2. **Restart terminal:**
   - Close and reopen PowerShell
   - `.env` is loaded when script starts

3. **Check key is valid:**
   - Login to https://vnstocks.com
   - Verify key is active

---

## ✅ Verification

After adding API key, run:

```powershell
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('API Key loaded!' if os.getenv('VNSTOCK_API_KEY') else 'API Key NOT found')"
```

Should print: `API Key loaded!`

---

## 🔐 Security Checklist

- [x] API key in `.env` file
- [x] `.env` in `.gitignore`
- [x] Never share API key
- [x] Never commit API key to GitHub
- [x] API key only in local `.env` and GitHub Secrets

---

## 📊 Rate Limits

| Plan | Rate Limit |
|------|------------|
| Guest (no key) | 20 req/min |
| Community (free key) | 60 req/min |
| Sponsor | 180-600 req/min |

With free API key, you get **3x more requests**! 🚀
