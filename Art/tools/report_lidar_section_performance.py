"""Compare matched warmed stationary windows; never mix screenshot stalls into timing."""
import csv,json,statistics,math
from pathlib import Path
ROOT=Path('C:/GrandTour');QA=ROOT/'Saved/LidarAuthoringQA/RS7'
def percentile(xs,p):
 xs=sorted(xs);return xs[min(len(xs)-1,math.ceil(len(xs)*p)-1)]
def read(label):
 info=json.loads((QA/('runtime-'+label+'.json')).read_text());rows=list(csv.DictReader(open(info['csv'],newline='')));out={}
 views=info['views'];views=views.get('value',[]) if isinstance(views,dict) else views
 for i,v in enumerate(views):
  # B03 baseline camera was below terrain and was corrected for the candidate.
  if v['view']=='B03':continue
  start=200+i*info['frames_per_view'];selected=rows[start+150:start+265]+rows[start+325:start+390]
  stats={}
  for key in ['FrameTime','GPUTime','GPUMem/LocalUsedMB','GPUMem/LocalBudgetMB','GPU/Basepass','GPU/ShadowDepths']:
   values=[]
   for r in selected:
    try:values.append(float(r[key]))
    except (KeyError,ValueError,TypeError):pass
   if values:stats[key]={'mean':statistics.mean(values),'p95':percentile(values,.95),'max':max(values),'samples':len(values)}
  ft=[float(r['FrameTime']) for r in selected if r.get('FrameTime')]
  stats['hitches_over_50ms']=sum(x>50 for x in ft);out[v['view']]=stats
 return out
labels=[p.name.removeprefix('runtime-').removesuffix('.json') for p in QA.glob('runtime-*.json')]
result={'resolution':[1600,900],'preset':'saved v6','window':'180 frames per view after warmup; screenshot and post-shot recovery excluded','excluded_view':'B03 camera corrected; no matched baseline','runs':{label:read(label) for label in labels}}
base='baseline-final' if 'baseline-final' in labels else 'baseline-repeat'
candidate='final' if 'final' in labels else 'candidate'
if base in labels and candidate in labels:
 result['comparison']={'baseline':base,'candidate':candidate}
 result['gpu_delta_ms']={v:result['runs'][candidate][v]['GPUTime']['mean']-result['runs'][base][v]['GPUTime']['mean'] for v in result['runs'][candidate]}
(QA/'performance-comparison.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='runs'},indent=2))
for label,data in result['runs'].items():print(label,{v:round(s['GPUTime']['mean'],2) for v,s in data.items()})
