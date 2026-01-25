# -*- coding: utf-8 -*-
"""
Stock Screener - Tìm Mã Chứng Khoán Đang Hot
Quét toàn bộ thị trường VN và tìm cơ hội đầu tư
"""

import pandas as pd
from vnstock import Vnstock
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import os
import sys
import json
from dotenv import load_dotenv
from config import get_google_credentials

# Load environment variables
load_dotenv()

def get_all_stock_symbols():
    """
    Lấy danh sách TẤT CẢ mã chứng khoán trên sàn HOSE, HNX, UPCOM
    """
    try:
        vs = Vnstock()
        
        # Lấy danh sách từ các sàn
        all_stocks = []
        
        # HOSE (Sàn HOSE - cổ phiếu lớn)
        try:
            hose = vs.stock(symbol='VNM', source='TCBS').listing.all_symbols(exchange='HOSE')
            if not hose.empty:
                all_stocks.append(hose)
                print(f"✅ HOSE: {len(hose)} mã")
        except Exception as e:
            print(f"⚠️ Lỗi lấy HOSE: {e}")
        
        # HNX (Sàn Hà Nội)
        try:
            hnx = vs.stock(symbol='VNM', source='TCBS').listing.all_symbols(exchange='HNX')
            if not hnx.empty:
                all_stocks.append(hnx)
                print(f"✅ HNX: {len(hnx)} mã")
        except Exception as e:
            print(f"⚠️ Lỗi lấy HNX: {e}")
        
        # UPCOM (Sàn OTC)
        try:
            upcom = vs.stock(symbol='VNM', source='TCBS').listing.all_symbols(exchange='UPCOM')
            if not upcom.empty:
                all_stocks.append(upcom)
                print(f"✅ UPCOM: {len(upcom)} mã")
        except Exception as e:
            print(f"⚠️ Lỗi lấy UPCOM: {e}")
        
        if all_stocks:
            combined = pd.concat(all_stocks, ignore_index=True)
            # Lấy cột ticker/symbol
            if 'ticker' in combined.columns:
                symbols = combined['ticker'].unique().tolist()
            elif 'symbol' in combined.columns:
                symbols = combined['symbol'].unique().tolist()
            else:
                symbols = combined.iloc[:, 0].unique().tolist()
            
            print(f"\n🎯 Tổng cộng: {len(symbols)} mã chứng khoán")
            return symbols
        else:
            print("⚠️ Không lấy được danh sách mã. Dùng danh sách mặc định.")
            return get_default_symbols()
    
    except Exception as e:
        print(f"❌ Lỗi lấy danh sách mã: {e}")
        return get_default_symbols()

def get_default_symbols():
    """Danh sách mã phổ biến nếu không lấy được từ API"""
    return [
        # VN30 - Top 30 cổ phiếu vốn hóa lớn nhất
        'VNM', 'VIC', 'VHM', 'VCB', 'GAS', 'MSN', 'BID', 'CTG', 'HPG', 'TCB',
        'MBB', 'VPB', 'VRE', 'SAB', 'PLX', 'VJC', 'MWG', 'FPT', 'POW', 'SSI',
        'HDB', 'TPB', 'ACB', 'STB', 'GVR', 'PDR', 'KDH', 'NVL', 'BCM', 'VHC',
        # Thêm một số mã khác
        'HNG', 'DGC', 'DXG', 'REE', 'GMD', 'PNJ', 'VCI', 'DCM', 'DPM', 'NT2'
    ]

