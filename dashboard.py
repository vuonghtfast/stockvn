# -*- coding: utf-8 -*-
"""
Stock Analysis Dashboard
Phân tích chứng khoán Việt Nam
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
from datetime import datetime, timedelta
from vnstock import Vnstock
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
from config import get_google_credentials, get_config, update_config
import time
import warnings
from sectors import get_sector, get_all_sectors
from financial_screening import calculate_all_metrics, screen_by_criteria, calculate_composite_score
from watchlist import add_to_watchlist, get_watchlist, update_watchlist_metrics
from dashboard_tabs import render_money_flow_tab, render_financial_screening_tab, render_watchlist_tab

# Suppress Streamlit secrets warning for local development
warnings.filterwarnings('ignore', category=UserWarning, module='streamlit')

# Page config
st.set_page_config(
    page_title="Stock Analysis Dashboard",
    page_icon="📈",
    layout="wide"
)

# Cached data fetching function with TTL (Time To Live)
@st.cache_data(ttl=600)  # Cache for 10 minutes
def fetch_stock_data(symbol, start_date, end_date):
    """Fetch stock data from Google Sheets (pre-loaded by GitHub Actions)"""
    try:
        spreadsheet = get_spreadsheet()
        ws = spreadsheet.worksheet("price")
        
        # Get all data
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        
        if df.empty:
            st.warning(f"⚠️ Không có dữ liệu giá trong Google Sheets")
            return pd.DataFrame()
        
        # Filter by ticker and date range
        df = df[df['ticker'] == symbol].copy()
        
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
            df = df.sort_values('date')
            df.set_index('date', inplace=True)
        
        # Ensure numeric columns
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    
    except Exception as e:
        st.error("❌ Lỗi đọc dữ liệu: ")
        return pd.DataFrame()

@st.cache_data(ttl=3600)  # Finance data is daily, cache for 1 hour
def fetch_financial_sheet(sheet_name):
    """Fetch financial data from a specific sheet"""
    try:
        spreadsheet = get_spreadsheet()
        ws = spreadsheet.worksheet(sheet_name)
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        
        if df.empty:
            st.warning(f"⚠️ Sheet '{sheet_name}' không có dữ liệu")
        
        return df
    except Exception as e:
        st.error(f"❌ Lỗi đọc sheet '{sheet_name}': ")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def fetch_ticker_list():
    """Fetch list of tickers from watchlist_flow sheet"""
    try:
        spreadsheet = get_spreadsheet()
        ws = spreadsheet.worksheet("watchlist_flow")
        data = ws.get_all_records()
        
        if data:
            df = pd.DataFrame(data)
            if 'ticker' in df.columns:
                tickers = df['ticker'].dropna().unique().tolist()
                tickers = [t.strip().upper() for t in tickers if t.strip()]
                
                return pd.DataFrame({
                    'ticker': tickers,
                    'sector': [get_sector(t) for t in tickers]
                })
        
        # Fallback if no data
        default_tickers = ["VNM", "HPG", "VIC"]
        return pd.DataFrame({
            'ticker': default_tickers,
            'sector': [get_sector(t) for t in default_tickers]
        })
        
    except Exception as e:
        st.error("⚠️ Lỗi đọc danh sách mã từ watchlist_flow")
        default_tickers = ["VNM", "HPG", "VIC"]
        return pd.DataFrame({
            'ticker': default_tickers,
            'sector': [get_sector(t) for t in default_tickers]
        })

def calculate_financial_metrics(symbol):
    """Calculate key financial metrics for a stock"""
    metrics = {}
    
    try:
        # Fetch financial data
        income_df = fetch_financial_sheet("income")
        balance_df = fetch_financial_sheet("balance")
        
        # Normalize column names (lowercase, replace spaces with underscores)
        if not income_df.empty:
            income_df.columns = income_df.columns.str.lower().str.replace(' ', '_')
        if not balance_df.empty:
            balance_df.columns = balance_df.columns.str.lower().str.replace(' ', '_')
        
        if not income_df.empty:
            ticker_income = income_df[income_df['ticker'].astype(str).str.upper() == symbol]
            
            if not ticker_income.empty:
                latest_income = ticker_income.iloc[-1]
                
                # Convert numeric columns
                for col in ['revenue', 'net_income', 'share_holder_income', 'post_tax_profit']:
                    if col in latest_income:
                        try:
                            latest_income[col] = pd.to_numeric(latest_income[col], errors='coerce')
                        except:
                            pass
                
                # Handle different column names for net income
                net_income = 0
                if 'net_income' in latest_income and pd.notna(latest_income['net_income']):
                    net_income = latest_income['net_income']
                elif 'share_holder_income' in latest_income and pd.notna(latest_income['share_holder_income']):
                    net_income = latest_income['share_holder_income']
                elif 'post_tax_profit' in latest_income and pd.notna(latest_income['post_tax_profit']):
                    net_income = latest_income['post_tax_profit']
                
                revenue = latest_income.get('revenue', 0)
                if pd.isna(revenue):
                    revenue = 0
                
                # Get current price for PE and PB
                end_date = datetime.now()
                start_date = end_date - timedelta(days=7)
                price_df = fetch_stock_data(symbol, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
                current_price = 0
                if not price_df.empty:
                    current_price = price_df.iloc[-1]['close']
                
                if not balance_df.empty:
                    ticker_balance = balance_df[balance_df['ticker'].astype(str).str.upper() == symbol]
                    
                    if not ticker_balance.empty:
                        latest_balance = ticker_balance.iloc[-1]
                        
                        # Convert numeric columns
                        for col in ['equity', 'total_assets', 'total_liabilities', 'owner_capital', 'share_outstanding']:
                            if col in latest_balance:
                                try:
                                    latest_balance[col] = pd.to_numeric(latest_balance[col], errors='coerce')
                                except:
                                    pass
                        
                        # Handle different column names for equity
                        equity = 0
                        if 'equity' in latest_balance and pd.notna(latest_balance['equity']):
                            equity = latest_balance['equity']
                        elif 'owner_capital' in latest_balance and pd.notna(latest_balance['owner_capital']):
                            equity = latest_balance['owner_capital']
                        
                        total_assets = latest_balance.get('total_assets', 0)
                        if pd.isna(total_assets):
                            total_assets = 0
                            
                        total_liabilities = latest_balance.get('total_liabilities', 0)
                        if pd.isna(total_liabilities):
                            total_liabilities = 0
                        
                        # Shares outstanding (try to get from balance sheet or estimate)
                        shares_outstanding = latest_balance.get('share_outstanding', 0)
                        if pd.isna(shares_outstanding) or shares_outstanding == 0:
                            # Estimate from equity and typical book value
                            if equity > 0 and current_price > 0:
                                shares_outstanding = equity / (current_price / 1.5)  # Rough estimate
                        
                        # Calculate metrics
                        if equity and equity != 0:
                            metrics['ROE'] = (float(net_income) / float(equity)) * 100
                            metrics['debt_to_equity'] = float(total_liabilities) / float(equity)
                            
                            # Book Value per Share
                            if shares_outstanding and shares_outstanding > 0:
                                book_value_per_share = float(equity) / float(shares_outstanding)
                                if current_price > 0:
                                    metrics['PB'] = float(current_price) / book_value_per_share
                        
                        if total_assets and total_assets != 0:
                            metrics['ROA'] = (float(net_income) / float(total_assets)) * 100
                        
                        if revenue and revenue != 0:
                            metrics['profit_margin'] = (float(net_income) / float(revenue)) * 100
                        
                        # EPS and PE
                        if shares_outstanding and shares_outstanding > 0:
                            metrics['EPS'] = float(net_income) / float(shares_outstanding)
                            if current_price > 0 and metrics['EPS'] > 0:
                                metrics['PE'] = float(current_price) / metrics['EPS']
    
    except Exception as e:
        st.warning("⚠️ Lỗi tính toán metrics: ")
        import traceback
        st.text(traceback.format_exc())
    
    return metrics

@st.cache_resource
def get_gspread_client():
    """Get authenticated gspread client (cached)"""
    creds = get_google_credentials()
    return gspread.authorize(creds)

@st.cache_resource
def get_spreadsheet():
    """Get the target spreadsheet (cached)"""
    client = get_gspread_client()
    
    # Try Streamlit secrets first (with safe check)
    spreadsheet_id = None
    try:
        if hasattr(st, 'secrets') and 'SPREADSHEET_ID' in st.secrets:
            spreadsheet_id = st.secrets['SPREADSHEET_ID']
    except:
        pass  # Secrets not available, will try env
    
    # Fallback to environment variable
    if not spreadsheet_id and 'SPREADSHEET_ID' in os.environ:
        spreadsheet_id = os.getenv("SPREADSHEET_ID")
    
    if spreadsheet_id:
        return client.open_by_key(spreadsheet_id)
    return client.open("stockdata")


# ===== VN Index Helper Function =====
@st.cache_data(ttl=300)  # Cache 5 minutes
def get_vnindex_data():
    """Lấy dữ liệu VN-Index từ Google Sheets"""
    try:
        spreadsheet = get_spreadsheet()
        
        try:
            vnindex_ws = spreadsheet.worksheet("vnindex")
            vnindex_data = vnindex_ws.get_all_records()
            
            if vnindex_data:
                vnindex_df = pd.DataFrame(vnindex_data)
                # Lấy record mới nhất
                latest = vnindex_df.iloc[-1]
                return {
                    'value': float(latest.get('value', 0)),
                    'change': float(latest.get('change', 0)),
                    'change_pct': float(latest.get('change_pct', 0)),
                    'timestamp': latest.get('timestamp', ''),
                    'volume': int(latest.get('volume', 0))
                }
        except:
            pass
        
        return None
    except Exception as e:
        return None


# ===== Money Flow Helper Functions =====
@st.cache_data(ttl=300)  # Cache 5 minutes
def get_money_flow_top():
    """Lay du lieu dong tien tu money_flow_top sheet"""
    try:
        spreadsheet = get_spreadsheet()
        if not spreadsheet:
            return None, None, None
        
        try:
            flow_ws = spreadsheet.worksheet("money_flow_top")
            flow_data = flow_ws.get_all_records()
            flow_df = pd.DataFrame(flow_data)
            
            if flow_df.empty:
                return None, None, None
            
            # Convert numeric columns
            numeric_cols = ['price', 'volume', 'buy_flow', 'sell_flow', 'net_flow']
            for col in numeric_cols:
                if col in flow_df.columns:
                    flow_df[col] = pd.to_numeric(flow_df[col], errors='coerce')
            
            # Split by type - now includes stock_buy, stock_sell, sector_positive, sector_negative
            buy_stocks = flow_df[flow_df['type'] == 'stock_buy'].copy()
            sell_stocks = flow_df[flow_df['type'] == 'stock_sell'].copy()
            # For backwards compatibility, combine buy and sell as "stocks_df"
            stocks_df = pd.concat([buy_stocks, sell_stocks], ignore_index=True)
            # Also support old format (type == 'stock')
            if stocks_df.empty:
                stocks_df = flow_df[flow_df['type'] == 'stock'].copy()
            
            positive_sectors = flow_df[flow_df['type'] == 'sector_positive'].copy()
            negative_sectors = flow_df[flow_df['type'] == 'sector_negative'].copy()
            
            return stocks_df, positive_sectors, negative_sectors
        except Exception as e:
            # st.error(f"Lỗi đọc sheet money_flow_top: {e}") # Uncomment for debugging
            print(f"[ERROR] get_money_flow_top inner: {e}")
            return None, None, None
    except Exception as e:
        # st.error(f"Lỗi kết nối Google Sheets: {e}") # Uncomment for debugging
        print(f"[ERROR] get_money_flow_top outer: {e}")
        return None, None, None


# ===== Tab Render Functions are imported from dashboard_tabs.py =====
# See line 23: from dashboard_tabs import render_money_flow_tab, render_financial_screening_tab, render_watchlist_tab


    """Render tab Dòng Tiền"""
    st.markdown('<div class="main-header">💰 Dòng Tiền & Định Giá</div>', unsafe_allow_html=True)
    
    # Lấy dữ liệu
    with st.spinner("Đang tải dữ liệu dòng tiền..."):
        flow_df = get_money_flow_data()
    
    if flow_df.empty:
        st.warning("⚠️ Chưa có dữ liệu dòng tiền. Vui lòng chạy `python money_flow.py --interval 15` để thu thập dữ liệu.")
        st.info("💡 Hoặc đợi GitHub Actions tự động chạy vào giờ giao dịch (9:30-11:30, 13:30-14:45)")
        return
    
    # Lấy dữ liệu mới nhất
    latest_df = flow_df.groupby('ticker').tail(1).reset_index(drop=True)
    
    st.markdown("### 📊 Top 3 Ngành Có Dòng Tiền Mạnh Nhất")
    
    # Tổng hợp theo ngành
    sector_summary = latest_df.groupby('sector').agg({
        'money_flow_normalized': 'sum',
        'price_change_pct': 'mean',
        'pe_ratio': 'mean',
        'pb_ratio': 'mean',
        'ticker': 'count'
    }).reset_index()
    
    sector_summary.columns = ['sector', 'total_flow', 'avg_price_change', 'avg_pe', 'avg_pb', 'stock_count']
    sector_summary = sector_summary.sort_values('total_flow', ascending=False).head(3)
    
    # Hiển thị metrics cho top 3 sectors
    cols = st.columns(3)
    for idx, (_, row) in enumerate(sector_summary.iterrows()):
        with cols[idx]:
            st.metric(
                label=f"{row['sector']}",
                value=f"{row['total_flow']:.2f}B VNĐ",
                delta=f"{row['avg_price_change']:.2f}%"
            )
            st.caption(f"P/E TB: {row['avg_pe']:.1f} | P/B TB: {row['avg_pb']:.2f} | {int(row['stock_count'])} mã")
    
    # Biểu đồ cột
    fig_sector = go.Figure(data=[
        go.Bar(
            x=sector_summary['sector'],
            y=sector_summary['total_flow'],
            marker_color=['green' if x > 0 else 'red' for x in sector_summary['total_flow']],
            text=sector_summary['total_flow'].apply(lambda x: f"{x:.2f}B"),
            textposition='auto'
        )
    ])
    fig_sector.update_layout(
        title="Dòng Tiền Theo Ngành",
        xaxis_title="Ngành",
        yaxis_title="Dòng Tiền (Tỷ VNĐ)",
        height=400
    )
    st.plotly_chart(fig_sector, use_container_width=True)
    
    st.markdown("### 🔥 Top 5 Cổ Phiếu Có Dòng Tiền Mạnh Nhất")
    
    # Top 5 stocks
    top_stocks = latest_df.nlargest(5, 'money_flow_normalized')
    
    # Hiển thị bảng
    display_df = top_stocks[['ticker', 'sector', 'close', 'money_flow_normalized', 'price_change_pct', 'pe_ratio', 'pb_ratio', 'ps_ratio']].copy()
    display_df.columns = ['Mã', 'Ngành', 'Giá', 'Dòng Tiền (B)', '% Thay Đổi', 'P/E', 'P/B', 'P/S']
    
    # Format với styling
    st.dataframe(
        display_df.style.format({
            'Giá': '{:.2f}',
            'Dòng Tiền (B)': '{:.2f}',
            '% Thay Đổi': '{:+.2f}%',
            'P/E': '{:.1f}',
            'P/B': '{:.2f}',
            'P/S': '{:.2f}'
        }).background_gradient(subset=['Dòng Tiền (B)'], cmap='RdYlGn'),
        use_container_width=True
    )
    
    # Nút thêm vào watchlist
    st.markdown("#### ➕ Thêm vào Danh Sách Theo Dõi")
    for _, row in top_stocks.iterrows():
        col1, col2, col3 = st.columns([2, 6, 2])
        with col1:
            st.write(f"**{row['ticker']}**")
        with col2:
            st.write(f"Dòng tiền: {row['money_flow_normalized']:.2f}B | P/E: {row['pe_ratio']:.1f} | P/B: {row['pb_ratio']:.2f}")
        with col3:
            if st.button(f"➕ Thêm", key=f"add_flow_{row['ticker']}"):
                if add_to_watchlist(row['ticker'], 'flow'):
                    st.success(f"✅ Đã thêm {row['ticker']}")
                else:
                    st.error(f"❌ Lỗi khi thêm {row['ticker']}")
    
    st.markdown("### 🔍 Bộ Lọc Nâng Cao")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        min_flow = st.number_input("Dòng tiền >= (B VNĐ)", min_value=0.0, value=0.0, step=0.1)
    with col2:
        min_price_change = st.number_input("% tăng giá >=", min_value=-100.0, value=0.0, step=1.0)
    with col3:
        max_pe = st.number_input("P/E <=", min_value=0.0, value=25.0, step=1.0)
    with col4:
        max_pb = st.number_input("P/B <=", min_value=0.0, value=5.0, step=0.5)
    
    if st.button("🔍 Lọc", type="primary"):
        filtered_df = latest_df[
            (latest_df['money_flow_normalized'] >= min_flow) &
            (latest_df['price_change_pct'] >= min_price_change) &
            (latest_df['pe_ratio'] <= max_pe) &
            (latest_df['pb_ratio'] <= max_pb)
        ]
        
        if not filtered_df.empty:
            st.success(f"✅ Tìm thấy {len(filtered_df)} mã thỏa mãn")
            st.dataframe(
                filtered_df[['ticker', 'sector', 'money_flow_normalized', 'price_change_pct', 'pe_ratio', 'pb_ratio']],
                use_container_width=True
            )
        else:
            st.warning("⚠️ Không tìm thấy mã nào thỏa mãn tiêu chí")
    
    st.markdown("### 📈 Phân Tích Định Giá (P/E vs P/B)")
    
    # Scatter plot
    fig_scatter = px.scatter(
        latest_df,
        x='pe_ratio',
        y='pb_ratio',
        color='sector',
        size='money_flow_normalized',
        hover_data=['ticker', 'money_flow_normalized'],
        title="Phân Tích Định Giá Theo Ngành"
    )
    fig_scatter.update_layout(height=500)
    st.plotly_chart(fig_scatter, use_container_width=True)



def render_financial_screening_tab():
    """Render tab Lọc Cổ Phiếu"""
    
    # Real-time mode toggle
    st.markdown("### ⚡ Chế Độ Lọc")
    col_mode1, col_mode2 = st.columns([1, 3])
    with col_mode1:
        realtime_mode = st.toggle("🔴 Real-time Mode", value=False, 
                                  help="Sử dụng dữ liệu dòng tiền real-time (cập nhật mỗi 15 phút)")
    with col_mode2:
        if realtime_mode:
            st.info("💡 Đang sử dụng dữ liệu dòng tiền real-time từ intraday_flow")
        else:
            st.info("💡 Đang sử dụng dữ liệu tài chính từ báo cáo định kỳ")
    
    st.markdown("---")
    
    # Main header
    st.markdown('<div class="main-header">🔍 Lọc Cổ Phiếu Chất Lượng</div>', unsafe_allow_html=True)
    
    st.markdown("### 📊 Hệ Thống 10 Chỉ Tiêu Tài Chính")
    
    # Expander 1: Profitability
    with st.expander("💰 Khả năng sinh lời", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            min_roe = st.number_input("ROE >= (%)", min_value=0.0, max_value=100.0, value=15.0, step=1.0,
                                      help="Tỷ suất sinh lời trên vốn chủ sở hữu. Tốt: ≥15%, Xuất sắc: ≥20%")
        with col2:
            min_roa = st.number_input("ROA >= (%)", min_value=0.0, max_value=100.0, value=5.0, step=1.0,
                                      help="Tỷ suất sinh lời trên tài sản. Tốt: ≥5%, Xuất sắc: ≥10%")
        with col3:
            min_profit_margin = st.number_input("Biên lợi nhuận >= (%)", min_value=0.0, max_value=100.0, value=10.0, step=1.0,
                                                help="Lợi nhuận ròng / Doanh thu. Tốt: ≥10%")
    
    # Expander 2: Valuation
    with st.expander("📊 Định giá", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            max_pe = st.number_input("P/E <=", min_value=0.0, max_value=100.0, value=20.0, step=1.0,
                                     help="Giá/Thu nhập. Ngân hàng: 8-15, Công nghệ: 15-25, Tiêu dùng: 12-20")
        with col2:
            max_pb = st.number_input("P/B <=", min_value=0.0, max_value=10.0, value=3.0, step=0.5,
                                     help="Giá/Giá trị sổ sách. Tốt: <3, Xuất sắc: <1.5")
        with col3:
            max_ps = st.number_input("P/S <=", min_value=0.0, max_value=10.0, value=2.0, step=0.5,
                                     help="Vốn hóa/Doanh thu. Tốt: <2")
    
    # Expander 3: Growth
    with st.expander("📈 Tăng trưởng", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            min_eps_growth = st.number_input("Tăng trưởng EPS >= (% YoY)", min_value=-100.0, max_value=500.0, value=10.0, step=1.0,
                                             help="Tốt: ≥10%, Xuất sắc: ≥15%")
        with col2:
            min_revenue_growth = st.number_input("Tăng trưởng doanh thu >= (% YoY)", min_value=-100.0, max_value=500.0, value=10.0, step=1.0,
                                                 help="Tốt: ≥10%, Xuất sắc: ≥20%")
    
    # Expander 4: Financial Health
    with st.expander("🏥 Sức khỏe tài chính", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            max_debt_equity = st.number_input("Nợ/Vốn <=", min_value=0.0, max_value=10.0, value=1.0, step=0.1,
                                              help="Tốt: <1.0 (Ngân hàng có thể <5)")
        with col2:
            min_current_ratio = st.number_input("Tỷ lệ thanh khoản >=", min_value=0.0, max_value=10.0, value=1.5, step=0.1,
                                                help="Tốt: ≥1.5, Xuất sắc: ≥2.0")
    
    # Expander 5: Shareholder Returns
    with st.expander("💵 Lợi ích cổ đông", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            min_dividend_yield = st.number_input("Tỷ suất cổ tức >= (%)", min_value=0.0, max_value=20.0, value=3.0, step=0.5,
                                                 help="Tốt: ≥3%, Xuất sắc: ≥5%")
        with col2:
            dividend_years = st.selectbox("Số năm chia cổ tức liên tục", options=[1, 2, 3, 4, 5], index=2,
                                          help="Kiểm tra tính ổn định của cổ tức")
    
    # Bộ lọc bổ sung
    col1, col2 = st.columns(2)
    with col1:
        selected_sectors = st.multiselect("Chọn ngành", options=get_all_sectors(), 
                                          help="Để trống = lọc tất cả ngành")
    with col2:
        # Lấy tickers từ watchlist_flow
        try:
            creds = get_google_credentials()
            client = gspread.authorize(creds)
            import os
            spreadsheet_id = os.getenv("SPREADSHEET_ID")
            if spreadsheet_id:
                spreadsheet = client.open_by_key(spreadsheet_id)
            else:
                spreadsheet = client.open("stockdata")
            wl_ws = spreadsheet.worksheet("watchlist_flow")
            wl_data = wl_ws.get_all_records()
            if wl_data:
                wl_df = pd.DataFrame(wl_data)
                all_tickers = wl_df['ticker'].dropna().unique().tolist() if 'ticker' in wl_df.columns else []
            else:
                all_tickers = []
        except:
            all_tickers = []
        
        selected_tickers = st.multiselect("Hoặc chọn mã cụ thể", options=all_tickers,
                                          help="Để trống = lọc tất cả mã")
    
    if st.button("🔍 Lọc cổ phiếu", type="primary", use_container_width=True):
        with st.spinner("Đang phân tích..."):
            results = screen_by_criteria(
                min_roe=min_roe if min_roe > 0 else None,
                min_roa=min_roa if min_roa > 0 else None,
                min_profit_margin=min_profit_margin if min_profit_margin > 0 else None,
                max_pe=max_pe if max_pe > 0 else None,
                max_pb=max_pb if max_pb > 0 else None,
                max_ps=max_ps if max_ps > 0 else None,
                min_eps_growth=min_eps_growth if min_eps_growth > -100 else None,
                min_revenue_growth=min_revenue_growth if min_revenue_growth > -100 else None,
                max_debt_equity=max_debt_equity if max_debt_equity > 0 else None,
                min_current_ratio=min_current_ratio if min_current_ratio > 0 else None,
                min_dividend_yield=min_dividend_yield if min_dividend_yield > 0 else None,
                sectors_filter=selected_sectors if selected_sectors else None,
                tickers_filter=selected_tickers if selected_tickers else None
            )
        
        if not results.empty:
            st.success(f"✅ Tìm thấy {len(results)} mã thỏa mãn tiêu chí")
            
            # Hiển thị bảng kết quả với styling
            st.dataframe(
                results[['ticker', 'sector', 'composite_score', 'roe', 'roa', 'profit_margin',
                         'pe', 'pb', 'ps', 'eps_growth', 'revenue_growth', 
                         'debt_equity', 'current_ratio', 'dividend_yield']]
                .style.background_gradient(subset=['composite_score'], cmap='RdYlGn')
                .format({
                    'composite_score': '{:.0f}',
                    'roe': '{:.1f}%', 'roa': '{:.1f}%', 'profit_margin': '{:.1f}%',
                    'pe': '{:.1f}', 'pb': '{:.2f}', 'ps': '{:.2f}',
                    'eps_growth': '{:.1f}%', 'revenue_growth': '{:.1f}%',
                    'debt_equity': '{:.2f}', 'current_ratio': '{:.2f}',
                    'dividend_yield': '{:.1f}%'
                }),
                use_container_width=True
            )
            
            # Nút thêm vào watchlist
            st.markdown("### ➕ Thêm vào danh sách theo dõi")
            for idx, row in results.head(10).iterrows():
                col1, col2, col3 = st.columns([2, 6, 2])
                with col1:
                    st.write(f"**{row['ticker']}**")
                with col2:
                    st.write(f"Điểm: {row['composite_score']:.0f} | ROE: {row['roe']:.1f}% | P/E: {row['pe']:.1f}")
                with col3:
                    if st.button(f"➕ Thêm", key=f"add_fund_{row['ticker']}"):
                        if add_to_watchlist(row['ticker'], 'fundamental'):
                            st.success(f"✅ Đã thêm {row['ticker']}")
                        else:
                            st.error(f"❌ Lỗi khi thêm {row['ticker']}")
        else:
            st.warning("⚠️ Không tìm thấy mã nào thỏa mãn tiêu chí. Hãy thử giảm ngưỡng lọc.")



def render_watchlist_tab():
    """Render tab Danh Sách Theo Dõi - Enhanced with flow trend chart"""
    st.markdown('<div class="main-header">📋 Danh Sách Theo Dõi</div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["💰 Dòng Tiền", "📊 Cơ Bản"])
    
    with tab1:
        st.markdown("### 💰 Danh Sách Theo Dõi Dòng Tiền")
        st.caption("Các mã được thêm từ phân tích Giao dịch mua-bán")
        
        flow_watchlist = get_watchlist('flow')
        
        # Add new stock section
        with st.expander("➕ Thêm Mã Mới"):
            add_col1, add_col2 = st.columns([3, 1])
            with add_col1:
                new_ticker = st.text_input("Nhập mã cổ phiếu", placeholder="VNM", key="add_new_flow_ticker")
            with add_col2:
                st.write("")
                st.write("")
                if st.button("➕ Thêm", key="btn_add_flow"):
                    if new_ticker.strip():
                        if add_to_watchlist(new_ticker.strip().upper(), 'flow'):
                            st.success(f"✅ Đã thêm {new_ticker.upper()}")
                            st.rerun()
                        else:
                            st.error("❌ Lỗi khi thêm")
                    else:
                        st.warning("Vui lòng nhập mã")
        
        if not flow_watchlist.empty:
            # Display current data with delete buttons
            st.markdown("#### 📊 Danh mục hiện tại")
            
            for idx, row in flow_watchlist.iterrows():
                ticker = row.get('ticker', 'N/A') if isinstance(row, pd.Series) else row
                
                with st.container():
                    col1, col2, col3 = st.columns([2, 6, 2])
                    
                    with col1:
                        st.markdown(f"**{ticker}**")
                    
                    with col2:
                        # Display current metrics if available
                        if isinstance(row, pd.Series):
                            flow = row.get('money_flow', 0)
                            price = row.get('price', 0)
                            change = row.get('change_pct', 0)
                            if flow or price:
                                st.caption(f"💰 Dòng tiền: {flow:.2f}B | Giá: {price:,.1f}K | Δ: {change:+.2f}%")
                            else:
                                st.caption("Chưa có dữ liệu")
                        else:
                            st.caption("Đang tải...")
                    
                    with col3:
                        if st.button("🗑️", key=f"del_flow_{idx}_{ticker}", help=f"Xóa {ticker}"):
                            # Delete from watchlist
                            try:
                                creds = get_google_credentials()
                                client = gspread.authorize(creds)
                                spreadsheet = client.open("Stock_Data_Storage")
                                ws = spreadsheet.worksheet("watchlist_flow")
                                all_data = ws.get_all_records()
                                df = pd.DataFrame(all_data)
                                if not df.empty and 'ticker' in df.columns:
                                    df = df[df['ticker'] != ticker]
                                    ws.clear()
                                    ws.update([df.columns.values.tolist()] + df.values.tolist())
                                    st.success(f"✅ Đã xóa {ticker}")
                                    st.rerun()
                            except Exception as e:
                                st.error(f"❌ Lỗi: {str(e)}")
                
                st.markdown("---")
            
            # Flow trend chart - last 7 days
            st.markdown("#### 📈 Biểu Đồ Dòng Tiền 1 Tuần")
            st.caption("Xu hướng dòng tiền của các mã trong danh mục (7 ngày gần nhất)")
            
            try:
                # Get historical flow data from historical_flow sheet (not real-time)
                creds = get_google_credentials()
                client = gspread.authorize(creds)
                spreadsheet_id = os.getenv("SPREADSHEET_ID")
                if spreadsheet_id:
                    spreadsheet = client.open_by_key(spreadsheet_id)
                else:
                    spreadsheet = client.open("stockdata")
                
                try:
                    # Use historical_flow for 7-day trend (populated by historical_money_flow.py)
                    flow_ws = spreadsheet.worksheet("historical_flow")
                    flow_data = flow_ws.get_all_records()
                    flow_df = pd.DataFrame(flow_data)
                    
                    if not flow_df.empty:
                        # Get tickers from watchlist
                        wl_tickers = flow_watchlist['ticker'].tolist() if 'ticker' in flow_watchlist.columns else []
                        
                        if wl_tickers and 'ticker' in flow_df.columns:
                            # Filter for watchlist tickers
                            wl_flow = flow_df[flow_df['ticker'].isin(wl_tickers)].copy()
                            
                            # historical_flow uses 'date' column, not 'timestamp'
                            if not wl_flow.empty and 'date' in wl_flow.columns:
                                wl_flow['date'] = pd.to_datetime(wl_flow['date'], errors='coerce')
                                wl_flow['money_flow_normalized'] = pd.to_numeric(wl_flow['money_flow_normalized'], errors='coerce')
                                
                                # Last 7 days
                                cutoff = datetime.now() - timedelta(days=7)
                                recent = wl_flow[wl_flow['date'] >= cutoff]
                                
                                if not recent.empty:
                                    fig = px.line(
                                        recent,
                                        x='date',
                                        y='money_flow_normalized',
                                        color='ticker',
                                        markers=True,
                                        title="📈 Xu hướng Dòng Tiền 7 Ngày",
                                        labels={'money_flow_normalized': 'Dòng Tiền (Tỷ VNĐ)', 'date': 'Ngày'}
                                    )
                                    fig.update_layout(
                                        height=400,
                                        hovermode='x unified',
                                        legend=dict(orientation='h', yanchor='bottom', y=1.02)
                                    )
                                    st.plotly_chart(fig, use_container_width=True)
                                else:
                                    st.info("📊 Chưa có dữ liệu 7 ngày gần đây. Chạy `python historical_money_flow.py --days 7` để cào.")
                            else:
                                st.info("📊 Chưa có dữ liệu dòng tiền cho các mã trong danh mục")
                        else:
                            st.info("📊 Thêm mã vào danh mục để xem biểu đồ trend")
                    else:
                        st.info("📊 Chưa có dữ liệu lịch sử. Chạy `python historical_money_flow.py --days 7` để cào.")
                except gspread.WorksheetNotFound:
                    st.info("📊 Sheet historical_flow chưa tồn tại. Chạy `python historical_money_flow.py --days 7` để tạo.")
                except Exception as e:
                    st.info(f"Chưa có dữ liệu biểu đồ: {str(e)[:50]}")
            except Exception as e:
                st.info("Không thể tải dữ liệu biểu đồ")
            
            if st.button("🔄 Cập nhật dòng tiền", key="update_flow"):
                with st.spinner("Đang cập nhật..."):
                    update_watchlist_metrics('flow')
                    st.success("✅ Đã cập nhật!")
                    st.rerun()
        else:
            st.info("📝 Danh sách trống. Thêm mã từ menu Giao dịch mua-bán hoặc nhập ở trên.")
    
    with tab2:
        st.markdown("### 📊 Danh Sách Theo Dõi Cơ Bản")
        
        fund_watchlist = get_watchlist('fundamental')
        
        if not fund_watchlist.empty:
            st.dataframe(fund_watchlist, use_container_width=True)
            
            if st.button("🔄 Cập nhật chỉ số", key="update_fund"):
                with st.spinner("Đang cập nhật..."):
                    update_watchlist_metrics('fundamental')
                    st.success("✅ Đã cập nhật!")
                    st.rerun()
        else:
            st.info("📝 Danh sách trống. Thêm mã từ tab Lọc Cổ Phiếu.")

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(90deg, #1f77b4, #2ca02c);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("# 📈 Stock Analysis")
    st.markdown("**Phân Tích Chứng Khoán VN**")
    st.markdown("---")
    
    # Auto-refresh settings
    st.markdown("### ⚙️ Cài Đặt")
    auto_refresh = st.checkbox("🔄 Auto-refresh", value=True, help="Tự động làm mới dữ liệu mỗi 20 phút")
    refresh_interval = st.slider(
        "Refresh mỗi (phút)",
        min_value=5,
        max_value=60,
        value=20,
        step=5,
        disabled=not auto_refresh
    )
    
    st.markdown("---")
    
    page = st.radio(
        "📍 Navigation",
        ["🏠 Dashboard", "📊 Phân Tích", "💰 Báo Cáo Tài Chính", "💸 Giao dịch mua-bán", "🔍 Lọc Cổ Phiếu", "📋 Danh Sách Theo Dõi", "🌐 Khuyến Nghị", "🔬 Backtest", "⚙️ Hệ thống"],
        label_visibility="collapsed"
    )

# Main content
if page == "🏠 Dashboard":
    st.markdown('<div class="main-header">📈 Stock Analysis Dashboard</div>', unsafe_allow_html=True)
    
    # VN-Index Display
    vnindex = get_vnindex_data()
    if vnindex:
        col_vn1, col_vn2, col_vn3, col_vn4 = st.columns(4)
        with col_vn1:
            st.metric(
                "📊 VN-Index",
                f"{vnindex['value']:,.2f}",
                f"{vnindex['change']:+,.2f} ({vnindex['change_pct']:+.2f}%)",
                delta_color="normal"
            )
        with col_vn2:
            st.metric("🕐 Cập nhật", vnindex['timestamp'].split(' ')[1] if ' ' in vnindex['timestamp'] else vnindex['timestamp'])
        with col_vn3:
            st.metric("📊 Khối lượng", f"{vnindex['volume']:,}")
        with col_vn4:
            trend = "📈 Tăng" if vnindex['change'] > 0 else "📉 Giảm" if vnindex['change'] < 0 else "➡️ Đứng"
            st.metric("Xu hướng", trend)
        
        st.markdown("---")
    
    # Money Flow Summary - Using new money_flow_top format
    st.markdown("## 💰 Tổng Quan Dòng Tiền Mua-Bán")
    
    stocks_df, positive_sectors, negative_sectors = get_money_flow_top()
    
    if (positive_sectors is not None and not positive_sectors.empty) or \
       (negative_sectors is not None and not negative_sectors.empty):
        
        # Timestamp
        if stocks_df is not None and not stocks_df.empty and 'timestamp' in stocks_df.columns:
            st.caption(f"🕐 Cập nhật lúc: {stocks_df['timestamp'].iloc[0]}")
        
        # ===== Charts Section (Only Charts, No Metric Cards) =====
        
        # Chart 1: Sector bar charts - Positive and Negative side by side
        col_chart1, col_chart2 = st.columns(2)
        
        # Chart 1a: Top 3 Ngành MUA Mạnh
        with col_chart1:
            if positive_sectors is not None and not positive_sectors.empty:
                fig_pos = go.Figure()
                pos_sectors_top3 = positive_sectors.head(3)
                
                # Add net flow bars
                fig_pos.add_trace(go.Bar(
                    name='Dòng tiền ròng',
                    x=[f"🟢 {s}" for s in pos_sectors_top3['sector'].tolist()],
                    y=pos_sectors_top3['net_flow'].tolist(),
                    marker_color='#26a69a',
                    text=[f"+{v:.2f}B" for v in pos_sectors_top3['net_flow'].tolist()],
                    textposition='outside'
                ))
                
                fig_pos.update_layout(
                    title="📈 Top 3 Ngành MUA Mạnh",
                    xaxis_title="Ngành",
                    yaxis_title="Dòng tiền ròng (Tỷ VNĐ)",
                    height=350,
                    showlegend=False
                )
                st.plotly_chart(fig_pos, use_container_width=True)
            else:
                st.info("Chưa có dữ liệu ngành mua mạnh")
        
        # Chart 1b: Top 3 Ngành BÁN Mạnh
        with col_chart2:
            if negative_sectors is not None and not negative_sectors.empty:
                fig_neg = go.Figure()
                neg_sectors_top3 = negative_sectors.head(3)
                
                # Add net flow bars (negative)
                fig_neg.add_trace(go.Bar(
                    name='Dòng tiền ròng',
                    x=[f"🔴 {s}" for s in neg_sectors_top3['sector'].tolist()],
                    y=[abs(v) for v in neg_sectors_top3['net_flow'].tolist()],
                    marker_color='#ef5350',
                    text=[f"-{abs(v):.2f}B" for v in neg_sectors_top3['net_flow'].tolist()],
                    textposition='outside'
                ))
                
                fig_neg.update_layout(
                    title="📉 Top 3 Ngành BÁN Mạnh",
                    xaxis_title="Ngành",
                    yaxis_title="Dòng tiền ròng (Tỷ VNĐ)",
                    height=350,
                    showlegend=False
                )
                st.plotly_chart(fig_neg, use_container_width=True)
            else:
                st.info("Chưa có dữ liệu ngành bán mạnh")
        
        # Chart 2: Top stocks - BUY and SELL side by side
        if stocks_df is not None and not stocks_df.empty:
            st.markdown("### 📊 Top Cổ Phiếu Theo Dòng Tiền")
            
            # Separate buy and sell
            buy_stocks = stocks_df[stocks_df['type'] == 'stock_buy'].head(9) if 'type' in stocks_df.columns else stocks_df[stocks_df['net_flow'] > 0].head(9)
            sell_stocks = stocks_df[stocks_df['type'] == 'stock_sell'].head(9) if 'type' in stocks_df.columns else stocks_df[stocks_df['net_flow'] < 0].head(9)
            
            col_buy, col_sell = st.columns(2)
            
            # Chart 2a: Top BUY stocks
            with col_buy:
                if not buy_stocks.empty:
                    fig_buy = go.Figure()
                    fig_buy.add_trace(go.Bar(
                        name='Dòng tiền MUA',
                        x=buy_stocks['ticker'].tolist(),
                        y=buy_stocks['net_flow'].tolist(),
                        marker_color='#26a69a',
                        text=[f"+{v:.2f}B" for v in buy_stocks['net_flow'].tolist()],
                        textposition='outside'
                    ))
                    fig_buy.update_layout(
                        title="🟢 Top 9 Cổ Phiếu MUA Mạnh",
                        xaxis_title="Mã", yaxis_title="Dòng tiền (Tỷ VNĐ)",
                        height=350, showlegend=False
                    )
                    st.plotly_chart(fig_buy, use_container_width=True)
                else:
                    st.info("Chưa có dữ liệu mã mua mạnh")
            
            # Chart 2b: Top SELL stocks
            with col_sell:
                if not sell_stocks.empty:
                    fig_sell = go.Figure()
                    fig_sell.add_trace(go.Bar(
                        name='Dòng tiền BÁN',
                        x=sell_stocks['ticker'].tolist(),
                        y=[abs(v) for v in sell_stocks['net_flow'].tolist()],
                        marker_color='#ef5350',
                        text=[f"-{abs(v):.2f}B" for v in sell_stocks['net_flow'].tolist()],
                        textposition='outside'
                    ))
                    fig_sell.update_layout(
                        title="🔴 Top 9 Cổ Phiếu BÁN Mạnh",
                        xaxis_title="Mã", yaxis_title="Dòng tiền (Tỷ VNĐ)",
                        height=350, showlegend=False
                    )
                    st.plotly_chart(fig_sell, use_container_width=True)
                else:
                    st.info("Chưa có dữ liệu mã bán mạnh")
        
    else:
        st.warning("Chua co du lieu dong tien. Vui long chay `python money_flow.py` de cap nhat.")
        st.info("Hoac doi GitHub Actions tu dong cap nhat vao gio giao dich.")

elif page == "📊 Phân Tích":
    st.markdown('<div class="main-header">📊 Phân Tích Kỹ Thuật</div>', unsafe_allow_html=True)
    st.caption("Lấy mã từ Danh Sách Theo Dõi. Có thể chọn tất cả nếu muốn.")
    
    # Get watchlist tickers first
    flow_watchlist = get_watchlist('flow')
    watchlist_tickers = flow_watchlist['ticker'].tolist() if not flow_watchlist.empty and 'ticker' in flow_watchlist.columns else []
    all_tickers = fetch_ticker_list()
    
    # Stock source selection
    col_src1, col_src2 = st.columns([1, 3])
    with col_src1:
        use_watchlist = st.checkbox("📋 Từ Danh mục", value=True, help="Chỉ hiển thị mã trong Danh Sách Theo Dõi")
    
    # Determine ticker list
    available_tickers = watchlist_tickers if use_watchlist and watchlist_tickers else all_tickers
    
    if not available_tickers:
        st.warning("Chưa có mã nào trong Danh Sách Theo Dõi. Vui lòng thêm mã từ menu Giao dịch mua-bán.")
        available_tickers = all_tickers
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        default_idx = 0
        ta_symbol = st.selectbox("Mã chứng khoán", options=available_tickers, key="ta_symbol", index=default_idx)
    with col2:
        period_options = {
            "1 Tuần": 7,
            "1 Tháng": 30,
            "3 Tháng": 90,
            "6 Tháng": 180,
            "1 Năm": 365,
            "2 Năm": 730,
            "3 Năm": 1095,
            "5 Năm": 1825
        }
        selected_period = st.selectbox("Khoảng thời gian", options=list(period_options.keys()), index=4)  # Default to 1 Year
        ta_days = period_options[selected_period]
    with col3:
        indicators = st.multiselect(
            "Chỉ báo kỹ thuật",
            ["SMA 20", "SMA 50", "SMA 200", "RSI", "MACD"],
            default=["SMA 20", "SMA 50"]
        )

    if ta_symbol:
        try:
            with st.spinner(f"Đang tính toán chỉ báo cho {ta_symbol}..."):
                # Fetch data
                end_date = datetime.now()
                start_date = end_date - timedelta(days=ta_days)
                df = fetch_stock_data(ta_symbol, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
                
                if not df.empty:
                    # Calculations
                    if "SMA 20" in indicators:
                        df['SMA20'] = df['close'].rolling(window=20).mean()
                    if "SMA 50" in indicators:
                        df['SMA50'] = df['close'].rolling(window=50).mean()
                    if "SMA 200" in indicators:
                        df['SMA200'] = df['close'].rolling(window=200).mean()
                    
                    # Main TA Chart
                    fig_ta = go.Figure()
                    
                    # Add candlestick first
                    fig_ta.add_trace(go.Candlestick(
                        x=df.index,
                        open=df['open'],
                        high=df['high'],
                        low=df['low'],
                        close=df['close'],
                        name=ta_symbol,
                        increasing_line_color='#26a69a',
                        decreasing_line_color='#ef5350'
                    ))
                    
                    # Add MA lines on top with distinct colors and thicker lines
                    if "SMA20" in df.columns:
                        fig_ta.add_trace(go.Scatter(
                            x=df.index,
                            y=df['SMA20'],
                            name='SMA 20',
                            line=dict(color='#FF6B6B', width=2),
                            mode='lines'
                        ))
                    
                    if "SMA50" in df.columns:
                        fig_ta.add_trace(go.Scatter(
                            x=df.index,
                            y=df['SMA50'],
                            name='SMA 50',
                            line=dict(color='#4ECDC4', width=2),
                            mode='lines'
                        ))
                    
                    if "SMA200" in df.columns:
                        fig_ta.add_trace(go.Scatter(
                            x=df.index,
                            y=df['SMA200'],
                            name='SMA 200',
                            line=dict(color='#FFD93D', width=2),
                            mode='lines'
                        ))
                    
                    fig_ta.update_layout(
                        height=600,
                        xaxis_rangeslider_visible=False,
                        yaxis_title="Giá (VNĐ)",
                        hovermode='x unified',
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="right",
                            x=1
                        )
                    )
                    st.plotly_chart(fig_ta, use_container_width=True)
                    
                    # Volume Chart
                    st.subheader("📊 Khối Lượng Giao Dịch")
                    colors = ['#26a69a' if df['close'].iloc[i] >= df['open'].iloc[i] else '#ef5350' 
                             for i in range(len(df))]
                    
                    fig_vol = go.Figure()
                    fig_vol.add_trace(go.Bar(
                        x=df.index,
                        y=df['volume'],
                        name='Khối lượng',
                        marker_color=colors
                    ))
                    fig_vol.update_layout(
                        height=200,
                        yaxis_title="Khối lượng",
                        hovermode='x unified',
                        showlegend=False
                    )
                    st.plotly_chart(fig_vol, use_container_width=True)
                    
                    # RSI Chart
                    if "RSI" in indicators:
                        delta = df['close'].diff()
                        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                        rs = gain / loss
                        df['RSI'] = 100 - (100 / (1 + rs))
                        
                        st.subheader("RSI (14)")
                        fig_rsi = go.Figure()
                        fig_rsi.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI', line=dict(color='purple')))
                        fig_rsi.add_hline(y=70, line_dash="dash", line_color="red")
                        fig_rsi.add_hline(y=30, line_dash="dash", line_color="green")
                        fig_rsi.update_layout(height=200, yaxis=dict(range=[0, 100]))
                        st.plotly_chart(fig_rsi, use_container_width=True)
                    
                    # MACD Chart
                    if "MACD" in indicators:
                        exp1 = df['close'].ewm(span=12, adjust=False).mean()
                        exp2 = df['close'].ewm(span=26, adjust=False).mean()
                        df['MACD'] = exp1 - exp2
                        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
                        df['Hist'] = df['MACD'] - df['Signal']
                        
                        st.subheader("MACD")
                        fig_macd = go.Figure()
                        fig_macd.add_trace(go.Scatter(x=df.index, y=df['MACD'], name='MACD', line=dict(color='blue')))
                        fig_macd.add_trace(go.Scatter(x=df.index, y=df['Signal'], name='Signal', line=dict(color='orange')))
                        fig_macd.add_trace(go.Bar(x=df.index, y=df['Hist'], name='Histogram'))
                        fig_macd.update_layout(height=250)
                        st.plotly_chart(fig_macd, use_container_width=True)

                else:
                    st.error(f"❌ Không lấy được dữ liệu cho {ta_symbol}")
        except Exception as e:
            st.error("❌ Lỗi phân tích: ")

elif page == "💰 Báo Cáo Tài Chính":
    st.markdown('<div class="main-header">💰 Báo Cáo Tài Chính</div>', unsafe_allow_html=True)
    
    # Add cache clear button
    if st.button("🔄 Làm mới dữ liệu", help="Xóa cache để lấy dữ liệu mới nhất"):
        fetch_financial_sheet.clear()
        get_spreadsheet.clear()  # Also clear spreadsheet cache
        st.success("✅ Đã xóa cache!")
        st.rerun()
    
    # Get tickers from scraped income data - with detailed debug
    try:
        # Direct access to check spreadsheet
        spreadsheet = get_spreadsheet()
        st.info(f"📊 Đang kết nối: **{spreadsheet.title}**")
        
        # Try to access income sheet directly
        try:
            ws = spreadsheet.worksheet("income")
            all_data = ws.get_all_records()
            st.info(f"📋 Sheet 'income': {len(all_data)} bản ghi")
            
            if all_data:
                income_df = pd.DataFrame(all_data)
                st.info(f"📝 Các cột: {list(income_df.columns)[:8]}")
                
                if 'ticker' in income_df.columns:
                    finance_tickers = sorted(income_df['ticker'].dropna().unique().tolist())
                    st.success(f"✅ Tìm thấy {len(finance_tickers)} mã: {finance_tickers[:10]}...")
                    # Clear cache so report display gets fresh data
                    fetch_financial_sheet.clear()
                else:
                    st.warning(f"⚠️ Không có cột 'ticker'. Các cột: {list(income_df.columns)}")
                    finance_tickers = []
            else:
                st.warning("⚠️ Sheet 'income' có 0 bản ghi")
                finance_tickers = []
                
        except gspread.WorksheetNotFound:
            st.error("❌ Không tìm thấy sheet 'income'")
            # List available sheets
            sheets = [ws.title for ws in spreadsheet.worksheets()]
            st.info(f"📑 Các sheet có sẵn: {sheets}")
            finance_tickers = []
            
    except Exception as e:
        st.error(f"❌ Lỗi: {str(e)}")
        import traceback
        st.code(traceback.format_exc()[:500])
        finance_tickers = []
    
    # Add new ticker section
    with st.expander("➕ Thêm/Xóa Mã Báo Cáo Tài Chính"):
        add_col1, add_col2 = st.columns([3, 1])
        with add_col1:
            new_fin_ticker = st.text_input("Nhập mã cổ phiếu cần cào BCTC", placeholder="VNM, FPT", key="add_fin_ticker")
        with add_col2:
            st.write("")
            st.write("")
            if st.button("📋 Cào BCTC", key="btn_scrape_new_fin"):
                if new_fin_ticker.strip():
                    with st.spinner(f"Đang cào BCTC {new_fin_ticker}..."):
                        try:
                            import subprocess
                            result = subprocess.run(
                                [sys.executable, 'finance.py', '--tickers', new_fin_ticker.strip()],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, encoding='utf-8', errors='replace',
                                timeout=300,
                                cwd=os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else '.'
                            )
                            if result.returncode == 0:
                                st.success(f"✅ Đã cào BCTC {new_fin_ticker}")
                                st.rerun()
                            else:
                                st.error(f"❌ Lỗi: {result.stderr[:500] if result.stderr else 'Unknown error'}")
                        except subprocess.TimeoutExpired:
                            st.error("⏰ Timeout sau 5 phút")
                        except Exception as e:
                            st.error(f"❌ Lỗi: {str(e)}")
                else:
                    st.warning("Vui lòng nhập mã")
        
        # Delete section
        if finance_tickers:
            del_tickers = st.multiselect("🗑️ Chọn mã cần xóa khỏi BCTC", options=finance_tickers, key="del_fin_tickers")
            if st.button("🗑️ Xóa Dữ Liệu Đã Chọn", key="btn_del_fin"):
                if del_tickers:
                    with st.spinner("Đang xóa..."):
                        try:
                            creds = get_google_credentials()
                            client = gspread.authorize(creds)
                            spreadsheet = client.open("stockdata")
                            
                            deleted_count = 0
                            for sheet_name in ["income", "balance", "cashflow"]:
                                try:
                                    ws = spreadsheet.worksheet(sheet_name)
                                    all_data = ws.get_all_records()
                                    df = pd.DataFrame(all_data)
                                    if not df.empty and 'ticker' in df.columns:
                                        original = len(df)
                                        df = df[~df['ticker'].isin(del_tickers)]
                                        deleted_count += original - len(df)
                                        ws.clear()
                                        ws.update([df.columns.values.tolist()] + df.values.tolist())
                                except:
                                    pass
                            st.success(f"✅ Đã xóa {deleted_count} bản ghi!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Lỗi: {str(e)}")
    
    # Show ticker selection from available data
    if finance_tickers:
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            fin_symbol = st.selectbox("Chọn mã xem báo cáo", options=finance_tickers, key="fin_symbol")
        with col2:
            period_type = st.radio("Kỳ báo cáo", ["Quý", "Năm"], horizontal=True)
        with col3:
            current_year = datetime.now().year
            if period_type == "Năm":
                selected_year = st.selectbox("Năm", options=list(range(current_year, current_year-10, -1)), index=0)
                selected_quarter = None
            else:
                selected_year = st.selectbox("Năm", options=list(range(current_year, current_year-5, -1)), index=0, key="year_q")
                selected_quarter = st.selectbox("Quý", options=[1, 2, 3, 4], index=0)
    else:
        st.info("📝 Chưa có dữ liệu BCTC. Vui lòng nhập mã và bấm 'Cào BCTC' ở trên.")
        fin_symbol = None
        period_type = "Quý"
        selected_year = datetime.now().year
        selected_quarter = 1

    if fin_symbol:
        with st.spinner(f"Đang tải báo cáo tài chính {fin_symbol}..."):
            # Calculate and display key metrics
            metrics = calculate_financial_metrics(fin_symbol)
            
            if metrics:
                st.subheader("📈 Chỉ số tài chính quan trọng")
                col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
                
                with col1:
                    if 'ROE' in metrics:
                        st.metric("ROE", f"{metrics['ROE']:.2f}%")
                    else:
                        st.metric("ROE", "N/A")
                
                with col2:
                    if 'ROA' in metrics:
                        st.metric("ROA", f"{metrics['ROA']:.2f}%")
                    else:
                        st.metric("ROA", "N/A")
                
                with col3:
                    if 'profit_margin' in metrics:
                        st.metric("Profit Margin", f"{metrics['profit_margin']:.2f}%")
                    else:
                        st.metric("Profit Margin", "N/A")
                
                with col4:
                    if 'debt_to_equity' in metrics:
                        st.metric("Debt/Equity", f"{metrics['debt_to_equity']:.2f}")
                    else:
                        st.metric("Debt/Equity", "N/A")
                
                with col5:
                    if 'EPS' in metrics:
                        st.metric("EPS", f"{metrics['EPS']:,.0f}")
                    else:
                        st.metric("EPS", "N/A")
                
                with col6:
                    if 'PE' in metrics:
                        st.metric("P/E", f"{metrics['PE']:.2f}")
                    else:
                        st.metric("P/E", "N/A")
                
                with col7:
                    if 'PB' in metrics:
                        st.metric("P/B", f"{metrics['PB']:.2f}")
                    else:
                        st.metric("P/B", "N/A")
                
                st.markdown("---")
            
            # Load sheets
            income_df = fetch_financial_sheet("income")
            balance_df = fetch_financial_sheet("balance")
            cashflow_df = fetch_financial_sheet("cashflow")
            
            # Normalize column names
            if not income_df.empty:
                income_df.columns = income_df.columns.str.lower().str.replace(' ', '_')
            if not balance_df.empty:
                balance_df.columns = balance_df.columns.str.lower().str.replace(' ', '_')
            if not cashflow_df.empty:
                cashflow_df.columns = cashflow_df.columns.str.lower().str.replace(' ', '_')
            
            # Filter by ticker
            if not income_df.empty:
                ticker_income = income_df[income_df['ticker'].astype(str).str.upper() == fin_symbol]
                
                if not ticker_income.empty:
                    # Filter by period
                    if period_type == "Năm":
                        # Get 3 most recent years for comparison
                        if 'year' in ticker_income.columns:
                            ticker_income['year'] = pd.to_numeric(ticker_income['year'], errors='coerce')
                            recent_years = sorted(ticker_income['year'].dropna().unique(), reverse=True)[:3]
                            filtered_income = ticker_income[ticker_income['year'].isin(recent_years)]
                            filtered_income = filtered_income.sort_values('year', ascending=False)
                        else:
                            filtered_income = ticker_income.tail(3)
                    else:
                        # Filter by selected quarter and show 3 years comparison
                        if 'year' in ticker_income.columns and 'quarter' in ticker_income.columns:
                            ticker_income['year'] = pd.to_numeric(ticker_income['year'], errors='coerce')
                            ticker_income['quarter'] = pd.to_numeric(ticker_income['quarter'], errors='coerce')
                            
                            # Get same quarter for 3 recent years
                            years_to_compare = [selected_year, selected_year-1, selected_year-2]
                            filtered_income = ticker_income[
                                (ticker_income['quarter'] == selected_quarter) &
                                (ticker_income['year'].isin(years_to_compare))
                            ]
                            filtered_income = filtered_income.sort_values(['year', 'quarter'], ascending=False)
                        else:
                            filtered_income = ticker_income.tail(3)
                    
                    # Tabs for different reports
                    tab1, tab2, tab3 = st.tabs(["📊 Kết Quả Kinh Doanh", "⚖️ Bảng Cân Đối", "💸 Lưu Chuyển Tiền Tệ"])
                    
                    with tab1:
                        st.subheader(f"Báo cáo Kết quả Kinh doanh - {period_type}")
                        
                        # Show comparison info
                        if period_type == "Năm":
                            st.info(f"📊 So sánh 3 năm gần nhất")
                        else:
                            st.info(f"📊 So sánh Quý {selected_quarter} của 3 năm: {selected_year}, {selected_year-1}, {selected_year-2}")
                        
                        # Growth Chart
                        if not filtered_income.empty and 'revenue' in filtered_income.columns:
                            fig_growth = go.Figure()
                            
                            # Prepare x-axis labels
                            if period_type == "Năm":
                                x_labels = filtered_income['year'].astype(str)
                            else:
                                x_labels = "Q" + filtered_income['quarter'].astype(str) + "/" + filtered_income['year'].astype(str)
                            
                            fig_growth.add_trace(go.Bar(
                                x=x_labels,
                                y=pd.to_numeric(filtered_income['revenue'], errors='coerce'),
                                name='Doanh thu',
                                marker_color='#4ECDC4'
                            ))
                            
                            # Handle different column names for net income
                            net_income_col = None
                            for col in ['net_income', 'share_holder_income', 'post_tax_profit']:
                                if col in filtered_income.columns:
                                    net_income_col = col
                                    break
                            
                            if net_income_col:
                                fig_growth.add_trace(go.Scatter(
                                    x=x_labels,
                                    y=pd.to_numeric(filtered_income[net_income_col], errors='coerce'),
                                    name='Lợi nhuận sau thuế',
                                    yaxis='y2',
                                    line=dict(color='#FF6B6B', width=3),
                                    mode='lines+markers'
                                ))
                            
                            fig_growth.update_layout(
                                yaxis_title="Doanh thu",
                                yaxis2=dict(title="Lợi nhuận", overlaying='y', side='right'),
                                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                                height=400,
                                hovermode='x unified'
                            )
                            st.plotly_chart(fig_growth, use_container_width=True)
                        
                        # Summary table (key metrics only)
                        st.subheader("📋 Bảng So Sánh")
                        if not filtered_income.empty:
                            # Select only important columns
                            display_cols = []
                            for col in ['year', 'quarter', 'revenue', 'net_income', 'share_holder_income', 'post_tax_profit']:
                                if col in filtered_income.columns:
                                    display_cols.append(col)
                            
                            if display_cols:
                                summary_df = filtered_income[display_cols].copy()
                                # Format numbers
                                for col in summary_df.columns:
                                    if col not in ['year', 'quarter']:
                                        summary_df[col] = pd.to_numeric(summary_df[col], errors='coerce').apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "N/A")
                                st.dataframe(summary_df, use_container_width=True, hide_index=True)
                    
                    with tab2:
                        st.subheader("Bảng Cân đối Kế toán")
                        if not balance_df.empty:
                            ticker_balance = balance_df[balance_df['ticker'].astype(str).str.upper() == fin_symbol]
                            
                            # Apply same filtering
                            if period_type == "Năm" and 'year' in ticker_balance.columns:
                                ticker_balance['year'] = pd.to_numeric(ticker_balance['year'], errors='coerce')
                                recent_years = sorted(ticker_balance['year'].dropna().unique(), reverse=True)[:3]
                                filtered_balance = ticker_balance[ticker_balance['year'].isin(recent_years)]
                                filtered_balance = filtered_balance.sort_values('year', ascending=False)
                            elif 'year' in ticker_balance.columns and 'quarter' in ticker_balance.columns:
                                ticker_balance['year'] = pd.to_numeric(ticker_balance['year'], errors='coerce')
                                ticker_balance['quarter'] = pd.to_numeric(ticker_balance['quarter'], errors='coerce')
                                years_to_compare = [selected_year, selected_year-1, selected_year-2]
                                filtered_balance = ticker_balance[
                                    (ticker_balance['quarter'] == selected_quarter) &
                                    (ticker_balance['year'].isin(years_to_compare))
                                ]
                                filtered_balance = filtered_balance.sort_values(['year', 'quarter'], ascending=False)
                            else:
                                filtered_balance = ticker_balance.tail(3)
                            
                            st.dataframe(filtered_balance, use_container_width=True)
                        else:
                            st.warning("Không có dữ liệu Bảng cân đối")
                            
                    with tab3:
                        st.subheader("Báo cáo Lưu chuyển Tiền tệ")
                        if not cashflow_df.empty:
                            ticker_cashflow = cashflow_df[cashflow_df['ticker'].astype(str).str.upper() == fin_symbol]
                            
                            # Apply same filtering
                            if period_type == "Năm" and 'year' in ticker_cashflow.columns:
                                ticker_cashflow['year'] = pd.to_numeric(ticker_cashflow['year'], errors='coerce')
                                recent_years = sorted(ticker_cashflow['year'].dropna().unique(), reverse=True)[:3]
                                filtered_cashflow = ticker_cashflow[ticker_cashflow['year'].isin(recent_years)]
                                filtered_cashflow = filtered_cashflow.sort_values('year', ascending=False)
                            elif 'year' in ticker_cashflow.columns and 'quarter' in ticker_cashflow.columns:
                                ticker_cashflow['year'] = pd.to_numeric(ticker_cashflow['year'], errors='coerce')
                                ticker_cashflow['quarter'] = pd.to_numeric(ticker_cashflow['quarter'], errors='coerce')
                                years_to_compare = [selected_year, selected_year-1, selected_year-2]
                                filtered_cashflow = ticker_cashflow[
                                    (ticker_cashflow['quarter'] == selected_quarter) &
                                    (ticker_cashflow['year'].isin(years_to_compare))
                                ]
                                filtered_cashflow = filtered_cashflow.sort_values(['year', 'quarter'], ascending=False)
                            else:
                                filtered_cashflow = ticker_cashflow.tail(3)
                            
                            st.dataframe(filtered_cashflow, use_container_width=True)
                        else:
                            st.warning("Không có dữ liệu Lưu chuyển tiền tệ")
                else:
                    st.error(f"❌ Không tìm thấy dữ liệu tài chính cho mã {fin_symbol}")
                    st.info("💡 Đảm bảo bạn đã chạy script `finance.py` để cập nhật dữ liệu vào Google Sheets.")
            else:
                st.info("💡 Chưa có dữ liệu tài chính. Vui lòng chạy `finance.py` hoặc kiểm tra kết nối Sheets.")
    
    # ===== Finance Scraper Section =====
    st.markdown("---")
    st.subheader("📥 Cào Dữ Liệu Báo Cáo Tài Chính")
    st.info("💡 Cào dữ liệu báo cáo tài chính (Income, Balance, Cashflow) từ vnstock")
    
    # Filter options - Row 1
    fin_scr_col1, fin_scr_col2, fin_scr_col3 = st.columns(3)
    
    with fin_scr_col1:
        fin_scr_period = st.selectbox(
            "📅 Loại báo cáo",
            options=["quarter", "annual"],
            format_func=lambda x: "Theo Quý" if x == "quarter" else "Theo Năm",
            key="fin_scr_period"
        )
    
    with fin_scr_col2:
        fin_scr_years = st.selectbox(
            "📆 Số năm cần cào",
            options=[1, 2, 3, 4, 5],
            index=2,  # Default 3 years
            help="Số năm dữ liệu cần cào (1-5 năm)",
            key="fin_scr_years"
        )
    
    with fin_scr_col3:
        fin_scr_tickers_input = st.text_input(
            "🔍 Mã cổ phiếu (để trống = tất cả)",
            placeholder="VNM, FPT, VCB",
            help="Nhập các mã cách nhau bởi dấu phẩy.",
            key="fin_scr_tickers"
        )
    
    # Sector filter - Row 2
    all_sectors = get_all_sectors()
    fin_scr_selected_sectors = st.multiselect(
        "🏭 Lọc theo ngành (bỏ trống = tất cả ngành)",
        options=all_sectors,
        help="Chọn các ngành muốn cào. Bỏ trống để cào tất cả ngành.",
        key="fin_scr_sectors"
    )
    
    # Scrape button
    if st.button("📋 Cào Báo Cáo Tài Chính", use_container_width=True, type="primary", key="btn_fin_scrape"):
        with st.spinner("Đang cào báo cáo tài chính..."):
            try:
                import subprocess
                
                # Build command with filters
                cmd = [sys.executable, 'finance.py', '--period', fin_scr_period, '--years', str(fin_scr_years)]
                
                # Add ticker filter
                if fin_scr_tickers_input.strip():
                    cmd.extend(['--tickers', fin_scr_tickers_input.strip()])
                
                # Add sector filter - get tickers from selected sectors
                if fin_scr_selected_sectors and not fin_scr_tickers_input.strip():
                    from sectors import get_tickers_by_sector
                    sector_tickers = []
                    for sector in fin_scr_selected_sectors:
                        sector_tickers.extend(get_tickers_by_sector(sector))
                    if sector_tickers:
                        cmd.extend(['--tickers', ','.join(set(sector_tickers))])
                
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
                    timeout=1800
                )
                if result.returncode == 0:
                    st.success("✅ Hoàn tất cào báo cáo tài chính!")
                    st.balloons()
                    if result.stdout:
                        with st.expander("📄 Chi tiết"):
                            st.code(result.stdout[-2000:])
                else:
                    st.error(f"❌ Lỗi khi cào báo cáo tài chính (Exit code: {result.returncode})")
                    if result.stderr:
                        st.code(result.stderr)
            except subprocess.TimeoutExpired:
                st.error("⏰ Lỗi: Quá thời gian chờ (Timeout 30 phút)")
            except Exception as e:
                st.error(f"❌ Lỗi hệ thống: {str(e)}")
    
    # ===== Delete Finance Data Section =====
    st.markdown("---")
    st.subheader("🗑️ Xóa Dữ Liệu Báo Cáo Tài Chính")
    
    # Load scraped tickers from sheets
    try:
        income_df = fetch_financial_sheet("income")
        scraped_tickers = []
        if not income_df.empty and 'ticker' in income_df.columns:
            scraped_tickers = sorted(income_df['ticker'].dropna().unique().tolist())
    except:
        scraped_tickers = []
    
    if scraped_tickers:
        fin_delete_tickers = st.multiselect(
            "Chọn mã cần xóa dữ liệu",
            options=scraped_tickers,
            help="Chọn các mã muốn xóa khỏi báo cáo tài chính",
            key="fin_delete_tickers"
        )
        
        if st.button("🗑️ Xóa Dữ Liệu Đã Chọn", type="secondary", key="btn_fin_delete"):
            if fin_delete_tickers:
                with st.spinner("Đang xóa dữ liệu..."):
                    try:
                        creds = get_google_credentials()
                        client = gspread.authorize(creds)
                        spreadsheet = client.open("Stock_Data_Storage")
                        
                        deleted_count = 0
                        for sheet_name in ["income", "balance", "cashflow"]:
                            try:
                                ws = spreadsheet.worksheet(sheet_name)
                                all_data = ws.get_all_records()
                                df = pd.DataFrame(all_data)
                                
                                if not df.empty and 'ticker' in df.columns:
                                    original_count = len(df)
                                    df = df[~df['ticker'].isin(fin_delete_tickers)]
                                    deleted_count += original_count - len(df)
                                    
                                    # Write back
                                    ws.clear()
                                    ws.update([df.columns.values.tolist()] + df.values.tolist())
                            except Exception as e:
                                st.warning(f"Lỗi xóa từ {sheet_name}: {str(e)}")
                        
                        st.success(f"✅ Đã xóa {deleted_count} bản ghi của {len(fin_delete_tickers)} mã!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Lỗi: {str(e)}")
            else:
                st.warning("Vui lòng chọn ít nhất một mã để xóa")
    else:
        st.info("Chưa có dữ liệu đã cào. Vui lòng cào dữ liệu trước.")


elif page == "💸 Giao dịch mua-bán":
    render_money_flow_tab()

elif page == "🔍 Lọc Cổ Phiếu":
    render_financial_screening_tab()

elif page == "📋 Danh Sách Theo Dõi":
    render_watchlist_tab()

elif page == "🌐 Khuyến Nghị":

    st.markdown('<div class="main-header">🎯 Khuyến Nghị Đầu Tư</div>', unsafe_allow_html=True)
    
    st.warning("⚠️ **TUYÊN BỐ MIỄN TRỪ TRÁCH NHIỆM:** Đây chỉ là hệ thống hỗ trợ ra quyết định dựa trên dữ liệu lịch sử. Kết quả không đảm bảo lợi nhuận trong tương lai. Bạn hoàn toàn chịu trách nhiệm về các quyết định đầu tư của mình.")
    
    # Tabs for different analysis types
    tab_quick, tab_ai, tab_methodology = st.tabs(["📊 Điểm Số Nhanh", "🤖 Phân Tích AI Chi Tiết", "📚 Phương Pháp"])
    
    # ===== TAB 1: Quick Score (Original functionality) =====
    with tab_quick:
        st.subheader("📊 Đánh Giá Nhanh")
        
        tickers = fetch_ticker_list()
        rec_symbol = st.selectbox("Chọn mã cổ phiếu", options=tickers, key="rec_symbol_quick", index=0)
        
        if rec_symbol:
            with st.spinner(f"Đang phân tích {rec_symbol}..."):
                # 1. Technical Score
                end_date = datetime.now()
                start_date = end_date - timedelta(days=60)
                df = fetch_stock_data(rec_symbol, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
                
                tech_score = 50
                tech_reasons = []
                
                if not df.empty and len(df) > 20:
                    # RSI check
                    delta = df['close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rs = gain / loss
                    rsi = 100 - (100 / (1 + rs)).iloc[-1]
                    
                    if rsi < 30: 
                        tech_score += 20
                        tech_reasons.append("✅ RSI Quá bán (Overbought) - Cơ hội hồi phục")
                    elif rsi > 70:
                        tech_score -= 20
                        tech_reasons.append("❌ RSI Quá mua (Oversold) - Rủi ro điều chỉnh")
                    
                    # MA check
                    sma20 = df['close'].rolling(window=20).mean().iloc[-1]
                    if df['close'].iloc[-1] > sma20:
                        tech_score += 15
                        tech_reasons.append("✅ Giá nằm trên MA20 - Xu hướng ngắn hạn tốt")
                    else:
                        tech_score -= 10
                        tech_reasons.append("❌ Giá nằm dưới MA20 - Xu hướng ngắn hạn yếu")
                
                # 2. Fundamental Score
                fund_score = 50
                fund_reasons = []
                income_df = fetch_financial_sheet("income")
                if not income_df.empty:
                    ticker_income = income_df[income_df['ticker'].astype(str).str.upper() == rec_symbol]
                    if not ticker_income.empty and len(ticker_income) >= 2:
                        current = ticker_income.iloc[-1]
                        prev = ticker_income.iloc[-2]
                        
                        if 'revenue' in current and 'revenue' in prev:
                            try:
                                rev_current = float(current['revenue'])
                                rev_prev = float(prev['revenue'])
                                if rev_prev != 0:
                                    rev_growth = (rev_current - rev_prev) / rev_prev
                                    if rev_growth > 0.1:
                                        fund_score += 15
                                        fund_reasons.append(f"✅ Doanh thu tăng trưởng mạnh (+{rev_growth:.1%})")
                                    elif rev_growth < 0:
                                        fund_score -= 10
                                        fund_reasons.append(f"❌ Doanh thu sụt giảm ({rev_growth:.1%})")
                            except:
                                pass
                        
                        if 'net_income' in current and 'net_income' in prev:
                            try:
                                profit_current = float(current['net_income'])
                                profit_prev = float(prev['net_income'])
                                if profit_prev != 0:
                                    profit_growth = (profit_current - profit_prev) / profit_prev
                                    if profit_growth > 0.1:
                                        fund_score += 15
                                        fund_reasons.append(f"✅ Lợi nhuận tăng trưởng tốt (+{profit_growth:.1%})")
                            except:
                                pass

                # Final Calculation
                final_score = (tech_score * 0.4 + fund_score * 0.6)
                
                # Display
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.metric("TỔNG ĐIỂM", f"{final_score:.1f}/100")
                    if final_score > 70:
                        st.success("💪 TÍN HIỆU: MUA")
                    elif final_score < 40:
                        st.error("📉 TÍN HIỆU: BÁN")
                    else:
                        st.warning("⚖️ TÍN HIỆU: THEO DÕI")
                
                with col2:
                    st.subheader("Chi tiết đánh giá")
                    for r in tech_reasons + fund_reasons:
                        st.write(r)
    
    # ===== TAB 2: AI Analysis =====
    with tab_ai:
        st.subheader("🤖 Phân Tích Kỹ Thuật Bằng AI")
        st.info("💡 Tạo báo cáo phân tích kỹ thuật chi tiết bằng AI. Báo cáo sẽ được lưu vào Google Sheets.")
        
        # Configuration row
        col_ticker, col_custom, col_days, col_provider = st.columns([2, 1.5, 1, 1])
        
        with col_ticker:
            # Get watchlist from watchlist_flow sheet
            watchlist_tickers = []
            try:
                flow_watchlist = get_watchlist('flow')
                if not flow_watchlist.empty and 'ticker' in flow_watchlist.columns:
                    watchlist_tickers = flow_watchlist['ticker'].tolist()
            except:
                pass
            
            if watchlist_tickers:
                ai_ticker_select = st.selectbox(
                    "Chọn từ danh mục", 
                    options=[""] + watchlist_tickers, 
                    key="ai_ticker_select",
                    help="Chọn mã từ danh sách theo dõi"
                )
            else:
                ai_ticker_select = ""
                st.info("Chưa có mã trong danh mục")
        
        with col_custom:
            ai_ticker_custom = st.text_input(
                "Hoặc nhập mã", 
                placeholder="VD: ACB",
                key="ai_ticker_custom",
                help="Nhập mã bất kỳ (ưu tiên nếu có)"
            ).upper().strip()
        
        # Priority: custom input > select from watchlist
        ai_ticker = ai_ticker_custom if ai_ticker_custom else ai_ticker_select
        
        with col_days:
            ai_days = st.number_input(
                "Số ngày dữ liệu", 
                min_value=60, 
                max_value=1000, 
                value=int(os.getenv('AI_ANALYSIS_DAYS', 400)),
                step=50,
                help="Số ngày dữ liệu lịch sử để phân tích (khuyến nghị: 400)"
            )
        
        with col_provider:
            ai_provider = st.selectbox(
                "AI Provider",
                options=["gemini", "openai", "anthropic"],
                index=0,
                help="Chọn nhà cung cấp AI (Gemini mặc định)"
            )
        
        # Trading parameters (collapsible)
        with st.expander("⚙️ Tham Số Giao Dịch", expanded=False):
            param_col1, param_col2, param_col3 = st.columns(3)
            with param_col1:
                tp1_pct = st.number_input("TP1 (%)", min_value=1.0, max_value=50.0, 
                    value=float(os.getenv('TP1_PCT', 5)), step=1.0, key="ai_tp1")
                tp2_pct = st.number_input("TP2 (%)", min_value=1.0, max_value=50.0, 
                    value=float(os.getenv('TP2_PCT', 10)), step=1.0, key="ai_tp2")
            with param_col2:
                tp3_pct = st.number_input("TP3 (%)", min_value=1.0, max_value=50.0, 
                    value=float(os.getenv('TP3_PCT', 15)), step=1.0, key="ai_tp3")
                sl_pct = st.number_input("Stop Loss (%)", min_value=1.0, max_value=20.0, 
                    value=float(os.getenv('SL_PCT', 6)), step=0.5, key="ai_sl",
                    help="% cắt lỗ tính từ giá Entry (mặc định 6%)")
            with param_col3:
                sl_buffer_pct = st.number_input("SL Buffer (%)", min_value=1.0, max_value=10.0, 
                    value=float(os.getenv('SL_BUFFER_PCT', 3)), step=0.5, key="ai_sl_buffer",
                    help="Buffer % dưới MA50/Support khi tính SL")
                st.caption(f"**Tóm tắt:** TP: +{tp1_pct}%/+{tp2_pct}%/+{tp3_pct}%, SL: -{sl_pct}%")
        
        # Check API key
        api_key_env = {
            'gemini': 'GEMINI_API_KEY',
            'openai': 'OPENAI_API_KEY', 
            'anthropic': 'ANTHROPIC_API_KEY'
        }
        
        has_api_key = os.getenv(api_key_env.get(ai_provider, '')) not in [None, '', 'your_gemini_api_key_here', 'your_openai_api_key_here', 'your_anthropic_api_key_here']
        
        if not has_api_key:
            st.error(f"⚠️ Thiếu API key cho {ai_provider.upper()}. Vui lòng thêm `{api_key_env[ai_provider]}` vào file `.env`")
            st.markdown(f"""
            **Hướng dẫn lấy API key:**
            - **Gemini**: https://aistudio.google.com/app/apikey
            - **OpenAI**: https://platform.openai.com/api-keys  
            - **Anthropic**: https://console.anthropic.com/
            """)
        
        # Analyze button
        col_btn, col_save = st.columns([2, 1])
        with col_btn:
            analyze_btn = st.button("🔍 Phân Tích Bằng AI", type="primary", use_container_width=True, disabled=not has_api_key)
        with col_save:
            save_to_sheets = st.checkbox("💾 Lưu báo cáo", value=True, help="Lưu báo cáo vào Google Sheets")
        
        if analyze_btn and ai_ticker:
            with st.spinner(f"🤖 Đang phân tích {ai_ticker} với {ai_provider.upper()}... (có thể mất 30-60 giây)"):
                try:
                    # 1. Fetch data DIRECTLY from vnstock API (faster, no GSheets needed)
                    from vnstock import Vnstock
                    stock = Vnstock().stock(symbol=ai_ticker, source='VCI')
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=ai_days + 50)  # Extra buffer for MA200
                    
                    df = stock.quote.history(
                        start=start_date.strftime("%Y-%m-%d"),
                        end=end_date.strftime("%Y-%m-%d"),
                        interval='1D'
                    )
                    
                    if df is None or df.empty:
                        st.error(f"❌ Không có dữ liệu cho {ai_ticker} từ vnstock API.")
                    else:
                        # Rename columns to match expected format
                        df.columns = df.columns.str.lower()
                        if 'time' in df.columns:
                            df = df.rename(columns={'time': 'date'})
                            df.set_index('date', inplace=True)
                        
                        # 2. Calculate technical indicators
                        from technical_analysis import TechnicalAnalyzer
                        analyzer = TechnicalAnalyzer(
                            df, days=ai_days,
                            tp1_pct=tp1_pct, tp2_pct=tp2_pct, tp3_pct=tp3_pct,
                            sl_pct=sl_pct, sl_buffer_pct=sl_buffer_pct
                        )
                        indicators = analyzer.get_analysis_summary()
                        
                        # 2.5 Fetch Fundamental Data (GSheets first, then vnstock)
                        from technical_analysis import fetch_fundamental_data
                        fundamental = fetch_fundamental_data(ai_ticker)
                        
                        # Merge fundamental data into indicators
                        indicators['fundamental_has_data'] = fundamental.get('has_data', False)
                        indicators['fundamental_source'] = fundamental.get('source', 'N/A')
                        indicators['fundamental_eps'] = fundamental.get('eps')
                        indicators['fundamental_pe'] = fundamental.get('pe')
                        indicators['fundamental_pb'] = fundamental.get('pb')
                        indicators['fundamental_roe'] = fundamental.get('roe')
                        indicators['fundamental_revenue'] = fundamental.get('revenue')
                        indicators['fundamental_net_income'] = fundamental.get('net_income')
                        indicators['fundamental_revenue_growth'] = fundamental.get('revenue_growth')
                        indicators['fundamental_profit_growth'] = fundamental.get('profit_growth')
                        
                        # 3. Quick summary before AI
                        st.markdown("### 📊 Tóm Tắt Chỉ Báo")
                        col_ind1, col_ind2, col_ind3, col_ind4 = st.columns(4)
                        with col_ind1:
                            st.metric("Giá hiện tại", f"{indicators['current_price']:,.1f}")
                        with col_ind2:
                            rsi_color = "normal" if 30 < indicators['rsi'] < 70 else "inverse"
                            st.metric("RSI (14)", f"{indicators['rsi']:.1f}")
                        with col_ind3:
                            st.metric("Volume Ratio", f"{indicators['volume_ratio']:.2f}x")
                        with col_ind4:
                            trend_emoji = "📈" if "uptrend" in indicators['trend'] else "📉" if "downtrend" in indicators['trend'] else "➡️"
                            st.metric("Xu hướng", f"{trend_emoji} {indicators['trend']}")
                        
                        # Calculate SL % from entry
                        entry_price = indicators['entry_low']
                        sl_price = indicators['stop_loss']
                        sl_percent = ((entry_price - sl_price) / entry_price * 100) if entry_price > 0 else 0
                        
                        col_lvl1, col_lvl2, col_lvl3, col_lvl4 = st.columns(4)
                        with col_lvl1:
                            st.metric("Hỗ trợ", f"{indicators['support']:,.1f}")
                        with col_lvl2:
                            st.metric("Kháng cự", f"{indicators['resistance']:,.1f}")
                        with col_lvl3:
                            st.metric("Stop Loss", f"{sl_price:,.1f} (-{sl_percent:.1f}%)")
                        with col_lvl4:
                            rec_color = "✅" if "MUA" in indicators['recommendation'] else "❌" if "BÁN" in indicators['recommendation'] else "⚖️"
                            st.metric("Khuyến nghị", f"{rec_color} {indicators['recommendation']}")
                        
                        st.markdown("---")
                        
                        # 4. Generate AI report
                        from ai_analyzer import AIAnalyzer
                        ai = AIAnalyzer(provider=ai_provider)
                        report = ai.generate_report(ai_ticker, indicators)
                        
                        # 5. Display report
                        st.markdown("### 📝 Báo Cáo Phân Tích Chi Tiết")
                        st.markdown(report)
                        
                        # 6. Save to sheets
                        if save_to_sheets:
                            if ai.save_report_to_sheets(ai_ticker, report, indicators):
                                st.success("✅ Đã lưu báo cáo vào Google Sheets (sheet: ai_reports)")
                            else:
                                st.warning("⚠️ Không thể lưu báo cáo vào Sheets")
                        
                        # 7. Download option
                        st.download_button(
                            label="📥 Tải Báo Cáo (TXT)",
                            data=report,
                            file_name=f"analysis_{ai_ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                            mime="text/plain"
                        )
                        
                except ImportError as e:
                    st.error(f"❌ Thiếu thư viện: {str(e)}")
                    st.info("💡 Chạy: `pip install google-generativeai openai anthropic`")
                except Exception as e:
                    st.error(f"❌ Lỗi phân tích: {str(e)}")
                    import traceback
                    with st.expander("Chi tiết lỗi"):
                        st.code(traceback.format_exc())
        
        # Show saved reports
        st.markdown("---")
        st.subheader("📚 Báo Cáo Đã Lưu")
        
        try:
            from ai_analyzer import AIAnalyzer
            ai = AIAnalyzer(provider='gemini')  # Just for reading, doesn't need valid key
            saved_reports = ai.get_saved_reports(limit=5)
            
            if saved_reports:
                for report in saved_reports:
                    with st.expander(f"📄 {report.get('ticker', 'N/A')} - {report.get('timestamp', 'N/A')} - {report.get('recommendation', '')}"):
                        col_r1, col_r2, col_r3 = st.columns(3)
                        with col_r1:
                            st.write(f"**Entry:** {report.get('entry_zone', 'N/A')}")
                        with col_r2:
                            st.write(f"**TP:** {report.get('tp1', 0)} / {report.get('tp2', 0)} / {report.get('tp3', 0)}")
                        with col_r3:
                            st.write(f"**SL:** {report.get('stop_loss', 'N/A')}")
                        
                        if report.get('report'):
                            st.markdown(report['report'][:2000] + "..." if len(report.get('report', '')) > 2000 else report.get('report', ''))
            else:
                st.info("📝 Chưa có báo cáo nào được lưu. Phân tích một mã để bắt đầu!")
        except Exception as e:
            st.info("📝 Chưa có báo cáo nào được lưu.")
    
    # ===== TAB 3: Methodology =====
    with tab_methodology:
        st.subheader("📚 Phương Pháp Phân Tích & Thuật Toán Khuyến Nghị")
        
        st.markdown("""
        ### 🎯 Tổng Quan
        Hệ thống sử dụng 2 phương pháp phân tích song song:
        1. **Điểm Số Nhanh**: Thuật toán tính điểm tự động
        2. **Phân Tích AI**: Sử dụng AI để tạo báo cáo chi tiết
        
        ---
        
        ### 📊 TAB 1: ĐIỂM SỐ NHANH
        
        #### Các chỉ báo kỹ thuật sử dụng:
        
        | Chỉ báo | Công thức | Ý nghĩa |
        |---------|-----------|---------|
        | **MA20/50/200** | SMA của giá đóng cửa | Xu hướng ngắn/trung/dài hạn |
        | **RSI (14)** | 100 - 100/(1 + RS) | Quá mua (>70) / Quá bán (<30) |
        | **MACD** | EMA12 - EMA26 | Động lượng xu hướng |
        | **Volume Ratio** | Volume / SMA20(Volume) | Dòng tiền mạnh/yếu |
        
        #### Cách tính điểm khuyến nghị:
        
        ```
        Base Score = 50 điểm
        
        ➕ Xu hướng:
          +20: Strong Uptrend (MA20 > MA50 > MA200, tất cả dốc lên)
          +10: Uptrend
          -10: Downtrend  
          -20: Strong Downtrend
        
        ➕ Sắp xếp MA (Golden Alignment):
          +15: Giá > MA20 > MA50 > MA200 (Golden)
          -15: Giá < MA20 < MA50 < MA200 (Death)
        
        ➕ RSI:
          +10: 40 < RSI < 70 (Vùng khỏe mạnh)
          +5: RSI < 30 (Quá bán - tiềm năng đảo chiều)
          -5: RSI > 70 (Quá mua - cẩn trọng)
        
        ➕ MACD Histogram:
          +5: Histogram > 0 (Momentum tăng)
          -5: Histogram < 0 (Momentum giảm)
        
        ➕ Volume:
          +10: Volume Ratio > 1.5 kết hợp Uptrend
        ```
        
        #### Khuyến nghị dựa trên điểm:
        - **≥70 điểm**: MUA / TÍCH LŨY 🟢
        - **50-69 điểm**: THEO DÕI 🟡
        - **<50 điểm**: BÁN / HẠ TỶ TRỌNG 🔴
        
        ---
        
        ### 🤖 TAB 2: PHÂN TÍCH AI CHI TIẾT
        
        #### Dữ liệu đầu vào cho AI:
        
        | Loại | Dữ liệu |
        |------|---------|
        | **Giá** | OHLCV 400 ngày (có thể điều chỉnh) |
        | **MA** | MA20, MA50, MA200, Alignment, Slope 60d |
        | **Momentum** | RSI, MACD, Signal, Histogram |
        | **Volume** | Volume Ratio, Volume Spike |
        | **Trend** | Xu hướng, Pha Wyckoff |
        | **Levels** | Support, Resistance |
        | **Trading** | Entry Zone, TP1/2/3, Stop Loss |
        | **Fundamental** 🆕 | EPS, P/E, P/B, ROE, Doanh thu, Lợi nhuận, Tăng trưởng |
        
        #### Công thức tính các mức giao dịch:
        
        ```python
        # Entry Zone
        Entry Low = max(MA20 × 0.98, Support)  # Uptrend
        Entry Low = Support                   # Sideways/Downtrend
        
        # Take Profit (tuỳ chỉnh được)
        TP1 = Entry × (1 + TP1_PCT%)  # Mặc định +5%
        TP2 = Entry × (1 + TP2_PCT%)  # Mặc định +10%
        TP3 = Entry × (1 + TP3_PCT%)  # Mặc định +15%
        
        # Stop Loss (tuỳ chỉnh được)
        SL = Entry × (1 - SL_PCT%)    # Mặc định -6%
        ```
        
        #### AI Prompt Structure:
        AI được cung cấp toàn bộ dữ liệu trên và yêu cầu tạo báo cáo 6 phần:
        1. **Xu hướng & Cấu trúc giá** - Golden Alignment, Wyckoff Phase
        2. **Price Action** - Hành động giá, Pattern nến
        3. **Chỉ báo kỹ thuật** - RSI, MACD, Volume
        4. **Vùng giá quan trọng** - Support, Resistance
        5. **Chiến lược giao dịch** - Entry, TP, SL (CHỈ LONG, không Short)
        6. **Rủi ro** - Các điều kiện vô hiệu hóa
        
        ---
        
        ### ⚙️ Tuỳ Chỉnh Tham Số
        
        Có thể điều chỉnh qua file `.env` hoặc UI:
        
        | Tham số | Mặc định | Mô tả |
        |---------|----------|-------|
        | `TP1_PCT` | 5% | Take Profit 1 |
        | `TP2_PCT` | 10% | Take Profit 2 |
        | `TP3_PCT` | 15% | Take Profit 3 |
        | `SL_PCT` | 6% | Stop Loss |
        | `AI_ANALYSIS_DAYS` | 400 | Số ngày dữ liệu |
        | `AI_DEFAULT_PROVIDER` | gemini | AI provider |
        
        ---
        
        ### ⚠️ Lưu Ý Quan Trọng
        
        1. **Chỉ phân tích LONG** - Không có short vì thị trường VN chưa cho phép
        2. **Dữ liệu lịch sử** - Kết quả quá khứ không đảm bảo tương lai
        3. **Rủi ro thị trường** - Luôn quản lý rủi ro và đa dạng hóa danh mục
        4. **Kiểm tra kỹ** - Đây chỉ là công cụ hỗ trợ, không phải khuyến nghị đầu tư
        """)


elif page == "🔬 Backtest":
    st.markdown('<div class="main-header">🔬 Backtest Chiến Lược Breakout</div>', unsafe_allow_html=True)
    
    st.info("📊 **Chiến lược Breakout**: Mua khi giá vượt đỉnh 20 ngày + khối lượng tăng đột biến (>2x). Thoát khi lãi 10%, lỗ 5%, hoặc giữ tối đa 20 ngày.")
    
    # Tabs for Single vs Batch backtest
    tab1, tab2 = st.tabs(["📈 Backtest Đơn", "📊 Backtest Danh Mục"])
    
    with tab1:
        st.subheader("Backtest 1 mã")
        # Configuration
        col1, col2, col3 = st.columns(3)
        with col1:
            tickers = fetch_ticker_list()
            selected_ticker = st.selectbox("Chọn mã để backtest", options=tickers, index=0 if "VNM" not in tickers else tickers.index("VNM"))
        with col2:
            period_type = st.selectbox("Đơn vị thời gian", options=["Tháng", "Năm"], index=0)
            if period_type == "Tháng":
                period_value = st.selectbox("Khoảng thời gian", options=[3, 6, 9, 12, 18, 24], index=1)
                period_days = period_value * 30
            else:
                period_value = st.selectbox("Khoảng thời gian", options=[1, 2, 3, 5], index=1)
                period_days = period_value * 365
        with col3:
            lookback_days = st.number_input("Lookback (ngày)", min_value=10, max_value=50, value=20)
        
        col4, col5, col6 = st.columns(3)
        with col4:
            take_profit = st.number_input("Take Profit (%)", min_value=1.0, max_value=50.0, value=10.0, step=1.0) / 100
        with col5:
            stop_loss = st.number_input("Stop Loss (%)", min_value=1.0, max_value=20.0, value=5.0, step=1.0) / 100
        with col6:
            max_hold = st.number_input("Max Hold (ngày)", min_value=5, max_value=60, value=20)
        
        if st.button("🚀 Chạy Backtest", type="primary", key="single_backtest"):
            period_label = f"{period_value} {period_type.lower()}"
            with st.spinner(f"Đang backtest {selected_ticker} trong {period_label}..."):
                try:
                    metrics = None  # Initialize metrics
                    
                    # Fetch data from Google Sheets instead of API
                    price_df = fetch_financial_sheet("price")
                    
                    if price_df.empty:
                        st.error("❌ Không có dữ liệu giá trong Google Sheets. Vui lòng chạy `price.py` trước.")
                    else:
                        # Filter data for selected ticker
                        price_df.columns = price_df.columns.str.lower().str.replace(' ', '_')
                        ticker_data = price_df[price_df['ticker'].astype(str).str.upper() == selected_ticker].copy()
                        
                        if ticker_data.empty:
                            st.error(f"❌ Không có dữ liệu cho {selected_ticker}. Chạy `price.py` để cập nhật.")
                        else:
                            # Prepare data for backtest
                            end_date = datetime.now()
                            start_date = end_date - timedelta(days=period_days)
                            
                            # Convert date column
                            if 'date' in ticker_data.columns:
                                ticker_data['date'] = pd.to_datetime(ticker_data['date'], errors='coerce')
                                ticker_data = ticker_data[(ticker_data['date'] >= start_date) & (ticker_data['date'] <= end_date)]
                                ticker_data = ticker_data.sort_values('date')
                                ticker_data.set_index('date', inplace=True)
                            
                            # Run backtest with local data
                            from backtest_breakout import backtest_with_dataframe
                            
                            metrics = backtest_with_dataframe(
                                ticker_data,
                                selected_ticker,
                                lookback=lookback_days,
                                take_profit=take_profit,
                                stop_loss=stop_loss,
                                max_hold_days=max_hold
                                )
                    
                    if metrics and metrics['total_trades'] > 0:
                        st.success(f"✅ Hoàn tất backtest {selected_ticker}")
                        
                        # Metrics display
                        st.subheader("📊 Kết Quả Backtest")
                        col1, col2, col3, col4, col5 = st.columns(5)
                        
                        with col1:
                            st.metric("Tổng Giao Dịch", metrics['total_trades'])
                        with col2:
                            st.metric("Win Rate", f"{metrics['win_rate']:.1f}%")
                        with col3:
                            color = "normal" if metrics['total_return'] >= 0 else "inverse"
                            st.metric("Tổng Lợi Nhuận", f"{metrics['total_return']:.2f}%", delta=None)
                        with col4:
                            st.metric("Avg Gain", f"{metrics['avg_gain']:.2f}%")
                        with col5:
                            st.metric("Avg Loss", f"{metrics['avg_loss']:.2f}%")
                        
                        col6, col7, col8, col9 = st.columns(4)
                        with col6:
                            st.metric("Best Trade", f"{metrics['best_trade']:.2f}%")
                        with col7:
                            st.metric("Worst Trade", f"{metrics['worst_trade']:.2f}%")
                        with col8:
                            st.metric("Max Drawdown", f"{metrics['max_drawdown']:.2f}%")
                        with col9:
                            st.metric("Avg Hold", f"{metrics['avg_hold_days']:.1f} days")
                        
                        # Visualization
                        st.markdown("---")
                        st.subheader("📈 Phân Tích Chi Tiết")
                        
                        col_a, col_b = st.columns(2)
                        
                        with col_a:
                            # Win/Loss pie chart
                            fig_pie = go.Figure(data=[go.Pie(
                                labels=['Thắng', 'Thua'],
                                values=[metrics['winning_trades'], metrics['losing_trades']],
                                marker_colors=['#26a69a', '#ef5350'],
                                hole=0.4
                            )])
                            fig_pie.update_layout(title="Tỷ Lệ Thắng/Thua", height=300)
                            st.plotly_chart(fig_pie, use_container_width=True)
                        
                        with col_b:
                            # Performance bar chart
                            fig_bar = go.Figure()
                            fig_bar.add_trace(go.Bar(
                                x=['Avg Gain', 'Avg Loss', 'Total Return'],
                                y=[metrics['avg_gain'], metrics['avg_loss'], metrics['total_return']],
                                marker_color=['#26a69a', '#ef5350', '#4ECDC4']
                            ))
                            fig_bar.update_layout(title="Hiệu Suất (%)", height=300, yaxis_title="%")
                            st.plotly_chart(fig_bar, use_container_width=True)
                        
                        # Interpretation
                        st.markdown("---")
                        st.subheader("💡 Đánh Giá")
                        
                        if metrics['win_rate'] >= 60:
                            st.success(f"✅ **Win rate cao ({metrics['win_rate']:.1f}%)** - Chiến lược hoạt động tốt với {selected_ticker}")
                        elif metrics['win_rate'] >= 45:
                            st.info(f"⚖️ **Win rate trung bình ({metrics['win_rate']:.1f}%)** - Chiến lược có thể cân nhắc")
                        else:
                            st.warning(f"⚠️ **Win rate thấp ({metrics['win_rate']:.1f}%)** - Chiến lược chưa phù hợp với {selected_ticker}")
                        
                        if metrics['total_return'] > 0:
                            st.success(f"💰 **Lợi nhuận tích lũy: +{metrics['total_return']:.2f}%**")
                        else:
                            st.error(f"📉 **Lỗ tích lũy: {metrics['total_return']:.2f}%**")
                        
                        # Risk/Reward
                        if metrics['avg_gain'] > 0 and abs(metrics['avg_loss']) > 0:
                            risk_reward = metrics['avg_gain'] / abs(metrics['avg_loss'])
                            st.metric("Risk/Reward Ratio", f"{risk_reward:.2f}")
                            if risk_reward >= 2:
                                st.success("✅ Risk/Reward tốt (≥2:1)")
                            elif risk_reward >= 1.5:
                                st.info("⚖️ Risk/Reward chấp nhận được")
                            else:
                                st.warning("⚠️ Risk/Reward thấp - Cân nhắc điều chỉnh tham số")
                    
                    elif metrics and metrics['total_trades'] == 0:
                        if 'error' in metrics:
                            st.error(f"❌ Lỗi: {metrics['error']}")
                            st.info("💡 **Nguyên nhân có thể:**\n"
                                   "- API vnstock tạm thời không khả dụng\n"
                                   "- Mã chứng khoán không hợp lệ\n"
                                   "- Không đủ dữ liệu lịch sử\n"
                                   "- Kết nối mạng bị gián đoạn")
                        else:
                            st.warning(f"⚠️ Không có tín hiệu breakout nào trong {period_label} qua cho {selected_ticker}")
                    else:
                        st.error(f"❌ Không thể backtest {selected_ticker}. Kiểm tra dữ liệu.")
                        st.info("💡 **Thử:**\n"
                               "- Chọn mã khác (VD: VNM, HPG, FPT)\n"
                               "- Giảm khoảng thời gian xuống 1 năm\n"
                               "- Kiểm tra kết nối internet")
                
                except Exception as e:
                    st.error("❌ Lỗi backtest: ")
                    import traceback
    with tab2:
        st.subheader("Backtest Danh Mục Khuyến Nghị")
        
        # Watchlist management
        st.markdown("### 📋 Quản Lý Danh Mục")
        
        # Load watchlist from Google Sheets
        try:
            spreadsheet = get_spreadsheet()
            
            # Try to get watchlist sheet, create if not exists
            try:
                watchlist_ws = spreadsheet.worksheet("watchlist")
                watchlist_tickers = watchlist_ws.col_values(1)[1:]  # Skip header
            except:
                # Create watchlist sheet if doesn't exist
                watchlist_ws = spreadsheet.add_worksheet(title="watchlist", rows=100, cols=5)
                watchlist_ws.update('A1:E1', [['ticker', 'added_date', 'note', 'last_backtest', 'win_rate']])
                watchlist_tickers = []
            
            col_a, col_b = st.columns([2, 1])
            
            with col_a:
                # Add ticker to watchlist
                all_tickers = fetch_ticker_list()
                new_ticker = st.selectbox("Thêm mã vào danh mục", options=[t for t in all_tickers if t not in watchlist_tickers], key="add_watchlist")
                note = st.text_input("Ghi chú (tùy chọn)", key="watchlist_note")
                
                if st.button("➕ Thêm vào danh mục", type="primary"):
                    if new_ticker:
                        watchlist_ws.append_row([new_ticker, datetime.now().strftime("%Y-%m-%d"), note, "", ""])
                        st.success(f"✅ Đã thêm {new_ticker} vào danh mục!")
                        st.rerun()
            
            with col_b:
                st.metric("Tổng số mã", len(watchlist_tickers))
                if watchlist_tickers:
                    st.info(f"📊 {', '.join(watchlist_tickers[:5])}{' ...' if len(watchlist_tickers) > 5 else ''}")
            
            # Display watchlist
            if watchlist_tickers:
                st.markdown("---")
                st.markdown("### 📊 Danh Sách Mã")
                
                # Get full watchlist data
                watchlist_data = watchlist_ws.get_all_records()
                watchlist_df = pd.DataFrame(watchlist_data)
                
                # Display with option to remove
                for idx, row in watchlist_df.iterrows():
                    col1, col2, col3, col4 = st.columns([1, 2, 2, 1])
                    with col1:
                        st.write(f"**{row['ticker']}**")
                    with col2:
                        st.write(f"📅 {row['added_date']}")
                    with col3:
                        st.write(f"📝 {row['note']}")
                    with col4:
                        if st.button("🗑️", key=f"remove_{row['ticker']}"):
                            # Remove from sheet
                            cell = watchlist_ws.find(row['ticker'])
                            watchlist_ws.delete_rows(cell.row)
                            st.success(f"Đã xóa {row['ticker']}")
                            st.rerun()
                
                st.markdown("---")
                
                # Batch backtest configuration
                st.markdown("### 🚀 Chạy Backtest Hàng Loạt")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    batch_period_type = st.selectbox("Đơn vị thời gian", options=["Tháng", "Năm"], index=0, key="batch_period_type")
                    if batch_period_type == "Tháng":
                        batch_period_value = st.selectbox("Khoảng thời gian", options=[3, 6, 9, 12, 18, 24], index=1, key="batch_period")
                        batch_period_days = batch_period_value * 30
                    else:
                        batch_period_value = st.selectbox("Khoảng thời gian", options=[1, 2, 3, 5], index=1, key="batch_period_year")
                        batch_period_days = batch_period_value * 365
                with col2:
                    batch_lookback = st.number_input("Lookback", min_value=10, max_value=50, value=20, key="batch_lookback")
                with col3:
                    batch_tp = st.number_input("Take Profit (%)", min_value=1.0, max_value=50.0, value=10.0, key="batch_tp") / 100
                
                col4, col5 = st.columns(2)
                with col4:
                    batch_sl = st.number_input("Stop Loss (%)", min_value=1.0, max_value=20.0, value=5.0, key="batch_sl") / 100
                with col5:
                    batch_hold = st.number_input("Max Hold", min_value=5, max_value=60, value=20, key="batch_hold")
                
                if st.button("🚀 Backtest Tất Cả", type="primary", key="batch_backtest"):
                    results = []
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for idx, ticker in enumerate(watchlist_tickers):
                        status_text.text(f"Đang backtest {ticker} ({idx+1}/{len(watchlist_tickers)})...")
                        progress_bar.progress((idx + 1) / len(watchlist_tickers))
                        
                        try:
                            # Fetch data
                            price_df = fetch_financial_sheet("price")
                            if not price_df.empty:
                                price_df.columns = price_df.columns.str.lower().str.replace(' ', '_')
                                ticker_data = price_df[price_df['ticker'].astype(str).str.upper() == ticker].copy()
                                
                                if not ticker_data.empty:
                                    end_date = datetime.now()
                                    start_date = end_date - timedelta(days=batch_period_days)
                                    
                                    if 'date' in ticker_data.columns:
                                        ticker_data['date'] = pd.to_datetime(ticker_data['date'], errors='coerce')
                                        ticker_data = ticker_data[(ticker_data['date'] >= start_date) & (ticker_data['date'] <= end_date)]
                                        ticker_data = ticker_data.sort_values('date')
                                        ticker_data.set_index('date', inplace=True)
                                    
                                    from backtest_breakout import backtest_with_dataframe
                                    
                                    metrics = backtest_with_dataframe(
                                        ticker_data,
                                        ticker,
                                        lookback=batch_lookback,
                                        take_profit=batch_tp,
                                        stop_loss=batch_sl,
                                        max_hold_days=batch_hold
                                    )
                                    
                                    if metrics:
                                        results.append(metrics)
                        except Exception as e:
                            st.warning(f"⚠️ Lỗi backtest {ticker}: ")
                    
                    progress_bar.empty()
                    status_text.empty()
                    
                    if results:
                        st.success(f"✅ Hoàn tất backtest {len(results)}/{len(watchlist_tickers)} mã!")
                        
                        # Display results table
                        results_df = pd.DataFrame(results)
                        results_df = results_df.sort_values('win_rate', ascending=False)
                        
                        st.markdown("### 📊 Kết Quả Backtest")
                        
                        # Summary metrics
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Avg Win Rate", f"{results_df['win_rate'].mean():.1f}%")
                        with col2:
                            st.metric("Best Win Rate", f"{results_df['win_rate'].max():.1f}%")
                        with col3:
                            profitable = len(results_df[results_df['total_return'] > 0])
                            st.metric("Mã Có Lãi", f"{profitable}/{len(results_df)}")
                        with col4:
                            st.metric("Avg Total Return", f"{results_df['total_return'].mean():.2f}%")
                        
                        # Results table
                        st.dataframe(
                            results_df[['ticker', 'total_trades', 'win_rate', 'total_return', 'avg_gain', 'avg_loss', 'avg_hold_days']].style.format({
                                'win_rate': '{:.1f}%',
                                'total_return': '{:.2f}%',
                                'avg_gain': '{:.2f}%',
                                'avg_loss': '{:.2f}%',
                                'avg_hold_days': '{:.1f}'
                            }),
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        # Top performers
                        st.markdown("### ⭐ Top 5 Mã Tốt Nhất")
                        top5 = results_df.head(5)
                        for idx, row in top5.iterrows():
                            st.success(f"**{row['ticker']}**: Win rate {row['win_rate']:.1f}%, Total return {row['total_return']:.2f}%, {row['total_trades']} trades")
                    else:
                        st.error("❌ Không có kết quả backtest nào")
            else:
                st.info("📝 Danh mục trống. Thêm mã để bắt đầu backtest!")
        
        except Exception as e:
            st.error("❌ Lỗi quản lý danh mục: ")
            import traceback
elif page == "⚙️ Settings":
    from ticker_manager import add_ticker, remove_ticker, get_current_tickers
    
    st.markdown('<div class="main-header">⚙️ Cài Đặt</div>', unsafe_allow_html=True)
    
    # ===== Ticker Management =====
    st.markdown("### 📋 Quản Lý Danh Sách Mã")
    
    # Get current tickers
    try:
        spreadsheet = get_spreadsheet()
        current_tickers = get_current_tickers(spreadsheet)
    except Exception as e:
        st.error("Lỗi kết nối Google Sheets: ")
        current_tickers = []
    
    # Display current tickers
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.metric("Tổng số mã", len(current_tickers))
        
        # Display tickers in a nice format
        if current_tickers:
            # Create DataFrame for display
            from sectors import get_sector
            
            ticker_data = []
            for ticker in current_tickers:
                sector = get_sector(ticker)
                ticker_data.append({
                    'Mã': ticker,
                    'Ngành': sector
                })
            
            df_tickers = pd.DataFrame(ticker_data)
            st.dataframe(df_tickers, use_container_width=True, hide_index=True)
    
    with col2:
        st.markdown("**Thao tác**")
        
        # Add ticker
        with st.form("add_ticker_form"):
            new_ticker = st.text_input("Thêm mã mới", placeholder="VD: VNM", max_chars=4)
            submit_add = st.form_submit_button("➕ Thêm", use_container_width=True)
            
            if submit_add and new_ticker:
                success, message = add_ticker(spreadsheet, new_ticker)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
        
        # Remove ticker
        with st.form("remove_ticker_form"):
            ticker_to_remove = st.selectbox("Xóa mã", options=current_tickers if current_tickers else [""])
            submit_remove = st.form_submit_button("🗑️ Xóa", use_container_width=True)
            
            if submit_remove and ticker_to_remove:
                success, message = remove_ticker(spreadsheet, ticker_to_remove)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
    
    st.markdown("---")
    
    # ===== System Info =====
    st.markdown("### 📊 Thông Tin Hệ Thống")
    
    info_col1, info_col2, info_col3 = st.columns(3)
    
    with info_col1:
        st.metric("Streamlit", st.__version__)
    
    with info_col2:
        st.metric("Python", f"{sys.version_info.major}.{sys.version_info.minor}")
    
    with info_col3:
        try:
            spreadsheet = get_spreadsheet()
            st.metric("Google Sheets", "✅ OK")
        except:
            st.metric("Google Sheets", "❌ Error")
    
    st.markdown("---")
    
    # ===== Automation Info =====
    st.markdown("### 🤖 Tự Động Hóa")
    
    st.info("""
    **GitHub Actions đang chạy tự động:**
    
    - 💸 **Money Flow**: Mỗi 15 phút (9:30-11:15, 13:30-14:30)
    - 📊 **Price & Finance**: Theo lịch workflows
    - 🧹 **Cleanup**: 15:00 hàng ngày
    - 🎯 **Auto-skip**: Cuối tuần & ngày lễ VN
    
    Không cần chạy thủ công!
    """)
    
    st.markdown("---")
    
    # ===== CLI Commands Reference =====
    with st.expander("🔧 Lệnh CLI (Tham khảo)"):
        st.markdown("""
        **Cào dữ liệu giá:**
        ```bash
        python price.py --period 5y --interval 1D
        ```
        
        **Cào dữ liệu tài chính:**
        ```bash
        python finance.py
        ```
        
        **Money flow:**
        ```bash
        python money_flow.py --interval 15
        python historical_money_flow.py --days 30
        ```
        
        **Financial screening:**
        ```bash
        python financial_screening.py --min-roe 15
        ```
        
        **Watchlist:**
        ```bash
        python watchlist.py --add VNM --type flow
        python watchlist.py --list --type flow
        ```
        """)
    st.markdown('<div class="main-header">⚙️ Cài Đặt Hệ Thống</div>', unsafe_allow_html=True)
    
    # ===== AI API Configuration =====
    st.subheader("🤖 Cấu Hình AI API")
    
    with st.expander("🔑 Khai Báo API Keys cho AI Analysis", expanded=False):
        st.markdown("""
        **Hướng dẫn:** Nhập API key để sử dụng tính năng phân tích AI.
        - API keys được lưu trong session (không lưu vĩnh viễn vì lý do bảo mật)
        - Để lưu vĩnh viễn, thêm vào file `.env`
        """)
        
        # Gemini API
        gemini_key_current = os.getenv('GEMINI_API_KEY', '')
        gemini_key_masked = gemini_key_current[:8] + '...' if gemini_key_current and len(gemini_key_current) > 8 else ''
        
        col_gem1, col_gem2 = st.columns([3, 1])
        with col_gem1:
            gemini_key = st.text_input(
                "🌟 Gemini API Key", 
                type="password",
                placeholder="AIzaSy... (Lấy tại https://aistudio.google.com/apikey)",
                help="Google Gemini API key - Free tier: 15 requests/minute"
            )
        with col_gem2:
            st.caption("**Status:**")
            if gemini_key_current and gemini_key_current not in ['', 'your_gemini_api_key_here']:
                st.success(f"✅ Đã có ({gemini_key_masked})")
            else:
                st.warning("⚠️ Chưa có")
        
        # OpenAI API
        openai_key_current = os.getenv('OPENAI_API_KEY', '')
        openai_key_masked = openai_key_current[:8] + '...' if openai_key_current and len(openai_key_current) > 8 else ''
        
        col_oai1, col_oai2 = st.columns([3, 1])
        with col_oai1:
            openai_key = st.text_input(
                "🌐 OpenAI API Key",
                type="password",
                placeholder="sk-... (Lấy tại https://platform.openai.com/api-keys)",
                help="OpenAI API key - Paid tier"
            )
        with col_oai2:
            st.caption("**Status:**")
            if openai_key_current and openai_key_current not in ['', 'your_openai_api_key_here']:
                st.success(f"✅ Đã có ({openai_key_masked})")
            else:
                st.info("ℹ️ Optional")
        
        # Anthropic API
        anthropic_key_current = os.getenv('ANTHROPIC_API_KEY', '')
        anthropic_key_masked = anthropic_key_current[:8] + '...' if anthropic_key_current and len(anthropic_key_current) > 8 else ''
        
        col_ant1, col_ant2 = st.columns([3, 1])
        with col_ant1:
            anthropic_key = st.text_input(
                "🧠 Anthropic API Key",
                type="password",
                placeholder="sk-ant-... (Lấy tại https://console.anthropic.com/)",
                help="Anthropic Claude API key - Paid tier"
            )
        with col_ant2:
            st.caption("**Status:**")
            if anthropic_key_current and anthropic_key_current not in ['', 'your_anthropic_api_key_here']:
                st.success(f"✅ Đã có ({anthropic_key_masked})")
            else:
                st.info("ℹ️ Optional")
        
        # Save to session/env
        if st.button("💾 Lưu API Keys vào Session", type="primary"):
            updated = []
            if gemini_key:
                os.environ['GEMINI_API_KEY'] = gemini_key
                updated.append("Gemini")
            if openai_key:
                os.environ['OPENAI_API_KEY'] = openai_key
                updated.append("OpenAI")
            if anthropic_key:
                os.environ['ANTHROPIC_API_KEY'] = anthropic_key
                updated.append("Anthropic")
            
            if updated:
                st.success(f"✅ Đã lưu API keys: {', '.join(updated)} vào session!")
                st.info("💡 **Lưu ý:** API keys chỉ có hiệu lực trong phiên làm việc này. Để lưu vĩnh viễn, thêm vào file `.env`")
            else:
                st.warning("⚠️ Không có key mới để lưu")
        
        # Show .env example
        with st.expander("📄 Mẫu file .env"):
            st.code("""
