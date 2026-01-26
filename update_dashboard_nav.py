import sys

# Read dashboard.py
with open('e:/Cao Phi/Code/stockvn/dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the navigation radio and update it to include new tabs
old_nav = '["🏠 Dashboard", "📊 Phân Tích", "💰 Báo Cáo Tài Chính", "🌐 Khuyến Nghị", "🔬 Backtest", "⚙️ Settings"]'
new_nav = '["🏠 Dashboard", "📊 Phân Tích", "💰 Báo Cáo Tài Chính", "💸 Dòng Tiền", "🔍 Lọc Cổ Phiếu", "📋 Danh Sách", "🌐 Khuyến Nghị", "🔬 Backtest", "⚙️ Settings"]'

content = content.replace(old_nav, new_nav)

# Find where to insert the new elif blocks (before "elif page == "🌐 Khuyến Nghị":")
marker = 'elif page == "🌐 Khuyến Nghị":'

new_elif_blocks = '''elif page == "💸 Dòng Tiền":
    render_money_flow_tab()

elif page == "🔍 Lọc Cổ Phiếu":
    render_financial_screening_tab()

elif page == "📋 Danh Sách":
    render_watchlist_tab()

'''

content = content.replace(marker, new_elif_blocks + marker)

# Write back
with open('e:/Cao Phi/Code/stockvn/dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated dashboard.py with new tabs in navigation")
