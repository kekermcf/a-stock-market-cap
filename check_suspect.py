import json
with open('c:/Users/LG-NB/WorkBuddy/20260425113716/cache/ah_status.json','r',encoding='utf-8') as f:
    ah = json.load(f)

suspect = {
    '300059.SZ': '东方财富',
    '688036.SH': '传音控股',
    '002415.SZ': '海康威视',
    '002459.SZ': '晶澳科技',
}
for code, name in suspect.items():
    print(f'{code} {name}: {ah.get(code, "NOT FOUND")}')
