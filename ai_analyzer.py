# -*- coding: utf-8 -*-
"""
AI Analyzer Module - Multi-Provider Support
Tích hợp Gemini, OpenAI, Anthropic cho phân tích kỹ thuật AI
"""

import os
import json
from datetime import datetime
from typing import Dict, Optional
from dotenv import load_dotenv

# Load environment
load_dotenv()

# ===== AI Provider Clients =====

class AIAnalyzer:
    """
    Multi-provider AI Technical Analysis
    Hỗ trợ: Gemini (default), OpenAI, Anthropic
    """
    
    PROVIDERS = ['gemini', 'openai', 'anthropic']
    
    def __init__(self, provider: str = None):
        """
        Args:
            provider: 'gemini', 'openai', hoặc 'anthropic'
                      Mặc định lấy từ env AI_DEFAULT_PROVIDER hoặc 'gemini'
        """
        self.provider = provider or os.getenv('AI_DEFAULT_PROVIDER', 'gemini')
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Khởi tạo AI client dựa trên provider"""
        if self.provider == 'gemini':
            self._init_gemini()
        elif self.provider == 'openai':
            self._init_openai()
        elif self.provider == 'anthropic':
            self._init_anthropic()
        else:
            raise ValueError(f"Provider không hợp lệ: {self.provider}. Chọn: {self.PROVIDERS}")
    
    def _init_gemini(self):
        """Khởi tạo Google Gemini"""
        try:
            import google.generativeai as genai
            
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise ValueError("Thiếu GEMINI_API_KEY trong .env")
            
            genai.configure(api_key=api_key)
            # Model names: gemini-1.5-flash, gemini-1.5-pro, gemini-pro
            model_name = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')
            self.client = genai.GenerativeModel(model_name)
            self.model_name = model_name
        except ImportError:
            raise ImportError("Cần cài đặt: pip install google-generativeai")
    
    def _init_openai(self):
        """Khởi tạo OpenAI"""
        try:
            from openai import OpenAI
            
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("Thiếu OPENAI_API_KEY trong .env")
            
            self.client = OpenAI(api_key=api_key)
            self.model_name = 'gpt-4-turbo-preview'
        except ImportError:
            raise ImportError("Cần cài đặt: pip install openai")
    
    def _init_anthropic(self):
        """Khởi tạo Anthropic Claude"""
        try:
            import anthropic
            
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("Thiếu ANTHROPIC_API_KEY trong .env")
            
            self.client = anthropic.Anthropic(api_key=api_key)
            self.model_name = 'claude-3-sonnet-20240229'
        except ImportError:
            raise ImportError("Cần cài đặt: pip install anthropic")
    
    # ===== Prompt Building =====
    
    def _build_prompt(self, ticker: str, indicators: Dict) -> str:
        """
        Xây dựng prompt cho AI phân tích kỹ thuật
        
        QUAN TRỌNG: Chỉ phân tích long (mua/bán), không có short
        """
        
        prompt = f"""Bạn là một chuyên gia phân tích kỹ thuật chứng khoán Việt Nam với hơn 20 năm kinh nghiệm.

DỮ LIỆU PHÂN TÍCH CHO MÃ {ticker}:
- Ngày phân tích: {indicators.get('analysis_date', datetime.now().strftime('%d-%m-%Y %H:%M:%S'))}
- Số ngày dữ liệu: {indicators.get('data_days', 0)} ngày

GIÁ:
- Giá hiện tại: {indicators.get('current_price', 0)}

ĐƯỜNG TRUNG BÌNH ĐỘNG:
- MA20: {indicators.get('ma20', 0)}
- MA50: {indicators.get('ma50', 0)}
- MA200: {indicators.get('ma200', 0)}
- Sắp xếp MA: {indicators.get('ma_alignment', 'N/A')}
- Giá trên MA20: {indicators.get('price_above_ma20', 'N/A')}
- MA20 trên MA50: {indicators.get('ma20_above_ma50', 'N/A')}
- MA50 trên MA200: {indicators.get('ma50_above_ma200', 'N/A')}
- Độ dốc MA200 (60 ngày): {indicators.get('ma200_slope_60d', 0)}%