# AI API Keys
GEMINI_API_KEY=AIzaSy... 
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# AI Settings  
AI_DEFAULT_PROVIDER=gemini
GEMINI_MODEL=gemini-2.0-flash
AI_ANALYSIS_DAYS=400
            """, language="bash")
    
    st.markdown("---")
    
    st.subheader("📊 Cào Dữ Liệu Giá Chứng Khoán")
    
    # System Maintenance
    with st.expander("🛠️ Bảo Trì Hệ Thống (Cache & Debug)"):
        if st.button("🗑️ Xóa Cache Dashboard", type="secondary", use_container_width=True):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.success("✅ Đã xóa cache! Vui lòng reload trang (F5) để thấy dữ liệu mới.")
    
    st.info("💡 **Hướng dẫn**: Chọn tham số và nhấn 'Cào Dữ Liệu' để lấy dữ liệu từ vnstock vào Google Sheets")
    
    # Configuration
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Khoảng Thời Gian**")
        period = st.selectbox(
            "Period",
            options=['1d', '1w', '1m', '3m', '6m', '1y', '2y', '5y'],
            index=7,  # Default: 5y
            help="Khoảng thời gian lấy dữ liệu lịch sử",
            label_visibility="collapsed"
        )
        
        period_desc = {
            '1d': '1 ngày',
            '1w': '1 tuần',
            '1m': '1 tháng',
            '3m': '3 tháng',
            '6m': '6 tháng',
            '1y': '1 năm',
            '2y': '2 năm',
            '5y': '5 năm'
        }
        st.caption(f"📅 {period_desc[period]}")
    
    with col2:
        st.markdown("**Interval**")
        interval = st.selectbox(
            "Interval",
            options=['1m', '3m', '5m', '15m', '30m', '1H', '1D'],
            index=6,  # Default: 1D
            help="Độ phân giải dữ liệu",
            label_visibility="collapsed"
        )
        
        interval_desc = {
            '1m': '1 phút (realtime)',
            '3m': '3 phút (realtime)',
            '5m': '5 phút (realtime)',
            '15m': '15 phút (realtime)',
            '30m': '30 phút (realtime)',
            '1H': '1 giờ',
            '1D': '1 ngày (backtest)'
        }
        st.caption(f"⏱️ {interval_desc[interval]}")
    
    with col3:
        st.markdown("**Mode**")
        mode = st.selectbox(
            "Mode",
            options=['historical', 'realtime', 'update'],
            index=0,
            help="historical: Ghi đè toàn bộ | realtime: Intraday | update: Append mới",
            label_visibility="collapsed"
        )
        
        mode_desc = {
            'historical': '🔄 Ghi đè toàn bộ',
            'realtime': '⚡ Realtime intraday',
            'update': '➕ Append dữ liệu mới'
        }
        st.caption(mode_desc[mode])
    
    # Ticker selection
    st.markdown("---")
    st.markdown("**Chọn Mã Chứng Khoán**")
    
    col_a, col_b = st.columns([3, 1])
    
    with col_a:
        ticker_mode = st.radio(
            "Ticker mode",
            options=['Tất cả mã', 'Chọn mã cụ thể'],
            horizontal=True,
            label_visibility="collapsed"
        )
    
    with col_b:
        if ticker_mode == 'Tất cả mã':
            tickers = fetch_ticker_list()
            st.metric("Tổng số mã", len(tickers))
    
    if ticker_mode == 'Chọn mã cụ thể':
        all_tickers = fetch_ticker_list()
        selected_tickers = st.multiselect(
            "Chọn mã",
            options=all_tickers,
            default=['VNM', 'HPG', 'FPT'] if all(t in all_tickers for t in ['VNM', 'HPG', 'FPT']) else all_tickers[:3],
            label_visibility="collapsed"
        )
        tickers_arg = ','.join(selected_tickers) if selected_tickers else None
    else:
        tickers_arg = None
    
    # Summary
    st.markdown("---")
    st.markdown("**📋 Tóm Tắt Cấu Hình**")
    
    summary_col1, summary_col2, summary_col3 = st.columns(3)
    with summary_col1:
        st.info(f"**Period**: {period_desc[period]}")
    with summary_col2:
        st.info(f"**Interval**: {interval_desc[interval]}")
    with summary_col3:
        st.info(f"**Mode**: {mode_desc[mode]}")
    
    # Warning for realtime
    if interval in ['1m', '3m', '5m', '15m', '30m']:
        st.warning("⚠️ **Lưu ý**: Interval ngắn chỉ có dữ liệu trong ngày giao dịch. Không phù hợp cho backtest lịch sử.")
    
    if mode == 'historical':
        st.warning("⚠️ **Cảnh báo**: Mode 'historical' sẽ **xóa toàn bộ** dữ liệu cũ trong sheet 'price'")
    
    # Run button
    st.markdown("---")
    if st.button("🚀 Cào Dữ Liệu", type="primary", use_container_width=True):
        with st.spinner("Đang cào dữ liệu..."):
            try:
                # Build command
                import subprocess
                
                cmd = ['python', 'price.py', '--period', period, '--interval', interval, '--mode', mode]
                if tickers_arg:
                    cmd.extend(['--tickers', tickers_arg])
                
                st.info(f"🔧 Command: `{' '.join(cmd)}`")
                
                # Run price.py
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace'  # Handle encoding errors
                )
                
                # Display output
                if result.returncode == 0:
                    st.success("✅ Hoàn tất cào dữ liệu!")
                    
                    # Show output in expander
                    with st.expander("📄 Chi tiết output"):
                        st.code(result.stdout)
                    
                    st.balloons()
                else:
                    st.error(f"❌ Lỗi khi chạy price.py (exit code: {result.returncode})")
                    st.code(result.stderr)
                    
                    # Show suggestions
                    st.info("💡 **Gợi ý:**\n"
                           "- Kiểm tra kết nối internet\n"
                           "- Kiểm tra credentials.json\n"
                           "- Thử giảm số lượng mã\n"
                           "- Kiểm tra Google Sheets API quota")
            
            except Exception as e:
                st.error("❌ Lỗi: ")
                import traceback
    # Quick actions
    st.markdown("---")
    st.markdown("**⚡ Quick Actions**")
    
    quick_col1, quick_col2, quick_col3 = st.columns(3)
    
    with quick_col1:
        if st.button("📊 Lấy 5 năm cho Backtest", use_container_width=True):
            st.info("Chạy: `python price.py --period 5y --interval 1D --mode historical`")
    
    with quick_col2:
        if st.button("⚡ Realtime 5 phút", use_container_width=True):
            st.info("Chạy: `python price.py --period 1d --interval 5m --mode realtime`")
    
    with quick_col3:
        if st.button("🔄 Update hàng ngày", use_container_width=True):
            st.info("Chạy: `python price.py --period 1w --interval 1D --mode update`")
    
    # ===== Money Flow Scraper =====
    st.markdown("---")
    st.subheader("💸 Cào Dữ Liệu Dòng Tiền")
    st.info("💡 Cào dữ liệu dòng tiền mua-bán real-time từ vnstock intraday API")
    
    mf_col1, mf_col2 = st.columns(2)
    
    with mf_col1:
        if st.button("🔄 Cào Dòng Tiền Real-time", use_container_width=True, type="primary"):
            with st.spinner("Đang cào dữ liệu dòng tiền..."):
                try:
                    import subprocess
                    result = subprocess.run(
                        [sys.executable, 'money_flow.py', '--skip-holiday-check'],
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.DEVNULL,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        timeout=300
                    )
                    if result.returncode == 0:
                        st.success("Hoan tat cao dong tien!")
                        st.balloons()
                    else:
                        st.error("Loi khi cao dong tien")
                except Exception as e:
                    st.error("Loi he thong")
    
    with mf_col2:
        st.markdown("**Output:** Sheet `money_flow_top`")
        st.caption("Top 3 ngành + 9 cổ phiếu dòng tiền mua mạnh nhất")
    
    # ===== Finance Scraper =====
    st.markdown("---")
    st.subheader("📋 Cào Báo Cáo Tài Chính")
    st.info("💡 Cào dữ liệu báo cáo tài chính (Income, Balance, Cashflow) từ vnstock")
    
    # Filter options - Row 1
    fin_filter_col1, fin_filter_col2, fin_filter_col3 = st.columns(3)
    
    with fin_filter_col1:
        fin_period = st.selectbox(
            "📅 Loại báo cáo",
            options=["quarter", "annual"],
            format_func=lambda x: "Theo Quý" if x == "quarter" else "Theo Năm",
            key="fin_period"
        )
    
    with fin_filter_col2:
        fin_years = st.selectbox(
            "📆 Số năm cần cào",
            options=[1, 2, 3, 4, 5],
            index=2,  # Default 3 years
            help="Số năm dữ liệu cần cào (1-5 năm)",
            key="fin_years"
        )
    
    with fin_filter_col3:
        fin_tickers_input = st.text_input(
            "🔍 Mã cổ phiếu (để trống = tất cả)",
            placeholder="VNM, FPT, VCB",
            help="Nhập các mã cách nhau bởi dấu phẩy. Để trống để cào toàn bộ danh sách.",
            key="fin_tickers"
        )
    
    # Sector filter - Row 2
    all_sectors = get_all_sectors()
    fin_selected_sectors = st.multiselect(
        "🏭 Lọc theo ngành (bỏ trống = tất cả ngành)",
        options=all_sectors,
        help="Chọn các ngành muốn cào. Bỏ trống để cào tất cả ngành.",
        key="fin_sectors"
    )
    
    # Action buttons
    fin_col1, fin_col2 = st.columns(2)
    
    with fin_col1:
        if st.button("📋 Cào Báo Cáo Tài Chính", use_container_width=True, type="primary"):
            with st.spinner("Đang cào báo cáo tài chính..."):
                try:
                    import subprocess
                    
                    # Build command with filters
                    cmd = [sys.executable, 'finance.py', '--period', fin_period, '--years', str(fin_years)]
                    
                    # Add ticker filter
                    if fin_tickers_input.strip():
                        cmd.extend(['--tickers', fin_tickers_input.strip()])
                    
                    # Add sector filter - get tickers from selected sectors
                    if fin_selected_sectors and not fin_tickers_input.strip():
                        from sectors import get_tickers_by_sector
                        sector_tickers = []
                        for sector in fin_selected_sectors:
                            sector_tickers.extend(get_tickers_by_sector(sector))
                        if sector_tickers:
                            cmd.extend(['--tickers', ','.join(set(sector_tickers))])
                    
                    result = subprocess.run(
                        cmd,
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
                        timeout=1800
                    )
                    if result.returncode == 0:
                        st.success("✅ Hoàn tất cào báo cáo tài chính!")
                        st.balloons()
                        # Show summary
                        if result.stdout:
                            with st.expander("📄 Chi tiết"):
                                st.code(result.stdout[-2000:])  # Last 2000 chars
                    else:
                        st.error(f"❌ Lỗi khi cào báo cáo tài chính (Exit code: {result.returncode})")
                        if result.stderr:
                            st.code(result.stderr)
                except subprocess.TimeoutExpired:
                     st.error("⏰ Lỗi: Quá thời gian chờ (Timeout 30 phút)")
                except Exception as e:
                    st.error(f"❌ Lỗi hệ thống: {str(e)}")
    
    with fin_col2:
        st.markdown("**Output:** Sheets `income`, `balance`, `cashflow`")
        st.caption("Báo cáo kết quả kinh doanh, bảng cân đối kế toán, lưu chuyển tiền tệ")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        Stock Analysis Dashboard | Made with ❤️ using Streamlit & vnstock
    </div>
    """,
    unsafe_allow_html=True
)
