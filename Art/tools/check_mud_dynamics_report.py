"""Acceptance checks on recorded unrestricted vehicle trials, independent of the UE runner."""
import json,math
from pathlib import Path
OUT=Path(__file__).resolve().parents[1]/'Export/MudResponse'

def validate():
    path=OUT/'dynamics-after.json';report=json.loads(path.read_text())
    r={run['name']:run for run in report['runs']}
    bog=r['bog_start'];crawl=r['bog_crawl']
    checks={
        'firm_ground_acceleration_retained':r['firm_start']['end_kmh']>35,
        'bog_start_resists_full_throttle':.1<bog['end_kmh']<10 and bog['travel_cm']>30,
        'controlled_throttle_makes_progress':crawl['travel_cm']>100,
        'settled_40_kmh_entry_loses_speed':r['bog_coast40']['end_kmh']<15,
        'fresh_40_kmh_entry_loses_speed':r['bog_fresh40']['end_kmh']<20,
        'restart_after_settling':r['bog_restart']['travel_cm']>30,
        'reverse_drives_backwards':r['bog_reverse']['travel_cm']<-30,
        'wheelspin_is_not_road_speed':max(sum(abs(v) for v in s['tread'])/4-s['speed_kmh'] for s in bog['samples'])>5,
        'loaded_body_sits_lower':r['firm_start']['samples'][0]['position'][2]-bog['samples'][0]['position'][2]>5,
        'bog_keeps_wheel_contact':sum(sum(s['contacts']) for s in bog['samples'])>=len(bog['samples'])*3.4,
        'all_results_finite':all(math.isfinite(v) for run in r.values() for s in run['samples'] for v in s['position']+[s['speed_kmh']]),
        'no_automatic_speed_braking':report['automatic_speed_braking'] is False,
    }
    report['checks']=checks;report['ok']=len(r)==10 and all(checks.values());path.write_text(json.dumps(report,indent=2))
    return checks

if __name__=='__main__':
    checks=validate();print(json.dumps(checks,indent=2))
    raise SystemExit(0 if all(checks.values()) else 1)
