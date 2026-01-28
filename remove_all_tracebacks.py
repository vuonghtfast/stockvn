# Remove all traceback displays from Python files
import re

files_to_fix = [
    'dashboard.py',
    'dashboard_tabs.py'
]

for filename in files_to_fix:
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remove st.code(traceback.format_exc()) lines
        content = re.sub(r'\s*st\.code\(traceback\.format_exc\(\)\)\s*\n', '\n', content)
        
        # Remove import traceback lines that are standalone
        lines = content.split('\n')
        new_lines = []
        for i, line in enumerate(lines):
            # Skip standalone "import traceback" in exception handlers
            if 'import traceback' in line and line.strip() == 'import traceback':
                # Check if next line has st.code(traceback
                if i + 1 < len(lines) and 'st.code(traceback' in lines[i+1]:
                    continue
            new_lines.append(line)
        
        content = '\n'.join(new_lines)
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Fixed {filename}")
    except Exception as e:
        print(f"Error fixing {filename}: {e}")

print("Done!")
