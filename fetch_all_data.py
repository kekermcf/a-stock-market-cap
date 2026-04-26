#!/usr/bin/env python3
"""
A股市值>200亿 完整数据获取脚本 v6
====================================
改动：
1. 涨跌幅改为2024/2025/2026 YTD三列
2. 行业改为NeoData二级行业（更细分）
3. 弹窗增加公司简介（上市时间、业务模式、主营构成）
4. 缓存逻辑：市值数据按截止日期缓存，财务数据缓存后复用
5. NeoData批量查询：每批5只，获取行业+简介+YTD涨跌幅

数据源：
- Tushare bak_basic: 基础数据（总股本）
- 腾讯财经API: 收盘价、日K线
- 东方财富API: 2025年报财务数据
- NeoData: 二级行业、公司简介、YTD涨跌幅

缓存文件：
- cache/mv_data_{date}.json — 按日期的市值数据缓存
- cache/finance_data.json — 财务数据缓存
- cache/neodata_profiles.json — NeoData公司简介缓存
- cache/kline_monthly_mv.json — 月度市值采样缓存
"""
import json, requests, time, concurrent.futures, os, re, sys, csv
from datetime import datetime

DATA_DIR = 'c:/Users/LG-NB/WorkBuddy/20260425113716'
CACHE_DIR = f'{DATA_DIR}/cache'
os.makedirs(CACHE_DIR, exist_ok=True)

TUSHARE_TOKEN = '0ea302669814ada44d52d64f5fb924b5f4ffd50215924322229eb54b'
QQ_URL = 'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get'
QQ_HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
EM_URL = 'https://datacenter.eastmoney.com/securities/api/data/v1/get'
EM_HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# ========== NeoData ==========
sys.path.insert(0, r'C:\Users\LG-NB\.workbuddy\plugins\marketplaces\cb_teams_marketplace\plugins\finance-data\skills\neodata-financial-search\scripts')
from query import query_neodata

# ========== Utility ==========
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
    }).encode('utf-8')
    req = urllib.request.Request('https://api.tushare.pro', data=payload,
        headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

# ========== Step 1: 市值数据（带缓存） ==========
def fetch_mv_data(trade_date):
    """获取指定日期的市值数据，带缓存"""
    cache_path = f'{CACHE_DIR}/mv_data_{trade_date}.json'
    
    # 检查缓存
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            cached = json.load(f)
        print(f'  [Cache HIT] Loaded {len(cached)} stocks from {cache_path}')
        return cached
    
    print(f'  [Cache MISS] Fetching MV data for {trade_date} from Tushare + Tencent...')
    
    # Tushare基础数据
    print('    Step 1a: Tushare bak_basic...')
    data = tushare_call('bak_basic', {'trade_date': trade_date}, 'ts_code,name,industry,area,total_share,float_share,bvps,pb')
    if data.get('code') != 0:
        raise Exception(f'Tushare error: {data}')
    
    fields = data['data']['fields']
    items = data['data']['items']
    
    stock_map = {}
    for item in items:
        row = dict(zip(fields, item))
        ts_code = row['ts_code']
        code6, qq_code = parse_ts_code(ts_code)
        total_share = row.get('total_share', 0)
        float_share = row.get('float_share', 0)
        if total_share and total_share > 0:
            stock_map[qq_code] = {
                'ts_code': ts_code, 'qq_code': qq_code,
                'name': row['name'], 'industry': row.get('industry', ''),
                'area': row.get('area', ''),
                'total_share_yi': float(total_share),
                'float_share_yi': float(float_share),
            }
    print(f'    {len(stock_map)} valid stocks from Tushare')
    
    # 腾讯API获取收盘价
    print('    Step 1b: Tencent price API...')
    def fetch_qq_price(code):
        try:
            resp = requests.get(QQ_URL, params={'_var': 'k', 'param': f'{code},day,,,3,qfq'},
                headers=QQ_HEADERS, timeout=10)
            j = json.loads(resp.text[resp.text.index('=')+1:])
            qt = j['data'][code]['qt'][code]
            return {
                'ts_code': code,
                'close': float(qt[3]),
                'prev_close': float(qt[4]),
                'pct_chg': float(qt[32]),
                'pe': qt[62] if qt[62] else '',
                'pb': qt[63] if qt[63] else '',
            }
        except:
            return {'ts_code': code, 'error': True}
    
    all_qq_codes = list(stock_map.keys())
    price_data = {}
    errors = 0
    t0 = time.time()
    
    batch_size = 100
    for i in range(0, len(all_qq_codes), batch_size):
        batch = all_qq_codes[i:i+batch_size]
        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            futures = {executor.submit(fetch_qq_price, c): c for c in batch}
            for fut in concurrent.futures.as_completed(futures):
                r = fut.result()
                if 'error' not in r:
                    price_data[r['ts_code']] = r
                else:
                    errors += 1
    
    print(f'    Price fetch done: {len(price_data)} ok, {errors} errors in {time.time()-t0:.1f}s')
    
    # 合并数据
    results = []
    for qq_code, base in stock_map.items():
        price = price_data.get(qq_code)
        if not price:
            continue
        close = price['close']
        total_mv_yi = close * base['total_share_yi']
        if total_mv_yi >= 200:
            results.append({
                'ts_code': base['ts_code'], 'qq_code': qq_code,
                'name': base['name'], 'industry': base['industry'],
                'area': base['area'], 'close': close,
                'prev_close': price['prev_close'],
                'pct_chg': price['pct_chg'],
                'pe': price['pe'], 'pb': price['pb'],
                'total_mv': round(total_mv_yi, 2),
            })
    
    results.sort(key=lambda x: x['total_mv'], reverse=True)
    print(f'    {len(results)} stocks with MV >= 200亿')
    
    # 写缓存
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False)
    print(f'    Cached to {cache_path}')
    
    return results

