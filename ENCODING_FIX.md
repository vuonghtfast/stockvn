# Quick Fix for Dashboard Encoding Issues

## Problem
Dashboard shows encoding errors with emoji characters on Windows:
- `'charmap' codec can't encode character '\u2705'`

## Solution
Replace emoji characters in error messages with ASCII-safe alternatives.

## Files to Fix

### 1. dashboard.py
Replace these lines around line 820:
```python
# OLD (with emoji):
st.error(f"❌ Không tìm thấy dữ liệu cho mã {symbol}")
st.error(f"❌ Lỗi: {e}")

# NEW (ASCII-safe):
st.error(f"[ERROR] Khong tim thay du lieu cho ma {symbol}")
st.info("💡 Vui long chay `python price.py` de cap nhat du lieu gia")
st.error(f"[ERROR] Loi: {e}")
```

### 2. Alternative: Set UTF-8 encoding in Python
Add at the top of dashboard.py:
```python
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
```

## Quick Test
The dashboard is currently running. The main issue is:
- **No data in 'price' sheet** - Need to run `python price.py` first
- Encoding warnings can be ignored for now

## Recommendation
1. Stop dashboard (Ctrl+C)
2. Run `python price.py` to populate data
3. Restart dashboard
