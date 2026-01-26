# -*- coding: utf-8 -*-
"""
Money Flow Tracker - Theo dõi dòng tiền theo ngành và cổ phiếu
Tính toán dòng tiền, định giá (P/E, P/B, P/S) và phân tích theo ngành
"""

import pandas as pd
from vnstock import Vnstock
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import os
import sys
import json
import argparse
from dotenv import load_dotenv
from config import get_google_credentials
from sectors import get_sector, get_all_sectors
from vietnam_holidays import is_trading_day, is_trading_hours

# Load environment variables
load_dotenv()

# ===== Command Line Arguments =====
parser = argparse.ArgumentParser(description='Theo dõi dòng tiền và định giá cổ phiếu')
parser.add_argument('--interval', type=int, default=10, 
                    help='Interval in minutes (default: 10)')
parser.add_argument('--cleanup', action='store_true',
                    help='Cleanup intraday data (run at end of day)')
parser.add_argument('--skip-holiday-check', action='store_true',
                    help='Skip holiday check (for testing)')
args = parser.parse_args()

print(f"[CONFIG] Mode: {'Cleanup' if args.cleanup else f'Track (interval: {args.interval} min)'}")

# ===== Check if today is a trading day =====
if not args.cleanup and not args.skip_holiday_check:
    if not is_trading_day():
        print("[INFO] Today is not a trading day (weekend or holiday). Exiting.")
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
    print(f"[ERROR] Failed to connect to Google Sheets: {e}")
    sys.exit(1)

# ===== 2. Get tickers =====
try:
    tickers_sheet = spreadsheet.worksheet("tickers")
    tickers = tickers_sheet.col_values(1)[1:]  # Skip header
    print(f"[INFO] Tracking {len(tickers)} tickers")
except Exception as e:
    print(f"[ERROR] Failed to read tickers: {e}")
    sys.exit(1)

# ===== 3. Initialize vnstock =====
api_key = os.getenv("VNSTOCK_API_KEY")
if api_key:
    print("[INFO] Using vnstock with API key (60 req/min)")
else:
    print("[WARN] Using vnstock without API key (20 req/min)")

vs = Vnstock()

# ===== 4. Helper Functions =====
def get_financial_data(ticker):
    """Lấy dữ liệu tài chính từ Google Sheets"""
    try:
        # Đọc từ income sheet
        income_ws = spreadsheet.worksheet("income")
        income_data = income_ws.get_all_records()
        income_df = pd.DataFrame(income_data)
        
        # Đọc từ balance sheet
        balance_ws = spreadsheet.worksheet("balance")
        balance_data = balance_ws.get_all_records()
        balance_df = pd.DataFrame(balance_data)
        
        # Filter cho ticker hiện tại
        ticker_income = income_df[income_df['ticker'] == ticker]
        ticker_balance = balance_df[balance_df['ticker'] == ticker]
        
        if ticker_income.empty or ticker_balance.empty:
            return None
        
        # Lấy dữ liệu mới nhất
        latest_income = ticker_income.iloc[-1]
        latest_balance = ticker_balance.iloc[-1]
        
        return {
            'eps': pd.to_numeric(latest_income.get('eps', 0), errors='coerce'),
            'revenue': pd.to_numeric(latest_income.get('revenue', 0), errors='coerce'),
            'equity': pd.to_numeric(latest_balance.get('equity', 0), errors='coerce'),
            'shares_outstanding': pd.to_numeric(latest_balance.get('shares_outstanding', 0), errors='coerce')
        }
    except Exception as e:
        print(f"[WARN] Failed to get financial data for {ticker}: {e}")
        return None

def calculate_valuation(ticker, current_price, financial_data):
    """Tính toán P/E, P/B, P/S"""
    if not financial_data:
        return {'pe': None, 'pb': None, 'ps': None, 'market_cap': None}
    
    try:
        # P/E = Price / EPS
        eps = financial_data['eps']
        pe = current_price / eps if eps and eps > 0 else None
        
        # P/B = Price / Book Value per Share
        equity = financial_data['equity']
        shares = financial_data['shares_outstanding']
        book_value = equity / shares if shares and shares > 0 else None
        pb = current_price / book_value if book_value and book_value > 0 else None
        
        # P/S = Market Cap / Revenue
        revenue = financial_data['revenue']
        market_cap = current_price * shares if shares else None
        ps = market_cap / revenue if market_cap and revenue and revenue > 0 else None
        
        return {
            'pe': round(pe, 2) if pe else None,
            'pb': round(pb, 2) if pb else None,
            'ps': round(ps, 2) if ps else None,
            'market_cap': round(market_cap / 1e9, 2) if market_cap else None  # Tỷ VNĐ
        }
    except Exception as e:
        print(f"[WARN] Failed to calculate valuation for {ticker}: {e}")
        return {'pe': None, 'pb': None, 'ps': None, 'market_cap': None}

def calculate_money_flow(ticker):
    """Tính toán dòng tiền cho 1 mã"""
    try:
        # Lấy dữ liệu realtime (1 ngày gần nhất)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)
        
        df = vs.stock(symbol=ticker, source='VCI').quote.history(
            start=start_date.strftime('%Y-%m-%d'),
            end=end_date.strftime('%Y-%m-%d'),
            interval='1D'
        )
        
        if df.empty:
            return None
        
        latest = df.iloc[-1]
        
        # Tính dòng tiền = (close - open) * volume
        price_change = latest['close'] - latest['open']
        money_flow = price_change * latest['volume']
        price_change_pct = (price_change / latest['open']) * 100 if latest['open'] > 0 else 0
        
        # Lấy dữ liệu tài chính
        financial_data = get_financial_data(ticker)
        
        # Tính định giá
        valuation = calculate_valuation(ticker, latest['close'], financial_data)
        
        # Lấy ngành
        sector = get_sector(ticker)
        
        return {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'ticker': ticker,
            'sector': sector,
            'open': round(latest['open'], 2),
            'close': round(latest['close'], 2),
            'volume': int(latest['volume']),
            'price_change_pct': round(price_change_pct, 2),
            'money_flow': round(money_flow, 2),
            'money_flow_normalized': round(money_flow / 1e9, 2),  # Tỷ VNĐ
            'pe_ratio': valuation['pe'],
            'pb_ratio': valuation['pb'],
            'ps_ratio': valuation['ps'],
            'market_cap': valuation['market_cap']
        }
    except Exception as e:
        print(f"[ERROR] {ticker}: {e}")
        return None

