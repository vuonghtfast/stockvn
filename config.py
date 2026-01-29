# -*- coding: utf-8 -*-
"""
Centralized Configuration Management
Reads from Google Sheets 'config' sheet with fallback to .env
"""

import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import json
import sys
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Cache config to reduce API calls
_config_cache = {}
_cache_timestamp = None
CACHE_TTL_SECONDS = 300  # 5 minutes

def get_google_credentials():
    """Load Google credentials from environment, file, or Streamlit secrets"""
    
    # Try environment variable FIRST (for GitHub Actions)
    if "GOOGLE_CREDENTIALS" in os.environ:
        try:
            creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
            print("[OK] Loaded credentials from environment variable")
            return ServiceAccountCredentials.from_json_keyfile_dict(
                creds_dict,
                ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            )
        except Exception as e:
            print(f"[!] Error loading credentials from environment: {e}")
    
    # Fallback to credentials.json SECOND (for local development - avoids Streamlit import)
    if os.path.exists("credentials.json"):
        print("[OK] Loaded credentials from credentials.json")
        return ServiceAccountCredentials.from_json_keyfile_name(
            "credentials.json",
            ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        )
    
    # Try Streamlit secrets LAST (for Streamlit Cloud only)
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and 'GOOGLE_CREDENTIALS' in st.secrets:
            creds_json = st.secrets['GOOGLE_CREDENTIALS']
            if isinstance(creds_json, str):
                creds_dict = json.loads(creds_json)
            else:
                creds_dict = dict(creds_json)
            
            print("[OK] Loaded credentials from Streamlit secrets")
            return ServiceAccountCredentials.from_json_keyfile_dict(
                creds_dict,
                ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            )
    except (ImportError, AttributeError, KeyError) as e:
        pass  # Silently skip if Streamlit not available
    
    raise Exception("No credentials found. Please set GOOGLE_CREDENTIALS environment variable, Streamlit secrets, or add credentials.json")

def get_config(key=None, default=None):
    """
    Get configuration value from Google Sheets or .env
    
    Args:
        key: Config key to retrieve (None = get all)
        default: Default value if key not found
    
    Returns:
        Config value or dict of all configs
    """
    global _config_cache, _cache_timestamp
    
    # Check cache
    now = datetime.now()
    if _cache_timestamp and (now - _cache_timestamp).total_seconds() < CACHE_TTL_SECONDS:
        if key:
            return _config_cache.get(key, default)
        return _config_cache
    
    # Default configuration
    default_config = {
        "update_interval_minutes": int(os.getenv("UPDATE_INTERVAL_MINUTES", "10")),
        "alert_cooldown_hours": int(os.getenv("ALERT_COOLDOWN_HOURS", "1")),
        "recommendation_refresh_hours": int(os.getenv("RECOMMENDATION_REFRESH_HOURS", "24")),
        "backtest_start_date": os.getenv("BACKTEST_START_DATE", "2021-01-01"),
        "risk_free_rate": float(os.getenv("RISK_FREE_RATE", "0.05")),
        "data_retention_days": int(os.getenv("DATA_RETENTION_DAYS", "30")),
        "historical_years": int(os.getenv("HISTORICAL_YEARS", "5")),
    }
    
    try:
        # Try to read from Google Sheets
        creds = get_google_credentials()
        client = gspread.authorize(creds)
        
        spreadsheet_id = os.getenv("SPREADSHEET_ID")
        if spreadsheet_id:
            spreadsheet = client.open_by_key(spreadsheet_id)
        else:
            spreadsheet = client.open("stockdata")
        
        # Try to get config sheet
        try:
            config_sheet = spreadsheet.worksheet("config")
            config_data = config_sheet.get_all_records()
            
            # Convert list of dicts to single dict
            for row in config_data:
                key_name = row.get("key")
                value = row.get("value")
                if key_name and value:
                    # Try to convert to appropriate type
                    try:
                        if "." in str(value):
                            default_config[key_name] = float(value)
                        else:
                            default_config[key_name] = int(value)
                    except (ValueError, TypeError):
                        default_config[key_name] = value
            
            print("[OK] Loaded config from Google Sheets")
        except gspread.WorksheetNotFound:
            print("[!] Sheet 'config' không tồn tại. Tạo sheet mẫu...")
            create_default_config_sheet(spreadsheet)
            print("[OK] Đã tạo sheet 'config' mẫu. Sử dụng config mặc định.")
    
    except Exception as e:
        print(f"[!] Không thể đọc config từ Sheets: {e}. Sử dụng .env và defaults.")
    
    # Update cache
    _config_cache = default_config
    _cache_timestamp = now
    
    if key:
        return _config_cache.get(key, default)
    return _config_cache

def create_default_config_sheet(spreadsheet):
    """Create default config sheet with sample values"""
    try:
        config_sheet = spreadsheet.add_worksheet(title="config", rows="20", cols="3")
        config_sheet.update([
            ["key", "value", "description"],
            ["update_interval_minutes", "10", "Tần suất cập nhật giá (phút)"],
            ["alert_cooldown_hours", "1", "Thời gian chờ giữa các alert (giờ)"],
            ["recommendation_refresh_hours", "24", "Tần suất cập nhật khuyến nghị (giờ)"],
            ["backtest_start_date", "2021-01-01", "Ngày bắt đầu backtest"],
            ["risk_free_rate", "0.05", "Lãi suất phi rủi ro (5%)"],
            ["data_retention_days", "30", "Số ngày giữ data trong Sheets"],
            ["historical_years", "5", "Số năm lưu historical data trong SQLite"],
        ])
    except Exception as e:
        print(f"[X] Lỗi tạo config sheet: {e}")

def update_config(key, value):
    """
    Update configuration value in Google Sheets
    
    Args:
        key: Config key to update
        value: New value
    """
    global _config_cache, _cache_timestamp
    
    try:
        creds = get_google_credentials()
        client = gspread.authorize(creds)
        
        spreadsheet_id = os.getenv("SPREADSHEET_ID")
        if spreadsheet_id:
            spreadsheet = client.open_by_key(spreadsheet_id)
        else:
            spreadsheet = client.open("stockdata")
        
        config_sheet = spreadsheet.worksheet("config")
        
        # Find the row with the key
        cell = config_sheet.find(key)
        if cell:
            # Update the value in the next column
            config_sheet.update_cell(cell.row, 2, value)
            print(f"[OK] Updated config: {key} = {value}")
            
            # Invalidate cache
            _cache_timestamp = None
        else:
            print(f"[!] Config key '{key}' not found in sheet")
    
    except Exception as e:
        print(f"[X] Lỗi cập nhật config: {e}")

if __name__ == "__main__":
    # Test config loading
    print("=== Testing Config Management ===")
    config = get_config()
    print("\nAll configs:")
    for k, v in config.items():
        print(f"  {k}: {v}")
    
    print(f"\nUpdate interval: {get_config('update_interval_minutes')} minutes")
    print(f"Backtest start: {get_config('backtest_start_date')}")