CHỈ BÁO ĐỘNG LƯỢNG:
- RSI (14): {indicators.get('rsi', 50)}
- MACD: {indicators.get('macd', 0)}
- MACD Signal: {indicators.get('macd_signal', 0)}
- MACD Histogram: {indicators.get('macd_histogram', 0)}

KHỐI LƯỢNG:
- Volume Ratio (so với TB 20 ngày): {indicators.get('volume_ratio', 1)}
- Volume Spike: {'Có' if indicators.get('volume_spike', False) else 'Không'}

XU HƯỚNG:
- Xu hướng hiện tại: {indicators.get('trend', 'N/A')}
- Pha Wyckoff: {indicators.get('wyckoff_phase', 'N/A')}

VÙNG GIÁ QUAN TRỌNG:
- Hỗ trợ: {indicators.get('support', 0)}
- Kháng cự: {indicators.get('resistance', 0)}

MỨC GIAO DỊCH ĐỀ XUẤT:
- Vùng mua: {indicators.get('entry_low', 0)} - {indicators.get('entry_high', 0)}
- Stop Loss: {indicators.get('stop_loss', 0)}
- TP1 (+5%): {indicators.get('tp1', 0)}
- TP2 (+10%): {indicators.get('tp2', 0)}
- TP3 (+15%): {indicators.get('tp3', 0)}
- Khuyến nghị kỹ thuật: {indicators.get('recommendation', 'THEO DÕI')}

PHÂN TÍCH CƠ BẢN (FUNDAMENTAL):
- Có dữ liệu: {'Có' if indicators.get('fundamental_has_data', False) else 'Không'}
- Nguồn: {indicators.get('fundamental_source', 'N/A')}
- EPS: {indicators.get('fundamental_eps', 'N/A')}
- P/E: {indicators.get('fundamental_pe', 'N/A')}
- P/B: {indicators.get('fundamental_pb', 'N/A')}
- ROE: {indicators.get('fundamental_roe', 'N/A')}
- Doanh thu (tỷ VND): {indicators.get('fundamental_revenue', 'N/A')}
- Lợi nhuận ròng (tỷ VND): {indicators.get('fundamental_net_income', 'N/A')}
- Tăng trưởng doanh thu: {f"{indicators.get('fundamental_revenue_growth', 0):.1f}%" if indicators.get('fundamental_revenue_growth') else 'N/A'}
- Tăng trưởng lợi nhuận: {f"{indicators.get('fundamental_profit_growth', 0):.1f}%" if indicators.get('fundamental_profit_growth') else 'N/A'}

---

YÊU CẦU: Viết báo cáo phân tích kỹ thuật chuyên sâu bằng tiếng Việt theo đúng format sau:

Báo cáo Phân tích Kỹ thuật,
[Thời gian hiện tại]

{ticker}: [KHUYẾN NGHỊ - dựa trên dữ liệu]
---------------------------
Vùng Mua (Entry): [Giá entry đề xuất]
Take Profit:
TP1: [Giá]
TP2: [Giá]
TP3: [Giá]
Stop Loss: [Giá]
---------------------------

1. XU HƯỚNG & CẤU TRÚC GIÁ
[Phân tích xu hướng dựa trên MA, cấu trúc đỉnh/đáy, pha Wyckoff. Giải thích "Golden Alignment" nếu có.]

2. PHÂN TÍCH HÀNH ĐỘNG GIÁ (PRICE ACTION)
[Mô tả hành động giá hiện tại, phản ứng tại các vùng hỗ trợ/kháng cự, các pattern nến quan trọng.]

3. CHỈ BÁO KỸ THUẬT
[Phân tích RSI (vùng quá mua/quá bán), MACD Histogram (momentum), Volume (xác nhận dòng tiền).]

4. PHÂN TÍCH CƠ BẢN (FUNDAMENTAL)
[Nếu có dữ liệu fundamental: Đánh giá P/E so với ngành, tăng trưởng doanh thu/lợi nhuận, ROE. Nếu không có dữ liệu: ghi "Chưa có dữ liệu fundamental."]

5. VÙNG GIÁ QUAN TRỌNG
[Liệt kê và giải thích các mức hỗ trợ/kháng cự quan trọng, dynamic support từ MA.]

