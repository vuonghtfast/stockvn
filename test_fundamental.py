# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from technical_analysis import fetch_fundamental_data

data = fetch_fundamental_data('CTR')
print("CTR Fundamental Data:")
for k, v in data.items():
    print(f"  {k}: {v}")
