# -*- coding: utf-8 -*-
"""
Backtest Breakout Strategy
Test breakout signals on historical data to measure success rate
"""

import pandas as pd
from vnstock import Vnstock
from datetime import datetime, timedelta
import sys

def backtest_breakout_strategy(symbol, start_date, end_date, lookback=20, take_profit=0.10, stop_loss=0.05, max_hold_days=20):
    """
    Backtest breakout strategy on a single ticker
    
    Strategy:
    - Entry: Price breaks above 20-day high + volume spike (2x average)
    - Exit: Take profit (+10%), Stop loss (-5%), or Max hold (20 days)
    
    Returns:
        dict: Performance metrics
    """
    try:
        vs = Vnstock()
        
        print(f"Fetching data for {symbol} from {start_date} to {end_date}...")
        
        df = vs.stock(symbol=symbol, source='TCBS').quote.history(
            start=start_date,
            end=end_date,
            interval='1D'
        )
        
        if df is None or df.empty:
            print(f"[X] No data returned for {symbol}")
            return {
                'ticker': symbol,
                'error': 'No data available',
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'avg_gain': 0,
                'avg_loss': 0,
                'total_return': 0,
                'max_drawdown': 0,
                'best_trade': 0,
                'worst_trade': 0,
                'avg_hold_days': 0
            }
        
        print(f"[OK] Got {len(df)} days of data")
        
        if len(df) < lookback + 10:
            print(f"[!] Not enough data: {len(df)} days (need at least {lookback + 10})")
            return {
                'ticker': symbol,
                'error': f'Insufficient data: {len(df)} days',
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'avg_gain': 0,
                'avg_loss': 0,
                'total_return': 0,
                'max_drawdown': 0,
                'best_trade': 0,
                'worst_trade': 0,
                'avg_hold_days': 0
            }
        
        # Calculate indicators
        df['high_20d'] = df['high'].rolling(window=lookback).max()
        df['avg_volume'] = df['volume'].rolling(window=lookback).mean()
        df['volume_spike'] = df['volume'] / df['avg_volume']
        
        # Detect breakout signals
        df['breakout'] = (
            (df['close'] > df['high_20d'].shift(1)) &  # Price breaks above previous 20-day high
            (df['volume_spike'] > 2.0)  # Volume spike
        )
        
        # Simulate trades
        trades = []
        in_position = False
        entry_price = 0
        entry_date = None
        hold_days = 0
        
        for i in range(lookback, len(df)):
            current_date = df.index[i]
            current_price = df.iloc[i]['close']
            current_open = df.iloc[i]['open']
            
            if in_position:
                hold_days += 1
                
                # Calculate P&L
                pnl_pct = (current_price - entry_price) / entry_price
                
                # Exit conditions
                exit_reason = None
                if pnl_pct >= take_profit:
                    exit_reason = "Take Profit"
                elif pnl_pct <= -stop_loss:
                    exit_reason = "Stop Loss"
                elif hold_days >= max_hold_days:
                    exit_reason = "Max Hold"
                
                if exit_reason:
                    trades.append({
                        'entry_date': entry_date,
                        'exit_date': current_date,
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'pnl_pct': pnl_pct * 100,
                        'hold_days': hold_days,
                        'exit_reason': exit_reason
                    })
                    in_position = False
                    hold_days = 0
            
            else:
                # Check for breakout signal
                if df.iloc[i]['breakout']:
                    # Enter next day at open
                    if i + 1 < len(df):
                        entry_price = df.iloc[i + 1]['open']
                        entry_date = df.index[i + 1]
                        in_position = True
                        hold_days = 0
        
        # Calculate performance metrics
        if not trades:
            return {
                'ticker': symbol,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'avg_gain': 0,
                'avg_loss': 0,
                'total_return': 0,
                'max_drawdown': 0,
                'best_trade': 0,
                'worst_trade': 0,
                'avg_hold_days': 0
            }
        
        trades_df = pd.DataFrame(trades)
        winning_trades = trades_df[trades_df['pnl_pct'] > 0]
        losing_trades = trades_df[trades_df['pnl_pct'] <= 0]
        
        metrics = {
            'ticker': symbol,
            'total_trades': len(trades_df),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': (len(winning_trades) / len(trades_df)) * 100 if len(trades_df) > 0 else 0,
            'avg_gain': winning_trades['pnl_pct'].mean() if len(winning_trades) > 0 else 0,
            'avg_loss': losing_trades['pnl_pct'].mean() if len(losing_trades) > 0 else 0,
            'total_return': trades_df['pnl_pct'].sum(),
            'max_drawdown': trades_df['pnl_pct'].min(),
            'best_trade': trades_df['pnl_pct'].max(),
            'worst_trade': trades_df['pnl_pct'].min(),
            'avg_hold_days': trades_df['hold_days'].mean()
        }
        
        return metrics
    
    except Exception as e:
        print(f"[X] Lỗi backtest {symbol}: {e}")
        return None

