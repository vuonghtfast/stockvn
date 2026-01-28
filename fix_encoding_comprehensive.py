# -*- coding: utf-8 -*-
# Comprehensive fix for all encoding issues
import re

def fix_file(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Fix 1: Remove emoji from st.error, st.warning, st.info, print statements
    emoji_mapping = {
        '❌': '[X]',
        '✅': '[OK]',
        '⚠️': '[!]',
        '💡': '[i]',
        '🔥': '[HOT]',
        '💰': '[MONEY]',
        '📊': '[CHART]',
        '📈': '[UP]',
        '📉': '[DOWN]',
        '💸': '[CASH]',
        '🔍': '[SEARCH]',
        '📋': '[LIST]',
        '🌐': '[WEB]',
        '🔬': '[LAB]',
        '⚙️': '[SETTINGS]',
        '🏠': '[HOME]',
        '🔴': '[LIVE]',
        '🎯': '[TARGET]',
        '📅': '[CALENDAR]',
        '➕': '[+]',
        '➖': '[-]',
        '🔄': '[REFRESH]',
        '🔔': '[BELL]',
    }
    
    # Only replace emoji in print() and st.error/warning/info statements
    for emoji, replacement in emoji_mapping.items():
        # Replace in print statements
        content = re.sub(
            rf'(print\([^)]*){re.escape(emoji)}([^)]*\))',
            rf'\1{replacement}\2',
            content
        )
    
    # Fix 2: Fix f-string issues - ensure strings with {variable} use f"..." prefix
    # Find st.error("...'{sheet_name}'...") without f prefix and add f
    content = re.sub(
        r'st\.error\("([^"]*\{[^}]+\}[^"]*)"\)',
        r'st.error(f"\1")',
        content
    )
    content = re.sub(
        r"st\.error\('([^']*\{[^}]+\}[^']*)'\)",
        r"st.error(f'\1')",
        content
    )
    
    # Fix st.warning similarly
    content = re.sub(
        r'st\.warning\("([^"]*\{[^}]+\}[^"]*)"\)',
        r'st.warning(f"\1")',
        content
    )
    
    if content != original:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

files = ['dashboard.py', 'dashboard_tabs.py', 'watchlist.py', 'config.py', 'price.py', 'finance.py', 
         'stock_screener.py', 'alerts.py', 'ticker_manager.py', 'test_features.py', 'temp_recommendation.py']

fixed = []
for f in files:
    try:
        if fix_file(f):
            fixed.append(f)
    except:
        pass

print(f"Fixed {len(fixed)} files: {', '.join(fixed)}")
