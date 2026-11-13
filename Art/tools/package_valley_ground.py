"""Matched valley-distance game captures and protected-asset evidence."""
from pathlib import Path
import json,hashlib,shutil,math
from PIL import Image,ImageDraw,ImageFont
from measure_perceived_detail import run
ROOT=Path('C:/GrandTour');QA=ROOT/'Saved/LidarAuthoringQA/ValleyGround';CAP=ROOT/'Saved/LidarAuthoringQA/RS7'
OUT=ROOT/'Art/Export/LidarStudy/Place/ValleyGround/Review';OUT.mkdir(parents=True,exist_ok=True)
before=run('valley-ground-before');after=run('valley-ground-after')
assert before['views']==after['views'] and before['commands']==after['commands'] and before['extra_commands']==after['extra_commands']
installation=json.loads((QA/'installed.json').read_text());assert installation['ok']
verification=json.loads((QA/'verified.json').read_text());assert verification['ok']
prepared=json.loads((QA/'prepared.json').read_text())
for rel,digest in prepared['protected'].items():
    if rel.endswith(('M_Terrain.uasset','M_Detail.uasset')):continue
    assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==digest,rel
metrics={}
for v in before['measurements']:
    metrics[v]={s:r['measurements'][v]['GPUTime']['median'] for s,r in [('before',before),('after',after)]}
    metrics[v]['delta']=metrics[v]['after']-metrics[v]['before']
    for s,r in [('before',before),('after',after)]:shutil.copy2(CAP/(r['label']+'-'+v+'.png'),OUT/(s+'-'+v+'.png'))
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',25)
board=Image.new('RGB',(1600,970),'#19221b');draw=ImageDraw.Draw(board)
for j,v in enumerate(['V02','V01']):
    for col,s in enumerate(['before','after']):
        draw.text((col*800+12,j*485+8),s.title()+' — '+('across the valley' if j==0 else 'down into the valley'),font=font,fill='white')
        im=Image.open(OUT/(s+'-'+v+'.png'));board.paste(im.resize((800,450),Image.Resampling.LANCZOS),(col*800,j*485+35))
board.save(OUT/'comparison.jpg',quality=95)
shutil.copy2(ROOT/'Art/References/ReferenceStyle/2026-11-05.jpg',OUT/'original-reference.jpg')
shutil.copy2(ROOT/'Art/References/Waimeamea/02_house_shed_gravel_yard_bush_hill.jpg',OUT/'site-reference.jpg')
distances={v['view']:round(math.dist(v['position'],v['target'])/100) for v in before['views']}
record=dict(installation=installation,verification=verification,before=before,after=after,metrics=metrics,camera_target_distances_m=distances,
    method='One world-aligned map carrying approximate canopy enclosure and broad ground-cover variation, blended from 45 to 140 metres. Derivative normals give broad cover modest lighting relief. Existing woodland eligibility excludes roads, pastures, water, exposed rock and the approved local bank.',
    scope='Terrain and detail materials only; three review cameras added. Planting, canopy shaders, lighting, physics and close floor assets unchanged.',
    limitations=['Enclosure is an approximation from existing canopy bases, not directional shadows or a 3D AO bake.','Does not replace missing distant understory geometry or improve crossed-card canopy silhouettes.','One matched warmed GPU pair; full-route performance acceptance remains open.'],
    owner_visual_acceptance='pending',references=['https://dev.epicgames.com/documentation/unreal-engine/landscape-materials-in-unreal-engine'])
(OUT/'evidence.json').write_text(json.dumps(record,indent=2))
buttons=''.join(f'<button onclick="view(\'{v}\')">{v} · {distances[v]} m to target</button>' for v in ['V02','V01','V03','G01'])
rows=''.join(f'<tr><td>{v}</td><td>{r["before"]:.2f}</td><td>{r["after"]:.2f}</td><td>{r["delta"]:+.2f}</td></tr>' for v,r in metrics.items())
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Valley forest floor — game review</title><style>body{margin:24px;background:#19221b;color:#eee8dc;font:16px/1.5 system-ui}main{max-width:1800px;margin:auto}.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}img{width:100%;height:auto}button{padding:10px 16px;font:inherit;background:#354a37;color:white;border:1px solid #8b9b78;cursor:pointer}nav{display:flex;gap:10px;flex-wrap:wrap}a{color:#b8dbad}td,th{text-align:left;padding:8px 20px 8px 0}.refs img{max-height:650px;object-fit:contain;object-position:top}@media(max-width:900px){.pair{grid-template-columns:1fr}}</style><main><h1>Ground beneath the forest, viewed across the valleys</h1><p>The previous floor resolved to an almost uniform colour beyond 60 metres. This pass carries broad ground-cover variation, approximate canopy enclosure and subdued lighting relief into valley views. It uses the existing tree positions and adds no vegetation instances.</p><nav>BUTTONS</nav><div class="pair"><section><h2>Before</h2><a id="beforeLink"><img id="before" alt="Before — actual game"></a></section><section><h2>After</h2><a id="afterLink"><img id="after" alt="After — actual game"></a></section></div><p>Same saved map, camera, exposure and v6 rendering settings. Actual 1600 × 900 game captures; click for full resolution. Distances identify the camera target, with nearer and farther terrain visible in each frame. G01 is the close-ground regression view.</p><h2>References</h2><div class="pair refs"><img src="original-reference.jpg" alt="Original woodland style reference"><img src="site-reference.jpg" alt="Site photograph of forest behind the house"></div><h2>Measured GPU time</h2><table><tr><th>View</th><th>Before ms</th><th>After ms</th><th>Delta ms</th></tr>ROWS</table><p>One matched warmed pair. Broad material shading does not replace understory geometry or fix distant tree silhouettes. <a href="evidence.json">Validation, limitations and source</a>.</p></main><script>function view(v){for(const s of ['before','after']){let p=s+'-'+v+'.png';document.getElementById(s).src=p;document.getElementById(s+'Link').href=p}}view('V02')</script></html>'''
(OUT/'index.html').write_text(page.replace('BUTTONS',buttons).replace('ROWS',rows),encoding='utf-8')
print(json.dumps(metrics,indent=2));print(OUT/'index.html')
