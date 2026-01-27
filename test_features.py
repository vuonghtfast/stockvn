# Test Script for Stock Analysis Platform
# Run this to verify all new features

import sys
import os

print("=" * 60)
print("STOCK ANALYSIS PLATFORM - TEST SUITE")
print("=" * 60)

# Test 1: Config System
print("\n[TEST 1] Config System")
print("-" * 60)
try:
    from config import get_config
    config = get_config()
    print("[OK] Config loaded successfully")
    print(f"   - Update interval: {config.get('update_interval_minutes')} minutes")
    print(f"   - Data retention: {config.get('data_retention_days')} days")
    print(f"   - Historical years: {config.get('historical_years')} years")
except Exception as e:
    print(f"[X] Config test failed: {e}")
    sys.exit(1)

# Test 2: Database Initialization
print("\n[TEST 2] Database Initialization")
print("-" * 60)
try:
    from data_archiver import init_database, DB_PATH
    init_database()
    if os.path.exists(DB_PATH):
        print(f"[OK] Database created: {DB_PATH}")
        print(f"   - Size: {os.path.getsize(DB_PATH) / 1024:.2f} KB")
    else:
        print("[!] Database file not found (will be created on first archive)")
except Exception as e:
    print(f"[X] Database test failed: {e}")

# Test 3: Price Data Collection
print("\n[TEST 3] Price Data Collection")
print("-" * 60)
print("[!] This will fetch real data from TCBS API")
response = input("Continue? (y/n): ")
if response.lower() == 'y':
    try:
        print("Running price.py...")
        os.system("python price.py")
        print("[OK] Price collection completed")
        print("   Check Google Sheets:")
        print("   - Sheet 'data' should have latest prices")
        print("   - Sheet 'price_history' should have appended data")
    except Exception as e:
        print(f"[X] Price collection failed: {e}")
else:
    print("[SKIP] Skipped")

# Test 4: Alert System
print("\n[TEST 4] Alert System")
print("-" * 60)
print("[!] This will check alerts and may send Telegram messages")
response = input("Continue? (y/n): ")
if response.lower() == 'y':
    try:
        print("Running alerts.py...")
        os.system("python alerts.py")
        print("[OK] Alert check completed")
        print("   Check:")
        print("   - Sheet 'alerts' created with sample data")
        print("   - Sheet 'alert_history' created")
        print("   - Telegram messages sent (if any alerts triggered)")
    except Exception as e:
        print(f"[X] Alert test failed: {e}")
else:
    print("[SKIP] Skipped")

# Test 5: Data Archival
print("\n[TEST 5] Data Archival")
print("-" * 60)
print("[!] This will move old data from Sheets to SQLite")
response = input("Continue? (y/n): ")
if response.lower() == 'y':
    try:
        print("Running data_archiver.py...")
        os.system("python data_archiver.py")
        print("[OK] Data archival completed")
        print("   Check:")
        print("   - data/stockvn.db file created/updated")
        print("   - Sheet 'price_history' cleaned (only recent data)")
    except Exception as e:
        print(f"[X] Archival test failed: {e}")
else:
    print("[SKIP] Skipped")

# Test 6: Data Aggregation
print("\n[TEST 6] Data Aggregation")
print("-" * 60)
print("[!] This requires historical data in SQLite")
response = input("Continue? (y/n): ")
if response.lower() == 'y':
    try:
        print("Running data_aggregator.py...")
        os.system("python data_aggregator.py")
        print("[OK] Data aggregation completed")
        print("   Check:")
        print("   - SQLite tables: price_weekly, price_monthly")
        print("   - ATR and support/resistance levels printed")
    except Exception as e:
        print(f"[X] Aggregation test failed: {e}")
else:
    print("[SKIP] Skipped")

print("\n" + "=" * 60)
print("TEST SUITE COMPLETED")
print("=" * 60)
print("\nNext Steps:")
print("1. Check Google Sheets for new sheets (config, price_history, alerts, alert_history)")
print("2. Verify data/stockvn.db file exists")
print("3. Test Telegram alerts by setting low thresholds")
print("4. Monitor GitHub Actions workflows")
