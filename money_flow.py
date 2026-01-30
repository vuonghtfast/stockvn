# -*- coding: utf-8 -*-
"""
Money Flow Tracker v2.5 - Market-Wide Money Flow Real-time
Method: 2-Layer Funnel
1. Scan All Market -> Filter Top 60 Liquidity (Volume * Price)
2. Deep Scan Top 60 -> Calculate Buy/Sell Flow
"""

import pandas as pd
from vnstock import Vnstock
import gspread
from datetime import datetime, timezone, timedelta
import os
import sys
import argparse
import time
import logging
import io
import concurrent.futures
import threading

# Fix encoding for Windows console
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Suppress noisy logs from vnstock/urllib3
logging.getLogger('vnstock').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR)

from dotenv import load_dotenv
from config import get_google_credentials
from sectors import get_sector
from vietnam_holidays import is_trading_day

# Load environment variables
load_dotenv()

# ===== Command Line Arguments =====
parser = argparse.ArgumentParser(description='Market-Wide Money Flow Tracker')
parser.add_argument('--interval', type=int, default=20, help='Interval in minutes (default: 20)')
parser.add_argument('--top', type=int, default=60, help='Number of top liquid stocks to scan (default: 60)')
parser.add_argument('--skip-holiday-check', action='store_true', help='Skip holiday check')
args = parser.parse_args()

print(f"[CONFIG] Money Flow (Market-Wide) - Top: {args.top} - Interval: {args.interval}m")

# ===== Check if today is a trading day =====
if not args.skip_holiday_check:
    if not is_trading_day():
        print("[i] Today is not a trading day. Exiting.")
        sys.exit(0)
    print("[OK] Trading day confirmed")

# ===== 1. Connect to Google Sheets =====
try:
    creds = get_google_credentials()
    client = gspread.authorize(creds)
    spreadsheet_id = os.getenv("SPREADSHEET_ID")
    spreadsheet = client.open_by_key(spreadsheet_id) if spreadsheet_id else client.open("stockdata")
    print(f"[OK] Connected to Google Sheets: {spreadsheet.title}")
except Exception as e:
    print(f"[X] Failed to connect to Google Sheets: {e}")
    sys.exit(1)

# ===== 2. Initialize vnstock =====
vs = Vnstock()

def get_market_leaders(top_n=60):
    """
    Layer 1: Get Top N stocks by Liquidity (Turnover) from whole market
    """
    print("\n[LAYER 1] Scanning market for Top Liquidity...")
    try:
        # Step A: Get all symbols
        exchanges = ['HOSE', 'HNX', 'UPCOM']
        all_symbols = []
        
        for ex in exchanges:
            try:
                # Listing source TCBS is stable
                df = vs.stock(symbol='VNM', source='TCBS').listing.all_symbols(exchange=ex)
                if not df.empty and 'ticker' in df.columns:
                    all_symbols.extend(df['ticker'].tolist())
            except Exception as e:
                print(f"  [!] Failed to get {ex} symbols: {e}")
        
        # Remove duplicates
        all_symbols = list(set(all_symbols))
        print(f"  > Found {len(all_symbols)} total symbols")
        
        # Step B: Batch fetch price/volume to find leaders
        # We need efficient batching. SSI/VCI supports batching.
        # Let's chunk into 50s
        chunk_size = 50
        candidates = []
        
        print(f"  > Batch fetching quotes (Chunk size: {chunk_size}, Threads: 5)...")
        
        def fetch_chunk(chunk_symbols):
            try:
                chunk_str = ",".join(chunk_symbols)
                # Using VCI source for price board snapshot
                prices = vs.stock(symbol=chunk_str, source='VCI').quote.now()
                
                if not prices.empty:
                    # Calculate approximate turnover (Volume * Price)
                    p_col = 'price' if 'price' in prices.columns else 'match_price'
                    v_col = 'volume' if 'volume' in prices.columns else 'accumulatedVolume'
                    
                    if p_col in prices.columns and v_col in prices.columns:
                        # Ensure numeric
                        prices[p_col] = pd.to_numeric(prices[p_col], errors='coerce').fillna(0)
                        prices[v_col] = pd.to_numeric(prices[v_col], errors='coerce').fillna(0)
                        
                        # Turnover
                        prices['turnover'] = prices[p_col] * prices[v_col]
                        
                        # Keep relevant info
                        return prices[['ticker', p_col, v_col, 'turnover']]
            except Exception:
                pass
            return pd.DataFrame()

        # Use ThreadPoolExecutor for parallel fetching
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i in range(0, len(all_symbols), chunk_size):
                chunk = all_symbols[i:i+chunk_size]
                futures.append(executor.submit(fetch_chunk, chunk))
            
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                if not res.empty:
                    candidates.append(res)
                
        if not candidates:
            print("[X] Failed to fetch market data. Using fallback list.")
            return []

        # Combine
        full_market = pd.concat(candidates, ignore_index=True)
        
        # Sort by Turnover (Liquidity)
        full_market = full_market.sort_values('turnover', ascending=False)
        
        # Select Top N
        top_tickers = full_market.head(top_n)['ticker'].tolist()
        print(f"  > Selected Top {len(top_tickers)} by liquidity")
        print(f"  > Leaders: {', '.join(top_tickers[:5])}...")
        
        return top_tickers
        
    except Exception as e:
        print(f"[X] Layer 1 failed: {e}")
        return []

