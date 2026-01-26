# Fix escaped quotes in dashboard.py

with open('e:/Cao Phi/Code/stockvn/dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the malformed f-strings
content = content.replace('f"{latest[\\'high\\']:,.2f}"', 'f"{latest[\'high\']:,.2f}"')
content = content.replace('f"{latest[\\'low\\']:,.2f}"', 'f"{latest[\'low\']:,.2f}"')
content = content.replace('f"{latest[\\'close\\']:,.2f}"', 'f"{latest[\'close\']:,.2f}"')

with open('e:/Cao Phi/Code/stockvn/dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed escaped quotes")
