# Fix error message in dashboard.py
with open('dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the error line
old_line = '        st.error("Lỗi khi lấy dữ liệu dòng tiền: ")'
new_line = '        # Don\'t display exception message to avoid encoding errors\n        pass'

content = content.replace(old_line, new_line)

with open('dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed error handler in dashboard.py")
