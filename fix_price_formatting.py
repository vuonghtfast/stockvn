# Script to fix price formatting in dashboard.py
# Replace :.0f with :.2f for price displays

import re

# Read dashboard.py
with open('e:/Cao Phi/Code/stockvn/dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix price formatting patterns
# Pattern 1: st.metric with :.0f for prices
content = re.sub(
    r'st\.metric\("Cao nhất", f"{latest\[\'high\'\]:,\.0f}"\)',
    r'st.metric("Cao nhất", f"{latest[\'high\']:,.2f}")',
    content
)

content = re.sub(
    r'st\.metric\("Thấp nhất", f"{latest\[\'low\'\]:,\.0f}"\)',
    r'st.metric("Thấp nhất", f"{latest[\'low\']:,.2f}")',
    content
)

# Pattern 2: Giá đóng cửa (find and replace)
content = re.sub(
    r'(st\.metric\("Giá đóng cửa",\s*f"{[^}]+):,\.0f}',
    r'\1:,.2f}',
    content
)

# Pattern 3: Any price-related metrics with :.0f that should be :.2f
# But keep volume as :.0f (integer)
lines = content.split('\n')
new_lines = []

for line in lines:
    # Skip if it's volume
    if 'Khối lượng' in line or 'volume' in line.lower():
        new_lines.append(line)
        continue
    
    # Fix price metrics
    if 'st.metric' in line and ('Giá' in line or 'Cao' in line or 'Thấp' in line or 'high' in line or 'low' in line or 'close' in line):
        # Replace :.0f with :.2f
        line = line.replace(':,.0f}', ':,.2f}')
    
    new_lines.append(line)

content = '\n'.join(new_lines)

# Write back
with open('e:/Cao Phi/Code/stockvn/dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed price formatting in dashboard.py")
