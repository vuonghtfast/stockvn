# Quick Fix for Dashboard Integration

Để tích hợp nhanh các tab mới vào dashboard.py, làm theo các bước sau:

## Bước 1: Thêm import (dòng 20)

Sau dòng:
```python
from sectors import get_sector, get_all_sectors
```

Thêm:
```python
from dashboard_tabs import render_money_flow_tab, render_financial_screening_tab, render_watchlist_tab
```

## Bước 2: Sửa navigation (dòng 292)

Thay:
```python
["🏠 Dashboard", "📊 Phân Tích", "💰 Báo Cáo Tài Chính", "🌐 Khuyến Nghị", "🔬 Backtest", "⚙️ Settings"],
```

Bằng:
```python
["🏠 Dashboard", "📊 Phân Tích", "💰 Báo Cáo Tài Chính", "💸 Dòng Tiền", "🔍 Lọc Cổ Phiếu", "📋 Danh Sách", "🌐 Khuyến Nghị", "🔬 Backtest", "⚙️ Settings"],
```

## Bước 3: Thêm elif blocks (sau dòng 813, trước elif page == "🌐 Khuyến Nghị":)

Thêm:
```python
elif page == "💸 Dòng Tiền":
    render_money_flow_tab()

elif page == "🔍 Lọc Cổ Phiếu":
    render_financial_screening_tab()

elif page == "📋 Danh Sách":
    render_watchlist_tab()
```

## Hoặc sử dụng dashboard_new.py

Nếu gặp khó khăn, chỉ cần chạy:
```bash
streamlit run dashboard_new.py
```

Dashboard này đã có đầy đủ 3 tính năng mới và hoạt động tốt!
