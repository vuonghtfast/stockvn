# -*- coding: utf-8 -*-
"""
Update dashboard.py to use new money_flow_top sheet format
"""

# Read dashboard.py
with open('dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

# New get_money_flow_data function
new_function = '''
# ===== Money Flow Helper Functions =====
@st.cache_data(ttl=300)  # Cache 5 minutes
def get_money_flow_top():
    """Lay du lieu dong tien tu money_flow_top sheet"""
    try:
        spreadsheet = get_spreadsheet()
        if not spreadsheet:
            return None, None, None
        
        try:
            flow_ws = spreadsheet.worksheet("money_flow_top")
            flow_data = flow_ws.get_all_records()
            flow_df = pd.DataFrame(flow_data)
            
            if flow_df.empty:
                return None, None, None
            
            # Convert numeric columns
            numeric_cols = ['price', 'volume', 'buy_flow', 'sell_flow', 'net_flow']
            for col in numeric_cols:
                if col in flow_df.columns:
                    flow_df[col] = pd.to_numeric(flow_df[col], errors='coerce')
            
            # Split by type
            stocks_df = flow_df[flow_df['type'] == 'stock'].copy()
            positive_sectors = flow_df[flow_df['type'] == 'sector_positive'].copy()
            negative_sectors = flow_df[flow_df['type'] == 'sector_negative'].copy()
            
            return stocks_df, positive_sectors, negative_sectors
        except:
            return None, None, None
    except:
        return None, None, None
'''

# Old function to replace
old_function_start = '# ===== Money Flow Helper Functions ====='
old_function_end = "        return pd.DataFrame()\n\n\n# ===== Tab Render Functions"

# Find and replace
start_idx = content.find(old_function_start)
end_idx = content.find("# ===== Tab Render Functions")

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + new_function + "\n\n" + content[end_idx:]
    print("[OK] Replaced get_money_flow_data function")
else:
    print("[!] Could not find function to replace, appending new function")
    # Insert after imports section
    import_end = content.find("# ===== Helper Functions =====")
    if import_end == -1:
        import_end = content.find("@st.cache_data")
    if import_end != -1:
        content = content[:import_end] + new_function + "\n\n" + content[import_end:]

# Write back
with open('dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("[OK] Updated dashboard.py with new money flow function")
