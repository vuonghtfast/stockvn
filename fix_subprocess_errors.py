# Fix subprocess error display in dashboard_tabs.py
with open('dashboard_tabs.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace error display with friendly message
old_patterns = [
    'st.error(f"❌ Lỗi: {result.stderr}")',
    'st.error(f\"❌ Lỗi: {result.stderr}\")',
]

for pattern in old_patterns:
    content = content.replace(pattern, 'st.error("[X] Khong the cao du lieu. Vui long thu lai sau.")')

# Also fix timeout message
content = content.replace('st.error("❌ Timeout sau 5 phút")', 'st.error("[X] Timeout sau 5 phut")')
content = content.replace('st.error("❌ Lỗi: ")', 'st.error("[X] Loi he thong")')

with open('dashboard_tabs.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed subprocess error display in dashboard_tabs.py")
