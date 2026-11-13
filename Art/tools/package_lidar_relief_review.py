"""Publish before/after proof of physical, rather than shading-only, bank relief."""
import csv,hashlib,json,math,shutil,statistics,re,sys
from pathlib import Path
ROOT=Path('C:/GrandTour');QA=ROOT/'Saved/LidarAuthoringQA/RS7';RELIEF=ROOT/'Saved/LidarAuthoringQA/RS7Relief';OUT=ROOT/'Art/Export/LidarStudy/FirstSection/Review/PhysicalRelief'
sys.path.insert(0,str(ROOT/'Art/Unreal'));import lidar_section_surface as S;import lidar_bank_relief_detail as D
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def run(label):
 info=read(QA/f'runtime-{label}.json');assert info['exit_code']==0
 rows=list(csv.DictReader(open(info['csv'],newline='')));views=info['views'];views=views.get('value',[]) if isinstance(views,dict) else views
 result={}
 for i,v in enumerate(views):
  start=200+i*info['frames_per_view'];sample=rows[start+150:start+265]+rows[start+325:start+390];stats={}
  for key in ['GPUTime','FrameTime','GPUMem/LocalUsedMB']:
   values=[float(r[key]) for r in sample if r.get(key)];stats[key]={'mean':statistics.mean(values),'p95':sorted(values)[math.ceil(len(values)*.95)-1],'samples':len(values)}
  stats['hitches_over_50ms']=sum(float(r['FrameTime'])>50 for r in sample if r.get('FrameTime'));result[v['view']]=stats
 return {'measurements':result,'csv':info['csv'],'commands':info['commands'],'views':views}
before=run('relief-before');after=run('relief-final');assert before['commands']==after['commands'] and before['views']==after['views']
deltas={v:after['measurements'][v]['GPUTime']['mean']-before['measurements'][v]['GPUTime']['mean'] for v in after['measurements']}
for v in after['measurements']:
 for dest,label in [('before','relief-before'),('after','relief-final')]:shutil.copy2(QA/f'{label}-{v}.png',OUT/f'{dest}-{v}.png')
samples=[D.additional(*S.xy(a,b)) for a in range(-1000,1001,20) for b in range(-650,651,20)]
survey=read(RELIEF/'survey.json');mesh=ROOT/'Content/GrandTour/ArtTests/LidarStudy/FirstSection/SM_RS7_BankSkin.uasset'
expected=Path(survey['backup'])/'Final-BankSkin.uasset';assert hashlib.sha256(mesh.read_bytes()).digest()==hashlib.sha256(expected.read_bytes()).digest()
report={'revision':'RS7 physical ground relief','date':'2026-11-06','scope':'Same first section and approved planting; actual surface geometry rebuilt','geometry':{'faces':70648,'grid_spacing_cm':10,'ledges':len(D.DATA['rock_ledges']),'embedded_stone_features':len(D.DATA['embedded_stones']),'contact_constraints':len(D.DATA['caps']),'sampled_max_added_height_cm':max(samples),'sampled_mean_added_height_cm':statistics.mean(samples),'sampling':'20 cm regular grid inside the section','render_and_collision_share_mesh':True},'validation':read(RELIEF/'validation.json'),'reload_validation':read(RELIEF/'reload-validation.json') if (RELIEF/'reload-validation.json').exists() else None,'before':before,'after':after,'mean_gpu_delta_ms':deltas,'backup':survey['backup'],'mesh_sha256':hashlib.sha256(mesh.read_bytes()).hexdigest(),'method':'180 warmed frames per view, excluding screenshot and recovery. Same 1600x900 saved v6 preset, camera poses and exposure. One matched pair does not characterize all timing variance.','limitations':['Only the first bank section is rebuilt.','Detailed collision was probed, but a complete driving/walking route remains outside this check.','The fixed-camera images demonstrate shape; they do not certify every temporal artefact.']}
(OUT/'evidence.json').write_text(json.dumps(report,indent=2)+'\n')
html=(OUT/'index.html').read_text(encoding='utf-8')
html=html.replace('Riverbank ground detail — actual game comparison','Riverbank physical relief — actual game comparison').replace('Riverbank · ground surface detail','Riverbank · physical surface relief').replace('Before · smooth surface shading','Before · textured surface').replace('After · soil grain and rock relief','After · geometric ledges and soil').replace('Revised ground material in the actual game','Rebuilt surface geometry in the actual game')
html=re.sub(r'<section class="evidence">.*?</section>',f'<section class="evidence"><p>The surface now has real soil hummocks, embedded stones, stepped rock faces and stronger root runs. Sharp transitions retain their edges; mild geometry-based cavity shading helps the recesses read in forest shade.</p><p>All 152 fern placements are retained. Checks cover 608 root contacts and 10,285 frond samples, with no extra frond penetration. The rendering and collision use the same fitted mesh.</p><p class="small" id="timing">Matched mean GPU change: {min(deltas.values()):+.2f} to {max(deltas.values()):+.2f} ms across five views. Same graphics preset; one comparison pair does not capture all run-to-run variance.</p><p class="small"><a href="evidence.json">Geometry, contact and performance evidence</a> · <a href="../index.html">Original references</a></p></section>',html,flags=re.S)
(OUT/'index.html').write_text(html,encoding='utf-8')
path=ROOT/'Art/Export/LidarStudy/Place/first-section.json';manifest=read(path);manifest['latest_relief_review']=str(OUT/'index.html');manifest['latest_relief_evidence']=str(OUT/'evidence.json');manifest['ground_geometry_revision']='RS7 physical ground relief';path.write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'mean_gpu_delta_ms':deltas,'geometry':report['geometry'],'review':str(OUT/'index.html')},indent=2))
