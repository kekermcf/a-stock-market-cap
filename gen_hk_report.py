"""Generate hongkong.html - HK stock page (teal theme)"""
import json, os, glob

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(DATA_DIR, 'cache')

# Auto-detect latest trade date from HK cache
mv_files = sorted(glob.glob(f'{CACHE_DIR}/hk_data_*.json'))
if mv_files:
    trade_date = os.path.basename(mv_files[-1]).replace('hk_data_', '').replace('.json', '')
else:
    from datetime import datetime, timedelta
    d = datetime.now()
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    trade_date = d.strftime('%Y%m%d')

date_display = f'{trade_date[:4]}年{int(trade_date[4:6])}月{int(trade_date[6:8])}日'

# Load HK stock data
with open(f'{CACHE_DIR}/hk_data_{trade_date}.json', 'r', encoding='utf-8') as f:
    stocks = json.load(f)

print(f'Loaded {len(stocks)} HK stocks')

# Industry stats
industry_stats = {}
for r in stocks:
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
total_stocks = len(stocks)
max_mv = f"{stocks[0]['total_mv']:,.0f}" if stocks else "0"
avg_mv = f"{sum(r['total_mv'] for r in stocks)/len(stocks):,.0f}" if stocks else "0"
med_mv = f"{stocks[len(stocks)//2]['total_mv']:,.0f}" if stocks else "0"

