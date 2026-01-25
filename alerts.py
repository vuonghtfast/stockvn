# -*- coding: utf-8 -*-
"""
Enhanced Alert System for Stock Price Monitoring
Supports: price thresholds, volume spikes, multi-condition rules, cooldown, and history tracking
"""

import os
import sys
import gspread
import requests
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json
from config import get_config

# Load environment variables
load_dotenv()

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
        print(f"❌ Lỗi tải credentials: {e}")
        sys.exit(1)

def send_telegram_message(message):
    """Send message via Telegram bot"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("⚠️ Telegram credentials not configured. Skipping alert.")
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"✅ Đã gửi Telegram: {message[:50]}...")
            return True
        else:
            print(f"❌ Lỗi gửi Telegram: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Lỗi kết nối Telegram: {e}")
        return False

def calculate_average_volume(ticker, price_data, lookback_days=20):
    """Calculate average volume for a ticker over lookback period"""
    ticker_data = [row for row in price_data if row.get('ticker') == ticker]
    
    if len(ticker_data) < lookback_days:
        return None
    
    # Get last N days
    recent_data = ticker_data[-lookback_days:]
    volumes = [float(row.get('volume', 0)) for row in recent_data if row.get('volume')]
    
    if not volumes:
        return None
    
    return sum(volumes) / len(volumes)

def check_cooldown(ticker, alert_type, last_alert_time, cooldown_hours):
    """Check if alert is in cooldown period"""
    if not last_alert_time:
        return False  # No previous alert, not in cooldown
    
    try:
        last_time = datetime.strptime(last_alert_time, "%Y-%m-%d %H:%M:%S")
        now = datetime.now()
        hours_since = (now - last_time).total_seconds() / 3600
        
        if hours_since < cooldown_hours:
            print(f"⏳ {ticker} ({alert_type}): In cooldown ({hours_since:.1f}h < {cooldown_hours}h)")
            return True
        return False
    except:
        return False

def log_alert_history(spreadsheet, ticker, alert_type, message, triggered=True):
    """Log alert to history sheet"""
    try:
        try:
            history_sheet = spreadsheet.worksheet("alert_history")
        except gspread.WorksheetNotFound:
            history_sheet = spreadsheet.add_worksheet(title="alert_history", rows="1000", cols="6")
            history_sheet.update([[
                "timestamp", "ticker", "alert_type", "message", "triggered", "sent"
            ]])
        
        # Append new record
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        history_sheet.append_row([
            timestamp, ticker, alert_type, message, str(triggered), str(triggered)
        ])
        
    except Exception as e:
        print(f"⚠️ Lỗi log alert history: {e}")

def update_last_alert_time(alerts_sheet, row_num):
    """Update last_alert_time for an alert rule"""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        alerts_sheet.update_cell(row_num, 5, timestamp)  # Column 5 = last_alert_time
    except Exception as e:
        print(f"⚠️ Lỗi update last_alert_time: {e}")

def check_alerts():
    """Enhanced alert checking with multiple alert types"""
    try:
        # Get configuration
        cooldown_hours = get_config("alert_cooldown_hours", 1)
        
        # Connect to Google Sheets
        creds = get_google_credentials()
        client = gspread.authorize(creds)
        
        spreadsheet_id = os.getenv("SPREADSHEET_ID")
        if spreadsheet_id:
            spreadsheet = client.open_by_key(spreadsheet_id)
        else:
            spreadsheet = client.open("stockdata")
        
        # Read alerts configuration
        try:
            alerts_sheet = spreadsheet.worksheet("alerts")
            alerts_data = alerts_sheet.get_all_records()
        except gspread.WorksheetNotFound:
            print("⚠️ Sheet 'alerts' không tồn tại. Tạo sheet mẫu...")
            create_sample_alerts_sheet(spreadsheet)
            return
        
        # Read latest prices and historical data
        data_sheet = spreadsheet.worksheet("data")
        price_data = data_sheet.get_all_records()
        
        if not price_data:
            print("⚠️ Không có dữ liệu giá để kiểm tra.")
            return
        
        # Create price lookup dict
        latest_prices = {}
        latest_volumes = {}
        for row in price_data:
            ticker = row.get("ticker")
            close_price = row.get("close")
            volume = row.get("volume")
            if ticker and close_price:
                try:
                    latest_prices[ticker] = float(close_price)
                    latest_volumes[ticker] = float(volume) if volume else 0
                except (ValueError, TypeError):
                    continue
        
        # Check each alert
        alerts_triggered = []
        
        for idx, alert in enumerate(alerts_data, start=2):  # Start at row 2 (after header)
            ticker = alert.get("ticker")
            alert_type = alert.get("alert_type", "price_below")
            enabled = str(alert.get("enabled", "TRUE")).upper()
            last_alert_time = alert.get("last_alert_time", "")
            
            if enabled != "TRUE" or not ticker:
                continue
            
            # Check cooldown
            if check_cooldown(ticker, alert_type, last_alert_time, cooldown_hours):
                continue
            
            current_price = latest_prices.get(ticker)
            current_volume = latest_volumes.get(ticker, 0)
            
            if not current_price:
                continue
            
            triggered = False
            message = ""
            
            # === PRICE ALERTS ===
            if alert_type in ["below", "price_below"]:
                threshold = alert.get("threshold_price")
                if threshold:
                    try:
                        threshold = float(threshold)
                        if current_price < threshold:
                            triggered = True
                            message = f"🚨 <b>CẢNH BÁO GIÁ XUỐNG</b>\n\n" \
                                     f"Mã: <b>{ticker}</b>\n" \
                                     f"Giá hiện tại: <b>{current_price:,.0f} VNĐ</b>\n" \
                                     f"Ngưỡng: {threshold:,.0f} VNĐ\n" \
                                     f"Chênh lệch: {((current_price - threshold) / threshold * 100):.2f}%"
                    except (ValueError, TypeError):
                        pass
            
            elif alert_type in ["above", "price_above"]:
                threshold = alert.get("threshold_price")
                if threshold:
                    try:
                        threshold = float(threshold)
                        if current_price > threshold:
                            triggered = True
                            message = f"📈 <b>CẢNH BÁO GIÁ TĂNG</b>\n\n" \
                                     f"Mã: <b>{ticker}</b>\n" \
                                     f"Giá hiện tại: <b>{current_price:,.0f} VNĐ</b>\n" \
                                     f"Ngưỡng: {threshold:,.0f} VNĐ\n" \
                                     f"Chênh lệch: {((current_price - threshold) / threshold * 100):.2f}%"
                    except (ValueError, TypeError):
                        pass
            
            # === VOLUME ALERTS ===
            elif alert_type == "volume_spike":
                threshold_multiplier = alert.get("threshold_price", 2.0)  # Reuse field
                lookback_days = alert.get("lookback_days", 20)
                
                try:
                    threshold_multiplier = float(threshold_multiplier)
                    lookback_days = int(lookback_days) if lookback_days else 20
                    
                    avg_volume = calculate_average_volume(ticker, price_data, lookback_days)
                    
                    if avg_volume and current_volume > avg_volume * threshold_multiplier:
                        triggered = True
                        message = f"📊 <b>CẢNH BÁO KHỐI LƯỢNG BẤT THƯỜNG</b>\n\n" \
                                 f"Mã: <b>{ticker}</b>\n" \
                                 f"Khối lượng hiện tại: <b>{current_volume:,.0f}</b>\n" \
                                 f"Trung bình {lookback_days} ngày: {avg_volume:,.0f}\n" \
                                 f"Tăng: <b>{(current_volume / avg_volume):.2f}x</b> (ngưỡng: {threshold_multiplier}x)"
                except (ValueError, TypeError):
                    pass
            
            # === BREAKOUT ALERTS (Multi-condition) ===
            elif alert_type == "breakout":
                # Example: Price above resistance AND volume spike
                resistance = alert.get("threshold_price")
                volume_multiplier = alert.get("volume_multiplier", 1.5)
                
                try:
                    resistance = float(resistance)
                    volume_multiplier = float(volume_multiplier) if volume_multiplier else 1.5
                    
                    avg_volume = calculate_average_volume(ticker, price_data, 20)
                    
                    if current_price > resistance and avg_volume and current_volume > avg_volume * volume_multiplier:
                        triggered = True
                        message = f"🚀 <b>CẢNH BÁO BREAKOUT</b>\n\n" \
                                 f"Mã: <b>{ticker}</b>\n" \
                                 f"Giá: <b>{current_price:,.0f}</b> (vượt kháng cự {resistance:,.0f})\n" \
                                 f"Khối lượng: <b>{current_volume:,.0f}</b> ({(current_volume / avg_volume):.2f}x TB)"
                except (ValueError, TypeError):
                    pass
            
            # Log and send if triggered
            if triggered:
                alerts_triggered.append((ticker, alert_type, message))
                log_alert_history(spreadsheet, ticker, alert_type, message, True)
                update_last_alert_time(alerts_sheet, idx)
        
        # Send alerts
        if alerts_triggered:
            for ticker, alert_type, message in alerts_triggered:
                send_telegram_message(message)
            print(f"✅ Đã gửi {len(alerts_triggered)} cảnh báo.")
        else:
            print("✅ Không có cảnh báo nào được kích hoạt.")
    
    except Exception as e:
        print(f"❌ Lỗi kiểm tra alerts: {e}")
        import traceback
        traceback.print_exc()

def create_sample_alerts_sheet(spreadsheet):
    """Create sample alerts sheet with enhanced fields"""
    try:
        alerts_sheet = spreadsheet.add_worksheet(title="alerts", rows="100", cols="7")
        alerts_sheet.update([
            ["ticker", "threshold_price", "alert_type", "enabled", "last_alert_time", "lookback_days", "volume_multiplier"],
            ["VNM", "80000", "price_below", "TRUE", "", "", ""],
            ["VIC", "50000", "price_above", "TRUE", "", "", ""],
            ["FPT", "2.0", "volume_spike", "TRUE", "", "20", ""],
            ["HPG", "30000", "breakout", "TRUE", "", "", "1.5"],
        ])
        print("✅ Đã tạo sheet 'alerts' mẫu với các loại alert nâng cao.")
    except Exception as e:
        print(f"❌ Lỗi tạo alerts sheet: {e}")

if __name__ == "__main__":
    print("🔔 Bắt đầu kiểm tra alerts (Enhanced)...")
    check_alerts()
    print("✅ Hoàn tất kiểm tra alerts.")
