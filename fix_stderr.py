# Completely suppress stderr in subprocess calls
import re

with open('dashboard_tabs.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace capture_output=True with stdout only capture and stderr to DEVNULL
content = content.replace(
    "capture_output=True,",
    "stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,"
)

# Also need to add import subprocess.DEVNULL - but DEVNULL is in subprocess module
# Need to use subprocess.DEVNULL which should work

with open('dashboard_tabs.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed: stderr is now suppressed in subprocess calls")
