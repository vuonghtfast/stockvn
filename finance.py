import io
import sys
import argparse

# Fix encoding for Windows console
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import vnstock as vs
from vnstock import Vnstock
import pandas as pd
import gspread
import os
from oauth2client.service_account import ServiceAccountCredentials
import numpy as np
import time
from cleanup_helper import cleanup_removed_tickers 

# ===== Command Line Arguments =====
parser = argparse.ArgumentParser(description='Financial Report Scraper')
parser.add_argument('--tickers', type=str, default='', help='Comma-separated tickers (e.g., VNM,FPT,VCB). Empty = all from sheet')
parser.add_argument('--period', type=str, default='quarter', choices=['quarter', 'annual'], help='Report period: quarter or annual')
parser.add_argument('--years', type=int, default=3, help='Number of years to fetch (1-5, default: 3)')
args = parser.parse_args()

print(f"[CONFIG] Finance Scraper - Period: {args.period}, Years: {args.years}, Tickers filter: {args.tickers or 'All'}")

# Initialize vnstock with API key if available
api_key = os.getenv("VNSTOCK_API_KEY")
if api_key:
    print("[i] Using vnstock with API key (60 req/min)")
else:
    print("[!] Using vnstock without API key (20 req/min). Register at https://vnstocks.com/login")

# 1. Auth Google Sheets
from config import get_google_credentials

try:
    creds = get_google_credentials()
    client = gspread.authorize(creds)
    spreadsheet = client.open("stockdata")
except Exception as e:
    print(f"[X] Lỗi kết nối Google Sheets: {e}")
    sys.exit(1)

# 2. Đọc danh sách mã cổ phiếu
# Ưu tiên: 1. --tickers (nếu có) + watchlist_flow
try:
    # Get tickers from watchlist_flow (default source)
    watchlist_tickers = []
    try:
        wl_ws = spreadsheet.worksheet("watchlist_flow")
        wl_data = wl_ws.get_all_records()
        if wl_data:
            wl_df = pd.DataFrame(wl_data)
            if 'ticker' in wl_df.columns:
                watchlist_tickers = wl_df['ticker'].dropna().unique().tolist()
        print(f"[i] Từ watchlist_flow: {len(watchlist_tickers)} mã")
    except Exception as e:
        print(f"[!] Không đọc được watchlist_flow: {e}")
    
    # Add custom tickers from command line
    custom_tickers = []
    if args.tickers:
        custom_tickers = [t.strip().upper() for t in args.tickers.split(',') if t.strip()]
        print(f"[i] Từ --tickers: {len(custom_tickers)} mã ({', '.join(custom_tickers)})")
    
    # Combine: watchlist + custom (unique)
    all_tickers = list(set(watchlist_tickers + custom_tickers))
    tickers = all_tickers
    
    if not tickers:
        print("[!] Không có mã cổ phiếu nào. Thêm mã vào watchlist_flow hoặc dùng --tickers VNM,FPT")
        sys.exit(0)
    
    print(f"[OK] Tổng cộng: {len(tickers)} mã sẽ được cào BCTC")
    
except Exception as e:
    print(f"[X] Lỗi đọc danh sách mã: {e}")
    sys.exit(1)

# 3. Hàm lấy báo cáo tài chính (CẬP NHẬT API VNSTOCK MỚI)
def fetch_financials(symbol, period="quarter"):
    """Lấy báo cáo tài chính từ vnstock API mới"""
    data = {}
    try:
        # API mới: Vnstock().stock(symbol, source).finance
        stock = Vnstock().stock(symbol=symbol, source="VCI")
        finance = stock.finance
        
        # Lấy từng loại báo cáo
        try:
            data["income"] = finance.income_statement(period=period)
        except Exception as e:
            print(f"  [!] Income statement {symbol}: {e}")
            
        try:
            data["balance"] = finance.balance_sheet(period=period)
        except Exception as e:
            print(f"  [!] Balance sheet {symbol}: {e}")
        
        try:
            data["cashflow"] = finance.cash_flow(period=period)
        except Exception as e:
            print(f"  [!] Cash flow {symbol}: {e}")
            
        return data

    except Exception as e:
        print(f"[X] Lỗi khi lấy báo cáo {symbol} | {period}: {e}")
        return {}

# 4. Ghi dữ liệu vào Google Sheets (CẬP NHẬT: MERGE DỮ LIỆU)
def get_existing_data(sheet_name):
    """Đọc dữ liệu cũ từ Google Sheet"""
    try:
        ws = spreadsheet.worksheet(sheet_name)
        data = ws.get_all_records()
        if data:
            return pd.DataFrame(data)
    except gspread.WorksheetNotFound:
        return pd.DataFrame()
    except Exception as e:
        print(f"[!] Lỗi đọc sheet {sheet_name}: {e}")
        return pd.DataFrame()
    return pd.DataFrame()

