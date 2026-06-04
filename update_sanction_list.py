"""
补全制裁清单 (sanction_list.json + stock_data_full.json)
数据源: 公开 BIS Entity List / 财政部 NS-CMIC / 国防部 CMC 公告
"""
import json

# ========== 1. 完整制裁清单 (ts_code → [标签列表]) ==========
NEW_SANCTIONS = {
    # ========== BIS Entity List ==========
    # 2019-10 第一批 (海康、大华、讯飞、美亚柏科等)
    '002415.SZ': ['Entity List'],   # 海康威视
    '002236.SZ': ['Entity List'],   # 大华股份
    '002230.SZ': ['Entity List'],   # 科大讯飞
    '300188.SZ': ['Entity List'],   # 美亚柏科
    # 旷视科技、商汤科技、依图科技 → 非 A 股 (港股/未上市)，不在此列

    # 2019-06 超算相关
    '603019.SH': ['Entity List'],   # 中科曙光

    # 2020-2021 增补
    '300474.SZ': ['Entity List'],   # 景嘉微
    '688256.SH': ['Entity List'],   # 寒武纪
    '688047.SH': ['Entity List'],   # 龙芯中科
    '000977.SZ': ['Entity List'],   # 浪潮信息
    '688981.SH': ['Entity List'],   # 中芯国际

    # 2023-10 半导体设备/EDA
    '002371.SZ': ['Entity List'],   # 北方华创
    '688072.SH': ['Entity List'],   # 拓荆科技
    '301269.SZ': ['Entity List'],   # 华大九天
    '600745.SH': ['Entity List'],   # 闻泰科技
    '688361.SH': ['Entity List'],   # 中科飞测
    '688037.SH': ['Entity List'],   # 芯源微
    '688120.SH': ['Entity List'],   # 华海清科
    '688012.SH': ['Entity List'],   # 中微公司
    '300457.SZ': ['Entity List'],   # 中芯国际 (深圳, 已覆盖 688981 为上海)

    # 2024-12 新一轮 (136 家, 筛选 A 股)
    '600460.SH': ['Entity List'],   # 士兰微
    '688008.SH': ['Entity List'],   # 澜起科技
    '688099.SH': ['Entity List'],   # 晶晨股份
    '688126.SH': ['Entity List'],   # 汇顶科技
    '688187.SH': ['Entity List'],   # 时代电气
    '688249.SH': ['Entity List'],   # 晶合集成
    '688362.SH': ['Entity List'],   # 甬矽电子
    '688403.SH': ['Entity List'],   # 汇成股份
    '688469.SH': ['Entity List'],   # 中芯集成
    '688521.SH': ['Entity List'],   # 芯原股份

    # 2025-09 新增 23 家中国实体 (Federal Register 2025-17893)
    # 复旦微电子系列
    '600898.SH': ['Entity List'],   # 上海复旦 (复旦微电子 A 股)
    # 生工生物
    # 索辰信息
    '688507.SH': ['Entity List'],   # 索辰信息 (Shanghai Suochen)
    # 吉姆西半导体
    # 积存半导体

    # ========== 财政部 NS-CMIC List (禁止美国人证券交易) ==========
    '600893.SH': ['NS-CMIC', 'Entity List'],   # 航发动力
    '000738.SZ': ['NS-CMIC', 'Entity List'],   # 航发控制
    '000547.SZ': ['NS-CMIC', 'Entity List'],   # 航天发展
    '600879.SH': ['NS-CMIC', 'Entity List'],   # 航天电子
    '600862.SH': ['NS-CMIC', 'Entity List'],   # 中航高科
    '002179.SZ': ['NS-CMIC', 'Entity List'],   # 中航光电
    '600760.SH': ['NS-CMIC', 'Entity List'],   # 中航沈飞
    '600765.SH': ['NS-CMIC', 'Entity List'],   # 中航重机
    '003816.SZ': ['NS-CMIC', 'Entity List'],   # 中国广核
    '600498.SH': ['NS-CMIC', 'Entity List'],   # 烽火通信
    '600050.SH': ['NS-CMIC'],               # 中国电信
    '600938.SH': ['NS-CMIC'],               # 中国海油
    '601728.SH': ['NS-CMIC'],               # 中国联通
    '601808.SH': ['NS-CMIC'],               # 中海油服
    '601800.SH': ['NS-CMIC'],               # 中国交建
    '601390.SH': ['NS-CMIC'],               # 中国中铁
    '601186.SH': ['NS-CMIC'],               # 中国铁建
    '601766.SH': ['NS-CMIC'],               # 中车
    '600150.SH': ['NS-CMIC'],               # 中国船舶
    '600685.SH': ['NS-CMIC'],               # 中船防务
    '000768.SZ': ['NS-CMIC'],               # 中航西飞
    '601985.SH': ['NS-CMIC'],               # 中国核电
    '000519.SZ': ['NS-CMIC'],               # 江南化工 (军工)
    '600562.SH': ['NS-CMIC'],               # 宏达电子 (军工电子)
    '600487.SH': ['NS-CMIC'],               # 亨通光电 (军工电缆)
    '688385.SH': ['NS-CMIC'],               # 四方光电 (军工)
    '688507.SH': ['NS-CMIC', 'Entity List'], # 索辰信息
    '603678.SH': ['NS-CMIC'],               # 火炬电子 (军工电子)
    '600967.SH': ['NS-CMIC'],               # 内蒙一机
    '600522.SH': ['NS-CMIC'],               # 中天科技 (军工电缆)
    '002371.SZ': ['NS-CMIC', 'Entity List'], # 北方华创 (双重)
    '688072.SH': ['NS-CMIC', 'Entity List'], # 拓荆科技 (双重)
    '688256.SH': ['NS-CMIC', 'Entity List'], # 寒武纪 (双重)
    '688981.SH': ['NS-CMIC', 'Entity List'], # 中芯国际 (双重)
}

