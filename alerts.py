# -*- coding: utf-8 -*-
"""
Alert System for Stock Price Monitoring
Kiểm tra giá và gửi thông báo qua Telegram khi đạt ngưỡng
"""

import os
import sys
import gspread
import requests
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

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

def check_alerts():
    """Check price alerts and send notifications"""
    try:
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
            # Create sample alerts sheet
            alerts_sheet = spreadsheet.add_worksheet(title="alerts", rows="100", cols="5")
            alerts_sheet.update([
                ["ticker", "threshold_price", "alert_type", "enabled", "last_alert_time"],
                ["VNM", "80000", "below", "TRUE", ""],
                ["VIC", "50000", "below", "TRUE", ""]
            ])
            print("✅ Đã tạo sheet 'alerts' mẫu. Vui lòng cấu hình ngưỡng giá.")
            return
        
        # Read latest prices
        data_sheet = spreadsheet.worksheet("data")
        price_data = data_sheet.get_all_records()
        
        if not price_data:
            print("⚠️ Không có dữ liệu giá để kiểm tra.")
            return
        
        # Create price lookup dict (latest price for each ticker)
        latest_prices = {}
        for row in price_data:
            ticker = row.get("ticker")
            close_price = row.get("close")
            if ticker and close_price:
                try:
                    latest_prices[ticker] = float(close_price)
                except (ValueError, TypeError):
                    continue
        
        # Check each alert
        alerts_triggered = []
        for alert in alerts_data:
            ticker = alert.get("ticker")
            threshold = alert.get("threshold_price")
            alert_type = alert.get("alert_type", "below")
            enabled = str(alert.get("enabled", "TRUE")).upper()
            
            if enabled != "TRUE" or not ticker or not threshold:
                continue
            
            current_price = latest_prices.get(ticker)
            if not current_price:
                continue
            
            try:
                threshold = float(threshold)
            except (ValueError, TypeError):
                continue
            
            # Check condition
            triggered = False
            if alert_type == "below" and current_price < threshold:
                triggered = True
                message = f"🚨 <b>CẢNH BÁO GIÁ XUỐNG</b>\n\n" \
                         f"Mã: <b>{ticker}</b>\n" \
                         f"Giá hiện tại: <b>{current_price:,.0f} VNĐ</b>\n" \
                         f"Ngưỡng: {threshold:,.0f} VNĐ\n" \
                         f"Chênh lệch: {((current_price - threshold) / threshold * 100):.2f}%"
            elif alert_type == "above" and current_price > threshold:
                triggered = True
                message = f"📈 <b>CẢNH BÁO GIÁ TĂNG</b>\n\n" \
                         f"Mã: <b>{ticker}</b>\n" \
                         f"Giá hiện tại: <b>{current_price:,.0f} VNĐ</b>\n" \
                         f"Ngưỡng: {threshold:,.0f} VNĐ\n" \
                         f"Chênh lệch: {((current_price - threshold) / threshold * 100):.2f}%"
            
            if triggered:
                alerts_triggered.append((ticker, message))
        
        # Send alerts
        if alerts_triggered:
            for ticker, message in alerts_triggered:
                send_telegram_message(message)
            print(f"✅ Đã gửi {len(alerts_triggered)} cảnh báo.")
        else:
            print("✅ Không có cảnh báo nào được kích hoạt.")
    
    except Exception as e:
        print(f"❌ Lỗi kiểm tra alerts: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔔 Bắt đầu kiểm tra alerts...")
    check_alerts()
    print("✅ Hoàn tất kiểm tra alerts.")
