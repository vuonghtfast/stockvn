# Settings Page Replacement for dashboard.py
# Replace from line 1642 to end of Settings section

elif page == "⚙️ Settings":
    from ticker_manager import add_ticker, remove_ticker, get_current_tickers, format_price
    
    st.markdown('<div class="main-header">⚙️ Cài Đặt</div>', unsafe_allow_html=True)
    
    # ===== Ticker Management =====
    st.markdown("### 📋 Quản Lý Danh Sách Mã")
    
    # Get current tickers
    try:
        spreadsheet = get_spreadsheet()
        current_tickers = get_current_tickers(spreadsheet)
    except Exception as e:
        st.error(f"Lỗi kết nối Google Sheets: {e}")
        current_tickers = []
    
    # Display current tickers
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.metric("Tổng số mã", len(current_tickers))
        
        # Display tickers in a nice format
        if current_tickers:
            # Create DataFrame for display
            import pandas as pd
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
        import sys
        st.metric("Python", f"{sys.version_info.major}.{sys.version_info.minor}")
    
    with info_col3:
        try:
            spreadsheet = get_spreadsheet()
            st.metric("Google Sheets", "✅ Connected")
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
