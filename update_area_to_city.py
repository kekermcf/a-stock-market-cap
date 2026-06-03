import json

# Province → capital city mapping
PROVINCE_TO_CITY = {
    '北京': '北京市', '上海': '上海市', '天津': '天津市', '重庆': '重庆市',
    '广东': '广州市', '浙江': '杭州市', '江苏': '南京市', '山东': '济南市',
    '福建': '福州市', '四川': '成都市', '安徽': '合肥市', '湖南': '长沙市',
    '湖北': '武汉市', '河南': '郑州市', '河北': '石家庄市', '陕西': '西安市',
    '山西': '太原市', '辽宁': '沈阳市', '吉林': '长春市', '黑龙江': '哈尔滨市',
    '云南': '昆明市', '贵州': '贵阳市', '广西': '南宁市', '甘肃': '兰州市',
    '青海': '西宁市', '宁夏': '银川市', '新疆': '乌鲁木齐市',
    '西藏': '拉萨市', '海南': '海口市', '江西': '南昌市',
    '内蒙古': '呼和浩特市', '内蒙': '呼和浩特市',
    '深圳': '深圳市',
}

# Manual company city overrides (ts_code → city)
COMPANY_CITY = {
    '300750.SZ': '宁德市',    # 宁德时代
    '601899.SH': '龙岩市',    # 紫金矿业
    '600549.SH': '厦门市',    # 厦门钨业
    '601166.SH': '福州市',    # 兴业银行
    '601933.SH': '福州市',    # 永辉超市
    '002594.SZ': '深圳市',    # 比亚迪
    '000333.SZ': '佛山市',    # 美的集团
    '000651.SZ': '珠海市',    # 格力电器
    '600690.SH': '青岛市',    # 海尔智家
    '601012.SH': '西安市',    # 隆基绿能
    '300308.SZ': '苏州市',    # 中际旭创
    '600519.SH': '遵义市',    # 贵州茅台
    '601138.SH': '深圳市',    # 工业富联
    '002415.SZ': '杭州市',    # 海康威视
    '601888.SH': '海口市',    # 中国中免
    '600036.SH': '深圳市',    # 招商银行
    '601318.SH': '深圳市',    # 中国平安
    '600048.SH': '广州市',    # 保利发展
    '001979.SZ': '深圳市',    # 招商蛇口
    '300502.SZ': '成都市',    # 新易盛
    '600900.SH': '宜昌市',    # 长江电力
    '601211.SH': '上海市',    # 国泰君安
    '600837.SH': '上海市',    # 海通证券
    '601688.SH': '南京市',    # 华泰证券
    '300124.SZ': '苏州市',    # 汇川技术
    '002475.SZ': '深圳市',    # 立讯精密
    '000858.SZ': '宜宾市',    # 五粮液
    '603288.SH': '湖州市',    # 海天味业
}

def main():
    path = 'stock_data_full.json'
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    updated = 0
    kept = 0
    overridden = 0

    for r in data:
        ts = r['ts_code']
        area = r.get('area', '')
        if not area:
            continue

        # Already city-level
        if '市' in area:
            kept += 1
            continue

        # Manual override
        if ts in COMPANY_CITY:
            r['area'] = COMPANY_CITY[ts]
            overridden += 1
            updated += 1
            continue

        # Province → capital
        if area in PROVINCE_TO_CITY:
            r['area'] = PROVINCE_TO_CITY[area]
            updated += 1
        else:
            print(f"  Unmapped: {ts} {r.get('name','')} area={area}")

    print(f"Kept as-is (already city): {kept}")
    print(f"Updated (province→capital): {updated - overridden}")
    print(f"Overridden (manual): {overridden}")
    print(f"Total updated: {updated}")

    # Write without indent to be fast
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    print("Saved (no indent for speed).")

    # Re-format with indent in a second pass (optional, can skip)
    # Actually, gen_report.py doesn't care about formatting, so skip re-format.

if __name__ == '__main__':
    main()
