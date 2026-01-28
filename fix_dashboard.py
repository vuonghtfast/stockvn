import sys

# Read dashboard.py
with open('e:/Cao Phi/Code/stockvn/dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the problematic section and fix it
# The issue is missing except block after line 288

# Find "return pd.DataFrame()\n\n# ===== Tab Render Functions =====" 
# and replace with proper except block

old_pattern = """        return pd.DataFrame()

# ===== Tab Render Functions ====="""

new_pattern = """        return pd.DataFrame()
    except Exception as e:
        st.error("Lỗi khi lấy dữ liệu dòng tiền: ")
        return pd.DataFrame()

# ===== Tab Render Functions ====="""

content = content.replace(old_pattern, new_pattern)

# Write back
with open('e:/Cao Phi/Code/stockvn/dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed syntax error in dashboard.py")
