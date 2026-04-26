"""用NeoData批量验证ah_status.json中"announced"股票是否已完成港股上市"""
import json, subprocess, sys, time

AH_PATH = 'c:/Users/LG-NB/WorkBuddy/20260425113716/cache/ah_status.json'
SCRIPT = r'C:\Users\LG-NB\.workbuddy\plugins\marketplaces\cb_teams_marketplace\plugins\finance-data\skills\neodata-financial-search\scripts\query.py'
PYTHON = r'C:\Users\LG-NB\.workbuddy\binaries\python\versions\3.13.12\python.exe'

with open(AH_PATH, 'r', encoding='utf-8') as f:
    ah = json.load(f)

# Get all "announced" stocks
announced_stocks = {k: v for k, v in ah.items() if v == 'announced'}
print(f"Total announced: {len(announced_stocks)}")

# Check each one with NeoData
changes = []
for i, (code, _) in enumerate(announced_stocks.items()):
    name = code  # fallback
    # Get stock name from stock_data_full.json
    print(f"[{i+1}/{len(announced_stocks)}] Checking {code}...")
    
    result = subprocess.run(
        [PYTHON, SCRIPT, '--query', f'{code} 是否已在港股上市，港股代码是什么', '--data-type', 'api'],
        capture_output=True, text=True, timeout=30
    )
    
    output = result.stdout + result.stderr
    
    # Check if output mentions HK stock code
    if 'HK' in output or '.HK' in output or '港股' in output:
        # Further check: if it mentions "已上市" or has a HK code like 03xxx
        if '已上市' in output or '上市' in output:
            # Look for HK code pattern
            import re
            hk_codes = re.findall(r'0\d{4}\.HK', output)
            if hk_codes:
                print(f"  -> Already listed! HK code: {hk_codes[0]}")
                changes.append((code, 'listed', hk_codes[0]))
            else:
                print(f"  -> May be listed (mentions 上市)")
        else:
            print(f"  -> Still in progress (递表/公告)")
    else:
        print(f"  -> No HK listing info found")
    
    time.sleep(1)  # rate limit

# Apply changes
for code, status, hk_code in changes:
    ah[code] = status
    print(f"UPDATED: {code} -> {status} (HK: {hk_code})")

if changes:
    with open(AH_PATH, 'w', encoding='utf-8') as f:
        json.dump(ah, f, ensure_ascii=False, indent=2)
    print(f"\nTotal changes: {len(changes)}")
else:
    print("\nNo changes needed")
