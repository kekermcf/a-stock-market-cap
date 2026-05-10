"""Fix SOE list v2: properly check both industry_l1 and industry_l2 fields,
fix false positives (中国宝安), add missing securities & insurers."""

import json

DATA_DIR = 'c:/Users/LG-NB/WorkBuddy/20260425113716'

with open(f'{DATA_DIR}/cache/controller_data.json', 'r', encoding='utf-8') as f:
    ctrl_data = json.load(f)

with open(f'{DATA_DIR}/cache/soe_list.json', 'r', encoding='utf-8') as f:
    soe_list = json.load(f)

with open(f'{DATA_DIR}/stock_data_full.json', 'r', encoding='utf-8') as f:
    all_stocks = json.load(f)

name_map = {s['ts_code']: s['name'] for s in all_stocks}
# Get ALL industry text (l1 + l2) for keyword matching
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
}

# === Additional known SOEs (that East Money has no data for) ===
KNOWN_SOE_EXTRA = {
    # Major securities
    '600030.SH',  # 中信证券
    '601066.SH',  # 中信建投
    '600958.SH',  # 东方证券
    '601901.SH',  # 方正证券
    '000783.SZ',  # 长江证券
    '601696.SH',  # 中银证券
    # Insurance
    '601601.SH',  # 中国太保
    '601336.SH',  # 新华保险
    # 中国 prefix + strategic
    '601138.SH',  # 工业富联 - NOT SOE (Foxconn), skip
}

# Remove 工业富联 from consideration
if '601138.SH' in KNOWN_SOE_EXTRA:
    KNOWN_SOE_EXTRA.remove('601138.SH')

# === Heuristic rules ===
additions = []
removals = []

# First: remove known false positives from SOE list
for fp_code in ['000009.SZ']:  # 中国宝安
    if fp_code in soe_list:
        soe_list.remove(fp_code)
        removals.append(fp_code)
        if fp_code in ctrl_data:
            ctrl_data[fp_code] = ''  # Reset

for code, ctrl in ctrl_data.items():
    if ctrl and ctrl != '' and code not in removals:
        continue  # already has good controller data
    name = name_map.get(code, '')
    ind_full = ind_all.get(code, '')
    
    if code in NON_SOE_CODES:
        # Ensure it's removed from SOE list
        if code in soe_list:
            soe_list.remove(code)
            removals.append(code)
        continue
    
    is_soe = False
    reason = ''
    
    # RULE 1: All Chinese banks (industry contains 银行)
    if '银行' in ind_full and name.endswith('银行'):
        is_soe = True
        reason = '银行(国控)'
    
    # RULE 2: All Chinese securities (industry contains 证券)
    elif '证券' in ind_full and name.endswith('证券'):
        is_soe = True
        reason = '证券(国控)'
    
    # RULE 3: 中国 prefix + 保险 in name
    elif '保险' in ind_full and name.startswith('中国'):
        is_soe = True
        reason = '保险(国控)'
    
    # RULE 4: Known major SOEs
    elif code in KNOWN_SOE_EXTRA:
        is_soe = True
        reason = '已知国企'
    
    # RULE 5: "中国" prefix + truly strategic industry  
    elif name.startswith('中国') and any(kw in ind_full for kw in ['铁路', '航空运输', '航天', '军工', '国防']):
        is_soe = True
        reason = f'央企({ind_full[:20]})'
    
    if is_soe:
        ctrl_data[code] = f'{reason}'
        additions.append((code, name, ind_full[:30], reason))
        if code not in soe_list:
            soe_list.append(code)

# Save
with open(f'{DATA_DIR}/cache/controller_data.json', 'w', encoding='utf-8') as f:
    json.dump(ctrl_data, f, ensure_ascii=False, indent=2)

with open(f'{DATA_DIR}/cache/soe_list.json', 'w', encoding='utf-8') as f:
    json.dump(soe_list, f, ensure_ascii=False, indent=2)

print(f'Added {len(additions)} SOE stocks:')
for code, name, ind, reason in additions:
    print(f'  + {code} {name} ({ind}) -> {reason}')

if removals:
    print(f'\nRemoved {len(removals)} false positives:')
    for code in removals:
        print(f'  - {code} {name_map.get(code, "?")}')

prev_soe = len(soe_list) - len(additions) + len(removals)
print(f'\nTotal SOE: {len(soe_list)} (was {prev_soe})')
remaining = sum(1 for c in ctrl_data.values() if not c or c == '')
print(f'Still empty controller: {remaining}')
