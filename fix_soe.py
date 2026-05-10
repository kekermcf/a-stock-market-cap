"""Fix SOE list v4: add all国有资产 keyword variants (监督管理局/管理中心/运营中心/经营)."""

import json, os

# DATA_DIR: 项目根目录 = 脚本所在目录（macOS/Linux 兼容）
DATA_DIR = os.path.dirname(os.path.abspath(__file__))

with open(f'{DATA_DIR}/cache/controller_data.json', 'r', encoding='utf-8') as f:
    ctrl_data = json.load(f)

with open(f'{DATA_DIR}/cache/soe_list.json', 'r', encoding='utf-8') as f:
    soe_list = json.load(f)

with open(f'{DATA_DIR}/stock_data_full.json', 'r', encoding='utf-8') as f:
    all_stocks = json.load(f)

name_map = {s['ts_code']: s['name'] for s in all_stocks}

def get_all_ind(s):
    parts = []
    if s.get('industry_l1'): parts.append(s['industry_l1'])
    if s.get('industry_l2'): parts.append(s['industry_l2'])
    if s.get('industry'): parts.append(s['industry'])
    return ' '.join(parts)
ind_all = {s['ts_code']: get_all_ind(s) for s in all_stocks}

# === Known NON-SOE exceptions ===
NON_SOE_CODES = {
    # Private banks
    '000001.SZ',  # 平安银行
    '600016.SH',  # 民生银行
    '002142.SZ',  # 宁波银行
    # Private securities
    '000776.SZ',  # 广发证券
    '600109.SH',  # 国金证券
    # Private insurance
    '601318.SH',  # 中国平安
    # Private corporations
    '600887.SH',  # 伊利股份
    '000651.SZ',  # 格力电器
    '000538.SZ',  # 云南白药
    '000002.SZ',  # 万科
    '300999.SZ',  # 金龙鱼
    '300058.SZ',  # 蓝色光标
    '000009.SZ',  # 中国宝安 (private, 富安控股)
    '000893.SZ',  # 亚钾国际 (private)
    '002129.SZ',  # TCL中环 (private)
    '000100.SZ',  # TCL科技 (private)
    '301358.SZ',  # 湖南裕能 (private)
    '603175.SH',  # 超颖电子 (private)
    '688428.SH',  # 诺诚健华 (private, BIO-pharma)
    '688235.SH',  # 百济神州 (private)
    '688820.SH',  # C盛合
    '601138.SH',  # 工业富联 (Foxconn)
    '600007.SH',  # 中国国贸 (Kerry Properties, not SOE)
    '605389.SH',  # 混合持有 (个人+国资)，不算纯国企
}

# === Additional known SOEs (API has no data or no matching keywords) ===
KNOWN_SOE_EXTRA = {
    # Major securities (API empty)
    '600030.SH',  # 中信证券
    '601066.SH',  # 中信建投
    '600958.SH',  # 东方证券
    '601901.SH',  # 方正证券
    '000783.SZ',  # 长江证券
    '601696.SH',  # 中银证券
    # Insurance (API empty)
    '601601.SH',  # 中国太保
    '601336.SH',  # 新华保险
    # State-backed tech
    '688981.SH',  # 中芯国际 (SMIC - 大基金/国资背景)
    '688041.SH',  # 海光信息 (中科院背景)
    '688256.SH',  # 寒武纪 (中科院背景)
    # County-level 财政局 = local SOE
    '601899.SH',  # 紫金矿业 (上杭县财政局)
}

# === Broad SOE keyword matching ===
SOE_CTRL_KEYWORDS = [
    # 国有资产 all variants
    '国有资产监督管理委员会', '国有资产监督管理办公室',
    '国有资产监督管理局', '国有资产管理局',
    '国有资产管理中心', '国有资产运营中心', '国有资产经营',
    '国有资产投资', '国有资产管理委员会',
    '国有资产',  # catch-all for any remaining variants
    '国资委',
    # Government fiscal/finance
    '财政部', '中华人民共和国财政部', '财政局',
    # Government bodies
    '人民政府', '省政府', '市政府', '县政府', '区政府', '自治区',
    '中国投资有限责任公司', '中央汇金', '汇金投资',
    '国务院', '中共中央',
    # Social security
    '全国社会保障基金', '社保基金',
    # State capital variants
    '国有资本', '国资运营', '国资经营', '国资管理', '国资控股',
    '国有控股', '国有独资',
    # Academies
    '中国科学院', '中国社科院',
    # Cooperatives
    '供销总社', '供销合作社',
    # Tobacco
    '国家烟草', '中国烟草',
    # Production corps
    '新疆生产建设兵团',
]

