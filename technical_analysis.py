# -*- coding: utf-8 -*-
"""
Technical Analysis Module
Tính toán đầy đủ các chỉ báo kỹ thuật cho phân tích AI
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional


class TechnicalAnalyzer:
    """
    Tính toán tất cả chỉ báo kỹ thuật cho một cổ phiếu.
    
    Sử dụng:
        analyzer = TechnicalAnalyzer(df, days=400)
        indicators = analyzer.get_analysis_summary()
        
    Tuỳ chỉnh tham số:
        analyzer = TechnicalAnalyzer(df, days=400, tp1_pct=5, tp2_pct=10, tp3_pct=15, sl_pct=6)
    """
    
    # Default trading parameters (có thể override qua __init__ hoặc env)
    DEFAULT_TP1_PCT = 5   # Take Profit 1: +5%
    DEFAULT_TP2_PCT = 10  # Take Profit 2: +10%
    DEFAULT_TP3_PCT = 15  # Take Profit 3: +15%
    DEFAULT_SL_PCT = 6    # Stop Loss: -6%
    DEFAULT_SL_BUFFER_PCT = 3  # Buffer dưới MA50/Support: 3%
    
    def __init__(self, df: pd.DataFrame, days: int = 400,
                 tp1_pct: float = None, tp2_pct: float = None, tp3_pct: float = None,
                 sl_pct: float = None, sl_buffer_pct: float = None):
        """
        Args:
            df: DataFrame với cột: open, high, low, close, volume
            days: Số ngày dữ liệu để phân tích (mặc định 400)
            tp1_pct: Take Profit 1 % (mặc định 5%)
            tp2_pct: Take Profit 2 % (mặc định 10%)
            tp3_pct: Take Profit 3 % (mặc định 15%)
            sl_pct: Stop Loss % default (mặc định 6%)
            sl_buffer_pct: Buffer % dưới MA50/Support (mặc định 3%)
        """
        self.original_df = df.copy()
        self.days = days
        
        # Trading parameters - có thể override
        import os
        self.tp1_pct = tp1_pct if tp1_pct is not None else float(os.getenv('TP1_PCT', self.DEFAULT_TP1_PCT))
        self.tp2_pct = tp2_pct if tp2_pct is not None else float(os.getenv('TP2_PCT', self.DEFAULT_TP2_PCT))
        self.tp3_pct = tp3_pct if tp3_pct is not None else float(os.getenv('TP3_PCT', self.DEFAULT_TP3_PCT))
        self.sl_pct = sl_pct if sl_pct is not None else float(os.getenv('SL_PCT', self.DEFAULT_SL_PCT))
        self.sl_buffer_pct = sl_buffer_pct if sl_buffer_pct is not None else float(os.getenv('SL_BUFFER_PCT', self.DEFAULT_SL_BUFFER_PCT))
        
        # Lọc dữ liệu theo số ngày
        if len(df) > days:
            self.df = df.tail(days).copy()
        else:
            self.df = df.copy()
        
        # Đảm bảo các cột là numeric
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in self.df.columns:
                self.df[col] = pd.to_numeric(self.df[col], errors='coerce')
        
        # Drop NA
        self.df = self.df.dropna(subset=['close'])
        
        # Tính toán các chỉ báo cơ bản
        self._calculate_all_indicators()
    
    def _calculate_all_indicators(self):
        """Tính toán tất cả chỉ báo một lần"""
        if len(self.df) < 20:
            return
        
        # Moving Averages
        self.df['MA20'] = self.df['close'].rolling(window=20).mean()
        self.df['MA50'] = self.df['close'].rolling(window=50).mean()
        self.df['MA200'] = self.df['close'].rolling(window=200).mean()
        
        # RSI
        delta = self.df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        self.df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = self.df['close'].ewm(span=12, adjust=False).mean()
        exp2 = self.df['close'].ewm(span=26, adjust=False).mean()
        self.df['MACD'] = exp1 - exp2
        self.df['MACD_Signal'] = self.df['MACD'].ewm(span=9, adjust=False).mean()
        self.df['MACD_Histogram'] = self.df['MACD'] - self.df['MACD_Signal']
        
        # Volume
        self.df['Volume_MA20'] = self.df['volume'].rolling(window=20).mean()
        self.df['Volume_Ratio'] = self.df['volume'] / self.df['Volume_MA20']
    
    # ===== Moving Averages =====
    
    def get_current_price(self) -> float:
        """Lấy giá hiện tại"""
        return float(self.df['close'].iloc[-1]) if not self.df.empty else 0
    
    def get_ma(self, period: int) -> float:
        """Lấy giá trị MA"""
        col = f'MA{period}'
        if col in self.df.columns and not self.df[col].isna().all():
            return float(self.df[col].iloc[-1])
        return 0
    
    def get_ma_alignment(self) -> Dict:
        """
        Kiểm tra sắp xếp MA (Golden Alignment)
        Returns: {
            'alignment': 'golden' / 'death' / 'mixed',
            'price_above_ma20': bool,
            'ma20_above_ma50': bool,
            'ma50_above_ma200': bool
        }
        """
        price = self.get_current_price()
        ma20 = self.get_ma(20)
        ma50 = self.get_ma(50)
        ma200 = self.get_ma(200)
        
        price_above_ma20 = price > ma20 if ma20 > 0 else None
        ma20_above_ma50 = ma20 > ma50 if ma50 > 0 else None
        ma50_above_ma200 = ma50 > ma200 if ma200 > 0 else None
        
        # Determine alignment
        if price_above_ma20 and ma20_above_ma50 and ma50_above_ma200:
            alignment = 'golden'
        elif not price_above_ma20 and not ma20_above_ma50 and not ma50_above_ma200:
            alignment = 'death'
        else:
            alignment = 'mixed'
        
        return {
            'alignment': alignment,
            'price_above_ma20': price_above_ma20,
            'ma20_above_ma50': ma20_above_ma50,
            'ma50_above_ma200': ma50_above_ma200
        }
    
    def get_ma_slope(self, period: int, lookback_days: int = 60) -> float:
        """
        Tính độ dốc của MA trong N ngày gần đây
        Returns: % thay đổi của MA
        """
        col = f'MA{period}'
        if col not in self.df.columns:
            return 0
        
        ma_series = self.df[col].dropna()
        if len(ma_series) < lookback_days:
            return 0
        
        start_val = ma_series.iloc[-lookback_days]
        end_val = ma_series.iloc[-1]
        
        if start_val > 0:
            return ((end_val - start_val) / start_val) * 100
        return 0
    
    # ===== Momentum Indicators =====
    
    def get_rsi(self) -> float:
        """Lấy RSI hiện tại"""
        if 'RSI' in self.df.columns and not self.df['RSI'].isna().all():
            return float(self.df['RSI'].iloc[-1])
        return 50
    
    def get_macd(self) -> Dict:
        """Lấy MACD data"""
        return {
            'macd': float(self.df['MACD'].iloc[-1]) if 'MACD' in self.df.columns else 0,
            'signal': float(self.df['MACD_Signal'].iloc[-1]) if 'MACD_Signal' in self.df.columns else 0,
            'histogram': float(self.df['MACD_Histogram'].iloc[-1]) if 'MACD_Histogram' in self.df.columns else 0
        }
    
    # ===== Volume Analysis =====
    
    def get_volume_ratio(self) -> float:
        """Lấy Volume Ratio so với trung bình 20 ngày"""
        if 'Volume_Ratio' in self.df.columns and not self.df['Volume_Ratio'].isna().all():
            return float(self.df['Volume_Ratio'].iloc[-1])
        return 1.0
    
    def detect_volume_spike(self, threshold: float = 1.5) -> bool:
        """Kiểm tra có Volume spike không"""
        return self.get_volume_ratio() > threshold
    
    # ===== Trend Detection =====
    
    def detect_trend(self) -> str:
        """
        Xác định xu hướng: uptrend, downtrend, sideways
        Dựa trên MA và cấu trúc giá
        """
        if len(self.df) < 50:
            return 'insufficient_data'
        
        price = self.get_current_price()
        ma20 = self.get_ma(20)
        ma50 = self.get_ma(50)
        ma200 = self.get_ma(200)
        
        ma20_slope = self.get_ma_slope(20, 20)
        ma50_slope = self.get_ma_slope(50, 30)
        
        # Strong Uptrend
        if price > ma20 > ma50 and ma20_slope > 0 and ma50_slope > 0:
            if ma200 > 0 and ma50 > ma200:
                return 'strong_uptrend'
            return 'uptrend'
        
        # Strong Downtrend  
        if price < ma20 < ma50 and ma20_slope < 0 and ma50_slope < 0:
            if ma200 > 0 and ma50 < ma200:
                return 'strong_downtrend'
            return 'downtrend'
        
        # Sideways
        return 'sideways'
    
    def detect_wyckoff_phase(self) -> str:
        """
        Xác định pha Wyckoff: accumulation, markup, distribution, markdown
        """
        trend = self.detect_trend()
        volume_ratio = self.get_volume_ratio()
        rsi = self.get_rsi()
        ma_alignment = self.get_ma_alignment()
        
        if trend in ['strong_uptrend', 'uptrend']:
            if volume_ratio > 1.2 and rsi > 50:
                return 'markup'
            return 'accumulation'
        elif trend in ['strong_downtrend', 'downtrend']:
            if volume_ratio > 1.2 and rsi < 50:
                return 'markdown'
            return 'distribution'
        else:
            if rsi < 40:
                return 'accumulation'
            elif rsi > 60:
                return 'distribution'
            return 'ranging'
    
    # ===== Support & Resistance =====
    
    def find_support_resistance(self) -> Dict:
        """
        Tìm vùng hỗ trợ và kháng cự
        Returns: {'support': float, 'resistance': float}
        """
        if len(self.df) < 20:
            return {'support': 0, 'resistance': 0}
        
        # Sử dụng các đáy/đỉnh local trong 60 ngày gần nhất
        recent = self.df.tail(60)
        price = self.get_current_price()
        
        # Tìm các đáy (local minima)
        lows = recent['low'].values
        supports = []
        for i in range(2, len(lows) - 2):
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                if lows[i] < price:
                    supports.append(lows[i])
        
        # Tìm các đỉnh (local maxima)  
        highs = recent['high'].values
        resistances = []
        for i in range(2, len(highs) - 2):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                if highs[i] > price:
                    resistances.append(highs[i])
        
        # Lấy support gần nhất (cao nhất dưới giá)
        support = max(supports) if supports else self.get_ma(50)
        if support == 0:
            support = price * 0.95  # Fallback -5%
        
        # Lấy resistance gần nhất (thấp nhất trên giá)
        resistance = min(resistances) if resistances else recent['high'].max()
        if resistance <= price:
            resistance = price * 1.1  # Fallback +10%
        
        return {
            'support': round(float(support), 1),
            'resistance': round(float(resistance), 1)
        }
    
    # ===== Entry/Exit Zones =====
    
    def calculate_entry_zone(self) -> Tuple[float, float]:
        """
        Tính vùng mua tối ưu
        Returns: (entry_low, entry_high)
        """
        price = self.get_current_price()
        ma20 = self.get_ma(20)
        support = self.find_support_resistance()['support']
        
        trend = self.detect_trend()
        
        if trend in ['strong_uptrend', 'uptrend']:
            # Mua gần MA20 hoặc khi breakout
            entry_low = max(ma20 * 0.98, support) if ma20 > 0 else price * 0.95
            entry_high = price
        else:
            # Mua gần support
            entry_low = support
            entry_high = ma20 if ma20 > 0 else price * 0.98
        
        return (round(entry_low, 1), round(entry_high, 1))
    
    def calculate_take_profits(self, entry: float = None) -> Dict:
        """
        Tính các mức chốt lời dựa trên tham số tp1_pct, tp2_pct, tp3_pct
        """
        if entry is None:
            entry = self.get_current_price()
        
        resistance = self.find_support_resistance()['resistance']
        
        # TP dựa trên % từ tham số
        tp1 = round(entry * (1 + self.tp1_pct / 100), 1)
        tp2 = round(entry * (1 + self.tp2_pct / 100), 1)
        tp3 = round(entry * (1 + self.tp3_pct / 100), 1)
        
        # Điều chỉnh TP1 theo resistance nếu gần
        if resistance > entry and resistance < tp1:
            tp1 = round(resistance, 1)
        
        return {
            'tp1': tp1,
            'tp2': tp2,
            'tp3': tp3
        }
    
    def calculate_stop_loss(self, entry: float = None) -> float:
        """
        Tính mức cắt lỗ = Entry × (1 - sl_pct%)
        Đơn giản và nhất quán với tham số SL_PCT
        """
        if entry is None:
            entry = self.get_current_price()
        
        # Stop loss = Entry - sl_pct%
        sl_multiplier = 1 - (self.sl_pct / 100)  # VD: 6% -> 0.94
        stop_loss = entry * sl_multiplier
        
        return round(stop_loss, 1)
    
    # ===== Recommendation =====
    
    def get_recommendation(self) -> str:
        """
        Đưa ra khuyến nghị: MUA / TÍCH LŨY, THEO DÕI, BÁN / HẠ TỶ TRỌNG
        """
        trend = self.detect_trend()
        rsi = self.get_rsi()
        ma_alignment = self.get_ma_alignment()
        volume_ratio = self.get_volume_ratio()
        macd = self.get_macd()
        
        score = 50  # Base score
        
        # Trend
        if trend == 'strong_uptrend':
            score += 20
        elif trend == 'uptrend':
            score += 10
        elif trend == 'downtrend':
            score -= 10
        elif trend == 'strong_downtrend':
            score -= 20
        
        # MA Alignment
        if ma_alignment['alignment'] == 'golden':
            score += 15
        elif ma_alignment['alignment'] == 'death':
            score -= 15
        
        # RSI
        if 40 < rsi < 70:
            score += 10  # Healthy zone
        elif rsi < 30:
            score += 5  # Oversold - potential reversal
        elif rsi > 70:
            score -= 5  # Overbought - caution
        
        # MACD
        if macd['histogram'] > 0:
            score += 5
        else:
            score -= 5
        
        # Volume
        if volume_ratio > 1.5 and trend in ['uptrend', 'strong_uptrend']:
            score += 10
        
        # Recommendation
        if score >= 70:
            return 'MUA / TÍCH LŨY'
        elif score >= 50:
            return 'THEO DÕI'
        else:
            return 'BÁN / HẠ TỶ TRỌNG'
    
    # ===== Summary =====
    
    def get_analysis_summary(self) -> Dict:
        """
        Trả về tất cả dữ liệu phân tích cho AI prompt
        """
        price = self.get_current_price()
        ma20 = self.get_ma(20)
        ma50 = self.get_ma(50)
        ma200 = self.get_ma(200)
        ma_alignment = self.get_ma_alignment()
        
        support_resistance = self.find_support_resistance()
        entry_zone = self.calculate_entry_zone()
        take_profits = self.calculate_take_profits(entry_zone[0])
        stop_loss = self.calculate_stop_loss(entry_zone[0])
        
        macd = self.get_macd()
        
        return {
            # Price data
            'current_price': price,
            'data_days': len(self.df),
            'analysis_date': datetime.now().strftime('%d-%m-%Y %H:%M:%S'),
            
            # Moving Averages
            'ma20': round(ma20, 1),
            'ma50': round(ma50, 1),
            'ma200': round(ma200, 1),
            'ma_alignment': ma_alignment['alignment'],
            'price_above_ma20': ma_alignment['price_above_ma20'],
            'ma20_above_ma50': ma_alignment['ma20_above_ma50'],
            'ma50_above_ma200': ma_alignment['ma50_above_ma200'],
            'ma200_slope_60d': round(self.get_ma_slope(200, 60), 2),
            
            # Momentum
            'rsi': round(self.get_rsi(), 1),
            'macd': round(macd['macd'], 2),
            'macd_signal': round(macd['signal'], 2),
            'macd_histogram': round(macd['histogram'], 2),
            
            # Volume
            'volume_ratio': round(self.get_volume_ratio(), 2),
            'volume_spike': self.detect_volume_spike(),
            
            # Trend
            'trend': self.detect_trend(),
            'wyckoff_phase': self.detect_wyckoff_phase(),
            
            # Levels
            'support': support_resistance['support'],
            'resistance': support_resistance['resistance'],
            
            # Trading levels
            'entry_low': entry_zone[0],
            'entry_high': entry_zone[1],
            'stop_loss': stop_loss,
            'tp1': take_profits['tp1'],
            'tp2': take_profits['tp2'],
            'tp3': take_profits['tp3'],
            
            # Recommendation
            'recommendation': self.get_recommendation()
        }


# ===== Helper function for quick analysis =====

def analyze_stock(df: pd.DataFrame, days: int = 400) -> Dict:
    """
    Quick helper to analyze a stock
    
    Args:
        df: OHLCV DataFrame
        days: Number of days to analyze
    
    Returns:
        Dict with all technical indicators
    """
    analyzer = TechnicalAnalyzer(df, days=days)
    return analyzer.get_analysis_summary()


if __name__ == '__main__':
    # Test với data mẫu
    print("Technical Analysis Module loaded successfully!")
    print("Usage: TechnicalAnalyzer(df, days=400).get_analysis_summary()")
