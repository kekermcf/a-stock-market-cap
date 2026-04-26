import akshare as ak
import json

# Get AH stock spot data (A-share perspective)
df = ak.stock_zh_ah_spot_em()
print(f'Total: {len(df)}')
print(f'Columns: {list(df.columns)}')
df.to_csv('c:/Users/LG-NB/WorkBuddy/20260425113716/ah_spot_akshare.csv', index=False, encoding='utf-8-sig')

with open('c:/Users/LG-NB/WorkBuddy/20260425113716/cache/ah_status.json', 'r', encoding='utf-8') as f:
    ah_status = json.load(f)

# Find A-share code column
code_col = None
for col in df.columns:
    if '代码' in str(col):
        code_col = col
        break
if code_col is None:
    code_col = df.columns[0]

name_col = None
for col in df.columns:
    if '名称' in str(col):
        name_col = col
        break
if name_col is None:
    name_col = df.columns[1] if len(df.columns) > 1 else None

print(f'Using code_col={code_col}, name_col={name_col}')
print(f'Sample: {df[code_col].head(3).tolist()}')

missing = []
wrong = []
for _, row in df.iterrows():
    code = str(row[code_col]).zfill(6)
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

print(f'\nWrong status (should be listed but is something else):')
for tc, nm, st in wrong:
    print(f'  {tc} {nm} -> {st}')

print(f'\nTotal missing: {len(missing)}, wrong: {len(wrong)}')
