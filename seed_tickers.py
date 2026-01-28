# -*- coding: utf-8 -*-
import gspread
from config import get_google_credentials
import os
from dotenv import load_dotenv
from sectors import get_sector

load_dotenv()

def seed_tickers():
    try:
        creds = get_google_credentials()
        client = gspread.authorize(creds)
        spreadsheet_id = os.getenv("SPREADSHEET_ID")
        spreadsheet = client.open_by_key(spreadsheet_id)
        
        try:
            ws = spreadsheet.worksheet("tickers")
        except:
            ws = spreadsheet.add_worksheet("tickers", 1000, 5)
            ws.append_row(["ticker", "sector", "exchange"])
            
        existing_tickers = set(ws.col_values(1)[1:])
        
        # List of tickers to add
        vn30 = ['ACB', 'BCM', 'BID', 'BVH', 'CTG', 'FPT', 'GAS', 'GVR', 'HDB', 'HPG', 
                'MBB', 'MSN', 'MWG', 'PLX', 'POW', 'SAB', 'SHB', 'SSB', 'SSI', 'STB', 
                'TCB', 'TPB', 'VCB', 'VHM', 'VIB', 'VIC', 'VJC', 'VNM', 'VPB', 'VRE']
                
        hot_stocks = ['DIG', 'CEO', 'DXG', 'NVL', 'PDR', 'VIX', 'VND', 'HCM', 'NKG', 'HSG', 'DBC', 'HAG', 'DGC', 'FTS', 'BSI']
        
        all_tickers = sorted(list(set(vn30 + hot_stocks)))
        
        added_count = 0
        rows_to_add = []
        
        for ticker in all_tickers:
            if ticker not in existing_tickers:
                sector = get_sector(ticker)
                rows_to_add.append([ticker, sector, "HOSE"]) # Assuming HOSE for simplicity/majority
                added_count += 1
        
        if rows_to_add:
            ws.append_rows(rows_to_add)
            print(f"[OK] Added {added_count} tickers to watchlist.")
        else:
            print("[i] All tickers already exist.")
            
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    seed_tickers()