def backtest_with_dataframe(df, symbol, lookback=20, take_profit=0.10, stop_loss=0.05, max_hold_days=20):
    """
    Backtest using pre-loaded DataFrame (from Google Sheets)
    
    Args:
        df: DataFrame with columns: open, high, low, close, volume
        symbol: Ticker symbol
        lookback: Lookback period for breakout detection
        take_profit: Take profit percentage
        stop_loss: Stop loss percentage
        max_hold_days: Maximum holding period
    
    Returns:
        dict: Performance metrics
    """
    try:
        if df.empty or len(df) < lookback + 10:
            return {
                'ticker': symbol,
                'error': f'Insufficient data: {len(df)} days',
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'avg_gain': 0,
                'avg_loss': 0,
                'total_return': 0,
                'max_drawdown': 0,
                'best_trade': 0,
                'worst_trade': 0,
                'avg_hold_days': 0
            }
        
        # Ensure numeric columns
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Calculate indicators
        df['high_20d'] = df['high'].rolling(window=lookback).max()
        df['avg_volume'] = df['volume'].rolling(window=lookback).mean()
        df['volume_spike'] = df['volume'] / df['avg_volume']
        
        # Detect breakout signals
        df['breakout'] = (
            (df['close'] > df['high_20d'].shift(1)) &
            (df['volume_spike'] > 2.0)
        )
        
        # Simulate trades
        trades = []
        in_position = False
        entry_price = 0
        entry_date = None
        hold_days = 0
        
        for i in range(lookback, len(df)):
            current_date = df.index[i]
            current_price = df.iloc[i]['close']
            
            if in_position:
                hold_days += 1
                pnl_pct = (current_price - entry_price) / entry_price
                
                exit_reason = None
                if pnl_pct >= take_profit:
                    exit_reason = "Take Profit"
                elif pnl_pct <= -stop_loss:
                    exit_reason = "Stop Loss"
                elif hold_days >= max_hold_days:
                    exit_reason = "Max Hold"
                
                if exit_reason:
                    trades.append({
                        'entry_date': entry_date,
                        'exit_date': current_date,
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'pnl_pct': pnl_pct * 100,
                        'hold_days': hold_days,
                        'exit_reason': exit_reason
                    })
                    in_position = False
                    hold_days = 0
            else:
                if df.iloc[i]['breakout']:
                    if i + 1 < len(df):
                        entry_price = df.iloc[i + 1]['open']
                        entry_date = df.index[i + 1]
                        in_position = True
                        hold_days = 0
        
        # Calculate metrics
        if not trades:
            return {
                'ticker': symbol,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'avg_gain': 0,
                'avg_loss': 0,
                'total_return': 0,
                'max_drawdown': 0,
                'best_trade': 0,
                'worst_trade': 0,
                'avg_hold_days': 0
            }
        
        trades_df = pd.DataFrame(trades)
        winning_trades = trades_df[trades_df['pnl_pct'] > 0]
        losing_trades = trades_df[trades_df['pnl_pct'] <= 0]
        
        return {
            'ticker': symbol,
            'total_trades': len(trades_df),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': (len(winning_trades) / len(trades_df)) * 100 if len(trades_df) > 0 else 0,
            'avg_gain': winning_trades['pnl_pct'].mean() if len(winning_trades) > 0 else 0,
            'avg_loss': losing_trades['pnl_pct'].mean() if len(losing_trades) > 0 else 0,
            'total_return': trades_df['pnl_pct'].sum(),
            'max_drawdown': trades_df['pnl_pct'].min(),
            'best_trade': trades_df['pnl_pct'].max(),
            'worst_trade': trades_df['pnl_pct'].min(),
            'avg_hold_days': trades_df['hold_days'].mean()
        }
    
    except Exception as e:
        print(f"[X] Lỗi backtest {symbol}: {e}")
        import traceback
        traceback.print_exc()
        return {
            'ticker': symbol,
            'error': str(e),
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'avg_gain': 0,
            'avg_loss': 0,
            'total_return': 0,
            'max_drawdown': 0,
            'best_trade': 0,
            'worst_trade': 0,
            'avg_hold_days': 0
        }