def write_to_sheet(sheet_name, new_df):
    """Ghi DataFrame vào Google Sheet, merge với dữ liệu cũ."""
    try:
        try:
            ws = spreadsheet.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            ws = spreadsheet.add_worksheet(title=sheet_name, rows="2000", cols="20")
            
        # 1. Đọc dữ liệu cũ
        old_df = get_existing_data(sheet_name)
        
        # 2. Merge dữ liệu
        if not old_df.empty:
            # Chuẩn hóa cột để merge
            # Chuyển đổi tên cột cũ về dạng chuẩn (lower + underscore) nếu cần
            old_df.columns = old_df.columns.str.lower().str.replace(' ', '_')
            # Xóa cột trùng lặp (giữ cột đầu tiên)
            old_df = old_df.loc[:, ~old_df.columns.duplicated()]
            
            # Đảm bảo new_df cũng chuẩn
            if not new_df.empty:
                new_df.columns = new_df.columns.str.lower().str.replace(' ', '_')
                # Xóa cột trùng lặp (giữ cột đầu tiên)
                new_df = new_df.loc[:, ~new_df.columns.duplicated()]
                
                # Cột để xác định trùng lặp (Composite Key)
                # Income/Balance/Cashflow: Ticker + Year + Quarter (nếu có)
                subset_cols = ['ticker', 'year', 'quarter'] if 'quarter' in new_df.columns else ['ticker', 'year']
                
                # Kiểm tra xem các cột key có tồn tại không
                valid_keys = [c for c in subset_cols if c in old_df.columns and c in new_df.columns]
                
                if valid_keys:
                    # Gộp và xóa trùng lặp, giữ lại dữ liệu MỚI NHẤT (từ new_df)
                    # concat row mới lên trên row cũ, rồi drop_duplicates keep='first'
                    combined_df = pd.concat([new_df, old_df], ignore_index=True)
                    
                    # Xóa cột trùng lặp sau khi concat
                    combined_df = combined_df.loc[:, ~combined_df.columns.duplicated()]
                    
                    # Chuyển đổi key sang string để so sánh chính xác
                    for col in valid_keys:
                        combined_df[col] = combined_df[col].astype(str)
                        
                    combined_df = combined_df.drop_duplicates(subset=valid_keys, keep='first')
                else:
                    # Nếu không tìm thấy key chung, cứ append (có rủi ro trùng)
                    print(f"[!] Không tìm thấy key chung ({subset_cols}) để merge {sheet_name}. Append dữ liệu.")
                    combined_df = pd.concat([old_df, new_df], ignore_index=True)
                    combined_df = combined_df.loc[:, ~combined_df.columns.duplicated()]
            else:
                combined_df = old_df
        else:
            combined_df = new_df
            if not combined_df.empty:
                combined_df = combined_df.loc[:, ~combined_df.columns.duplicated()]

        if combined_df.empty:
            print(f"[!] Không có dữ liệu để ghi cho {sheet_name}")
            return

        # 3. Ghi lại vào Sheet
        # Sắp xếp lại nếu có cột ticker và year
        sort_cols = []
        if 'ticker' in combined_df.columns: sort_cols.append('ticker')
        if 'year' in combined_df.columns: sort_cols.append('year')
        if 'quarter' in combined_df.columns: sort_cols.append('quarter')
        
        if sort_cols:
            combined_df = combined_df.sort_values(sort_cols)

        # Thay thế NaN bằng chuỗi rỗng để tránh lỗi JSON
        combined_df = combined_df.fillna('')
        
        # Xóa sheet cũ và ghi mới (An toàn hơn update range)
        ws.clear()
        ws.update([combined_df.columns.values.tolist()] + combined_df.astype(str).values.tolist())
        print(f"[OK] Đã merge và ghi {sheet_name}: {len(combined_df)} dòng (Thêm mới: {len(combined_df) - len(old_df) if not old_df.empty else len(combined_df)})")
        
    except Exception as e:
        print(f"[X] Lỗi khi ghi sheet {sheet_name}: {e}")
        import traceback
        traceback.print_exc()

# ===== Cleanup removed tickers =====
# cleanup_removed_tickers(spreadsheet, tickers, ['income', 'balance', 'cashflow']) 
# Tạm thời comment cleanup để tránh xóa nhầm dữ liệu lịch sử của các mã cũ

