import akshare as ak
import json
import time

# Test: get stock basic info with city
# Try stock_basic_info_em or similar
try:
    # This function returns basic stock info including city
    df = ak.stock_basic_info_em()
    print("stock_basic_info_em columns:", df.columns.tolist())
    print(df.head(3))
except Exception as e:
    print(f"stock_basic_info_em failed: {e}")

try:
    df2 = ak.stock_info_a_code_name()
    print("stock_info_a_code_name sample:", df2.head(3))
except Exception as e:
    print(f"stock_info_a_code_name failed: {e}")
