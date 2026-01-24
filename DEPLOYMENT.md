# 🚀 Hướng Dẫn Triển Khai

Xem hướng dẫn chi tiết tại artifact: [deployment_guide.md](file:///C:/Users/Huynh%20The%20Vuong/.gemini/antigravity/brain/352d3e31-1298-48bd-a47b-26f1c38d9fec/deployment_guide.md)

## Tóm Tắt Nhanh

### 1. Setup Telegram Bot (Tùy chọn)
- Tạo bot qua [@BotFather](https://t.me/botfather)
- Lấy BOT_TOKEN và CHAT_ID

### 2. Cấu Hình GitHub Secrets
Thêm vào Settings → Secrets:
- `GOOGLE_CREDENTIALS`
- `SPREADSHEET_ID`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

### 3. Push Code
```bash
git push origin main
```

### 4. Kiểm Tra
- Vào tab **Actions** trên GitHub
- Chạy workflow thủ công để test
- Kiểm tra Google Sheets

### 5. Deploy Dashboard
- Truy cập [share.streamlit.io](https://share.streamlit.io)
- Deploy với secrets tương tự

---

**Xem chi tiết đầy đủ trong artifact deployment_guide.md**
