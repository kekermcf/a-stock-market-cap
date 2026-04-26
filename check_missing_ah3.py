"""Known A+H stocks that completed listing recently, manually verified from web search.
Add them all at once to ah_status.json"""

import json

with open('c:/Users/LG-NB/WorkBuddy/20260425113716/cache/ah_status.json', 'r', encoding='utf-8') as f:
    ah = json.load(f)

# All A+H stocks that completed Hong Kong listing, verified from web searches
# Format: ts_code -> 'listed'
new_listed = {
    # 2025 completions
    '601127.SH': 'listed',  # 赛力斯 2025.11.5 H股上市
    '600276.SH': 'listed',  # 恒瑞医药 2025.5.23 H股上市
    '300750.SZ': 'listed',  # 宁德时代 2025.5.20 H股上市
    '000333.SZ': 'listed',  # 美的集团 2024.9.17 H股上市
    '002352.SZ': 'listed',  # 顺丰控股 2024.11.19 H股上市
    '603288.SH': 'listed',  # 海天味业 2025.6.19 H股上市
    '600570.SH': 'listed',  # 恒生电子 check
    '603501.SH': 'listed',  # 韦尔股份 check
    
    # 2025-2026 newly completed A+H listings (from news searches)
    '300124.SZ': 'listed',  # 汇川技术 
    '601766.SH': 'listed',  # 中国中车 (old A+H)
    '600036.SH': 'listed',  # 招商银行 (old A+H)
    '601318.SH': 'listed',  # 中国平安 (old A+H)
    '601398.SH': 'listed',  # 工商银行 (old A+H)
    '600028.SH': 'listed',  # 中国石化 (old A+H)
    '601857.SH': 'listed',  # 中国石油 (already have)
}

# Actually let me be more targeted - only add stocks I've verified through web search
# as recently completing A+H that are missing from our list
verified_new_listed = {
    '603296.SH': 'listed',  # 华勤技术 2026.4.23 H股上市 03296.HK
    '601127.SH': 'listed',  # 赛力斯 2025.11.5 H股上市
}

# Check which are already in ah_status
for code, name_str in [('603296.SH', '华勤技术'), ('601127.SH', '赛力斯')]:
    current = ah.get(code, 'NOT_FOUND')
    print(f'{code} {name_str}: {current}')

# Add them
for code, status in verified_new_listed.items():
    ah[code] = status

listed = sum(1 for v in ah.values() if v == 'listed')
announced = sum(1 for v in ah.values() if v == 'announced')
rumor = sum(1 for v in ah.values() if v == 'rumor')
print(f'\nAfter update: listed={listed}, announced={announced}, rumor={rumor}, total={listed+announced+rumor}')

with open('c:/Users/LG-NB/WorkBuddy/20260425113716/cache/ah_status.json', 'w', encoding='utf-8') as f:
    json.dump(ah, f, ensure_ascii=False, indent=2)
print('Saved!')
