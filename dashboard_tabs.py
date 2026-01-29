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
        st.error("Lỗi khi lấy dữ liệu dòng tiền: ")
        return pd.DataFrame()

@st.cache_data(ttl=600)  # Cache 10 minutes
def get_stock_financial_metrics(ticker):
    """Lấy chỉ số tài chính của một mã cổ phiếu từ dữ liệu đã cào"""
    try:
        creds = get_google_credentials()
        client = gspread.authorize(creds)
        spreadsheet = client.open("Stock_Data_Storage")
        
        metrics = {'ticker': ticker, 'has_data': False}
        
        # Get income data for EPS, ROE, ROA
        try:
            income_ws = spreadsheet.worksheet("income")
            income_data = income_ws.get_all_records()
            income_df = pd.DataFrame(income_data)
            
            if not income_df.empty and 'ticker' in income_df.columns:
                ticker_data = income_df[income_df['ticker'].astype(str).str.upper() == ticker.upper()]
                if not ticker_data.empty:
                    latest = ticker_data.iloc[-1]
                    metrics['has_data'] = True
                    
                    # EPS
                    if 'eps' in latest.index:
                        metrics['EPS'] = pd.to_numeric(latest.get('eps', 0), errors='coerce')
                    elif 'share_holder_income' in latest.index and 'outstanding_share' in latest.index:
                        shi = pd.to_numeric(latest.get('share_holder_income', 0), errors='coerce')
                        shares = pd.to_numeric(latest.get('outstanding_share', 1), errors='coerce')
                        if shares and shares > 0:
                            metrics['EPS'] = (shi * 1e9) / shares
        except:
            pass
        
        # Get balance data for ROE, ROA
        try:
            balance_ws = spreadsheet.worksheet("balance")
            balance_data = balance_ws.get_all_records()
            balance_df = pd.DataFrame(balance_data)
            
            if not balance_df.empty and 'ticker' in balance_df.columns:
                ticker_data = balance_df[balance_df['ticker'].astype(str).str.upper() == ticker.upper()]
                if not ticker_data.empty:
                    latest = ticker_data.iloc[-1]
                    metrics['has_data'] = True
                    
                    # ROE, ROA (if available)
                    if 'roe' in latest.index:
                        metrics['ROE'] = pd.to_numeric(latest.get('roe', 0), errors='coerce')
                    if 'roa' in latest.index:
                        metrics['ROA'] = pd.to_numeric(latest.get('roa', 0), errors='coerce')
        except:
            pass
        
        return metrics
    except:
        return {'ticker': ticker, 'has_data': False}

