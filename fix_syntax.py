import re

# Read file
with open('e:/Cao Phi/Code/stockvn/dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the malformed line 1187
# Replace: elif page == "🌐 Khuyến Nghị":")
# With: elif page == "🌐 Khuyến Nghị":
content = content.replace('elif page == "🌐 Khuyến Nghị":")', 'elif page == "🌐 Khuyến Nghị":')

# Remove duplicate elif blocks for Money Flow, Financial Screening, Watchlist
# that appear after line 1187
lines = content.split('\n')
new_lines = []
skip_until_next_elif = False
found_first_money_flow = False

for i, line in enumerate(lines):
    # Check if this is the duplicate Money Flow block (after Khuyến Nghị)
    if 'elif page == "💸 Dòng Tiền":' in line:
        if found_first_money_flow:
            # This is the duplicate, skip it and everything until next major elif
            skip_until_next_elif = True
            continue
        else:
            found_first_money_flow = True
    
    # Stop skipping when we hit Khuyến Nghị content or Backtest
    if skip_until_next_elif and ('elif page == "🔬 Backtest":' in line or 'elif page == "⚙️ Settings":' in line or 'st.markdown' in line and 'Khuyến Nghị' in line):
        skip_until_next_elif = False
    
    if not skip_until_next_elif:
        new_lines.append(line)

content = '\n'.join(new_lines)

# Write back
with open('e:/Cao Phi/Code/stockvn/dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed dashboard.py syntax errors")
