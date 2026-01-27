# -*- coding: utf-8 -*-
"""
Money Flow Tracker v2 - Theo doi dong tien mua-ban real-time
Su dung vnstock intraday API voi match_type (Buy/Sell)
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
from sectors import get_sector, get_all_sectors
from vietnam_holidays import is_trading_day

# Load environment variables
load_dotenv()

# ===== Command Line Arguments =====
parser = argparse.ArgumentParser(description='Theo doi dong tien mua-ban real-time')
parser.add_argument('--interval', type=int, default=20, 
                    help='Interval in minutes (default: 20)')
parser.add_argument('--skip-holiday-check', action='store_true',
                    help='Skip holiday check (for testing)')
args = parser.parse_args()

print(f"[CONFIG] Money Flow Tracker v2 - Interval: {args.interval} min")

# ===== Check if today is a trading day =====
if not args.skip_holiday_check:
    if not is_trading_day():
        print("[i] Today is not a trading day (weekend or holiday). Exiting.")
        sys.exit(0)
    print("[OK] Trading day confirmed")

# ===== 1. Connect to Google Sheets =====
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

# ===== 2. Get tickers =====
try:
    tickers_sheet = spreadsheet.worksheet("tickers")
    tickers = tickers_sheet.col_values(1)[1:]  # Skip header
    print(f"[i] Tracking {len(tickers)} tickers")
except Exception as e:
    print(f"[X] Failed to read tickers: {e}")
    sys.exit(1)

# ===== 3. Initialize vnstock =====
vs = Vnstock()

# ===== 4. Calculate Money Flow using Intraday Buy/Sell =====
def calculate_money_flow_intraday(ticker):
    """Tinh dong tien tu intraday data voi Buy/Sell"""
    try:
        # Get intraday data
        stock = vs.stock(symbol=ticker, source='VCI')
        df = stock.quote.intraday(show_log=False)
        
        if df.empty:
            return None
        
        # Calculate buy/sell flow
        buy_df = df[df['match_type'] == 'Buy']
        sell_df = df[df['match_type'] == 'Sell']
        
        buy_flow = (buy_df['price'] * buy_df['volume']).sum()
        sell_flow = (sell_df['price'] * sell_df['volume']).sum()
        net_flow = buy_flow - sell_flow
        
        # Get latest price
        latest_price = df['price'].iloc[-1] if len(df) > 0 else 0
        total_volume = df['volume'].sum()
        
        # Get sector
        sector = get_sector(ticker)
        
        return {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'ticker': ticker,
            'sector': sector,
            'price': round(latest_price, 2),
            'volume': int(total_volume),
            'buy_flow': round(buy_flow / 1e9, 2),  # Ty VND
            'sell_flow': round(sell_flow / 1e9, 2),
            'net_flow': round(net_flow / 1e9, 2),
        }
    except Exception as e:
        print(f"[X] {ticker}: {e}")
        return None

# ===== 5. Main Logic =====
print(f"\n[i] Fetching intraday data for {len(tickers)} tickers...")

all_data = []
for i, ticker in enumerate(tickers):
    result = calculate_money_flow_intraday(ticker)
    if result:
        all_data.append(result)
    
    # Progress
    if (i + 1) % 10 == 0:
        print(f"[i] Progress: {i + 1}/{len(tickers)}")

if not all_data:
    print("[X] No data collected")
    sys.exit(1)

df = pd.DataFrame(all_data)
print(f"[OK] Collected data for {len(df)} tickers")

# ===== 6. Aggregate by Sector =====
sector_summary = df.groupby('sector').agg({
    'buy_flow': 'sum',
    'sell_flow': 'sum',
    'net_flow': 'sum',
    'ticker': 'count'
}).reset_index()
sector_summary.columns = ['sector', 'buy_flow', 'sell_flow', 'net_flow', 'stock_count']
sector_summary = sector_summary.sort_values('net_flow', ascending=False)

# ===== 7. Top 3 Sectors with POSITIVE flow (with stocks) =====
positive_sectors = sector_summary[sector_summary['net_flow'] > 0].head(3)
print(f"\n[OK] Top 3 sectors with positive flow:")
for _, row in positive_sectors.iterrows():
    try:
        print(f"  - {row['sector']}: +{row['net_flow']:.2f}B VND")
    except UnicodeEncodeError:
        print(f"  - [Sector]: +{row['net_flow']:.2f}B VND")

# Get top 3 stocks from each positive sector
top_stocks = []
for sector in positive_sectors['sector']:
    sector_stocks = df[df['sector'] == sector].nlargest(3, 'net_flow')
    top_stocks.append(sector_stocks)

if top_stocks:
    top_stocks_df = pd.concat(top_stocks)
    print(f"[OK] Top {len(top_stocks_df)} stocks from positive sectors")
else:
    top_stocks_df = pd.DataFrame()

# ===== 8. Top 3 Sectors with NEGATIVE flow (sectors only) =====
negative_sectors = sector_summary[sector_summary['net_flow'] < 0].tail(3).iloc[::-1]  # Worst first
print(f"\n[OK] Top 3 sectors with negative flow:")
for _, row in negative_sectors.iterrows():
    try:
        print(f"  - {row['sector']}: {row['net_flow']:.2f}B VND")
    except UnicodeEncodeError:
        print(f"  - [Sector]: {row['net_flow']:.2f}B VND")

# ===== 9. Save to Google Sheets =====
try:
    # Sheet: money_flow_top
    try:
        mf_ws = spreadsheet.worksheet("money_flow_top")
    except gspread.WorksheetNotFound:
        mf_ws = spreadsheet.add_worksheet(title="money_flow_top", rows="100", cols="15")
    
    # Prepare data
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Save top stocks
    if not top_stocks_df.empty:
        stocks_data = top_stocks_df[['timestamp', 'ticker', 'sector', 'price', 'volume', 'buy_flow', 'sell_flow', 'net_flow']].copy()
        stocks_data['type'] = 'stock'
    else:
        stocks_data = pd.DataFrame()
    
    # Save positive sectors
    pos_sectors_data = positive_sectors[['sector', 'buy_flow', 'sell_flow', 'net_flow', 'stock_count']].copy()
    pos_sectors_data['timestamp'] = timestamp
    pos_sectors_data['type'] = 'sector_positive'
    pos_sectors_data['ticker'] = ''
    pos_sectors_data['price'] = 0
    pos_sectors_data['volume'] = 0
    
    # Save negative sectors
    neg_sectors_data = negative_sectors[['sector', 'buy_flow', 'sell_flow', 'net_flow', 'stock_count']].copy()
    neg_sectors_data['timestamp'] = timestamp
    neg_sectors_data['type'] = 'sector_negative'
    neg_sectors_data['ticker'] = ''
    neg_sectors_data['price'] = 0
    neg_sectors_data['volume'] = 0
    
    # Combine all
    all_output = pd.concat([stocks_data, pos_sectors_data, neg_sectors_data], ignore_index=True)
    
    # Reorder columns
    cols = ['timestamp', 'type', 'ticker', 'sector', 'price', 'volume', 'buy_flow', 'sell_flow', 'net_flow']
    all_output = all_output[[c for c in cols if c in all_output.columns]]
    
    # Clear and write
    mf_ws.clear()
    mf_ws.update([all_output.columns.values.tolist()] + all_output.astype(str).values.tolist())
    
    print(f"\n[OK] Saved to money_flow_top sheet ({len(all_output)} records)")

except Exception as e:
    print(f"[X] Failed to save: {e}")
    sys.exit(1)

print("\n[DONE] Money Flow Tracker v2 completed!")
