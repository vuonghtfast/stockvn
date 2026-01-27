# -*- coding: utf-8 -*-
"""
Hybrid Storage Manager
Manages data archival from Google Sheets to SQLite for long-term storage
"""

import sqlite3
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import os
import sys
import json
from dotenv import load_dotenv
from config import get_config

# Load environment variables
load_dotenv()

# SQLite database path
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "stockvn.db")

def get_google_credentials():
    """Load Google credentials from environment or file"""
    try:
        if "GOOGLE_CREDENTIALS" in os.environ:
            creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
            return ServiceAccountCredentials.from_json_keyfile_dict(
                creds_dict,
                ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            )
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

def init_database():
    """Initialize SQLite database with schema"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create price_history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            timestamp TEXT NOT NULL,
            ticker TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            value REAL,
            PRIMARY KEY (timestamp, ticker)
        )
    """)
    
    # Create indexes for fast queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ticker_date 
        ON price_history(ticker, timestamp)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_timestamp 
        ON price_history(timestamp)
    """)
    
    # Create metadata table to track archival
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS archival_metadata (
            last_archival_date TEXT,
            total_records INTEGER,
            last_updated TEXT
        )
    """)
    
    conn.commit()
    conn.close()
    print("[OK] Database initialized")

def archive_old_data():
    """
    Archive data older than retention period from Google Sheets to SQLite
    """
    try:
        # Get configuration
        retention_days = get_config("data_retention_days", 30)
        cutoff_date = (datetime.now() - timedelta(days=retention_days)).strftime("%Y-%m-%d")
        
        print(f"📦 Archiving data older than {cutoff_date} (retention: {retention_days} days)")
        
        # Connect to Google Sheets
        creds = get_google_credentials()
        client = gspread.authorize(creds)
        
        spreadsheet_id = os.getenv("SPREADSHEET_ID")
        if spreadsheet_id:
            spreadsheet = client.open_by_key(spreadsheet_id)
        else:
            spreadsheet = client.open("stockdata")
        
        # Check if price_history sheet exists
        try:
            history_sheet = spreadsheet.worksheet("price_history")
        except gspread.WorksheetNotFound:
            print("[!] Sheet 'price_history' không tồn tại. Không có gì để archive.")
            return
        
        # Read all data from price_history
        all_data = history_sheet.get_all_records()
        if not all_data:
            print("[!] Sheet 'price_history' trống.")
            return
        
        df = pd.DataFrame(all_data)
        
        # Ensure timestamp column exists
        if 'timestamp' not in df.columns and 'time' in df.columns:
            df['timestamp'] = df['time']
        
        if 'timestamp' not in df.columns:
            print("[X] Không tìm thấy cột timestamp/time trong data")
            return
        
        # Filter old data (to archive)
        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime("%Y-%m-%d")
        old_data = df[df['timestamp'] < cutoff_date].copy()
        recent_data = df[df['timestamp'] >= cutoff_date].copy()
        
        if old_data.empty:
            print(f"[OK] Không có data cũ hơn {cutoff_date} để archive")
            return
        
        print(f"[CHART] Found {len(old_data)} records to archive, {len(recent_data)} to keep in Sheets")
        
        # Initialize database
        init_database()
        
        # Archive to SQLite
        conn = sqlite3.connect(DB_PATH)
        
        # Ensure required columns exist
        required_cols = ['timestamp', 'ticker', 'open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in old_data.columns:
                old_data[col] = None
        
        # Add value column if not exists
        if 'value' not in old_data.columns:
            old_data['value'] = old_data['close'] * old_data['volume']
        
        # Select only required columns
        archive_df = old_data[['timestamp', 'ticker', 'open', 'high', 'low', 'close', 'volume', 'value']]
        
        # Insert into SQLite (ignore duplicates)
        archive_df.to_sql('price_history', conn, if_exists='append', index=False)
        
        # Update metadata
        cursor = conn.cursor()
        cursor.execute("DELETE FROM archival_metadata")
        cursor.execute("""
            INSERT INTO archival_metadata (last_archival_date, total_records, last_updated)
            VALUES (?, ?, ?)
        """, (cutoff_date, len(archive_df), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        conn.commit()
        conn.close()
        
        print(f"[OK] Archived {len(archive_df)} records to SQLite")
        
        # Update Google Sheets to keep only recent data
        if not recent_data.empty:
            history_sheet.clear()
            history_sheet.update([recent_data.columns.values.tolist()] + recent_data.values.tolist())
            print(f"[OK] Updated Sheets to keep {len(recent_data)} recent records")
        else:
            print("[!] Không có data gần đây để giữ lại trong Sheets")
    
    except Exception as e:
        print(f"[X] Lỗi archive data: {e}")
        import traceback
        traceback.print_exc()

def get_historical_data(ticker, start_date, end_date):
    """
    Unified query interface: Get data from SQLite (old) + Sheets (recent)
    
    Args:
        ticker: Stock ticker symbol
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
    
    Returns:
        DataFrame with historical price data
    """
    all_data = []
    
    # Get retention period
    retention_days = get_config("data_retention_days", 30)
    cutoff_date = (datetime.now() - timedelta(days=retention_days)).strftime("%Y-%m-%d")
    
    # 1. Query from SQLite for old data
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            query = """
                SELECT * FROM price_history
                WHERE ticker = ? AND timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp
            """
            sqlite_df = pd.read_sql_query(query, conn, params=(ticker, start_date, min(end_date, cutoff_date)))
            conn.close()
            
            if not sqlite_df.empty:
                all_data.append(sqlite_df)
                print(f"[CHART] Loaded {len(sqlite_df)} records from SQLite for {ticker}")
        except Exception as e:
            print(f"[!] Lỗi query SQLite: {e}")
    
    # 2. Query from Google Sheets for recent data
    try:
        creds = get_google_credentials()
        client = gspread.authorize(creds)
        
        spreadsheet_id = os.getenv("SPREADSHEET_ID")
        if spreadsheet_id:
            spreadsheet = client.open_by_key(spreadsheet_id)
        else:
            spreadsheet = client.open("stockdata")
        
        history_sheet = spreadsheet.worksheet("price_history")
        sheets_data = history_sheet.get_all_records()
        
        if sheets_data:
            sheets_df = pd.DataFrame(sheets_data)
            
            # Normalize column names
            if 'time' in sheets_df.columns:
                sheets_df['timestamp'] = sheets_df['time']
            
            # Filter by ticker and date range
            sheets_df['timestamp'] = pd.to_datetime(sheets_df['timestamp']).dt.strftime("%Y-%m-%d")
            filtered = sheets_df[
                (sheets_df['ticker'] == ticker) &
                (sheets_df['timestamp'] >= max(start_date, cutoff_date)) &
                (sheets_df['timestamp'] <= end_date)
            ]
            
            if not filtered.empty:
                all_data.append(filtered)
                print(f"[CHART] Loaded {len(filtered)} records from Sheets for {ticker}")
    
    except Exception as e:
        print(f"[!] Lỗi query Sheets: {e}")
    
    # 3. Merge and return
    if all_data:
        result = pd.concat(all_data, ignore_index=True)
        result = result.sort_values('timestamp').drop_duplicates(subset=['timestamp', 'ticker'])
        print(f"[OK] Total {len(result)} records for {ticker} from {start_date} to {end_date}")
        return result
    else:
        print(f"[!] Không tìm thấy data cho {ticker}")
        return pd.DataFrame()

def get_database_stats():
    """Get statistics about archived data"""
    if not os.path.exists(DB_PATH):
        print("[!] Database chưa tồn tại")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get total records
    cursor.execute("SELECT COUNT(*) FROM price_history")
    total_records = cursor.fetchone()[0]
    
    # Get date range
    cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM price_history")
    date_range = cursor.fetchone()
    
    # Get tickers count
    cursor.execute("SELECT COUNT(DISTINCT ticker) FROM price_history")
    ticker_count = cursor.fetchone()[0]
    
    # Get metadata
    cursor.execute("SELECT * FROM archival_metadata")
    metadata = cursor.fetchone()
    
    conn.close()
    
    print("\n=== Database Statistics ===")
    print(f"Total records: {total_records:,}")
    print(f"Date range: {date_range[0]} to {date_range[1]}")
    print(f"Tickers: {ticker_count}")
    if metadata:
        print(f"Last archival: {metadata[0]}")
        print(f"Last updated: {metadata[2]}")
    print(f"Database size: {os.path.getsize(DB_PATH) / 1024 / 1024:.2f} MB")

if __name__ == "__main__":
    print("=== Data Archiver ===")
    
    # Initialize database
    init_database()
    
    # Archive old data
    archive_old_data()
    
    # Show stats
    get_database_stats()
