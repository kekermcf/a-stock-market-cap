#!/usr/bin/env python3
"""
每日自动刷新脚本：
1. 检测最新交易日（自动跳过周末和节假日）
2. 拉取最新市值数据
3. 重新计算涨跌幅
4. 生成HTML报告
"""
import json, requests, time, concurrent.futures, os, sys, csv, glob
from datetime import datetime, timedelta

DATA_DIR = 'c:/Users/LG-NB/WorkBuddy/20260425113716'
CACHE_DIR = f'{DATA_DIR}/cache'
os.makedirs(CACHE_DIR, exist_ok=True)

TUSHARE_TOKEN = '0ea302669814ada44d52d64f5fb924b5f4ffd50215924322229eb54b'
QQ_URL = 'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get'
QQ_HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
EM_URL = 'https://datacenter.eastmoney.com/securities/api/data/v1/get'
EM_HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

sys.path.insert(0, r'C:\Users\LG-NB\.workbuddy\plugins\marketplaces\cb_teams_marketplace\plugins\finance-data\skills\neodata-financial-search\scripts')
from query import query_neodata

def parse_ts_code(ts_code):
    parts = ts_code.split('.')
    if len(parts) == 2:
        return parts[0], parts[1].lower() + parts[0]
    return ts_code, ts_code