# ========== Step 2: 财务数据（带缓存） ==========
def fetch_finance_data(stocks, force_refresh=False):
    """获取2025年报财务数据，带缓存"""
    cache_path = f'{CACHE_DIR}/finance_data.json'
    
    if not force_refresh and os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            cached = json.load(f)
        # 检查覆盖率
        covered = sum(1 for s in stocks if s['ts_code'] in cached and cached[s['ts_code']].get('revenue'))
        print(f'  [Finance Cache] {covered}/{len(stocks)} already have finance data')
        return cached
    
    print(f'  [Finance Cache MISS] Fetching 2025 annual report data from Eastmoney...')
    
    def fetch_finance(code6):
        try:
            resp = requests.get(EM_URL, params={
                'reportName': 'RPT_F10_FINANCE_MAINFINADATA',
                'columns': 'SECURITY_CODE,TOTALOPERATEREVE,MLR,PARENTNETPROFIT,XSMLL,XSJLL',
                'filter': f'(SECURITY_CODE="{code6}")(REPORT_DATE_NAME="2025年报")',
                'pageNumber': '1', 'pageSize': '1',
            }, headers=EM_HEADERS, timeout=10)
            data = resp.json()
            if data.get('success') and data.get('result') and data['result'].get('data'):
                item = data['result']['data'][0]
                rev = item.get('TOTALOPERATEREVE')
                mlr = item.get('MLR')
                np_ = item.get('PARENTNETPROFIT')
                gpr = item.get('XSMLL')
                npm = item.get('XSJLL')
                gross_profit = mlr if (mlr and mlr > 0) else (rev * gpr / 100 if (rev and gpr and gpr > 0) else None)
                return {
                    'code': code6,
                    'revenue': round(rev / 1e8, 2) if rev and rev > 0 else None,
                    'gross_profit': round(gross_profit / 1e8, 2) if gross_profit else None,
                    'net_profit': round(np_ / 1e8, 2) if np_ and np_ > 0 else None,
                    'gpr': round(gpr, 2) if gpr and gpr > 0 else None,
                    'npm': round(npm, 2) if npm and npm > 0 else None,
                }
            return {'code': code6}
        except:
            return {'code': code6}
    
    code_list = [parse_ts_code(s['ts_code'])[0] for s in stocks]
    fin_data = {}
    errors = 0
    t0 = time.time()
    
    batch_size = 100
    for i in range(0, len(code_list), batch_size):
        batch = code_list[i:i+batch_size]
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(fetch_finance, c): c for c in batch}
            for fut in concurrent.futures.as_completed(futures):
                r = fut.result()
                code = r.pop('code')
                if r.get('revenue') or r.get('net_profit'):
                    fin_data[code] = r
                else:
                    errors += 1
        progress = min(i + batch_size, len(code_list))
        if progress % 200 == 0 or progress == len(code_list):
            print(f'    Progress: {progress}/{len(code_list)}, ok: {len(fin_data)}, no-data: {errors}')
    
    print(f'    Done! {len(fin_data)} with finance data in {time.time()-t0:.1f}s')
    
    # 写缓存
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(fin_data, f, ensure_ascii=False)
    
    return fin_data

