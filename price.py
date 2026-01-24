import pandas as pd
from vnstock import Vnstock
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import os
import sys
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ===== 1. Kết nối Google Sheets =====
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

creds = get_google_credentials()
client = gspread.authorize(creds)

# Open spreadsheet by ID (from env) or name
spreadsheet_id = os.getenv("SPREADSHEET_ID")
if spreadsheet_id:
    spreadsheet = client.open_by_key(spreadsheet_id)
else:
    spreadsheet = client.open("stockdata")
tickers_sheet = spreadsheet.worksheet("tickers")
tickers = tickers_sheet.col_values(1)[1:]
data_sheet = spreadsheet.worksheet("data")

# ===== 2. Ngày chạy =====
today = datetime.today().strftime("%Y-%m-%d")
yesterday = (datetime.today() - timedelta(days=2)).strftime("%Y-%m-%d")  # để phòng trường hợp cần khoảng rộng hơn

# ===== 3. Lấy dữ liệu từ vnstock =====
vs = Vnstock()
all_data = []

for ticker in tickers:
    df = vs.stock(symbol=ticker, source='TCBS').quote.history(
        start=yesterday,
        end=today,
        interval='1D'
    )
    if not df.empty and today in df['time'].astype(str).values:
        today_row = df[df['time'].astype(str) == today].copy()
        today_row["ticker"] = ticker
        all_data.append(today_row)
        print(f"✅ {ticker}: lấy dữ liệu ngày {today}")
    else:
        print(f"⚠️ Không có dữ liệu {ticker} cho ngày {today}")

# ===== 4. Ghi vào Google Sheets (nếu có dữ liệu) =====
if all_data:
    final_df = pd.concat(all_data)
    final_df = final_df.astype(str)
    data_sheet.clear()
    data_sheet.update([final_df.columns.values.tolist()] + final_df.values.tolist())
    print(f"🎉 Đã cập nhật dữ liệu ngày {today} cho {len(all_data)} mã")
else:
    print(f"❌ Không có dữ liệu nào cho ngày {today}")
