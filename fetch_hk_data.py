#!/usr/bin/env python3
"""
港股数据获取脚本
================
通过 AKShare 获取全部港股实时数据，筛选港币市值 >= 250 亿的公司。
通过 QQ K-line API 计算 2024/2025/2026 年初至今涨跌幅。

数据源（优先级）：
1. AKShare stock_hk_spot_em() — 东方财富（国内网络优先，含市值/PE/PB）
2. AKShare stock_hk_spot() + 腾讯 qt.gtimg.cn — 新浪获取列表 + 腾讯批量获取行情市值（海外 fallback）

YTD 涨跌幅：
- QQ Finance K-line (hkXXXXX): 历史 K 线

缓存：
- cache/hk_data_{date}.json — 按日期的港股数据缓存
- cache/hk_annual_pctchg.json — 年度涨跌幅缓存
"""
import json, requests, time, concurrent.futures, os, sys
from datetime import datetime

# DATA_DIR: 项目根目录 = 脚本所在目录
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(DATA_DIR, 'cache')
os.makedirs(CACHE_DIR, exist_ok=True)

QQ_QUOTE_URL = 'https://qt.gtimg.cn/q='
QQ_KLINE_URL = 'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get'
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# 市值门槛：250 亿港币
MV_THRESHOLD = 250

# 腾讯 quote 字段映射（v_hkXXXXX="..."）
# 索引: 0=type, 1=名称, 2=代码, 3=最新价, 4=昨收, 5=开盘, 6=成交量,
#       31=涨跌额, 32=涨跌幅%, 33=最高, 34=最低, 35=收盘, 37=成交额,
#       39=PE, 43=PB, 44=H股市值(亿港币), 45=总市值(亿港币),
#       47=每股净资产?, 48=52周高, 49=52周低, 51=股息率%
QQ_F_NAME = 1
QQ_F_CODE = 2
QQ_F_PRICE = 3
QQ_F_CHG = 31
QQ_F_PCTCHG = 32
QQ_F_HIGH = 33
QQ_F_LOW = 34
QQ_F_PE = 39
QQ_F_PB = 43
QQ_F_MV_H = 44    # H股流通市值
QQ_F_MV_TOTAL = 45  # 总市值（含A+H全部股份）


def _num(v, default=0):
    """安全转数字"""
    if v is None or v == '' or v == '-' or v == 'None':
        return default
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


def fetch_hk_spot_em():
    """方式1：AKShare 东方财富（国内网络优先，含市值/PE/PB）"""
    try:
        import akshare as ak
        print('  尝试 AKShare 东方财富数据源...')
        df = ak.stock_hk_spot_em()
        print(f'  东方财富返回 {len(df)} 只港股')
        return df
    except ImportError:
        print('  ERROR: akshare not installed. Run: pip install akshare')
        return None
    except Exception as e:
        print(f'  东方财富不可用: {e}')
        return None


def fetch_hk_spot_sina():
    """方式2：AKShare 新浪获取全量港股列表"""
    try:
        import akshare as ak
        print('  尝试 AKShare 新浪数据源...')
        df = ak.stock_hk_spot()
        print(f'  新浪返回 {len(df)} 只港股')
        return df
    except Exception as e:
        print(f'  新浪不可用: {e}')
        return None


def fetch_qq_batch(codes):
    """通过腾讯接口批量获取港股行情（含市值/PE/PB）
    每次最多约50只，逗号分隔
    """
    BATCH = 50
    all_stocks = []

    for i in range(0, len(codes), BATCH):
        batch = codes[i:i+BATCH]
        qq_codes = ','.join(f'hk{c}' for c in batch)
        try:
            r = requests.get(f'{QQ_QUOTE_URL}{qq_codes}', headers=UA, timeout=15)
            for line in r.text.strip().split(';'):
                line = line.strip()
                if not line or '=' not in line:
                    continue
                idx = line.index('=')
                data = line[idx+1:].strip('"').split('~')
                if len(data) < 50:
                    continue

                code = str(data[QQ_F_CODE]).strip().zfill(5)
                name = data[QQ_F_NAME]
                # Use max(H股市值, 总市值) for total market cap
                mv_h = _num(data[QQ_F_MV_H])
                mv_total = _num(data[QQ_F_MV_TOTAL])
                total_mv = max(mv_h, mv_total)
                # Skip 5-digit codes starting with 8 (RMB counter: -R/-WR)
                if len(code) == 5 and code.startswith('8'):
                    continue
                close = _num(data[QQ_F_PRICE])
                pct_chg = _num(data[QQ_F_PCTCHG])
                pe = data[QQ_F_PE] if data[QQ_F_PE] else ''
                pb = data[QQ_F_PB] if data[QQ_F_PB] else ''

                all_stocks.append({
                    'code': code,
                    'qq_code': f'hk{code}',
                    'name': name,
                    'close': close,
                    'pct_chg': pct_chg,
                    'pe': pe,
                    'pb': pb,
                    'total_mv': round(total_mv, 2),
                    'industry': '',
                    'ytd_2024': None, 'ytd_2025': None, 'ytd_2026': None,
                    'revenue': None, 'gross_profit': None, 'net_profit': None,
                    'gpr': None, 'npm': None, 'mv_history': None,
                })
        except Exception as e:
            print(f'  腾讯批量请求错误: {e}')

        if i + BATCH < len(codes):
            time.sleep(0.5)

    return all_stocks


