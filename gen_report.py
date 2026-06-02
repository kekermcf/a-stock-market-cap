import json, os

# DATA_DIR: 项目根目录 = 脚本所在目录（macOS/Linux 兼容）
DATA_DIR = os.path.dirname(os.path.abspath(__file__))

# 自动检测最新交易日：从缓存文件名推断，或用今天/上个交易日
import glob
mv_files = sorted(glob.glob(f'{DATA_DIR}/cache/mv_data_*.json'))
if mv_files:
    trade_date = os.path.basename(mv_files[-1]).replace('mv_data_', '').replace('.json', '')
else:
    from datetime import datetime, timedelta
    d = datetime.now()
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    trade_date = d.strftime('%Y%m%d')

date_display = f'{trade_date[:4]}年{int(trade_date[4:6])}月{int(trade_date[6:8])}日'

with open(f'{DATA_DIR}/stock_data_full.json', 'r', encoding='utf-8') as f:
    results_all = json.load(f)

# Merge supplementary stocks from QQ qt data
existing_codes = {r['ts_code'] for r in results_all}
mv_mid_path = f'{DATA_DIR}/cache/mv_100_200_data.json'
if os.path.exists(mv_mid_path):
    with open(mv_mid_path, 'r', encoding='utf-8') as f:
        mv_mid = json.load(f)
    # Load annual_pctchg for ytd data
    pct_data = {}
    pct_path = f'{DATA_DIR}/cache/annual_pctchg.json'
    if os.path.exists(pct_path):
        with open(pct_path, 'r', encoding='utf-8') as f:
            pct_data = json.load(f)
    mid_added = 0
    for s in mv_mid:
        code = s.get('ts_code', '')
        if not code or code in existing_codes:
            continue
        if s.get('total_mv', 0) < 200:
            continue
        pct = pct_data.get(code, {})
        results_all.append({
            'ts_code': code,
            'name': s.get('name', ''),
            'industry': s.get('industry', ''),
            'industry_l1': '',
            'industry_l2': '',
            'area': s.get('area', ''),
            'close': s.get('close', 0),
            'pct_chg': s.get('pct_chg', ''),
            'pe': s.get('pe', ''),
            'pb': s.get('pb', ''),
            'total_mv': s.get('total_mv', 0),
            'revenue': None,
            'gross_profit': None,
            'net_profit': None,
            'gpr': None,
            'npm': None,
            'ytd_2024': pct.get('ytd_2024'),
            'ytd_2025': pct.get('ytd_2025'),
            'ytd_2026': pct.get('ytd_2026'),
            'mv_history': None,
            'list_date': '',
            'business_desc': '',
            'main_biz': '',
            'products': [],
            'regions': [],
        })
        existing_codes.add(code)
        mid_added += 1
    print(f'Merged {mid_added} supplementary stocks (>=200B)')

# Filter >= 200B
results = [r for r in results_all if r.get('total_mv', 0) >= 200]
print(f'{len(results)} stocks with MV >= 200B')

# Load A+H status (needed for JS filter)
ah_status = {}
ah_path = f'{DATA_DIR}/cache/ah_status.json'
if os.path.exists(ah_path):
    with open(ah_path, 'r', encoding='utf-8') as f:
        ah_status = json.load(f)

# Load sanction list (dict: ts_code → ["NS-CMIC", "Entity List", ...])
sanction_list = {}
sl_path = f'{DATA_DIR}/cache/sanction_list.json'
if os.path.exists(sl_path):
    with open(sl_path, 'r', encoding='utf-8') as f:
        sanction_list = json.load(f)

# Load SOE list
soe_list = []
soe_path = f'{DATA_DIR}/cache/soe_list.json'
if os.path.exists(soe_path):
    with open(soe_path, 'r', encoding='utf-8') as f:
        soe_list = json.load(f)

# Build data JSON
embed_data = []
for r in results:
    embed_data.append({
        'ts_code': r['ts_code'],
        'name': r['name'],
        'industry': r.get('industry', ''),
        'industry_l1': r.get('industry_l1', ''),
        'industry_l2': r.get('industry_l2', ''),
        'close': r['close'],
        'total_mv': r['total_mv'],
        'pe': r.get('pe', ''),
        'pb': r.get('pb', ''),
        'revenue': r.get('revenue'),
        'gross_profit': r.get('gross_profit'),
        'net_profit': r.get('net_profit'),
        'gpr': r.get('gpr'),
        'npm': r.get('npm'),
        'ytd_2024': r.get('ytd_2024'),
        'ytd_2025': r.get('ytd_2025'),
        'ytd_2026': r.get('ytd_2026'),
        'mv_history': r.get('mv_history'),
        'list_date': r.get('list_date', ''),
        'business_desc': r.get('business_desc', ''),
        'area': r.get('area', ''),
        'products': r.get('products', []),
        'regions': r.get('regions', []),
    })

# Load A+H code mapping
ah_code_map = {}
ah_map_path = f'{DATA_DIR}/cache/ah_code_map.json'
if os.path.exists(ah_map_path):
    with open(ah_map_path, 'r', encoding='utf-8') as f:
        ah_code_map = json.load(f)
# Inject hk_code into embed_data
for d in embed_data:
    d['hk_code'] = ah_code_map.get(d['ts_code'], '')

# Load A+H HK listing dates
ah_hk_dates = {}
ah_hk_dates_path = f'{DATA_DIR}/cache/ah_hk_list_dates.json'
if os.path.exists(ah_hk_dates_path):
    with open(ah_hk_dates_path, 'r', encoding='utf-8') as f:
        ah_hk_dates = json.load(f)
for d in embed_data:
    d['hk_list_date'] = ah_hk_dates.get(d['ts_code'], '')

# Load A+H premium data
ah_premia = {}
ah_premia_path = f'{DATA_DIR}/cache/ah_premia.json'
if os.path.exists(ah_premia_path):
    with open(ah_premia_path, 'r', encoding='utf-8') as f:
        ah_premia = json.load(f)
for d in embed_data:
    _ap = ah_premia.get(d['ts_code'], None)
    d['ah_premium'] = -_ap if _ap is not None else None

rj = json.dumps(embed_data, ensure_ascii=True)
aj = json.dumps(ah_status, ensure_ascii=True)
cj = json.dumps(ah_code_map, ensure_ascii=True)
sj = json.dumps(sanction_list, ensure_ascii=True)
soej = json.dumps(soe_list, ensure_ascii=True)

# Industry stats
industry_stats = {}
for r in results:
    ind = r.get('industry') or '未分类'
    if ind not in industry_stats:
        industry_stats[ind] = {'count': 0, 'total_mv': 0}
    industry_stats[ind]['count'] += 1
    industry_stats[ind]['total_mv'] += r['total_mv']
ind_sorted = sorted(industry_stats.items(), key=lambda x: x[1]['total_mv'], reverse=True)
max_ind_mv = ind_sorted[0][1]['total_mv'] if ind_sorted else 1

ind_options = ''.join(f'<option value="{ind}">{ind} ({stat["count"]})</option>\n' for ind, stat in ind_sorted)

ind_bars = ''.join(
    f'<div class="ind-row"><div class="ind-name">{ind}</div><div class="ind-bar-wrap"><div class="ind-bar"><div class="ind-bar-fill" style="width:{stat["total_mv"]/max_ind_mv*100:.1f}%"></div></div></div><div class="ind-count">{stat["count"]}</div><div class="ind-mv">{stat["total_mv"]:,.0f}</div></div>\n'
    for ind, stat in ind_sorted[:30]
)

# Stats
total_stocks = len(results)
has_fin = sum(1 for r in results if r.get('revenue'))
max_mv = f"{results[0]['total_mv']:,.0f}"
avg_mv = f"{sum(r['total_mv'] for r in results)/len(results):,.0f}"
med_mv = f"{results[len(results)//2]['total_mv']:,.0f}"

