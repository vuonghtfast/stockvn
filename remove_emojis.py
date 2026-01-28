# -*- coding: utf-8 -*-
"""
Script to replace all emoji characters in Python files with ASCII equivalents
This fixes Windows console encoding errors
"""

import os
import re
from pathlib import Path

# Emoji replacement mapping
EMOJI_REPLACEMENTS = {
    '✅': '✅',
    '❌': '❌',
    '🔥': '🔥',
    '💰': '💰',
    '📊': '📊',
    '📈': '📈',
    '📉': '📉',
    '💸': '💸',
    '🔍': '🔍',
    '📋': '📋',
    '🌐': '🌐',
    '🔬': '🔬',
    '⚙️': '⚙️',
    '🏠': '🏠',
    '⚡': '⚡',
    '🔴': '🔴',
    '💡': '💡',
    '⚠️': '⚠️',
    '🎯': '🎯',
    '📅': '📅',
    '🕐': '🕐',
    '➕': '➕',
    '➖': '➖',
    '✨': '✨',
    '🚀': '🚀',
    '🎉': '🎉',
    '👆': '👆',
    '🔄': '🔄',
    '📄': '📄',
    '➡️': '➡️',
    '⭕': '⭕',
    '🔔': '🔔',
}

def replace_emojis_in_file(filepath):
    """Replace all emojis in a Python file with ASCII equivalents"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes_made = False
        
        # Replace each emoji
        for emoji, replacement in EMOJI_REPLACEMENTS.items():
            if emoji in content:
                content = content.replace(emoji, replacement)
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
    
    print(f"[i] Found {len(python_files)} Python files")
    print(f"[i] Starting emoji replacement...")
    print()
    
    modified_files = []
    
    for py_file in python_files:
        # Skip this script itself
        if py_file.name == 'remove_emojis.py':
            continue
            
        changed, filepath = replace_emojis_in_file(py_file)
        if changed:
            modified_files.append(py_file.name)
            print(f"[OK] Modified: {py_file.name}")
    
    print()
    print(f"[DONE] Modified {len(modified_files)} files:")
    for filename in modified_files:
        print(f"  - {filename}")
    
    if not modified_files:
        print("[i] No files needed modification")

if __name__ == '__main__':
    main()