def backtest_multiple_tickers(tickers, period_years=2):
    """Backtest multiple tickers and return aggregated results"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=period_years * 365)
    
    results = []
    
    print(f"\n[LAB] Bắt đầu backtest {len(tickers)} mã...")
    print(f"[CALENDAR] Khoảng thời gian: {start_date.strftime('%Y-%m-%d')} đến {end_date.strftime('%Y-%m-%d')}\n")
    
    for idx, ticker in enumerate(tickers, 1):
        print(f"Progress: {idx}/{len(tickers)} - Testing {ticker}...")
        
        metrics = backtest_breakout_strategy(
            ticker,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        if metrics and metrics['total_trades'] > 0:
            results.append(metrics)
            print(f"[OK] {ticker}: {metrics['total_trades']} trades, Win rate: {metrics['win_rate']:.1f}%")
    
    return pd.DataFrame(results)

def print_backtest_summary(results_df):
    """Print summary of backtest results"""
    if results_df.empty:
        print("\n[X] Không có kết quả backtest nào.")
        return
    
    print("\n" + "="*80)
    print("[CHART] KẾT QUẢ BACKTEST CHIẾN LƯỢC BREAKOUT")
    print("="*80)
    
    print(f"\n[TARGET] Tổng số mã test: {len(results_df)}")
    print(f"[UP] Tổng số giao dịch: {results_df['total_trades'].sum()}")
    
    # Overall statistics
    total_trades = results_df['total_trades'].sum()
    total_wins = results_df['winning_trades'].sum()
    overall_win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
    
    print(f"\n[MONEY] HIỆU SUẤT TỔNG THỂ:")
    print(f"  - Win Rate: {overall_win_rate:.2f}%")
    print(f"  - Avg Gain (winning trades): {results_df['avg_gain'].mean():.2f}%")
    print(f"  - Avg Loss (losing trades): {results_df['avg_loss'].mean():.2f}%")
    print(f"  - Avg Hold Days: {results_df['avg_hold_days'].mean():.1f} days")
    
    # Top performers
    print(f"\n⭐ TOP 10 MÃ HIỆU SUẤT CAO NHẤT (Win Rate):")
    top_performers = results_df.nlargest(10, 'win_rate')[['ticker', 'total_trades', 'win_rate', 'total_return']]
    print(top_performers.to_string(index=False))
    
    # Best total returns
    print(f"\n💎 TOP 10 LỢI NHUẬN CAO NHẤT:")
    top_returns = results_df.nlargest(10, 'total_return')[['ticker', 'total_trades', 'win_rate', 'total_return']]
    print(top_returns.to_string(index=False))
    
    print("\n" + "="*80)

if __name__ == "__main__":
    # Example: Backtest VN30
    vn30_tickers = [
        'VNM', 'VIC', 'VHM', 'VCB', 'GAS', 'MSN', 'BID', 'CTG', 'HPG', 'TCB',
        'MBB', 'VPB', 'VRE', 'SAB', 'PLX', 'VJC', 'MWG', 'FPT', 'POW', 'SSI',
        'HDB', 'TPB', 'ACB', 'STB', 'GVR', 'PDR', 'KDH', 'NVL', 'BCM', 'VHC'
    ]
    
    # Run backtest
    results = backtest_multiple_tickers(vn30_tickers, period_years=2)
    
    # Print summary
    print_backtest_summary(results)
    
    # Save to CSV
    if not results.empty:
        filename = f"backtest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        results.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n[OK] Đã lưu kết quả vào file: {filename}")
