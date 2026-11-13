"""Unretouched game evidence beside owner photos and explicitly labelled concepts."""
from pathlib import Path
import json,shutil,hashlib
from PIL import Image,ImageDraw,ImageFont
from measure_perceived_detail import run
ROOT=Path('C:/GrandTour');QA=ROOT/'Saved/LidarAuthoringQA/PeatMoss';CAP=ROOT/'Saved/LidarAuthoringQA/RS7'
OUT=ROOT/'Art/Export/LidarStudy/FirstSection/Review/PeatMoss';OUT.mkdir(parents=True,exist_ok=True)
before=run('peat-moss-before');after=run('peat-moss-after')
assert before['views']==after['views'] and before['commands']==after['commands'] and before['extra_commands']==after['extra_commands']
installed=json.loads((QA/'installed.json').read_text());assert installed['ok']
metrics={}
for view in before['measurements']:
    metrics[view]={side:r['measurements'][view]['GPUTime']['median'] for side,r in [('before',before),('after',after)]}
    metrics[view]['delta']=metrics[view]['after']-metrics[view]['before']
    for side,r in [('before',before),('after',after)]:shutil.copy2(CAP/(r['label']+'-'+view+'.png'),OUT/(side+'-'+view+'.png'))
refs={'site-forest.jpg':ROOT/'Art/References/Waimeamea/08_bush_interior_crown_fern_pole_beech_mud.jpg',
      'original-style.jpg':ROOT/'Art/References/ReferenceStyle/2026-11-05.jpg',
      'material-concept.png':ROOT/'Art/References/ReferenceStyle/PhotoBased/waimeamea-ground-materials-v01.png',
      'implementation-concept.png':ROOT/'Art/References/ReferenceStyle/PhotoBased/waimeamea-ground-implementation-v01.png'}
