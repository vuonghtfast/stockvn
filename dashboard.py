# -*- coding: utf-8 -*-
"""
Stock Analysis Dashboard
Phân tích chứng khoán Việt Nam
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from vnstock import stock_historical_data

# Page config
st.set_page_config(
    page_title="Stock Analysis Dashboard",
    page_icon="📈",
    layout="wide"
)

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
    
    page = st.radio(
        "📍 Navigation",
        ["🏠 Dashboard", "📊 Phân Tích", "💰 Báo Cáo Tài Chính", "⚙️ Settings"],
        label_visibility="collapsed"
    )

# Main content
if page == "🏠 Dashboard":
    st.markdown('<div class="main-header">📈 Stock Analysis Dashboard</div>', unsafe_allow_html=True)
    
    # Stock symbol input
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        symbol = st.text_input("Mã chứng khoán", value="VNM", placeholder="VD: VNM, VIC, HPG...")
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
            
            with st.spinner(f"Đang tải dữ liệu {symbol}..."):
                df = stock_historical_data(
                    symbol=symbol,
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d"),
                    resolution="1D",
                    type="stock"
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
            else:
                st.error(f"❌ Không tìm thấy dữ liệu cho mã {symbol}")
                
        except Exception as e:
            st.error(f"❌ Lỗi: {e}")
    else:
        st.info("👆 Nhập mã chứng khoán để bắt đầu phân tích")

elif page == "📊 Phân Tích":
    st.markdown('<div class="main-header">📊 Phân Tích Kỹ Thuật</div>', unsafe_allow_html=True)
    st.info("🚧 Tính năng đang phát triển...")

elif page == "💰 Báo Cáo Tài Chính":
    st.markdown('<div class="main-header">💰 Báo Cáo Tài Chính</div>', unsafe_allow_html=True)
    st.info("🚧 Tính năng đang phát triển...")

elif page == "⚙️ Settings":
    st.markdown('<div class="main-header">⚙️ Settings</div>', unsafe_allow_html=True)
    st.info("⚙️ Cấu hình ứng dụng")

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
