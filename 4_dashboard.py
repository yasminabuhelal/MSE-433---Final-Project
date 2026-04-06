import pandas as pd
import json

print("Loading results...")
all_results = json.load(open('optimization_results.json'))
thresholds  = json.load(open('risk_thresholds.json'))
all_ints    = pd.read_csv('intersections_with_risk.csv')
print(f"Candidate pool: {len(all_results)} sites")

max_cost     = sum(r['cost_mid'] for r in all_results)
default_budget = 5_000_000
p33          = thresholds['p33']
p66          = thresholds['p66']

# Loads optimization_results.json and risk_thresholds.json produced by scripts 2 and 3

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Toronto Road Safety Dashboard</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f4f4f4;color:#222;}}
.header{{background:#0f172a;color:white;padding:1.1rem 2rem;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;}}
.header h1{{font-size:1.1rem;font-weight:600;}}
.header p{{font-size:0.75rem;opacity:0.55;margin-top:2px;}}
.badge{{background:#1e293b;color:#93c5fd;font-size:11px;padding:4px 10px;border-radius:20px;white-space:nowrap;}}
.budget-bar{{background:#1e293b;padding:.8rem 2rem;display:flex;align-items:center;gap:16px;flex-wrap:wrap;}}
.budget-bar label{{color:#94a3b8;font-size:12px;white-space:nowrap;}}
.budget-bar input[type=range]{{flex:1;min-width:160px;max-width:460px;accent-color:#3b82f6;}}
.budget-input{{background:#0f172a;border:1px solid #334155;color:white;padding:5px 10px;border-radius:6px;font-size:13px;width:130px;text-align:right;}}
.budget-val{{color:#60a5fa;font-size:1rem;font-weight:600;min-width:110px;}}
.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;padding:1rem 2rem;}}
.metric{{background:white;border-radius:8px;padding:.85rem 1rem;border:1px solid #e5e5e5;}}
.metric .label{{font-size:11px;color:#888;text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px;}}
.metric .value{{font-size:1.5rem;font-weight:600;color:#0f172a;line-height:1;}}
.metric .sub{{font-size:11px;color:#aaa;margin-top:4px;}}
.body{{padding:0 2rem 2rem;display:grid;grid-template-columns:1fr 310px;gap:14px;}}
.card{{background:white;border-radius:8px;border:1px solid #e5e5e5;overflow:hidden;}}
.card-head{{padding:.75rem 1.1rem;border-bottom:1px solid #eee;font-size:13px;font-weight:600;color:#333;display:flex;align-items:center;justify-content:space-between;}}
.legend{{display:flex;gap:10px;}}
.leg{{display:flex;align-items:center;gap:4px;font-size:11px;color:#666;font-weight:400;}}
.dot{{width:9px;height:9px;border-radius:50%;display:inline-block;}}
#map{{width:100%;height:490px;}}
.mix-body{{padding:1rem 1.1rem;}}
.mix-row{{margin-bottom:12px;}}
.mix-row-head{{display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px;}}
.bar-bg{{background:#f0f0f0;border-radius:4px;height:7px;}}
.bar-fill{{border-radius:4px;height:7px;transition:width .3s;}}
.full{{grid-column:1/-1;}}
.table-wrap{{overflow-x:auto;max-height:430px;overflow-y:auto;}}
table{{width:100%;border-collapse:collapse;font-size:12.5px;}}
th{{padding:.6rem .85rem;text-align:left;background:#f9f9f9;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.04em;color:#666;border-bottom:1px solid #eee;position:sticky;top:0;z-index:1;}}
td{{padding:.6rem .85rem;border-bottom:1px solid #f5f5f5;color:#333;}}
tr:hover td{{background:#fafafa;}}
.badge-sm{{padding:2px 8px;border-radius:20px;font-size:11px;font-weight:500;white-space:nowrap;}}
@media(max-width:900px){{.body{{grid-template-columns:1fr;}}.metrics{{grid-template-columns:repeat(2,1fr);}}}}
</style>
</head>
<body>
<div class="header">
  <div>
    <h1>Toronto Road Safety — Intervention Dashboard</h1>
    <p>City of Toronto Transportation Services</p>
  </div>
  <div class="badge"></div>
</div>

<div class="budget-bar">
  <label>BUDGET (CAD)</label>
  <input type="range" id="budgetSlider" min="100000" max="{int(max_cost)}" step="100000" value="{default_budget}">
  <input type="number" class="budget-input" id="budgetInput" min="100000" max="{int(max_cost)}" step="100000" value="{default_budget}">
  <span class="budget-val" id="budgetDisplay">$5,000,000</span>
</div>

<div class="metrics">
  <div class="metric"><div class="label">Sites selected</div><div class="value" id="mSites">—</div><div class="sub">from optimisation model</div></div>
  <div class="metric"><div class="label">Budget used</div><div class="value" id="mCost">—</div><div class="sub" id="mCostPct">of selected budget</div></div>
  <div class="metric"><div class="label">Crashes prevented</div><div class="value" id="mPrev">—</div><div class="sub">expected · risk-weighted</div></div>
  <div class="metric"><div class="label">Intervention types</div><div class="value" id="mTypes">—</div><div class="sub">distinct countermeasures</div></div>
</div>

<div class="body">
  <div class="card">
    <div class="card-head">
      <span>Risk Map — Selected Intervention Sites</span>
      <div class="legend">
        <div class="leg"><span class="dot" style="background:#dc2626;"></span>High risk</div>
        <div class="leg"><span class="dot" style="background:#d97706;"></span>Medium</div>
        <div class="leg"><span class="dot" style="background:#16a34a;"></span>Lower</div>
      </div>
    </div>
    <div id="map"></div>
  </div>

  <div>
    <div class="card">
      <div class="card-head">Intervention Mix</div>
      <div class="mix-body" id="mixPanel"></div>
    </div>
  </div>

  <div class="card full">
    <div class="card-head" style="flex-wrap:wrap;gap:8px;">
      <span>Priority Intersections</span>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
        <input type="text" id="searchBox" placeholder="Search neighbourhood..."
          style="padding:5px 10px;border:1px solid #ddd;border-radius:6px;font-size:12px;width:180px;outline:none;">
        <select id="filterType" style="padding:5px 10px;border:1px solid #ddd;border-radius:6px;font-size:12px;">
          <option value="">All interventions</option>
          <option value="crosswalk_visibility">Crosswalk Visibility</option>
          <option value="street_lighting">Street Lighting</option>
          <option value="adaptive_signal">Adaptive Signal</option>
          <option value="hfst">HFST</option>
          <option value="bike_lane">Bike Lane</option>
          <option value="raised_median">Raised Median</option>
        </select>
        <select id="sortBy" style="padding:5px 10px;border:1px solid #ddd;border-radius:6px;font-size:12px;">
          <option value="efficiency">Sort: Efficiency (default)</option>
          <option value="risk_desc">Sort: Risk Score ↓</option>
          <option value="risk_asc">Sort: Risk Score ↑</option>
          <option value="collisions_desc">Sort: Collisions ↓</option>
          <option value="severe_desc">Sort: Severe ↓</option>
          <option value="cost_asc">Sort: Cost ↑</option>
          <option value="cost_desc">Sort: Cost ↓</option>
          <option value="prevented_desc">Sort: Crashes Prevented ↓</option>
        </select>
        <span id="rowCount" style="font-size:12px;color:#888;white-space:nowrap;"></span>
      </div>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Rank</th><th>Neighbourhood</th><th>Risk Score</th>
            <th style="text-align:center">Collisions</th>
            <th style="text-align:center">Severe</th>
            <th>Why this intervention</th>
            <th>Recommended Intervention</th>
            <th style="text-align:right">Est. Cost (CAD)</th>
            <th style="text-align:center">Reduction</th>
            <th style="text-align:center">Prevented</th>
          </tr>
        </thead>
        <tbody id="tableBody"></tbody>
      </table>
    </div>
  </div>
</div>

<script>
const ALL_RESULTS = [];
fetch('optimization_results.json')
  .then(r => r.json())
  .then(data => {{
    ALL_RESULTS.push(...data);
    window.addEventListener('load', () => setBudget(5000000));
  }});
const P33 = {p33};
const P66 = {p66};

const COLORS = {{
  leading_pedestrian_interval: ['#eff6ff','#1d4ed8'],
  crosswalk_visibility:        ['#fdf4ff','#7e22ce'],
  street_lighting:             ['#fefce8','#a16207'],
  hfst:                        ['#fff7ed','#c2410c'],
  bike_lane:                   ['#f0fdf4','#166534'],
  adaptive_signal:             ['#f5f3ff','#6d28d9'],
  raised_median:               ['#fff1f2','#be123c'],
}};

function bandColor(score) {{
  if (score >= P66)  return '#dc2626';
  if (score >= P33)  return '#d97706';
  return '#16a34a';
}}

function fmtCAD(n) {{
  if (n >= 1e6) return '$' + (n/1e6).toFixed(2) + 'M';
  if (n >= 1e3) return '$' + Math.round(n/1000) + 'K';
  return '$' + n.toLocaleString();
}}

function riskBadge(score, pct) {{
  const topPct = Math.round((1 - pct) * 100);
  let bg, fg, label;
  if (score >= P66)      {{ bg='#fee2e2'; fg='#991b1b'; label='High'; }}
  else if (score >= P33) {{ bg='#fef3c7'; fg='#92400e'; label='Medium'; }}
  else                   {{ bg='#dcfce7'; fg='#166534'; label='Lower'; }}
  return `<span style="background:${{bg}};color:${{fg}};padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600;" title="Risk score: ${{score.toFixed(3)}} — top ${{topPct}}% most dangerous intersections in Toronto&#10;Scale: 0 = safest, 1 = most dangerous&#10;Based on: collision frequency, severity, pedestrian rate, nighttime rate">${{score.toFixed(3)}} · ${{label}}</span>`;
}}

const map = L.map('map').setView([43.72, -79.38], 11);
L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png',{{
  attribution:'© OpenStreetMap contributors © CARTO'
}}).addTo(map);

let markerLayer = L.layerGroup().addTo(map);

function update(budget) {{
  const selected = [];
  let spent = 0;
  for (const site of ALL_RESULTS) {{
    if (spent + site.cost_mid <= budget) {{
      selected.push(site);
      spent += site.cost_mid;
    }}
  }}

  const totalPrev = selected.reduce((a,s)=>a+s.crashes_prevented,0);
  const nTypes    = new Set(selected.map(s=>s.intervention_key)).size;

  document.getElementById('mSites').textContent = selected.length;
  document.getElementById('mCost').textContent  = fmtCAD(spent);
  document.getElementById('mCostPct').textContent = `of ${{fmtCAD(budget)}} · ${{(spent/budget*100).toFixed(0)}}% utilised`;
  document.getElementById('mPrev').textContent  = totalPrev.toFixed(1);
  document.getElementById('mTypes').textContent = nTypes;

  // Map
  markerLayer.clearLayers();
  selected.forEach((site, idx) => {{
    const color = bandColor(site.risk_score);
    const topPct = Math.round((1 - site.risk_percentile) * 100);
    const [,fg] = COLORS[site.intervention_key] || ['#f1f5f9','#334155'];
    const popup = `
<div style="font-family:-apple-system,sans-serif;width:260px;padding:6px 8px;">
  <b style="font-size:13px;">${{site.neighbourhood}}</b>
  <div style="font-size:11px;color:#888;margin-top:2px;">Rank #${{idx+1}} of ${{selected.length}} selected sites</div>
  <hr style="border:none;border-top:1px solid #eee;margin:6px 0;">
  <div style="font-size:12px;margin-bottom:6px;">
    <b>Risk score: ${{site.risk_score.toFixed(3)}}</b>
    <span style="color:#666;"> (0 = safest · 1 = most dangerous)</span><br>
    <span style="color:${{color}};font-weight:600;">Top ${{topPct}}% most dangerous intersections in Toronto</span>
  </div>
  <table style="font-size:12px;width:100%;border-collapse:collapse;">
    <tr><td style="color:#666;padding:2px 0;">Collisions</td><td style="text-align:right;">${{site.collision_count}}</td></tr>
    <tr><td style="color:#666;padding:2px 0;">Severe crashes</td><td style="text-align:right;">${{site.severe_count}}</td></tr>
    <tr><td style="color:#666;padding:2px 0;">Fatalities</td><td style="text-align:right;">${{site.fatality_count}}</td></tr>
    <tr><td style="color:#666;padding:2px 0;">Nighttime rate</td><td style="text-align:right;">${{(site.nighttime_rate*100).toFixed(0)}}%</td></tr>
    <tr><td style="color:#666;padding:2px 0;">Pedestrian rate</td><td style="text-align:right;">${{(site.ped_rate*100).toFixed(0)}}%</td></tr>
    <tr><td style="color:#666;padding:2px 0;">Bicycle rate</td><td style="text-align:right;">${{(site.bike_rate*100).toFixed(0)}}%</td></tr>
  </table>
  <hr style="border:none;border-top:1px solid #eee;margin:6px 0;">
  <div style="color:${{fg}};font-weight:600;font-size:12px;margin-bottom:3px;">${{site.icon}} ${{site.intervention}}</div>
  <div style="font-size:11px;color:#666;margin-bottom:6px;font-style:italic;">${{site.condition}}</div>
  <table style="font-size:12px;width:100%;border-collapse:collapse;">
    <tr><td style="color:#666;padding:2px 0;">Estimated cost</td><td style="text-align:right;">${{fmtCAD(site.cost_low)}} – ${{fmtCAD(site.cost_high)}} CAD</td></tr>
    <tr><td style="color:#666;padding:2px 0;">Crash reduction</td><td style="text-align:right;">${{site.crf_pct}}%</td></tr>
    <tr><td style="color:#666;padding:2px 0;">Crashes prevented</td><td style="text-align:right;">~${{site.crashes_prevented.toFixed(2)}}</td></tr>
    <tr><td style="color:#666;padding:2px 0;">Relevance score</td><td style="text-align:right;">${{site.relevance.toFixed(2)}} / 1.00</td></tr>
  </table>
  <div style="font-size:10px;color:#aaa;margin-top:6px;">CMF source: ${{site.source}}</div>
</div>`;
    L.circleMarker([site.lat, site.lon], {{
      radius: 8, color: color, fillColor: color,
      fillOpacity: 0.82, weight: 2
    }}).bindPopup(popup, {{maxWidth: 280}})
      .bindTooltip(`${{site.icon}} #${{idx+1}} ${{site.neighbourhood}} · ${{site.collision_count}} collisions · Risk: ${{site.risk_score.toFixed(3)}} (top ${{topPct}}% most dangerous · 0=safest, 1=most dangerous)`)
      .addTo(markerLayer);
  }});

  // Mix panel
  const mixCounts = {{}};
  selected.forEach(s => {{
    if (!mixCounts[s.intervention_key])
      mixCounts[s.intervention_key] = {{name:s.intervention,icon:s.icon,count:0,cost:0}};
    mixCounts[s.intervention_key].count++;
    mixCounts[s.intervention_key].cost += s.cost_mid;
  }});
  const mixPanel = document.getElementById('mixPanel');
  const entries  = Object.entries(mixCounts).sort((a,b)=>b[1].count-a[1].count);
  mixPanel.innerHTML = entries.map(([key, v]) => {{
    const [bg, fg] = COLORS[key] || ['#f1f5f9','#334155'];
    const pct = (v.count / selected.length * 100).toFixed(0);
    return `<div class="mix-row">
      <div class="mix-row-head">
        <span style="font-size:12px;">${{v.icon}} ${{v.name}}</span>
        <span style="font-size:11px;color:#666;">${{v.count}} sites · ${{fmtCAD(v.cost)}}</span>
      </div>
      <div class="bar-bg"><div class="bar-fill" style="background:${{fg}};width:${{pct}}%;"></div></div>
    </div>`;
  }}).join('') + `
  <div style="margin-top:14px;padding-top:12px;border-top:1px solid #eee;">
    <div style="font-size:11px;color:#999;margin-bottom:4px;">BUDGET ALLOCATION</div>
    <div class="bar-bg" style="height:10px;"><div class="bar-fill" style="background:#0f172a;height:10px;width:${{(spent/budget*100).toFixed(0)}}%;"></div></div>
    <div style="display:flex;justify-content:space-between;font-size:11px;color:#888;margin-top:4px;">
      <span>${{fmtCAD(spent)}} used</span><span>${{fmtCAD(budget)}} total</span>
    </div>
  </div>`;

  // Store selected globally for search/sort/filter
  window._selected = selected;
  renderTable();
}}

function renderTable() {{
  const selected = window._selected || [];
  const search   = (document.getElementById('searchBox')?.value || '').toLowerCase();
  const filter   = document.getElementById('filterType')?.value || '';
  const sortBy   = document.getElementById('sortBy')?.value || 'efficiency';

  let rows = selected.filter(s => {{
    const matchSearch = !search || s.neighbourhood.toLowerCase().includes(search);
    const matchFilter = !filter || s.intervention_key === filter;
    return matchSearch && matchFilter;
  }});

  const sortFns = {{
    efficiency:      (a,b) => b.value_ratio - a.value_ratio,
    risk_desc:       (a,b) => b.risk_score - a.risk_score,
    risk_asc:        (a,b) => a.risk_score - b.risk_score,
    collisions_desc: (a,b) => b.collision_count - a.collision_count,
    severe_desc:     (a,b) => b.severe_count - a.severe_count,
    cost_asc:        (a,b) => a.cost_mid - b.cost_mid,
    cost_desc:       (a,b) => b.cost_mid - a.cost_mid,
    prevented_desc:  (a,b) => b.crashes_prevented - a.crashes_prevented,
  }};
  rows.sort(sortFns[sortBy] || sortFns.efficiency);

  document.getElementById('rowCount').textContent =
    rows.length === selected.length
      ? `${{rows.length}} sites`
      : `${{rows.length}} of ${{selected.length}} sites`;

  document.getElementById('tableBody').innerHTML = rows.map((site, idx) => {{
    const [bg, fg] = COLORS[site.intervention_key] || ['#f1f5f9','#334155'];
    return `<tr>
      <td style="color:#888;font-size:12px;">#${{idx+1}}</td>
      <td style="font-weight:500;">${{site.neighbourhood}}</td>
      <td>${{riskBadge(site.risk_score, site.risk_percentile)}}</td>
      <td style="text-align:center;">${{site.collision_count}}</td>
      <td style="text-align:center;">${{site.severe_count}}</td>
      <td style="font-size:11px;color:#666;font-style:italic;max-width:180px;">${{site.condition}}</td>
      <td><span class="badge-sm" style="background:${{bg}};color:${{fg}};">${{site.icon}} ${{site.intervention}}</span></td>
      <td style="text-align:right;font-size:12px;white-space:nowrap;">${{fmtCAD(site.cost_low)}}–${{fmtCAD(site.cost_high)}}</td>
      <td style="text-align:center;">${{site.crf_pct}}%</td>
      <td style="text-align:center;">~${{site.crashes_prevented.toFixed(2)}}</td>
    </tr>`;
  }}).join('');
}}

const slider  = document.getElementById('budgetSlider');
const input   = document.getElementById('budgetInput');
const display = document.getElementById('budgetDisplay');

function setBudget(val) {{
  val = Math.max(100000, Math.min({int(max_cost)}, Math.round(val/100000)*100000));
  slider.value = val;
  input.value  = val;
  display.textContent = '$' + val.toLocaleString();
  update(val);
}}

slider.addEventListener('input',  () => setBudget(+slider.value));
input.addEventListener('change',  () => setBudget(+input.value));

// Wait for full page load before initialising map markers


// Search, filter, sort listeners — re-render table without changing budget
document.getElementById('searchBox').addEventListener('input',  renderTable);
document.getElementById('filterType').addEventListener('change', () => {{ renderTable(); }});
document.getElementById('sortBy').addEventListener('change',    () => {{ renderTable(); }});
</script>
</body>
</html>"""

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("Saved: dashboard.html")