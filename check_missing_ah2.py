"""Check missing A+H stocks by fetching from eastmoney sector API"""
import json, urllib.request

with open('c:/Users/LG-NB/WorkBuddy/20260425113716/cache/ah_status.json', 'r', encoding='utf-8') as f:
    ah_status = json.load(f)

# Try different eastmoney API endpoint for AH concept stocks
url = 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=500&np=1&fltt=2&invt=2&fid=f3&fs=b:BK2421&fields=f12,f13,f14'
try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    
    if data.get('data') and data['data'].get('diff'):
        stocks = data['data']['diff']
        print(f'Got {len(stocks)} AH stocks from eastmoney')
    else:
        print(f'API returned no data: {json.dumps(data, ensure_ascii=False)[:300]}')
        stocks = []
except Exception as e:
    print(f'Error: {e}')
    stocks = []

# If that didn't work, try another approach - use the AH premium index constituents
if not stocks:
    # Try ths AH concept
    url2 = 'https://datacenter-web.eastmoney.com/api/data/v1/get?sortColumns=SECURITY_CODE&sortTypes=1&pageSize=500&pageNumber=1&reportName=RPT_AH_LIST&columns=SECURITY_CODE,SECURITY_NAME_ABBR,TRADE_MARKET_CODE&source=WEB&client=WEB'
    try:
        req = urllib.request.Request(url2, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data2 = json.loads(resp.read().decode('utf-8'))
        
        if data2.get('result') and data2['result'].get('data'):
            stocks = data2['result']['data']
            print(f'Got {len(stocks)} from datacenter API')
            
            missing = []
            wrong = []
            for s in stocks:
                code = s.get('SECURITY_CODE', '')
                name = s.get('SECURITY_NAME_ABBR', '')
                market_code = s.get('TRADE_MARKET_CODE', '')
                
                # Determine ts_code
                if market_code == '1' or code.startswith('6'):
                    ts_code = code + '.SH'
                else:
                    ts_code = code + '.SZ'
                
                status = ah_status.get(ts_code, 'NOT_FOUND')
                if status == 'NOT_FOUND':
                    missing.append((ts_code, name))
                elif status != 'listed':
                    wrong.append((ts_code, name, status))
            
            print(f'\nMissing (should be listed):')
            for tc, nm in missing:
                print(f'  {tc} {nm}')
            
            print(f'\nWrong status (should be listed):')
            for tc, nm, st in wrong:
                print(f'  {tc} {nm} -> {st}')
            
            print(f'\nTotal missing: {len(missing)}, wrong: {len(wrong)}')
        else:
            print(f'datacenter API also failed: {json.dumps(data2, ensure_ascii=False)[:300]}')
    except Exception as e2:
        print(f'datacenter error: {e2}')
