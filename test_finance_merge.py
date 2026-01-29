
import pandas as pd
import numpy as np

def merge_logic(old_df, new_df, sheet_name):
    """Simulate the merge logic from finance.py"""
    if not old_df.empty:
        old_df.columns = old_df.columns.str.lower().str.replace(' ', '_')
        if not new_df.empty:
            new_df.columns = new_df.columns.str.lower().str.replace(' ', '_')
            
            subset_cols = ['ticker', 'year', 'quarter'] if 'quarter' in new_df.columns else ['ticker', 'year']
            valid_keys = [c for c in subset_cols if c in old_df.columns and c in new_df.columns]
            
            if valid_keys:
                print(f"Merging on keys: {valid_keys}")
                # Create combined DF
                combined_df = pd.concat([new_df, old_df], ignore_index=True)
                
                # Convert keys to string for comparison
                for col in valid_keys:
                    combined_df[col] = combined_df[col].astype(str)
                    
                combined_df = combined_df.drop_duplicates(subset=valid_keys, keep='first')
                return combined_df
            else:
                print("No valid keys found, appending.")
                return pd.concat([old_df, new_df], ignore_index=True)
        return old_df
    return new_df

def test_merge():
    # Scenario 1: Merge Income Statement (Quarterly)
    print("\n--- Test 1: Merge Quarterly Data ---")
    old_data = pd.DataFrame({
        'Ticker': ['AAA', 'AAA'],
        'Year': ['2023', '2023'],
        'Quarter': ['1', '2'],
        'Revenue': [100, 110]
    })
    
    new_data = pd.DataFrame({
        'Ticker': ['AAA', 'BBB'],
        'Year': ['2023', '2023'],
        'Quarter': ['2', '2'],
        'Revenue': [120, 200]  # AAA Q2 updated (110 -> 120), BBB new
    })
    
    merged = merge_logic(old_data, new_data, "income")
    print(merged)
    
    # Expect: AAA Q1: 100, AAA Q2: 120 (updated), BBB Q2: 200
    assert len(merged) == 3
    assert merged[merged['ticker']=='AAA'][merged['quarter']=='2']['revenue'].iloc[0] == 120
    print("✅ Test 1 Passed")

    # Scenario 2: Merge Summary (Yearly)
    print("\n--- Test 2: Merge Yearly Summary ---")
    old_summary = pd.DataFrame({
        'ticker': ['AAA', 'CCC'],
        'year': ['2022', '2022'],
        'revenue': [1000, 500]
    })
    new_summary = pd.DataFrame({
        'ticker': ['AAA'],
        'year': ['2023'],
        'revenue': [1100]
    })
    
    merged_summary = merge_logic(old_summary, new_summary, "summary_y")
    print(merged_summary)
    
    # Expect: AAA 2022, CCC 2022, AAA 2023
    assert len(merged_summary) == 3
    print("✅ Test 2 Passed")

if __name__ == "__main__":
    test_merge()