def parse_hk_df_em(df):
    """解析东方财富 DataFrame"""
    if df is None or df.empty:
        return []

    col_map = {}
    for col in df.columns:
        cl = col.lower()
        if '代码' in col or 'code' in cl:
            col_map[col] = 'code'
        elif '名称' in col or 'name' in cl:
            col_map[col] = 'name'
        elif '总市值' in col:
            col_map[col] = 'total_mv'
        elif '最新价' in col or '收盘' in col:
            col_map[col] = 'close'
        elif '涨跌幅' in col:
            col_map[col] = 'pct_chg'
        elif '市盈率' in col:
            col_map[col] = 'pe'
        elif '市净率' in col:
            col_map[col] = 'pb'

    if 'total_mv' not in col_map.values():
        for col in df.columns:
            if '市值' in col:
                col_map[col] = 'total_mv'
                break

    df = df.rename(columns=col_map)
    stocks = []
    for _, row in df.iterrows():
        code = str(row.get('code', '')).strip().zfill(5)
        name = str(row.get('name', '')).strip()
        raw_mv = _num(row.get('total_mv'))
        total_mv = raw_mv / 1e8 if raw_mv > 1e6 else raw_mv

        if total_mv >= MV_THRESHOLD:
            pe_val = row.get('pe', '')
            pb_val = row.get('pb', '')
            stocks.append({
                'code': code,
                'qq_code': f'hk{code}',
                'name': name,
                'close': _num(row.get('close')),
                'pct_chg': _num(row.get('pct_chg')),
                'pe': pe_val if pe_val and str(pe_val) != '-' else '',
                'pb': pb_val if pb_val and str(pb_val) != '-' else '',
                'total_mv': round(total_mv, 2),
                'industry': '',
                'ytd_2024': None, 'ytd_2025': None, 'ytd_2026': None,
                'revenue': None, 'gross_profit': None, 'net_profit': None,
                'gpr': None, 'npm': None, 'mv_history': None,
            })

    stocks.sort(key=lambda x: x['total_mv'], reverse=True)
    return stocks


def fetch_kline_hk(qq_code, end_date='2026-12-31'):
    """获取港股 K 线数据（用于计算 YTD 涨跌幅）
    必须提供 start+end 日期，返回字段为 'day'（非 'qfqday'）
    """
    try:
        resp = requests.get(QQ_KLINE_URL, params={
            '_var': 'k', 'param': f'{qq_code},day,2024-01-02,{end_date},1000,qfq'
        }, headers=UA, timeout=15)
        text = resp.text
        idx = text.index('=')
        j = json.loads(text[idx+1:])
        data = j.get('data', {}).get(qq_code, {})
        klines = data.get('day', []) or data.get('qfqday', [])
        return [(k[0], float(k[2])) for k in klines] if klines else None
    except:
        return None


def calc_ytd(klines, start_date, end_date):
    """计算年初至今涨跌幅"""
    if not klines:
        return None
    start_close = end_close = None
    for date_str, close in klines:
        if date_str >= start_date and start_close is None:
            start_close = close
        if date_str <= end_date:
            end_close = close
    if start_close and end_close and start_close > 0:
        return round((end_close - start_close) / start_close * 100, 2)
    return None


