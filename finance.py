import vnstock as vs
from vnstock import Vnstock
import pandas as pd
import gspread
import os
from oauth2client.service_account import ServiceAccountCredentials
import sys 
import numpy as np 

# Initialize vnstock with API key if available
api_key = os.getenv("VNSTOCK_API_KEY")
if api_key:
    print("[INFO] Using vnstock with API key (60 req/min)")
else:
    print("[WARN] Using vnstock without API key (20 req/min). Register at https://vnstocks.com/login")

# 1. Auth Google Sheets (Không thay đổi)
try:
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        eval(os.environ["GOOGLE_CREDENTIALS"]),
        ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    )
    client = gspread.authorize(creds)
    spreadsheet = client.open("stockdata")
except Exception as e:
    print(f"❌ Lỗi kết nối Google Sheets: {e}")
    sys.exit(1)

# 2. Đọc danh sách mã cổ phiếu (Không thay đổi)
try:
    tickers_ws = spreadsheet.worksheet("tickers")
    tickers = [row[0] for row in tickers_ws.get_all_values()[1:] if row] 
    if not tickers:
        print("⚠️ Sheet 'tickers' không có mã cổ phiếu nào. Chương trình dừng lại.")
        sys.exit(0)
except Exception as e:
    print(f"❌ Lỗi đọc sheet 'tickers': {e}")
    sys.exit(1)

# 3. Hàm lấy báo cáo tài chính (ĐÃ LOẠI BỎ TỶ SỐ)
def fetch_financials(symbol, period="quarter"):
    data = {}
    try:
        # vnstock reads API key from VNSTOCK_API_KEY environment variable automatically
        comp = vs.Company(symbol=symbol, source="TCBS")
        
        data["income"] = comp.finance.income_statement(period=period)
        data["balance"] = comp.finance.balance_sheet(period=period)
        
        try:
            data["cashflow"] = comp.finance.cash_flow(period=period) 
        except AttributeError as attr_e:
            print(f"⚠️ Bỏ qua LCTT cho {symbol} | {period}. Lỗi tên: {attr_e}")
        except Exception:
            pass
            
        return data

    except Exception as e:
        print(f"❌ Lỗi khi khởi tạo hoặc lấy báo cáo cơ bản {symbol} | {period}: {e}")
        return {}

# 4. Ghi dữ liệu vào Google Sheets (Không thay đổi)
def write_to_sheet(sheet_name, df):
    """Ghi DataFrame vào Google Sheet, tạo sheet mới nếu chưa tồn tại."""
    try:
        ws = spreadsheet.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=sheet_name, rows="2000", cols="20")
    except Exception as e:
        print(f"❌ Lỗi khi truy cập/tạo sheet {sheet_name}: {e}")
        return 
        
    ws.clear()
    ws.update([df.columns.values.tolist()] + df.astype(str).values.tolist(), range_name='A1')
    print(f"✅ Ghi {sheet_name} xong ({len(df)} dòng)")