# ========== Step 3: NeoData 公司简介 + 二级行业 + YTD涨跌幅 ==========
def parse_neodata_company_info(content):
    """
    从NeoData '公司概况与所属行业信息' 的content中解析：
    - 上市日期
    - 二级行业
    - 主营业务描述
    """
    result = {}
    
    # 上市日期：于YYYY-MM-DD在A股上市
    m = re.search(r'于(\d{4}-\d{2}-\d{2})在A股上市', content)
    if m:
        result['list_date'] = m.group(1)
    
    # 二级行业：所属二级行业：XXX
    m = re.search(r'所属二级行业[：:]([^，。\n；]+)', content)
    if m:
        result['industry_l2'] = m.group(1).strip()
    
    # 一级行业：所属一级行业：XXX
    m = re.search(r'所属一级行业[：:]([^，。\n；]+)', content)
    if m:
        result['industry_l1'] = m.group(1).strip()
    
    # 主营业务：主营业务：...；或 主营业务[：:]...；
    m = re.search(r'主营业务[：:](.+?)(?:所属|；|。|$)', content, re.DOTALL)
    if m:
        desc = m.group(1).strip().rstrip('；').strip()
        result['business_desc'] = desc
    
    return result

def parse_neodata_ytd(content, year):
    """
    从NeoData行情或业绩内容中解析某年的年初至今涨跌幅或年涨跌幅
    """
    # Pattern: "年初至今涨跌幅： X.XX%" or "XXXX年初至今涨跌幅 X.XX%"
    patterns = [
        rf'{year}年初至今涨跌幅[：: ]*([+-]?\d+\.?\d*)%',
        rf'年初至今涨跌幅[：: ]*([+-]?\d+\.?\d*)%',  # 如果content只包含最新年份的
    ]
    for p in patterns:
        m = re.search(p, content)
        if m:
            return float(m.group(1))
    return None

def parse_neodata_mainbiz(content):
    """
    从NeoData '主营构成与业绩趋势' 中提取主营构成描述
    返回结构化的业务信息，适合弹窗展示
    """
    result = {}
    
    # 主营业务构成部分
    biz_pattern = r'主营业务构成[：:]\n((?:.*\n)*?)(?=\n主营地区|最近几年|$)'
    m = re.search(biz_pattern, content)
    if m:
        biz_text = m.group(1).strip()
        items = re.findall(r'(.+?)收入([\d,.]+)亿元（占比([\d.]+)%）', biz_text)
        if items:
            result['main_biz'] = [(name.strip(), float(rev), float(pct)) for name, rev, pct in items]
    
    # 主营收入产品分布（更细分）
    prod_pattern = r'主营收入产品分布[：:]\n((?:.*\n)*?)(?=\n最近几年|$)'
    m = re.search(prod_pattern, content)
    if m:
        prod_text = m.group(1).strip()
        prods = re.findall(r'(.+?)收入([\d,.]+)亿元（占比([\d.]+)%）', prod_text)
        if prods:
            result['products'] = [(name.strip(), float(rev), float(pct)) for name, rev, pct in prods]
    
    # 主营地区构成
    region_pattern = r'主营地区构成[：:]\n((?:.*\n)*?)(?=\n主营收入|最近几年|$)'
    m = re.search(region_pattern, content)
    if m:
        region_text = m.group(1).strip()
        regions = re.findall(r'(.+?)收入([\d,.]+)亿元（占比([\d.]+)%）', region_text)
        if regions:
            result['regions'] = [(name.strip(), float(rev), float(pct)) for name, rev, pct in regions]
    
    return result

