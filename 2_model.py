import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import classification_report
import json
import warnings
warnings.filterwarnings('ignore')

print("Loading intersection data...")
df = pd.read_csv('intersections_cleaned.csv')
print(f"Loaded {len(df)} intersections")

# Composite Risk Score 
# Normalize each indicator to 0-1, then combine with literature based weights
# Collision count and severity each get 0.30 as primary risk indicators
# Pedestrian rate gets 0.20, higher weight due to crash severity outcomes
scaler = MinMaxScaler()
df['n_collisions'] = scaler.fit_transform(df[['collision_count']]).flatten()
df['n_severe']     = scaler.fit_transform(df[['severe_count']]).flatten()
df['n_ped']        = scaler.fit_transform(df[['ped_rate']]).flatten()
df['n_nighttime']  = scaler.fit_transform(df[['nighttime_rate']]).flatten()
df['n_bike']       = scaler.fit_transform(df[['bike_rate']]).flatten()
df['n_fatality']   = scaler.fit_transform(df[['fatality_count']]).flatten()

df['risk_score'] = (
    0.30 * df['n_collisions'] +
    0.30 * df['n_severe']    +
    0.20 * df['n_ped']       +
    0.10 * df['n_nighttime'] +
    0.05 * df['n_bike']      +
    0.05 * df['n_fatality']
).round(4)

df.drop(columns=['n_collisions','n_severe','n_ped',
                 'n_nighttime','n_bike','n_fatality'], inplace=True)

# Risk Bands 
# Use percentiles of non-zero scores only — many intersections score 0
# (single collision, no severity) which would collapse the band thresholds
nonzero = df[df['risk_score'] > 0]['risk_score']
if len(nonzero) >= 10:
    p33 = float(nonzero.quantile(0.33))
    p66 = float(nonzero.quantile(0.66))
else:
    p33 = float(df['risk_score'].quantile(0.50))
    p66 = float(df['risk_score'].quantile(0.80))

if p33 >= p66:
    p33 = float(df['risk_score'].quantile(0.33))
    p66 = float(df['risk_score'].quantile(0.80))

print(f"Risk score range: {df['risk_score'].min():.4f} – {df['risk_score'].max():.4f}")
print(f"Band thresholds: Lower < {p33:.4f} ≤ Medium < {p66:.4f} ≤ High")

df['risk_band']       = df['risk_score'].apply(lambda s: 'High' if s >= p66 else ('Medium' if s >= p33 else 'Lower'))
# Percentile rank used in optimization benefit calculation (always non-zero)
df['risk_percentile'] = df['risk_score'].rank(pct=True).round(4)

print("\nRisk band distribution:")
print(df['risk_band'].value_counts())

# Random Forest 
# Used for feature importance and cross-validation reporting only
threshold = df['risk_score'].quantile(0.75)
df['is_high_risk'] = (df['risk_score'] >= threshold).astype(int)
print(f"\nHigh-risk intersections (top 25%): {df['is_high_risk'].sum()}")

feature_cols = ['collision_count','ped_rate','bike_rate',
                'nighttime_rate','peak_rate','moto_count','severe_count']
X = df[feature_cols].fillna(0)
y = df['is_high_risk']

print("\nTraining Random Forest...")
rf = RandomForestClassifier(
    n_estimators=300, max_depth=6, min_samples_leaf=10,
    class_weight='balanced', random_state=42, n_jobs=-1
)
n_splits = min(5, max(2, int(y.sum() // 5)))
cv       = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
cv_auc   = cross_val_score(rf, X, y, cv=cv, scoring='roc_auc')
cv_prec  = cross_val_score(rf, X, y, cv=cv, scoring='precision')
cv_rec   = cross_val_score(rf, X, y, cv=cv, scoring='recall')

print(f"\nCross-Validation ({n_splits}-fold):")
print(f"  AUC:       {cv_auc.mean():.3f} ± {cv_auc.std():.3f}")
print(f"  Precision: {cv_prec.mean():.3f} ± {cv_prec.std():.3f}")
print(f"  Recall:    {cv_rec.mean():.3f}  ± {cv_rec.std():.3f}")

rf.fit(X, y)
importance = pd.DataFrame({
    'feature': feature_cols, 'importance': rf.feature_importances_
}).sort_values('importance', ascending=False)

print("\nFeature Importance:")
for _, row in importance.iterrows():
    print(f"  {row['feature']:<22} {row['importance']:.3f}  {'█' * int(row['importance']*40)}")

print("\nClassification Report:")
print(classification_report(y, rf.predict(X), target_names=['Lower risk','High risk']))

# Save thresholds for the dashboard to apply consistent band coloring
with open('risk_thresholds.json', 'w') as f:
    json.dump({'p33': p33, 'p66': p66}, f)

df.to_csv('intersections_with_risk.csv', index=False)
print("Saved: intersections_with_risk.csv, risk_thresholds.json")