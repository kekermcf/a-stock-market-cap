"""Compare AH stock list from AKShare with our ah_status.json
AKShare gives us HK codes, we need to find matching A-share stocks in our mv data
"""
import json, csv

# Load AH list from AKShare (HK codes)
hk_ah = {}
with open('c:/Users/LG-NB/WorkBuddy/20260425113716/ah_list_akshare.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        hk_code = row['代码'].zfill(5)
        hk_name = row['名称']
        hk_ah[hk_code] = hk_name

print(f'AKShare AH list: {len(hk_ah)} HK stocks')

# Load our mv data to get A-share code -> name mapping
import glob, os
cache_dir = 'c:/Users/LG-NB/WorkBuddy/20260425113716/cache'
mv_files = sorted(glob.glob(os.path.join(cache_dir, 'mv_data_*.json')))
with open(mv_files[-1], 'r', encoding='utf-8') as f:
    mv_data = json.load(f)

# Build A-share stock list
a_stocks = {}
if isinstance(mv_data, list):
    for item in mv_data:
        code = item.get('ts_code', item.get('code', ''))
        name = item.get('name', '')
        a_stocks[code] = name

print(f'Our A-share stock list: {len(a_stocks)} stocks')

# Load ah_status
with open('c:/Users/LG-NB/WorkBuddy/20260425113716/cache/ah_status.json', 'r', encoding='utf-8') as f:
    ah_status = json.load(f)

# Count how many of our listed stocks are in the HK list
# Many HK codes for A+H stocks share similar digits with A-share codes
# e.g. A: 601318.SH -> H: 02318
# The pattern is usually: A-code 6xxxxx -> H-code 0xxxx (drop leading 6/0, pad to 5 digits)

# Alternative approach: just check all stocks in ah_status as 'listed' 
# and see if we can find them in the HK list by name matching

# Let's check which of our "listed" stocks have names that match HK names
listed_codes = [k for k, v in ah_status.items() if v == 'listed']
print(f'Our listed A+H: {len(listed_codes)}')

# Now let's find all A-share stocks (in our mv data) that are NOT in ah_status
# but whose names might indicate they're A+H
# We can also check by looking at the AKShare HK list and matching by name similarity

# Simple name match (remove common suffixes like 股份/H/股份公司/A etc)
def normalize_name(name):
    suffixes = ['股份', '股份有限公司', '集团', 'A', 'H', '控股', '科技', '有限公司']
    n = name
    for s in suffixes:
        n = n.replace(s, '')
    return n.strip()

# Build name -> ts_code map
a_name_map = {}
for code, name in a_stocks.items():
    norm = normalize_name(name)
    a_name_map[norm] = code

# Check HK names against A-share names
potential_missing = []
for hk_code, hk_name in hk_ah.items():
    norm_hk = normalize_name(hk_name.replace('股份', ''))
    # Try to find matching A-share
    for norm_a, ts_code in a_name_map.items():
        if norm_a == norm_hk or norm_a in norm_hk or norm_hk in norm_a:
            if len(norm_a) >= 2:  # At least 2 chars to avoid false matches
                status = ah_status.get(ts_code, 'NOT_FOUND')
                if status != 'listed':
                    potential_missing.append((ts_code, a_stocks.get(ts_code, ''), hk_code, hk_name, status))
                break

print(f'\nPotential A+H stocks in our data but not marked as listed:')
for ts_code, a_name, hk_code, hk_name, status in potential_missing:
    print(f'  {ts_code} {a_name} (H: {hk_code} {hk_name}) -> {status}')
print(f'Total: {len(potential_missing)}')
