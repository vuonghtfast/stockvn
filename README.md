# 📈 Stock Analysis Dashboard

Dashboard phân tích chứng khoán Việt Nam với **tự động hóa hoàn toàn** và **thông báo giá real-time**.

## ✨ Tính Năng

### 🤖 Tự Động Hóa
- ✅ **Cập nhật giá mỗi 10 phút** (9:00-15:00, T2-T6) qua GitHub Actions
- ✅ **Cập nhật báo cáo tài chính** mỗi ngày 9:00 sáng
- ✅ **Thông báo Telegram nâng cao**: Giá, khối lượng, breakout
- ✅ **Lưu trữ Hybrid**: Google Sheets (30 ngày) + SQLite (3-5 năm)

### 📊 Dashboard
- ✅ Biểu đồ nến (candlestick) và khối lượng
- ✅ Metrics real-time (giá, volume, thay đổi %)
- ✅ Auto-refresh UI (tùy chọn 5-30 phút)
- ✅ Dữ liệu từ TCBS (chính xác, ổn định)
- ✅ Lịch sử 3-5 năm cho backtest và phân tích chu kỳ

---

## 🚀 Quick Start

### 1. Cài Đặt

```bash
# Clone repository
git clone https://github.com/your-username/stockvn.git
cd stockvn

# Cài đặt dependencies
pip install -r requirements.txt

# Copy và cấu hình .env
cp .env.example .env
# Sửa .env với credentials của bạn
```

### 2. Chạy Local

```bash
# Test lấy dữ liệu giá
python price.py

# Test lấy báo cáo tài chính
python finance.py

# Chạy dashboard
streamlit run dashboard.py
```

### 3. Deploy Tự Động

Xem hướng dẫn chi tiết trong [DEPLOYMENT.md](DEPLOYMENT.md)

---

## 📁 Cấu Trúc Dự Án

```
stockvn/
├── .github/workflows/       # GitHub Actions workflows
│   ├── update_price.yml     # Cập nhật giá mỗi 10 phút
│   ├── update_finance.yml   # Cập nhật tài chính mỗi ngày
│   └── daily_archival.yml   # Archive data cũ vào SQLite
├── data/                    # SQLite database cho historical data
│   └── stockvn.db           # 3-5 năm lịch sử giá
├── dashboard.py             # Streamlit dashboard
├── price.py                 # Script lấy giá chứng khoán
├── finance.py               # Script lấy báo cáo tài chính
├── alerts.py                # Hệ thống thông báo Telegram (enhanced)
├── config.py                # Centralized configuration
├── data_archiver.py         # Hybrid storage manager
├── data_aggregator.py       # Weekly/monthly aggregation
├── requirements.txt         # Dependencies
├── .env.example             # Template environment variables
└── README.md                # Tài liệu này
```
```

---

## 🔧 Cấu Hình

### Environment Variables

Tạo file `.env` với nội dung:

```bash
# Google Sheets
SPREADSHEET_ID=your_spreadsheet_id
GOOGLE_CREDENTIALS={"type": "service_account", ...}

# Telegram (Tùy chọn)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### Google Sheets Structure

Sheet cần có:
- `tickers`: Danh sách mã chứng khoán
- `config`: Cấu hình hệ thống (tự động tạo)
- `data`: Dữ liệu giá mới nhất (tự động tạo)
- `price_history`: Lịch sử giá 30 ngày gần nhất (tự động tạo)
- `alerts`: Cấu hình ngưỡng giá/khối lượng (tùy chọn)
- `alert_history`: Lịch sử cảnh báo (tự động tạo)
- `income`, `balance`, `cashflow`: Báo cáo tài chính (tự động tạo)

### Alert Types

Hệ thống hỗ trợ 4 loại cảnh báo:
1. **price_below**: Giá xuống dưới ngưỡng
2. **price_above**: Giá vượt ngưỡng
3. **volume_spike**: Khối lượng bất thường (ví dụ: 2x trung bình)
4. **breakout**: Đa điều kiện (giá vượt kháng cự + khối lượng cao)

---

## 📖 Tài Liệu

- [📘 Deployment Guide](DEPLOYMENT.md) - Hướng dẫn triển khai chi tiết
- [🔔 Telegram Setup](DEPLOYMENT.md#bước-1-setup-telegram-bot-tùy-chọn) - Cấu hình thông báo
- [⚙️ GitHub Actions](DEPLOYMENT.md#bước-2-cấu-hình-github-secrets) - Tự động hóa

---

## 🎯 Roadmap

### ✅ Completed (Phase 1-3)
- [x] Tự động cập nhật giá mỗi 10 phút
- [x] Thông báo Telegram nâng cao (giá, khối lượng, breakout)
- [x] Dashboard với auto-refresh
- [x] Hybrid storage (Sheets + SQLite) cho 3-5 năm lịch sử
- [x] Alert cooldown và history tracking
- [x] Data aggregation (weekly/monthly OHLCV)

### 🔄 In Progress (Phase 4-5)
- [ ] Recommendation engine (technical + fundamental analysis)
- [ ] Backtest framework với 3-5 năm dữ liệu
- [ ] Tích hợp tab "Phân Tích" với indicators (MA, RSI, MACD)
- [ ] Tích hợp tab "Báo Cáo Tài Chính"
- [ ] Portfolio performance tracking
- [ ] Risk analysis reports

---

## 🤝 Contributing

Contributions are welcome! Feel free to open issues or pull requests.

---

## 📄 License

MIT License - feel free to use for your own projects!

---

## 🙏 Credits

- [vnstock](https://github.com/thinh-vu/vnstock) - Thư viện lấy dữ liệu chứng khoán VN
- [Streamlit](https://streamlit.io) - Framework dashboard
- [GitHub Actions](https://github.com/features/actions) - CI/CD miễn phí

---

**Made with ❤️ for Vietnamese stock traders**
