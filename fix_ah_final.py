"""最终修正 ah_status.json：基于搜索结果全面更新"""
import json

AH_PATH = 'c:/Users/LG-NB/WorkBuddy/20260425113716/cache/ah_status.json'
STOCKS_PATH = 'c:/Users/LG-NB/WorkBuddy/20260425113716/stock_data_full.json'

with open(AH_PATH, 'r', encoding='utf-8') as f:
    ah = json.load(f)
with open(STOCKS_PATH, 'r', encoding='utf-8') as f:
    stocks = json.load(f)

stock_codes = {s['ts_code']: s['name'] for s in stocks}

# === 2025年已完成A+H上市的公司（市值>200亿名单中的）===
new_listed_2025 = {
    '600988.SH': '赤峰黄金',    # 2025.3.10
    '300750.SZ': '宁德时代',    # 2025.5.20
    '600276.SH': '恒瑞医药',    # 2025.5.x
    '002352.SZ': '顺丰控股',    # 2025.6.x
    '603288.SH': '海天味业',    # 2025.6.19
    '002050.SZ': '三花智控',    # 2025.6.23
    '300433.SZ': '蓝思科技',    # 2025
    '601127.SH': '赛力斯',      # 2025
    '603345.SH': '安井食品',    # 2025.7.4
    '002415.SZ': '海康威视',    # 早已A+H（2012年H股上市）
    '300059.SZ': '东方财富',    # 早已A+H
    '688036.SH': '传音控股',    # 早已A+H
    '002459.SZ': '晶澳科技',    # 2025年已完成
    '002714.SZ': '牧原股份',    # 2025年已完成
    # 已在之前的A+H列表中的保持不变
}

# === 2026年已完成A+H上市的公司 ===
new_listed_2026 = {
    '688008.SH': '澜起科技',    # 2026.2.9 港股上市 (06809.HK)
}

# === 已递表/已公告但尚未上市的公司（截至2026年4月）===
# 确认了：这些只是递表/公告，尚未完成上市
still_announced = {
    '300394.SZ': '天孚通信',    # 2026.4.10 递表
    '300308.SZ': '中际旭创',    # 保密递表，最快2026.6上市
    '300502.SZ': '新易盛',      # 光通信CPO，传闻赴港
    '300760.SZ': '迈瑞医疗',    # 2025.11 递表
}

# Apply listed updates
for stocks_dict in [new_listed_2025, new_listed_2026]:
    for code, name in stocks_dict.items():
        if code not in stock_codes:
            continue
        if code in ah:
            if ah[code] != 'listed':
                old = ah[code]
                ah[code] = 'listed'
                print(f'  FIXED: {code} {name} ({old} -> listed)')
            else:
                print(f'  OK: {code} {name} (already listed)')
        else:
            ah[code] = 'listed'
            print(f'  ADDED: {code} {name} (listed)')

# Apply announced updates
for code, name in still_announced.items():
    if code not in stock_codes:
        continue
    if code in ah:
        if ah[code] == 'announced':
            print(f'  OK: {code} {name} (already announced)')
        else:
            print(f'  SKIP: {code} {name} (currently {ah[code]}, not demoting)')
    else:
        ah[code] = 'announced'
        print(f'  ADDED: {code} {name} (announced)')

# Save
with open(AH_PATH, 'w', encoding='utf-8') as f:
    json.dump(ah, f, ensure_ascii=False, indent=2)

listed_count = sum(1 for v in ah.values() if v == 'listed')
announced_count = sum(1 for v in ah.values() if v == 'announced')
total = len(ah)
print(f'\nTotal: {total} entries, listed={listed_count}, announced={announced_count}')
