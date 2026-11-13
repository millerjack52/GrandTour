"""Package unretouched map-wide game captures and their matched measurements."""
import json,re,shutil,hashlib
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from measure_perceived_detail import run
ROOT=Path('C:/GrandTour');QA=ROOT/'Saved/LidarAuthoringQA/ForestGround';CAP=ROOT/'Saved/LidarAuthoringQA/RS7'
OUT=ROOT/'Art/Export/LidarStudy/Place/ForestGround/Review';OUT.mkdir(parents=True,exist_ok=True)
before=run('forest-ground-before');after=run('forest-ground-after')
assert before['views']==after['views'] and before['commands']==after['commands']
assert not before['extra_commands'] and after['extra_commands']==['gt.ForestGround.Report 1']
installed=json.loads((QA/'installed.json').read_text());assert installed['ok']
backup=json.loads((QA/'backup.json').read_text())
for rel,digest in backup['files'].items():
    if rel.endswith(('L_LidarStudy.umap','M_Terrain.uasset','M_Detail.uasset')):continue
    assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==digest,rel
for rel,digest in json.loads((QA/'source-map-hashes.json').read_text()).items():
    assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==digest,rel
metrics={}
for v in before['measurements']:
    metrics[v]={k:r['measurements'][v]['GPUTime']['median'] for k,r in [('before',before),('after',after)]}
    metrics[v]['delta']=metrics[v]['after']-metrics[v]['before']
    for side,r in [('before',before),('after',after)]:shutil.copy2(CAP/(r['label']+'-'+v+'.png'),OUT/(side+'-'+v+'.png'))
