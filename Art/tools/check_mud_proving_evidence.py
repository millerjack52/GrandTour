"""Integration gates from actual Unreal driving samples, separate from visual judgement."""
import json,math,re,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/MudProvingGround'
r=json.loads((OUT/'review-report.json').read_text())
status=json.loads((OUT/'review-run-status.json').read_text(encoding='utf-8-sig'))
assert r['ok'] and status['fresh'] and status['exit_code']==0
def phase(name):
    rows=[s for s in r['samples'] if s['phase']==name]
    assert len(rows)>=5,name
    return rows
crawl=phase('crawl');cross=phase('crossing');entry=phase('rolling_entry')
settled=[v for s in crawl if s['t']>3 for v in s['sinkage']]
contact_ratio=statistics.fmean(float(v) for s in crawl+cross for v in s['contacts'])
peak=max(s['speed_cm_s'] for s in entry)
balance=float(re.search(r'balance_cm3=([-\d.]+)',r['surface_after']).group(1))
summary={
    'conditions':{'level':'L_MudProvingGround','throttle':.6,'crawl_and_crossing':'Low range, differential locked','rolling_entry':'Accelerated from rest on firm ground in high range; no injected velocity','scope':'Current project test car and one saturated patch'},
    'mean_loaded_penetration_cm':statistics.fmean(settled),
    'wheel_contact_fraction_crawl_and_crossing':contact_ratio,
    'crossing_travel_cm':cross[-1]['position'][1]-cross[0]['position'][1],
    'firm_ground_entry_peak_kmh':peak*.036,
    'firm_ground_entry_final_kmh':entry[-1]['speed_cm_s']*.036,
    'lowest_final_tyre_coating':min(crawl[-1]['tyre_coat']),
    'volume_balance_error_cm3':balance,
    'visual_acceptance':'Separate image inspection; owner approval pending',
    'performance_acceptance':'Pending isolated GPU run' if status['other_game_observed'] else 'See timing report; small-scene scope only'
}
checks={
    'loaded_wheels_yield':6<summary['mean_loaded_penetration_cm']<25,
    'retains_contact_through_ruts':contact_ratio>.95,
    'crosses_existing_tracks':summary['crossing_travel_cm']>300,
    'accelerated_entry_reaches_bog':entry[-1]['position'][1]>-300 and peak>180,
    'entry_loses_momentum_in_mud':entry[-1]['speed_cm_s']<peak*.5,
    'tyres_pick_up_mud':summary['lowest_final_tyre_coating']>.1,
    'displaced_volume_conserved':abs(balance)<.01,
    'finite_motion':all(math.isfinite(v) for s in r['samples'] for v in s['position'])
}
summary['checks']=checks;summary['ok']=all(checks.values())
(OUT/'integration-checks.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2));assert summary['ok'],checks