html = f"""<!-- deploy:v20260602-3 -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>A股市值超200亿股票名单（{trade_date}）</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;background:#f5f7fa;color:#333}}
.header{{background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%);color:#fff;padding:32px 24px;text-align:center}}
.header h1{{font-size:28px;margin-bottom:8px}}
.header .date{{font-size:14px;opacity:.8}}
.header .method{{font-size:12px;opacity:.6;margin-top:4px}}
.container{{max-width:1900px;margin:0 auto 40px;padding:0 24px}}
.section{{background:#fff;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,.06);margin-bottom:24px;overflow:hidden}}
.section-title{{font-size:18px;font-weight:600;padding:16px 20px;border-bottom:1px solid #eee;display:flex;align-items:center;gap:8px}}
.controls{{padding:16px 20px;border-bottom:1px solid #eee;display:flex;gap:12px;flex-wrap:wrap;align-items:center}}
.search-box{{flex:1;min-width:200px;padding:10px 16px;border:1px solid #ddd;border-radius:8px;font-size:14px;outline:none}}
.search-box:focus{{border-color:#0f3460}}
select{{padding:10px 16px;border:1px solid #ddd;border-radius:8px;font-size:14px;background:#fff;cursor:pointer}}
.badge{{display:inline-block;background:#eef2ff;color:#4338ca;padding:2px 10px;border-radius:12px;font-size:13px;font-weight:500}}
table{{width:100%;border-collapse:collapse;font-size:14px}}
thead th{{background:#f8f9fa;padding:12px 8px;text-align:right;font-weight:600;color:#555;font-size:13px;position:sticky;top:0;cursor:pointer;user-select:none;white-space:nowrap;z-index:2}}
thead th:nth-child(1),thead th:nth-child(2),thead th:nth-child(3),thead th:nth-child(4),thead th:nth-child(5),thead th:nth-child(6){{text-align:left}}
thead th:hover{{background:#eef2ff}}
tbody tr{{border-bottom:1px solid #f0f0f0;transition:background .15s;cursor:pointer}}
tbody tr:hover{{background:#f8faff}}
tbody tr.ah-listed{{background:#e8f4fd}}
tbody tr.ah-listed:hover{{background:#d6eaf8}}
tbody tr.ah-announced{{background:#fef9e7}}
tbody tr.ah-announced:hover{{background:#fdf2d1}}
tbody tr.ah-rumor{{background:#f5eef8}}
tbody tr.ah-rumor:hover{{background:#ebe1f0}}
.ah-tag{{display:inline-block;font-size:11px;padding:1px 6px;border-radius:4px;margin-left:6px;vertical-align:middle;font-weight:500}}
.ah-tag.listed{{background:#b3d9f2;color:#1a5276}}
.ah-tag.announced{{background:#f9e79f;color:#7d6608}}
.ah-tag.rumor{{background:#e8daef;color:#6c3483}}
tbody td{{padding:10px 8px;white-space:nowrap;text-align:right}}
tbody td:nth-child(1),tbody td:nth-child(2),tbody td:nth-child(3),tbody td:nth-child(4),tbody td:nth-child(5),tbody td:nth-child(6){{text-align:left}}
.code{{font-family:'SF Mono','Consolas',monospace;font-size:13px;color:#666}}
.hk-code{{font-family:'SF Mono','Consolas',monospace;font-size:11px;color:#f39c12;line-height:1.2}}
.hk-ld{{font-size:10px;color:#999;margin-left:4px;font-weight:400;white-space:nowrap}}
.ah-prem{{font-size:10px;margin-left:4px;font-weight:600;white-space:nowrap}}
.ah-prem.pos{{color:#e74c3c}}
.ah-prem.neg{{color:#27ae60}}
.ytd-merged{{white-space:nowrap}}
.mc-ytd-merged{{font-size:12px;color:#555;margin-top:4px}}
.fav-star{{cursor:pointer;font-size:15px;user-select:none}}
.mv{{font-weight:600;color:#c0392b}}
.chg-up{{color:#c0392b;font-weight:500}}
.chg-dn{{color:#27ae60;font-weight:500}}
.fin-pos{{color:#c0392b;font-weight:500}}
.fin-neg{{color:#27ae60}}
.rate-pos{{color:#27ae60}}
.rate-neg{{color:#c0392b}}
.rate-val{{color:#2980b9;font-weight:500}}
.pending{{color:#bbb;font-style:italic;font-size:12px}}
.biz-col{{max-width:300px;font-size:13px;color:#555;text-align:left;white-space:normal;word-break:break-all}}
.col-ah-status,.col-sanction,.col-hk-date,.col-ah-prem{{white-space:nowrap;text-align:center}}
.col-hk-date{{font-size:11px;color:#999}}
.col-ah-prem{{font-size:11px;font-weight:600}}
.no-report{{color:#999;font-size:11px}}
.name-cell{{display:flex;align-items:center;justify-content:space-between;width:100%;min-width:0}}
.name-cell-left{{display:flex;align-items:center;gap:4px;min-width:0;overflow:hidden}}
.name-cell-right{{display:flex;align-items:center;gap:4px;flex-shrink:0;margin-left:8px}}
.table-wrap{{max-height:700px;overflow-y:auto}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin:24px 0}}
.stat-card{{background:#fff;border-radius:12px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,.06)}}
.stat-card .label{{font-size:13px;color:#888;margin-bottom:6px}}
.stat-card .value{{font-size:28px;font-weight:700;color:#1a1a2e}}
.stat-card .value.red{{color:#e74c3c}}
.stat-card .value.blue{{color:#2980b9}}
.industry-section{{max-height:500px;overflow-y:auto}}
.ind-row{{display:flex;justify-content:space-between;padding:10px 20px;border-bottom:1px solid #f0f0f0;align-items:center}}
.ind-row:hover{{background:#f8faff}}
.ind-name{{font-weight:500;min-width:120px;font-size:13px}}
.ind-bar-wrap{{flex:1;max-width:400px;margin:0 20px;align-self:center}}
.ind-bar{{height:8px;background:#eef2ff;border-radius:4px;overflow:hidden}}
.ind-bar-fill{{height:100%;background:linear-gradient(90deg,#4338ca,#6366f1);border-radius:4px;transition:width .3s}}
.ind-count{{color:#888;font-size:13px;min-width:50px;text-align:right}}
.ind-mv{{font-weight:600;color:#c0392b;min-width:100px;text-align:right;font-size:13px}}
.pagination{{padding:8px 20px 14px;display:flex;justify-content:flex-start;align-items:flex-start;gap:6px;flex-wrap:wrap;border-bottom:1px solid #eee;margin-bottom:2px}}
.page-btn{{padding:6px 14px;border:1px solid #ddd;border-radius:6px;background:#fff;cursor:pointer;font-size:13px}}
.page-btn:hover{{background:#f0f0f0}}
.page-btn.active{{background:#1a1a2e;color:#fff;border-color:#1a1a2e}}
.page-info{{font-size:13px;color:#888}}
.page-btn-wrap{{display:inline-flex;flex-direction:column;align-items:center;gap:2px}}
.page-mv-label{{font-size:10px;color:#999;line-height:1}}
.goto-wrap{{display:inline-flex;align-items:center;gap:4px;margin-left:8px}}
.goto-input{{width:48px;padding:4px 6px;border:1px solid #ddd;border-radius:6px;font-size:13px;text-align:center;outline:none}}
.goto-input:focus{{border-color:#0f3460}}
.goto-btn{{padding:4px 10px;font-size:12px}}
.modal-overlay{{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.5);z-index:1000;justify-content:center;align-items:center}}
.modal-overlay.active{{display:flex}}
.modal{{background:#fff;border-radius:16px;width:94%;max-width:1000px;max-height:92vh;overflow-y:auto;box-shadow:0 20px 60px rgba(0,0,0,.3);position:relative}}
.modal-header{{padding:24px 28px 16px;border-bottom:1px solid #eee;display:flex;justify-content:space-between;align-items:flex-start}}
.modal-header h2{{font-size:22px;color:#1a1a2e}}
.modal-header .sub{{font-size:14px;color:#888;margin-top:4px}}
.modal-header .price-info{{font-size:13px;margin-top:6px}}
.modal-close{{width:36px;height:36px;border:none;background:#f0f0f0;border-radius:50%;font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center;color:#666;flex-shrink:0}}
.modal-close:hover{{background:#e0e0e0}}
.modal-body{{padding:24px 28px}}
.modal-section{{margin-bottom:24px}}
.modal-section h3{{font-size:16px;font-weight:600;color:#1a1a2e;margin-bottom:12px;padding-bottom:8px;border-bottom:2px solid #eef2ff}}
.finance-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px}}
.finance-item{{background:#f8f9fa;border-radius:10px;padding:14px}}
.finance-item .fl{{font-size:12px;color:#888;margin-bottom:4px}}
.finance-item .fv{{font-size:18px;font-weight:700;color:#1a1a2e}}
.finance-item .fv.red{{color:#c0392b}}
.finance-item .fv.green{{color:#27ae60}}
.finance-item .fv.blue{{color:#2980b9}}
#chartBox{{width:100%;height:420px}}
.profile-box{{background:#f8f9fa;border-radius:10px;padding:16px 20px;font-size:14px;line-height:1.8;color:#444}}
.profile-box .label{{color:#888;font-size:12px;display:inline-block;min-width:80px}}
.profile-box .info-row{{margin-bottom:6px}}
.profile-box .desc{{margin-top:10px;color:#333;padding-top:10px;border-top:1px solid #eee}}
.biz-detail{{margin-top:12px;padding-top:10px;border-top:1px solid #eee}}
.biz-title{{font-size:13px;font-weight:600;color:#555;margin-bottom:6px}}
.biz-row{{display:flex;align-items:center;justify-content:space-between;padding:3px 0;font-size:13px}}
.biz-name{{flex:1;color:#444}}
.biz-rev{{color:#2980b9;font-weight:500;min-width:100px;text-align:right}}
.biz-pct{{color:#888;min-width:60px;text-align:right}}
.ytd-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:12px}}
.ytd-card{{text-align:center;padding:12px;border-radius:10px;background:#f8f9fa}}
.ytd-card .year{{font-size:13px;color:#888;margin-bottom:4px}}
.ytd-card .val{{font-size:22px;font-weight:700}}
.data-source{{font-size:11px;color:#aaa;text-align:center;margin-top:8px;display:none}}
body.mobile .data-source{{display:block}}
.view-toggle{{background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.3);color:#fff;padding:8px 14px;border-radius:8px;cursor:pointer;font-size:13px;white-space:nowrap;transition:background .2s;display:flex;align-items:center;gap:6px}}
.view-toggle:hover{{background:rgba(255,255,255,.25)}}
/* ===== Mobile View ===== */
body.mobile .container{{padding:0 12px}}
body.mobile .header h1{{font-size:20px}}
body.mobile .header .method{{display:none}}
body.mobile .controls{{padding:10px 12px;gap:8px;flex-wrap:wrap}}
body.mobile .search-box{{min-width:0;font-size:16px;flex:0 0 100%}}  /* 16px prevents iOS zoom, full width */
body.mobile select{{font-size:16px;padding:8px 12px}}
body.mobile .table-wrap{{max-height:none;overflow:visible}}
body.mobile table{{display:none}}
body.mobile .pagination{{padding:12px}}
body.mobile .mobile-list{{display:block!important}}
body.mobile .stats{{grid-template-columns:repeat(2,1fr);gap:10px;margin:12px 0}}
body.mobile .stat-card{{padding:14px}}
body.mobile .stat-card .value{{font-size:22px}}
body.mobile .stat-card .label{{font-size:12px}}
body.mobile .industry-section{{max-height:none}}
body.mobile .ind-bar-wrap{{max-width:200px}}
body.mobile .modal{{width:100%;max-width:100%;max-height:100vh;border-radius:0;top:0;position:fixed}}
body.mobile .modal-header{{padding:16px}}
body.mobile .modal-body{{padding:16px}}
body.mobile .finance-grid{{grid-template-columns:repeat(2,1fr)}}
body.mobile #chartBox{{height:300px}}
body.mobile .section-title{{font-size:16px;padding:12px 16px}}
body.mobile .modal-header{{position:sticky;top:0;background:#fff;z-index:10;padding:12px 16px}}
body.mobile .modal-close{{width:44px;height:44px;font-size:22px}}
/* Mobile card list */
.mobile-list{{display:none}}
.mobile-card{{background:#fff;border-radius:10px;padding:14px 16px;margin-bottom:10px;box-shadow:0 1px 4px rgba(0,0,0,.06);cursor:pointer;transition:box-shadow .2s}}
.mobile-card:hover{{box-shadow:0 2px 8px rgba(0,0,0,.12)}}
.mobile-card.ah-listed{{background:#e8f4fd}}
.mobile-card.ah-announced{{background:#fef9e7}}
.mobile-card.ah-rumor{{background:#f5eef8}}
.mc-top{{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}}
.mc-rank{{font-size:12px;color:#999;margin-right:6px;font-weight:600}}
.mc-name{{font-size:16px;font-weight:700;color:#1a1a2e}}
.mc-name .ah-tag{{font-size:10px;padding:1px 5px;margin-left:4px}}
.mc-mv{{font-size:18px;font-weight:700;color:#c0392b}}
.mc-info{{display:flex;gap:16px;font-size:13px;color:#888;align-items:center}}
.mc-info span{{white-space:nowrap}}
.mc-info .code{{font-family:'SF Mono','Consolas',monospace;font-size:12px}}
.hk-code-m{{font-family:'SF Mono','Consolas',monospace;font-size:11px;color:#f39c12}}
.mc-ytd{{display:flex;gap:8px;margin-top:8px}}
.mc-ytd-item{{font-size:13px;white-space:nowrap}}
.mc-ytd-item .year-label{{color:#888;margin-right:2px}}
.mc-fin{{display:flex;gap:16px;margin-top:6px;font-size:12px;color:#666}}
/* Watchlist button only - page navigates to watchlist.html */
.watch-btn{{background:linear-gradient(135deg,#f39c12,#e67e22);color:#fff;border:none;border-radius:8px;padding:8px 16px;font-size:14px;cursor:pointer;margin-right:12px;font-weight:600;text-decoration:none}}
.watch-btn:hover{{opacity:.9}}
.fav-star{{display:inline-block;cursor:pointer;font-size:16px;padding:0 6px;user-select:none;transition:transform .2s}}
.fav-star:hover{{transform:scale(1.3)}}
.fav-star.on{{color:#f39c12}}
.fav-star.off{{color:#ccc}}
/* Sanction tag */
.sanction-tag{{display:inline-block;cursor:pointer;font-size:12px;padding:0 5px;user-select:none;transition:transform .2s;vertical-align:middle;margin-left:4px;border-radius:3px;font-weight:600;letter-spacing:1px}}
.sanction-tag:hover{{transform:scale(1.2)}}
.sanction-tag.on{{background:#c0392b;color:#fff;font-size:10px}}
.sanction-tag.off{{color:#ddd;font-size:14px}}
/* Sanction row highlight */
tr.sanction-row{{background:#fde8e8!important}}
tr.sanction-row:hover{{background:#f5c6c6!important}}
.mobile-card.sanction-row{{background:#fde8e8!important}}
/* Mobile back-to-top */
.back-top{{display:none;width:100%;padding:14px 0;text-align:center;background:#f0f2f5;color:#555;font-size:15px;font-weight:600;border:none;cursor:pointer;border-radius:10px;margin-top:12px;letter-spacing:2px}}
body.mobile .back-top{{display:block}}
/* Mobile watchlist tweaks */
body.mobile .fav-star{{font-size:20px;padding:4px 8px}}
body.mobile .watch-btn{{padding:6px 12px;font-size:13px;margin-right:8px}}
body.mobile .sanction-tag{{font-size:14px;padding:2px 6px}}
body.mobile .sanction-tag.on{{font-size:11px}}
</style>
</head>
<body>
<div id="jsError" style="display:none;position:fixed;top:0;left:0;width:100%;padding:12px;background:#fee;color:#c00;z-index:9999;font-size:14px"></div>

<div class="header">
  <div style="position:relative">
    <div>
      <nav style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap;justify-content:center">
        <a href="ashare.html" style="color:#fff;text-decoration:none;font-size:13px;padding:4px 10px;border-radius:6px;background:rgba(79,70,229,.5);font-weight:600">🇨🇳 A股</a>
        <a href="hongkong.html" style="color:rgba(255,255,255,.7);text-decoration:none;font-size:13px;padding:4px 10px;border-radius:6px;background:rgba(255,255,255,.1)">🇭🇰 H股</a>
        <a href="watchlist.html" style="color:rgba(255,255,255,.7);text-decoration:none;font-size:13px;padding:4px 10px;border-radius:6px;background:rgba(255,255,255,.1)">⭐ 自选</a>
      </nav>
      <h1 style="text-align:center">A股市值超200亿股票名单</h1>
      <div class="date">数据截止：{date_display}（收盘）</div>
      <div class="method" style="text-align:center">市值：腾讯财经API x Tushare总股本 · 行业：NeoData二级行业 · 财务：东方财富（2025年报） · 点击行查看详情</div>
    </div>
    <button id="viewToggle" class="view-toggle" onclick="toggleView()" title="切换手机版/桌面版" style="position:absolute;right:0;top:0">
      <span id="viewIcon">📱</span>
      <span id="viewLabel">手机版</span>
    </button>
  </div>
  </div>
</div>

<div class="container">
  <div class="section">
    <div class="section-title">
      股票名单
      <span class="badge" id="countBadge">{total_stocks} 只</span>
      <span style="margin-left:auto;font-size:12px;color:#aaa;font-weight:400">点击公司行查看详情与市值走势</span>
    </div>
    <div class="controls">
      <input type="text" class="search-box" id="searchInput" placeholder="搜索股票代码/名称/行业...">
      <select id="industryFilter"><option value="">全部行业</option>{ind_options}</select>
      <select id="mvFilter">
        <option value="0">全部市值</option>
        <option value="200">&gt;200亿</option>
        <option value="300">&gt;300亿</option>
        <option value="500">&gt;500亿</option>
        <option value="1000">&gt;1,000亿</option>
        <option value="3000">&gt;3,000亿</option>
        <option value="5000">&gt;5,000亿</option>
        <option value="10000">&gt;10,000亿</option>
      </select>
      <select id="ahFilter">
        <option value="">全部状态</option>
        <option value="listed">A+H</option>
        <option value="announced">拟H股</option>
        <option value="rumor">Rumor</option>
        <option value="none">无动作</option>
      </select>
      <select id="sanctionFilter">
        <option value="">含制裁</option>
        <option value="exclude">排除制裁</option>
      </select>
      <select id="soeFilter">
        <option value="">含国企</option>
        <option value="exclude">排除国企</option>
      </select>
      <button id="filterHkNew" style="padding:8px 14px;border:1px solid #ddd;border-radius:8px;background:#fff;cursor:pointer;font-size:13px;white-space:nowrap" title="仅显示A+H公司，按H股上市时间倒序">🇭🇰 H股次新股</button>
      <button id="clearFilters" style="padding:8px 14px;border:1px solid #ddd;border-radius:8px;background:#fff;cursor:pointer;font-size:13px;white-space:nowrap;color:#888" title="清除所有筛选条件">✕ 清除</button>
    </div>
    <div class="pagination" id="pagination"></div>
    <div class="table-wrap">
      <table>
        <thead><tr>
          <th data-sort="rank">排名</th>
          <th data-sort="fav" style="width:32px;text-align:center">收藏</th>
          <th data-sort="ts_code">代码</th>
          <th data-sort="name">名称</th>
          <th data-sort="industry">行业</th>
          <th data-sort="business_desc">主营业务</th>
          <th data-sort="ah_status">A+H状态</th>
          <th style="text-align:center">制裁</th>
          <th style="text-align:center">H上市日</th>
          <th data-sort="ah_premium">H/A溢价</th>
          <th data-sort="total_mv">总市值(亿)</th>
          <th data-sort="ytd_2024">24TD | 25TD | YTD</th>
          <th data-sort="revenue">2025收入(亿)</th>
          <th data-sort="gpr">毛利率</th>
          <th data-sort="net_profit">净利润(亿)</th>
          <th data-sort="npm">净利率</th>
        </tr></thead>
        <tbody id="stockTableBody"></tbody>
      </table>
      <div class="mobile-list" id="mobileList"></div>
      <button class="back-top" id="backTop" onclick="window.scrollTo({{top:0,behavior:'smooth'}})">⬆ 回到顶端</button>
    </div>
  </div>

  <div class="stats">
    <div class="stat-card"><div class="label">市值超200亿股票总数</div><div class="value">{total_stocks}</div></div>
    <div class="stat-card"><div class="label">有2025年报数据</div><div class="value blue">{has_fin}</div></div>
    <div class="stat-card"><div class="label">最大市值</div><div class="value red">{max_mv} 亿</div></div>
    <div class="stat-card"><div class="label">平均市值</div><div class="value">{avg_mv} 亿</div></div>
    <div class="stat-card"><div class="label">市值中位数</div><div class="value">{med_mv} 亿</div></div>
  </div>

  <div class="section">
    <div class="section-title">行业分布（市值Top 30）</div>
    <div class="industry-section">
{ind_bars}    </div>
  </div>

  <div class="data-source">数据来源：Tushare Pro（基础数据） · 腾讯财经API（收盘价/K线） · 东方财富（2025年报） · NeoData（二级行业/公司简介） | 仅供参考，不构成投资建议</div>
</div>

<div class="modal-overlay" id="modalOverlay">
  <div class="modal">
    <div class="modal-header">
      <div><h2 id="modalTitle">-</h2><div class="sub" id="modalSub">-</div><div class="price-info" id="modalPrice"></div></div>
      <button class="modal-close" id="modalClose">&times;</button>
    </div>
    <div class="modal-body" id="modalBody"></div>
  </div>
</div>

<script>
window.onerror = function(msg, url, line) {{
  var el = document.getElementById('jsError');
  if (el) {{ el.style.display = 'block'; el.textContent = 'JS Error: ' + msg + ' (line ' + line + ')'; }}
  return false;
}};

var allData = {rj};
var ahStatus = {aj};  // A+H status: "listed", "announced", or "rumor"
var ahCodeMap = {cj};  // A-share code -> H-share code
var defaultSanction = {sj};  // Pre-loaded sanction dict: ts_code → ["NS-CMIC", "Entity List", ...]
var defaultSOE = {soej};  // Pre-loaded SOE list
// 预计算每只股票按市值降序的原始排名
var mvRank = {{}};
var sorted = allData.slice().sort(function(a, b) {{ return b.total_mv - a.total_mv; }});
for (var ri = 0; ri < sorted.length; ri++) {{ mvRank[sorted[ri].ts_code] = ri + 1; }}
for (var ai = 0; ai < allData.length; ai++) {{ allData[ai]._rank = mvRank[allData[ai].ts_code]; }}
document.getElementById('jsError') && (document.getElementById('jsError').textContent = 'Data loaded: ' + allData.length + ' stocks');

var PAGE_SIZE = 60;
var filtered = allData.slice();
var hkNewOn = false;
var curPage = 1;
var sortKey = 'total_mv';
var sortDir = -1;

function numfmt(v, d) {{
  d = d || 0;
  if (v == null || v === 0 || v === '') return '<span class="pending">-</span>';
  return Math.round(Number(v)).toLocaleString('zh-CN');
}}

function ytdHtml(v) {{
  if (v == null) return '<span class="pending">-</span>';
  var cls = v > 0 ? 'chg-up' : v < 0 ? 'chg-dn' : '';
  var txt = (v > 0 ? '+' : '') + Math.round(v) + '%';
  return '<span class="' + cls + '">' + txt + '</span>';
}}

function rateCls(v) {{
  if (v == null) return '';
  return v >= 30 ? 'rate-pos' : v <= 10 ? 'rate-neg' : 'rate-val';
}}

function render() {{
  PAGE_SIZE = document.body.classList.contains('mobile') ? 20 : 60;
  var tbody = document.getElementById('stockTableBody');
  if (!tbody) return;
  var s = (curPage - 1) * PAGE_SIZE;
  var pd = filtered.slice(s, s + PAGE_SIZE);
  // Desktop table
  var rows = [];
  for (var i = 0; i < pd.length; i++) {{
    var r = pd[i];
    var rk = r._rank;
    var ah = ahStatus[r.ts_code] || '';
    var ahClass = ah === 'listed' ? ' ah-listed' : ah === 'announced' ? ' ah-announced' : ah === 'rumor' ? ' ah-rumor' : '';
    var ahTag = ah === 'listed' ? ' <span class="ah-tag listed">A+H</span>' : ah === 'announced' ? ' <span class="ah-tag announced">拟H股</span>' : ah === 'rumor' ? ' <span class="ah-tag rumor">Rumor</span>' : '';
    var revHtml = r.revenue != null ? numfmt(r.revenue, 1) : '<span class="pending">暂无</span>';
    var gprHtml = r.gpr != null ? Math.round(r.gpr) + '%' : '<span class="pending">-</span>';
    var npHtml = r.net_profit != null ? numfmt(r.net_profit, 0) : '<span class="pending">暂无</span>';
    var npmHtml = r.npm != null ? Math.round(r.npm) + '%' : '<span class="pending">-</span>';
    var npCls = r.net_profit != null ? (r.net_profit >= 0 ? 'fin-pos' : 'fin-neg') : '';
    rows.push('<tr data-code="' + r.ts_code + '" class="' + ahClass.trim() + '">' +
      '<td>' + rk + '</td>' +
      '<td style="text-align:center">' + '<span class="fav-star off" data-code="' + r.ts_code + '">\u2606</span>' + '</td>' +
      '<td class="code">' + r.ts_code + (r.hk_code ? '<br><span class="hk-code">' + r.hk_code + '.HK</span>' : '') + '</td>' +
      '<td><b>' + r.name + '</b></td>' +
      '<td>' + (r.industry || '-') + '</td>' +
      '<td class="biz-col">' + (r.business_desc || '-') + '</td>' +
      '<td class="col-ah-status">' + ahTag + '</td>' +
      '<td class="col-sanction" style="text-align:center">' + '<span class="sanction-tag ' + (defaultSanction.hasOwnProperty(r.ts_code) ? 'on' : 'off') + '" data-code="' + r.ts_code + '">' + (defaultSanction.hasOwnProperty(r.ts_code) ? getSanctionLabel(r.ts_code) : '\u26d4') + '</span>' + '</td>' +
      '<td class="col-hk-date">' + (r.hk_list_date ? '<span class="hk-ld">H' + r.hk_list_date + '</span>' : '-') + '</td>' +
      '<td class="col-ah-prem">' + (r.ah_premium != null ? '<span class="ah-prem ' + (r.ah_premium >= 0 ? 'pos' : 'neg') + '">H/A:' + (r.ah_premium >= 0 ? '+' : '') + r.ah_premium + '%</span>' : '-') + '</td>' +
      '<td class="mv">' + Math.round(r.total_mv).toLocaleString('zh-CN') + '</td>' +
      '<td class="ytd-merged">' + ytdHtml(r.ytd_2024) + ' | ' + ytdHtml(r.ytd_2025) + ' | ' + ytdHtml(r.ytd_2026) + '</td>' +
      '<td>' + revHtml + '</td>' +
      '<td class="' + rateCls(r.gpr) + '">' + gprHtml + '</td>' +
      '<td class="' + npCls + '">' + npHtml + '</td>' +
      '<td class="' + rateCls(r.npm) + '">' + npmHtml + '</td>' +
      '</tr>');
  }}
  tbody.innerHTML = rows.join('');
  // Mobile card list
  renderMobileList(pd);
  document.getElementById('countBadge').textContent = filtered.length + ' 只';
  renderPg();
  updateFavStars();
  updateSanctionTags();
  updateSanctionRows();
}}

function renderMobileList(pd) {{
  var el = document.getElementById('mobileList');
  if (!el) return;
  var cards = [];
  for (var i = 0; i < pd.length; i++) {{
    var r = pd[i];
    var ah = ahStatus[r.ts_code] || '';
    var ahClass = ah === 'listed' ? ' ah-listed' : ah === 'announced' ? ' ah-announced' : ah === 'rumor' ? ' ah-rumor' : '';
    var ahTag = ah === 'listed' ? ' <span class="ah-tag listed">A+H</span>' : ah === 'announced' ? ' <span class="ah-tag announced">拟H股</span>' : ah === 'rumor' ? ' <span class="ah-tag rumor">Rumor</span>' : '';
    var ytd24 = r.ytd_2024 != null ? ytdHtml(r.ytd_2024) : '<span class="pending">-</span>';
    var ytd25 = r.ytd_2025 != null ? ytdHtml(r.ytd_2025) : '<span class="pending">-</span>';
    var ytd26 = r.ytd_2026 != null ? ytdHtml(r.ytd_2026) : '<span class="pending">-</span>';
    cards.push(
      '<div class="mobile-card' + ahClass + '" data-code="' + r.ts_code + '">' +
        '<div style="display:flex;align-items:center;gap:4px;margin-bottom:4px">' +
          '<span class="fav-star off" data-code="' + r.ts_code + '">\u2606</span>' +
          '<span class="mc-rank">' + r._rank + '</span>' +
        '</div>' +
        '<div class="mc-top">' +
          '<div class="mc-name" style="display:flex;align-items:center;gap:4px;flex-wrap:wrap">' + r.name + '</div>' +
          '<div class="mc-mv">' + Math.round(r.total_mv).toLocaleString('zh-CN') + '亿</div>' +
        '</div>' +
        '<div class="mc-ah-status" style="margin:4px 0;font-size:12px;color:#555;display:flex;gap:8px;flex-wrap:wrap">' +
          '<span class="mc-ah-status-item">' + ahTag + '</span>' +
          '<span class="mc-ah-status-item">' + '<span class="sanction-tag ' + (defaultSanction.hasOwnProperty(r.ts_code) ? 'on' : 'off') + '" data-code="' + r.ts_code + '">★</span>' + '</span>' +
          '<span class="mc-ah-status-item">' + (r.hk_list_date ? 'H'+r.hk_list_date : '-') + '</span>' +
          '<span class="mc-ah-status-item">' + (r.ah_premium != null ? '<span class="ah-prem ' + (r.ah_premium >= 0 ? 'pos' : 'neg') + '">H/A:' + (r.ah_premium >= 0 ? '+' : '') + r.ah_premium + '%</span>' : '-') + '</span>' +
        '</div>' +
        '<div class="mc-info">' +
          '<span class="code">' + r.ts_code + '</span>' +
          (r.hk_code ? '<span class="hk-code-m">' + r.hk_code + '.HK</span>' : '') +
          '<span>' + (r.industry || '-') + '</span>' +
        '</div>' +
        (r.business_desc ? '<div class="biz-col" style="margin-top:4px">' + r.business_desc + '</div>' : '') +
        '<div class="mc-ytd-merged">' + ytd24 + ' | ' + ytd25 + ' | ' + ytd26 + '</div>' +
        (r.revenue != null || r.net_profit != null ? '<div class="mc-fin">' +
          (r.revenue != null ? '<span>营收' + numfmt(r.revenue, 0) + '亿</span>' : '') +
          (r.net_profit != null ? '<span>净利' + numfmt(r.net_profit, 0) + '亿</span>' : '') +
          (r.gpr != null ? '<span>毛利' + Math.round(r.gpr) + '%</span>' : '') +
        '</div>' : '') +
      '</div>'
    );
  }}
  el.innerHTML = cards.join('');
}}

function toggleView() {{
  var body = document.body;
  var isMobile = body.classList.toggle('mobile');
  document.getElementById('viewIcon').textContent = isMobile ? '💻' : '📱';
  document.getElementById('viewLabel').textContent = isMobile ? '桌面版' : '手机版';
  curPage = 1;
  render();
}}

function handleMobileClick(e) {{
  if (e.target.classList.contains('fav-star')) {{
    e.stopPropagation();
    toggleFav(e.target.getAttribute('data-code'));
    return;
  }}
  if (e.target.classList.contains('sanction-tag')) {{
    e.stopPropagation();
    toggleSanction(e.target.getAttribute('data-code'));
    return;
  }}
  var card = e.target.closest('.mobile-card');
  if (!card) return;
  var code = card.getAttribute('data-code');
  if (code) openModal(code);
}}

function renderPg() {{
  var total = Math.ceil(filtered.length / PAGE_SIZE);
  var el = document.getElementById('pagination');
  if (total <= 1) {{ el.innerHTML = ''; return; }}
  var isMobile = document.body.classList.contains('mobile');
  // 预计算每页最大市值（filtered已按当前排序）
  var pageMv = [];
  for (var pi = 0; pi < total; pi++) {{
    var first = filtered[pi * PAGE_SIZE];
    pageMv.push(first ? Math.round(first.total_mv) : 0);
  }}
  function mvLabel(p) {{
    var v = pageMv[p - 1];
    return v >= 10000 ? (v / 10000).toFixed(1) + '\u4e07\u4ebf' : v.toLocaleString() + '\u4ebf';
  }}
  if (isMobile) {{
    var mh = '';
    var mRng = [];
    for (var mi = 1; mi <= total; mi++) {{
      if (mi === 1 || mi === total || Math.abs(mi - curPage) <= 2) mRng.push(mi);
      else if (mRng[mRng.length-1] !== '..') mRng.push('..');
    }}
    for (var mj = 0; mj < mRng.length; mj++) {{
      var mp = mRng[mj];
      if (mp === '..') mh += '<span class="page-info">...</span>';
      else mh += '<div class="page-btn-wrap"><button class="page-btn ' + (mp===curPage?'active':'') + '" onclick="go(' + mp + ')">' + mp + '</button><div class="page-mv-label">' + mvLabel(mp) + '</div></div>';
    }}
    el.innerHTML = mh;
    return;
  }}
  var h = '<button class="page-btn" onclick="go(' + (curPage-1) + ')"' + (curPage===1?' disabled':'') + '>\u4e0a\u4e00\u9875</button>';
  var rng = [];
  for (var i = 1; i <= total; i++) {{
    if (i === 1 || i === total || Math.abs(i - curPage) <= 2) rng.push(i);
    else if (rng[rng.length-1] !== '..') rng.push('..');
  }}
  for (var j = 0; j < rng.length; j++) {{
    var p = rng[j];
    if (p === '..') h += '<span class="page-info">...</span>';
    else h += '<div class="page-btn-wrap"><button class="page-btn ' + (p===curPage?'active':'') + '" onclick="go(' + p + ')">' + p + '</button><div class="page-mv-label">' + mvLabel(p) + '</div></div>';
  }}
  h += '<button class="page-btn" onclick="go(' + (curPage+1) + ')"' + (curPage===total?' disabled':'') + '>\u4e0b\u4e00\u9875</button>';
  h += '<span class="page-info">' + curPage + '/' + total + '\u9875</span>';
  h += '<div class="goto-wrap"><span class="page-info">\u8df3\u8f6c</span><input type="number" class="goto-input" id="gotoInput" min="1" max="' + total + '" placeholder="' + curPage + '"><button class="page-btn goto-btn" onclick="goToPage()">Go</button></div>';
  el.innerHTML = h;
  var gInput = document.getElementById('gotoInput');
  if (gInput) gInput.addEventListener('keydown', function(e) {{ if (e.key === 'Enter') goToPage(); }});
}}

function goToPage() {{
  var v = parseInt(document.getElementById('gotoInput').value);
  var t = Math.ceil(filtered.length / PAGE_SIZE);
  if (isNaN(v) || v < 1 || v > t) return;
  go(v);
}}

function go(p) {{
  var t = Math.ceil(filtered.length / PAGE_SIZE);
  if (p < 1 || p > t) return;
  curPage = p;
  render();
  var wrap = document.querySelector('.table-wrap');
  if (wrap) wrap.scrollTop = 0;
  window.scrollTo({{top: 0, behavior: 'smooth'}});
}}

function filterData() {{
  var q = document.getElementById('searchInput').value.toLowerCase();
  var ind = document.getElementById('industryFilter').value;
  var mvVal = document.getElementById('mvFilter').value;
  var ahVal = document.getElementById('ahFilter').value;
  var scVal = document.getElementById('sanctionFilter').value;
  var soeVal = document.getElementById('soeFilter').value;

  // Parse mv filter value (supports ranges like "100-200" and single values)
  var mvMin = 0, mvMax = Infinity;
  if (mvVal.indexOf('-') > 0) {{
    var parts = mvVal.split('-');
    mvMin = +parts[0];
    mvMax = +parts[1];
  }} else if (+mvVal > 0) {{
    mvMin = +mvVal;
  }}

  var isFiltered = !!(q || ind || mvVal !== '0' || ahVal || scVal || soeVal || hkNewOn);

  // Filter first, then check if current page is out of range
  filtered = allData.filter(function(r) {{
    if (r.total_mv < mvMin || r.total_mv >= mvMax) return false;
    if (ind && r.industry !== ind) return false;
    if (ahVal) {{
      var s = ahStatus[r.ts_code] || '';
      if (ahVal === 'none') {{ if (s) return false; }}
      else {{ if (s !== ahVal) return false; }}
    }}
    if (scVal === 'exclude' && isSanctioned(r.ts_code)) return false;
    if (soeVal === 'exclude' && isSOE(r.ts_code)) return false;
    if (hkNewOn) {{
      var s = ahStatus[r.ts_code] || '';
      if (s !== 'listed') return false;
    }}
    if (q) {{
      var t = (r.ts_code + r.name + (r.industry || '')).toLowerCase();
      if (t.indexOf(q) === -1) return false;
    }}
    return true;
  }});
  // Reset sort to default (market cap descending) unless hkNewOn
  if (hkNewOn) {{
    sortKey = 'hk_list_date';
    sortDir = -1;
  }} else {{
    sortKey = 'total_mv';
    sortDir = -1;
  }}

  doSort();

  // Fix: if current page exceeds filtered results, reset to page 1
  var totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  if (curPage > totalPages) curPage = 1;

  render();
}}

function doSort() {{
  filtered.sort(function(a, b) {{
    if (sortKey === 'rank') return sortDir * (b.total_mv - a.total_mv);
    if (sortKey === 'hk_list_date') {{
      var va = a.hk_list_date || '', vb = b.hk_list_date || '';
      if (va && vb) return sortDir * va.localeCompare(vb);
      if (va) return -1;
      if (vb) return 1;
      return sortDir * (b.total_mv - a.total_mv);
    }}
    var va = a[sortKey], vb = b[sortKey];
    if (va == null && vb == null) return 0;
    if (va == null) return 1;
    if (vb == null) return -1;
    return sortDir * (va - vb);
  }});
}}

document.querySelectorAll('thead th[data-sort]').forEach(function(th) {{
  th.addEventListener('click', function() {{
    var k = this.dataset.sort;
    if (sortKey === k) sortDir *= -1;
    else {{ sortKey = k; sortDir = k === 'name' ? 1 : -1; }}
    curPage = 1;
    doSort();
    render();
  }});
}});

document.getElementById('stockTableBody').addEventListener('click', function(e) {{
  if (e.target.classList.contains('fav-star')) {{
    e.stopPropagation();
    toggleFav(e.target.getAttribute('data-code'));
    return;
  }}
  if (e.target.classList.contains('sanction-tag')) {{
    e.stopPropagation();
    toggleSanction(e.target.getAttribute('data-code'));
    return;
  }}
  var tr = e.target.closest('tr');
  if (!tr) return;
  var code = tr.getAttribute('data-code');
  if (code) openModal(code);
}});

document.getElementById('searchInput').addEventListener('input', filterData);
document.getElementById('industryFilter').addEventListener('change', filterData);
document.getElementById('mvFilter').addEventListener('change', filterData);
document.getElementById('ahFilter').addEventListener('change', filterData);
document.getElementById('sanctionFilter').addEventListener('change', filterData);
document.getElementById('soeFilter').addEventListener('change', filterData);
document.getElementById('filterHkNew').addEventListener('click', function() {{
  hkNewOn = !hkNewOn;
  if (hkNewOn) {{
    sortKey = 'hk_list_date';
    sortDir = -1;
  }} else {{
    sortKey = 'rank';
    sortDir = -1;
  }}
  var btn = document.getElementById('filterHkNew');
  btn.style.background = hkNewOn ? '#e0f2fe' : '#fff';
  btn.style.borderColor = hkNewOn ? '#0d9488' : '#ddd';
  btn.style.color = hkNewOn ? '#0d9488' : '#333';
  curPage = 1;
  filterData();
}});

document.getElementById('clearFilters').addEventListener('click', function() {{
  document.getElementById('searchInput').value = '';
  document.getElementById('industryFilter').value = '';
  document.getElementById('mvFilter').value = '0';
  document.getElementById('ahFilter').value = '';
  document.getElementById('sanctionFilter').value = '';
  document.getElementById('soeFilter').value = '';
  hkNewOn = false;
  var hkBtn = document.getElementById('filterHkNew');
  hkBtn.style.background = '#fff';
  hkBtn.style.borderColor = '#ddd';
  hkBtn.style.color = '#333';
  sortKey = 'total_mv';
  sortDir = -1;
  curPage = 1;
  filterData();
}});
function openModal(tsCode) {{
  var stock = null;
  for (var i = 0; i < allData.length; i++) {{
    if (allData[i].ts_code === tsCode) {{ stock = allData[i]; break; }}
  }}
  if (!stock) return;

  var hkCode = stock.hk_code || '';
  document.getElementById('modalTitle').textContent = stock.name + '\uff08' + tsCode + (hkCode ? ' / ' + hkCode + '.HK' : '') + '\uff09';
  var subText = stock.industry;
  if (stock.industry_l1 && stock.industry_l1 !== stock.industry) {{
    subText += '  |  ' + stock.industry_l1;
  }}
  if (stock.ah_premium != null) {{
    subText += '  |  H/A\u6ea2\u4ef7 ' + (stock.ah_premium >= 0 ? '+' : '') + stock.ah_premium + '%';
  }}
  if (isSanctioned(tsCode)) {{
    subText += '  |  \u26d4 ' + getSanctionLabel(tsCode);
  }}
  document.getElementById('modalSub').textContent = subText;
  var peStr = stock.pe ? stock.pe : '-';
  var pbStr = stock.pb ? stock.pb : '-';
  document.getElementById('modalPrice').innerHTML = '\u6536\u76d8\u4ef7: <b>' + stock.close.toFixed(2) + '</b> \u00b7 \u603b\u5e02\u503c: <b style="color:#c0392b">' + stock.total_mv.toLocaleString() + '\u4ebf</b> \u00b7 PE: ' + peStr + ' \u00b7 PB: ' + pbStr;
  document.getElementById('modalOverlay').classList.add('active');

  var html = '';

  // Company Profile
  html += '<div class="modal-section"><h3>📋 公司简介</h3>';
  html += '<div class="profile-box">';
  if (stock.list_date) {{
    html += '<div class="info-row"><span class="label">\u4e0a\u5e02\u65e5\u671f\uff1a</span>' + stock.list_date + '</div>';
  }}
  if (stock.area) {{
    html += '<div class="info-row"><span class="label">\u6240\u5c5e\u5730\u57df\uff1a</span>' + stock.area + '</div>';
  }}
  if (stock.business_desc) {{
    html += '<div class="desc"><span class="label">\u4e3b\u8425\u4e1a\u52a1\uff1a</span>' + stock.business_desc + '</div>';
  }}
  // 产品构成
  if (stock.products && stock.products.length > 0) {{
    html += '<div class="biz-detail">';
    html += '<div class="biz-title">\u4ea7\u54c1\u6536\u5165\u6784\u6210</div>';
    for (var pi = 0; pi < stock.products.length; pi++) {{
      var p = stock.products[pi];
      html += '<div class="biz-row"><span class="biz-name">' + p[0] + '</span><span class="biz-rev">' + Number(p[1]).toLocaleString() + '\u4ebf</span><span class="biz-pct">' + p[2].toFixed(1) + '%</span></div>';
    }}
    html += '</div>';
  }}
  // 地区构成
  if (stock.regions && stock.regions.length > 0) {{
    html += '<div class="biz-detail">';
    html += '<div class="biz-title">\u5730\u533a\u6536\u5165\u6784\u6210</div>';
    for (var ri = 0; ri < stock.regions.length; ri++) {{
      var rg = stock.regions[ri];
      html += '<div class="biz-row"><span class="biz-name">' + rg[0] + '</span><span class="biz-rev">' + Number(rg[1]).toLocaleString() + '\u4ebf</span><span class="biz-pct">' + rg[2].toFixed(1) + '%</span></div>';
    }}
    html += '</div>';
  }}
  html += '</div></div>';

  // YTD Performance
  html += '<div class="modal-section"><h3>📈 年度涨跌幅（年初至最新截止日）</h3>';
  html += '<div class="ytd-grid">';
  html += ytdCard('2024至今', stock.ytd_2024);
  html += ytdCard('2025至今', stock.ytd_2025);
  html += ytdCard('2026至今', stock.ytd_2026);
  html += '</div></div>';

  // Finance cards
  html += '<div class="modal-section"><h3>💰 2025年年报财务数据</h3><div class="finance-grid">';
  html += fi('\u8425\u4e1a\u6536\u5165', stock.revenue, '\u4ebf', 'red');
  html += fi('\u6bdb\u5229\u6da6', stock.gross_profit, '\u4ebf', 'blue');
  html += fi('\u6bdb\u5229\u7387', stock.gpr, '%', 'green');
  html += fi('\u5f52\u6bcd\u51c0\u5229\u6da6', stock.net_profit, '\u4ebf', stock.net_profit >= 0 ? 'red' : 'green');
  html += fi('\u51c0\u5229\u7387', stock.npm, '%', 'green');
  html += '</div></div>';

  // MV history chart
  html += '<div class="modal-section"><h3>📈 总市值走势（近5年 · 月度采样）</h3>';
  var mv = stock.mv_history;
  if (mv && mv.dates && mv.dates.length > 2) {{
    html += '<div id="chartBox"></div>';
    document.getElementById('modalBody').innerHTML = html;
    renderMVChart(mv, stock.name);
  }} else {{
    html += '<p style="color:#888;text-align:center;padding:20px">\u6682\u65e0\u8db3\u591f\u7684\u5386\u53f2\u5e02\u503c\u6570\u636e</p>';
    document.getElementById('modalBody').innerHTML = html;
  }}
}}

function ytdCard(label, val) {{
  if (val == null) return '<div class="ytd-card"><div class="year">' + label + '</div><div class="val" style="color:#bbb">-</div></div>';
  var color = val > 0 ? '#c0392b' : val < 0 ? '#27ae60' : '#333';
  var txt = (val > 0 ? '+' : '') + Math.round(val) + '%';
  return '<div class="ytd-card"><div class="year">' + label + '</div><div class="val" style="color:' + color + '">' + txt + '</div></div>';
}}

function fi(label, val, unit, cls) {{
  var v = val != null ? ((typeof val === 'number' ? Math.round(val).toLocaleString('zh-CN') : val) + unit) : '<span class="no-report">\u6682\u65e0\u5e74\u62a5</span>';
  return '<div class="finance-item"><div class="fl">' + label + '</div><div class="fv ' + cls + '">' + v + '</div></div>';
}}

function renderMVChart(mv, name) {{
  var el = document.getElementById('chartBox');
  if (!el) return;
  if (typeof echarts === 'undefined') {{
    el.innerHTML = '<p style="color:#888;text-align:center;padding:20px">ECharts\u672a\u52a0\u8f7d\uff0c\u65e0\u6cd5\u663e\u793a\u56fe\u8868</p>';
    return;
  }}
  var chart = echarts.init(el);
  var points = [];
  for (var i = 0; i < mv.dates.length; i++) {{
    points.push([mv.dates[i], mv.mv[i]]);
  }}
  var minMV = Math.min.apply(null, mv.mv) * 0.9;
  var maxMV = Math.max.apply(null, mv.mv) * 1.1;
  var currentMV = points[points.length - 1][1];

  chart.setOption({{
    backgroundColor: '#fff',
    title: {{text: name + ' \u603b\u5e02\u503c\u8d70\u52bf', left: 'center', textStyle: {{fontSize: 16, color: '#333'}}}},
    tooltip: {{
      trigger: 'axis',
      formatter: function(p) {{
        if (!p || p.length === 0) return '';
        return p[0].name + '<br/>\u603b\u5e02\u503c: <b>' + Number(p[0].value[1]).toLocaleString() + ' \u4ebf</b>';
      }}
    }},
    grid: {{left: '10%', right: '5%', top: '15%', bottom: '25%'}},
    xAxis: {{type: 'category', data: mv.dates, axisLabel: {{fontSize: 11, rotate: 30, margin: 12}}}},
    yAxis: {{type: 'value', min: minMV, max: maxMV, name: '\u5e02\u503c\uff08\u4ebf\uff09',
      axisLabel: {{fontSize: 11, formatter: function(v) {{ return v >= 10000 ? (v/10000).toFixed(1) + '\u4e07' : v.toLocaleString(); }}}}}},
    dataZoom: [{{type: 'inside', start: 60, end: 100}}, {{type: 'slider', bottom: 2, height: 20, start: 60, end: 100}}],
    series: [{{
      type: 'line', data: points, smooth: true,
      lineStyle: {{color: '#4338ca', width: 2}},
      areaStyle: {{color: {{type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
        colorStops: [{{offset: 0, color: 'rgba(67,56,202,0.15)'}}, {{offset: 1, color: 'rgba(67,56,202,0.01)'}}]
      }}}},
      symbol: 'none',
      markPoint: {{data: [{{type: 'max', name: '\u6700\u9ad8'}}, {{type: 'min', name: '\u6700\u4f4e'}}], symbolSize: 50}},
      markLine: {{data: [{{yAxis: currentMV, name: '\u5f53\u524d', label: {{formatter: '\u5f53\u524d: {{c}} \u4ebf', fontSize: 11}}, lineStyle: {{color: '#c0392b', type: 'dashed'}}}}], symbol: 'none'}}
    }}]
  }});
  window.addEventListener('resize', function() {{ chart.resize(); }});
}}

// Close modal
document.getElementById('modalClose').addEventListener('click', function() {{ document.getElementById('modalOverlay').classList.remove('active'); }});
document.getElementById('modalOverlay').addEventListener('click', function(e) {{ if (e.target === e.currentTarget) e.currentTarget.classList.remove('active'); }});
document.addEventListener('keydown', function(e) {{ if (e.key === 'Escape') document.getElementById('modalOverlay').classList.remove('active'); }});

// Init view toggle button on page load
(function(){{
  // Auto-detect mobile on page load
  if (window.innerWidth < 768 || /Android|iPhone|iPad|iPod/i.test(navigator.userAgent)) {{
    document.body.classList.add('mobile');
  }}
  var isMb = document.body.classList.contains('mobile');
  var icon = document.getElementById('viewIcon');
  var label = document.getElementById('viewLabel');
  if (icon) icon.textContent = isMb ? '💻' : '📱';
  if (label) label.textContent = isMb ? '桌面版' : '手机版';
  // 自动检测为手机版时绑定点击事件（toggleView中也会绑，这里补上初始加载的情况）
  if (isMb) {{
    document.getElementById('mobileList').addEventListener('click', handleMobileClick);
  }}
}})();

// ========== keke自选股 ==========
var WL_KEY = 'keke_watchlist';
var watchlist = [];

// 从localStorage加载自选股
function loadWatchlist() {{
  try {{
    var raw = localStorage.getItem(WL_KEY);
    watchlist = raw ? JSON.parse(raw) : [];
  }} catch(e) {{ watchlist = []; }}
  return watchlist;
}}
loadWatchlist();

// 切换收藏
function toggleFav(tsCode) {{
  var idx = watchlist.indexOf(tsCode);
  if (idx >= 0) {{
    watchlist.splice(idx, 1);
  }} else {{
    watchlist.push(tsCode);
  }}
  localStorage.setItem(WL_KEY, JSON.stringify(watchlist));
  updateFavStars();
}}

// 更新所有⭐按钮状态
function updateFavStars() {{
  var stars = document.querySelectorAll('.fav-star');
  for (var i = 0; i < stars.length; i++) {{
    var s = stars[i];
    var code = s.getAttribute('data-code');
    if (watchlist.indexOf(code) >= 0) {{
      s.textContent = '\u2b50';
      s.className = 'fav-star on';
    }} else {{
      s.textContent = '\u2606';
      s.className = 'fav-star off';
    }}
  }}
}}

// ========== 美国制裁清单标注 ==========
var SC_KEY = 'keke_sanction_list';
var sanctionList = [];

function loadSanctionList() {{
  try {{
    var raw = localStorage.getItem(SC_KEY);
    var local = raw ? JSON.parse(raw) : [];
    // sanctionList only stores user-toggled codes (not in defaultSanction)
    sanctionList = [];
    for (var i = 0; i < local.length; i++) {{
      if (!defaultSanction.hasOwnProperty(local[i])) {{
        sanctionList.push(local[i]);
      }}
    }}
  }} catch(e) {{ sanctionList = []; }}
  return sanctionList;
}}
loadSanctionList();

function isSanctioned(tsCode) {{
  return defaultSanction.hasOwnProperty(tsCode) || sanctionList.indexOf(tsCode) >= 0;
}}

function getSanctionLabel(tsCode) {{
  if (defaultSanction.hasOwnProperty(tsCode)) {{
    var tags = defaultSanction[tsCode];
    var hasNS = tags.indexOf('NS-CMIC') >= 0;
    var hasEL = tags.indexOf('Entity List') >= 0;
    if (hasNS && hasEL) return 'NS-CMIC+EL';
    if (hasNS) return 'NS-CMIC';
    if (hasEL) return 'Entity List';
    return tags.join('+');
  }}
  if (sanctionList.indexOf(tsCode) >= 0) return 'US\\u5236\\u88c1';
  return '';
}}

function isSOE(tsCode) {{
  return defaultSOE.indexOf(tsCode) >= 0;
}}

function toggleSanction(tsCode) {{
  // Cannot toggle off defaultSanction companies (they are always shown)
  if (defaultSanction.hasOwnProperty(tsCode)) return;
  var idx = sanctionList.indexOf(tsCode);
  if (idx >= 0) {{
    sanctionList.splice(idx, 1);
  }} else {{
    sanctionList.push(tsCode);
  }}
  localStorage.setItem(SC_KEY, JSON.stringify(sanctionList));
  updateSanctionTags();
  updateSanctionRows();
}}

function updateSanctionTags() {{
  var tags = document.querySelectorAll('.sanction-tag');
  for (var i = 0; i < tags.length; i++) {{
    var t = tags[i];
    var code = t.getAttribute('data-code');
    if (isSanctioned(code)) {{
      t.textContent = getSanctionLabel(code);
      t.className = 'sanction-tag on';
    }} else {{
      t.textContent = '\\u26d4';
      t.className = 'sanction-tag off';
    }}
  }}
}}

function updateSanctionRows() {{
  var rows = document.querySelectorAll('tr[data-code]');
  for (var i = 0; i < rows.length; i++) {{
    var code = rows[i].getAttribute('data-code');
    if (isSanctioned(code)) {{
      rows[i].classList.add('sanction-row');
    }} else {{
      rows[i].classList.remove('sanction-row');
    }}
  }}
  var cards = document.querySelectorAll('.mobile-card[data-code]');
  for (var i = 0; i < cards.length; i++) {{
    var code = cards[i].getAttribute('data-code');
    if (isSanctioned(code)) {{
      cards[i].classList.add('sanction-row');
    }} else {{
      cards[i].classList.remove('sanction-row');
    }}
  }}
}}

try {{
  filterData();
  document.getElementById('jsError').style.display = 'none';
}} catch(e) {{
  document.getElementById('jsError').style.display = 'block';
  document.getElementById('jsError').textContent = 'Render Error: ' + e.message;
}}
</script>
</body>
</html>"""

output_path = f'{DATA_DIR}/A股市值超200亿名单_{trade_date}.html'
with open(output_path, 'wb') as f:
    f.write(b'\xef\xbb\xbf')
    f.write(html.encode('utf-8'))

# Also save as ashare.html for GitHub Pages
index_path = f'{DATA_DIR}/ashare.html'
with open(index_path, 'wb') as f:
    f.write(b'\xef\xbb\xbf')
    f.write(html.encode('utf-8'))

file_size = len(html.encode('utf-8')) / (1024 * 1024)
print(f'Done! {len(results)} stocks')
print(f'HTML size: {file_size:.2f} MB')
print(f'Saved to: {output_path}')
print(f'Index: {index_path}')