def render_money_flow_tab():
    """Render Money Flow Analysis tab - Giao dịch mua-bán"""
    
    st.markdown("### 💸 Giao dịch mua-bán")
    
    # Manual fetch button
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
    
    with col_btn1:
        if st.button("🔄 Cào Dữ Liệu Ngay", use_container_width=True, type="primary"):
            with st.spinner("🔄 Đang cào dữ liệu dòng tiền..."):
                try:
                    # Run money_flow.py
                    result = subprocess.run(
                        [sys.executable, 'money_flow.py', '--interval', '15'],
                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                        text=True,
                        timeout=300,
                        cwd=os.path.dirname(os.path.abspath(__file__))
                    )
                    
                    if result.returncode == 0:
                        st.success("✅ Cào dữ liệu thành công!")
                        st.rerun()
                    else:
                        st.error("[X] Khong the cao du lieu. Vui long thu lai sau.")
                except subprocess.TimeoutExpired:
                    st.error("[X] Timeout sau 5 phut")
                except Exception as e:
                    st.error("[X] Loi he thong")
    
    with col_btn2:
        st.caption("⚡ Real-time: Cào giao dịch mua-bán hiện tại")
    
    with col_btn3:
        st.info(f"🕒 Cập nhật lần cuối: {datetime.now().strftime('%H:%M:%S')}")
    
    st.markdown("---")
    
    # ===== Historical Scraping Section with Filters =====
    st.subheader("📅 Cào Giao Dịch Lịch Sử")
    st.caption("Cào dữ liệu giá và khối lượng giao dịch trong quá khứ")
    
    # Row 1: Time period and sector filter
    hist_col1, hist_col2 = st.columns(2)
    
    with hist_col1:
        hist_time_period = st.selectbox(
            "⏱️ Thời gian cần cào",
            options=["6 tháng", "1 năm", "2 năm", "3 năm", "4 năm", "5 năm"],
            index=1,  # Default: 1 năm
            key="hist_time_period"
        )
        # Convert to days
        time_map = {"6 tháng": 180, "1 năm": 365, "2 năm": 730, "3 năm": 1095, "4 năm": 1460, "5 năm": 1825}
        hist_days = time_map.get(hist_time_period, 365)
    
    with hist_col2:
        all_sectors = get_all_sectors()
        hist_sectors = st.multiselect(
            "🏭 Lọc theo ngành (bỏ trống = tất cả)",
            options=all_sectors,
            key="hist_sectors"
        )
    
    # Row 2: Stock ticker filter
    hist_tickers_input = st.text_input(
        "🔍 Mã cổ phiếu cụ thể (bỏ trống = tất cả)",
        placeholder="VNM, FPT, VCB",
        help="Nhập các mã cách nhau bởi dấu phẩy. Bỏ trống để cào tất cả.",
        key="hist_tickers"
    )
    
    # Scrape button
    if st.button("📅 Cào Dữ Liệu Lịch Sử", use_container_width=True, type="secondary"):
        with st.spinner(f"🔄 Đang cào dữ liệu {hist_time_period}..."):
            try:
                # Build command with filters
                cmd = [sys.executable, 'price.py', '--days', str(hist_days)]
                
                # Add ticker filter
                tickers_to_scrape = []
                if hist_tickers_input.strip():
                    tickers_to_scrape = [t.strip().upper() for t in hist_tickers_input.split(',')]
                elif hist_sectors:
                    # Get tickers from selected sectors
                    from sectors import get_tickers_by_sector
                    for sector in hist_sectors:
                        tickers_to_scrape.extend(get_tickers_by_sector(sector))
                    tickers_to_scrape = list(set(tickers_to_scrape))
                
                if tickers_to_scrape:
                    cmd.extend(['--tickers', ','.join(tickers_to_scrape)])
                
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=1800,
                    cwd=os.path.dirname(os.path.abspath(__file__))
                )
                
                if result.returncode == 0:
                    st.success(f"✅ Đã cào dữ liệu {hist_time_period} thành công!")
                    if result.stdout:
                        with st.expander("📄 Chi tiết"):
                            st.code(result.stdout[-2000:])
                    st.rerun()
                else:
                    st.error("❌ Không thể cào dữ liệu. Vui lòng thử lại sau.")
                    if result.stderr:
                        st.code(result.stderr[:1000])
            except subprocess.TimeoutExpired:
                st.error("⏰ Timeout sau 30 phút")
            except Exception as e:
                st.error(f"❌ Lỗi hệ thống: {str(e)}")
    
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
    
    st.markdown("### 🔥 Top 15 Cổ Phiếu Dòng Tiền Mua Mạnh Nhất")
    st.caption("5 cổ phiếu mỗi ngành × 3 ngành hàng đầu. Hiển thị chỉ số tài chính + nút thêm vào Danh mục theo dõi.")
    
    # Get top 15 stocks (5 per sector for top 3 sectors)
    top_sectors = sector_summary['sector'].tolist()
    top_stocks_list = []
    for sector in top_sectors:
        sector_stocks = latest_df[latest_df['sector'] == sector].nlargest(5, 'money_flow_normalized')
        top_stocks_list.append(sector_stocks)
    
    top_stocks = pd.concat(top_stocks_list) if top_stocks_list else latest_df.nlargest(15, 'money_flow_normalized')
    
    # Display each stock with expanded info
    for sector in top_sectors:
        sector_stocks = top_stocks[top_stocks['sector'] == sector]
        if sector_stocks.empty:
            continue
            
        st.markdown(f"#### 🏭 {sector}")
        
        for _, row in sector_stocks.iterrows():
            ticker = row['ticker']
            
            # Get financial metrics
            fin_metrics = get_stock_financial_metrics(ticker)
            
            with st.container():
                col1, col2, col3, col4 = st.columns([1.5, 3, 3, 2.5])
                
                with col1:
                    st.markdown(f"**{ticker}**")
                    st.caption(f"Giá: {row.get('close', 0):,.1f}K")
                
                with col2:
                    st.write(f"💰 Dòng tiền: **{row['money_flow_normalized']:,.2f}B**")
                    st.caption(f"P/E: {row.get('pe_ratio', 0):.1f} | P/B: {row.get('pb_ratio', 0):.2f} | Δ: {row.get('price_change_pct', 0):+.2f}%")
                
                with col3:
                    if fin_metrics.get('has_data', False):
                        roe = fin_metrics.get('ROE', 0)
                        roa = fin_metrics.get('ROA', 0)
                        eps = fin_metrics.get('EPS', 0)
                        roe_str = f"{roe:.1f}%" if roe else "N/A"
                        roa_str = f"{roa:.1f}%" if roa else "N/A"
                        eps_str = f"{eps:,.0f}" if eps else "N/A"
                        st.caption(f"📊 ROE: {roe_str} | ROA: {roa_str} | EPS: {eps_str}")
                    else:
                        st.caption("⚠️ Chưa có dữ liệu BCTC")
                        if st.button(f"📋 Cào BCTC", key=f"scrape_fin_{ticker}", help=f"Cào báo cáo tài chính {ticker}"):
                            with st.spinner(f"Đang cào BCTC {ticker}..."):
                                try:
                                    result = subprocess.run(
                                        [sys.executable, 'finance.py', '--tickers', ticker],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        text=True, timeout=120,
                                        cwd=os.path.dirname(os.path.abspath(__file__))
                                    )
                                    if result.returncode == 0:
                                        st.success(f"✅ Đã cào BCTC {ticker}")
                                        get_stock_financial_metrics.clear()  # Clear cache
                                        st.rerun()
                                    else:
                                        st.error(f"❌ Lỗi cào BCTC")
                                except Exception as e:
                                    st.error(f"❌ Lỗi: {str(e)}")
                
                with col4:
                    if st.button(f"➕ Thêm vào Danh mục", key=f"add_wl_{ticker}"):
                        if add_to_watchlist(ticker, 'flow'):
                            st.success(f"✅ Đã thêm {ticker}")
                        else:
                            st.error(f"❌ Lỗi")
                
                st.markdown("---")
    
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
        st.error("Lỗi khi tạo biểu đồ: ")
    
    # ===== Delete Trading Data Section =====
    st.markdown("---")
    st.subheader("🗑️ Xóa Dữ Liệu Giao Dịch")
    
    try:
        creds = get_google_credentials()
        client = gspread.authorize(creds)
        spreadsheet_id = os.getenv("SPREADSHEET_ID")
        if spreadsheet_id:
            spreadsheet = client.open_by_key(spreadsheet_id)
        else:
            spreadsheet = client.open("Stock_Data_Storage")
        
        # Get available tickers from money_flow_top sheet
        try:
            mf_ws = spreadsheet.worksheet("money_flow_top")
            mf_data = mf_ws.get_all_records()
            mf_df = pd.DataFrame(mf_data)
            
            if not mf_df.empty:
                available_sectors = sorted(mf_df['sector'].dropna().unique().tolist()) if 'sector' in mf_df.columns else []
                available_tickers = sorted(mf_df['ticker'].dropna().unique().tolist()) if 'ticker' in mf_df.columns else []
                
                delete_mode = st.radio("Xóa theo", ["Ngành", "Mã cổ phiếu"], horizontal=True, key="mf_delete_mode")
                
                if delete_mode == "Ngành" and available_sectors:
                    delete_sectors = st.multiselect("Chọn ngành cần xóa", options=available_sectors, key="mf_delete_sectors")
                    
                    if st.button("🗑️ Xóa Dữ Liệu Ngành Đã Chọn", key="btn_mf_delete_sector"):
                        if delete_sectors:
                            mf_df = mf_df[~mf_df['sector'].isin(delete_sectors)]
                            mf_ws.clear()
                            mf_ws.update([mf_df.columns.values.tolist()] + mf_df.values.tolist())
                            st.success(f"✅ Đã xóa dữ liệu của {len(delete_sectors)} ngành!")
                            st.rerun()
                        else:
                            st.warning("Vui lòng chọn ít nhất một ngành")
                
                elif delete_mode == "Mã cổ phiếu" and available_tickers:
                    delete_tickers = st.multiselect("Chọn mã cần xóa", options=available_tickers, key="mf_delete_tickers")
                    
                    if st.button("🗑️ Xóa Dữ Liệu Mã Đã Chọn", key="btn_mf_delete_ticker"):
                        if delete_tickers:
                            mf_df = mf_df[~mf_df['ticker'].isin(delete_tickers)]
                            mf_ws.clear()
                            mf_ws.update([mf_df.columns.values.tolist()] + mf_df.values.tolist())
                            st.success(f"✅ Đã xóa dữ liệu của {len(delete_tickers)} mã!")
                            st.rerun()
                        else:
                            st.warning("Vui lòng chọn ít nhất một mã")
            else:
                st.info("Chưa có dữ liệu giao dịch để xóa")
        except Exception as e:
            st.info("Chưa có dữ liệu giao dịch")
    except Exception as e:
        st.error("Lỗi khi kết nối Google Sheets")

