"""Fetch actual controller (实际控制人) for all stocks from East Money,
then classify as SOE based on controller name keywords."""

import json, time, os, sys
import requests

# DATA_DIR: 项目根目录 = 脚本所在目录（macOS/Linux 兼容）
DATA_DIR = os.path.dirname(os.path.abspath(__file__))

# Load stock codes (>=100B only)
with open(f'{DATA_DIR}/stock_data_full.json', 'r', encoding='utf-8') as f:
    stocks = json.load(f)
codes = [s['ts_code'] for s in stocks if s.get('total_mv', 0) >= 100]
print(f'Total codes to fetch: {len(codes)}', flush=True)

# SOE keywords in controller name
SOE_KEYWORDS = [
    '国资委', '国有资产监督管理委员会', '国有资产管理局',
    '财政部', '中华人民共和国财政部',
    '人民政府', '省政府', '市政府', '县政府', '区政府', '自治区',
    '中国投资有限责任公司', '中央汇金', '汇金投资',
    '国务院', '中共中央',
    '全国社会保障基金', '社保基金',
    '国有资本', '国资运营', '国资经营', '国资管理', '国资控股',
    '国有控股', '国有独资',
    '中国铁路',
    '中国石油', '中国石化', '中国海油',
    '国家电网', '南方电网',
    '中国建筑', '中国中铁', '中国铁建', '中国交建',
    '中国中车', '中国船舶', '中国航发', '中国兵', '中国电科',
    '中国核工业', '中国航天', '中国航空', '中国商用飞机',
    '中国移动', '中国联通', '中国电信',
    '中国宝武', '中国铝业', '中国五矿',
    '中国化工', '中化集团',
    '国家能源', '中国华能', '中国大唐', '中国华电', '国家电投',
    '中国三峡', '中国广核',
    '中国远洋', '中远海运',
    '中国医药', '国药集团',
    '中国建材',
    '中国电子', '中国电科',
    '中国国新', '中国诚通',
    '中国科学院', '中国社科院',
    '供销总社', '供销合作社',
    '中国信达', '中国华融', '中国长城', '中国东方',
]

NON_SOE_KEYWORDS = ['香港', '澳门']

def fetch_controller(ts_code):
    parts = ts_code.split('.')
    em_code = parts[1][:2].upper() + parts[0]
    url = f'https://emweb.securities.eastmoney.com/PC_HSF10/ShareholderResearch/PageAjax?code={em_code}'
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        sjkzr = data.get('sjkzr', [])
        if sjkzr and len(sjkzr) > 0:
            holder = sjkzr[0].get('HOLDER_NAME', '') or ''
            return holder
        return ''
    except Exception as e:
        return ''

def is_soe(controller_name):
    if not controller_name or controller_name == 'None':
        return False
    name = str(controller_name)
    for kw in NON_SOE_KEYWORDS:
        if kw in name:
            return False
    for kw in SOE_KEYWORDS:
        if kw in name:
            return True
    return False

# Check for cached progress
cache_path = f'{DATA_DIR}/cache/controller_data.json'
controller_data = {}
if os.path.exists(cache_path):
    with open(cache_path, 'r', encoding='utf-8') as f:
        controller_data = json.load(f)
    print(f'Loaded {len(controller_data)} cached controllers', flush=True)

done = len(controller_data)
errors = 0
start = time.time()

for ts_code in codes:
    if ts_code in controller_data:
        continue
    controller = fetch_controller(ts_code)
    if controller:
        controller_data[ts_code] = controller
    else:
        controller_data[ts_code] = ''
        errors += 1
    done += 1
    if done % 50 == 0:
        elapsed = time.time() - start
        rate = done / elapsed if elapsed > 0 else 0
        print(f'  {done}/{len(codes)} ({rate:.1f}/s), errors: {errors}', flush=True)
    # Save progress every 200
    if done % 200 == 0:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(controller_data, f, ensure_ascii=False)
    time.sleep(0.05)

# Final save
with open(cache_path, 'w', encoding='utf-8') as f:
    json.dump(controller_data, f, ensure_ascii=False)

# Classify SOE
soe_list = []
for ts_code, controller in controller_data.items():
    if is_soe(controller):
        soe_list.append(ts_code)

soe_path = f'{DATA_DIR}/cache/soe_list.json'
with open(soe_path, 'w', encoding='utf-8') as f:
    json.dump(soe_list, f, ensure_ascii=False, indent=2)

print(f'\nDone! {len(controller_data)} controllers, {errors} errors', flush=True)
print(f'SOE stocks: {len(soe_list)}', flush=True)

# Print some SOE examples
for ts_code in soe_list[:15]:
    print(f'  {ts_code}: {controller_data.get(ts_code, "")}', flush=True)
