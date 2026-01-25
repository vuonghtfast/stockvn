# -*- coding: utf-8 -*-
"""
Stock Analysis Dashboard
Phân tích chứng khoán Việt Nam
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
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

# Suppress Streamlit secrets warning for local development
warnings.filterwarnings('ignore', category=UserWarning, module='streamlit')

# Page config
st.set_page_config(
    page_title="Stock Analysis Dashboard",
    page_icon="📈",
    layout="wide"
)

# Cached data fetching function with TTL (Time To Live)
@st.cache_data(ttl=300)  # Cache for 5 minutes (300 seconds)
def fetch_stock_data(symbol, start_date, end_date):
    """Fetch stock data with caching to reduce API calls"""
    stock = Vnstock().stock(symbol=symbol, source='VCI')
    df = stock.quote.history(
        start=start_date,
        end=end_date,
        interval='1D'
    )
    return df

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
        st.error(f"❌ Lỗi đọc sheet '{sheet_name}': {e}")
        import traceback
        st.code(traceback.format_exc())
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def fetch_ticker_list():
    """Fetch list of tickers from Google Sheets with sector info"""
    try:
        spreadsheet = get_spreadsheet()
        ws = spreadsheet.worksheet("tickers")
        tickers = ws.col_values(1)[1:]  # Skip header
        tickers = [t.strip().upper() for t in tickers if t.strip()]
        
        # Add sector information
        df = pd.DataFrame({
            'ticker': tickers,
            'sector': [get_sector(t) for t in tickers]
        })
        
        return df
    except Exception as e:
        st.error(f"⚠️ Lỗi đọc danh sách mã: {e}")
        # Return default fallback with sectors
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
        st.warning(f"⚠️ Lỗi tính toán metrics: {e}")
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
    auto_refresh = st.checkbox("🔄 Auto-refresh", value=False, help="Tự động làm mới dữ liệu")
    refresh_interval = st.slider(
        "Refresh mỗi (phút)",
        min_value=5,
        max_value=30,
        value=5,
        step=5,
        disabled=not auto_refresh
    )
    
    st.markdown("---")
    
    page = st.radio(
        "📍 Navigation",
        ["🏠 Dashboard", "📊 Phân Tích", "💰 Báo Cáo Tài Chính", "🌐 Khuyến Nghị", "🔬 Backtest", "⚙️ Settings"],
        label_visibility="collapsed"
    )

# Main content
if page == "🏠 Dashboard":
    st.markdown('<div class="main-header">📈 Stock Analysis Dashboard</div>', unsafe_allow_html=True)
    
    # Stock symbol input
    tickers = fetch_ticker_list()
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        symbol = st.selectbox("Mã chứng khoán", options=tickers, index=0 if "VNM" not in tickers else tickers.index("VNM"))
    with col2:
        days = st.number_input("Số ngày", min_value=30, max_value=365, value=90)
    with col3:
        if st.button("🔍 Phân tích", use_container_width=True, type="primary"):
            st.rerun()
    
    if symbol:
        try:
            # Get stock data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Fetch data with caching
            with st.spinner(f"Đang tải dữ liệu {symbol}..."):
                df = fetch_stock_data(
                    symbol=symbol,
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d")
                )
            
            if df is not None and len(df) > 0:
                # Display metrics
                latest = df.iloc[-1]
                prev = df.iloc[-2] if len(df) > 1 else latest
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    change = latest['close'] - prev['close']
                    change_pct = (change / prev['close']) * 100
                    st.metric(
                        "Giá đóng cửa",
                        f"{latest['close']:,.0f}",
                        f"{change:+,.0f} ({change_pct:+.2f}%)"
                    )
                with col2:
                    st.metric("Cao nhất", f"{latest['high']:,.0f}")
                with col3:
                    st.metric("Thấp nhất", f"{latest['low']:,.0f}")
                with col4:
                    st.metric("Khối lượng", f"{latest['volume']:,.0f}")
                
                st.markdown("---")
                
                # Candlestick chart
                st.subheader(f"📊 Biểu Đồ Giá {symbol}")
                
                fig = go.Figure(data=[go.Candlestick(
                    x=df.index,
                    open=df['open'],
                    high=df['high'],
                    low=df['low'],
                    close=df['close'],
                    name=symbol
                )])
                
                fig.update_layout(
                    xaxis_title="Ngày",
                    yaxis_title="Giá (VNĐ)",
                    height=500,
                    xaxis_rangeslider_visible=False
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Volume chart
                st.subheader("📈 Khối Lượng Giao Dịch")
                
                fig_vol = go.Figure(data=[go.Bar(
                    x=df.index,
                    y=df['volume'],
                    name='Volume',
                    marker_color='lightblue'
                )])
                
                fig_vol.update_layout(
                    xaxis_title="Ngày",
                    yaxis_title="Khối lượng",
                    height=300
                )
                
                st.plotly_chart(fig_vol, use_container_width=True)
                
                # Data table
                with st.expander("📄 Xem dữ liệu chi tiết"):
                    st.dataframe(df.tail(20), use_container_width=True)
                
                # Auto-refresh countdown
                if auto_refresh:
                    refresh_placeholder = st.empty()
                    for remaining in range(refresh_interval * 60, 0, -1):
                        mins, secs = divmod(remaining, 60)
                        refresh_placeholder.info(
                            f"🔄 Tự động làm mới sau: {mins:02d}:{secs:02d}"
                        )
                        time.sleep(1)
                    st.rerun()
            else:
                st.error(f"❌ Không tìm thấy dữ liệu cho mã {symbol}")
                
        except Exception as e:
            st.error(f"❌ Lỗi: {e}")
    else:
        st.info("👆 Nhập mã chứng khoán để bắt đầu phân tích")

elif page == "📊 Phân Tích":
    st.markdown('<div class="main-header">📊 Phân Tích Kỹ Thuật</div>', unsafe_allow_html=True)
    
    tickers = fetch_ticker_list()
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        ta_symbol = st.selectbox("Mã chứng khoán", options=tickers, key="ta_symbol", index=0 if "VNM" not in tickers else tickers.index("VNM"))
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
            st.error(f"❌ Lỗi phân tích: {e}")

elif page == "💰 Báo Cáo Tài Chính":
    st.markdown('<div class="main-header">💰 Báo Cáo Tài Chính</div>', unsafe_allow_html=True)
    
    # Selection
    tickers = fetch_ticker_list()
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        fin_symbol = st.selectbox("Nhập mã chứng khoán", options=tickers, key="fin_symbol", index=0 if "VNM" not in tickers else tickers.index("VNM"))
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


elif page == "🌐 Khuyến Nghị":
    st.markdown('<div class="main-header">🎯 Khuyến Nghị Đầu Tư</div>', unsafe_allow_html=True)
    
    st.warning("⚠️ **TUYÊN BỐ MIỄN TRỪ TRÁCH NHIỆM:** Đây chỉ là hệ thống hỗ trợ ra quyết định dựa trên dữ liệu lịch sử. Kết quả không đảm bảo lợi nhuận trong tương lai. Bạn hoàn toàn chịu trách nhiệm về các quyết định đầu tư của mình.")
    
    tickers = fetch_ticker_list()
    rec_symbol = st.selectbox("Nhập mã để xem khuyến nghị", options=tickers, key="rec_symbol", index=0 if "VNM" not in tickers else tickers.index("VNM"))
    
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
                        rev_growth = (current['revenue'] - prev['revenue']) / prev['revenue']
                        if rev_growth > 0.1:
                            fund_score += 15
                            fund_reasons.append(f"✅ Doanh thu tăng trưởng mạnh (+{rev_growth:.1%})")
                        elif rev_growth < 0:
                            fund_score -= 10
                            fund_reasons.append(f"❌ Doanh thu sụt giảm ({rev_growth:.1%})")
                    
                    if 'net_income' in current and 'net_income' in prev:
                        profit_growth = (current['net_income'] - prev['net_income']) / prev['net_income']
                        if profit_growth > 0.1:
                            fund_score += 15
                            fund_reasons.append(f"✅ Lợi nhuận tăng trưởng tốt (+{profit_growth:.1%})")

            # Final Calculation
            final_score = (tech_score * 0.4 + fund_score * 0.6)
            
            # Display
            col1, col2 = st.columns([1, 2])
            with col1:
                st.metric("TỔNG ĐIỂM", f"{final_score:.1f}/100")
                if final_score > 70:
                    st.success("💪 TÍNH HIỆU: MUA")
                elif final_score < 40:
                    st.error("📉 TÍNH HIỆU: BÁN")
                else:
                    st.warning("⚖️ TÍNH HIỆU: THEO DÕI")
            
            with col2:
                st.subheader("Chi tiết đánh giá")
                for r in tech_reasons + fund_reasons:
                    st.write(r)

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
                    st.error(f"❌ Lỗi backtest: {e}")
                    import traceback
                    st.code(traceback.format_exc())
    
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
                            st.warning(f"⚠️ Lỗi backtest {ticker}: {e}")
                    
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
            st.error(f"❌ Lỗi quản lý danh mục: {e}")
            import traceback
            st.code(traceback.format_exc())

elif page == "⚙️ Settings":
    st.markdown('<div class="main-header">⚙️ Cài Đặt Hệ Thống</div>', unsafe_allow_html=True)
    
    st.subheader("📊 Cào Dữ Liệu Giá Chứng Khoán")
    
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
                st.error(f"❌ Lỗi: {e}")
                import traceback
                st.code(traceback.format_exc())
    
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
