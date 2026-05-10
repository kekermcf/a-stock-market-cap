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

# DATA_DIR: 项目根目录 = 脚本所在目录（macOS/Linux 兼容）
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(DATA_DIR, 'cache')
os.makedirs(CACHE_DIR, exist_ok=True)

QQ_URL = 'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get'
QQ_HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
EM_URL = 'https://datacenter.eastmoney.com/securities/api/data/v1/get'
EM_HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# NeoData plugin path (macOS 路径，Windows 不再需要)
_neodata_paths = [
    os.path.expanduser('~/.workbuddy/plugins/marketplaces/cb_teams_marketplace/plugins/finance-data/skills/neodata-financial-search/scripts'),
]
for _ndp in _neodata_paths:
    if os.path.isdir(_ndp):
        sys.path.insert(0, _ndp)
        break
try:
    from query import query_neodata
except ImportError:
    query_neodata = None
    print('WARNING: query_neodata not available')

def parse_ts_code(ts_code):
    parts = ts_code.split('.')
    if len(parts) == 2:
        return parts[0], parts[1].lower() + parts[0]
    return ts_code, ts_code

# 交易日检测用样本股（大盘蓝筹，必然每个交易日都有K线）
_TRADE_DATE_SAMPLES = ['sh600519', 'sz000001', 'sz000858']  # 茅台、平安银行、五粮液

def _check_kline_exists(qq_code, date_str):
    """用QQ K-line检查某日期是否有交易数据"""
    try:
        # date_str 是 YYYYMMDD，转成 YYYY-MM-DD 格式匹配K线
        target = f'{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}'
        # 查最近10天K线
        resp = requests.get(QQ_URL, params={
            '_var': 'k', 'param': f'{qq_code},day,2026-04-15,,20,qfq'
        }, headers=QQ_HEADERS, timeout=10)
        text = resp.text
        idx = text.index('=')
        j = json.loads(text[idx+1:])
        klines = j['data'][qq_code].get('qfqday', [])
        # 检查最后几条K线日期是否包含目标日期
        for k in klines[-5:]:
            if k[0] == target:
                return True
        return False
    except:
        return None  # 异常时返回None（不确定）

def get_latest_trade_date():
    """获取最新交易日：跳过周末后用QQ K-line交叉验证（兼顾节假日）"""
    d = datetime.now()
    # 如果是早上9点前，T日数据可能还没出来，从T-1开始试
    if d.hour < 9:
        d -= timedelta(days=1)
    
    for _ in range(15):  # 最多回退15天
        if d.weekday() >= 5:  # 跳过周末
            d -= timedelta(days=1)
            continue
        date_str = d.strftime('%Y%m%d')
        
        # 用样本股交叉验证
        ok_count = 0
        for qq_code in _TRADE_DATE_SAMPLES:
            result = _check_kline_exists(qq_code, date_str)
            if result is True:
                ok_count += 1
            elif result is False:
                pass  # 明确没有数据
            else:
                ok_count += 0.5  # 不确定时给半票
        
        if ok_count >= 2:  # 至少2只股票确认有数据
            print(f'  Verified trade date: {date_str} ({ok_count:.1f}/3 samples ok)')
            return date_str
        
        d -= timedelta(days=1)
    
    # 兜底：纯周末跳过
    d = datetime.now()
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    fallback = d.strftime('%Y%m%d')
    print(f'  WARNING: K-line verification failed, using fallback: {fallback}')
    return fallback

def find_available_trade_date(preferred_date):
    """如果指定日期缓存不存在，往前找最近的可用缓存（不调Tushare，已挂）"""
    # 先检查缓存的mv_data文件
    cache_path = f'{CACHE_DIR}/mv_data_{preferred_date}.json'
    if os.path.exists(cache_path):
        return preferred_date
    
    # 往前回退最多10个自然日，找缓存
    d = datetime.strptime(preferred_date, '%Y%m%d')
    for _ in range(10):
        d -= timedelta(days=1)
        dt_str = d.strftime('%Y%m%d')
        cache_path = f'{CACHE_DIR}/mv_data_{dt_str}.json'
        if os.path.exists(cache_path):
            print(f'  Using cached data from {dt_str}')
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
    """拉取市值数据（从缓存；无缓存时返回None，由QQ fallback接管）"""
    cache_path = f'{CACHE_DIR}/mv_data_{trade_date}.json'
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            stocks = json.load(f)
            if stocks:
                print(f'  Loaded {len(stocks)} stocks from cache ({trade_date})')
                return stocks
    print(f'  No cache for {trade_date}, will use QQ fallback')
    return None