for name,path in refs.items():shutil.copy2(path,OUT/name)
record=dict(installation=installed,before=before,after=after,metrics=metrics,
    reference_roles={'site-forest.jpg':'Owner site photo: material identity and scale','original-style.jpg':'Owner original style: colour grouping and authored readable shapes','material-concept.png':'Generated direction only; not game evidence','implementation-concept.png':'Generated implementation illustration; not game evidence'},
    owner_visual_acceptance='PENDING',performance='One matched warmed pair; indicative, not a repeated or full-route performance gate',
    scope='Existing bank surface material and replacement of its decorative fitted floor. Underlying bank mesh/collision, plants, other existing material packages, lighting and renderer settings unchanged.',
    limitations=['Ground concept is a target, not proof of an exact visual match.','Static contact bake must be rebuilt after terrain or plant layout changes.','River gravel remains a separate follow-up.','Earlier global perceived-detail performance gate remains unresolved.'],
    map_sha256=hashlib.sha256((ROOT/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap').read_bytes()).hexdigest())
(OUT/'evidence.json').write_text(json.dumps(record,indent=2))
rows=''.join(f'<tr><td>{v}</td><td>{m["before"]:.2f}</td><td>{m["after"]:.2f}</td><td>{m["delta"]:+.2f}</td></tr>' for v,m in metrics.items())
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Peat and moss — actual game review</title><style>
body{margin:24px;background:#19221b;color:#eee8dc;font:16px/1.5 system-ui}main{max-width:1700px;margin:auto}h1{font-size:30px}h2{font-size:22px}p{max-width:1100px}a{color:#b8dbad}.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}.pair img{width:100%;height:auto}.ref{max-height:650px;width:100%;object-fit:contain;object-position:top;background:#101912}button{padding:10px 16px;font:inherit;background:#354a37;color:white;border:1px solid #8b9b78;cursor:pointer}nav{display:flex;gap:10px;flex-wrap:wrap}td,th{text-align:left;padding:8px 20px 8px 0}table{border-collapse:collapse}tr{border-bottom:1px solid #506249}video{width:100%;max-width:1200px}@media(max-width:900px){.pair{grid-template-columns:1fr}}</style>
<main><h1>Peat, roots and moss — actual game review</h1><p>The green base is replaced with dark peat and small root/litter detail. Irregular moss patches share the same outline in the ground material and fitted raised geometry. Fallen leaves are smaller; roots remain embedded. The existing terrain, collision, plant positions and lighting are preserved.</p>
<nav><button onclick="view('G01')">Ground close-up</button><button onclick="view('D01')">Low oblique view</button><button onclick="view('B01')">Riverbank</button><button onclick="view('B04')">Across the river</button></nav>
<div class="pair"><section><h2>Before — actual game</h2><a id="beforeLink"><img id="before" alt="Actual game before peat and moss"></a></section><section><h2>After — actual game</h2><a id="afterLink"><img id="after" alt="Actual game after peat and moss"></a></section></div><p>Unretouched standalone captures, identical cameras and saved v6 settings, 1600 × 900. Click for full resolution. Visual acceptance remains with the owner.</p>
<h2>References that govern the result</h2><div class="pair"><section><h3>Your site photo — ground identity</h3><a href="site-forest.jpg"><img class="ref" src="site-forest.jpg" alt="Owner site photograph showing peat, roots and fern floor"></a></section><section><h3>Your original — style and colour</h3><a href="original-style.jpg"><img class="ref" src="original-style.jpg" alt="Owner original colourful stylized woodland reference"></a></section></div>
<h2>Generated direction — not game captures</h2><div class="pair"><img src="material-concept.png" alt="Generated ground material reference"><img src="implementation-concept.png" alt="Generated implementation diagram"></div>
<h2>Checks and cost</h2><p>229 local and 207,399 outside plant transforms retained. Existing terrain/collision and other material packages verified unchanged. The replacement decorative floor has TRIANGLES source triangles, two reduced distance meshes, and no collision. One matched warmed pair below; this is not full-route or repeated performance certification.</p><table><tr><th>View</th><th>Before GPU ms</th><th>After GPU ms</th><th>Delta ms</th></tr>ROWS</table><p><a href="evidence.json">Full evidence</a> · <a href="../../PeatMoss/recipe.json">Rebuild recipe</a></p>MOTION</main>
<script>function view(v){for(const side of ['before','after']){let p=side+'-'+v+'.png';document.getElementById(side).src=p;document.getElementById(side+'Link').href=p}}view('G01')</script></html>'''
motion='<h2>Moving game view</h2><video controls loop muted src="bank-motion.mp4"></video><p>12 fps viewport samples for visual inspection; playback is not a frame-rate benchmark.</p>' if (OUT/'bank-motion.mp4').exists() else ''
(OUT/'index.html').write_text(page.replace('ROWS',rows).replace('MOTION',motion).replace('TRIANGLES',format(installed['bake']['triangles'],',')),encoding='utf-8')
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',26)
board=Image.new('RGB',(1600,1000),'#19221b');draw=ImageDraw.Draw(board)
for row,v in enumerate(['G01','D01']):
    for col,side in enumerate(['before','after']):
        x=col*800;y=row*500
        draw.text((x+14,y+8),('Ground close-up' if v=='G01' else 'Low view')+' — '+side+' (game)',font=font,fill='white')
        board.paste(Image.open(OUT/(side+'-'+v+'.png')).resize((800,450),Image.Resampling.LANCZOS),(x,y+45))
board.save(OUT/'comparison.jpg',quality=95)
board=Image.new('RGB',(1600,1060),'#19221b');draw=ImageDraw.Draw(board)
for x,title,file in [(0,'Actual game — new ground','after-G01.png'),(800,'Generated target — not game','material-concept.png')]:
    draw.text((x+14,10),title,font=font,fill='white');im=Image.open(OUT/file);im.thumbnail((800,450));board.paste(im,(x,50))
draw.text((14,530),'Site photo — peat, roots, patchy moss',font=font,fill='white');im=Image.open(OUT/'site-forest.jpg');im.thumbnail((800,490));board.paste(im,(0,570))
draw.text((814,530),'Original style — landscape crop',font=font,fill='white');im=Image.open(OUT/'original-style.jpg').crop((0,75,591,666));im.thumbnail((800,490));board.paste(im,(800,570))
board.save(OUT/'references-alongside.jpg',quality=95)
print(json.dumps(metrics,indent=2));print(OUT/'index.html')
