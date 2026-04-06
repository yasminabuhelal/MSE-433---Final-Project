import pandas as pd
import numpy as np
import pulp
import json
from collections import Counter

print("Loading risk data...")
df = pd.read_csv('intersections_with_risk.csv')
print(f"Loaded {len(df)} intersections")

# cmf = Crash Modification Factor, crf = 1 - cmf (crash reduction)
# cost_mid used in optimization, cost_low/high shown to client in dashboard
INTERVENTIONS = {
    'crosswalk_visibility': {
        'name': 'Crosswalk Visibility Enhancement',
        'cmf': 0.60, 'crf': 0.40,
        'cost_mid': 17500, 'cost_low': 10000, 'cost_high': 25000,
        'source': 'Chen et al., 2012 (CMF ID: 4123)',
        'icon': '🦓',
        'condition': 'High pedestrian rate + daytime exposure at uncontrolled crossings',
    },
    'street_lighting': {
        'name': 'Street Lighting Upgrade',
        'cmf': 0.82, 'crf': 0.18,
        'cost_mid': 35000, 'cost_low': 20000, 'cost_high': 50000,
        'source': 'Runyan et al., 2024 (CMF Clearinghouse)',
        'icon': '💡',
        'condition': 'High nighttime collision rate',
    },
    'hfst': {
        'name': 'High Friction Surface Treatment',
        'cmf': 0.80, 'crf': 0.20,
        'cost_mid': 27500, 'cost_low': 15000, 'cost_high': 40000,
        'source': 'NCHRP Report 617 (CMF ID: 2259); Essa et al., 2025',
        'icon': '🛣',
        'condition': 'High severity + high automobile rate (rear-end / failure-to-yield history)',
    },
    'bike_lane': {
        'name': 'Bike Lane Installation',
        'cmf': 0.734, 'crf': 0.266,
        'cost_mid': 75000, 'cost_low': 50000, 'cost_high': 100000,
        'source': 'Avelar et al., 2021 (CMF Clearinghouse)',
        'icon': '🚲',
        'condition': 'High bicycle collision rate',
    },
    'adaptive_signal': {
        'name': 'Adaptive Signal Control',
        'cmf': 0.87, 'crf': 0.13,
        'cost_mid': 48000, 'cost_low': 30000, 'cost_high': 65000,
        'source': 'Khattak et al., 2018 (CMF Clearinghouse)',
        'icon': '🚦',
        'condition': 'High collision volume + peak hour congestion',
    },
    'raised_median': {
        'name': 'Raised Median / Pedestrian Refuge',
        'cmf': 0.685, 'crf': 0.315,
        'cost_mid': 55000, 'cost_low': 30000, 'cost_high': 80000,
        'source': 'Zegeer et al., 2017 (CMF Clearinghouse)',
        'icon': '🛡',
        'condition': 'High pedestrian rate + high severity + fatality history',
    },
}
INT_KEYS = list(INTERVENTIONS.keys())

# Percentile ranks used instead of raw rates — rates are unstable on sparse data
def prank(s): return s.rank(pct=True)

df['pr_ped']        = prank(df['ped_rate'])
df['pr_nighttime']  = prank(df['nighttime_rate'])
df['pr_bike']       = prank(df['bike_rate'])
df['pr_severe']     = prank(df['severe_count'])
df['pr_collisions'] = prank(df['collision_count'])
df['pr_peak']       = prank(df['peak_rate'])
df['pr_daytime']    = prank(df['daytime_rate'])
df['pr_fatality']   = prank(df['fatality_count'])
df['pr_auto']       = prank(df['auto_rate'])

# Relevance score (0.5-1.0) — how well the intersection profile matches
# the FHWA-specified conditions for each intervention
# Base of 0.5 means every intervention is at least marginally applicable
def compute_relevance(row, key):
    if key == 'crosswalk_visibility':
        return 0.5 + 0.3 * row['pr_ped'] + 0.2 * row['pr_daytime']
    if key == 'street_lighting':
        return 0.5 + 0.5 * row['pr_nighttime']
    if key == 'hfst':
        return 0.5 + 0.3 * row['pr_severe'] + 0.2 * row['pr_auto']
    if key == 'bike_lane':
        return 0.5 + 0.5 * row['pr_bike']
    if key == 'adaptive_signal':
        return 0.5 + 0.3 * row['pr_collisions'] + 0.2 * row['pr_peak']
    if key == 'raised_median':
        # Ineligible below dataset median ped rate — FHWA specifies this for
        # pedestrian crossings only, not general severity
        if row['pr_ped'] < 0.50:
            return 0.0
        return 0.5 + 0.2 * row['pr_ped'] + 0.15 * row['pr_severe'] + 0.15 * row['pr_fatality']
    return 0.5

