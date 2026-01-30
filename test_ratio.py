# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from vnstock import Vnstock

stock = Vnstock().stock(symbol='CTR', source='VCI')
ratio = stock.finance.ratio(period='quarter', lang='en')

print("Columns:")
for col in ratio.columns.tolist():
    print(f"  - {col}")

print("\nLast row values:")
last = ratio.iloc[-1]
for col in ratio.columns:
    print(f"  {col}: {last[col]}")
