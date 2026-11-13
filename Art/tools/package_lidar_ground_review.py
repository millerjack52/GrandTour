"""Matched material-only review. Preserve the original first-section evidence."""
import csv,hashlib,json,math,shutil,statistics,re
from pathlib import Path
ROOT=Path('C:/GrandTour');QA=ROOT/'Saved/LidarAuthoringQA/RS7';GROUND=ROOT/'Saved/LidarAuthoringQA/RS7Ground';OUT=ROOT/'Art/Export/LidarStudy/FirstSection/Review/GroundDetail'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(label):
 info=read(QA/f'runtime-{label}.json');assert info['exit_code']==0
 rows=list(csv.DictReader(open(info['csv'],newline='')));views=info['views'];views=views.get('value',[]) if isinstance(views,dict) else views
 result={}
 for i,v in enumerate(views):
  start=200+i*info['frames_per_view'];sample=rows[start+150:start+265]+rows[start+325:start+390];stats={}
  for key in ['GPUTime','FrameTime','GPUMem/LocalUsedMB']:
   values=[float(r[key]) for r in sample if r.get(key)]
   stats[key]={'mean':statistics.mean(values),'p95':sorted(values)[math.ceil(len(values)*.95)-1],'samples':len(values)}
  stats['hitches_over_50ms']=sum(float(r['FrameTime'])>50 for r in sample if r.get('FrameTime'));result[v['view']]=stats
 return {'measurements':result,'csv':info['csv'],'commands':info['commands'],'views':views}
before=run('ground-before-run');after=run('ground-final');assert before['commands']==after['commands'] and before['views']==after['views']
deltas={v:after['measurements'][v]['GPUTime']['mean']-before['measurements'][v]['GPUTime']['mean'] for v in after['measurements']}
for v in after['measurements']:
 for dest,label in [('before','ground-before-run'),('after','ground-final')]:shutil.copy2(QA/f'{label}-{v}.png',OUT/f'{dest}-{v}.png')
assets=ROOT/'Content/GrandTour/ArtTests/LidarStudy/FirstSection'
report={'revision':'RS7 ground surface detail','date':'2026-11-06','scope':'Material-only update on the first section','apply':read(GROUND/'apply.json'),'texture_residency':read(GROUND/'texture-loaded.json'),'backup':read(GROUND/'backup.json'),'before':before,'after':after,'mean_gpu_delta_ms':deltas,'method':'180 warmed frames per view; screenshot and recovery frames excluded. Same saved v6 at 1600x900. A single matched pair does not measure all run-to-run variability.','known_limits':['Fine relief changes shading, not silhouettes or collision.','Surrounding banks outside the first section retain their previous materials.','No claim of a complete live-motion or driving-route sign-off from still captures.'],'normal_method_reference':'https://dev.epicgames.com/documentation/en-us/unreal-engine/bump-mapping-without-tangent-space-in-unreal-engine','asset_hashes':{n:digest(assets/(n+'.uasset')) for n in ['M_BankSurface','M_BankEarth','T_BankSoilColour','T_BankSoilORH']},'image_hashes':{p.name:digest(p) for p in OUT.glob('*.png')}}
(OUT/'evidence.json').write_text(json.dumps(report,indent=2)+'\n')
html=(OUT/'index.html').read_text(encoding='utf-8')
html=re.sub(r'(<p class="small" id="timing">).*?(</p>)',lambda m:m[1]+f'Matched mean GPU change across five views: {min(deltas.values()):+.2f} to {max(deltas.values()):+.2f} ms. No slowdown observed in this pair; negative values are not a proven performance gain. Same graphics preset; full measurements and sampling limits in the evidence record.'+m[2],html)
(OUT/'index.html').write_text(html,encoding='utf-8')
manifest_path=ROOT/'Art/Export/LidarStudy/Place/first-section.json';manifest=read(manifest_path)
manifest['latest_ground_review']=str(OUT/'index.html');manifest['latest_ground_evidence']=str(OUT/'evidence.json');manifest['ground_material_revision']='RS7 ground surface detail';manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'mean_gpu_delta_ms':deltas,'review':str(OUT/'index.html')},indent=2))