# 5. Tạo summary (YOY hoặc QOQ growth)
def create_summary(period="year"):
    """Tạo báo cáo tóm tắt tăng trưởng doanh thu/lợi nhuận từ dữ liệu đã lưu."""
    print(f"--- Đang tạo summary ({period}) từ dữ liệu đã lưu ---")
    
    # Đọc dữ liệu từ sheet income (đã được cập nhật)
    income_df = get_existing_data("income")
    
    if income_df.empty:
        print("[!] Không có dữ liệu income để tạo summary.")
        return

    # Chuẩn hóa cột
    income_df.columns = income_df.columns.str.lower().str.replace(' ', '_')
    
    # Map tên cột VCI API -> tên chuẩn
    income_df = income_df.rename(columns={
        'yearreport': 'year',
        'lengthreport': 'quarter',
        'revenue_(bn._vnd)': 'revenue',
        'attributable_to_parent_company': 'net_income',
        'net_profit_for_the_year': 'net_income',
        'share_holder_income': 'net_income', 
        'post_tax_profit': 'net_income', 
    }, errors='ignore')
    
    # Xóa cột trùng sau khi rename
    income_df = income_df.loc[:, ~income_df.columns.duplicated()]
    
    required_cols = ['ticker', 'revenue', 'net_income']
    if period == 'year':
        if 'year' not in income_df.columns:
            print(f"[!] Dữ liệu income thiếu cột 'year'. Các cột hiện có: {list(income_df.columns)}")
            return
        sort_cols = ['ticker', 'year']
    else: # quarter
        if 'year' not in income_df.columns or 'quarter' not in income_df.columns:
            print(f"[!] Dữ liệu income thiếu cột 'year' hoặc 'quarter'. Các cột hiện có: {list(income_df.columns)}")
            return
        sort_cols = ['ticker', 'year', 'quarter']

    # Convert numeric
    for col in ['revenue', 'net_income', 'year', 'quarter']:
        if col in income_df.columns:
             income_df[col] = pd.to_numeric(income_df[col], errors='coerce')

    # Sort
    income_df = income_df.sort_values(sort_cols)
    
    all_summaries = []
    
    # Group by ticker and calculate growth
    for ticker, group in income_df.groupby('ticker'):
        if len(group) < 2:
            continue
            
        # Calculate changes
        group = group.copy()
        
        # Calculate growth explicitly
        group['Revenue_Growth'] = group['revenue'].pct_change()
        group['NetIncome_Growth'] = group['net_income'].pct_change()
        
        # Rename for output match
        if period == 'year':
            group['NetIncome_YOY'] = group['NetIncome_Growth']
            group['Revenue_YOY'] = group['Revenue_Growth']
        else:
            group['NetIncome_QOQ'] = group['NetIncome_Growth']
            group['Revenue_QOQ'] = group['Revenue_Growth']
            
        # Get latest row
        latest = group.iloc[-1:].copy()
        all_summaries.append(latest)
        
    if all_summaries:
        final_df = pd.concat(all_summaries)
        
        # Clean up columns for export
        export_cols = ['ticker', 'year']
        if period == 'quarter':
            export_cols.append('quarter')
            
        if period == 'year':
            export_cols.extend(['revenue', 'net_income', 'Revenue_YOY', 'NetIncome_YOY'])
        else:
            export_cols.extend(['revenue', 'net_income', 'Revenue_QOQ', 'NetIncome_QOQ'])
            
        # Keep only existing columns
        export_cols = [c for c in export_cols if c in final_df.columns]
        final_df = final_df[export_cols]

        sheet_name = f"summary_{'y' if period=='year' else 'q'}"
        write_to_sheet(sheet_name, final_df)

        # Summary Latest (Overwrite)
        sheet_latest = f"summary_latest_{'y' if period=='year' else 'q'}"
        try:
             ws = spreadsheet.worksheet(sheet_latest)
             ws.clear()
             ws.update([final_df.columns.values.tolist()] + final_df.astype(str).values.tolist())
             print(f"[OK] Đã cập nhật {sheet_latest}")
        except gspread.WorksheetNotFound:
             write_to_sheet(sheet_latest, final_df)
        except Exception as e:
             print(f"[!] Lỗi cập nhật {sheet_latest}: {e}")

    else:
        print(f"[!] Không tính được growth cho {period}")

# 6. Chạy chính (Logic ghi sheet gộp dữ liệu)
if __name__ == "__main__":
    print(f"[GO] Bắt đầu lấy dữ liệu cho {len(tickers)} mã: {', '.join(tickers)}")
    
    all_reports = {
        "income": [],
        "balance": [],
        "cashflow": [], 
    }

    # Fetch data
    for t in tickers:
        print(f"--- Xử lý {t} ---")
        time.sleep(2) # Delay để tránh rate limit
        fdata = fetch_financials(t, period=args.period)  # Use CLI arg 
        
        for rtype, df in fdata.items():
            if df is not None and not df.empty and rtype in all_reports:
                df["Ticker"] = t 
                all_reports[rtype].append(df) 

    # Merge và Ghi
    for rtype, df_list in all_reports.items():
        if df_list:
            final_df = pd.concat(df_list, ignore_index=True)
            final_df.columns = final_df.columns.str.lower().str.replace(' ', '_')
            write_to_sheet(rtype, final_df) 
        else:
            print(f"[!] Không có dữ liệu mới để ghi cho báo cáo: {rtype}")
            
    # Tạo summary toàn bộ
    print("\n*** BẮT ĐẦU TẠO SUMMARY ***")
    create_summary("year")
    create_summary("quarter")
    
    print("\n[OK] HOÀN TẤT QUY TRÌNH.")
