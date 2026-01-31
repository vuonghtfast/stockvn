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
from cleanup_helper import cleanup_removed_tickers

# Load environment variables
load_dotenv()

# ===== Command Line Arguments =====
parser = argparse.ArgumentParser(description='Cào dữ liệu giá chứng khoán từ vnstock')
parser.add_argument('--period', type=str, default='5y', 
                    help='Khoảng thời gian: 1d, 1w, 1m, 3m, 6m, 1y, 2y, 5y (default: 5y)')
parser.add_argument('--interval', type=str, default='1D',
                    help='Interval: 1m, 3m, 5m, 15m, 30m, 1H, 1D (default: 1D)')
parser.add_argument('--mode', type=str, default='historical',
                    choices=['historical', 'realtime', 'update'],
                    help='Mode: historical (full history), realtime (intraday), update (latest only)')
parser.add_argument('--tickers', type=str, default=None,
                    help='Specific tickers (comma-separated), e.g., VNM,HPG,FPT')
args = parser.parse_args()

# Parse period
def parse_period(period_str):
    """Convert period string to start_date"""
    today = datetime.today()
    
    if period_str == '1d':
        return (today - timedelta(days=1)).strftime("%Y-%m-%d")
    elif period_str == '1w':
        return (today - timedelta(days=7)).strftime("%Y-%m-%d")
    elif period_str == '1m':
        return (today - timedelta(days=30)).strftime("%Y-%m-%d")
    elif period_str == '3m':
        return (today - timedelta(days=90)).strftime("%Y-%m-%d")
    elif period_str == '6m':
        return (today - timedelta(days=180)).strftime("%Y-%m-%d")
    elif period_str == '1y':
        return (today - timedelta(days=365)).strftime("%Y-%m-%d")
    elif period_str == '2y':
        return (today - timedelta(days=730)).strftime("%Y-%m-%d")
    elif period_str == '5y':
        return (today - timedelta(days=1825)).strftime("%Y-%m-%d")
    else:
        return (today - timedelta(days=1825)).strftime("%Y-%m-%d")

start_date = parse_period(args.period)
end_date = datetime.today().strftime("%Y-%m-%d")

print(f"[CONFIG]")
print(f"  - Period: {args.period} ({start_date} -> {end_date})")
print(f"  - Interval: {args.interval}")
print(f"  - Mode: {args.mode}")

# ===== 1. Kết nối Google Sheets =====
def get_google_credentials():
    """Load Google credentials from environment or file"""
    try:
        # Try from environment variable first (for GitHub Actions)
        if "GOOGLE_CREDENTIALS" in os.environ:
            creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
            return ServiceAccountCredentials.from_json_keyfile_dict(
                creds_dict,
                ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            )
        # Fallback to credentials.json (for local)
        elif os.path.exists("credentials.json"):
            return ServiceAccountCredentials.from_json_keyfile_name(
                "credentials.json",
                ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            )
        else:
            raise FileNotFoundError("No credentials found")
    except Exception as e:
        print(f"[X] Lỗi tải credentials: {e}")
        sys.exit(1)

creds = get_google_credentials()
client = gspread.authorize(creds)

# Open spreadsheet by ID (from env) or name
spreadsheet_id = os.getenv("SPREADSHEET_ID")
if spreadsheet_id:
    spreadsheet = client.open_by_key(spreadsheet_id)
else:
    spreadsheet = client.open("stockdata")

print(f"[OK] Connected to Google Sheets: {spreadsheet.title}")

# Get tickers from watchlist_flow sheet (centralized ticker management)
try:
    watchlist_sheet = spreadsheet.worksheet("watchlist_flow")
    all_tickers = watchlist_sheet.col_values(1)[1:]  # Skip header (column 'ticker')
    all_tickers = [t.strip().upper() for t in all_tickers if t.strip()]
except:
    # Fallback to tickers sheet if watchlist_flow doesn't exist
    tickers_sheet = spreadsheet.worksheet("tickers")
    all_tickers = tickers_sheet.col_values(1)[1:]

# Filter tickers if specified
if args.tickers:
    tickers = [t.strip().upper() for t in args.tickers.split(',')]
    print(f"[i] Using tickers from command line: {tickers}")
else:
    tickers = all_tickers
    print(f"[i] Using tickers from watchlist_flow: {len(tickers)} tickers")

