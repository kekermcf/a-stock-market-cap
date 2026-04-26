import json

with open('c:/Users/LG-NB/WorkBuddy/20260425113716/cache/ah_status.json', 'r', encoding='utf-8') as f:
    ah = json.load(f)

# 1. Fix: nanhua futures already listed on 2025.12.23
ah['603093.SH'] = 'listed'

# 2. Split announced into announced (formally filed) vs rumor (only rumored/planning)
# Based on research:

# These should be "rumor" - only rumored or planning, no formal HKEX filing:
rumor_codes = [
    '000725.SZ',  # jingdongfang A - no filing record
    '300502.SZ',  # xin yi sheng - 2026.4 rumor only
    '300783.SZ',  # san zhi song shu - 2025.4 filed but expired, no re-filing
    '300896.SZ',  # ai mei ke - 2022 filed but expired, no new filing
    '601126.SH',  # si fang gu fen - 2026.4.13 announced planning only
    '688099.SH',  # jing chen gu fen - no filing record
    '300153.SZ',  # ke tai dian yuan - only announced planning
]

for code in rumor_codes:
    if code in ah:
        ah[code] = 'rumor'

listed = sum(1 for v in ah.values() if v == 'listed')
announced_count = sum(1 for v in ah.values() if v == 'announced')
rumor_count = sum(1 for v in ah.values() if v == 'rumor')
print(f'Total: listed={listed}, announced={announced_count}, rumor={rumor_count}')
print(f'Grand total: {listed + announced_count + rumor_count}')

# Show rumor stocks
print('\nRumor stocks:')
for code, status in sorted(ah.items()):
    if status == 'rumor':
        print(f'  {code}')

# Show announced stocks  
print('\nAnnounced stocks (formally filed):')
for code, status in sorted(ah.items()):
    if status == 'announced':
        print(f'  {code}')

with open('c:/Users/LG-NB/WorkBuddy/20260425113716/cache/ah_status.json', 'w', encoding='utf-8') as f:
    json.dump(ah, f, ensure_ascii=False, indent=2)
print('\nSaved!')