# ===== 3. Calculate Money Flow (Layer 2) =====
def calculate_money_flow_intraday(ticker):
    """Calculates Buy/Sell/Net flow from intraday match data"""
    try:
        # Get intraday data (Source: VCI is best for match_type)
        stock = vs.stock(symbol=ticker, source='VCI')
        df = stock.quote.intraday(show_log=False)
        
        if df.empty:
            return None
        
        # Standardize columns just in case
        # VCI: price, volume, match_type, time...
        
        # Calculate buy/sell flow
        buy_df = df[df['match_type'] == 'Buy']
        sell_df = df[df['match_type'] == 'Sell']
        
        buy_flow = (buy_df['price'] * buy_df['volume']).sum()
        sell_flow = (sell_df['price'] * sell_df['volume']).sum()
        net_flow = buy_flow - sell_flow
        
        # Get latest price stats
        latest_price = df['price'].iloc[-1] if len(df) > 0 else 0
        total_volume = df['volume'].sum()
        
        sector = get_sector(ticker)
        
        return {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'ticker': ticker,
            'sector': sector,
            'price': round(latest_price, 2),
            'volume': int(total_volume),
            'buy_flow': round(buy_flow / 1e9, 2),  # Billions VND
            'sell_flow': round(sell_flow / 1e9, 2),
            'net_flow': round(net_flow / 1e9, 2),
        }
    except Exception as e:
        print(f"  [!] {ticker} error: {e}")
        return None

