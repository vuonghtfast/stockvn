# Force Streamlit Reload
# Run this to clear Streamlit cache and reload modules

import streamlit as st
import sys
import importlib

# Clear all caches
st.cache_data.clear()
st.cache_resource.clear()

# Reload dashboard_tabs module
if 'dashboard_tabs' in sys.modules:
    importlib.reload(sys.modules['dashboard_tabs'])
    print("[OK] Reloaded dashboard_tabs module")
else:
    print("[X] dashboard_tabs not loaded yet")

print("[OK] Cache cleared!")
print("Now restart Streamlit: Ctrl+C then run 'streamlit run dashboard.py'")