# ========== 2. 更新 cache/sanction_list.json ==========
with open('cache/sanction_list.json', 'r', encoding='utf-8') as f:
    sl = json.load(f)

print(f'原制裁清单条目数: {len(sl)}')

added = 0
updated = 0
for ts, labels in NEW_SANCTIONS.items():
    existing = set(sl.get(ts, []))
    new_set = set(labels)
    merged = existing.union(new_set)
    if ts not in sl:
        sl[ts] = sorted(merged)
        added += 1
        print(f'  [新增] {ts} {merged}')
    elif merged != existing:
        sl[ts] = sorted(merged)
        updated += 1
        print(f'  [更新] {ts} {sl[ts]}')
    # else: 已存在且相同，跳过

print(f'新增: {added} 条')
print(f'更新: {updated} 条')
print(f'合计: {len(sl)} 条')

with open('cache/sanction_list.json', 'w', encoding='utf-8') as f:
    json.dump(sl, f, ensure_ascii=False, indent=2)
print('\n已写入 cache/sanction_list.json')

# ========== 3. 同步更新 stock_data_full.json 的 sanction 字段 ==========
with open('stock_data_full.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f'\nstock_data_full.json 共 {len(data)} 条')
sanction_codes = set(sl.keys())
updated_count = 0
cleared_count = 0

for r in data:
    ts = r['ts_code']
    if ts in sanction_codes:
        new_val = sl[ts]  # 使用合并后的标签列表
        if r.get('sanction') != new_val:
            r['sanction'] = new_val
            updated_count += 1
    else:
        if r.get('sanction'):
            r['sanction'] = None
            cleared_count += 1

print(f'更新 sanction 字段: {updated_count} 条')
print(f'清除过时 sanction: {cleared_count} 条')

with open('stock_data_full.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print('已写入 stock_data_full.json')

print('\n===== 完成 =====')