def tushare_call(api_name, params=None, fields=''):
    import urllib.request
    payload = json.dumps({
        'api_name': api_name, 'token': TUSHARE_TOKEN,
        'params': params or {}, 'fields': fields
    })
    req = urllib.request.Request(
        'https://api.tsws.org/v1/tushare',
        data=payload.encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            j = json.loads(resp.read().decode('utf-8'))
            return j.get('data', {})
    except:
        return {}

def get_latest_trade_date():
    """获取最新交易日（当日的bak_basic数据可能还没出来，自动回退）"""
    # 用Tushare交易日历
    today = datetime.now().strftime('%Y%m%d')
    data = tushare_call('trade_cal', {'exchange': 'SSE', 'start_date': '20260420', 'end_date': today}, 'cal_date,is_open')
    if data and data.get('records'):
        for rec in reversed(data['records']):
            if rec.get('is_open') == 1:
                return rec['cal_date']
    # Fallback: 用上一个工作日
    d = datetime.now()
    while d.weekday() >= 5:  # skip weekend
        d -= timedelta(days=1)
    return d.strftime('%Y%m%d')

def find_available_trade_date(preferred_date):
    """如果指定日期没有数据，往前找最近的可用交易日"""
    # 先检查缓存的mv_data文件（最可靠的判断标准）
    cache_path = f'{CACHE_DIR}/mv_data_{preferred_date}.json'
    if os.path.exists(cache_path):
        return preferred_date
    
    # 尝试从API获取（带完整字段验证，不仅要records还要有total_mv）
    data = tushare_call('bak_basic', {'trade_date': preferred_date}, 'ts_code,total_mv')
    if data and data.get('records'):
        # 验证至少有一些股票有市值数据
        has_mv = any(r.get('total_mv') for r in data['records'][:10])
        if has_mv:
            return preferred_date
        print(f'  API returned records for {preferred_date} but no total_mv data, trying earlier...')
    
    # 往前回退最多10个自然日
    d = datetime.strptime(preferred_date, '%Y%m%d')
    for _ in range(10):
        d -= timedelta(days=1)
        dt_str = d.strftime('%Y%m%d')
        # 优先检查本地缓存
        cache_path = f'{CACHE_DIR}/mv_data_{dt_str}.json'
        if os.path.exists(cache_path):
            print(f'  Using cached data from {dt_str}')
            return dt_str
        # 再尝试API
        data = tushare_call('bak_basic', {'trade_date': dt_str}, 'ts_code,total_mv')
        if data and data.get('records'):
            has_mv = any(r.get('total_mv') for r in data['records'][:10])
            if has_mv:
                return dt_str
    
    print(f'  No available data found in the past 10 days, using cached data if any...')
    # Last resort: find any existing mv_data cache file
    import glob
    existing = sorted(glob.glob(f'{CACHE_DIR}/mv_data_*.json'), reverse=True)
    if existing:
        date_str = os.path.basename(existing[0]).replace('mv_data_', '').replace('.json', '')
        print(f'  Using latest cached data from {date_str}')
        return date_str
    
    return preferred_date  # fallback

def fetch_mv_data(trade_date):
    """拉取市值数据（从缓存或API）"""
    cache_path = f'{CACHE_DIR}/mv_data_{trade_date}.json'
    
    # Always check cache first
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            stocks = json.load(f)
            if stocks:
                print(f'  Loaded {len(stocks)} stocks from cache ({trade_date})')
                return stocks
    
    # Get basic stock list from API
    data = tushare_call('bak_basic', {'trade_date': trade_date}, 'ts_code,name,industry,area,total_mv,pe,pb,close,pct_chg')
    if not data or not data.get('records'):
        print(f'  API returned no records for {trade_date}')
        return None
    
    stocks = data['records']
    # Filter mv >= 200
    stocks = [s for s in stocks if s.get('total_mv') and float(s['total_mv']) >= 200]
    if not stocks:
        print(f'  API returned records but no valid total_mv for {trade_date}')
        return None
    
    stocks.sort(key=lambda x: float(x.get('total_mv', 0)), reverse=True)
    print(f'  Fetched {len(stocks)} stocks from API ({trade_date})')
    
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(stocks, f, ensure_ascii=False)
    
    return stocks

def fetch_finance_data(stocks):
    """从缓存获取财务数据"""
    cache_path = f'{CACHE_DIR}/finance_data.json'
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def fetch_neodata_profiles(stocks):
    """从缓存获取NeoData简介"""
    cache_path = f'{CACHE_DIR}/neodata_profiles.json'
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def fetch_kline_monthly_mv(stocks):
    """从缓存获取月度K线"""
    cache_path = f'{CACHE_DIR}/kline_monthly_mv.json'
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def recalc_ytd(trade_date):
    """重新计算涨跌幅：2024/2025年初至最新截止日"""
    annual_cache_path = f'{CACHE_DIR}/annual_pctchg.json'
    annual_data = {}
    if os.path.exists(annual_cache_path):
        with open(annual_cache_path, 'r', encoding='utf-8') as f:
            annual_data = json.load(f)
    
    # Load stock list
    with open(f'{DATA_DIR}/stock_data_full.json', 'r', encoding='utf-8') as f:
        stocks = json.load(f)
    
    end_date = f'{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:8]}'
    need_codes = [(s['ts_code'], parse_ts_code(s['ts_code'])[1]) for s in stocks]
    
    results = dict(annual_data)  # copy existing
    errors = 0
    
    def fetch_kline(qq_code):
        try:
            resp = requests.get(QQ_URL, params={
                '_var': 'k', 'param': f'{qq_code},day,2024-01-01,,1000,qfq'
            }, headers=QQ_HEADERS, timeout=15)
            text = resp.text
            idx = text.index('=')
            j = json.loads(text[idx+1:])
            klines = j['data'][qq_code].get('qfqday', [])
            return [(k[0], float(k[2])) for k in klines] if klines else None
        except:
            return None
    
    def calc_ytd(klines, start_date, end_date):
        if not klines: return None
        start_close = end_close = None
        for date_str, close in klines:
            if date_str >= start_date and start_close is None:
                start_close = close
            if date_str <= end_date:
                end_close = close
        if start_close and end_close and start_close > 0:
            return round((end_close - start_close) / start_close * 100, 2)
        return None
    
    batch_size = 100
    for i in range(0, len(need_codes), batch_size):
        batch = need_codes[i:i+batch_size]
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fetch_kline, qq): ts for ts, qq in batch}
            for fut in concurrent.futures.as_completed(futures):
                ts_code = futures[fut]
                klines = fut.result()
                if klines:
                    y24 = calc_ytd(klines, '2024-01-02', end_date)
                    y25 = calc_ytd(klines, '2025-01-02', end_date)
                    results[ts_code] = {
                        'ytd_2024': y24,
                        'ytd_2025': y25,
                        'ytd_2026': annual_data.get(ts_code, {}).get('ytd_2026')
                    }
                else:
                    errors += 1
    
    # Also update ytd_2026 from NeoData for new date
    # Try to get ytd_2026 from K-line
    y26_start = f'{trade_date[:4]}-01-02'
    for i in range(0, len(need_codes), batch_size):
        batch = need_codes[i:i+batch_size]
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fetch_kline, qq): ts for ts, qq in batch}
            for fut in concurrent.futures.as_completed(futures):
                ts_code = futures[fut]
                klines = fut.result()
                if klines:
                    y26 = calc_ytd(klines, y26_start, end_date)
                    if y26 is not None and ts_code in results:
                        results[ts_code]['ytd_2026'] = y26
    
    with open(annual_cache_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False)
    
    return results

