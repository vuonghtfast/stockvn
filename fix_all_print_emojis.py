# -*- coding: utf-8 -*-
# Fix ALL emoji in ALL Python files
import re
from pathlib import Path

EMOJI_MAP = {
    '❌': '[X]', '✅': '[OK]', '⚠️': '[!]', '💡': '[i]', '🔥': '[HOT]',
    '💰': '[MONEY]', '📊': '[CHART]', '📈': '[UP]', '📉': '[DOWN]', '💸': '[CASH]',
    '🔍': '[SEARCH]', '📋': '[LIST]', '🌐': '[WEB]', '🔬': '[LAB]', '⚙️': '[SETTINGS]',
    '🏠': '[HOME]', '🔴': '[LIVE]', '🎯': '[TARGET]', '📅': '[CALENDAR]', '➕': '[+]',
    '➖': '[-]', '🔄': '[REFRESH]', '🔔': '[BELL]', '⏭️': '[SKIP]', '✨': '[*]',
    '🚀': '[GO]', '🎉': '[OK]', '👆': '[^]', '📄': '[DOC]', '➡️': '[->]', '⭕': '[O]',
}

def fix_all_print_statements(filepath):
    """Replace emoji in print() statements only"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        
        # Find all print() statements and replace emoji within them
        def replace_emoji_in_print(match):
            print_content = match.group(0)
            for emoji, replacement in EMOJI_MAP.items():
                print_content = print_content.replace(emoji, replacement)
            return print_content
        
        # Match print(...) including multiline
        content = re.sub(r'print\([^)]*\)', replace_emoji_in_print, content)
        
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except:
        return False

# Fix all Python files
current_dir = Path(__file__).parent
fixed = []

for py_file in current_dir.glob('*.py'):
    if py_file.name in ['fix_all_print_emojis.py']:
        continue
    if fix_all_print_statements(py_file):
        fixed.append(py_file.name)

with open('fix_print_result.txt', 'w') as f:
    f.write(f"Fixed {len(fixed)} files:\n")
    for fname in fixed:
        f.write(f"  - {fname}\n")
