# -*- coding: utf-8 -*-
"""
Cleanup Helper - Xóa dữ liệu của tickers không còn trong danh sách
"""

import gspread
import pandas as pd

def cleanup_removed_tickers(spreadsheet, current_tickers, sheets_to_clean):
    """
    Xóa dữ liệu của các tickers không còn trong danh sách hiện tại
    
    Args:
        spreadsheet: gspread Spreadsheet object
        current_tickers: List of current ticker symbols
        sheets_to_clean: List of sheet names to clean
    """
    print(f"\n[CLEANUP] Checking for removed tickers...")
    print(f"[i] Current tickers: {len(current_tickers)} tickers")
    
    for sheet_name in sheets_to_clean:
        try:
            ws = spreadsheet.worksheet(sheet_name)
            data = ws.get_all_records()
            
            if not data:
                print(f"  - {sheet_name}: Empty sheet, skipping")
                continue
            
            df = pd.DataFrame(data)
            
            # Check if 'ticker' column exists
            if 'ticker' not in df.columns:
                print(f"  - {sheet_name}: No 'ticker' column, skipping")
                continue
            
            # Find tickers to remove
            existing_tickers = df['ticker'].unique().tolist()
            removed_tickers = [t for t in existing_tickers if t not in current_tickers]
            
            if not removed_tickers:
                print(f"  - {sheet_name}: No removed tickers")
                continue
            
            # Remove rows with removed tickers
            df_cleaned = df[df['ticker'].isin(current_tickers)]
            rows_removed = len(df) - len(df_cleaned)
            
            if rows_removed > 0:
                # Update sheet with cleaned data
                ws.clear()
                ws.update([df_cleaned.columns.values.tolist()] + df_cleaned.astype(str).values.tolist())
                print(f"  - {sheet_name}: Removed {rows_removed} rows for tickers: {removed_tickers}")
            
        except gspread.WorksheetNotFound:
            print(f"  - {sheet_name}: Sheet not found, skipping")
        except Exception as e:
            print(f"  - {sheet_name}: Error during cleanup: {e}")
    
    print(f"[CLEANUP] Cleanup complete\n")

if __name__ == "__main__":
    print("This is a helper module. Import and use cleanup_removed_tickers() function.")