def main():
    print('=' * 60)
    print('A股 市值>200亿 每日自动刷新')
    print('=' * 60)
    
    # Step 1: Get latest trade date (with fallback)
    preferred_date = get_latest_trade_date()
    print(f'\nPreferred trade date: {preferred_date}')
    trade_date = find_available_trade_date(preferred_date)
    if trade_date != preferred_date:
        print(f'  No data for {preferred_date}, falling back to {trade_date}')
    else:
        print(f'Latest trade date: {trade_date}')
    
    # Step 2: Fetch market value
    print('\n[1/5] Market Value Data')
    stocks = fetch_mv_data(trade_date)
    if not stocks:
        print('No market data available. Exiting.')
        return
    print(f'  {len(stocks)} stocks with MV >= 200B')
    
    # Step 3: Load cached data
    print('\n[2/5] Finance & Profile Data (from cache)')
    fin_data = fetch_finance_data(stocks)
    profiles = fetch_neodata_profiles(stocks)
    mv_cache = fetch_kline_monthly_mv(stocks)
    print(f'  Finance: {len(fin_data)}, Profiles: {len(profiles)}, MV history: {len(mv_cache)}')
    
    # Step 4: Recalc YTD
    print('\n[3/5] Recalculating YTD')
    annual_data = recalc_ytd(trade_date)
    print(f'  {len(annual_data)} stocks with annual data')
    
    # Step 5: Auto-update AH status (best-effort)
    print('\n[4/6] Auto-update AH status')
    try:
        # Call update_ah_status_v2.py if exists
        ah_updater = os.path.join(DATA_DIR, 'update_ah_status_v2.py')
        if os.path.exists(ah_updater):
            import subprocess as sp_ah
            r = sp_ah.run([sys.executable, ah_updater],
                               capture_output=True, text=True, timeout=120,
                               cwd=DATA_DIR)
            if r.returncode == 0:
                print('  AH status auto-updated.')
            else:
                print(f'  AH update skipped: {r.stderr[:100]}')
        else:
            # Try AKShare directly
            try:
                import akshare as ak
                df = ak.stock_zh_ah_name()
                print(f'  AKShare returned {len(df)} AH stocks')
            except:
                print('  AKShare not available, skipping AH update')
    except Exception as e:
        print(f'  AH update failed (non-critical): {e}')

    # Step 6: Merge all data
    print('\n[5/6] Merging all data')
    output = []
    for s in stocks:
        ts_code = s['ts_code']
        code6, _ = parse_ts_code(ts_code)
        fin = fin_data.get(code6, {})
        prof = profiles.get(ts_code, {})
        mv = mv_cache.get(ts_code)
        ann = annual_data.get(ts_code, {})
        
        industry_l2 = prof.get('industry_l2', '')
        industry_l1 = prof.get('industry_l1', '') or s.get('industry', '')
        
        output.append({
            'ts_code': ts_code,
            'name': s['name'],
            'industry': industry_l2 or industry_l1,
            'industry_l1': industry_l1,
            'industry_l2': industry_l2,
            'area': s.get('area', ''),
            'close': s['close'],
            'pct_chg': s['pct_chg'],
            'pe': s.get('pe', ''),
            'pb': s.get('pb', ''),
            'total_mv': s['total_mv'],
            'revenue': fin.get('revenue'),
            'gross_profit': fin.get('gross_profit'),
            'net_profit': fin.get('net_profit'),
            'gpr': fin.get('gpr'),
            'npm': fin.get('npm'),
            'mv_history': mv,
            'list_date': prof.get('list_date', ''),
            'business_desc': prof.get('business_desc', ''),
            'main_biz': prof.get('main_biz', []),
            'products': prof.get('products', []),
            'regions': prof.get('regions', []),
            'ytd_2024': ann.get('ytd_2024'),
            'ytd_2025': ann.get('ytd_2025'),
            'ytd_2026': ann.get('ytd_2026'),
        })
    
    out_path = f'{DATA_DIR}/stock_data_full.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False)
    
    csv_path = f'{DATA_DIR}/A股市值超200亿名单_{trade_date}.csv'
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'ts_code', 'name', 'industry', 'industry_l1', 'industry_l2',
            'area', 'close', 'pct_chg', 'pe', 'pb', 'total_mv',
            'revenue', 'gross_profit', 'gpr', 'net_profit', 'npm',
            'list_date', 'ytd_2024', 'ytd_2025', 'ytd_2026'
        ], extrasaction='ignore')
        writer.writeheader()
        writer.writerows(output)
    
    # Step 6: Generate HTML
    print('\n[5/5] Generating HTML report')
    import subprocess as sp
    r = sp.run([sys.executable, f'{DATA_DIR}/gen_report.py'], capture_output=True, text=True, cwd=DATA_DIR, timeout=300)
    if r.returncode == 0:
        print(f'  {r.stdout.strip()}')
    else:
        print(f'  Error: {r.stderr.strip()[:300]}')
    
    # Step 7: Git push to GitHub Pages
    print('\n[6/6] Pushing to GitHub Pages')
    try:
        env = os.environ.copy()
        env['GIT_SSH_COMMAND'] = 'ssh -o StrictHostKeyChecking=accept-new'
        import subprocess as sp2
        # Use full git path since it may not be in PATH on Windows
        git_exe = os.environ.get('GIT_EXE', r'C:\Program Files\Git\cmd\git.exe')
        cmds = [
            [git_exe, 'add', '-A'],
            [git_exe, 'commit', '-m', f'Auto update: {trade_date}'],
            [git_exe, 'push', 'origin', 'main'],
        ]
        for cmd in cmds:
            result = sp2.run(cmd, capture_output=True, text=True, cwd=DATA_DIR, env=env, timeout=60)
            if result.returncode != 0 and 'nothing to commit' not in result.stdout and 'nothing to commit' not in result.stderr:
                if 'no changes added' not in result.stdout and 'no changes added' not in result.stderr:
                    print(f'  Warning: {" ".join(cmd)}: {result.stderr.strip()[:200]}')
            else:
                if 'commit' in cmd[1]:
                    print(f'  Committed: {trade_date}')
                elif 'push' in cmd[1]:
                    print(f'  Pushed to GitHub!')
    except Exception as e:
        print(f'  Git push failed: {e}')
    
    print('\nDone!')

if __name__ == '__main__':
    main()
