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
        return pd.DataFrame(data)
    except Exception as e:
        st.error("⚠️ Lỗi đọc sheet {sheet_name}: ")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def fetch_ticker_list():
    """Fetch list of tickers from Google Sheets"""
    try:
        spreadsheet = get_spreadsheet()
        ws = spreadsheet.worksheet("tickers")
        tickers = ws.col_values(1)[1:]  # Skip header
        return [t.strip().upper() for t in tickers if t.strip()]
    except Exception as e:
        st.error("⚠️ Lỗi đọc danh sách mã: ")
        return ["VNM", "HPG", "VIC"]  # Default fallback

def calculate_financial_metrics(symbol):
    """Calculate key financial metrics for a stock"""
    metrics = {}
    
    try:
        # Fetch financial data
        income_df = fetch_financial_sheet("income")
        balance_df = fetch_financial_sheet("balance")
        
        if not income_df.empty:
            ticker_income = income_df[income_df['ticker'].astype(str).str.upper() == symbol]
            if not ticker_income.empty:
                latest_income = ticker_income.iloc[-1]
                
                # Get latest price
                end_date = datetime.now()
                start_date = end_date - timedelta(days=7)
                price_df = fetch_stock_data(symbol, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
                
                if not price_df.empty:
                    current_price = price_df.iloc[-1]['close']
                    
                    # Estimate shares outstanding (simplified)
                    if 'net_income' in latest_income and latest_income['net_income'] != 0:
                        # PE Ratio approximation
                        metrics['current_price'] = current_price
        
        if not balance_df.empty:
            ticker_balance = balance_df[balance_df['ticker'].astype(str).str.upper() == symbol]
            if not ticker_balance.empty and not ticker_income.empty:
                latest_balance = ticker_balance.iloc[-1]
                latest_income = ticker_income.iloc[-1]
                
                # ROE = Net Income / Equity
                if 'equity' in latest_balance and latest_balance['equity'] != 0:
                    metrics['ROE'] = (latest_income.get('net_income', 0) / latest_balance['equity']) * 100
                
                # ROA = Net Income / Total Assets
                if 'total_assets' in latest_balance and latest_balance['total_assets'] != 0:
                    metrics['ROA'] = (latest_income.get('net_income', 0) / latest_balance['total_assets']) * 100
                
                # Profit Margin = Net Income / Revenue
                if 'revenue' in latest_income and latest_income['revenue'] != 0:
                    metrics['profit_margin'] = (latest_income.get('net_income', 0) / latest_income['revenue']) * 100
                
                # Debt to Equity
                if 'equity' in latest_balance and latest_balance['equity'] != 0:
                    metrics['debt_to_equity'] = latest_balance.get('total_liabilities', 0) / latest_balance['equity']
    
    except Exception as e:
        st.warning("Không thể tính toán metrics cho {symbol}: ")
    
    return metrics

def get_gspread_client():
    """Get authenticated gspread client"""
    creds = get_google_credentials()
    return gspread.authorize(creds)

def get_spreadsheet():
    """Get the target spreadsheet"""
    client = get_gspread_client()
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
        ["🏠 Dashboard", "📊 Phân Tích", "💰 Báo Cáo Tài Chính", "🌐 Khuyến Nghị", "⚙️ Settings"],
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
            st.error("❌ Lỗi: ")
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
                    fig_ta.add_trace(go.Candlestick(
                        x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name=ta_symbol
                    ))
                    
                    for ma in ["SMA20", "SMA50", "SMA200"]:
                        if ma in df.columns:
                            fig_ta.add_trace(go.Scatter(x=df.index, y=df[ma], name=ma, line=dict(width=1.5)))
                    
                    fig_ta.update_layout(height=600, xaxis_rangeslider_visible=False, yaxis_title="Giá (VNĐ)")
                    st.plotly_chart(fig_ta, use_container_width=True)
                    
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
    
    # Selection
    tickers = fetch_ticker_list()
    col1, col2 = st.columns([1, 1])
    with col1:
        fin_symbol = st.selectbox("Nhập mã chứng khoán", options=tickers, key="fin_symbol", index=0 if "VNM" not in tickers else tickers.index("VNM"))
    with col2:
        period_type = st.radio("Kỳ báo cáo", ["Quý", "Năm"], horizontal=True)

    if fin_symbol:
        with st.spinner(f"Đang tải báo cáo tài chính {fin_symbol}..."):
            # Calculate and display key metrics
            metrics = calculate_financial_metrics(fin_symbol)
            
            if metrics:
                st.subheader("📈 Chỉ số tài chính quan trọng")
                col1, col2, col3, col4 = st.columns(4)
                
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
                
                st.markdown("---")
            
            # Load sheets
            income_df = fetch_financial_sheet("income")
            balance_df = fetch_financial_sheet("balance")
            cashflow_df = fetch_financial_sheet("cashflow")
            
            # Filter
            if not income_df.empty:
                ticker_income = income_df[income_df['ticker'].astype(str).str.upper() == fin_symbol]
                
                if not ticker_income.empty:
                    # Tabs for different reports
                    tab1, tab2, tab3 = st.tabs(["📊 Kết Quả Kinh Doanh", "⚖️ Bảng Cân Đối", "💸 Lưu Chuyển Tiền Tệ"])
                    
                    with tab1:
                        st.subheader("Báo cáo Kết quả Kinh doanh")
                        
                        # Growth Chart
                        if 'revenue' in ticker_income.columns and 'net_income' in ticker_income.columns:
                            fig_growth = go.Figure()
                            fig_growth.add_trace(go.Bar(
                                x=ticker_income['year'].astype(str) + (ticker_income['quarter'].astype(str) if 'quarter' in ticker_income.columns else ""),
                                y=ticker_income['revenue'],
                                name='Doanh thu'
                            ))
                            fig_growth.add_trace(go.Scatter(
                                x=ticker_income['year'].astype(str) + (ticker_income['quarter'].astype(str) if 'quarter' in ticker_income.columns else ""),
                                y=ticker_income['net_income'],
                                name='Lợi nhuận sau thuế',
                                yaxis='y2'
                            ))
                            fig_growth.update_layout(
                                yaxis_title="Doanh thu",
                                yaxis2=dict(title="Lợi nhuận", overlaying='y', side='right'),
                                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                                height=400
                            )
                            st.plotly_chart(fig_growth, use_container_width=True)
                        
                        st.dataframe(ticker_income, use_container_width=True)
                    
                    with tab2:
                        st.subheader("Bảng Cân đối Kế toán")
                        if not balance_df.empty:
                            ticker_balance = balance_df[balance_df['ticker'].astype(str).str.upper() == fin_symbol]
                            st.dataframe(ticker_balance, use_container_width=True)
                        else:
                            st.warning("Không có dữ liệu Bảng cân đối")
                            
                    with tab3:
                        st.subheader("Báo cáo Lưu chuyển Tiền tệ")
                        if not cashflow_df.empty:
                            ticker_cashflow = cashflow_df[cashflow_df['ticker'].astype(str).str.upper() == fin_symbol]
                            st.dataframe(ticker_cashflow, use_container_width=True)
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
    
    rec_symbol = st.text_input("Nhập mã để xem khuyến nghị", value="VNM").upper()
    
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
    st.markdown('<div class="main-header">⚙️ Cấu Hình Hệ Thống</div>', unsafe_allow_html=True)
    
    try:
        spreadsheet = get_spreadsheet()
        
        # 1. Quản lý danh sách mã (Tickers)
        st.subheader("📋 Danh sách mã theo dõi")
        tickers_ws = spreadsheet.worksheet("tickers")
        current_tickers = tickers_ws.col_values(1)[1:] # Skip header
        
        tickers_str = st.text_area(
            "Nhập danh sách mã (cách nhau bằng dấu phẩy hoặc xuống dòng)",
            value="\n".join(current_tickers),
            height=150,
            help="Ví dụ: VNM, HPG, TCB..."
        )
        
        if st.button("💾 Lưu danh sách mã"):
            # Clean and parse tickers
            new_tickers = [t.strip().upper() for t in tickers_str.replace(",", "\n").split("\n") if t.strip()]
            if new_tickers:
                # Update sheet: Header + Data
                data_to_update = [["ticker"]] + [[t] for t in new_tickers]
                tickers_ws.clear()
                tickers_ws.update(data_to_update)
                st.success(f"✅ Đã lưu {len(new_tickers)} mã thành công!")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("⚠️ Danh sách không được để trống")

        st.markdown("---")

        # 2. Quản lý cấu hình (Config)
        st.subheader("⚙️ Thông số hệ thống")
        config_data = get_config()
        
        col1, col2 = st.columns(2)
        with col1:
            update_interval = st.number_input(
                "Tần suất cập nhật giá (phút)",
                min_value=1, max_value=60,
                value=int(config_data.get("update_interval_minutes", 10))
            )
            cooldown = st.number_input(
                "Thời gian chờ alert (giờ)",
                min_value=1, max_value=24,
                value=int(config_data.get("alert_cooldown_hours", 1))
            )
        with col2:
            retention = st.number_input(
                "Giữ data trong Sheets (ngày)",
                min_value=7, max_value=90,
                value=int(config_data.get("data_retention_days", 30))
            )
            hist_years = st.number_input(
                "Số năm lưu SQLite",
                min_value=1, max_value=10,
                value=int(config_data.get("historical_years", 5))
            )

        if st.button("📝 Cập nhật cấu hình"):
            with st.spinner("Đang lưu cấu hình..."):
                update_config("update_interval_minutes", update_interval)
                update_config("alert_cooldown_hours", cooldown)
                update_config("data_retention_days", retention)
                update_config("historical_years", hist_years)
                st.success("✅ Đã cập nhật cấu hình thành công!")
                time.sleep(1)
                st.rerun()

        st.markdown("---")
        
        # 3. Chạy script thủ công
        st.subheader("🚀 Chạy script thủ công")
        col_run1, col_run2 = st.columns(2)
        with col_run1:
            if st.button("📈 Cập nhật giá ngay (price.py)"):
                with st.spinner("Đang chạy price.py..."):
                    import subprocess
                    result = subprocess.run(["python", "price.py"], capture_output=True, text=True)
                    if result.returncode == 0:
                        st.success("✅ Cập nhật giá thành công!")
                    else:
                        st.error(f"❌ Lỗi: {result.stderr}")
        with col_run2:
            if st.button("💰 Cập nhật tài chính (finance.py)"):
                with st.spinner("Đang chạy finance.py..."):
                    import subprocess
                    result = subprocess.run(["python", "finance.py"], capture_output=True, text=True)
                    if result.returncode == 0:
                        st.success("✅ Cập nhật tài chính thành công!")
                    else:
                        st.error(f"❌ Lỗi: {result.stderr}")

    except Exception as e:
        st.error("❌ Lỗi kết nối cấu hình: ")

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
