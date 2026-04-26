"""Check missing A+H stocks by comparing with eastmoney AH stock list"""
import json, urllib.request

# Load current ah_status
with open('c:/Users/LG-NB/WorkBuddy/20260425113716/cache/ah_status.json', 'r', encoding='utf-8') as f:
    ah_status = json.load(f)

# Fetch AH stock list from eastmoney
# This API returns all current A+H stocks
url = 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=500&fs=b:BK2421&fields=f12,f14,f13'
try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    
    if data.get('data') and data['data'].get('diff'):
        stocks = data['data']['diff']
        print(f'Eastmoney AH stock list: {len(stocks)} stocks')
        
        missing_listed = []
        already_listed = []
        
        for s in stocks:
            code = s['f12']  # stock code like 000063
            name = s['f14']  # stock name
            market = s['f13']  # 0=SZ, 1=SH
            
            # Construct ts_code format
            if market == 1:
                ts_code = code + '.SH'
            else:
                ts_code = code + '.SZ'
            
            status = ah_status.get(ts_code, 'NOT_FOUND')
            if status == 'NOT_FOUND':
                missing_listed.append((ts_code, name))
            elif status != 'listed':
                already_listed.append((ts_code, name, status))
        
        print(f'\nMissing from ah_status.json (should be listed):')
        for ts_code, name in missing_listed:
            print(f'  {ts_code} {name}')
        
        print(f'\nWrong status (should be listed but marked as {status}):')
        for ts_code, name, status in already_listed:
            print(f'  {ts_code} {name} -> currently: {status}')
        
        print(f'\nTotal missing: {len(missing_listed)}')
        print(f'Total wrong status: {len(already_listed)}')
    else:
        print('No data returned from eastmoney API')
        print(json.dumps(data, ensure_ascii=False)[:500])
except Exception as e:
    print(f'Error: {e}')

# Also check: stocks in ah_status as "listed" but NOT in eastmoney (might be delisted or wrong)
listed_in_cache = [k for k, v in ah_status.items() if v == 'listed']
print(f'\nListed in our cache: {len(listed_in_cache)}')
