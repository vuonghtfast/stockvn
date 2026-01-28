# -*- coding: utf-8 -*-
"""
Script to restore emoji characters in Python files
Reverses the emoji-to-ASCII replacement
"""

import os
import re
from pathlib import Path

# Reverse mapping - ASCII back to emoji
EMOJI_RESTORE = {
    '[OK]': '✅',
    '[ERROR]': '❌',
    '[HOT]': '🔥',
    '[MONEY]': '💰',
    '[CHART]': '📊',
    '[UP]': '📈',
    '[DOWN]': '📉',
    '[CASH]': '💸',
    '[SEARCH]': '🔍',
    '[LIST]': '📋',
    '[WEB]': '🌐',
    '[LAB]': '🔬',
    '[SETTINGS]': '⚙️',
    '[HOME]': '🏠',
    '[POWER]': '⚡',
    '[LIVE]': '🔴',
    '[INFO]': '💡',
    '[WARN]': '⚠️',
    '[TARGET]': '🎯',
    '[CALENDAR]': '📅',
    '[TIME]': '🕐',
    '[ADD]': '➕',
    '[REMOVE]': '➖',
    '[STAR]': '✨',
    '[ROCKET]': '🚀',
    '[PARTY]': '🎉',
    '[UP_FINGER]': '👆',
    '[REFRESH]': '🔄',
    '[DOC]': '📄',
    '[RIGHT]': '➡️',
    '[CIRCLE]': '⭕',
    '[BELL]': '🔔',
}

def restore_emojis_in_file(filepath):
    """Restore all emojis in a Python file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes_made = False
        
        # Replace each ASCII tag with emoji
        for ascii_tag, emoji in EMOJI_RESTORE.items():
            if ascii_tag in content:
                content = content.replace(ascii_tag, emoji)
                changes_made = True
        
        if changes_made:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, filepath
        
        return False, None
        
    except Exception as e:
        print(f"[X] Failed to process {filepath}: {e}")
        return False, None

def main():
    """Process all Python files in the current directory"""
    current_dir = Path(__file__).parent
    python_files = list(current_dir.glob('*.py'))
    
    print(f"[CHART] Found {len(python_files)} Python files")
    print(f"⚡ Starting emoji restoration...")
    print()
    
    modified_files = []
    
    for py_file in python_files:
        # Skip this script itself
        if py_file.name == 'restore_emojis.py':
            continue
            
        changed, filepath = restore_emojis_in_file(py_file)
        if changed:
            modified_files.append(py_file.name)
            print(f"[OK] Restored: {py_file.name}")
    
    print()
    print(f"[OK] Restored {len(modified_files)} files:")
    for filename in modified_files:
        print(f"  - {filename}")
    
    if not modified_files:
        print("[i] No files needed restoration")

if __name__ == '__main__':
    main()
