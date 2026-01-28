# -*- coding: utf-8 -*-
"""
Add money flow and finance scrape buttons to Settings page
"""

with open('dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the location after Quick Actions section
insert_marker = '            st.info("Chạy: `python price.py --period 1w --interval 1D --mode update`")'

# New sections to add
new_sections = '''
    
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
    
    fin_col1, fin_col2 = st.columns(2)
    
    with fin_col1:
        if st.button("📋 Cào Báo Cáo Tài Chính", use_container_width=True, type="primary"):
            with st.spinner("Đang cào báo cáo tài chính..."):
                try:
                    import subprocess
                    result = subprocess.run(
                        [sys.executable, 'finance.py'],
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.DEVNULL,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        timeout=600
                    )
                    if result.returncode == 0:
                        st.success("Hoan tat cao bao cao tai chinh!")
                        st.balloons()
                    else:
                        st.error("Loi khi cao bao cao tai chinh")
                except Exception as e:
                    st.error("Loi he thong")
    
    with fin_col2:
        st.markdown("**Output:** Sheets `income`, `balance`, `cashflow`")
        st.caption("Báo cáo kết quả kinh doanh, bảng cân đối kế toán, lưu chuyển tiền tệ")'''

# Find and insert
idx = content.find(insert_marker)
if idx != -1:
    insert_point = idx + len(insert_marker)
    content = content[:insert_point] + new_sections + content[insert_point:]
    print("[OK] Added money flow and finance scrape buttons")
else:
    print("[X] Could not find insert marker")

# Write back
with open('dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("[DONE] Updated Settings page with new scrape buttons")
