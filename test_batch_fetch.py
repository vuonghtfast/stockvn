# Test script to find efficient way to get top liquidity
from vnstock import Vnstock
import pandas as pd
import time

vs = Vnstock()

def get_all_symbols():
    print("Fetching all symbols...")
    start = time.time()
    # Fetch from all 3 exchanges
    hose = vs.stock(symbol='VNM', source='TCBS').listing.all_symbols(exchange='HOSE')
    hnx = vs.stock(symbol='VNM', source='TCBS').listing.all_symbols(exchange='HNX')
    upcom = vs.stock(symbol='VNM', source='TCBS').listing.all_symbols(exchange='UPCOM')
    
    combined = pd.concat([hose, hnx, upcom])
    print(f"Got {len(combined)} symbols in {time.time() - start:.2f}s")
    return combined['ticker'].tolist()

def batch_get_latest(symbols, batch_size=50):
    print("Fetching latest price/volume...")
    start = time.time()
    
    all_data = []
    # Test with first 100 for speed
    test_symbols = symbols[:100] 
    
    # Try using quote.now() (SSI source usually supports batch)
    try:
        # Note: vnstock 3.x quote.now might need specific handling
        # Let's try fetching in batches
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i+batch_size]
            try:
                # Use VCI source which we use elsewhere
                # Or SSI if VCI doesn't support batch well logic
                batch_str = ",".join(batch)
                
                # Method A: quote.now()?
                # In vnstock 3, it might differ. Let's try standard price_board if available or just check source.
                # Actually, let's try the safest known method: stock().quote.now() loop or batch.
                
                # Check 1 batch
                df = vs.stock(symbol=batch[0], source='VCI').quote.now() 
                # Wait, this usually returns just one?
                # Docs say stock(symbol='A,B,C') working?
                pass
            except:
                pass
            
    except Exception as e:
        print(f"Error: {e}")

    # Alternative: Use price_board from SSI or similar?
    # Actually, stock_screener.py loops 1 by 1 for history. Here we just need current volume.
    
    # Efficient approach: Use TCBS price board feature if exposed, or loop VCI `quote.now()`
    # Let's try fetching a batch of 20 using comma separation
    
    subset = symbols[:20]
    subset_str = ",".join(subset)
    print(f"Testing batch fetch for: {subset_str}")
    
    try:
        # Try VCI
        df = vs.stock(symbol=subset_str, source='VCI').quote.now()
        print(f"VCI Batch Result: {len(df)} rows")
        print(df[['ticker', 'volume', 'accumulatedVolume'] if 'accumulatedVolume' in df.columns else df.columns])
    except Exception as e:
        print(f"VCI Batch Failed: {e}")

    try:
        # Try SSI (often good for realtime)
        df_ssi = vs.stock(symbol=subset_str, source='SSI').quote.now()
        print(f"SSI Batch Result: {len(df_ssi)} rows")
    except Exception as e:
        print(f"SSI Batch Failed: {e}")

if __name__ == "__main__":
    symbols = get_all_symbols()
    batch_get_latest(symbols)
