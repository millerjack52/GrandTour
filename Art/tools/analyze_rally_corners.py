"""Summarize actual corner traces, retaining failures and all driving hitches."""
from pathlib import Path
import argparse, json, math

ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser();parser.add_argument('labels',nargs='+');args=parser.parse_args()
result=[]
for label in args.labels:
    path=ROOT/'Saved/RallyHandlingQA'/('corners-'+label+'.json')
    report=json.loads(path.read_text());summary=dict(label=label,ok=report['ok'],error=report.get('error'),controller_version=report.get('controller_version',1),runs=[])
    process=path.with_name(path.stem+'-process.json')
    if process.exists():summary['process_exit_code']=json.loads(process.read_text(encoding='utf-8-sig'))['exit_code']
    for run in report['runs']:
        t=run['trace']
        if not t:continue
        row={k:v for k,v in run.items() if k!='trace'}
        perf=ROOT/'Saved/Profiling'/('gt_perf_rally-'+label+'-'+run['car']+'.json')
        if perf.exists():
            measured=json.loads(perf.read_text());row['engine_frame_ms']=measured['frame_ms']
        row['filtered_input_valid']=not (max(abs(x['solver']['filtered']) for x in t)==0 and max(abs(w['angle']) for x in t for w in x['solver']['wheels'])>1)
        if not row['filtered_input_valid']:
            row['saturated_seconds']=None
            row['telemetry_note']='Stored network input was not populated on this path. Wheel angles and forces remain valid; saturation requires the corrected ProcessSteering snapshot.'
        row['mean_abs_offset_m']=sum(x['off_m'] for x in t)/len(t)
        row['rms_slip_deg']=math.sqrt(sum(x['slip_deg']**2 for x in t)/len(t))
        row['countersteer_frames']=sum(x['command']*x['slip_deg']>0 and abs(x['slip_deg'])>5 for x in t)
        row['high_speed_frames']=sum(x['kmh']>70 for x in t)
        row['high_speed_saturated_frames']=sum(x['kmh']>70 and abs(x['solver']['filtered'])>.98 for x in t) if row['filtered_input_valid'] else None
        row['max_front_slip_deg']=max(w['slip_deg'] for x in t for w in x['solver']['wheels'][:2])
        row['max_rear_slip_deg']=max(w['slip_deg'] for x in t for w in x['solver']['wheels'][2:])
        row['sections']=[]
        for name,begin,end in [('fast_right',200,420),('linked',420,700),('sweeper',700,1000),('hairpin',1000,1200),('crest_exit',1200,1500)]:
            segment=[x for x in t if begin<=x['s_m']<end]
            if not segment:continue
            row['sections'].append(dict(name=name,completed=t[-1]['s_m']>=end,entry_kmh=segment[0]['kmh'],exit_kmh=segment[-1]['kmh'],max_off_m=max(x['off_m'] for x in segment),max_slip_deg=max(abs(x['slip_deg']) for x in segment),saturated_frames=sum(abs(x['solver']['filtered'])>.98 for x in segment)))
        summary['runs'].append(row)
    result.append(summary)
out=ROOT/'Saved/RallyHandlingQA'/('analysis-'+args.labels[-1]+'.json')
out.write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
