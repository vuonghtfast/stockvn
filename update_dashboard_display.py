# -*- coding: utf-8 -*-
"""
Replace Dashboard Money Flow section with new format
"""

with open('dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Old section to replace (from line 730 to 797)
old_section_start = '    # Money Flow Summary\n    st.markdown("## 💰 Tổng Quan Dòng Tiền")'
old_section_end = '        st.info("💡 Hoặc đợi GitHub Actions tự động cập nhật vào giờ giao dịch.")'

# New section
new_section = '''    # Money Flow Summary - Using new money_flow_top format
    st.markdown("## 💰 Tổng Quan Dòng Tiền Mua-Bán")
    
    stocks_df, positive_sectors, negative_sectors = get_money_flow_top()
    
    if positive_sectors is not None and not positive_sectors.empty:
        # Top 3 sectors with POSITIVE flow (with stocks)
        st.markdown("### 📈 Top 3 Ngành Dòng Tiền MUA Mạnh Nhất")
        
        col1, col2, col3 = st.columns(3)
        for idx, (col, row) in enumerate(zip([col1, col2, col3], positive_sectors.head(3).itertuples())):
            with col:
                st.metric(
                    f"#{idx+1} {row.sector}",
                    f"+{row.net_flow:,.2f}B VNĐ",
                    f"Mua: {row.buy_flow:,.1f}B | Bán: {row.sell_flow:,.1f}B"
                )
        
        st.markdown("---")
        
        # Top 9 stocks (3 per sector)
        if stocks_df is not None and not stocks_df.empty:
            st.markdown("### 🔥 Top 9 Cổ Phiếu Dòng Tiền MUA Mạnh Nhất")
            st.markdown("*(3 cổ phiếu mỗi ngành)*")
            
            # Display in 3 columns per row
            for i in range(0, min(9, len(stocks_df)), 3):
                cols = st.columns(3)
                for j, col in enumerate(cols):
                    if i + j < len(stocks_df):
                        row = stocks_df.iloc[i + j]
                        with col:
                            st.metric(
                                f"{row['ticker']}",
                                f"+{row['net_flow']:,.2f}B VNĐ",
                                f"Giá: {row['price']:,.1f}K",
                                delta_color="normal"
                            )
                            st.caption(f"Ngành: {row['sector']}")
            
            st.markdown("---")
        
        # Top 3 sectors with NEGATIVE flow (sectors only, no stocks)
        if negative_sectors is not None and not negative_sectors.empty:
            st.markdown("### 📉 Top 3 Ngành Dòng Tiền BÁN Mạnh Nhất")
            st.markdown("*(Chỉ hiển thị ngành, không chi tiết cổ phiếu)*")
            
            col1, col2, col3 = st.columns(3)
            for idx, (col, row) in enumerate(zip([col1, col2, col3], negative_sectors.head(3).itertuples())):
                with col:
                    st.metric(
                        f"#{idx+1} {row.sector}",
                        f"{row.net_flow:,.2f}B VNĐ",
                        f"Mua: {row.buy_flow:,.1f}B | Bán: {row.sell_flow:,.1f}B",
                        delta_color="inverse"
                    )
            
            st.markdown("---")
        
        # Timestamp
        if not stocks_df.empty and 'timestamp' in stocks_df.columns:
            st.caption(f"Cap nhat luc: {stocks_df['timestamp'].iloc[0]}")
        
    else:
        st.warning("Chua co du lieu dong tien. Vui long chay `python money_flow.py` de cap nhat.")
        st.info("Hoac doi GitHub Actions tu dong cap nhat vao gio giao dich.")'''

# Find and replace
start_idx = content.find('    # Money Flow Summary')
if start_idx == -1:
    print("[X] Could not find Money Flow Summary section")
else:
    # Find the end (elif page == "📊 Phân Tích":)
    end_marker = 'elif page == "📊 Phân Tích":'
    end_idx = content.find(end_marker, start_idx)
    
    if end_idx != -1:
        content = content[:start_idx] + new_section + "\n\n" + content[end_idx:]
        print("[OK] Replaced Money Flow section")
    else:
        print("[X] Could not find end marker")

# Write back
with open('dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("[DONE] Dashboard updated with new Money Flow display")
