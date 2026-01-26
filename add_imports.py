import sys

# Read dashboard.py
with open('e:/Cao Phi/Code/stockvn/dashboard.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find line 19 (after sectors import) and add new imports
for i, line in enumerate(lines):
    if 'from sectors import get_sector, get_all_sectors' in line:
        # Insert new imports after this line
        lines.insert(i + 1, 'from financial_screening import calculate_all_metrics, screen_by_criteria, calculate_composite_score\n')
        lines.insert(i + 2, 'from watchlist import add_to_watchlist, get_watchlist, update_watchlist_metrics\n')
        break

# Write back
with open('e:/Cao Phi/Code/stockvn/dashboard.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Added missing imports to dashboard.py")