# Get or create price sheet
try:
    price_sheet = spreadsheet.worksheet("price")
    print(f"[OK] Found sheet 'price'")
except gspread.WorksheetNotFound:
    print("[!] Sheet 'price' not found. Creating...")
    price_sheet = spreadsheet.add_worksheet(title="price", rows="50000", cols="15")
    print("[OK] Created sheet 'price'")

# ===== Cleanup removed tickers =====
cleanup_removed_tickers(spreadsheet, tickers, ['price', 'price_history'])

# ===== Main Logic =====dữ liệu từ vnstock =====
# Set API key as environment variable (vnstock reads from env)
api_key = os.getenv("VNSTOCK_API_KEY")
if api_key:
    # vnstock reads API key from environment variable automatically
    print("[i] Using vnstock with API key (60 req/min)")
else:
    print("[!] Using vnstock without API key (20 req/min). Register at https://vnstocks.com/login")

# Initialize vnstock (it will use API key from environment if available)
vs = Vnstock()
all_data = []

print(f"\n[START] Fetching data...")

for idx, ticker in enumerate(tickers, 1):
    try:
        status_msg = f"[{idx}/{len(tickers)}] {ticker}..."
        print(status_msg, end=" ", flush=True)
        
        # Try multiple sources with fallback (SSI -> VCI -> TCBS)
        df = None
        sources_to_try = ['SSI', 'VCI', 'TCBS']
        
        for source in sources_to_try:
            try:
                df = vs.stock(symbol=ticker, source=source).quote.history(
                    start=start_date,
                    end=end_date,
                    interval=args.interval
                )
                if df is not None and not df.empty:
                    break  # Success, stop trying other sources
            except Exception as source_error:
                if "403" in str(source_error) or "Forbidden" in str(source_error):
                    continue  # Try next source
                # For other errors, still try next source
                continue
        
        if df is not None and not df.empty:
            # Add ticker column
            df['ticker'] = ticker
            
            # Rename columns for consistency
            if 'time' in df.columns:
                df.rename(columns={'time': 'date'}, inplace=True)
            
            all_data.append(df)
            print(f"OK {len(df)} records")
        else:
            print("No data (all sources failed)")
    
    except Exception as e:
        print(f"Error: {str(e)}")

# ===== 3. Ghi vào Google Sheets =====
if all_data:
    print(f"\n[SAVE] Writing {len(all_data)} tickers to Google Sheets...")
    
    # Combine all data
    final_df = pd.concat(all_data, ignore_index=True)
    
    # Sort by ticker and date
    final_df = final_df.sort_values(['ticker', 'date'])
    
    # Reorder columns
    cols = ['ticker', 'date', 'open', 'high', 'low', 'close', 'volume']
    # Add any extra columns
    extra_cols = [c for c in final_df.columns if c not in cols]
    final_df = final_df[cols + extra_cols]
    
    print(f"[i] Total records: {len(final_df)}")
    print(f"[i] From {final_df['date'].min()} to {final_df['date'].max()}")
    
    # Convert to string for Google Sheets
    final_df = final_df.astype(str)
    
    # Write to sheet
    if args.mode == 'update':
        # Append mode - add new data to existing
        print("[MODE] UPDATE - Appending new data")
        existing_data = price_sheet.get_all_records()
        if existing_data:
            existing_df = pd.DataFrame(existing_data)
            # Combine and remove duplicates
            combined_df = pd.concat([existing_df, final_df], ignore_index=True)
            combined_df = combined_df.drop_duplicates(subset=['ticker', 'date'], keep='last')
            combined_df = combined_df.sort_values(['ticker', 'date'])
            final_df = combined_df
    else:
        # Overwrite mode
        print("[MODE] OVERWRITE - Replacing all data")
    
    price_sheet.clear()
    price_sheet.update([final_df.columns.values.tolist()] + final_df.values.tolist())
    
    print(f"[OK] Wrote {len(final_df)} records to sheet 'price'")
    print(f"[DONE] Complete!")
    
    # Summary
    print(f"\n[SUMMARY]")
    print(f"  - Total tickers: {final_df['ticker'].nunique()}")
    print(f"  - Total records: {len(final_df)}")
    print(f"  - Period: {final_df['date'].min()} -> {final_df['date'].max()}")
    
else:
    print(f"[X] No data fetched")