# Assign each intersection its best-matching intervention by highest relevance
# The optimizer then decides which assignments to fund within the budget
print("Assigning interventions...")
candidates = []
for i, row in df.iterrows():
    rels     = {k: compute_relevance(row, k) for k in INT_KEYS}
    best_key = max(rels, key=rels.get)
    rel      = rels[best_key]
    cost     = INTERVENTIONS[best_key]['cost_mid']
    # Benefit formula: collisions × CRF × risk_percentile × relevance
    benefit  = float(row['collision_count']) * INTERVENTIONS[best_key]['crf'] * float(row['risk_percentile']) * rel

    candidates.append({
        'idx':              i,
        'intersection_id':  row['intersection_id'],
        'lat':              round(float(row['lat']), 6),
        'lon':              round(float(row['lon']), 6),
        'neighbourhood':    str(row['neighbourhood']),
        'collision_count':  int(row['collision_count']),
        'severe_count':     int(row['severe_count']),
        'fatality_count':   int(row['fatality_count']),
        'risk_score':       round(float(row['risk_score']), 4),
        'risk_band':        str(row['risk_band']),
        'risk_percentile':  round(float(row['risk_percentile']), 4),
        'intervention':     INTERVENTIONS[best_key]['name'],
        'intervention_key': best_key,
        'condition':        INTERVENTIONS[best_key]['condition'],
        'icon':             INTERVENTIONS[best_key]['icon'],
        'cmf':              INTERVENTIONS[best_key]['cmf'],
        'crf_pct':          round(INTERVENTIONS[best_key]['crf'] * 100, 1),
        'cost_mid':         cost,
        'cost_low':         INTERVENTIONS[best_key]['cost_low'],
        'cost_high':        INTERVENTIONS[best_key]['cost_high'],
        'crashes_prevented': round(benefit, 4),
        'relevance':        round(rel, 3),
        'value_ratio':      round(benefit / cost, 8),
        'source':           INTERVENTIONS[best_key]['source'],
        'ped_rate':         round(float(row['ped_rate']), 3),
        'bike_rate':        round(float(row['bike_rate']), 3),
        'nighttime_rate':   round(float(row['nighttime_rate']), 3),
        'peak_rate':        round(float(row['peak_rate']), 3),
    })

print("Intervention assignment distribution:")
for k, v in Counter(c['intervention_key'] for c in candidates).most_common():
    print(f"  {INTERVENTIONS[k]['icon']} {INTERVENTIONS[k]['name']:<45} {v} sites")

# Binary knapsack solved at large max budget so all viable sites are evaluated
# Dashboard uses greedy selection on the sorted results for any user budget
MAX_BUDGET = 100_000_000
print(f"\nSolving at max budget ${MAX_BUDGET:,}...")

prob = pulp.LpProblem("road_safety", pulp.LpMaximize)
x    = [pulp.LpVariable(f"x_{k}", cat='Binary') for k in range(len(candidates))]

prob += pulp.lpSum(c['crashes_prevented'] * x[k] for k, c in enumerate(candidates))
prob += pulp.lpSum(c['cost_mid'] * x[k] for k, c in enumerate(candidates)) <= MAX_BUDGET

# One intervention per intersection
by_int = {}
for k, c in enumerate(candidates):
    by_int.setdefault(c['idx'], []).append(k)
for i, ks in by_int.items():
    prob += pulp.lpSum(x[k] for k in ks) <= 1

prob.solve(pulp.PULP_CBC_CMD(msg=0))
print(f"Status: {pulp.LpStatus[prob.status]}")

all_results = [c for k, c in enumerate(candidates) if x[k].varValue and x[k].varValue > 0.5]
all_results.sort(key=lambda r: -r['value_ratio'])

print(f"\nPool: {len(all_results)} sites")
print(f"Mix:  {Counter(r['intervention_key'] for r in all_results)}")

sel, spent = [], 0
for r in all_results:
    if spent + r['cost_mid'] <= 5_000_000:
        sel.append(r); spent += r['cost_mid']
print(f"\nAt $5M: {len(sel)} sites, ${spent:,}")
print(f"Mix: {Counter(s['intervention_key'] for s in sel)}")

pd.DataFrame(all_results).to_csv('optimization_results.csv', index=False)
with open('optimization_results.json', 'w') as f:
    json.dump(all_results, f)

summary = {
    'total_sites':     len(all_results),
    'total_pool_cost': sum(r['cost_mid'] for r in all_results),
    'interventions':   {
        k: {
            'name': v['name'], 'icon': v['icon'],
            'crf_pct': round(v['crf']*100, 1),
            'cost_low': v['cost_low'], 'cost_high': v['cost_high'],
            'cost_mid': v['cost_mid'], 'source': v['source'],
            'condition': v['condition'],
        } for k, v in INTERVENTIONS.items()
    }
}
with open('optimization_summary.json', 'w') as f:
    json.dump(summary, f)

print("\nSaved: optimization_results.csv, optimization_results.json, optimization_summary.json")