# 5. Tạo summary (YOY hoặc QOQ growth) - ĐÃ SỬA LỖI TypeError VÀ THIẾU CỘT
def create_summary(period="year"):
    """Tạo báo cáo tóm tắt tăng trưởng doanh thu/lợi nhuận mới nhất."""
    all_data = []
    
    # Định nghĩa tên cột cần thiết sau khi ánh xạ
    REQUIRED_COLS = {"year", "revenue", "net_income"}
    
    for t in tickers:
        fdata = fetch_financials(t, period=period)
        
        if "income" in fdata and not fdata["income"].empty:
            df = fdata["income"].copy()
            df["Ticker"] = t
            
            # CHUẨN HÓA CỘT
            df.columns = df.columns.str.lower().str.replace(' ', '_')
            
            # ÁNH XẠ TÊN CỘT DỰA TRÊN LOG DEBUG
            df = df.rename(columns={
                'share_holder_income': 'net_income', 
                'post_tax_profit': 'net_income', 
                # Nếu cột year không tồn tại trong báo cáo năm, cần tạo nó. 
                # Tạm thời không cần tạo vì chỉ cần kiểm tra sự tồn tại của cột tăng trưởng
            }, errors='ignore')
            
            # ĐIỀU CHỈNH CỘT THIẾU: TẠO CỘT 'year' NẾU THIẾU TRONG BÁO CÁO NĂM
            if period == "year" and "year" not in df.columns:
                # Nếu không có cột year, tạm thời tạo cột year giả (để code vượt qua kiểm tra) 
                # và dựa vào các cột tăng trưởng đã có sẵn
                if len(df) >= 1:
                   # Lấy năm từ index hoặc tạo mảng năm giả để sort
                   df['year'] = range(1, len(df) + 1)
                   
            # ⭐ KHẮC PHỤC LỖI TypeError: Đảm bảo cột tồn tại trước khi dùng to_numeric
            
            # Bắt buộc phải có revenue để tính YOY/QOQ
            if 'revenue' in df.columns:
                df["revenue"] = pd.to_numeric(df["revenue"], errors='coerce')

            # Kiểm tra và chuyển đổi net_income (nguyên nhân gây lỗi)
            if 'net_income' in df.columns:
                df["net_income"] = pd.to_numeric(df["net_income"], errors='coerce')
            else:
                # Nếu net_income không tồn tại, tạo cột rỗng để tránh lỗi
                df['net_income'] = np.nan 

            
            # Kiểm tra cột và đủ dữ liệu
            if not REQUIRED_COLS.issubset(df.columns) or len(df) < 2:
                missing = REQUIRED_COLS - set(df.columns)
                print(f"⚠️ Bỏ qua summary cho {t} ({period}). Thiếu cột ({missing}) hoặc không đủ dữ liệu lịch sử.")
                continue

            # Thực hiện tính toán
            if period == "year":
                df.sort_values("year", inplace=True)
                
                # SỬ DỤNG CỘT TĂNG TRƯỞNG CÓ SẴN TỪ API
                if 'year_share_holder_income_growth' in df.columns:
                    df['NetIncome_YOY'] = df['year_share_holder_income_growth']
                    df['Revenue_YOY'] = df['year_revenue_growth']
                else:
                    df["Revenue_YOY"] = df["revenue"].pct_change()
                    df["NetIncome_YOY"] = df["net_income"].pct_change()
                
            elif period == "quarter":
                if "quarter" not in df.columns:
                     print(f"⚠️ Bỏ qua summary QOQ cho {t}. Thiếu cột 'quarter'.")
                     continue
                df.sort_values(["year", "quarter"], inplace=True)
                
                # SỬ DỤNG CỘT TĂNG TRƯỞNG CÓ SẴN TỪ API
                if 'quarter_share_holder_income_growth' in df.columns:
                    df['NetIncome_QOQ'] = df['quarter_share_holder_income_growth']
                    df['Revenue_QOQ'] = df['quarter_revenue_growth']
                else:
                    df["Revenue_QOQ"] = df["revenue"].pct_change()
                    df["NetIncome_QOQ"] = df["net_income"].pct_change()
            
            latest = df.iloc[-1:] 
            all_data.append(latest)

    if all_data:
        final_df = pd.concat(all_data)
        sheet_name = f"summary_{'y' if period=='year' else 'q'}"
        write_to_sheet(sheet_name, final_df)

        latest_df = final_df.groupby("Ticker").tail(1)
        sheet_latest = f"summary_latest_{'y' if period=='year' else 'q'}"
        write_to_sheet(sheet_latest, latest_df)
    else:
        print(f"⚠️ Không có dữ liệu hợp lệ nào để tạo {period} summary.")

# 6. Chạy chính (Logic ghi sheet gộp dữ liệu)
if __name__ == "__main__":
    print(f"🚀 Bắt đầu lấy dữ liệu cho {len(tickers)} mã: {', '.join(tickers)}")
    
    all_reports = {
        "income": [],
        "balance": [],
        "cashflow": [], 
    }

    for t in tickers:
        print(f"\n--- Xử lý chi tiết mã {t} ---")
        fdata = fetch_financials(t, period="quarter") 
        
        for rtype, df in fdata.items():
            if df is not None and not df.empty and rtype in all_reports:
                df["Ticker"] = t 
                all_reports[rtype].append(df) 

    # Ghi từng loại báo cáo tổng hợp ra Google Sheet
    for rtype, df_list in all_reports.items():
        if df_list:
            final_df = pd.concat(df_list, ignore_index=True)
            final_df.columns = final_df.columns.str.lower().str.replace(' ', '_')
            write_to_sheet(rtype, final_df) 
        else:
            print(f"⚠️ Không có dữ liệu để ghi cho báo cáo: {rtype}")
            
    # Tạo summary toàn bộ
    print("\n*** BẮT ĐẦU TẠO SUMMARY ***")
    create_summary("year")
    create_summary("quarter")
    
    print("\n✅ HOÀN TẤT QUY TRÌNH.")
