# Quick Fix for Dashboard Money Flow Error

## Problem
Dashboard crashes with "I/O operation on closed file" when trying to load money flow data.

## Root Cause
The `get_money_flow_data()` function is trying to access Google Sheets but either:
1. The `intraday_flow` sheet doesn't exist yet
2. There's a credentials/connection issue
3. The file handle is being closed prematurely

## Solution
Wrap the money flow section in a try-except block to handle errors gracefully.

## Manual Fix Steps

1. Open `dashboard.py`
2. Find line 737: `money_flow_df = get_money_flow_data()`
3. Wrap the entire money flow section (lines 734-801) in try-except:

```python
# Money Flow Summary
st.markdown("## 💰 Tổng Quan Dòng Tiền")

try:
    money_flow_df = get_money_flow_data()
    
    if money_flow_df is not None and not money_flow_df.empty:
        # ... existing code ...
    else:
        st.warning("⚠️ Chưa có dữ liệu dòng tiền...")
        st.info("💡 Hoặc đợi GitHub Actions...")
except Exception as e:
    st.error(f"Lỗi: {type(e).__name__}")
    st.warning("⚠️ Chưa có dữ liệu dòng tiền. Vui lòng chạy `python money_flow.py --interval 15`")
```

4. Save and reload dashboard

## Alternative: Run money_flow.py first
```bash
python money_flow.py --interval 15
```

This will create the `intraday_flow` sheet and populate it with data.