runtime=json.loads((CAP/'runtime-forest-ground-after.json').read_text(encoding='utf-8-sig'))
log=Path(runtime['log']).read_text(encoding='utf-8',errors='replace')
streaming=re.findall(r'FOREST_GROUND active=.*',log)
assert streaming and all('configured=1' in line and 'pending=0' in line for line in streaming)
assert any(int(re.search(r'active=(\d+)',line)[1])>0 for line in streaming)
refs={'site-forest.jpg':ROOT/'Art/References/Waimeamea/08_bush_interior_crown_fern_pole_beech_mud.jpg','original-style.jpg':ROOT/'Art/References/ReferenceStyle/2026-11-05.jpg'}
for name,path in refs.items():shutil.copy2(path,OUT/name)
shutil.copy2(OUT.parent/'T_FG_Coverage.png',OUT/'coverage.png')
record=dict(installation=installed,before=before,after=after,metrics=metrics,streaming=streaming,
    performance='One matched warmed pair; indicative, not full-route certification. After enables diagnostic logging only.',
    scope='Eligible woodland across the map. Reviewed riverbank, roads, pasture, water, rocks, physics and existing plant transforms protected.',
    owner_visual_acceptance='PENDING',limitations=['Long-range canopy shaders are the next phase.','Geometry is local to the first player camera, with a 23–30m fade.','Steep or sharply curved terrain receives material detail without raised mats.','Earlier perceived-detail performance gate remains unresolved.'],
    map_sha256=hashlib.sha256((ROOT/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap').read_bytes()).hexdigest())
record['bounds']=json.loads((QA/'bounds.json').read_text())
record['lods']=json.loads((QA/'lods.json').read_text())
assetroot=ROOT/'Content/GrandTour/ArtTests/LidarStudy'
record['asset_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [assetroot/'M_Terrain.uasset',assetroot/'M_Detail.uasset',*(assetroot/'ForestGround').glob('*.uasset')]}
(OUT/'evidence.json').write_text(json.dumps(record,indent=2))
labels={'W01':'Dense western understory','W02':'Eastern slope','W03':'Southern woodland','W04':'Northwest clearing','B04':'River boundary','F01':'Pasture boundary','F02':'Bush track','G01':'Approved first section'}
buttons=''.join(f'<button onclick="view(\'{v}\')">{name}</button>' for v,name in labels.items())
rows=''.join(f'<tr><td>{labels[v]}</td><td>{m["before"]:.2f}</td><td>{m["after"]:.2f}</td><td>{m["delta"]:+.2f}</td></tr>' for v,m in metrics.items())
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Map-wide forest floor — game review</title><style>
body{margin:24px;background:#19221b;color:#eee8dc;font:16px/1.5 system-ui}main{max-width:1700px;margin:auto}h1{font-size:30px}h2{font-size:22px}p{max-width:1100px}a{color:#b8dbad}.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}.pair img{width:100%;height:auto}.ref{max-height:650px;object-fit:contain;object-position:top;background:#101912}button{padding:10px 16px;font:inherit;background:#354a37;color:white;border:1px solid #8b9b78;cursor:pointer}nav{display:flex;gap:10px;flex-wrap:wrap}td,th{text-align:left;padding:8px 20px 8px 0}tr{border-bottom:1px solid #506249}video{width:100%;max-width:1200px}@media(max-width:900px){.pair{grid-template-columns:1fr}}</style>
<main><h1>Forest-floor treatment across the LiDAR map</h1><p>10.36 km² of eligible woodland now shares the approved peat, patchy moss, small litter and embedded-root treatment. Raised detail follows the camera and fits the local slope. Roads, pasture, exposed rock, water and the approved riverbank are excluded.</p><nav>BUTTONS</nav>
<div class="pair"><section><h2>Before — actual game</h2><a id="beforeLink"><img id="before" alt="Actual game before rollout"></a></section><section><h2>After — actual game</h2><a id="afterLink"><img id="after" alt="Actual game after rollout"></a></section></div><p>Unretouched standalone captures. Identical cameras, saved v6 settings, 1600 × 900. Click for full resolution.</p>
<h2>Reference photographs</h2><div class="pair"><section><h3>Site photo — material identity and scale</h3><a href="site-forest.jpg"><img class="ref" src="site-forest.jpg" alt="Owner woodland photograph"></a></section><section><h3>Original reference — style and colour</h3><a href="original-style.jpg"><img class="ref" src="original-style.jpg" alt="Owner original style reference"></a></section></div>
<h2>Coverage and checks</h2><p><a href="coverage.png">View the woodland coverage mask</a>. Existing local and map-wide plant transforms are unchanged. The runtime details have no collision. Terrain deformation and native mud state retain precedence.</p><table><tr><th>View</th><th>Before GPU ms</th><th>After GPU ms</th><th>Delta ms</th></tr>ROWS</table><p>One matched warmed pair: indicative cost, not a full-route performance gate. Long-range forest shaders remain the next phase. <a href="evidence.json">Full evidence</a> · <a href="../recipe.json">Recipe</a></p>MOTION</main>
<script>function view(v){for(const s of ['before','after']){const p=s+'-'+v+'.png';document.getElementById(s).src=p;document.getElementById(s+'Link').href=p}}view('W02')</script></html>'''
motion='<h2>Moving game view</h2><video controls loop muted src="forest-motion.mp4"></video><p>12 fps viewport samples for visual inspection; this playback is not a frame-rate benchmark.</p>' if (OUT/'forest-motion.mp4').exists() else ''
(OUT/'index.html').write_text(page.replace('BUTTONS',buttons).replace('ROWS',rows).replace('MOTION',motion),encoding='utf-8')
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',26)
board=Image.new('RGB',(1600,1000),'#19221b');draw=ImageDraw.Draw(board)
for row,v in enumerate(['W02','W03']):
    for col,side in enumerate(['before','after']):
        x=col*800;y=row*500;draw.text((x+14,y+8),labels[v]+' — '+side+' (game)',font=font,fill='white')
        board.paste(Image.open(OUT/(side+'-'+v+'.png')).resize((800,450),Image.Resampling.LANCZOS),(x,y+45))
board.save(OUT/'comparison.jpg',quality=95)
board=Image.new('RGB',(1600,1060),'#19221b');draw=ImageDraw.Draw(board)
for x,v in [(0,'W02'),(800,'W03')]:
    draw.text((x+14,10),'Actual game — '+labels[v],font=font,fill='white');im=Image.open(OUT/('after-'+v+'.png'));im.thumbnail((800,450));board.paste(im,(x,50))
draw.text((14,530),'Site photo — ground identity',font=font,fill='white');im=Image.open(OUT/'site-forest.jpg');im.thumbnail((800,490));board.paste(im,(0,570))
draw.text((814,530),'Original style — landscape crop',font=font,fill='white');im=Image.open(OUT/'original-style.jpg').crop((0,75,591,666));im.thumbnail((800,490));board.paste(im,(800,570))
board.save(OUT/'references-alongside.jpg',quality=95)
print(json.dumps(metrics,indent=2));print(OUT/'index.html')