# ===== 5. Main Logic =====
if args.cleanup:
    # Cleanup mode: Xóa dữ liệu intraday, giữ lại summary
    print("\n[CLEANUP] Starting cleanup...")
    try:
        # Xóa intraday_flow sheet
        try:
            intraday_ws = spreadsheet.worksheet("intraday_flow")
            intraday_ws.clear()
            print("[OK] Cleared intraday_flow sheet")
        except gspread.WorksheetNotFound:
            print("[INFO] intraday_flow sheet not found, skipping")
        
        print("[OK] Cleanup complete")
    except Exception as e:
        print(f"[ERROR] Cleanup failed: {e}")
        sys.exit(1)
else:
    # Tracking mode
    print(f"\n[START] Tracking money flow for {len(tickers)} tickers...")
    print(f"[INFO] Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_data = []
    for idx, ticker in enumerate(tickers, 1):
        print(f"[{idx}/{len(tickers)}] {ticker}...", end=" ", flush=True)
        
        flow_data = calculate_money_flow(ticker)
        if flow_data:
            all_data.append(flow_data)
            print(f"OK | Flow: {flow_data['money_flow_normalized']:.2f}B | P/E: {flow_data['pe_ratio']}")
        else:
            print("No data")
    
    if not all_data:
        print("[ERROR] No data collected")
        sys.exit(1)
    
    # Tạo DataFrame
    df = pd.DataFrame(all_data)
    
    # ===== 6. Lưu vào intraday_flow sheet =====
    try:
        try:
            intraday_ws = spreadsheet.worksheet("intraday_flow")
        except gspread.WorksheetNotFound:
            intraday_ws = spreadsheet.add_worksheet(title="intraday_flow", rows="10000", cols="20")
        
        # Append data (không xóa dữ liệu cũ trong phiên)
        existing_data = intraday_ws.get_all_records()
        if existing_data:
            existing_df = pd.DataFrame(existing_data)
            combined_df = pd.concat([existing_df, df], ignore_index=True)
        else:
            combined_df = df
        
        # Ghi lại
        intraday_ws.clear()
        intraday_ws.update([combined_df.columns.values.tolist()] + combined_df.astype(str).values.tolist())
        print(f"\n[OK] Saved {len(df)} records to intraday_flow (total: {len(combined_df)})")
    except Exception as e:
        print(f"[ERROR] Failed to save intraday data: {e}")
    
    # ===== 7. Tạo daily summary =====
    try:
        # Tổng hợp theo ngành
        sector_summary = df.groupby('sector').agg({
            'money_flow_normalized': 'sum',
            'price_change_pct': 'mean',
            'pe_ratio': 'mean',
            'pb_ratio': 'mean',
            'ticker': 'count'
        }).reset_index()
        
        sector_summary.columns = ['sector', 'total_flow', 'avg_price_change', 'avg_pe', 'avg_pb', 'stock_count']
        sector_summary = sector_summary.sort_values('total_flow', ascending=False)
        
        # Top 3 ngành
        top_sectors = sector_summary.head(3)
        print("\n[SUMMARY] Top 3 Sectors:")
        for idx, row in top_sectors.iterrows():
            print(f"  {row['sector']}: {row['total_flow']:.2f}B VNĐ | Avg P/E: {row['avg_pe']:.1f} | {int(row['stock_count'])} stocks")
        
        # Top 5 cổ phiếu
        top_stocks = df.nlargest(5, 'money_flow_normalized')
        print("\n[SUMMARY] Top 5 Stocks:")
        for idx, row in top_stocks.iterrows():
            print(f"  {row['ticker']}: {row['money_flow_normalized']:.2f}B | P/E: {row['pe_ratio']} | P/B: {row['pb_ratio']}")
        
        # Lưu summary
        try:
            summary_ws = spreadsheet.worksheet("daily_flow_summary")
        except gspread.WorksheetNotFound:
            summary_ws = spreadsheet.add_worksheet(title="daily_flow_summary", rows="1000", cols="15")
        
        # Thêm timestamp
        sector_summary['date'] = datetime.now().strftime('%Y-%m-%d')
        
        # Append vào summary (không xóa dữ liệu cũ)
        existing_summary = summary_ws.get_all_records()
        if existing_summary:
            existing_summary_df = pd.DataFrame(existing_summary)
            # Xóa summary của ngày hôm nay nếu đã có
            existing_summary_df = existing_summary_df[existing_summary_df['date'] != sector_summary['date'].iloc[0]]
            combined_summary = pd.concat([existing_summary_df, sector_summary], ignore_index=True)
        else:
            combined_summary = sector_summary
        
        summary_ws.clear()
        summary_ws.update([combined_summary.columns.values.tolist()] + combined_summary.astype(str).values.tolist())
        print(f"\n[OK] Updated daily_flow_summary")
        
    except Exception as e:
        print(f"[ERROR] Failed to create summary: {e}")
    
    print("\n[DONE] Money flow tracking complete!")
