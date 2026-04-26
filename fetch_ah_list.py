"""Fetch AH concept stocks from AKShare and compare with our ah_status.json"""
import sys
sys.path.insert(0, 'C:\\Users\\LG-NB\\.workbuddy\\skills\\akshare\\scripts')
import akshare as ak
import json

# Get AH concept stock list
try:
    # stock_board_concept_cons_em - get concept board constituents
    df = ak.stock_board_concept_cons_em(symbol="AH股")
    print(f'AKShare AH concept: {len(df)} stocks')
    print(f'Columns: {list(df.columns)}')
    print(df.head(10).to_string(index=False))
except Exception as e:
    print(f'AH concept failed: {e}')
    # Try alternative
    try:
        df = ak.stock_hk_ah_name_em()
        print(f'AH name list: {len(df)}')
        print(f'Columns: {list(df.columns)}')
        print(df.head(10).to_string(index=False))
    except Exception as e2:
        print(f'AH name also failed: {e2}')
        df = None

if df is not None:
    with open('c:/Users/LG-NB/WorkBuddy/20260425113716/cache/ah_status.json', 'r', encoding='utf-8') as f:
        ah_status = json.load(f)
    
    # Find A-share codes
    missing = []
    for _, row in df.iterrows():
        code = str(row.iloc[0]).zfill(6)  # stock code
        name = str(row.iloc[1])
        
        # Determine ts_code
        if code.startswith('6'):
            ts_code = code + '.SH'
        else:
            ts_code = code + '.SZ'
        
        status = ah_status.get(ts_code, 'NOT_FOUND')
        if status != 'listed':
            missing.append((ts_code, name, status))
    
    print(f'\nMissing or wrong status (should be listed):')
    for tc, nm, st in missing:
        print(f'  {tc} {nm} -> {st}')
    print(f'\nTotal: {len(missing)}')
