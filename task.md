# Task Breakdown: Dashboard Enhancements

## 1. VN Index Display on Dashboard
- [x] Create `vnindex_fetcher.py` module
  - [x] Implement VN Index data fetching from vnstock
  - [x] Save to Google Sheets `vnindex` sheet
  - [x] Add error handling and retry logic
- [x] Create GitHub Actions workflow `update_vnindex.yml`
  - [x] Schedule for 9:30, 11:00, 14:00, 15:00 (Vietnam time)
  - [x] Add holiday checking (skip weekends and VN holidays)
  - [x] Configure secrets and credentials
- [x] Modify `dashboard.py` main dashboard page
  - [x] Fetch VN Index from Google Sheets
  - [x] Add VN Index hero metric at top
  - [x] Display current value, change, and percentage
  - [x] Style with appropriate colors (green/red)
  - [x] Show last update time
- [ ] Test VN Index display
  - [ ] Verify data fetches correctly from Sheets
  - [ ] Test manual run of vnindex_fetcher.py
  - [ ] Test GitHub Actions workflow
  - [ ] Verify dashboard displays correctly

## 2. Fix Money Flow Tab Data Source
- [x] Investigate current money flow tab implementation
  - [x] Check where `render_money_flow_tab()` is called
  - [x] Verify data source (should be `intraday_flow` sheet)
- [x] Fix navigation and tab rendering
  - [x] Ensure "💸 Dòng Tiền" page calls correct function
  - [x] Remove any duplicate or conflicting code
- [ ] Verify money flow tab displays correctly
  - [ ] Check top 3 sectors with strongest buy flow
  - [ ] Check top 3 stocks with strongest buy flow
  - [ ] Verify data comes from Money Flow tab, not Financial Report tab

## 3. Add Historical Money Flow Days Parameter
- [x] Add UI controls in Money Flow tab
  - [x] Add number input for days (default: 30, range: 7-365)
  - [x] Add "Cào Dữ Liệu Lịch Sử" button
  - [x] Add progress indicator
- [x] Implement script execution from dashboard
  - [x] Create function to run `historical_money_flow.py` with custom days
  - [x] Handle subprocess execution
  - [x] Display results and status
- [ ] Test historical money flow scraping
  - [ ] Test with different day values (30, 60, 90)
  - [ ] Verify data saves to Google Sheets
  - [ ] Check historical_flow and historical_flow_summary sheets

## 4. Real-time Stock Screening with Google Sheets Export
- [x] Enhance stock screening tab UI
  - [x] Add "Real-time Mode" toggle
  - [x] Add multi-select checkboxes for stock selection
  - [x] Add "Export to Watchlist" button
- [x] Implement real-time filtering
  - [x] Integrate with `get_money_flow_data()` for live data
  - [x] Combine with financial screening criteria
  - [x] Update results dynamically
- [x] Implement Google Sheets export
  - [x] Create function to export selected stocks to watchlist sheet
  - [x] Add metadata (date added, filter criteria used)
  - [x] Handle duplicates gracefully
- [ ] Test real-time screening
  - [ ] Test filtering with various criteria
  - [ ] Test stock selection
  - [ ] Test export to Google Sheets
  - [ ] Verify watchlist updates correctly

## Verification Checklist
- [ ] All 4 features implemented and working
- [ ] No breaking changes to existing functionality
- [ ] Dashboard loads without errors
- [ ] All tabs navigate correctly
- [ ] Google Sheets integration works
- [ ] Error handling in place for all new features

## ✅ IMPLEMENTATION COMPLETE!
All 4 features have been implemented:
1. ✅ VN Index Display - Fetches 4x/day via GitHub Actions
2. ✅ Money Flow Tab Fix - Proper navigation and rendering
3. ✅ Historical Money Flow Parameter - Configurable days (7-365)
4. ✅ Real-time Stock Screening - Toggle mode + multi-select export

Ready for testing!
