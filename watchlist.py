# -*- coding: utf-8 -*-
"""
Watchlist Management - Quản lý danh sách theo dõi cổ phiếu
Hỗ trợ 2 loại watchlist: dòng tiền (flow) và cơ bản (fundamental)
"""

import pandas as pd
import gspread
from datetime import datetime
import os
import sys
from config import get_google_credentials
from sectors import get_sector

def get_spreadsheet():
    """Kết nối Google Sheets"""
    try:
        creds = get_google_credentials()
        client = gspread.authorize(creds)
        
        spreadsheet_id = os.getenv("SPREADSHEET_ID")
        if spreadsheet_id:
            return client.open_by_key(spreadsheet_id)
        
        # Try multiple names
        names_to_try = ["stockdata", "Stock_Data_Storage"]
        for name in names_to_try:
            try:
                return client.open(name)
            except:
                continue
        
        print(f"[X] Could not find spreadsheet with names: {names_to_try}")
        return None
    except Exception as e:
        print(f"[X] Failed to connect to Google Sheets: {e}")
        return None

def add_to_watchlist(ticker, list_type='flow', note=''):
    """
    Thêm mã vào danh sách theo dõi
    
    Args:
        ticker: Mã cổ phiếu
        list_type: 'flow' hoặc 'fundamental'
        note: Ghi chú (optional)
    
    Returns:
        True nếu thành công, False nếu thất bại
    """
    try:
        spreadsheet = get_spreadsheet()
        if not spreadsheet:
            return False
        
        sheet_name = f"watchlist_{list_type}"
        
        # Tạo sheet nếu chưa có
        try:
            ws = spreadsheet.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            ws = spreadsheet.add_worksheet(title=sheet_name, rows="1000", cols="10")
            # Thêm header
            if list_type == 'flow':
                headers = ['ticker', 'sector', 'added_date', 'avg_flow_7d', 'note']
            else:  # fundamental
                headers = ['ticker', 'sector', 'added_date', 'roe', 'roa', 'eps', 'dividend_yield', 'note']
            ws.update([headers])
        
        # Kiểm tra xem mã đã tồn tại chưa
        existing_data = ws.get_all_records()
        existing_df = pd.DataFrame(existing_data)
        
        if not existing_df.empty and ticker in existing_df['ticker'].values:
            print(f"[i] {ticker} already in {list_type} watchlist")
            return True
        
        # Lấy thông tin ngành
        sector = get_sector(ticker)
        
        # Thêm mã mới
        new_row = [ticker, sector, datetime.now().strftime('%Y-%m-%d')]
        
        if list_type == 'flow':
            new_row.extend(['', note])  # avg_flow_7d sẽ được cập nhật sau
        else:  # fundamental
            new_row.extend(['', '', '', '', note])  # ROE, ROA, EPS, dividend_yield sẽ được cập nhật sau
        
        ws.append_row(new_row)
        print(f"[OK] Added {ticker} to {list_type} watchlist")
        return True
        
    except Exception as e:
        print(f"[X] Failed to add {ticker} to watchlist: {e}")
        return False

def remove_from_watchlist(ticker, list_type='flow'):
    """
    Xóa mã khỏi danh sách theo dõi
    
    Args:
        ticker: Mã cổ phiếu
        list_type: 'flow' hoặc 'fundamental'
    
    Returns:
        True nếu thành công, False nếu thất bại
    """
    try:
        spreadsheet = get_spreadsheet()
        if not spreadsheet:
            return False
        
        sheet_name = f"watchlist_{list_type}"
        
        try:
            ws = spreadsheet.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            print(f"[i] {sheet_name} not found")
            return False
        
        # Tìm và xóa row
        existing_data = ws.get_all_records()
        existing_df = pd.DataFrame(existing_data)
        
        if existing_df.empty or ticker not in existing_df['ticker'].values:
            print(f"[i] {ticker} not in {list_type} watchlist")
            return False
        
        # Xóa ticker
        filtered_df = existing_df[existing_df['ticker'] != ticker]
        
        # Ghi lại
        ws.clear()
        ws.update([filtered_df.columns.values.tolist()] + filtered_df.astype(str).values.tolist())
        
        print(f"[OK] Removed {ticker} from {list_type} watchlist")
        return True
        
    except Exception as e:
        print(f"[X] Failed to remove {ticker} from watchlist: {e}")
        return False

def get_watchlist(list_type='flow'):
    """
    Lấy danh sách theo dõi
    
    Args:
        list_type: 'flow' hoặc 'fundamental'
    
    Returns:
        DataFrame chứa danh sách, hoặc DataFrame rỗng nếu thất bại
    """
    try:
        spreadsheet = get_spreadsheet()
        if not spreadsheet:
            return pd.DataFrame()
        
        sheet_name = f"watchlist_{list_type}"
        
        try:
            ws = spreadsheet.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            print(f"[i] {sheet_name} not found")
            return pd.DataFrame()
        
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        
        return df
        
    except Exception as e:
        print(f"[X] Failed to get watchlist: {e}")
        return pd.DataFrame()