def is_soe_controller(ctrl_name):
    """Check if controller name indicates SOE ownership."""
    if not ctrl_name or ctrl_name.strip() == '':
        return False
    name = ctrl_name.strip()

    # Check specific keywords first
    for kw in SOE_CTRL_KEYWORDS:
        if kw in name:
            return True

    # Broad rule: controller starts with "中国" + enterprise suffix = SOE
    # This catches: 中国中信集团, 中国华润, 中国海洋石油集团, 中国稀土集团 etc.
    if name.startswith('中国') and any(name.endswith(s) for s in [
        '集团', '集团有限公司', '集团股份公司', '总公司', '有限公司',
        '公司',
    ]):
        # Exclude comma-separated where first controller is non-SOE
        if ',' in name:
            parts = [p.strip() for p in name.split(',')]
            # Check if any part is a SOE indicator
            for part in parts:
                if part.startswith('中国') and any(part.endswith(s) for s in
                    ['集团', '集团有限公司', '总公司', '有限公司']):
                    return True
            return False
        return True

    return False

# === Process ALL stocks ===
additions = []
removals = []
already_soe = set(soe_list)

# First: remove known false positives
for fp_code in NON_SOE_CODES:
    if fp_code in soe_list:
        soe_list.remove(fp_code)
        removals.append(fp_code)

# Re-classify ALL stocks using the new rules
for code in ctrl_data:
    ctrl = ctrl_data[code]

    # Remove from NON_SOE list
    if code in NON_SOE_CODES:
        continue

    # Known SOE extra
    if code in KNOWN_SOE_EXTRA:
        if code not in soe_list:
            soe_list.append(code)
            additions.append((code, name_map.get(code, ''), 'KNOWN_SOE_EXTRA', '已知国企'))
        continue

    # Check controller-based classification
    if ctrl and ctrl.strip() != '':
        if is_soe_controller(ctrl):
            if code not in soe_list:
                soe_list.append(code)
                additions.append((code, name_map.get(code, ''), ctrl, '央企控制人'))
        continue  # has controller data, move on

    # Empty controller: apply heuristics
    name = name_map.get(code, '')
    ind_full = ind_all.get(code, '')

    is_soe = False
    reason = ''

    # RULE: All Chinese banks
    if '银行' in ind_full and name.endswith('银行'):
        is_soe = True
        reason = '银行(国控)'
    # RULE: All Chinese securities
    elif '证券' in ind_full and name.endswith('证券'):
        is_soe = True
        reason = '证券(国控)'
    # RULE: 中国 prefix + insurance
    elif '保险' in ind_full and name.startswith('中国'):
        is_soe = True
        reason = '保险(国控)'
    # RULE: 中国 prefix + strategic industry
    elif name.startswith('中国') and any(kw in ind_full for kw in
        ['铁路', '航空运输', '航天', '军工', '国防', '核', '航天']):
        is_soe = True
        reason = f'央企战略({ind_full[:20]})'

    if is_soe:
        if code not in soe_list:
            soe_list.append(code)
            additions.append((code, name, ind_full[:30], reason))

# Save
with open(f'{DATA_DIR}/cache/controller_data.json', 'w', encoding='utf-8') as f:
    json.dump(ctrl_data, f, ensure_ascii=False, indent=2)

with open(f'{DATA_DIR}/cache/soe_list.json', 'w', encoding='utf-8') as f:
    json.dump(soe_list, f, ensure_ascii=False, indent=2)

print(f'Added {len(additions)} SOE stocks:')
for code, name, info, reason in additions:
    print(f'  + {code} {name} [{info}] -> {reason}')

if removals:
    print(f'\nRemoved {len(removals)} false positives:')
    for code in removals:
        print(f'  - {code} {name_map.get(code, "?")}')

print(f'\nTotal SOE: {len(soe_list)}')
remaining = sum(1 for c in ctrl_data.values() if not c or c.strip() == '')
print(f'Still empty controller: {remaining}')
