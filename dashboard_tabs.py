# -*- coding: utf-8 -*-
"""
Dashboard Tabs - Money Flow, Financial Screening, Watchlist
Các tab bổ sung cho dashboard
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from config import get_google_credentials
import gspread
from sectors import get_sector, get_all_sectors
from watchlist import add_to_watchlist, get_watchlist, update_watchlist_metrics
from financial_screening import calculate_all_metrics, screen_by_criteria, calculate_composite_score
import subprocess
import sys
import os

@st.cache_data(ttl=300)  # Cache 5 minutes
def get_money_flow_data():
    """Lấy dữ liệu dòng tiền từ Google Sheets"""
    try:
        creds = get_google_credentials()
        client = gspread.authorize(creds)
        
        import os
        spreadsheet_id = os.getenv("SPREADSHEET_ID")
        if spreadsheet_id:
            spreadsheet = client.open_by_key(spreadsheet_id)
        else:
            spreadsheet = client.open("stockdata")
        
        # Lấy intraday flow
        try:
            flow_ws = spreadsheet.worksheet("intraday_flow")
            flow_data = flow_ws.get_all_records()
            flow_df = pd.DataFrame(flow_data)
            
            if not flow_df.empty:
                # Convert numeric columns
                numeric_cols = ['money_flow_normalized', 'pe_ratio', 'pb_ratio', 'ps_ratio', 'price_change_pct']
                for col in numeric_cols:
                    if col in flow_df.columns:
                        flow_df[col] = pd.to_numeric(flow_df[col], errors='coerce')
                
                return flow_df
        except:
            pass
        
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Lỗi khi lấy dữ liệu dòng tiền: {e}")
        return pd.DataFrame()

def render_money_flow_tab():
    """Render Money Flow Analysis tab"""
    
    st.markdown("### 💸 Phân Tích Dòng Tiền")
    
    # Manual fetch button
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
    
    with col_btn1:
        if st.button("🔄 Cào Dữ Liệu Ngay", use_container_width=True, type="primary"):
            with st.spinner("🔄 Đang cào dữ liệu dòng tiền..."):
                try:
                    # Run money_flow.py
                    result = subprocess.run(
                        [sys.executable, 'money_flow.py', '--interval', '15'],
                        capture_output=True,
                        text=True,
                        timeout=300,
                        cwd='e:/Cao Phi/Code/stockvn'
                    )
                    
                    if result.returncode == 0:
                        st.success("[OK] Cào dữ liệu thành công!")
                        st.rerun()
                    else:
                        st.error(f"[ERROR] Lỗi: {result.stderr}")
                except subprocess.TimeoutExpired:
                    st.error("[ERROR] Timeout sau 5 phút")
                except Exception as e:
                    st.error(f"[ERROR] Lỗi: {e}")
    
    with col_btn2:
        if st.button("📅 Lịch Sử 30 Ngày", use_container_width=True):
            with st.spinner("🔄 Đang cào dữ liệu lịch sử..."):
                try:
                    result = subprocess.run(
                        [sys.executable, 'historical_money_flow.py', '--days', '30'],
                        capture_output=True,
                        text=True,
                        timeout=600,
                        cwd='e:/Cao Phi/Code/stockvn'
                    )
                    
                    if result.returncode == 0:
                        st.success("[OK] Cào dữ liệu lịch sử thành công!")
                        st.rerun()
                    else:
                        st.error(f"[ERROR] Lỗi: {result.stderr}")
                except Exception as e:
                    st.error(f"[ERROR] Lỗi: {e}")
    
    with col_btn3:
        st.info(f"🕒 Cập nhật lần cuối: {datetime.now().strftime('%H:%M:%S')}")
    
    st.markdown("---")
    
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
    
    # Scatter plot with error handling
    try:
        # Filter out invalid data for scatter plot
        scatter_df = latest_df[
            (latest_df['pe_ratio'].notna()) & 
            (latest_df['pb_ratio'].notna()) & 
            (latest_df['money_flow_normalized'].notna()) &
            (latest_df['pe_ratio'] > 0) &
            (latest_df['pb_ratio'] > 0) &
            (latest_df['money_flow_normalized'] > 0)
        ].copy()
        
        if not scatter_df.empty:
            fig_scatter = px.scatter(
                scatter_df,
                x='pe_ratio',
                y='pb_ratio',
                color='sector',
                size='money_flow_normalized',
                hover_data=['ticker', 'money_flow_normalized'],
                title="Phân Tích Định Giá Theo Ngành"
            )
            fig_scatter.update_layout(height=500)
            st.plotly_chart(fig_scatter, use_container_width=True)
        else:
            st.info("Không đủ dữ liệu hợp lệ để hiển thị biểu đồ phân tích định giá")
    except Exception as e:
        st.error(f"Lỗi khi tạo biểu đồ: {e}")

def render_financial_screening_tab():
    """Render tab Lọc Cổ Phiếu"""
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
        # Lấy tickers từ Google Sheets
        try:
            creds = get_google_credentials()
            client = gspread.authorize(creds)
            import os
            spreadsheet_id = os.getenv("SPREADSHEET_ID")
            if spreadsheet_id:
                spreadsheet = client.open_by_key(spreadsheet_id)
            else:
                spreadsheet = client.open("stockdata")
            tickers_ws = spreadsheet.worksheet("tickers")
            all_tickers = tickers_ws.col_values(1)[1:]
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
    """Render tab Danh Sách Theo Dõi"""
    st.markdown('<div class="main-header">📋 Danh Sách Theo Dõi</div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["💰 Dòng Tiền", "📊 Cơ Bản"])
    
    with tab1:
        st.markdown("### 💰 Danh Sách Theo Dõi Dòng Tiền")
        
        flow_watchlist = get_watchlist('flow')
        
        if not flow_watchlist.empty:
            st.dataframe(flow_watchlist, use_container_width=True)
            
            if st.button("🔄 Cập nhật dòng tiền", key="update_flow"):
                with st.spinner("Đang cập nhật..."):
                    update_watchlist_metrics('flow')
                    st.success("✅ Đã cập nhật!")
                    st.rerun()
        else:
            st.info("📝 Danh sách trống. Thêm mã từ tab Dòng Tiền.")
    
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