def screen_hot_stocks(symbols, lookback_days=30, min_volume_spike=2.0, min_price_change=5.0):
    """
    Quét và tìm mã đang hot dựa trên:
    1. Volume spike (khối lượng tăng đột biến)
    2. Price momentum (giá tăng mạnh)
    3. Breakout patterns (vượt đỉnh cũ)
    
    Args:
        symbols: Danh sách mã cần quét
        lookback_days: Số ngày lịch sử để phân tích
        min_volume_spike: Ngưỡng tăng khối lượng (2.0 = tăng gấp đôi)
        min_price_change: % thay đổi giá tối thiểu
    
    Returns:
        DataFrame chứa các mã hot
    """
    hot_stocks = []
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)
    
    vs = Vnstock()
    
    print(f"\n🔍 Bắt đầu quét {len(symbols)} mã...")
    print(f"📅 Khoảng thời gian: {start_date.strftime('%Y-%m-%d')} đến {end_date.strftime('%Y-%m-%d')}")
    print(f"⚙️ Tiêu chí: Volume spike >{min_volume_spike}x, Price change >{min_price_change}%\n")
    
    for idx, symbol in enumerate(symbols, 1):
        try:
            # Progress indicator
            if idx % 10 == 0:
                print(f"Progress: {idx}/{len(symbols)} ({idx/len(symbols)*100:.1f}%)")
            
            # Lấy dữ liệu
            df = vs.stock(symbol=symbol, source='TCBS').quote.history(
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d'),
                interval='1D'
            )
            
            if df.empty or len(df) < 10:
                continue
            
            # Tính toán metrics
            latest = df.iloc[-1]
            prev_week = df.iloc[-5] if len(df) >= 5 else df.iloc[0]
            
            # 1. Volume Spike
            avg_volume = df['volume'].iloc[:-1].mean()  # Trung bình không tính ngày hôm nay
            current_volume = latest['volume']
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
            
            # 2. Price Change
            price_change_pct = ((latest['close'] - prev_week['close']) / prev_week['close']) * 100
            
            # 3. Breakout (giá vượt đỉnh 20 ngày)
            high_20d = df['high'].iloc[-20:].max() if len(df) >= 20 else df['high'].max()
            is_breakout = latest['close'] >= high_20d * 0.98  # Gần đỉnh hoặc vượt đỉnh
            
            # 4. RSI (momentum indicator)
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1] if not rsi.empty else 50
            
            # Điều kiện lọc
            if volume_ratio >= min_volume_spike or abs(price_change_pct) >= min_price_change:
                hot_stocks.append({
                    'ticker': symbol,
                    'close': latest['close'],
                    'price_change_pct': price_change_pct,
                    'volume': current_volume,
                    'avg_volume': avg_volume,
                    'volume_spike': volume_ratio,
                    'is_breakout': is_breakout,
                    'rsi': current_rsi,
                    'high_20d': high_20d,
                    'signal': get_signal(price_change_pct, volume_ratio, is_breakout, current_rsi)
                })
                
                print(f"🔥 {symbol}: Price {price_change_pct:+.2f}%, Volume {volume_ratio:.2f}x, RSI {current_rsi:.1f}")
        
        except Exception as e:
            # Bỏ qua lỗi để tiếp tục quét
            pass
    
    if hot_stocks:
        result_df = pd.DataFrame(hot_stocks)
        result_df = result_df.sort_values('volume_spike', ascending=False)
        return result_df
    else:
        return pd.DataFrame()

def get_signal(price_change, volume_ratio, is_breakout, rsi):
    """Tạo tín hiệu mua/bán dựa trên các chỉ số"""
    score = 0
    
    # Price momentum
    if price_change > 10:
        score += 2
    elif price_change > 5:
        score += 1
    elif price_change < -5:
        score -= 1
    
    # Volume
    if volume_ratio > 3:
        score += 2
    elif volume_ratio > 2:
        score += 1
    
    # Breakout
    if is_breakout:
        score += 1
    
    # RSI
    if rsi < 30:
        score += 1  # Oversold - cơ hội mua
    elif rsi > 70:
        score -= 1  # Overbought - rủi ro cao
    
    # Tín hiệu
    if score >= 4:
        return "🚀 MUA MẠNH"
    elif score >= 2:
        return "✅ MUA"
    elif score <= -2:
        return "❌ BÁN"
    else:
        return "⚖️ THEO DÕI"

