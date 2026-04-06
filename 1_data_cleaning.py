import pandas as pd
import numpy as np

print("Loading data...")
df = pd.read_csv('Traffic_Collisions_Open_Data.csv', low_memory=False)
print(f"Loaded {len(df)} records")

# Records with missing or zero coordinates cannot be mapped
# Toronto bounding box: lat 43.0–44.5, lon -80.0 to -78.5
df = df[
    (df['LAT_WGS84'].notna()) & (df['LONG_WGS84'].notna()) &
    (df['LAT_WGS84'] > 43.0) & (df['LAT_WGS84'] < 44.5) &
    (df['LONG_WGS84'] > -80.0) & (df['LONG_WGS84'] < -78.5)
]
print(f"After dropping bad coordinates: {len(df)} records")

# Convert categorical YES/NO/N/R columns to binary (1/0) for modelling
yn_cols = ['AUTOMOBILE','MOTORCYCLE','PASSENGER','BICYCLE','PEDESTRIAN',
           'INJURY_COLLISIONS','FTR_COLLISIONS','PD_COLLISIONS']
for col in yn_cols:
    if col in df.columns:
        df[col] = df[col].map({'YES':1,'NO':0,'N/R':0}).fillna(0).astype(int)

# Time-of-day features used to match interventions to crash patterns
# Nighttime: 20:00–05:59 (FHWA: 77% of ped fatalities occur in darkness)
# Peak hour: 07:00–09:59 and 16:00–18:59 (congestion-driven crashes)
# Daytime:   09:00–19:59 (pedestrian/uncontrolled crossing exposure)
df['is_nighttime'] = ((df['OCC_HOUR'] >= 20) | (df['OCC_HOUR'] <= 5)).astype(int)
df['is_peak']      = (df['OCC_HOUR'].between(7,9) | df['OCC_HOUR'].between(16,18)).astype(int)
df['is_daytime']   = (df['OCC_HOUR'].between(9,19)).astype(int)
df['is_severe']    = ((df['FATALITIES'] > 0) | (df['INJURY_COLLISIONS'] == 1)).astype(int)

# Cluster individual collision records to intersection-level observations
# Rounding lat/lon to 3 decimal places creates ~100m grid cells
# All collisions within the same cell are treated as one intersection
df['lat_round'] = df['LAT_WGS84'].round(3)
df['lon_round'] = df['LONG_WGS84'].round(3)
df['intersection_id'] = df['lat_round'].astype(str) + '_' + df['lon_round'].astype(str)

print("Aggregating to intersections...")

def safe_mode(x):
    vals = x.dropna()
    return vals.mode()[0] if len(vals) > 0 else 'Unknown'

# Aggregate collision records to intersection level
agg = df.groupby('intersection_id').agg(
    lat             =('LAT_WGS84',         'mean'),
    lon             =('LONG_WGS84',        'mean'),
    collision_count =('OBJECTID',          'count'),
    severe_count    =('is_severe',         'sum'),
    ped_count       =('PEDESTRIAN',        'sum'),
    bike_count      =('BICYCLE',           'sum'),
    auto_count      =('AUTOMOBILE',        'sum'),
    moto_count      =('MOTORCYCLE',        'sum'),
    nighttime_count =('is_nighttime',      'sum'),
    peak_count      =('is_peak',           'sum'),
    daytime_count   =('is_daytime',        'sum'),
    fatality_count  =('FATALITIES',        'sum'),
    neighbourhood   =('NEIGHBOURHOOD_158', safe_mode),
).reset_index()

# Compute collision profile rates:proportion of collisions involving each user type
agg['severe_rate']    = agg['severe_count']    / agg['collision_count']
agg['ped_rate']       = agg['ped_count']       / agg['collision_count']
agg['bike_rate']      = agg['bike_count']      / agg['collision_count']
agg['auto_rate']      = agg['auto_count']      / agg['collision_count']
agg['moto_rate']      = agg['moto_count']      / agg['collision_count']
agg['nighttime_rate'] = agg['nighttime_count'] / agg['collision_count']
agg['peak_rate']      = agg['peak_count']      / agg['collision_count']
agg['daytime_rate']   = agg['daytime_count']   / agg['collision_count']

print(f"Total unique intersections: {len(agg)}")
agg.to_csv('intersections_cleaned.csv', index=False)
print("Saved: intersections_cleaned.csv")