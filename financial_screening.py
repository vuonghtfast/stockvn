# -*- coding: utf-8 -*-
"""
Financial Screening - Lọc cổ phiếu theo 10 chỉ tiêu tài chính
Hệ thống phân tích toàn diện: Profitability, Valuation, Growth, Financial Health, Shareholder Returns
"""

import pandas as pd
import gspread
import os
import sys
import argparse
from config import get_google_credentials
from sectors import get_sector, get_all_sectors, get_tickers_by_sector

def get_spreadsheet():
    """Kết nối Google Sheets"""
    try:
        creds = get_google_credentials()
        client = gspread.authorize(creds)
        
        spreadsheet_id = os.getenv("SPREADSHEET_ID")
        if spreadsheet_id:
            return client.open_by_key(spreadsheet_id)
        else:
            return client.open("stockdata")
    except Exception as e:
        print(f"[ERROR] Failed to connect to Google Sheets: {e}")
        return None

def calculate_all_metrics(ticker, spreadsheet):
    """Tính toán tất cả 10 chỉ tiêu tài chính cho 1 mã"""
    try:
        # Lấy dữ liệu từ sheets
        income_ws = spreadsheet.worksheet("income")
        balance_ws = spreadsheet.worksheet("balance")
        
        income_data = income_ws.get_all_records()
        balance_data = balance_ws.get_all_records()
        
        income_df = pd.DataFrame(income_data)
        balance_df = pd.DataFrame(balance_data)
        
        # Chuẩn hóa cột
        income_df.columns = income_df.columns.str.lower().str.replace(' ', '_')
        balance_df.columns = balance_df.columns.str.lower().str.replace(' ', '_')
        
        # Filter cho ticker
        ticker_income = income_df[income_df['ticker'] == ticker]
        ticker_balance = balance_df[balance_df['ticker'] == ticker]
        
        if ticker_income.empty or ticker_balance.empty:
            return None
        
        # Lấy dữ liệu mới nhất và trước đó
        latest_income = ticker_income.iloc[-1]
        latest_balance = ticker_balance.iloc[-1]
        
        prev_income = ticker_income.iloc[-2] if len(ticker_income) > 1 else latest_income
        
        # Chuẩn hóa cột
        def safe_numeric(value):
            return pd.to_numeric(value, errors='coerce') if value else 0
        
        # Lấy giá hiện tại (từ price sheet)
        try:
            price_ws = spreadsheet.worksheet("price")
            price_data = price_ws.get_all_records()
            price_df = pd.DataFrame(price_data)
            ticker_price = price_df[price_df['ticker'] == ticker]
            current_price = safe_numeric(ticker_price.iloc[-1]['close']) if not ticker_price.empty else 0
        except:
            current_price = 0
        
        # Tính toán metrics
        net_income = safe_numeric(latest_income.get('net_income', 0))
        revenue = safe_numeric(latest_income.get('revenue', 0))
        equity = safe_numeric(latest_balance.get('equity', 0))
        total_assets = safe_numeric(latest_balance.get('total_assets', 0))
        total_liabilities = safe_numeric(latest_balance.get('total_liabilities', 0))
        current_assets = safe_numeric(latest_balance.get('current_assets', 0))
        current_liabilities = safe_numeric(latest_balance.get('current_liabilities', 0))
        shares_outstanding = safe_numeric(latest_balance.get('shares_outstanding', 0))
        eps = safe_numeric(latest_income.get('eps', 0))
        
        prev_eps = safe_numeric(prev_income.get('eps', 0))
        prev_revenue = safe_numeric(prev_income.get('revenue', 0))
        
        # 1. Profitability
        roe = (net_income / equity * 100) if equity > 0 else 0
        roa = (net_income / total_assets * 100) if total_assets > 0 else 0
        profit_margin = (net_income / revenue * 100) if revenue > 0 else 0
        
        # 2. Valuation
        pe = (current_price / eps) if eps > 0 else None
        book_value = (equity / shares_outstanding) if shares_outstanding > 0 else 0
        pb = (current_price / book_value) if book_value > 0 else None
        market_cap = current_price * shares_outstanding if shares_outstanding > 0 else 0
        ps = (market_cap / revenue) if revenue > 0 else None
        
        # 3. Growth
        eps_growth = ((eps - prev_eps) / prev_eps * 100) if prev_eps > 0 else 0
        revenue_growth = ((revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0
        
        # 4. Financial Health
        debt_equity = (total_liabilities / equity) if equity > 0 else 0
        current_ratio = (current_assets / current_liabilities) if current_liabilities > 0 else 0
        
        # 5. Shareholder Returns (tạm thời để 0, cần dữ liệu cổ tức)
        dividend_yield = 0
        
        sector = get_sector(ticker)
        
        return {
            'ticker': ticker,
            'sector': sector,
            'roe': round(roe, 2),
            'roa': round(roa, 2),
            'profit_margin': round(profit_margin, 2),
            'pe': round(pe, 2) if pe else None,
            'pb': round(pb, 2) if pb else None,
            'ps': round(ps, 2) if ps else None,
            'eps_growth': round(eps_growth, 2),
            'revenue_growth': round(revenue_growth, 2),
            'debt_equity': round(debt_equity, 2),
            'current_ratio': round(current_ratio, 2),
            'dividend_yield': round(dividend_yield, 2)
        }
    except Exception as e:
        print(f"[ERROR] Failed to calculate metrics for {ticker}: {e}")
        return None

def get_industry_avg_pe(ticker):
    """Lấy P/E trung bình ngành"""
    sector = get_sector(ticker)
    
    # Giá trị P/E trung bình theo ngành
    industry_pe = {
        'Ngân hàng': 12, 'Bất động sản': 15, 'Thép': 10, 'Thực phẩm': 18,
        'Bán lẻ': 20, 'Dầu khí': 8, 'Điện': 12, 'Xây dựng': 10,
        'Chứng khoán': 15, 'Công nghệ': 22, 'Hàng không': 12,
        'Logistics': 14, 'Dược phẩm': 18, 'Cao su': 10, 'Thủy sản': 12,
        'Nông nghiệp': 10, 'Vận tải': 12, 'Khác': 15
    }
    return industry_pe.get(sector, 15)

def calculate_composite_score(metrics):
    """Tính điểm tổng hợp (0-100)"""
    score = 0
    
    # Profitability (30 points)
    if metrics['roe'] >= 20: score += 12
    elif metrics['roe'] >= 15: score += 8
    elif metrics['roe'] >= 10: score += 4
    
    if metrics['roa'] >= 10: score += 10
    elif metrics['roa'] >= 5: score += 6
    elif metrics['roa'] >= 3: score += 3
    
    if metrics['profit_margin'] >= 15: score += 8
    elif metrics['profit_margin'] >= 10: score += 5
    elif metrics['profit_margin'] >= 5: score += 2
    
    # Valuation (20 points)
    if metrics['pe']:
        industry_avg_pe = get_industry_avg_pe(metrics['ticker'])
        if metrics['pe'] < industry_avg_pe * 0.7: score += 10
        elif metrics['pe'] < industry_avg_pe: score += 6
        elif metrics['pe'] < industry_avg_pe * 1.2: score += 3
    
    if metrics['pb']:
        if metrics['pb'] < 1.5: score += 6
        elif metrics['pb'] < 2.5: score += 4
        elif metrics['pb'] < 3.5: score += 2
    
    if metrics['ps']:
        if metrics['ps'] < 1: score += 4
        elif metrics['ps'] < 2: score += 2
    
    # Growth (20 points)
    if metrics['eps_growth'] >= 20: score += 12
    elif metrics['eps_growth'] >= 15: score += 8
    elif metrics['eps_growth'] >= 10: score += 5
    
    if metrics['revenue_growth'] >= 20: score += 8
    elif metrics['revenue_growth'] >= 10: score += 5
    elif metrics['revenue_growth'] >= 5: score += 2
    
    # Financial Health (20 points)
    if metrics['debt_equity'] < 0.5: score += 12
    elif metrics['debt_equity'] < 1.0: score += 8
    elif metrics['debt_equity'] < 1.5: score += 4
    
    if metrics['current_ratio'] >= 2.0: score += 8
    elif metrics['current_ratio'] >= 1.5: score += 5
    elif metrics['current_ratio'] >= 1.0: score += 2
    
    # Shareholder Returns (10 points)
    if metrics['dividend_yield'] >= 5: score += 10
    elif metrics['dividend_yield'] >= 3: score += 6
    elif metrics['dividend_yield'] >= 2: score += 3
    
    return score

def screen_by_criteria(
    min_roe=None, min_roa=None, min_profit_margin=None,
    max_pe=None, max_pb=None, max_ps=None,
    min_eps_growth=None, min_revenue_growth=None,
    max_debt_equity=None, min_current_ratio=None,
    min_dividend_yield=None,
    sectors_filter=None, tickers_filter=None
):
    """Lọc cổ phiếu theo 10 tiêu chí tài chính"""
    spreadsheet = get_spreadsheet()
    if not spreadsheet:
        return pd.DataFrame()
    
    # Lấy danh sách tickers cần lọc
    if tickers_filter:
        ticker_list = tickers_filter
    elif sectors_filter:
        ticker_list = []
        for sector in sectors_filter:
            ticker_list.extend(get_tickers_by_sector(sector))
    else:
        # Lấy tất cả tickers từ sheet
        try:
            tickers_ws = spreadsheet.worksheet("tickers")
            ticker_list = tickers_ws.col_values(1)[1:]  # Skip header
        except:
            ticker_list = []
    
    print(f"\n[SCREEN] Screening {len(ticker_list)} tickers...")
    
    results = []
    for idx, ticker in enumerate(ticker_list, 1):
        print(f"[{idx}/{len(ticker_list)}] {ticker}...", end=" ", flush=True)
        
        metrics = calculate_all_metrics(ticker, spreadsheet)
        if not metrics:
            print("No data")
            continue
        
        # Apply filters
        if min_roe and metrics['roe'] < min_roe: 
            print(f"ROE {metrics['roe']:.1f} < {min_roe}")
            continue
        if min_roa and metrics['roa'] < min_roa: 
            print(f"ROA {metrics['roa']:.1f} < {min_roa}")
            continue
        if min_profit_margin and metrics['profit_margin'] < min_profit_margin: 
            print(f"Margin {metrics['profit_margin']:.1f} < {min_profit_margin}")
            continue
        
        if max_pe and metrics['pe'] and metrics['pe'] > max_pe: 
            print(f"P/E {metrics['pe']:.1f} > {max_pe}")
            continue
        if max_pb and metrics['pb'] and metrics['pb'] > max_pb: 
            print(f"P/B {metrics['pb']:.2f} > {max_pb}")
            continue
        if max_ps and metrics['ps'] and metrics['ps'] > max_ps: 
            print(f"P/S {metrics['ps']:.2f} > {max_ps}")
            continue
        
        if min_eps_growth and metrics['eps_growth'] < min_eps_growth: 
            print(f"EPS growth {metrics['eps_growth']:.1f} < {min_eps_growth}")
            continue
        if min_revenue_growth and metrics['revenue_growth'] < min_revenue_growth: 
            print(f"Revenue growth {metrics['revenue_growth']:.1f} < {min_revenue_growth}")
            continue
        
        if max_debt_equity and metrics['debt_equity'] > max_debt_equity: 
            print(f"D/E {metrics['debt_equity']:.2f} > {max_debt_equity}")
            continue
        if min_current_ratio and metrics['current_ratio'] < min_current_ratio: 
            print(f"Current ratio {metrics['current_ratio']:.2f} < {min_current_ratio}")
            continue
        
        if min_dividend_yield and metrics['dividend_yield'] < min_dividend_yield: 
            print(f"Dividend {metrics['dividend_yield']:.1f} < {min_dividend_yield}")
            continue
        
        # Calculate composite score
        metrics['composite_score'] = calculate_composite_score(metrics)
        results.append(metrics)
        print(f"✓ Score: {metrics['composite_score']}")
    
    if results:
        df = pd.DataFrame(results)
        df = df.sort_values('composite_score', ascending=False)
        
        print(f"\n[RESULT] Found {len(df)} stocks matching criteria")
        print("\nTop 10:")
        print(df.head(10)[['ticker', 'sector', 'composite_score', 'roe', 'roa', 'pe', 'pb']].to_string(index=False))
        
        return df
    else:
        print("\n[RESULT] No stocks match the criteria")
        return pd.DataFrame()

# ===== CLI Interface =====
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Lọc cổ phiếu theo tiêu chí tài chính')
    
    # Profitability
    parser.add_argument('--min-roe', type=float, help='ROE tối thiểu (%)')
    parser.add_argument('--min-roa', type=float, help='ROA tối thiểu (%)')
    parser.add_argument('--min-margin', type=float, help='Biên lợi nhuận tối thiểu (%)')
    
    # Valuation
    parser.add_argument('--max-pe', type=float, help='P/E tối đa')
    parser.add_argument('--max-pb', type=float, help='P/B tối đa')
    parser.add_argument('--max-ps', type=float, help='P/S tối đa')
    
    # Growth
    parser.add_argument('--min-eps-growth', type=float, help='Tăng trưởng EPS tối thiểu (%)')
    parser.add_argument('--min-revenue-growth', type=float, help='Tăng trưởng doanh thu tối thiểu (%)')
    
    # Financial Health
    parser.add_argument('--max-debt', type=float, help='Nợ/Vốn tối đa')
    parser.add_argument('--min-current-ratio', type=float, help='Tỷ lệ thanh khoản tối thiểu')
    
    # Shareholder Returns
    parser.add_argument('--min-dividend', type=float, help='Tỷ suất cổ tức tối thiểu (%)')
    
    # Filters
    parser.add_argument('--sectors', type=str, help='Danh sách ngành (phân cách bằng dấu phẩy)')
    parser.add_argument('--tickers', type=str, help='Danh sách mã (phân cách bằng dấu phẩy)')
    
    args = parser.parse_args()
    
    # Parse sectors and tickers
    sectors_filter = args.sectors.split(',') if args.sectors else None
    tickers_filter = args.tickers.split(',') if args.tickers else None
    
    # Run screening
    results = screen_by_criteria(
        min_roe=args.min_roe,
        min_roa=args.min_roa,
        min_profit_margin=args.min_margin,
        max_pe=args.max_pe,
        max_pb=args.max_pb,
        max_ps=args.max_ps,
        min_eps_growth=args.min_eps_growth,
        min_revenue_growth=args.min_revenue_growth,
        max_debt_equity=args.max_debt,
        min_current_ratio=args.min_current_ratio,
        min_dividend_yield=args.min_dividend,
        sectors_filter=sectors_filter,
        tickers_filter=tickers_filter
    )
    
    # Save to CSV
    if not results.empty:
        filename = f"screening_results_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
        results.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n✅ Saved results to {filename}")
