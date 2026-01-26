# GitHub Actions Setup Guide

## Required Secrets

Để GitHub Actions tự động chạy, bạn cần thêm 3 secrets vào repository:

### 1. GOOGLE_CREDENTIALS

**Nội dung:** JSON credentials từ Google Service Account

**Cách lấy:**
1. Vào [Google Cloud Console](https://console.cloud.google.com/)
2. Chọn project của bạn
3. IAM & Admin → Service Accounts
4. Chọn service account đang dùng
5. Keys → Add Key → Create new key → JSON
6. Download file JSON
7. Copy toàn bộ nội dung file JSON

**Cách thêm vào GitHub:**
1. Vào repository: https://github.com/vuonghtfast/stockvn
2. Settings → Secrets and variables → Actions
3. New repository secret
4. Name: `GOOGLE_CREDENTIALS`
5. Value: Paste toàn bộ nội dung JSON
6. Add secret

### 2. SPREADSHEET_ID

**Nội dung:** ID của Google Sheets

**Cách lấy:**
- Mở Google Sheets
- URL sẽ có dạng: `https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit`
- Copy phần `SPREADSHEET_ID`

**Ví dụ:**
```
URL: https://docs.google.com/spreadsheets/d/1abc123xyz/edit
SPREADSHEET_ID: 1abc123xyz
```

**Cách thêm vào GitHub:**
1. Settings → Secrets and variables → Actions
2. New repository secret
3. Name: `SPREADSHEET_ID`
4. Value: Paste SPREADSHEET_ID
5. Add secret

### 3. VNSTOCK_API_KEY

**Nội dung:** API key từ vnstock (optional nhưng khuyến nghị)

**Cách lấy:**
1. Đăng ký tại [vnstock.site](https://vnstock.site/)
2. Lấy API key từ dashboard
3. Với API key: 60 requests/phút
4. Không có API key: 20 requests/phút

**Cách thêm vào GitHub:**
1. Settings → Secrets and variables → Actions
2. New repository secret
3. Name: `VNSTOCK_API_KEY`
4. Value: Paste API key
5. Add secret

## Kiểm Tra Workflows

Sau khi thêm secrets:

1. **Vào Actions tab:** https://github.com/vuonghtfast/stockvn/actions
2. **Kiểm tra workflows:**
   - `Update Money Flow` - Chạy mỗi 15 phút trong giờ giao dịch
   - `Cleanup Intraday` - Chạy lúc 15:00 ICT hàng ngày

3. **Test thủ công:**
   - Vào workflow → Run workflow → Run workflow
   - Xem logs để kiểm tra

## Lịch Chạy Tự Động

### Update Money Flow
- **Sáng**: 9:30, 9:45, 10:00, 10:15, 10:30, 10:45, 11:00, 11:15, 11:30
- **Chiều**: 13:30, 13:45, 14:00, 14:15, 14:30, 14:45
- **Tổng**: 15 lần/ngày
- **Chỉ chạy**: Thứ 2-6 (trừ cuối tuần và ngày lễ)

### Cleanup Intraday
- **Thời gian**: 15:00 ICT (sau khi đóng cửa)
- **Chức năng**: Xóa dữ liệu intraday, giữ lại summary

## Quota GitHub Actions

- **Free tier**: 2,000 phút/tháng
- **Ước tính sử dụng**: ~660 phút/tháng (15 runs × 2 phút × 22 ngày)
- **Dư**: ~1,340 phút cho workflows khác

## Troubleshooting

### Workflow không chạy
1. Kiểm tra secrets đã thêm đúng chưa
2. Kiểm tra branch `main` đã có workflows chưa
3. Xem logs trong Actions tab

### Lỗi authentication
1. Kiểm tra `GOOGLE_CREDENTIALS` format JSON đúng
2. Kiểm tra service account có quyền truy cập Sheets
3. Kiểm tra `SPREADSHEET_ID` đúng

### Lỗi API quota
1. Thêm `VNSTOCK_API_KEY` để tăng quota
2. Giảm số lần chạy trong workflows
3. Kiểm tra logs để xem request nào bị fail

## Next Steps

Sau khi setup xong:
1. Đợi đến giờ giao dịch để workflows tự chạy
2. Kiểm tra Google Sheets có dữ liệu mới
3. Mở dashboard để xem tab "Dòng Tiền"