def fetch_neodata_profiles(stocks, force_refresh=False):
    """批量查询NeoData获取公司简介、二级行业、YTD涨跌幅"""
    cache_path = f'{CACHE_DIR}/neodata_profiles.json'
    
    if not force_refresh and os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            cached = json.load(f)
        covered = sum(1 for s in stocks if s['ts_code'] in cached)
        covered_biz = sum(1 for s in stocks if s['ts_code'] in cached and cached[s['ts_code']].get('products'))
        print(f'  [NeoData Cache] {covered}/{len(stocks)} have profiles, {covered_biz} have business detail')
        if covered >= len(stocks) and covered_biz >= len(stocks):
            return cached
    
    print(f'  [NeoData Cache MISS/PARTIAL] Fetching profiles, industry, YTD from NeoData...')
    
    profiles = {}
    if not force_refresh and os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            profiles = json.load(f)
    
    # 找出需要查询的股票
    need_query = [s for s in stocks if s['ts_code'] not in profiles]
    # 找出缺少详细主营构成的股票（需要重新查询补充）
    need_biz = [s for s in stocks if s['ts_code'] in profiles and not profiles[s['ts_code']].get('products')]
    if need_biz:
        print(f'    Need business detail refresh: {len(need_biz)} stocks (have profiles but missing products)')
        need_query.extend(need_biz)  # 追加到查询列表
    print(f'    Need to query: {len(need_query)} stocks')
    
    if not need_query:
        return profiles
    
    # 分批查询，每批5只
    batch_size = 5
    total_batches = (len(need_query) + batch_size - 1) // batch_size
    errors = 0
    t0 = time.time()
    
    for batch_idx in range(total_batches):
        start = batch_idx * batch_size
        end = min(start + batch_size, len(need_query))
        batch = need_query[start:end]
        
        codes = [s['ts_code'] for s in batch]
        query = ' '.join(codes) + ' 公司简介 行业 年初至今涨跌幅 主营业务构成 主要产品'
        
        try:
            result = query_neodata(query, 'api')
            
            if result.get('code') == '200':
                api_data = result['data']['apiData']
                recalls = api_data.get('apiRecall', [])
                
                # 解析每个召回结果
                all_profiles = {}
                for rc in recalls:
                    content = rc.get('content', '')
                    rc_type = rc.get('type', '')
                    
                    # 公司概况 - 包含行业、上市日期、业务描述
                    if rc_type == '公司概况与所属行业信息':
                        # 按股票分拆（每只股票之间用\n\n分隔）
                        stock_sections = re.split(r'\n\n(?=[^\n]+公司（股票代码)', content)
                        for section in stock_sections:
                            # 提取股票代码
                            code_match = re.search(r'股票代码[：:]([0-9A-Z.]+)', section)
                            if code_match:
                                code = code_match.group(1)
                                info = parse_neodata_company_info(section)
                                if code not in all_profiles:
                                    all_profiles[code] = {}
                                all_profiles[code].update(info)
                    
                    # 主营构成
                    if rc_type == '主营构成与业绩趋势':
                        stock_sections = re.split(r'\n根据\d{4}(?:年报|中报)', content)
                        for section in stock_sections:
                            code_match = re.search(r'股票代码[：:]([0-9A-Z.]+)', section)
                            if code_match:
                                code = code_match.group(1)
                                biz = parse_neodata_mainbiz(section)
                                if code not in all_profiles:
                                    all_profiles[code] = {}
                                for k, v in biz.items():
                                    all_profiles[code][k] = v
                    
                    # 股票行情 - 包含YTD涨跌幅
                    if '年初至今涨跌幅' in content:
                        # 多只股票混合在一起，按代码分拆
                        # Pattern: XXX(代码:600519.SH)...年初至今涨跌幅：X.XX%
                        ytd_matches = re.finditer(
                            r'[^)]*\(代码[：:]([0-9A-Z.]+)\).*?年初至今涨跌幅[：: ]*([+-]?\d+\.?\d*)%',
                            content, re.DOTALL
                        )
                        for ym in ytd_matches:
                            code = ym.group(1)
                            ytd_val = float(ym.group(2))
                            if code not in all_profiles:
                                all_profiles[code] = {}
                            # 这是2026年YTD（因为是最新的）
                            all_profiles[code]['ytd_2026'] = ytd_val
                
                # 更新到缓存
                for code, info in all_profiles.items():
                    if code not in profiles:
                        profiles[code] = info
                    else:
                        profiles[code].update(info)
                
            time.sleep(0.3)  # Rate limiting
            
        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f'    Error batch {batch_idx}: {e}')
        
        done = min(end, len(need_query))
        if (batch_idx + 1) % 50 == 0 or batch_idx == total_batches - 1:
            print(f'    Progress: {done}/{len(need_query)}, profiles: {len(profiles)}, errors: {errors}')
            # 保存中间结果
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(profiles, f, ensure_ascii=False)
    
    print(f'    Done! {len(profiles)} profiles in {time.time()-t0:.1f}s')
    
    # 最终保存
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(profiles, f, ensure_ascii=False)
    
    return profiles

