"""Summarize a supplied Unreal CSV without conflating screenshots with viewport size."""
import csv,json,sys,statistics
from pathlib import Path

source=Path(sys.argv[1])
rows=list(csv.DictReader(source.open(newline='',encoding='utf-8-sig')))
def numbers(key):
    out=[]
    for row in rows:
        try:value=float(row[key])
        except (KeyError,TypeError,ValueError):continue
        if value>0:out.append(value)
    return sorted(out)
def summarize(key):
    a=numbers(key)
    return dict(count=len(a),median_ms=round(statistics.median(a),3),p95_ms=round(a[int((len(a)-1)*.95)],3)) if a else None
result={'source':str(source.resolve()),'scope':'Wet replay, PIE cockpit; no screenshots during capture; not a packaged benchmark',
        'stats':{key:summarize(key) for key in ['FrameTime','GPUTime','GameThreadTime','GPU/Basepass','GPU/ShadowDepths','GPU/LumenScreenProbeGather']}}
report=Path(__file__).resolve().parents[1]/'Export/LiveMudDrive/drive-report.json'
result['viewport_size']=json.loads(report.read_text()).get('viewport_size')
out=report.with_name('performance-report.json');out.write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