def fetch_mv_via_qq(trade_date):
    """通过腾讯K线API推算最新市值（Tushare不可用时的fallback）
    返回 (stocks_list, actual_date_str) 元组
    """
    # 1. 找到最新的缓存mv_data作为基准
    existing = sorted(glob.glob(f'{CACHE_DIR}/mv_data_*.json'))
    if not existing:
        print('  No cached mv_data to use as baseline')
        return None, None
    baseline_path = existing[-1]
    base_date = os.path.basename(baseline_path).replace('mv_data_', '').replace('.json', '')
    with open(baseline_path, 'r', encoding='utf-8') as f:
        base_stocks = json.load(f)
    
    print(f'  Using {base_date} data as baseline ({len(base_stocks)} stocks), updating via QQ K-line...')
    
    # Build code lookup: ts_code -> old data
    old_map = {}
    for s in base_stocks:
        ts_code = s['ts_code']
        code6, qq_code = parse_ts_code(ts_code)
        old_map[ts_code] = {
            'old_mv': float(s.get('total_mv', 0)),
            'old_close': float(s.get('close', 0)),
            'qq_code': qq_code
        }
    
    # 先抽样检查实际最新K线日期（用前3只股票）
    sample_codes = list(old_map.keys())[:3]
    actual_kline_date = None
    for sc in sample_codes:
        try:
            resp = requests.get(QQ_URL, params={
                '_var': 'k', 'param': f'{old_map[sc]["qq_code"]},day,2026-04-20,,5,qfq'
            }, headers=QQ_HEADERS, timeout=10)
            text = resp.text
            idx = text.index('=')
            j = json.loads(text[idx+1:])
            klines = j['data'][old_map[sc]['qq_code']].get('qfqday', [])
            if klines:
                d = klines[-1][0].replace('-', '')
                actual_kline_date = d
                break
        except:
            pass
    if actual_kline_date:
        print(f'  QQ K-line latest date: {actual_kline_date}')
    else:
        actual_kline_date = trade_date
    
    def get_latest_from_qq(qq_code):
        """获取最新收盘价和涨跌幅"""
        try:
            resp = requests.get(QQ_URL, params={
                '_var': 'k', 'param': f'{qq_code},day,2026-04-20,,15,qfq'
            }, headers=QQ_HEADERS, timeout=10)
            text = resp.text
            idx = text.index('=')
            j = json.loads(text[idx+1:])
            klines = j['data'][qq_code].get('qfqday', [])
            if not klines:
                return None, None, None
            # 取最新一条
            latest = klines[-1]
            close = float(latest[2])
            kline_date = latest[0].replace('-', '')
            # 计算涨跌幅（相对于前一天）
            if len(klines) >= 2:
                prev_close = float(klines[-2][2])
                pct = round((close - prev_close) / prev_close * 100, 2)
            else:
                pct = 0
            return close, pct, kline_date
        except:
            return None, None, None
    
    # 并发获取最新价格
    updated = []
    errors = 0
    codes = list(old_map.keys())
    date_counts = {}  # 统计实际K线日期分布
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(get_latest_from_qq, old_map[c]['qq_code']): c for c in codes}
        for fut in concurrent.futures.as_completed(futures):
            ts_code = futures[fut]
            old = old_map[ts_code]
            new_close, new_pct, kline_date = fut.result()
            if kline_date:
                date_counts[kline_date] = date_counts.get(kline_date, 0) + 1
            if new_close and old['old_close'] > 0:
                # 新市值 = 旧市值 × (新价格 / 旧价格)
                ratio = new_close / old['old_close']
                new_mv = round(old['old_mv'] * ratio, 2)
            else:
                new_close = old['old_close']
                new_mv = old['old_mv']
                new_pct = 0
                errors += 1
            
            # 读取原始stock记录并更新
            base_s = next((s for s in base_stocks if s['ts_code'] == ts_code), None)
            if base_s:
                updated.append({
                    'ts_code': ts_code,
                    'name': base_s.get('name', ''),
                    'industry': base_s.get('industry', ''),
                    'area': base_s.get('area', ''),
                    'close': new_close,
                    'pct_chg': new_pct,
                    'pe': base_s.get('pe', ''),
                    'pb': base_s.get('pb', ''),
                    'total_mv': new_mv,
                })
    
    # 确定实际数据日期（多数股票的K线日期）
    if date_counts:
        actual_date = max(date_counts, key=date_counts.get)
    else:
        actual_date = actual_kline_date
    print(f'  K-line date distribution: {date_counts}')
    print(f'  Using actual date: {actual_date}')
    updated = [s for s in updated if s['total_mv'] >= 200]
    updated.sort(key=lambda x: x['total_mv'], reverse=True)
    
    if errors > 0:
        print(f'  {errors} stocks failed to update, using old close prices')
    print(f'  Updated {len(updated)} stocks via QQ K-line')
    
    # Save cache — 用实际K线日期，不是preferred_date
    cache_path = f'{CACHE_DIR}/mv_data_{actual_date}.json'
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(updated, f, ensure_ascii=False)
    
    return updated, actual_date

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
        # Tushare不可用，尝试QQ K-line fallback
        print('  Tushare unavailable, trying QQ K-line fallback...')
        result = fetch_mv_via_qq(preferred_date)
        if result[0]:
            stocks = result[0]
            trade_date = result[1]  # 用实际K线日期
    elif trade_date != preferred_date:
        # 回退到了旧日期，尝试用QQ K-line更新到最新交易日
        print(f'  Data date {trade_date} is older than preferred {preferred_date}, trying QQ update...')
        result = fetch_mv_via_qq(preferred_date)
        if result[0] and len(result[0]) >= len(stocks) * 0.9:  # 至少90%的股票更新成功
            stocks = result[0]
            trade_date = result[1]  # 用实际K线日期
        else:
            print(f'  QQ update insufficient ({len(result[0]) if result[0] else 0} stocks), keeping cached data')
    if not stocks:
        print('No market data available. Exiting.')
        return
    print(f'  {len(stocks)} stocks with MV >= 200B (data as of {trade_date})')
    
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
    print('\n[4/8] Auto-update AH status')
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
    print('\n[5/8] Merging all data')
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
    print('\n[5/8] Generating HTML report')
    import subprocess as sp
    r = sp.run([sys.executable, f'{DATA_DIR}/gen_report.py'], capture_output=True, text=True, cwd=DATA_DIR, timeout=300)
    if r.returncode == 0:
        print(f'  {r.stdout.strip()}')
    else:
        print(f'  Error: {r.stderr.strip()[:300]}')

    # Generate watchlist page
    print('  Generating watchlist page...')
    r2 = sp.run([sys.executable, f'{DATA_DIR}/gen_watchlist.py'], capture_output=True, text=True, cwd=DATA_DIR, timeout=300)
    if r2.returncode == 0:
        print(f'  {r2.stdout.strip()}')
    else:
        print(f'  Watchlist Error: {r2.stderr.strip()[:300]}')

    # Step 7: Fetch & Generate H-share (HK) page
    print('\n[6/8] Fetching HK stock data...')
    r3 = sp.run([sys.executable, f'{DATA_DIR}/fetch_hk_data.py'], capture_output=True, text=True, cwd=DATA_DIR, timeout=600)
    if r3.returncode == 0:
        print(f'  {r3.stdout.strip()}')
    else:
        print(f'  HK fetch Error: {r3.stderr.strip()[:300]}')

    print('\n[7/8] Generating HK report...')
    r4 = sp.run([sys.executable, f'{DATA_DIR}/gen_hk_report.py'], capture_output=True, text=True, cwd=DATA_DIR, timeout=300)
    if r4.returncode == 0:
        print(f'  {r4.stdout.strip()}')
    else:
        print(f'  HK report Error: {r4.stderr.strip()[:300]}')

    # Step 8: Git push to GitHub Pages
    print('\n[8/8] Pushing to GitHub Pages')
    try:
        env = os.environ.copy()
        env['GIT_SSH_COMMAND'] = 'ssh -o StrictHostKeyChecking=accept-new'
        import subprocess as sp2
        # Use full git path since it may not be in PATH on Windows
        git_exe = os.environ.get('GIT_EXE', 'git')
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
