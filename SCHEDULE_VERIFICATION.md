# GitHub Actions Schedule Verification

## Giờ giao dịch Việt Nam
- **Sáng**: 9:30 - 11:30 (2 giờ)
- **Chiều**: 13:30 - 14:45 (1 giờ 15 phút)

## Chuyển đổi sang UTC (GitHub Actions sử dụng UTC)
**Vietnam ICT = UTC + 7**

### Sáng (9:30-11:30 ICT)
- 9:30 ICT = 2:30 UTC
- 9:45 ICT = 2:45 UTC
- 10:00 ICT = 3:00 UTC
- 10:15 ICT = 3:15 UTC
- 10:30 ICT = 3:30 UTC
- 10:45 ICT = 3:45 UTC
- 11:00 ICT = 4:00 UTC
- 11:15 ICT = 4:15 UTC
- 11:30 ICT = 4:30 UTC

### Chiều (13:30-14:45 ICT)
- 13:30 ICT = 6:30 UTC
- 13:45 ICT = 6:45 UTC
- 14:00 ICT = 7:00 UTC
- 14:15 ICT = 7:15 UTC
- 14:30 ICT = 7:30 UTC
- 14:45 ICT = 7:45 UTC

## Cron Schedule trong update_money_flow.yml

```yaml
schedule:
  # Sáng: 9:30-11:30 ICT = 2:30-4:30 UTC
  - cron: '30,45 2 * * 1-5'  # 9:30, 9:45 ICT
  - cron: '0,15,30,45 3 * * 1-5'  # 10:00, 10:15, 10:30, 10:45 ICT
  - cron: '0,15,30 4 * * 1-5'  # 11:00, 11:15, 11:30 ICT
  
  # Chiều: 13:30-14:45 ICT = 6:30-7:45 UTC
  - cron: '30,45 6 * * 1-5'  # 13:30, 13:45 ICT
  - cron: '0,15,30,45 7 * * 1-5'  # 14:00, 14:15, 14:30, 14:45 ICT
```

## Cron Format
`minute hour day month weekday`
- `30,45 2 * * 1-5`: Phút 30 và 45 của giờ 2 UTC, mỗi ngày, thứ 2-6
- `0,15,30,45 3 * * 1-5`: Phút 0, 15, 30, 45 của giờ 3 UTC, mỗi ngày, thứ 2-6
- `1-5`: Thứ 2 đến thứ 6 (Monday to Friday)

## Số lần chạy mỗi ngày
- Sáng: 9 lần (9:30, 9:45, 10:00, 10:15, 10:30, 10:45, 11:00, 11:15, 11:30)
- Chiều: 6 lần (13:30, 13:45, 14:00, 14:15, 14:30, 14:45)
- **Tổng: 15 lần/ngày**

## GitHub Actions Quota Check

### Tính toán quota
```
Số lần chạy/ngày: 15
Thời gian mỗi lần: ~2 phút
Phút sử dụng/ngày: 15 × 2 = 30 phút

Số ngày giao dịch/tháng: ~22 ngày
Tổng phút/tháng: 30 × 22 = 660 phút

GitHub Free Tier: 2,000 phút/tháng
✅ AN TOÀN (660 << 2,000)
```

## Cleanup Schedule
```yaml
schedule:
  - cron: '0 8 * * 1-5'  # 15:00 ICT (8:00 UTC)
```
Chạy vào 15:00 ICT mỗi ngày sau khi kết thúc giao dịch lúc 14:45.

## Kiểm tra thực tế

### Cách 1: Xem GitHub Actions logs
1. Vào repository trên GitHub
2. Click tab "Actions"
3. Xem workflow "Update Money Flow"
4. Kiểm tra thời gian chạy có khớp với giờ Việt Nam không

### Cách 2: Test manual trigger
```bash
# Trigger workflow thủ công
gh workflow run update_money_flow.yml

# Xem kết quả
gh run list --workflow=update_money_flow.yml
```

### Cách 3: Kiểm tra trong Google Sheets
- Xem sheet `intraday_flow`
- Kiểm tra cột `timestamp`
- Đảm bảo timestamp khớp với giờ Việt Nam (9:30, 9:45, 10:00, ...)

## Lưu ý quan trọng

⚠️ **GitHub Actions Free Tier limitations:**
- Workflow có thể delay 5-10 phút trong giờ cao điểm
- Không đảm bảo chạy đúng giây
- Nếu repository private, quota thấp hơn

✅ **Giải pháp nếu delay:**
- Chấp nhận delay 5-10 phút (vẫn OK cho phân tích)
- Hoặc upgrade lên GitHub Pro (3,000 phút/tháng)
- Hoặc self-host runner (unlimited)

## Ví dụ timeline thực tế (ngày 26/01/2026)

```
9:30 ICT  → Workflow chạy lần 1
9:45 ICT  → Workflow chạy lần 2
10:00 ICT → Workflow chạy lần 3
10:15 ICT → Workflow chạy lần 4
10:30 ICT → Workflow chạy lần 5
10:45 ICT → Workflow chạy lần 6
11:00 ICT → Workflow chạy lần 7
11:15 ICT → Workflow chạy lần 8
11:30 ICT → Workflow chạy lần 9

13:30 ICT → Workflow chạy lần 10
13:45 ICT → Workflow chạy lần 11
14:00 ICT → Workflow chạy lần 12
14:15 ICT → Workflow chạy lần 13
14:30 ICT → Workflow chạy lần 14
14:45 ICT → Workflow chạy lần 15

15:00 ICT → Cleanup chạy
```