# ========== Step 4: 月度市值采样（带缓存） ==========
def fetch_kline_monthly_mv(stocks, force_refresh=False):
    """获取月度市值采样数据，带缓存"""
    cache_path = f'{CACHE_DIR}/kline_monthly_mv.json'
    
    if not force_refresh and os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            cached = json.load(f)
        covered = sum(1 for s in stocks if s['ts_code'] in cached)
        print(f'  [Kline Cache] {covered}/{len(stocks)} already have MV history')
        if covered >= len(stocks):
            return cached
    
    print(f'  [Kline Cache MISS/PARTIAL] Fetching K-line and sampling monthly MV...')
    
    mv_cache = {}
    if not force_refresh and os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            mv_cache = json.load(f)
    
    def fetch_daily_kline(qq_code):
        try:
            resp = requests.get(QQ_URL, params={
                '_var': 'k', 'param': f'{qq_code},day,,,{1300},qfq'
            }, headers=QQ_HEADERS, timeout=15)
            text = resp.text
            idx = text.index('=')
            j = json.loads(text[idx+1:])
            klines = j['data'][qq_code].get('qfqday', [])
            if not klines:
                return {'code': qq_code, 'data': None}
            daily = [(k[0], float(k[2])) for k in klines]
            return {'code': qq_code, 'data': daily}
        except:
            return {'code': qq_code, 'data': None}
    
    def sample_monthly_mv(daily_prices, current_mv, current_close):
        if not daily_prices or not current_close or current_close <= 0:
            return None
        ratio = current_mv / current_close
        by_month = {}
        for date_str, close in daily_prices:
            month_key = date_str[:7]
            if month_key not in by_month:
                by_month[month_key] = []
            by_month[month_key].append((date_str, close))
        samples = []
        for month_key in sorted(by_month.keys()):
            days = by_month[month_key]
            if len(days) < 1:
                continue
            samples.append((month_key + '-01', days[0][1]))
            if len(days) >= 10:
                samples.append((month_key + '-10', days[9][1]))
            elif len(days) >= 5:
                samples.append((month_key + '-10', days[len(days)//2][1]))
            samples.append((month_key + '-31', days[-1][1]))
        return {'dates': [s[0] for s in samples], 'mv': [round(s[1] * ratio, 2) for s in samples]}
    
    # 找出需要查询的
    need_query = [s for s in stocks if s['ts_code'] not in mv_cache]
    print(f'    Need to query: {len(need_query)} stocks')
    
    if not need_query:
        return mv_cache
    
    qq_map = {s['ts_code']: s['qq_code'] for s in need_query}
    errors = 0
    t0 = time.time()
    
    batch_size = 100
    qq_batch = list(qq_map.keys())
    qq_to_ts = {v: k for k, v in qq_map.items()}
    
    for i in range(0, len(qq_batch), batch_size):
        batch_ts = qq_batch[i:i+batch_size]
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fetch_daily_kline, qq_map[code]): code for code in batch_ts}
            for fut in concurrent.futures.as_completed(futures):
                r = fut.result()
                qq_code = r['code']
                ts_code = qq_to_ts.get(qq_code)
                if r.get('data') and ts_code:
                    stock = next((s for s in need_query if s['ts_code'] == ts_code), None)
                    if stock:
                        sampled = sample_monthly_mv(r['data'], stock['total_mv'], stock['close'])
                        if sampled:
                            mv_cache[ts_code] = sampled
                else:
                    errors += 1
        
        progress = min(i + batch_size, len(qq_batch))
        if progress % 200 == 0 or progress == len(qq_batch):
            print(f'    Progress: {progress}/{len(qq_batch)}, ok: {len(mv_cache)}, errors: {errors}')
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(mv_cache, f, ensure_ascii=False)
    
    print(f'    Done! {len(mv_cache)} with monthly MV in {time.time()-t0:.1f}s')
    
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(mv_cache, f, ensure_ascii=False)
    
    return mv_cache

# ========== Step 5: 计算2024/2025 YTD涨跌幅 ==========
def calc_ytd_from_kline(mv_history):
    """
    从月度市值采样数据中计算2024和2025的YTD涨跌幅
    YTD = (年末最后采样点市值 - 年初第一个采样点市值) / 年初第一个采样点市值 * 100
    
    但这不准确，因为我们的采样是用"当前收盘价比例"推算的。
    更好的方法：直接用收盘价比例
    """
    # 不用mv_history（因为它是用当前价推算的，不是真实市值）
    # 直接用收盘价就行
    return None

def calc_ytd_from_prices(daily_prices):
    """
    从日收盘价中计算某年的YTD涨跌幅
    """
    pass

# ========== Main ==========
def main():
    trade_date = '20260424'  # 数据截止日期
    
    print('=' * 60)
    print(f'A股 市值>200亿 数据获取 v7 — {trade_date}')
    print('=' * 60)
    
    # Step 1: 市值数据
    print('\n[Step 1/6] Market Value Data')
    stocks = fetch_mv_data(trade_date)
    
    # Step 2: 财务数据
    print('\n[Step 2/6] Finance Data (2025 Annual Report)')
    fin_data = fetch_finance_data(stocks)
    
    # Step 3: NeoData公司简介
    print('\n[Step 3/6] NeoData Profiles (Industry L2, Company Info, Business Detail)')
    profiles = fetch_neodata_profiles(stocks)
    
    # Step 4: 月度市值K线
    print('\n[Step 4/6] Monthly MV Sampling')
    mv_cache = fetch_kline_monthly_mv(stocks)
    
    # Step 5: 年度涨跌幅
    print('\n[Step 5/6] Annual % Change')
    annual_cache_path = f'{CACHE_DIR}/annual_pctchg.json'
    annual_data = {}
    if os.path.exists(annual_cache_path):
        with open(annual_cache_path, 'r', encoding='utf-8') as f:
            annual_data = json.load(f)
        print(f'  [Cache] {len(annual_data)} stocks have annual % change data')
    
    # Step 6: 合并所有数据
    print('\n[Step 6/6] Merging all data...')
    output = []
    for s in stocks:
        ts_code = s['ts_code']
        code6, _ = parse_ts_code(ts_code)
        
        fin = fin_data.get(code6, {})
        prof = profiles.get(ts_code, {})
        mv = mv_cache.get(ts_code)
        ann = annual_data.get(ts_code, {})
        
        # 确定行业：优先用二级行业，fallback到一级行业
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
            # 公司简介
            'list_date': prof.get('list_date', ''),
            'business_desc': prof.get('business_desc', ''),
            'main_biz': prof.get('main_biz', []),
            'products': prof.get('products', []),
            'regions': prof.get('regions', []),
            # YTD涨跌幅（从annual_pctchg缓存）
            'ytd_2024': ann.get('ytd_2024'),
            'ytd_2025': ann.get('ytd_2025'),
            'ytd_2026': ann.get('ytd_2026') or prof.get('ytd_2026'),
        })
    
    # 保存完整数据
    out_path = f'{DATA_DIR}/stock_data_full.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False)
    
    file_size = os.path.getsize(out_path) / (1024 * 1024)
    print(f'  Saved to {out_path} ({file_size:.2f} MB)')
    
    # 更新CSV
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
    print(f'  CSV updated: {csv_path}')
    
    # 统计
    has_fin = sum(1 for o in output if o.get('revenue'))
    has_mv = sum(1 for o in output if o.get('mv_history'))
    has_ind_l2 = sum(1 for o in output if o.get('industry_l2'))
    has_profile = sum(1 for o in output if o.get('business_desc'))
    has_products = sum(1 for o in output if o.get('products'))
    has_ytd24 = sum(1 for o in output if o.get('ytd_2024') is not None)
    has_ytd25 = sum(1 for o in output if o.get('ytd_2025') is not None)
    has_ytd26 = sum(1 for o in output if o.get('ytd_2026') is not None)
    
    print(f'\n{"=" * 60}')
    print(f'Summary:')
    print(f'  Total stocks: {len(output)}')
    print(f'  With 2025 finance: {has_fin} ({has_fin/len(output)*100:.1f}%)')
    print(f'  With MV history: {has_mv} ({has_mv/len(output)*100:.1f}%)')
    print(f'  With L2 industry: {has_ind_l2} ({has_ind_l2/len(output)*100:.1f}%)')
    print(f'  With company profile: {has_profile} ({has_profile/len(output)*100:.1f}%)')
    print(f'  With product detail: {has_products} ({has_products/len(output)*100:.1f}%)')
    print(f'  With 2024 YTD: {has_ytd24} ({has_ytd24/len(output)*100:.1f}%)')
    print(f'  With 2025 YTD: {has_ytd25} ({has_ytd25/len(output)*100:.1f}%)')
    print(f'  With 2026 YTD: {has_ytd26} ({has_ytd26/len(output)*100:.1f}%)')
    print(f'{"=" * 60}')

if __name__ == '__main__':
    main()