def calc_ytd_for_stocks(stocks, trade_date):
    """为所有港股计算 YTD 涨跌幅"""
    end_date = f'{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:8]}'

    # 加载缓存
    annual_cache_path = os.path.join(CACHE_DIR, 'hk_annual_pctchg.json')
    annual_data = {}
    if os.path.exists(annual_cache_path):
        with open(annual_cache_path, 'r', encoding='utf-8') as f:
            annual_data = json.load(f)

    results = dict(annual_data)
    errors = 0
    batch_size = 50

    for i in range(0, len(stocks), batch_size):
        batch = stocks[i:i+batch_size]
        print(f'  YTD batch {i//batch_size + 1}/{(len(stocks)-1)//batch_size + 1} ({len(batch)} stocks)...')

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fetch_kline_hk, s['qq_code'], end_date): s['code'] for s in batch}
            for fut in concurrent.futures.as_completed(futures):
                code = futures[fut]
                klines = fut.result()
                if klines:
                    y24 = calc_ytd(klines, '2024-01-02', end_date)
                    y25 = calc_ytd(klines, '2025-01-02', end_date)
                    y26 = calc_ytd(klines, f'{end_date[:4]}-01-02', end_date)
                    results[code] = {
                        'ytd_2024': y24,
                        'ytd_2025': y25,
                        'ytd_2026': y26,
                    }
                else:
                    errors += 1

    # 保存缓存
    with open(annual_cache_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False)

    print(f'  YTD: {len(results)} stocks calculated, {errors} errors')
    return results


def load_ah_status():
    """从 ah_status.json 加载 A+H 双上市状态，并构建 HK代码→状态 的映射"""
    ah_path = os.path.join(CACHE_DIR, 'ah_status.json')
    ah_status_a = {}
    if os.path.exists(ah_path):
        with open(ah_path, 'r', encoding='utf-8') as f:
            ah_status_a = json.load(f)

    # 从 ashare.html 提取 A股ts_code 和 ahStatus
    ashare_path = os.path.join(DATA_DIR, 'ashare.html')
    ah_status_from_html = {}
    if os.path.exists(ashare_path):
        with open(ashare_path, 'r', encoding='utf-8') as f:
            content = f.read()
        import re
        m = re.search(r'var ahStatus = (\{[^;]+\});', content)
        if m:
            ah_status_from_html = json.loads(m.group(1))

    if ah_status_from_html:
        ah_status_a = ah_status_from_html

    # Build A股代码 → HK代码 mapping using Tencent API
    # A股代码格式: 000001.SZ, 600036.SH
    # HK代码格式: 00700, 02318
    # We can query Tencent with the HK code to get the name,
    # then match with A-share names to find the mapping
    # But for efficiency, let's build a reverse mapping from known A+H stocks

    # Common A+H code mapping (A-share ts_code → HK code)
    # This is a well-known list - we'll try to match by querying names
    a_to_hk = {}
    a_codes = [k for k, v in ah_status_a.items() if v in ('listed', 'announced')]

    if a_codes:
        print(f'  Building A→HK mapping for {len(a_codes)} stocks...')
    # Query HK stocks by name matching
    # First, get A-stock names from ashare.html data
    a_names = {}
    if os.path.exists(ashare_path):
        with open(ashare_path, 'r', encoding='utf-8') as f:
            content = f.read()
        # Parse the JSON array properly (names are \uXXXX encoded)
        a_data_start = content.find('var allData = [')
        if a_data_start >= 0:
            a_data_start += len('var allData = ')
            depth = 0
            for ci in range(a_data_start, len(content)):
                if content[ci] == '[': depth += 1
                elif content[ci] == ']': depth -= 1
                if depth == 0:
                    a_data = json.loads(content[a_data_start:ci+1])
                    a_names = {s['ts_code']: s['name'] for s in a_data}
                    break

        # Query Tencent batch for all HK stocks to get HK code → name mapping
        try:
            # Get the full HK stock list
            import akshare as ak
            df = ak.stock_hk_spot()
            if df is not None and not df.empty:
                # Build HK name → code map
                hk_name_map = {}
                for _, row in df.iterrows():
                    hk_code = str(row.get('代码', '')).strip().zfill(5)
                    hk_name = str(row.get('中文名称', '')).strip()
                    if hk_code and hk_name:
                        hk_name_map[hk_name] = hk_code
                # Match A-stock name with HK name (exact or with suffix stripped)
                for ts_code in a_codes:
                    a_name = a_names.get(ts_code, '')
                    if not a_name:
                        continue
                    # Try exact match first
                    if a_name in hk_name_map and ts_code not in a_to_hk:
                        a_to_hk[ts_code] = hk_name_map[a_name]
                    else:
                        # Try stripping common suffixes
                        base_name = a_name.rstrip('-WH').rstrip('-W').rstrip('-R')
                        if base_name in hk_name_map and ts_code not in a_to_hk:
                            a_to_hk[ts_code] = hk_name_map[base_name]
        except Exception as e:
            print(f'  Warning: Could not build name mapping: {e}')

    # Build HK代码 → A+H状态
    hk_to_ah = {}
    for ts_code, status in ah_status_a.items():
        hk_code = a_to_hk.get(ts_code)
        if hk_code:
            hk_to_ah[hk_code] = status

    print(f'  A→HK mapping: {len(a_to_hk)} stocks, HK→AH status: {len(hk_to_ah)} entries')
    return hk_to_ah


