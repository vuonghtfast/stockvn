# -*- coding: utf-8 -*-
"""
Remove exception details from st.error() calls to avoid encoding issues
"""
import re
from pathlib import Path

def fix_error_calls(filepath):
    """Remove exception variable from st.error calls"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        
        # Pattern 1: st.error(f"... {e}")
        content = re.sub(
            r'st\.error\(f"([^"]*)\{e\}([^"]*)"\)',
            r'st.error("\1\2")',
            content
        )
        
        # Pattern 2: st.error(f'... {e}')
        content = re.sub(
            r"st\.error\(f'([^']*)\{e\}([^']*)'\)",
            r"st.error('\1\2')",
            content
        )
        
        # Pattern 3: st.warning(f"... {e}")
        content = re.sub(
            r'st\.warning\(f"([^"]*)\{e\}([^"]*)"\)',
            r'st.warning("\1\2")',
            content
        )
        
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except:
        return False

current_dir = Path(__file__).parent
count = 0
fixed_files = []

for py_file in current_dir.glob('*.py'):
    if py_file.name == 'fix_all_errors.py':
        continue
    
    if fix_error_calls(py_file):
        count += 1
        fixed_files.append(py_file.name)

with open('fix_errors_result.txt', 'w') as f:
    f.write(f"Fixed {count} files:\n")
    for fname in fixed_files:
        f.write(f"  - {fname}\n")
