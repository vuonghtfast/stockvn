# -*- coding: utf-8 -*-
"""
Ticker Management Helper
Functions to add/remove tickers from Google Sheets
"""

import gspread
from typing import List, Tuple

def get_current_tickers(spreadsheet) -> List[str]:
    """Get current list of tickers from watchlist_flow sheet"""
    try:
        ws = spreadsheet.worksheet("watchlist_flow")
        tickers = ws.col_values(1)[1:]  # Skip header (column 'ticker')
        return [t.strip().upper() for t in tickers if t.strip()]
    except Exception as e:
        print(f"Error getting tickers: {e}")
        return []

def add_ticker(spreadsheet, ticker: str) -> Tuple[bool, str]:
    """
    Add ticker to watchlist_flow sheet
    Returns: (success, message)
    """
    try:
        ticker = ticker.strip().upper()
        
        # Validate ticker format (2-4 letters)
        if not ticker or len(ticker) < 2 or len(ticker) > 4:
            return False, "Mã cổ phiếu phải có 2-4 ký tự"
        
        if not ticker.isalpha():
            return False, "Mã cổ phiếu chỉ được chứa chữ cái"
        
        # Check if already exists
        current_tickers = get_current_tickers(spreadsheet)
        if ticker in current_tickers:
            return False, f"Mã {ticker} đã tồn tại trong danh sách"
        
        # Add to watchlist_flow sheet
        ws = spreadsheet.worksheet("watchlist_flow")
        # Add with empty values for other columns (added_date, notes, etc.)
        from datetime import datetime
        ws.append_row([ticker, datetime.now().strftime("%Y-%m-%d"), ""])
        
        return True, f"✅ Đã thêm {ticker} vào danh sách theo dõi"
    
    except Exception as e:
        return False, f"Lỗi: {str(e)}"

def remove_ticker(spreadsheet, ticker: str) -> Tuple[bool, str]:
    """
    Remove ticker from watchlist_flow sheet
    Returns: (success, message)
    """
    try:
        ticker = ticker.strip().upper()
        
        # Get current tickers
        current_tickers = get_current_tickers(spreadsheet)
        
        if ticker not in current_tickers:
            return False, f"Mã {ticker} không tồn tại trong danh sách"
        
        # Prevent removing last ticker
        if len(current_tickers) <= 1:
            return False, "Không thể xóa mã cuối cùng"
        
        # Find and remove from watchlist_flow
        ws = spreadsheet.worksheet("watchlist_flow")
        cell = ws.find(ticker)
        if cell:
            ws.delete_rows(cell.row)
            return True, f"✅ Đã xóa {ticker} khỏi danh sách theo dõi"
        else:
            return False, f"Không tìm thấy {ticker}"
    
    except Exception as e:
        return False, f"Lỗi: {str(e)}"

def format_price(value, decimals=2):
    """Format price with proper decimal places"""
    try:
        if value is None or value == '':
            return "N/A"
        
        num_value = float(value)
        
        # Format with thousand separators and decimals
        return f"{num_value:,.{decimals}f}"
    except (ValueError, TypeError):
        return str(value)

def format_volume(value):
    """Format volume with thousand separators"""
    try:
        if value is None or value == '':
            return "N/A"
        
        num_value = int(float(value))
        return f"{num_value:,}"
    except (ValueError, TypeError):
        return str(value)