def main():
    print('=' * 60)
    print('港股数据获取 — 市值 >= 250 亿港币')
    print('=' * 60)

    # 获取交易日
    from datetime import timedelta
    d = datetime.now()
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    trade_date = d.strftime('%Y%m%d')

    # 尝试从现有缓存推断日期
    import glob
    mv_files = sorted(glob.glob(os.path.join(CACHE_DIR, 'hk_data_*.json')))
    if mv_files:
        latest_date = os.path.basename(mv_files[-1]).replace('hk_data_', '').replace('.json', '')
        if latest_date <= trade_date:
            trade_date = latest_date
    print(f'Trade date: {trade_date}')

    # Step 1: Fetch data
    print('\n[1/3] Fetching HK stock data...')
    stocks = []

    # 方式1: 东方财富（国内网络优先）
    df = fetch_hk_spot_em()
    if df is not None:
        stocks = parse_hk_df_em(df)
        if stocks:
            print(f'  东方财富: {len(stocks)} 只市值 >= {MV_THRESHOLD} 亿')

    # 方式2: 新浪列表 + 腾讯批量获取行情（海外 fallback）
    if not stocks:
        df_sina = fetch_hk_spot_sina()
        if df_sina is not None:
            all_codes = [str(c).strip().zfill(5) for c in df_sina['代码']]
            print(f'  通过腾讯批量获取 {len(all_codes)} 只港股行情...')
            all_stocks = fetch_qq_batch(all_codes)
            stocks = [s for s in all_stocks if s['total_mv'] >= MV_THRESHOLD]
            stocks.sort(key=lambda x: x['total_mv'], reverse=True)
            print(f'  腾讯: {len(all_stocks)} 只, 市值 >= {MV_THRESHOLD} 亿: {len(stocks)} 只')

    if not stocks:
        print('Failed to fetch data from all sources. Exiting.')
        return

    # 加载 A+H 双上市状态
    print('\n[AH] Loading A+H dual-listing status...')
    hk_ah_status = load_ah_status()
    for s in stocks:
        s['ah_status'] = hk_ah_status.get(s['code'], '')
    ah_listed = sum(1 for s in stocks if s['ah_status'] == 'listed')
    ah_announced = sum(1 for s in stocks if s['ah_status'] == 'announced')
    print(f'  A+H listed: {ah_listed}, announced: {ah_announced}')

    # 过滤 -T 股票和已由8开头过滤的
    stocks = [s for s in stocks if not s['name'].endswith('-T')]
    print(f'\n[2/3] Parsing and filtering...')
    print(f'  {len(stocks)} stocks with MV >= {MV_THRESHOLD}B HKD')

    # 保存基础数据
    cache_path = os.path.join(CACHE_DIR, f'hk_data_{trade_date}.json')
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(stocks, f, ensure_ascii=False)
    print(f'  Saved to {cache_path}')

    # Step 2: Calculate YTD
    print('\n[3/3] Calculating YTD...')
    annual_data = calc_ytd_for_stocks(stocks, trade_date)

    # Merge YTD into stock data
    for s in stocks:
        code = s['code']
        ann = annual_data.get(code, {})
        s['ytd_2024'] = ann.get('ytd_2024')
        s['ytd_2025'] = ann.get('ytd_2025')
        s['ytd_2026'] = ann.get('ytd_2026')

    # Save final merged data
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(stocks, f, ensure_ascii=False)

    print(f'\nDone! {len(stocks)} HK stocks ready')
    return stocks


if __name__ == '__main__':
    main()
