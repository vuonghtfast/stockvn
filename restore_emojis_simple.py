# -*- coding: utf-8 -*-
import os
from pathlib import Path

# ASCII to emoji mapping
RESTORE = {
    '[OK]': '✅', '[ERROR]': '❌', '[HOT]': '🔥', '[MONEY]': '💰',
    '[CHART]': '📊', '[UP]': '📈', '[DOWN]': '📉', '[CASH]': '💸',
    '[SEARCH]': '🔍', '[LIST]': '📋', '[WEB]': '🌐', '[LAB]': '🔬',
    '[SETTINGS]': '⚙️', '[HOME]': '🏠', '[POWER]': '⚡', '[LIVE]': '🔴',
    '[INFO]': '💡', '[WARN]': '⚠️', '[TARGET]': '🎯', '[CALENDAR]': '📅',
    '[TIME]': '🕐', '[ADD]': '➕', '[REMOVE]': '➖', '[STAR]': '✨',
    '[ROCKET]': '🚀', '[PARTY]': '🎉', '[UP_FINGER]': '👆',
    '[REFRESH]': '🔄', '[DOC]': '📄', '[RIGHT]': '➡️',
    '[CIRCLE]': '⭕', '[BELL]': '🔔',
}

current_dir = Path(__file__).parent
count = 0

for py_file in current_dir.glob('*.py'):
    if py_file.name in ['restore_emojis.py', 'restore_emojis_simple.py']:
        continue
    
    try:
        with open(py_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        for ascii_tag, emoji in RESTORE.items():
            content = content.replace(ascii_tag, emoji)
        
        if content != original:
            with open(py_file, 'w', encoding='utf-8') as f:
                f.write(content)
            count += 1
    except:
        pass

# Write result to file instead of printing
with open('restore_result.txt', 'w') as f:
    f.write(f"Restored emojis in {count} files\n")