6. CHIẾN LƯỢC GIAO DỊCH
[Đề xuất cụ thể: kịch bản Bullish/Bearish, vùng Entry tối ưu, Stop Loss, Take Profit. LƯU Ý: CHỈ PHÂN TÍCH CHO LONG (MUA), KHÔNG CÓ SHORT vì thị trường VN chưa cho phép bán khống.]

7. RỦI RO
[Các rủi ro kỹ thuật và cơ bản cần lưu ý: phân kỳ, volume thấp, P/E quá cao, tăng trưởng âm, invalidation conditions.]

KẾT LUẬN: [Tóm tắt ngắn gọn kết hợp cả kỹ thuật và cơ bản (nếu có). Đánh giá tổng quan.]

---
QUAN TRỌNG:
- Sử dụng các thuật ngữ chuyên môn như: Golden Alignment, Wyckoff Phase, Dynamic Support, Bullish/Bearish Divergence
- Đưa ra con số cụ thể từ dữ liệu được cung cấp
- CHỈ phân tích cho chiến lược LONG (MUA), KHÔNG đề cập đến SHORT vì thị trường Việt Nam chưa cho phép bán khống
- Kết hợp phân tích kỹ thuật và cơ bản nếu có dữ liệu
- Giải thích rõ ràng, dễ hiểu cho nhà đầu tư
"""
        return prompt
    
    def _build_comparison_prompt(self, stocks_data: list, custom_prompt: str = None) -> str:
        """
        Xây dựng prompt để so sánh và xếp hạng nhiều mã cổ phiếu
        
        Args:
            stocks_data: List[Dict] - Mỗi dict chứa ticker và indicators
            custom_prompt: Prompt tùy chỉnh từ người dùng
        """
        # Build stocks summary
        stocks_summary = ""
        for i, stock in enumerate(stocks_data, 1):
            ticker = stock.get('ticker', 'N/A')
            ind = stock.get('indicators', {})
            
            # Safe formatting helper
            def fmt(val, fmt_str='.1f'):
                if val is None or val == 'N/A':
                    return 'N/A'
                try:
                    return f"{float(val):{fmt_str}}"
                except:
                    return str(val)
            
            stocks_summary += f"""
### {i}. {ticker}
**Kỹ thuật:**
- Giá: {fmt(ind.get('current_price'), ',.1f')} VNĐ
- RSI(14): {fmt(ind.get('rsi'))}
- MACD Signal: {fmt(ind.get('macd_signal'), '.2f')}
- Xu hướng: {ind.get('trend', 'N/A')}
- Volume Ratio: {fmt(ind.get('volume_ratio'), '.2f')}x
- Hỗ trợ/Kháng cự: {fmt(ind.get('support'), ',.1f')} / {fmt(ind.get('resistance'), ',.1f')}
- Khuyến nghị Quick: {ind.get('recommendation', 'N/A')}

**Cơ bản:**
- EPS: {fmt(ind.get('fundamental_eps'), ',.0f')}
- P/E: {fmt(ind.get('fundamental_pe'))}
- P/B: {fmt(ind.get('fundamental_pb'))}
- ROE: {fmt(ind.get('fundamental_roe'))}%
- Tăng trưởng DT: {fmt(ind.get('fundamental_revenue_growth'))}%
"""
        
        # Default prompt or custom
        if custom_prompt:
            base_prompt = custom_prompt
        else:
            base_prompt = """Bạn là chuyên gia phân tích chứng khoán Việt Nam với 20 năm kinh nghiệm.

Nhiệm vụ: Đánh giá và XẾP HẠNG các mã cổ phiếu theo thứ tự ưu tiên đầu tư.

Tiêu chí đánh giá:
1. **Kỹ thuật (50%)**: RSI, Trend, Volume, Support/Resistance
2. **Cơ bản (30%)**: P/E, ROE, Tăng trưởng
3. **Risk/Reward (20%)**: Tiềm năng lợi nhuận vs rủi ro

Yêu cầu output:
1. Bảng xếp hạng với điểm số 0-100
2. Lý do cụ thể cho mỗi mã
3. Khuyến nghị phân bổ vốn (%)
4. Cảnh báo rủi ro chính