rj = json.dumps(stocks, ensure_ascii=True)

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>港股市值超250亿股票名单（{trade_date}）</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;background:#f5f7fa;color:#333}}
.header{{background:linear-gradient(135deg,#0f172a 0%,#134e4a 50%,#0d9488 100%);color:#fff;padding:32px 24px;text-align:center}}
.header h1{{font-size:28px;margin-bottom:8px}}
.header .date{{font-size:14px;opacity:.8}}
.header .method{{font-size:12px;opacity:.6;margin-top:4px}}
.container{{max-width:1500px;margin:0 auto 40px;padding:0 24px}}
.section{{background:#fff;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,.06);margin-bottom:24px;overflow:hidden}}
.section-title{{font-size:18px;font-weight:600;padding:16px 20px;border-bottom:1px solid #eee;display:flex;align-items:center;gap:8px}}
.controls{{padding:16px 20px;border-bottom:1px solid #eee;display:flex;gap:12px;flex-wrap:wrap;align-items:center}}
.search-box{{flex:1;min-width:200px;padding:10px 16px;border:1px solid #ddd;border-radius:8px;font-size:14px;outline:none}}
.search-box:focus{{border-color:#0d9488}}
select{{padding:10px 16px;border:1px solid #ddd;border-radius:8px;font-size:14px;background:#fff;cursor:pointer}}
.badge{{display:inline-block;background:#ccfbf1;color:#0d9488;padding:2px 10px;border-radius:12px;font-size:13px;font-weight:500}}
table{{width:100%;border-collapse:collapse;font-size:14px}}
thead th{{background:#f8f9fa;padding:12px 8px;text-align:right;font-weight:600;color:#555;font-size:13px;position:sticky;top:0;cursor:pointer;user-select:none;white-space:nowrap;z-index:2}}
thead th:nth-child(1),thead th:nth-child(2),thead th:nth-child(3),thead th:nth-child(4){{text-align:left}}
thead th:hover{{background:#ccfbf1}}
tbody tr{{border-bottom:1px solid #f0f0f0;transition:background .15s;cursor:pointer}}
tbody tr:hover{{background:#f0fdfa}}
tbody td{{padding:10px 8px;white-space:nowrap;text-align:right}}
tbody td:nth-child(1),tbody td:nth-child(2),tbody td:nth-child(3),tbody td:nth-child(4){{text-align:left}}
.code{{font-family:'SF Mono','Consolas',monospace;font-size:13px;color:#666}}
.mv{{font-weight:600;color:#c0392b}}
.chg-up{{color:#c0392b;font-weight:500}}
.chg-dn{{color:#27ae60;font-weight:500}}
.fin-pos{{color:#c0392b;font-weight:500}}
.fin-neg{{color:#27ae60}}
.rate-pos{{color:#27ae60}}
.rate-neg{{color:#c0392b}}
.rate-val{{color:#0d9488;font-weight:500}}
.pending{{color:#bbb;font-style:italic;font-size:12px}}
.no-report{{color:#999;font-size:11px}}
.table-wrap{{max-height:700px;overflow-y:auto}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin:24px 0}}
.stat-card{{background:#fff;border-radius:12px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,.06)}}
.stat-card .label{{font-size:13px;color:#888;margin-bottom:6px}}
.stat-card .value{{font-size:28px;font-weight:700;color:#0f172a}}
.stat-card .value.red{{color:#c0392b}}
.stat-card .value.teal{{color:#0d9488}}
.industry-section{{max-height:500px;overflow-y:auto}}
.ind-row{{display:flex;justify-content:space-between;padding:10px 20px;border-bottom:1px solid #f0f0f0;align-items:center}}
.ind-row:hover{{background:#f0fdfa}}
.ind-name{{font-weight:500;min-width:120px;font-size:13px}}
.ind-bar-wrap{{flex:1;max-width:400px;margin:0 20px;align-self:center}}
.ind-bar{{height:8px;background:#ccfbf1;border-radius:4px;overflow:hidden}}
.ind-bar-fill{{height:100%;background:linear-gradient(90deg,#0d9488,#2dd4bf);border-radius:4px;transition:width .3s}}
.ind-count{{color:#888;font-size:13px;min-width:50px;text-align:right}}
.ind-mv{{font-weight:600;color:#c0392b;min-width:100px;text-align:right;font-size:13px}}
.pagination{{padding:8px 20px 14px;display:flex;justify-content:flex-start;align-items:flex-start;gap:6px;flex-wrap:wrap;border-bottom:1px solid #eee;margin-bottom:2px}}
.page-btn{{padding:6px 14px;border:1px solid #ddd;border-radius:6px;background:#fff;cursor:pointer;font-size:13px}}
.page-btn:hover{{background:#f0f0f0}}
.page-btn.active{{background:#0f172a;color:#fff;border-color:#0f172a}}
.page-info{{font-size:13px;color:#888}}
.page-btn-wrap{{display:inline-flex;flex-direction:column;align-items:center;gap:2px}}
.page-mv-label{{font-size:10px;color:#999;line-height:1}}
.goto-wrap{{display:inline-flex;align-items:center;gap:4px;margin-left:8px}}
.goto-input{{width:48px;padding:4px 6px;border:1px solid #ddd;border-radius:6px;font-size:13px;text-align:center;outline:none}}
.goto-input:focus{{border-color:#0d9488}}
.goto-btn{{padding:4px 10px;font-size:12px}}
.modal-overlay{{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.5);z-index:1000;justify-content:center;align-items:center}}
.modal-overlay.active{{display:flex}}
.modal{{background:#fff;border-radius:16px;width:94%;max-width:1000px;max-height:92vh;overflow-y:auto;box-shadow:0 20px 60px rgba(0,0,0,.3);position:relative}}
.modal-header{{padding:24px 28px 16px;border-bottom:1px solid #eee;display:flex;justify-content:space-between;align-items:flex-start}}
.modal-header h2{{font-size:22px;color:#0f172a}}
.modal-header .sub{{font-size:14px;color:#888;margin-top:4px}}
.modal-header .price-info{{font-size:13px;margin-top:6px}}
.modal-close{{width:36px;height:36px;border:none;background:#f0f0f0;border-radius:50%;font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center;color:#666;flex-shrink:0}}
.modal-close:hover{{background:#e0e0e0}}
.modal-body{{padding:24px 28px}}
.modal-section{{margin-bottom:24px}}
.modal-section h3{{font-size:16px;font-weight:600;color:#0f172a;margin-bottom:12px;padding-bottom:8px;border-bottom:2px solid #ccfbf1}}
.finance-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px}}
.finance-item{{background:#f8f9fa;border-radius:10px;padding:14px}}
.finance-item .fl{{font-size:12px;color:#888;margin-bottom:4px}}
.finance-item .fv{{font-size:18px;font-weight:700;color:#0f172a}}
.finance-item .fv.red{{color:#c0392b}}
.finance-item .fv.green{{color:#27ae60}}
.finance-item .fv.teal{{color:#0d9488}}
#chartBox{{width:100%;height:420px}}
.ytd-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:12px}}
.ytd-card{{text-align:center;padding:12px;border-radius:10px;background:#f8f9fa}}
.ytd-card .year{{font-size:13px;color:#888;margin-bottom:4px}}
.ytd-card .val{{font-size:22px;font-weight:700}}
.data-source{{font-size:11px;color:#aaa;text-align:center;margin-top:8px}}
.view-toggle{{background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.3);color:#fff;padding:8px 14px;border-radius:8px;cursor:pointer;font-size:13px;white-space:nowrap;transition:background .2s;display:flex;align-items:center;gap:6px}}
.view-toggle:hover{{background:rgba(255,255,255,.25)}}
/* Mobile */
body.mobile .container{{padding:0 12px}}
body.mobile .header h1{{font-size:20px}}
body.mobile .header .method{{display:none}}
body.mobile .controls{{padding:10px 12px;gap:8px;flex-wrap:wrap}}
body.mobile .search-box{{min-width:0;font-size:16px;flex:0 0 100%}}
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
body.mobile .modal-header{{padding:16px;position:sticky;top:0;background:#fff;z-index:10}}
body.mobile .modal-body{{padding:16px}}
body.mobile .finance-grid{{grid-template-columns:repeat(2,1fr)}}
body.mobile #chartBox{{height:300px}}
body.mobile .section-title{{font-size:16px;padding:12px 16px}}
body.mobile .modal-close{{width:44px;height:44px;font-size:22px}}
.mobile-list{{display:none}}
.mobile-card{{background:#fff;border-radius:10px;padding:14px 16px;margin-bottom:10px;box-shadow:0 1px 4px rgba(0,0,0,.06);cursor:pointer;transition:box-shadow .2s}}
.mobile-card:hover{{box-shadow:0 2px 8px rgba(0,0,0,.12)}}
.mc-top{{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}}
.mc-name{{font-size:16px;font-weight:700;color:#0f172a}}
.mc-mv{{font-size:18px;font-weight:700;color:#c0392b}}
.mc-info{{display:flex;gap:16px;font-size:13px;color:#888;align-items:center}}
.mc-info span{{white-space:nowrap}}
.mc-info .code{{font-family:'SF Mono','Consolas',monospace;font-size:12px}}
.mc-ytd{{display:flex;gap:8px;margin-top:8px}}
.mc-ytd-item{{font-size:13px;white-space:nowrap}}
.mc-ytd-item .year-label{{color:#888;margin-right:2px}}
.mc-fin{{display:flex;gap:16px;margin-top:6px;font-size:12px;color:#666}}
.back-top{{display:none;width:100%;padding:14px 0;text-align:center;background:#f0f2f5;color:#555;font-size:15px;font-weight:600;border:none;cursor:pointer;border-radius:10px;margin-top:12px;letter-spacing:2px}}
body.mobile .back-top{{display:block}}
</style>
</head>
<body>
<div id="jsError" style="display:none;position:fixed;top:0;left:0;width:100%;padding:12px;background:#fee;color:#c00;z-index:9999;font-size:14px"></div>

<div class="header">
  <div style="display:flex;justify-content:space-between;align-items:flex-start">
    <div>
      <nav style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">
        <a href="index.html" style="color:rgba(255,255,255,.7);text-decoration:none;font-size:13px;padding:4px 10px;border-radius:6px;background:rgba(255,255,255,.1)">🏠 首页</a>
        <a href="ashare.html" style="color:rgba(255,255,255,.7);text-decoration:none;font-size:13px;padding:4px 10px;border-radius:6px;background:rgba(255,255,255,.1)">🇨🇳 A股</a>
        <a href="hongkong.html" style="color:#fff;text-decoration:none;font-size:13px;padding:4px 10px;border-radius:6px;background:rgba(13,148,136,.5);font-weight:600">🇭🇰 H股</a>
        <a href="watchlist.html" style="color:rgba(255,255,255,.7);text-decoration:none;font-size:13px;padding:4px 10px;border-radius:6px;background:rgba(255,255,255,.1)">⭐ 自选</a>
      </nav>
      <h1>港股市值超250亿股票名单</h1>
      <div class="date">数据截止：{date_display}（收盘）</div>
      <div class="method">数据来源：AKShare · QQ Finance K-line · 市值单位：亿港币 · 点击行查看详情</div>
    </div>
    <button id="viewToggle" class="view-toggle" onclick="toggleView()" title="切换手机版/桌面版">
      <span id="viewIcon">📱</span>
      <span id="viewLabel">手机版</span>
    </button>
  </div>
</div>

<div class="container">
  <div class="section">
    <div class="section-title">
      股票名单
      <span class="badge" id="countBadge">{total_stocks} 只</span>
      <span style="margin-left:auto;font-size:12px;color:#aaa;font-weight:400">点击公司行查看详情</span>
    </div>
    <div class="controls">
      <input type="text" class="search-box" id="searchInput" placeholder="搜索股票代码/名称/行业...">
      <select id="industryFilter"><option value="">全部行业</option>{ind_options}</select>
      <select id="mvFilter">
        <option value="0">全部市值</option>
        <option value="250">250亿以上</option>
        <option value="250-500">250-500亿</option>
        <option value="500-1000">500-1000亿</option>
        <option value="1000-3000">1000-3000亿</option>
        <option value="3000-5000">3000-5000亿</option>
        <option value="5000">5000亿以上</option>
      </select>
    </div>
    <div class="pagination" id="pagination"></div>
    <div class="table-wrap">
      <table>
        <thead><tr>
          <th data-sort="rank">排名</th>
          <th data-sort="code">代码</th>
          <th data-sort="name">名称</th>
          <th data-sort="industry">行业</th>
          <th data-sort="total_mv">总市值(亿港币)</th>
          <th data-sort="ytd_2024">2024至今</th>
          <th data-sort="ytd_2025">2025至今</th>
          <th data-sort="ytd_2026">2026至今</th>
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
    <div class="stat-card"><div class="label">市值超250亿港币股票总数</div><div class="value teal">{total_stocks}</div></div>
    <div class="stat-card"><div class="label">最大市值</div><div class="value red">{max_mv} 亿港币</div></div>
    <div class="stat-card"><div class="label">平均市值</div><div class="value">{avg_mv} 亿港币</div></div>
    <div class="stat-card"><div class="label">市值中位数</div><div class="value">{med_mv} 亿港币</div></div>
  </div>

  <div class="section">
    <div class="section-title">行业分布（市值Top 30）</div>
    <div class="industry-section">
{ind_bars}    </div>
  </div>

  <div class="data-source">数据来源：AKShare · QQ Finance K-line | 仅供参考，不构成投资建议</div>
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
var PAGE_SIZE = 60;
var filtered = allData.slice();
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
  var rows = [];
  for (var i = 0; i < pd.length; i++) {{
    var r = pd[i];
    var revHtml = r.revenue != null ? numfmt(r.revenue, 1) : '<span class="pending">暂无</span>';
    var gprHtml = r.gpr != null ? Math.round(r.gpr) + '%' : '<span class="pending">-</span>';
    var npHtml = r.net_profit != null ? numfmt(r.net_profit, 0) : '<span class="pending">暂无</span>';
    var npmHtml = r.npm != null ? Math.round(r.npm) + '%' : '<span class="pending">-</span>';
    var npCls = r.net_profit != null ? (r.net_profit >= 0 ? 'fin-pos' : 'fin-neg') : '';
    rows.push('<tr data-code="' + r.code + '">' +
      '<td>' + (i + s + 1) + '</td>' +
      '<td class="code">' + r.code + '.HK</td>' +
      '<td><b>' + r.name + '</b></td>' +
      '<td>' + (r.industry || '-') + '</td>' +
      '<td class="mv">' + Math.round(r.total_mv).toLocaleString('zh-CN') + '</td>' +
      '<td>' + ytdHtml(r.ytd_2024) + '</td>' +
      '<td>' + ytdHtml(r.ytd_2025) + '</td>' +
      '<td>' + ytdHtml(r.ytd_2026) + '</td>' +
      '<td>' + revHtml + '</td>' +
      '<td class="' + rateCls(r.gpr) + '">' + gprHtml + '</td>' +
      '<td class="' + npCls + '">' + npHtml + '</td>' +
      '<td class="' + rateCls(r.npm) + '">' + npmHtml + '</td>' +
      '</tr>');
  }}
  tbody.innerHTML = rows.join('');
  renderMobileList(pd);
  document.getElementById('countBadge').textContent = filtered.length + ' 只';
  renderPg();
}}

function renderMobileList(pd) {{
  var el = document.getElementById('mobileList');
  if (!el) return;
  var cards = [];
  for (var i = 0; i < pd.length; i++) {{
    var r = pd[i];
    var ytd24 = r.ytd_2024 != null ? ytdHtml(r.ytd_2024) : '<span class="pending">-</span>';
    var ytd25 = r.ytd_2025 != null ? ytdHtml(r.ytd_2025) : '<span class="pending">-</span>';
    var ytd26 = r.ytd_2026 != null ? ytdHtml(r.ytd_2026) : '<span class="pending">-</span>';
    cards.push(
      '<div class="mobile-card" data-code="' + r.code + '">' +
        '<div class="mc-top">' +
          '<div class="mc-name">' + (i+1) + '. ' + r.name + '</div>' +
          '<div class="mc-mv">' + Math.round(r.total_mv).toLocaleString('zh-CN') + '亿</div>' +
        '</div>' +
        '<div class="mc-info">' +
          '<span class="code">' + r.code + '.HK</span>' +
          '<span>' + (r.industry || '-') + '</span>' +
        '</div>' +
        '<div class="mc-ytd">' +
          '<div class="mc-ytd-item"><span class="year-label">24年初至今</span>' + ytd24 + '</div>' +
          '<div class="mc-ytd-item"><span class="year-label">25年初至今</span>' + ytd25 + '</div>' +
          '<div class="mc-ytd-item"><span class="year-label">YTD</span>' + ytd26 + '</div>' +
        '</div>' +
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
  var pageMv = [];
  for (var pi = 0; pi < total; pi++) {{
    var first = filtered[pi * PAGE_SIZE];
    pageMv.push(first ? Math.round(first.total_mv) : 0);
  }}
  function mvLabel(p) {{
    var v = pageMv[p - 1];
    return v >= 10000 ? (v / 10000).toFixed(1) + '万亿' : v.toLocaleString() + '亿';
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
  var h = '<button class="page-btn" onclick="go(' + (curPage-1) + ')"' + (curPage===1?' disabled':'') + '>上一页</button>';
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
  h += '<button class="page-btn" onclick="go(' + (curPage+1) + ')"' + (curPage===total?' disabled':'') + '>下一页</button>';
  h += '<span class="page-info">' + curPage + '/' + total + '页</span>';
  h += '<div class="goto-wrap"><span class="page-info">跳转</span><input type="number" class="goto-input" id="gotoInput" min="1" max="' + total + '" placeholder="' + curPage + '"><button class="page-btn goto-btn" onclick="goToPage()">Go</button></div>';
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
  var mvMin = 0, mvMax = Infinity;
  if (mvVal.indexOf('-') > 0) {{
    var parts = mvVal.split('-');
    mvMin = +parts[0]; mvMax = +parts[1];
  }} else if (+mvVal > 0) {{ mvMin = +mvVal; }}
  filtered = allData.filter(function(r) {{
    if (r.total_mv < mvMin || r.total_mv >= mvMax) return false;
    if (ind && r.industry !== ind) return false;
    if (q) {{
      var t = (r.code + r.name + (r.industry || '')).toLowerCase();
      if (t.indexOf(q) === -1) return false;
    }}
    return true;
  }});
  doSort();
  var totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  if (curPage > totalPages) curPage = 1;
  render();
}}

function doSort() {{
  filtered.sort(function(a, b) {{
    if (sortKey === 'rank') return sortDir * (b.total_mv - a.total_mv);
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

document.getElementById('searchInput').addEventListener('input', filterData);
document.getElementById('industryFilter').addEventListener('change', filterData);
document.getElementById('mvFilter').addEventListener('change', filterData);
document.getElementById('stockTableBody').addEventListener('click', function(e) {{
  var tr = e.target.closest('tr');
  if (!tr) return;
  var code = tr.getAttribute('data-code');
  if (code) openModal(code);
}});

// ========== Modal ==========
function openModal(code) {{
  var stock = null;
  for (var i = 0; i < allData.length; i++) {{
    if (allData[i].code === code) {{ stock = allData[i]; break; }}
  }}
  if (!stock) return;

  document.getElementById('modalTitle').textContent = stock.name + '（' + code + '.HK）';
  document.getElementById('modalSub').textContent = stock.industry || '-';
  var peStr = stock.pe ? stock.pe : '-';
  var pbStr = stock.pb ? stock.pb : '-';
  document.getElementById('modalPrice').innerHTML = '收盘价: <b>' + (stock.close ? stock.close.toFixed(2) : '-') + '</b> · 总市值: <b style="color:#c0392b">' + Math.round(stock.total_mv).toLocaleString() + '亿港币</b> · PE: ' + peStr + ' · PB: ' + pbStr;
  document.getElementById('modalOverlay').classList.add('active');

  var html = '';
  html += '<div class="modal-section"><h3>📈 年度涨跌幅</h3><div class="ytd-grid">';
  html += ytdCard('2024至今', stock.ytd_2024);
  html += ytdCard('2025至今', stock.ytd_2025);
  html += ytdCard('2026至今', stock.ytd_2026);
  html += '</div></div>';

  html += '<div class="modal-section"><h3>💰 财务数据</h3><div class="finance-grid">';
  html += fi('营业收入', stock.revenue, '亿', 'red');
  html += fi('毛利润', stock.gross_profit, '亿', 'teal');
  html += fi('毛利率', stock.gpr, '%', 'green');
  html += fi('净利润', stock.net_profit, '亿', stock.net_profit >= 0 ? 'red' : 'green');
  html += fi('净利率', stock.npm, '%', 'green');
  html += '</div></div>';

  document.getElementById('modalBody').innerHTML = html;
}}

function ytdCard(label, val) {{
  if (val == null) return '<div class="ytd-card"><div class="year">' + label + '</div><div class="val" style="color:#bbb">-</div></div>';
  var color = val > 0 ? '#c0392b' : val < 0 ? '#27ae60' : '#333';
  var txt = (val > 0 ? '+' : '') + Math.round(val) + '%';
  return '<div class="ytd-card"><div class="year">' + label + '</div><div class="val" style="color:' + color + '">' + txt + '</div></div>';
}}

function fi(label, val, unit, cls) {{
  var v = val != null ? ((typeof val === 'number' ? Math.round(val).toLocaleString('zh-CN') : val) + unit) : '<span class="no-report">暂无数据</span>';
  return '<div class="finance-item"><div class="fl">' + label + '</div><div class="fv ' + cls + '">' + v + '</div></div>';
}}

document.getElementById('modalClose').addEventListener('click', function() {{ document.getElementById('modalOverlay').classList.remove('active'); }});
document.getElementById('modalOverlay').addEventListener('click', function(e) {{ if (e.target === e.currentTarget) e.currentTarget.classList.remove('active'); }});
document.addEventListener('keydown', function(e) {{ if (e.key === 'Escape') document.getElementById('modalOverlay').classList.remove('active'); }});

// Init
(function(){{
  if (window.innerWidth < 768 || /Android|iPhone|iPad|iPod/i.test(navigator.userAgent)) {{
    document.body.classList.add('mobile');
  }}
  var isMb = document.body.classList.contains('mobile');
  var icon = document.getElementById('viewIcon');
  var label = document.getElementById('viewLabel');
  if (icon) icon.textContent = isMb ? '💻' : '📱';
  if (label) label.textContent = isMb ? '桌面版' : '手机版';
  if (isMb) {{
    document.getElementById('mobileList').addEventListener('click', handleMobileClick);
  }}
}})();

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

output_path = f'{DATA_DIR}/hongkong.html'
with open(output_path, 'wb') as f:
    f.write(b'\xef\xbb\xbf')
    f.write(html.encode('utf-8'))

file_size = len(html.encode('utf-8')) / (1024 * 1024)
print(f'Hong Kong report done! {total_stocks} stocks')
print(f'HTML size: {file_size:.2f} MB')
print(f'Saved to: {output_path}')