# ===== Main Execution =====
def main():
    # 1. Get Top Tickers
    target_tickers = get_market_leaders(args.top)
    
    if not target_tickers:
        print("[!] No tickers found from scan. Falling back to Watchlist.")
        try:
            tickers_sheet = spreadsheet.worksheet("tickers")
            target_tickers = tickers_sheet.col_values(1)[1:]
        except:
            print("[X] Fallback failed.")
            sys.exit(1)
            
    # 2. Process Layer 2
    print(f"\n[LAYER 2] Analyzing Money Flow for {len(target_tickers)} tickers (Threads: 10)...")
    
    all_data = []
    completed = 0
    lock = threading.Lock()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_ticker = {executor.submit(calculate_money_flow_intraday, ticker): ticker for ticker in target_tickers}
        
        for future in concurrent.futures.as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                res = future.result()
                if res:
                    all_data.append(res)
            except Exception as exc:
                print(f"  [!] {ticker} generated an exception: {exc}")
            
            with lock:
                completed += 1
                if completed % 5 == 0 or completed == len(target_tickers):
                    print(f"  > Progress: {completed}/{len(target_tickers)}", end='\r')
    
    print(f"\n  > Completed analysis. Success: {len(all_data)}/{len(target_tickers)}")
            
    if not all_data:
        print("[X] No data collected.")
        sys.exit(1)
        
    df = pd.DataFrame(all_data)
    
    # 3. Aggregation Logic (Same as before)
    # Group by Sector
    sector_summary = df.groupby('sector').agg({
        'buy_flow': 'sum',
        'sell_flow': 'sum',
        'net_flow': 'sum',
        'ticker': 'count'
    }).reset_index()
    sector_summary.columns = ['sector', 'buy_flow', 'sell_flow', 'net_flow', 'stock_count']
    sector_summary = sector_summary.sort_values('net_flow', ascending=False)
    
    # Identify Leaders
    positive_sectors = sector_summary[sector_summary['net_flow'] > 0].head(3)
    negative_sectors = sector_summary[sector_summary['net_flow'] < 0].tail(3).iloc[::-1]
    
    # Top Stocks from Positive Sectors
    top_stocks_list = []
    for sector in positive_sectors['sector']:
        # Get Top 3 stocks in this sector from our scanned list
        s_stocks = df[df['sector'] == sector].nlargest(5, 'net_flow')
        top_stocks_list.append(s_stocks)
        
    top_stocks_df = pd.concat(top_stocks_list) if top_stocks_list else pd.DataFrame()
    
    # 4. Save to Sheets
    try:
        try:
            mf_ws = spreadsheet.worksheet("money_flow_top")
        except gspread.WorksheetNotFound:
            mf_ws = spreadsheet.add_worksheet(title="money_flow_top", rows="100", cols="15")
        
        # Use Vietnam time (UTC+7)
        vn_tz = timezone(timedelta(hours=7))
        timestamp = datetime.now(vn_tz).strftime('%Y-%m-%d %H:%M:%S')
        
        # Prepare Rows
        # Stocks
        if not top_stocks_df.empty:
            stocks_out = top_stocks_df[['timestamp', 'ticker', 'sector', 'price', 'volume', 'buy_flow', 'sell_flow', 'net_flow']].copy()
            stocks_out['type'] = 'stock'
        else:
            stocks_out = pd.DataFrame()
            
        # Pos Sectors
        pos_out = positive_sectors[['sector', 'buy_flow', 'sell_flow', 'net_flow', 'stock_count']].copy()
        pos_out['timestamp'] = timestamp
        pos_out['type'] = 'sector_positive'
        pos_out['ticker'] = ''
        pos_out['price'] = 0
        pos_out['volume'] = 0
        
        # Neg Sectors
        neg_out = negative_sectors[['sector', 'buy_flow', 'sell_flow', 'net_flow', 'stock_count']].copy()
        neg_out['timestamp'] = timestamp
        neg_out['type'] = 'sector_negative'
        neg_out['ticker'] = ''
        neg_out['price'] = 0
        neg_out['volume'] = 0
        
        # Combine
        final_df = pd.concat([stocks_out, pos_out, neg_out], ignore_index=True)
        col_order = ['timestamp', 'type', 'ticker', 'sector', 'price', 'volume', 'buy_flow', 'sell_flow', 'net_flow']
        final_df = final_df[[c for c in col_order if c in final_df.columns]]
        
        # Write
        mf_ws.clear()
        mf_ws.update([final_df.columns.values.tolist()] + final_df.astype(str).values.tolist())
        print(f"\n[SUCCESS] Saved {len(final_df)} records to money_flow_top.")
        
        # ===== Auto-save to "Danh mục mua mạnh" watchlist =====
        if not top_stocks_df.empty:
            try:
                try:
                    wl_ws = spreadsheet.worksheet("watchlist_strong_buy")
                except gspread.WorksheetNotFound:
                    wl_ws = spreadsheet.add_worksheet(title="watchlist_strong_buy", rows="50", cols="10")
                
                # Prepare watchlist data
                wl_df = top_stocks_df[['ticker', 'sector', 'price', 'volume', 'net_flow']].copy()
                wl_df['updated'] = timestamp
                wl_df['list_name'] = 'Danh mục mua mạnh'
                
                # Clear and write
                wl_ws.clear()
                wl_ws.update([wl_df.columns.values.tolist()] + wl_df.astype(str).values.tolist())
                print(f"[SUCCESS] Auto-saved {len(wl_df)} stocks to 'Danh mục mua mạnh' watchlist.")
            except Exception as wl_e:
                print(f"[!] Failed to save watchlist: {wl_e}")
        
    except Exception as e:
        print(f"[X] Save failed: {e}")

if __name__ == "__main__":
    main()
