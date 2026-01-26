# -*- coding: utf-8 -*-
"""
Vietnam Holiday Checker
Kiểm tra ngày nghỉ lễ Việt Nam
"""

from datetime import datetime, date

# Danh sách ngày lễ cố định Việt Nam (theo dương lịch)
FIXED_HOLIDAYS = [
    (1, 1),   # Tết Dương lịch
    (4, 30),  # 30/4 - Giải phóng miền Nam
    (5, 1),   # Quốc tế Lao động
    (9, 2),   # Quốc khánh
]

# Ngày lễ Tết Âm lịch (cần cập nhật hàng năm)
# Format: (year, [(month, day), ...])
LUNAR_NEW_YEAR = {
    2024: [(2, 8), (2, 9), (2, 10), (2, 11), (2, 12), (2, 13), (2, 14)],  # 29 Tết - 6 Tết
    2025: [(1, 27), (1, 28), (1, 29), (1, 30), (1, 31), (2, 1), (2, 2), (2, 3), (2, 4)],  # 29 Tết - 7 Tết
    2026: [(2, 15), (2, 16), (2, 17), (2, 18), (2, 19), (2, 20), (2, 21)],  # 29 Tết - 6 Tết
    2027: [(2, 5), (2, 6), (2, 7), (2, 8), (2, 9), (2, 10), (2, 11)],  # 29 Tết - 6 Tết
}

# Ngày Giỗ Tổ Hùng Vương (10/3 Âm lịch, cần cập nhật hàng năm)
HUNG_VUONG = {
    2024: (4, 18),
    2025: (4, 7),
    2026: (4, 26),
    2027: (4, 16),
}

def is_weekend(check_date=None):
    """Kiểm tra có phải cuối tuần không (Thứ 7, Chủ nhật)"""
    if check_date is None:
        check_date = datetime.now().date()
    elif isinstance(check_date, datetime):
        check_date = check_date.date()
    
    # 5 = Saturday, 6 = Sunday
    return check_date.weekday() >= 5

def is_holiday(check_date=None):
    """Kiểm tra có phải ngày lễ không"""
    if check_date is None:
        check_date = datetime.now().date()
    elif isinstance(check_date, datetime):
        check_date = check_date.date()
    
    month, day = check_date.month, check_date.day
    year = check_date.year
    
    # Kiểm tra ngày lễ cố định
    if (month, day) in FIXED_HOLIDAYS:
        return True
    
    # Kiểm tra Tết Âm lịch
    if year in LUNAR_NEW_YEAR:
        if (month, day) in LUNAR_NEW_YEAR[year]:
            return True
    
    # Kiểm tra Giỗ Tổ Hùng Vương
    if year in HUNG_VUONG:
        if (month, day) == HUNG_VUONG[year]:
            return True
    
    return False

def is_trading_day(check_date=None):
    """Kiểm tra có phải ngày giao dịch không (không phải cuối tuần và ngày lễ)"""
    if check_date is None:
        check_date = datetime.now().date()
    elif isinstance(check_date, datetime):
        check_date = check_date.date()
    
    return not (is_weekend(check_date) or is_holiday(check_date))

def is_trading_hours(check_time=None):
    """Kiểm tra có phải giờ giao dịch không"""
    if check_time is None:
        check_time = datetime.now()
    
    # Kiểm tra ngày giao dịch
    if not is_trading_day(check_time):
        return False
    
    # Kiểm tra giờ giao dịch
    hour = check_time.hour
    minute = check_time.minute
    
    # Phiên sáng: 9:00 - 11:30
    morning_start = (9, 0)
    morning_end = (11, 30)
    
    # Phiên chiều: 13:00 - 15:00
    afternoon_start = (13, 0)
    afternoon_end = (15, 0)
    
    current_time = (hour, minute)
    
    is_morning = morning_start <= current_time <= morning_end
    is_afternoon = afternoon_start <= current_time <= afternoon_end
    
    return is_morning or is_afternoon

if __name__ == "__main__":
    # Test
    now = datetime.now()
    print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Is weekend: {is_weekend()}")
    print(f"Is holiday: {is_holiday()}")
    print(f"Is trading day: {is_trading_day()}")
    print(f"Is trading hours: {is_trading_hours()}")
