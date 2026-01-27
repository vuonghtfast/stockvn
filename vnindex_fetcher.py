# -*- coding: utf-8 -*-
"""
VN Index Fetcher - Lấy chỉ số VN-Index và lưu vào Google Sheets
Chạy 4 lần/ngày: 9:30, 11:00, 14:00, 15:00
"""

import pandas as pd
from vnstock import Vnstock
import gspread
from datetime import datetime
import os
import sys
from dotenv import load_dotenv
from config import get_google_credentials
from vietnam_holidays import is_trading_day

# Load environment variables
load_dotenv()

print(f"[i] VN Index Fetcher - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Check if today is a trading day
if not is_trading_day():
    print("[i] Today is not a trading day (weekend or holiday). Exiting.")
    sys.exit(0)

print("[OK] Trading day confirmed")

# ===== 1. Kết nối Google Sheets =====
try:
    creds = get_google_credentials()
    client = gspread.authorize(creds)
    
    spreadsheet_id = os.getenv("SPREADSHEET_ID")
    if spreadsheet_id:
        spreadsheet = client.open_by_key(spreadsheet_id)
    else:
        spreadsheet = client.open("stockdata")
    
    print(f"[OK] Connected to Google Sheets: {spreadsheet.title}")
except Exception as e:
    print(f"[X] Failed to connect to Google Sheets: {e}")
    sys.exit(1)

# ===== 2. Initialize vnstock =====
api_key = os.getenv("VNSTOCK_API_KEY")
if api_key:
    print("[i] Using vnstock with API key (60 req/min)")
else:
    print("[!] Using vnstock without API key (20 req/min)")

vs = Vnstock()

# ===== 3. Fetch VN-Index =====
try:
    print("[i] Fetching VN-Index data...")
    
    # Lấy dữ liệu VN-Index
    # VN-Index symbol trong vnstock là "VNINDEX"
    vnindex_data = vs.stock(symbol="VNINDEX", source='VCI').quote.history(
        start=(datetime.now().replace(hour=0, minute=0, second=0)).strftime('%Y-%m-%d'),
        end=datetime.now().strftime('%Y-%m-%d'),
        interval='1D'
    )
    
    if vnindex_data.empty:
        print("[X] No VN-Index data returned")
        sys.exit(1)
    
    latest = vnindex_data.iloc[-1]
    
    # Tính toán thay đổi
    if len(vnindex_data) > 1:
        prev = vnindex_data.iloc[-2]
        change = latest['close'] - prev['close']
        change_pct = (change / prev['close']) * 100
    else:
        # Nếu chỉ có 1 ngày, tính từ open
        change = latest['close'] - latest['open']
        change_pct = (change / latest['open']) * 100 if latest['open'] > 0 else 0
    
    vnindex_record = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'date': datetime.now().strftime('%Y-%m-%d'),
        'time': datetime.now().strftime('%H:%M:%S'),
        'value': round(latest['close'], 2),
        'open': round(latest['open'], 2),
        'high': round(latest['high'], 2),
        'low': round(latest['low'], 2),
        'volume': int(latest['volume']),
        'change': round(change, 2),
        'change_pct': round(change_pct, 2)
    }
    
    print(f"[OK] VN-Index: {vnindex_record['value']:.2f} ({vnindex_record['change']:+.2f}, {vnindex_record['change_pct']:+.2f}%)")
    
except Exception as e:
    print(f"[X] Failed to fetch VN-Index: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ===== 4. Lưu vào Google Sheets =====
try:
    # Tạo hoặc lấy sheet vnindex
    try:
        vnindex_ws = spreadsheet.worksheet("vnindex")
    except gspread.WorksheetNotFound:
        vnindex_ws = spreadsheet.add_worksheet(title="vnindex", rows="1000", cols="15")
        # Thêm header
        vnindex_ws.update('A1:J1', [[
            'timestamp', 'date', 'time', 'value', 'open', 'high', 'low', 
            'volume', 'change', 'change_pct'
        ]])
        print("[i] Created new 'vnindex' sheet")
    
    # Lấy dữ liệu hiện tại
    existing_data = vnindex_ws.get_all_records()
    
    if existing_data:
        existing_df = pd.DataFrame(existing_data)
        
        # Xóa dữ liệu cùng ngày (giữ lại lịch sử các ngày khác)
        today = datetime.now().strftime('%Y-%m-%d')
        existing_df = existing_df[existing_df['date'] != today]
        
        # Thêm record mới
        new_df = pd.concat([existing_df, pd.DataFrame([vnindex_record])], ignore_index=True)
    else:
        new_df = pd.DataFrame([vnindex_record])
    
    # Giới hạn 1000 records (khoảng 250 ngày giao dịch với 4 updates/ngày)
    if len(new_df) > 1000:
        new_df = new_df.tail(1000)
    
    # Ghi lại
    vnindex_ws.clear()
    vnindex_ws.update([new_df.columns.values.tolist()] + new_df.astype(str).values.tolist())
    
    print(f"[OK] Saved VN-Index to Google Sheets (total records: {len(new_df)})")
    
except Exception as e:
    print(f"[X] Failed to save to Google Sheets: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("[DONE] VN-Index update complete!")