def render_financial_screening_tab():
    """Render tab Lọc Cổ Phiếu"""
    
    # Real-time mode toggle - MOVED TO TOP
    st.markdown("### ⚡ Chế Độ Lọc")
    col_mode1, col_mode2, col_mode3 = st.columns([1, 2, 1])
    with col_mode1:
        realtime_mode = st.toggle("🔴 Real-time Mode", value=False, 
                                  help="Sử dụng dữ liệu dòng tiền real-time (cập nhật mỗi 15 phút)")
    with col_mode2:
        if realtime_mode:
            st.info("💡 Đang sử dụng dữ liệu dòng tiền real-time từ intraday_flow")
        else:
            st.info("💡 Đang sử dụng dữ liệu tài chính từ báo cáo định kỳ")
            
    with col_mode3:
        # Button Scrape Finance
        if st.button("🔄 Cập nhật BCTC", help="Cào dữ liệu báo cáo tài chính mới nhất"):
            with st.spinner("Đang cập nhật báo cáo tài chính (có thể lâu)..."):
                try:
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    result = subprocess.run(
                        [sys.executable, 'finance.py'],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        text=True,
                        timeout=900, # 15 minutes
                        cwd=current_dir
                    )
                    if result.returncode == 0:
                        st.success("✅ Cập nhật BCTC thành công!")
                        st.write(result.stdout)
                    else:
                        st.error("❌ Lỗi khi cập nhật BCTC")
                        st.text(result.stderr)
                except subprocess.TimeoutExpired:
                     st.error("❌ Timeout: Quá trình chạy quá lâu")
                except Exception as e:
                     st.error(f"❌ Lỗi hệ thống: {e}")

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
    
    # Real-time specific filters
    if realtime_mode:
        with st.expander("💸 Dòng Tiền (Real-time)", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                min_money_flow = st.number_input("Dòng tiền >= (Tỷ VNĐ)", min_value=0.0, value=0.5, step=0.1,
                                                help="Dòng tiền tối thiểu (tỷ VNĐ)")
            with col2:
                min_price_change = st.number_input("% Thay đổi giá >=", min_value=-100.0, value=0.0, step=0.5,
                                                  help="Phần trăm thay đổi giá tối thiểu")
    
    # Expander 3: Growth (only for non-realtime)
    if not realtime_mode:
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
            if realtime_mode:
                # Real-time filtering using money flow data
                flow_df = get_money_flow_data()
                
                if flow_df.empty:
                    st.error("❌ Không có dữ liệu dòng tiền. Vui lòng chạy money_flow.py trước.")
                else:
                    # Get latest data per ticker
                    latest_df = flow_df.groupby('ticker').tail(1).reset_index(drop=True)
                    
                    # Apply filters
                    filtered = latest_df[
                        (latest_df['money_flow_normalized'] >= min_money_flow) &
                        (latest_df['price_change_pct'] >= min_price_change) &
                        (latest_df['pe_ratio'] <= max_pe) &
                        (latest_df['pb_ratio'] <= max_pb) &
                        (latest_df['ps_ratio'] <= max_ps)
                    ]
                    
                    # Apply sector filter
                    if selected_sectors:
                        filtered = filtered[filtered['sector'].isin(selected_sectors)]
                    
                    # Apply ticker filter
                    if selected_tickers:
                        filtered = filtered[filtered['ticker'].isin(selected_tickers)]
                    
                    results = filtered.sort_values('money_flow_normalized', ascending=False)
                    
                    if not results.empty:
                        st.success(f"✅ Tìm thấy {len(results)} mã thỏa mãn tiêu chí")
                        
                        # Store results in session state for export
                        st.session_state['screening_results'] = results
                        
                        # Display results
                        display_cols = ['ticker', 'sector', 'close', 'money_flow_normalized', 
                                       'price_change_pct', 'pe_ratio', 'pb_ratio', 'ps_ratio']
                        st.dataframe(
                            results[display_cols].style.format({
                                'close': '{:.2f}',
                                'money_flow_normalized': '{:.2f}',
                                'price_change_pct': '{:+.2f}%',
                                'pe_ratio': '{:.1f}',
                                'pb_ratio': '{:.2f}',
                                'ps_ratio': '{:.2f}'
                            }).background_gradient(subset=['money_flow_normalized'], cmap='RdYlGn'),
                            use_container_width=True
                        )
                    else:
                        st.warning("⚠️ Không tìm thấy mã nào thỏa mãn tiêu chí")
                        st.session_state['screening_results'] = pd.DataFrame()
            else:
                # Traditional screening
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
                    
                    # Store results in session state
                    st.session_state['screening_results'] = results
                    
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
                else:
                    st.warning("⚠️ Không tìm thấy mã nào thỏa mãn tiêu chí. Hãy thử giảm ngưỡng lọc.")
                    st.session_state['screening_results'] = pd.DataFrame()
    
    # Export section
    if 'screening_results' in st.session_state and not st.session_state['screening_results'].empty:
        st.markdown("---")
        st.markdown("### 📤 Export Kết Quả")
        
        results_df = st.session_state['screening_results']
        
        # Multi-select for export
        col1, col2 = st.columns([3, 1])
        with col1:
            selected_for_export = st.multiselect(
                "Chọn mã để export vào Watchlist",
                options=results_df['ticker'].tolist(),
                default=results_df['ticker'].head(5).tolist() if len(results_df) >= 5 else results_df['ticker'].tolist(),
                help="Chọn các mã bạn muốn thêm vào danh sách theo dõi"
            )
        
        with col2:
            if st.button("📊 Export to Sheets", type="primary", use_container_width=True, disabled=len(selected_for_export) == 0):
                if selected_for_export:
                    with st.spinner(f"Đang export {len(selected_for_export)} mã..."):
                        try:
                            # Get spreadsheet
                            creds = get_google_credentials()
                            client = gspread.authorize(creds)
                            spreadsheet_id = os.getenv("SPREADSHEET_ID")
                            if spreadsheet_id:
                                spreadsheet = client.open_by_key(spreadsheet_id)
                            else:
                                spreadsheet = client.open("stockdata")
                            
                            # Get or create watchlist sheet
                            try:
                                watchlist_ws = spreadsheet.worksheet("watchlist")
                            except:
                                watchlist_ws = spreadsheet.add_worksheet(title="watchlist", rows=1000, cols=10)
                                watchlist_ws.update('A1:F1', [['ticker', 'added_date', 'source', 'note', 'pe', 'pb']])
                            
                            # Get existing data
                            existing_data = watchlist_ws.get_all_records()
                            existing_tickers = [row['ticker'] for row in existing_data] if existing_data else []
                            
                            # Prepare new rows
                            new_rows = []
                            added_count = 0
                            skipped_count = 0
                            
                            for ticker in selected_for_export:
                                if ticker not in existing_tickers:
                                    ticker_data = results_df[results_df['ticker'] == ticker].iloc[0]
                                    new_row = [
                                        ticker,
                                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                        'realtime_screening' if realtime_mode else 'financial_screening',
                                        f"Auto-added from screening",
                                        float(ticker_data.get('pe_ratio', ticker_data.get('pe', 0))),
                                        float(ticker_data.get('pb_ratio', ticker_data.get('pb', 0)))
                                    ]
                                    new_rows.append(new_row)
                                    added_count += 1
                                else:
                                    skipped_count += 1
                            
                            # Append new rows
                            if new_rows:
                                watchlist_ws.append_rows(new_rows)
                            
                            if added_count > 0:
                                st.success(f"✅ Đã thêm {added_count} mã vào watchlist!")
                            if skipped_count > 0:
                                st.info(f"ℹ️ Bỏ qua {skipped_count} mã đã có trong watchlist")
                            
                        except Exception as e:
                            st.error("❌ Lỗi khi export: ")
                            import traceback
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
