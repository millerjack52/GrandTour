"""Compare warmed game frames, excluding screenshot stalls and recovery."""
import csv,json,statistics,math,argparse
from pathlib import Path
ROOT=Path('C:/GrandTour');QA=ROOT/'Saved/LidarAuthoringQA/RS7'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def run(label):
 info=read(QA/f'runtime-{label}.json');assert info['exit_code']==0
 assert info.get('render_validation_passed',True),info.get('shader_failures')
 log=Path(info['log']).read_text(encoding='utf-8',errors='replace')
 assert not any(t in log for t in ['missing usage flag','Default Material will be used','Failed to compile Material']),label+' has a material fallback'
 with open(info['csv'],newline='') as f:rows=list(csv.DictReader(f))
 keys=[k for k in rows[0] if k in ['GPUTime','FrameTime','GPUMem/LocalUsedMB','GPUMem/LocalBudgetMB'] or k.startswith('NaniteStreaming/') or (k.startswith('GPU/') and any(s in k.lower() for s in ['basepass','prepass','shadow','nanite','temporal']))]
 views={}
 for i,v in enumerate(info['views']):
  start=200+i*info['frames_per_view'];samples=rows[start+150:start+265]+rows[start+325:start+390]
  result={}
  for key in keys:
   values=[float(r[key]) for r in samples if r.get(key)]
   if values:result[key]=dict(median=statistics.median(values),mean=statistics.mean(values),p95=sorted(values)[math.ceil(len(values)*.95)-1],max=max(values),n=len(values))
  views[v['view']]=result
 return dict(label=label,csv=info['csv'],views=info['views'],commands=info['commands'],extra_commands=info.get('extra_commands',[]),startup_arguments=info.get('startup_arguments',[]),measurements=views)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('labels',nargs='+');a=p.parse_args();runs=[run(l) for l in a.labels]
 path=ROOT/'Saved/LidarAuthoringQA/PerceivedDetail/measurements.json';old=read(path) if path.exists() else {}
 old.update({r['label']:r for r in runs});path.write_text(json.dumps(old,indent=2))
 for r in runs:print(r['label'],json.dumps({v:round(m['GPUTime']['median'],3) for v,m in r['measurements'].items()}))
 if len(runs)>1:
  base=runs[0]
  for r in runs[1:]:print(r['label']+' delta',json.dumps({v:round(m['GPUTime']['median']-base['measurements'][v]['GPUTime']['median'],3) for v,m in r['measurements'].items() if v in base['measurements']}))
