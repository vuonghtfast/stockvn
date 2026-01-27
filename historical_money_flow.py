# -*- coding: utf-8 -*-
"""
Historical Money Flow - Cào dữ liệu dòng tiền quá khứ
Tính toán dòng tiền và định giá cho dữ liệu lịch sử
"""

import pandas as pd
from vnstock import Vnstock
import gspread
from datetime import datetime, timedelta
import os
import sys
import argparse
from dotenv import load_dotenv
from config import get_google_credentials
from sectors import get_sector
from money_flow import calculate_valuation, get_financial_data

# Load environment variables
load_dotenv()

# Command Line Arguments
parser = argparse.ArgumentParser(description='Cào dữ liệu dòng tiền lịch sử')
parser.add_argument('--days', type=int, default=30, 
                    help='Số ngày lịch sử (default: 30)')
parser.add_argument('--start-date', type=str,
                    help='Ngày bắt đầu (YYYY-MM-DD)')
parser.add_argument('--end-date', type=str,
                    help='Ngày kết thúc (YYYY-MM-DD)')
args = parser.parse_args()

print(f"[CONFIG] Cào dữ liệu dòng tiền lịch sử")

# Kết nối Google Sheets
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

# Get tickers
try:
    tickers_sheet = spreadsheet.worksheet("tickers")
    tickers = tickers_sheet.col_values(1)[1:]  # Skip header
    print(f"[i] Tracking {len(tickers)} tickers")
except Exception as e:
    print(f"[X] Failed to read tickers: {e}")
    sys.exit(1)

# Initialize vnstock
api_key = os.getenv("VNSTOCK_API_KEY")
vs = Vnstock()

# Xác định khoảng thời gian
if args.start_date and args.end_date:
    start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
else:
    end_date = datetime.now()
    start_date = end_date - timedelta(days=args.days)

print(f"\n[i] Cào dữ liệu từ {start_date.strftime('%Y-%m-%d')} đến {end_date.strftime('%Y-%m-%d')}")

# Hàm tính dòng tiền cho 1 mã trong khoảng thời gian
def calculate_historical_money_flow(ticker, start_date, end_date):
    """Tính dòng tiền lịch sử cho 1 mã"""
    try:
        df = vs.stock(symbol=ticker, source='VCI').quote.history(
            start=start_date.strftime('%Y-%m-%d'),
            end=end_date.strftime('%Y-%m-%d'),
            interval='1D'
        )
        
        if df.empty:
            return None
        
        # Lấy dữ liệu tài chính (dùng chung cho tất cả các ngày)
        financial_data = get_financial_data(ticker)
        sector = get_sector(ticker)
        
        results = []
        for idx, row in df.iterrows():
            # Tính dòng tiền
            price_change = row['close'] - row['open']
            money_flow = price_change * row['volume']
            price_change_pct = (price_change / row['open']) * 100 if row['open'] > 0 else 0
            
            # Tính định giá
            valuation = calculate_valuation(ticker, row['close'], financial_data)
            
            results.append({
                'date': idx.strftime('%Y-%m-%d'),
                'ticker': ticker,
                'sector': sector,
                'open': round(row['open'], 2),
                'close': round(row['close'], 2),
                'volume': int(row['volume']),
                'price_change_pct': round(price_change_pct, 2),
                'money_flow': round(money_flow, 2),
                'money_flow_normalized': round(money_flow / 1e9, 2),  # Tỷ VNĐ
                'pe_ratio': valuation['pe'],
                'pb_ratio': valuation['pb'],
                'ps_ratio': valuation['ps'],
                'market_cap': valuation['market_cap']
            })
        
        return results
    except Exception as e:
        print(f"[X] {ticker}: {e}")
        return None

# Main logic
print(f"\n[START] Cào dữ liệu lịch sử cho {len(tickers)} tickers...")

all_data = []
for idx, ticker in enumerate(tickers, 1):
    print(f"[{idx}/{len(tickers)}] {ticker}...", end=" ", flush=True)
    
    flow_data = calculate_historical_money_flow(ticker, start_date, end_date)
    if flow_data:
        all_data.extend(flow_data)
        print(f"OK | {len(flow_data)} days")
    else:
        print("No data")

if not all_data:
    print("[X] No data collected")
    sys.exit(1)

# Tạo DataFrame
df = pd.DataFrame(all_data)

print(f"\n[i] Collected {len(df)} records")

# Lưu vào historical_flow sheet
try:
    try:
        hist_ws = spreadsheet.worksheet("historical_flow")
    except gspread.WorksheetNotFound:
        hist_ws = spreadsheet.add_worksheet(title="historical_flow", rows="50000", cols="20")
    
    # Append hoặc overwrite
    existing_data = hist_ws.get_all_records()
    if existing_data:
        existing_df = pd.DataFrame(existing_data)
        
        # Xóa dữ liệu trùng ngày
        existing_df = existing_df[~existing_df['date'].isin(df['date'].unique())]
        
        # Gộp
        combined_df = pd.concat([existing_df, df], ignore_index=True)
        combined_df = combined_df.sort_values(['date', 'ticker'])
    else:
        combined_df = df.sort_values(['date', 'ticker'])
    
    # Ghi lại
    hist_ws.clear()
    hist_ws.update([combined_df.columns.values.tolist()] + combined_df.astype(str).values.tolist())
    print(f"\n[OK] Saved {len(df)} new records to historical_flow (total: {len(combined_df)})")
except Exception as e:
    print(f"[X] Failed to save data: {e}")

# Tạo daily summary
try:
    # Group by date and sector
    daily_summary = df.groupby(['date', 'sector']).agg({
        'money_flow_normalized': 'sum',
        'price_change_pct': 'mean',
        'pe_ratio': 'mean',
        'pb_ratio': 'mean',
        'ticker': 'count'
    }).reset_index()
    
    daily_summary.columns = ['date', 'sector', 'total_flow', 'avg_price_change', 'avg_pe', 'avg_pb', 'stock_count']
    
    # Lưu vào historical_flow_summary
    try:
        summary_ws = spreadsheet.worksheet("historical_flow_summary")
    except gspread.WorksheetNotFound:
        summary_ws = spreadsheet.add_worksheet(title="historical_flow_summary", rows="10000", cols="15")
    
    # Append hoặc overwrite
    existing_summary = summary_ws.get_all_records()
    if existing_summary:
        existing_summary_df = pd.DataFrame(existing_summary)
        # Xóa dữ liệu trùng ngày
        existing_summary_df = existing_summary_df[~existing_summary_df['date'].isin(daily_summary['date'].unique())]
        combined_summary = pd.concat([existing_summary_df, daily_summary], ignore_index=True)
        combined_summary = combined_summary.sort_values(['date', 'sector'])
    else:
        combined_summary = daily_summary.sort_values(['date', 'sector'])
    
    summary_ws.clear()
    summary_ws.update([combined_summary.columns.values.tolist()] + combined_summary.astype(str).values.tolist())
    print(f"[OK] Updated historical_flow_summary")
    
except Exception as e:
    print(f"[X] Failed to create summary: {e}")

print("\n[DONE] Historical money flow collection complete!")
print(f"\n[i] Tip: Bạn có thể xem dữ liệu trong sheets:")
print(f"   - historical_flow: Dữ liệu chi tiết theo ngày")
print(f"   - historical_flow_summary: Tổng hợp theo ngành")
