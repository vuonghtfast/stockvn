# 📈 Stock Analysis Dashboard

Dashboard phân tích chứng khoán Việt Nam với **tự động hóa hoàn toàn** và **thông báo giá real-time**.

## ✨ Tính Năng

### 🤖 Tự Động Hóa
- ✅ **Cập nhật giá mỗi 5 phút** (9:00-15:00, T2-T6) qua GitHub Actions
- ✅ **Cập nhật báo cáo tài chính** mỗi ngày 9:00 sáng
- ✅ **Thông báo Telegram** khi giá đạt ngưỡng
- ✅ **Lưu trữ Google Sheets** - không mất dữ liệu

### 📊 Dashboard
- ✅ Biểu đồ nến (candlestick) và khối lượng
- ✅ Metrics real-time (giá, volume, thay đổi %)
- ✅ Auto-refresh UI (tùy chọn 5-30 phút)
- ✅ Dữ liệu từ TCBS (chính xác, ổn định)

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
│   ├── update_price.yml     # Cập nhật giá mỗi 5 phút
│   └── update_finance.yml   # Cập nhật tài chính mỗi ngày
├── dashboard.py             # Streamlit dashboard
├── price.py                 # Script lấy giá chứng khoán
├── finance.py               # Script lấy báo cáo tài chính
├── alerts.py                # Hệ thống thông báo Telegram
├── requirements.txt         # Dependencies
├── .env.example             # Template environment variables
└── README.md                # Tài liệu này
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
- `data`: Dữ liệu giá (tự động tạo)
- `alerts`: Cấu hình ngưỡng giá (tùy chọn)
- `income`, `balance`, `cashflow`: Báo cáo tài chính (tự động tạo)

---

## 📖 Tài Liệu

- [📘 Deployment Guide](DEPLOYMENT.md) - Hướng dẫn triển khai chi tiết
- [🔔 Telegram Setup](DEPLOYMENT.md#bước-1-setup-telegram-bot-tùy-chọn) - Cấu hình thông báo
- [⚙️ GitHub Actions](DEPLOYMENT.md#bước-2-cấu-hình-github-secrets) - Tự động hóa

---

## 🎯 Roadmap

- [x] Tự động cập nhật giá mỗi 5 phút
- [x] Thông báo Telegram khi giá đạt ngưỡng
- [x] Dashboard với auto-refresh
- [ ] Tích hợp tab "Phân Tích" với indicators (MA, RSI, MACD)
- [ ] Tích hợp tab "Báo Cáo Tài Chính"
- [ ] Backtesting chiến lược giao dịch

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