def save_to_sheets(df):
    """Lưu kết quả vào Google Sheets"""
    try:
        creds = get_google_credentials()
        client = gspread.authorize(creds)
        
        spreadsheet_id = os.getenv("SPREADSHEET_ID")
        if spreadsheet_id:
            spreadsheet = client.open_by_key(spreadsheet_id)
        else:
            spreadsheet = client.open("stockdata")
        
        # Tạo hoặc cập nhật sheet
        try:
            ws = spreadsheet.worksheet("hot_stocks")
        except gspread.WorksheetNotFound:
            ws = spreadsheet.add_worksheet(title="hot_stocks", rows="1000", cols="15")
        
        # Thêm timestamp
        df['scan_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Ghi dữ liệu
        ws.clear()
        ws.update([df.columns.values.tolist()] + df.astype(str).values.tolist())
        
        print(f"\n✅ Đã lưu {len(df)} mã hot vào Google Sheets (sheet: hot_stocks)")
    
    except Exception as e:
        print(f"⚠️ Lỗi lưu vào Sheets: {e}")

def print_summary(df):
    """In báo cáo tóm tắt"""
    if df.empty:
        print("\n❌ Không tìm thấy mã nào đáng chú ý.")
        return
    
    print("\n" + "="*80)
    print("📊 BÁO CÁO MÃ CHỨNG KHOÁN HOT")
    print("="*80)
    
    print(f"\n🔥 Tổng số mã hot: {len(df)}")
    
    # Top volume spike
    print("\n📈 TOP 10 KHỐI LƯỢNG TĂNG MẠNH:")
    top_volume = df.nlargest(10, 'volume_spike')[['ticker', 'close', 'volume_spike', 'price_change_pct', 'signal']]
    print(top_volume.to_string(index=False))
    
    # Top price gainers
    print("\n💰 TOP 10 TĂNG GIÁ MẠNH:")
    top_price = df.nlargest(10, 'price_change_pct')[['ticker', 'close', 'price_change_pct', 'volume_spike', 'signal']]
    print(top_price.to_string(index=False))
    
    # Breakout stocks
    breakouts = df[df['is_breakout'] == True]
    if not breakouts.empty:
        print(f"\n🚀 CÁC MÃ BREAKOUT ({len(breakouts)} mã):")
        print(breakouts[['ticker', 'close', 'high_20d', 'volume_spike', 'signal']].to_string(index=False))
    
    # Strong buy signals
    strong_buy = df[df['signal'] == "🚀 MUA MẠNH"]
    if not strong_buy.empty:
        print(f"\n⭐ TÍN HIỆU MUA MẠNH ({len(strong_buy)} mã):")
        print(strong_buy[['ticker', 'close', 'price_change_pct', 'volume_spike', 'rsi']].to_string(index=False))
    
    print("\n" + "="*80)

if __name__ == "__main__":
    print("🚀 STOCK SCREENER - TÌM MÃ CHỨNG KHOÁN HOT")
    print("="*80)
    
    # Lựa chọn: quét toàn bộ hoặc chỉ VN30
    scan_all = input("\nQuét toàn bộ thị trường? (y/n, mặc định: n): ").strip().lower()
    
    if scan_all == 'y':
        print("\n📡 Đang lấy danh sách TẤT CẢ mã chứng khoán...")
        symbols = get_all_stock_symbols()
    else:
        print("\n📡 Quét VN30 và các mã phổ biến...")
        symbols = get_default_symbols()
    
    # Tùy chỉnh tiêu chí
    print("\n⚙️ Cấu hình tiêu chí lọc:")
    try:
        lookback = int(input("Số ngày lịch sử (mặc định: 30): ") or "30")
        volume_spike = float(input("Ngưỡng volume spike (mặc định: 2.0x): ") or "2.0")
        price_change = float(input("% thay đổi giá tối thiểu (mặc định: 5%): ") or "5.0")
    except:
        lookback, volume_spike, price_change = 30, 2.0, 5.0
    
    # Quét thị trường
    hot_df = screen_hot_stocks(
        symbols=symbols,
        lookback_days=lookback,
        min_volume_spike=volume_spike,
        min_price_change=price_change
    )
    
    # Hiển thị kết quả
    print_summary(hot_df)
    
    # Lưu vào Sheets
    if not hot_df.empty:
        save_choice = input("\nLưu kết quả vào Google Sheets? (y/n): ").strip().lower()
        if save_choice == 'y':
            save_to_sheets(hot_df)
        
        # Export CSV
        csv_choice = input("Xuất ra file CSV? (y/n): ").strip().lower()
        if csv_choice == 'y':
            filename = f"hot_stocks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            hot_df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"✅ Đã xuất ra file: {filename}")
    
    print("\n✅ Hoàn tất quét thị trường!")
