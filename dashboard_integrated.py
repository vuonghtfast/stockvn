# -*- coding: utf-8 -*-
"""
Stock Analysis Dashboard - Integrated Version
Tích hợp đầy đủ: Money Flow, Financial Screening, Watchlist
"""

import streamlit as st
import sys
import os

# Import dashboard cũ và tabs mới
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import các hàm từ dashboard cũ
from dashboard import (
    fetch_stock_data, fetch_ticker_list, get_spreadsheet,
    calculate_financial_metrics, fetch_financial_sheet
)

# Import các tab mới
from dashboard_tabs import (
    render_money_flow_tab,
    render_financial_screening_tab, 
    render_watchlist_tab
)

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
        ["🏠 Dashboard", "💸 Dòng Tiền", "🔍 Lọc Cổ Phiếu", "📋 Danh Sách Theo Dõi"],
        label_visibility="collapsed"
    )

# Main content
if page == "🏠 Dashboard":
    st.markdown('<div class="main-header">📈 Stock Analysis Dashboard</div>', unsafe_allow_html=True)
    st.info("Chọn tab từ sidebar để sử dụng các tính năng mới!")
    
    st.markdown("""
    ### 🆕 Tính năng mới
    
    **💸 Dòng Tiền**
    - Top 3 ngành có dòng tiền mạnh nhất
    - Top 5 cổ phiếu có dòng tiền mạnh nhất
    - Phân tích định giá (P/E, P/B, P/S)
    - Bộ lọc nâng cao
    
    **🔍 Lọc Cổ Phiếu**
    - Hệ thống 10 chỉ tiêu tài chính
    - Composite scoring (0-100 điểm)
    - Lọc theo ngành và mã cụ thể
    
    **📋 Danh Sách Theo Dõi**
    - Quản lý 2 watchlists (Dòng tiền + Cơ bản)
    - Auto-update metrics
    - Xuất CSV
    
    ### 📚 Hướng dẫn
    
    **Thu thập dữ liệu dòng tiền:**
    ```bash
    # Dữ liệu hiện tại
    python money_flow.py --interval 15
    
    # Dữ liệu lịch sử 30 ngày
    python historical_money_flow.py --days 30
    ```
    
    **Lọc cổ phiếu:**
    ```bash
    python financial_screening.py --min-roe 15 --max-pe 20
    ```
    
    **Quản lý watchlist:**
    ```bash
    python watchlist.py --add VNM --type flow
    python watchlist.py --list --type flow
    ```
    """)

elif page == "💸 Dòng Tiền":
    render_money_flow_tab()

elif page == "🔍 Lọc Cổ Phiếu":
    render_financial_screening_tab()

elif page == "📋 Danh Sách Theo Dõi":
    render_watchlist_tab()
