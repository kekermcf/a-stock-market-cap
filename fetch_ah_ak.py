import akshare as ak
import json

# Get AH stock name list
df = ak.stock_zh_ah_name()
print(f'Total AH stocks: {len(df)}')
print(f'Columns: {list(df.columns)}')

# Save to file for inspection
df.to_csv('c:/Users/LG-NB/WorkBuddy/20260425113716/ah_list_akshare.csv', index=False, encoding='utf-8-sig')
print('Saved to ah_list_akshare.csv')

# Load our ah_status
with open('c:/Users/LG-NB/WorkBuddy/20260425113716/cache/ah_status.json', 'r', encoding='utf-8') as f:
    ah_status = json.load(f)

# Find missing - need to figure out which column is A-share code
print('\nSample data:')
for i, row in df.head(10).iterrows():
    print(f'  {list(row.values)}')

# Try to find A-code column and compare
# The typical columns from stock_zh_ah_name are: 序号, A股代码, A股简称, A股上市日期, H股代码, H股简称, H股上市日期
a_code_col = None
for col in df.columns:
    if 'A股代码' in str(col) or '代码' in str(col):
        a_code_col = col
        break

if a_code_col is None:
    # Try first column
    a_code_col = df.columns[1]  # usually the code column
    print(f'Using column: {a_code_col}')

missing = []
wrong = []
for _, row in df.iterrows():
    code = str(row[a_code_col]).zfill(6)
    name_col = None
    for col in df.columns:
        if 'A股简称' in str(col) or '简称' in str(col):
            name_col = col
            break
    name = str(row[name_col]) if name_col else ''
    
    if code.startswith('6') or code.startswith('9'):
        ts_code = code + '.SH'
    else:
        ts_code = code + '.SZ'
    
    status = ah_status.get(ts_code, 'NOT_FOUND')
    if status == 'NOT_FOUND':
        missing.append((ts_code, name))
    elif status != 'listed':
        wrong.append((ts_code, name, status))

print(f'\nMissing from ah_status (should be listed):')
for tc, nm in missing:
    print(f'  {tc} {nm}')

print(f'\nWrong status (should be listed):')
for tc, nm, st in wrong:
    print(f'  {tc} {nm} -> {st}')

print(f'\nTotal missing: {len(missing)}, wrong: {len(wrong)}')
