# Fix traceback display in dashboard.py
with open('dashboard.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Remove lines 86-87 (traceback display)
new_lines = []
skip_next = False
for i, line in enumerate(lines, 1):
    if i == 86 and 'import traceback' in line:
        skip_next = True
        continue
    if i == 87 and 'st.code(traceback' in line:
        continue
    new_lines.append(line)

with open('dashboard.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Removed traceback display from dashboard.py")