CHỈ phân tích LONG (MUA), KHÔNG đề cập SHORT."""
        
        prompt = f"""{base_prompt}

---

## DỮ LIỆU CÁC MÃ CỔ PHIẾU:
{stocks_summary}

---

## YÊU CẦU BÁO CÁO:

### 📊 BẢNG XẾP HẠNG ĐẦU TƯ

| Hạng | Mã | Điểm | Khuyến nghị | Phân bổ |
|------|-----|------|-------------|---------|
| 1 | XXX | 85/100 | MUA MẠNH | 40% |
| ... | ... | ... | ... | ... |

### 🔍 PHÂN TÍCH CHI TIẾT

(Phân tích từng mã theo thứ tự xếp hạng)

### ⚠️ RỦI RO CHÍNH

(Liệt kê rủi ro cần lưu ý)

### 💡 CHIẾN LƯỢC TỔNG QUAN

(Khuyến nghị chiến lược đầu tư tổng thể)
"""
        return prompt
    
    def compare_and_rank_stocks(self, stocks_data: list, custom_prompt: str = None) -> str:
        """
        So sánh và xếp hạng nhiều mã cổ phiếu
        
        Args:
            stocks_data: List[Dict] với mỗi dict = {ticker, indicators}
            custom_prompt: Prompt tùy chỉnh (optional)
        
        Returns:
            Báo cáo xếp hạng bằng tiếng Việt
        """
        if not stocks_data:
            return "❌ Không có dữ liệu để phân tích."
        
        prompt = self._build_comparison_prompt(stocks_data, custom_prompt)
        
        if self.provider == 'gemini':
            return self._call_gemini(prompt)
        elif self.provider == 'openai':
            return self._call_openai(prompt)
        elif self.provider == 'anthropic':
            return self._call_anthropic(prompt)
    
    # ===== Report Generation =====
    
    def generate_report(self, ticker: str, indicators: Dict) -> str:
        """
        Sinh báo cáo phân tích kỹ thuật
        
        Args:
            ticker: Mã cổ phiếu (VD: DGW)
            indicators: Dict từ TechnicalAnalyzer.get_analysis_summary()
        
        Returns:
            Báo cáo đầy đủ bằng tiếng Việt
        """
        prompt = self._build_prompt(ticker, indicators)
        
        if self.provider == 'gemini':
            return self._call_gemini(prompt)
        elif self.provider == 'openai':
            return self._call_openai(prompt)
        elif self.provider == 'anthropic':
            return self._call_anthropic(prompt)
    
    def _call_gemini(self, prompt: str, max_retries: int = 3) -> str:
        """Gọi Gemini API với retry logic cho rate limit"""
        import time
        
        for attempt in range(max_retries):
            try:
                response = self.client.generate_content(prompt)
                return response.text
            except Exception as e:
                error_msg = str(e)
                
                # Check if rate limit error (429)
                if "429" in error_msg or "quota" in error_msg.lower():
                    wait_time = 30 * (attempt + 1)  # 30s, 60s, 90s
                    if attempt < max_retries - 1:
                        print(f"[RATE LIMIT] Đợi {wait_time}s trước khi thử lại...")
                        time.sleep(wait_time)
                        continue
                    else:
                        return f"Lỗi Gemini API: Vượt quota. Vui lòng đợi 1 phút và thử lại."
                else:
                    return f"Lỗi Gemini API: {error_msg}"
        
        return "Lỗi Gemini API: Không thể kết nối sau nhiều lần thử"
    
    def _call_openai(self, prompt: str) -> str:
        """Gọi OpenAI API"""
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "Bạn là chuyên gia phân tích kỹ thuật chứng khoán Việt Nam."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4000,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Lỗi OpenAI API: {str(e)}"
    
    def _call_anthropic(self, prompt: str) -> str:
        """Gọi Anthropic API"""
        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=4000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content[0].text
        except Exception as e:
            return f"Lỗi Anthropic API: {str(e)}"
    
    # ===== Report Storage =====
    
    def save_report_to_sheets(self, ticker: str, report: str, indicators: Dict) -> bool:
        """
        Lưu báo cáo vào Google Sheets
        
        Args:
            ticker: Mã cổ phiếu
            report: Nội dung báo cáo
            indicators: Dữ liệu indicators để lưu tóm tắt
        
        Returns:
            True nếu thành công
        """
        try:
            import gspread
            from config import get_google_credentials
            
            creds = get_google_credentials()
            client = gspread.authorize(creds)
            
            spreadsheet_id = os.getenv("SPREADSHEET_ID")
            if spreadsheet_id:
                spreadsheet = client.open_by_key(spreadsheet_id)
            else:
                spreadsheet = client.open("stockdata")
            
            # Get or create ai_reports sheet
            try:
                ws = spreadsheet.worksheet("ai_reports")
            except gspread.WorksheetNotFound:
                ws = spreadsheet.add_worksheet(title="ai_reports", rows="1000", cols="15")
                # Add headers
                headers = ['ticker', 'timestamp', 'recommendation', 'entry_zone', 
                          'tp1', 'tp2', 'tp3', 'stop_loss', 'rsi', 'trend', 
                          'ma_alignment', 'ai_provider', 'report']
                ws.append_row(headers)
            
            # Prepare data row
            row = [
                ticker,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                indicators.get('recommendation', 'N/A'),
                f"{indicators.get('entry_low', 0)} - {indicators.get('entry_high', 0)}",
                indicators.get('tp1', 0),
                indicators.get('tp2', 0),
                indicators.get('tp3', 0),
                indicators.get('stop_loss', 0),
                indicators.get('rsi', 0),
                indicators.get('trend', 'N/A'),
                indicators.get('ma_alignment', 'N/A'),
                self.provider,
                report[:50000]  # Limit report length for GSheets cell limit
            ]
            
            ws.append_row(row)
            return True
            
        except Exception as e:
            print(f"[ERROR] Không thể lưu báo cáo vào Sheets: {e}")
            return False
    
    def get_saved_reports(self, ticker: str = None, limit: int = 10) -> list:
        """
        Lấy các báo cáo đã lưu
        
        Args:
            ticker: Lọc theo mã (optional)
            limit: Số báo cáo tối đa
        
        Returns:
            List các báo cáo
        """
        try:
            import gspread
            import pandas as pd
            from config import get_google_credentials
            
            creds = get_google_credentials()
            client = gspread.authorize(creds)
            
            spreadsheet_id = os.getenv("SPREADSHEET_ID")
            if spreadsheet_id:
                spreadsheet = client.open_by_key(spreadsheet_id)
            else:
                spreadsheet = client.open("stockdata")
            
            try:
                ws = spreadsheet.worksheet("ai_reports")
                data = ws.get_all_records()
                df = pd.DataFrame(data)
                
                if df.empty:
                    return []
                
                if ticker:
                    df = df[df['ticker'] == ticker]
                
                # Sort by timestamp descending
                df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
                df = df.sort_values('timestamp', ascending=False)
                
                return df.head(limit).to_dict('records')
                
            except gspread.WorksheetNotFound:
                return []
                
        except Exception as e:
            print(f"[ERROR] Không thể đọc báo cáo từ Sheets: {e}")
            return []


# ===== Quick helper =====

def analyze_with_ai(ticker: str, df, days: int = 400, provider: str = 'gemini', save: bool = True) -> str:
    """
    Helper function để phân tích nhanh
    
    Args:
        ticker: Mã cổ phiếu
        df: DataFrame OHLCV
        days: Số ngày dữ liệu
        provider: AI provider
        save: Có lưu vào GSheets không
    
    Returns:
        Báo cáo phân tích
    """
    from technical_analysis import TechnicalAnalyzer
    
    # Calculate indicators
    analyzer = TechnicalAnalyzer(df, days=days)
    indicators = analyzer.get_analysis_summary()
    
    # Generate AI report
    ai = AIAnalyzer(provider=provider)
    report = ai.generate_report(ticker, indicators)
    
    # Save to sheets
    if save:
        ai.save_report_to_sheets(ticker, report, indicators)
    
    return report


if __name__ == '__main__':
    print("AI Analyzer Module loaded successfully!")
    print(f"Available providers: {AIAnalyzer.PROVIDERS}")
    print("Usage: AIAnalyzer(provider='gemini').generate_report(ticker, indicators)")
