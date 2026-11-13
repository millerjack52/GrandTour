"""Summarize PF60 standalone CSV windows, excluding teleport/capture warm-up."""
import csv,json,statistics,sys,re,math
from pathlib import Path
csv.field_size_limit(2**24)
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/LidarStudy/Place'
def stats(v):
 v=sorted(v);mean=statistics.fmean(v)
 return dict(mean_ms=round(mean,3),p95_ms=round(v[int(.95*len(v))],3),p99_ms=round(v[int(.99*len(v))],3),max_ms=round(v[-1],3),samples=len(v))
def analyze(label):
 meta=json.loads((OUT/('playperf-'+label+'.json')).read_text(encoding='utf-8-sig'))
 assert meta['exit_code']==0
 poses=meta['poses'];poses=poses.get('value',[]) if isinstance(poses,dict) else poses
 with Path(meta['csv'][0]).open(newline='') as f:rows=list(csv.reader(f))
 header=rows[0];data=[]
 for row in rows[1:]:
  try:float(row[header.index('FrameTime')])
  except (ValueError,IndexError):break
  data.append(row)
 report=dict(label=label,resolution=meta['resolution'],commands=meta['commands'],csv=meta['csv'][0],frame_time_method=meta.get('frame_time_method','legacy_boot_capture'),scope='Standalone offscreen game, '+('on-foot camera' if meta.get('on_foot') else 'chase camera')+'; excludes loading, teleports and screenshot frames; not display presentation timing',sites=[])
 log=Path(meta['log']).read_text(errors='replace');assert log.count('LogCheatManager: BugItGo to:')==len(poses),'Missing pose changes'
 positions=[tuple(map(float,m)) for m in re.findall(r'LogCheatManager: BugItGo ([-\d.]+) ([-\d.]+) ([-\d.]+)',log)]
 for index,pose in enumerate(poses):
  start=meta['first_site_frame']+index*meta['frames_per_site']
  # Driving begins at +350, ends +850. Leave the initial launch frames out.
  lo,hi=(start+400,start+840) if meta.get('drive') or meta.get('walk') else (start+350,start+meta['frames_per_site']-10)
  sample=data[lo:hi];assert len(sample)==hi-lo,(pose['name'],len(data),lo,hi)
  cols={name:stats([float(row[header.index(name)]) for row in sample]) for name in ['FrameTime','GPUTime','GameThreadTime']}
  times=[float(row[header.index('FrameTime')]) for row in sample]
  top=sorted([(name,statistics.fmean(float(row[i]) for row in sample)) for i,name in enumerate(header) if name.startswith('GPU/')],key=lambda x:x[1],reverse=True)[:8]
  result=dict(name=pose['name'],frames=[lo,hi],fps_mean=round(1000/cols['FrameTime']['mean_ms'],1),over_16_9ms_percent=round(100*sum(t>16.9 for t in times)/len(times),2),over_120fps_budget_percent=round(100*sum(t>1000/120 for t in times)/len(times),2),columns=cols,gpu_pass_mean_ms={k:round(v,3) for k,v in top})
  if len(positions)==2*len(poses):result['travel_xy_m']=round(math.dist(positions[index*2][:2],positions[index*2+1][:2])*.01,2)
  if 'DynamicResolutionPercentage' in header:
   values=[float(row[header.index('DynamicResolutionPercentage')]) for row in sample]
   result['render_scale_percent']=dict(min=round(min(values),2),mean=round(statistics.fmean(values),2),max=round(max(values),2))
  if meta.get('distance_ab'):
   result['distance_ab']={}
   for phase,a,b in [('on',1400,1690),('off',1850,2140)]:
    result['distance_ab'][phase]={name:stats([float(row[header.index(name)]) for row in data[start+a:start+b]]) for name in ['FrameTime','GPUTime','GameThreadTime']}
  report['sites'].append(result)
  print(pose['name'],result['fps_mean'],'fps', 'frame',cols['FrameTime'],'gpu',cols['GPUTime'])
 report['meets_stationary_target']=not (meta.get('drive') or meta.get('walk')) and all(s['columns']['FrameTime']['p95_ms']<=16.9 for s in report['sites'])
 report['meets_60fps_p95']=all(s['columns']['FrameTime']['p95_ms']<=16.9 for s in report['sites'])
 report['meets_120fps_p95']=all(s['columns']['FrameTime']['p95_ms']<=1000/120 for s in report['sites'])
 report['drive']=meta.get('drive',False)
 report['walk']=meta.get('walk',False)
 (OUT/('playperf-'+label+'-summary.json')).write_text(json.dumps(report,indent=2));return report
def analyze_routes(label):
 folder=ROOT/'Saved/LidarAuthoringQA/Rally'
 source=json.loads((folder/(label+'.json')).read_text())
 assert source['ok'],source.get('error')
 report=dict(label=label,requested_resolution=source.get('requested_resolution',[1600,900]),viewport_resolution=source.get('viewport_resolution'),gc_stress=source.get('gc_stress',False),scope='Offscreen Play-in-Editor with automated route driver; includes editor and Python overhead, not standalone or presentation timing. Requested window 1600x900; actual viewport recorded separately when available.',runs=[])
 for run in source['runs']:
  with Path(run['csv']).open(newline='') as f:
   reader=csv.reader(f);header=next(reader);data=[]
   for row in reader:
    try:float(row[header.index('FrameTime')])
    except (ValueError,IndexError):break
    data.append(row)
  assert data,run['csv']
  # No teleport or screenshot is inside these captures. Report the whole drive,
  # including launch/streaming costs; do not discard its slow frames.
  cols={name:stats([float(row[header.index(name)]) for row in data]) for name in ['FrameTime','GPUTime','GameThreadTime']}
  times=[float(row[header.index('FrameTime')]) for row in data]
  result=dict(road=run['road'],csv=run['csv'],distance_m=run['distance_m'],peak_kmh=run['peak_kmh'],fps_mean=round(1000/statistics.fmean(times),1),columns=cols,over_120fps_budget_percent=round(100*sum(t>1000/120 for t in times)/len(times),2))
  gc_name='Exclusive/GameThread/GarbageCollection'
  if gc_name in header:
   active=[float(row[header.index(gc_name)]) for row in data if float(row[header.index(gc_name)])>.01]
   result['gc_active_frames']=stats(active) if active else None
  if 'GC/Count' in header:result['gc_cycles']=sum(float(row[header.index('GC/Count')]) for row in data)
  report['runs'].append(result)
  print(result['road'],result['fps_mean'],'fps',cols['FrameTime'])
 report['meets_120fps_p95']=all(r['columns']['FrameTime']['p95_ms']<=1000/120 for r in report['runs'])
 (folder/(label+'-perf.json')).write_text(json.dumps(report,indent=2))
 return report

if __name__=='__main__':
 if sys.argv[1]=='--routes':analyze_routes(sys.argv[2])
 else:analyze(sys.argv[1])
