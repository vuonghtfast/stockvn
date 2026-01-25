# -*- coding: utf-8 -*-
"""
Data Aggregator
Aggregates historical price data into weekly/monthly summaries
Calculates technical indicators and support/resistance levels
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from data_archiver import get_historical_data, get_google_credentials, DB_PATH
import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()

def calculate_atr(df, period=14):
    """Calculate Average True Range (ATR) - volatility indicator"""
    high = df['high'].astype(float)
    low = df['low'].astype(float)
    close = df['close'].astype(float)
    
    # True Range = max(high-low, abs(high-prev_close), abs(low-prev_close))
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = abs(high - prev_close)
    tr3 = abs(low - prev_close)
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    return atr

def find_support_resistance(df, window=20):
    """
    Find support and resistance levels using local minima/maxima
    
    Returns:
        dict with 'support' and 'resistance' price levels
    """
    close = df['close'].astype(float)
    
    # Find local minima (support)
    local_min = close[(close.shift(1) > close) & (close.shift(-1) > close)]
    
    # Find local maxima (resistance)
    local_max = close[(close.shift(1) < close) & (close.shift(-1) < close)]
    
    # Get most recent levels
    support_levels = local_min.tail(3).tolist() if not local_min.empty else []
    resistance_levels = local_max.tail(3).tolist() if not local_max.empty else []
    
    return {
        'support': support_levels,
        'resistance': resistance_levels
    }

def aggregate_to_weekly(df):
    """Aggregate daily data to weekly OHLCV"""
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')
    
    # Convert to numeric
    for col in ['open', 'high', 'low', 'close', 'volume', 'value']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Resample to weekly (W-FRI = week ending Friday)
    weekly = df.resample('W-FRI').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum',
        'value': 'sum',
        'ticker': 'first'
    })
    
    weekly = weekly.reset_index()
    weekly['timestamp'] = weekly['timestamp'].dt.strftime('%Y-%m-%d')
    
    return weekly

def aggregate_to_monthly(df):
    """Aggregate daily data to monthly OHLCV"""
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')
    
    # Convert to numeric
    for col in ['open', 'high', 'low', 'close', 'volume', 'value']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Resample to monthly (M = month end)
    monthly = df.resample('M').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum',
        'value': 'sum',
        'ticker': 'first'
    })
    
    monthly = monthly.reset_index()
    monthly['timestamp'] = monthly['timestamp'].dt.strftime('%Y-%m-%d')
    
    return monthly

def save_aggregated_data(weekly_df, monthly_df):
    """Save aggregated data to SQLite"""
    if not os.path.exists(DB_PATH):
        print("⚠️ Database chưa tồn tại. Chạy data_archiver.py trước.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    
    # Create tables if not exist
    conn.execute("""
        CREATE TABLE IF NOT EXISTS price_weekly (
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
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS price_monthly (
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
    
    # Save data
    if not weekly_df.empty:
        weekly_df.to_sql('price_weekly', conn, if_exists='replace', index=False)
        print(f"✅ Saved {len(weekly_df)} weekly records")
    
    if not monthly_df.empty:
        monthly_df.to_sql('price_monthly', conn, if_exists='replace', index=False)
        print(f"✅ Saved {len(monthly_df)} monthly records")
    
    conn.close()

def aggregate_all_tickers():
    """Main aggregation function"""
    try:
        # Get list of tickers from Google Sheets
        import gspread
        creds = get_google_credentials()
        client = gspread.authorize(creds)
        
        spreadsheet_id = os.getenv("SPREADSHEET_ID")
        if spreadsheet_id:
            spreadsheet = client.open_by_key(spreadsheet_id)
        else:
            spreadsheet = client.open("stockdata")
        
        tickers_sheet = spreadsheet.worksheet("tickers")
        tickers = tickers_sheet.col_values(1)[1:]
        
        print(f"📊 Aggregating data for {len(tickers)} tickers...")
        
        all_weekly = []
        all_monthly = []
        
        # Get date range (last 5 years)
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=365*5)).strftime("%Y-%m-%d")
        
        for ticker in tickers:
            print(f"\n--- Processing {ticker} ---")
            
            # Get historical data (from SQLite + Sheets)
            df = get_historical_data(ticker, start_date, end_date)
            
            if df.empty:
                print(f"⚠️ No data for {ticker}")
                continue
            
            # Calculate ATR
            df['atr'] = calculate_atr(df)
            
            # Find support/resistance
            levels = find_support_resistance(df)
            print(f"Support levels: {levels['support']}")
            print(f"Resistance levels: {levels['resistance']}")
            
            # Aggregate to weekly
            weekly = aggregate_to_weekly(df.copy())
            if not weekly.empty:
                all_weekly.append(weekly)
            
            # Aggregate to monthly
            monthly = aggregate_to_monthly(df.copy())
            if not monthly.empty:
                all_monthly.append(monthly)
        
        # Combine and save
        if all_weekly:
            weekly_df = pd.concat(all_weekly, ignore_index=True)
            print(f"\n📊 Total weekly records: {len(weekly_df)}")
        else:
            weekly_df = pd.DataFrame()
        
        if all_monthly:
            monthly_df = pd.concat(all_monthly, ignore_index=True)
            print(f"📊 Total monthly records: {len(monthly_df)}")
        else:
            monthly_df = pd.DataFrame()
        
        # Save to database
        save_aggregated_data(weekly_df, monthly_df)
        
        print("\n✅ Aggregation completed")
    
    except Exception as e:
        print(f"❌ Lỗi aggregation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=== Data Aggregator ===")
    aggregate_all_tickers()
