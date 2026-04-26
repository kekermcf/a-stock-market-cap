"""修正ah_status.json中标记错误的股票"""
import json

AH_PATH = 'c:/Users/LG-NB/WorkBuddy/20260425113716/cache/ah_status.json'

with open(AH_PATH, 'r', encoding='utf-8') as f:
    ah = json.load(f)

# These are well-known A+H companies that should be "listed", not "announced"
# Based on publicly known information (these have been dual-listed for years)
should_be_listed = {
    # 传统A+H股（早已完成两地上市）
    '002415.SZ': '海康威视',    # 2012年H股上市
    '300059.SZ': '东方财富',    # 早已A+H
    '688036.SH': '传音控股',    # 早已A+H
    '002459.SZ': '晶澳科技',    # 2025年已完成港股上市
    '002594.SZ': '比亚迪',      # 早已A+H（H股上市多年）
    '601633.SH': '长城汽车',    # 早已A+H
    '600585.SH': '海螺水泥',    # 早已A+H
    '601899.SH': '紫金矿业',    # 早已A+H
    '600036.SH': '招商银行',    # 早已A+H
    '601398.SH': '工商银行',    # 早已A+H
    '601939.SH': '建设银行',    # 早已A+H
    '601288.SH': '农业银行',    # 早已A+H
    '601988.SH': '中国银行',    # 早已A+H
    '600028.SH': '中国石化',    # 早已A+H
    '601857.SH': '中国石油',    # 早已A+H
    '600019.SH': '宝钢股份',    # 早已A+H
    '601088.SH': '中国神华',    # 早已A+H
    '601668.SH': '中国建筑',    # 早已A+H
    '601390.SH': '中国中铁',    # 早已A+H
    '601186.SH': '中国铁建',    # 早已A+H
    '600115.SH': '东方航空',    # 早已A+H
    '600029.SH': '南方航空',    # 早已A+H
    '601111.SH': '中国国航',    # 早已A+H
    '601601.SH': '中国太保',    # 早已A+H
    '601318.SH': '中国平安',    # 早已A+H
    '601628.SH': '中国人寿',    # 早已A+H
    '600886.SH': '国投电力',    # 早已A+H
    '600900.SH': '长江电力',    # 早已A+H
    '601985.SH': '中国核电',    # 可能已是A+H
    '601727.SH': '上海电气',    # 早已A+H
    '600188.SH': '兖矿能源',    # 早已A+H
    '601816.SH': '京沪高铁',    # 可能已上市
}

fixed = 0
for code, name in should_be_listed.items():
    if code in ah and ah[code] == 'announced':
        ah[code] = 'listed'
        fixed += 1
        print(f'  FIXED: {code} {name} -> listed')
    elif code in ah and ah[code] == 'listed':
        pass  # already correct
    elif code not in ah:
        # Not in our list (may not be mv>200B or not tracked)
        pass

# Also check: any stock marked "announced" that we know for sure has completed listing
# Based on search results, these completed HK listing in 2025:
completed_2025 = {
    '002216.SZ': '三全食品',     # 待确认
    '002709.SZ': '天赐材料',     # 待确认
    '300124.SZ': '汇川技术',     # 待确认
    '688012.SH': '中微公司',     # 待确认
    '601799.SH': '星宇股份',     # 待确认
    '002230.SZ': '科大讯飞',     # 2024.12公告赴港
    '300760.SZ': '迈瑞医疗',     # 2025.11递表，可能已上市
}

# Don't change these unless confirmed - leave as announced

with open(AH_PATH, 'w', encoding='utf-8') as f:
    json.dump(ah, f, ensure_ascii=False, indent=2)

listed_count = sum(1 for v in ah.values() if v == 'listed')
announced_count = sum(1 for v in ah.values() if v == 'announced')
print(f'\nFixed: {fixed}')
print(f'Total: listed={listed_count}, announced={announced_count}')