def update_watchlist_metrics(list_type='flow'):
    """
    Cập nhật metrics cho watchlist
    
    Args:
        list_type: 'flow' hoặc 'fundamental'
    
    Returns:
        True nếu thành công, False nếu thất bại
    """
    try:
        spreadsheet = get_spreadsheet()
        if not spreadsheet:
            return False
        
        sheet_name = f"watchlist_{list_type}"
        
        try:
            ws = spreadsheet.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            print(f"[i] {sheet_name} not found")
            return False
        
        watchlist_df = pd.DataFrame(ws.get_all_records())
        
        if watchlist_df.empty:
            print(f"[i] {sheet_name} is empty")
            return True
        
        if list_type == 'flow':
            # Cập nhật avg_flow_7d từ intraday_flow
            try:
                intraday_ws = spreadsheet.worksheet("intraday_flow")
                intraday_data = intraday_ws.get_all_records()
                intraday_df = pd.DataFrame(intraday_data)
                
                if not intraday_df.empty:
                    # Tính avg flow 7 ngày gần nhất
                    intraday_df['timestamp'] = pd.to_datetime(intraday_df['timestamp'])
                    cutoff_date = datetime.now() - pd.Timedelta(days=7)
                    recent_df = intraday_df[intraday_df['timestamp'] >= cutoff_date]
                    
                    avg_flow = recent_df.groupby('ticker')['money_flow_normalized'].mean().reset_index()
                    avg_flow.columns = ['ticker', 'avg_flow_7d']
                    
                    # Merge với watchlist
                    watchlist_df = watchlist_df.merge(avg_flow, on='ticker', how='left', suffixes=('', '_new'))
                    watchlist_df['avg_flow_7d'] = watchlist_df['avg_flow_7d_new'].fillna(watchlist_df['avg_flow_7d'])
                    watchlist_df = watchlist_df.drop(columns=['avg_flow_7d_new'], errors='ignore')
            except Exception as e:
                print(f"[!] Failed to update flow metrics: {e}")
        
        else:  # fundamental
            # Cập nhật ROE, ROA, EPS, dividend_yield từ finance sheets
            try:
                # Đọc income sheet
                income_ws = spreadsheet.worksheet("income")
                income_data = income_ws.get_all_records()
                income_df = pd.DataFrame(income_data)
                
                # Đọc balance sheet
                balance_ws = spreadsheet.worksheet("balance")
                balance_data = balance_ws.get_all_records()
                balance_df = pd.DataFrame(balance_data)
                
                if not income_df.empty and not balance_df.empty:
                    # Tính ROE, ROA cho từng ticker
                    for idx, row in watchlist_df.iterrows():
                        ticker = row['ticker']
                        
                        ticker_income = income_df[income_df['ticker'] == ticker]
                        ticker_balance = balance_df[balance_df['ticker'] == ticker]
                        
                        if not ticker_income.empty and not ticker_balance.empty:
                            latest_income = ticker_income.iloc[-1]
                            latest_balance = ticker_balance.iloc[-1]
                            
                            # Tính metrics
                            net_income = pd.to_numeric(latest_income.get('net_income', 0), errors='coerce')
                            equity = pd.to_numeric(latest_balance.get('equity', 0), errors='coerce')
                            total_assets = pd.to_numeric(latest_balance.get('total_assets', 0), errors='coerce')
                            eps = pd.to_numeric(latest_income.get('eps', 0), errors='coerce')
                            
                            roe = (net_income / equity * 100) if equity and equity > 0 else 0
                            roa = (net_income / total_assets * 100) if total_assets and total_assets > 0 else 0
                            
                            watchlist_df.at[idx, 'roe'] = round(roe, 2)
                            watchlist_df.at[idx, 'roa'] = round(roa, 2)
                            watchlist_df.at[idx, 'eps'] = round(eps, 0)
                            # dividend_yield cần tính từ dữ liệu cổ tức (tạm thời để trống)
            except Exception as e:
                print(f"[!] Failed to update fundamental metrics: {e}")
        
        # Ghi lại
        ws.clear()
        ws.update([watchlist_df.columns.values.tolist()] + watchlist_df.astype(str).values.tolist())
        
        print(f"[OK] Updated {sheet_name} metrics")
        return True
        
    except Exception as e:
        print(f"[X] Failed to update watchlist metrics: {e}")
        return False

def merge_watchlists():
    """
    Gộp 2 watchlist để phân tích
    
    Returns:
        DataFrame chứa tất cả tickers từ cả 2 watchlist
    """
    flow_df = get_watchlist('flow')
    fundamental_df = get_watchlist('fundamental')
    
    # Lấy unique tickers
    all_tickers = set()
    if not flow_df.empty:
        all_tickers.update(flow_df['ticker'].tolist())
    if not fundamental_df.empty:
        all_tickers.update(fundamental_df['ticker'].tolist())
    
    return pd.DataFrame({'ticker': list(all_tickers)})

# ===== CLI Interface =====
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Quản lý watchlist')
    parser.add_argument('--add', type=str, help='Thêm ticker vào watchlist')
    parser.add_argument('--remove', type=str, help='Xóa ticker khỏi watchlist')
    parser.add_argument('--list', action='store_true', help='Hiển thị watchlist')
    parser.add_argument('--update', action='store_true', help='Cập nhật metrics')
    parser.add_argument('--type', type=str, default='flow', choices=['flow', 'fundamental'],
                        help='Loại watchlist (default: flow)')
    parser.add_argument('--note', type=str, default='', help='Ghi chú khi thêm ticker')
    
    args = parser.parse_args()
    
    if args.add:
        add_to_watchlist(args.add, args.type, args.note)
    elif args.remove:
        remove_from_watchlist(args.remove, args.type)
    elif args.list:
        df = get_watchlist(args.type)
        if not df.empty:
            print(f"\n{args.type.upper()} Watchlist:")
            print(df.to_string(index=False))
        else:
            print(f"\n{args.type.upper()} Watchlist is empty")
    elif args.update:
        update_watchlist_metrics(args.type)
    else:
        parser.print_help()
