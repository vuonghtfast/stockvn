# Enhanced Recommendation Section for dashboard.py
# This replaces lines 485-568

elif page == "🌐 Khuyến Nghị":
    st.markdown('<div class="main-header">🎯 Khuyến Nghị Đầu Tư</div>', unsafe_allow_html=True)
    
    st.warning("⚠️ **TUYÊN BỐ MIỄN TRỪ TRÁCH NHIỆM:** Đây chỉ là hệ thống hỗ trợ ra quyết định dựa trên dữ liệu lịch sử. Kết quả không đảm bảo lợi nhuận trong tương lai. Bạn hoàn toàn chịu trách nhiệm về các quyết định đầu tư của mình.")
    
    def calculate_recommendation_score(symbol):
        """Calculate recommendation score for a stock"""
        try:
            # 1. Technical Score
            end_date = datetime.now()
            start_date = end_date - timedelta(days=60)
            df = fetch_stock_data(symbol, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
            
            tech_score = 50
            tech_reasons = []
            current_price = 0
            
            if not df.empty and len(df) > 20:
                current_price = df['close'].iloc[-1]
                
                # RSI check
                delta = df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs)).iloc[-1]
                
                if rsi < 30: 
                    tech_score += 20
                    tech_reasons.append("✅ RSI Quá bán - Cơ hội hồi phục")
                elif rsi > 70:
                    tech_score -= 20
                    tech_reasons.append("❌ RSI Quá mua - Rủi ro điều chỉnh")
                else:
                    tech_reasons.append(f"ℹ️ RSI: {rsi:.1f} - Trung lập")
                
                # MA check
                sma20 = df['close'].rolling(window=20).mean().iloc[-1]
                if current_price > sma20:
                    tech_score += 15
                    tech_reasons.append("✅ Giá trên MA20 - Xu hướng tốt")
                else:
                    tech_score -= 10
                    tech_reasons.append("❌ Giá dưới MA20 - Xu hướng yếu")
            
            # 2. Fundamental Score
            fund_score = 50
            fund_reasons = []
            income_df = fetch_financial_sheet("income")
            if not income_df.empty:
                ticker_income = income_df[income_df['ticker'].astype(str).str.upper() == symbol]
                if not ticker_income.empty and len(ticker_income) >= 2:
                    current = ticker_income.iloc[-1]
                    prev = ticker_income.iloc[-2]
                    
                    if 'revenue' in current and 'revenue' in prev and prev['revenue'] != 0:
                        rev_growth = (current['revenue'] - prev['revenue']) / prev['revenue']
                        if rev_growth > 0.1:
                            fund_score += 15
                            fund_reasons.append(f"✅ Doanh thu tăng mạnh (+{rev_growth:.1%})")
                        elif rev_growth < 0:
                            fund_score -= 10
                            fund_reasons.append(f"❌ Doanh thu giảm ({rev_growth:.1%})")
                        else:
                            fund_reasons.append(f"ℹ️ Doanh thu: {rev_growth:+.1%}")
                    
                    if 'net_income' in current and 'net_income' in prev and prev['net_income'] != 0:
                        profit_growth = (current['net_income'] - prev['net_income']) / prev['net_income']
                        if profit_growth > 0.1:
                            fund_score += 15
                            fund_reasons.append(f"✅ Lợi nhuận tăng tốt (+{profit_growth:.1%})")
                        elif profit_growth < 0:
                            fund_score -= 10
                            fund_reasons.append(f"❌ Lợi nhuận giảm ({profit_growth:.1%})")
                        else:
                            fund_reasons.append(f"ℹ️ Lợi nhuận: {profit_growth:+.1%}")
            
            # Final Calculation
            final_score = (tech_score * 0.4 + fund_score * 0.6)
            
            return {
                'symbol': symbol,
                'score': final_score,
                'tech_reasons': tech_reasons,
                'fund_reasons': fund_reasons,
                'current_price': current_price
            }
        except Exception as e:
            return None
    
    # Auto-calculate top 3 recommendations
    st.subheader("🏆 Top 3 Khuyến Nghị Hàng Đầu")
    
    with st.spinner("Đang phân tích tất cả mã..."):
        tickers = fetch_ticker_list()
        recommendations = []
        
        for ticker in tickers[:10]:  # Limit to first 10 for performance
            result = calculate_recommendation_score(ticker)
            if result:
                recommendations.append(result)
        
        # Sort by score
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        top_3 = recommendations[:3]
        
        # Display top 3
        for i, rec in enumerate(top_3, 1):
            with st.expander(f"#{i} - {rec['symbol']} | Điểm: {rec['score']:.1f}/100 | Giá: {rec['current_price']:,.0f} VNĐ", expanded=(i==1)):
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.metric("TỔNG ĐIỂM", f"{rec['score']:.1f}/100")
                    if rec['score'] > 70:
                        st.success("💪 TÍN HIỆU: MUA")
                    elif rec['score'] < 40:
                        st.error("📉 TÍN HIỆU: BÁN")
                    else:
                        st.warning("⚖️ TÍN HIỆU: THEO DÕI")
                    
                    # Financial metrics
                    metrics = calculate_financial_metrics(rec['symbol'])
                    if metrics:
                        st.markdown("**Chỉ số tài chính:**")
                        if 'ROE' in metrics:
                            st.write(f"ROE: {metrics['ROE']:.2f}%")
                        if 'profit_margin' in metrics:
                            st.write(f"Profit Margin: {metrics['profit_margin']:.2f}%")
                
                with col2:
                    st.markdown("**📊 Phân tích kỹ thuật:**")
                    for reason in rec['tech_reasons']:
                        st.write(reason)
                    
                    st.markdown("**💰 Phân tích cơ bản:**")
                    for reason in rec['fund_reasons']:
                        st.write(reason)
    
    st.markdown("---")
    
    # Multi-select for additional stocks
    st.subheader("📋 Xem thêm khuyến nghị")
    additional_tickers = st.multiselect(
        "Chọn mã để xem phân tích chi tiết",
        options=[t for t in tickers if t not in [r['symbol'] for r in top_3]],
        max_selections=5
    )
    
    if additional_tickers:
        for ticker in additional_tickers:
            rec = calculate_recommendation_score(ticker)
            if rec:
                with st.expander(f"{rec['symbol']} | Điểm: {rec['score']:.1f}/100 | Giá: {rec['current_price']:,.0f} VNĐ"):
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        st.metric("TỔNG ĐIỂM", f"{rec['score']:.1f}/100")
                        if rec['score'] > 70:
                            st.success("💪 TÍN HIỆU: MUA")
                        elif rec['score'] < 40:
                            st.error("📉 TÍN HIỆU: BÁN")
                        else:
                            st.warning("⚖️ TÍN HIỆU: THEO DÕI")
                        
                        metrics = calculate_financial_metrics(rec['symbol'])
                        if metrics:
                            st.markdown("**Chỉ số tài chính:**")
                            if 'ROE' in metrics:
                                st.write(f"ROE: {metrics['ROE']:.2f}%")
                            if 'profit_margin' in metrics:
                                st.write(f"Profit Margin: {metrics['profit_margin']:.2f}%")
                    
                    with col2:
                        st.markdown("**📊 Phân tích kỹ thuật:**")
                        for reason in rec['tech_reasons']:
                            st.write(reason)
                        
                        st.markdown("**💰 Phân tích cơ bản:**")
                        for reason in rec['fund_reasons']:
                            st.write(reason)

elif page == "⚙️ Settings":
