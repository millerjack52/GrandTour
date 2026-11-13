"""Final review of the finished isolated driving demo, using actual Unreal captures."""
from pathlib import Path
import json,hashlib,html
from PIL import Image,ImageDraw,ImageFont,ImageOps
O=Path('C:/GrandTour/Art/Export/FloraDrive');ROOT=Path('C:/GrandTour')
b=json.loads((O/'build-report.json').read_text());c=json.loads((O/'capture-report.json').read_text());f=json.loads((O/'functional-report.json').read_text())
assert b['ok'] and c['ok'] and f['ok']
protected=json.loads((O/'protected-before.json').read_text());assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in protected.items())
assert b['pond']['road_cells_changed']==0 and c['pond_bed_cm']<-20
assert b['foliage_materials'] and len(c['render_spot_checks'])==2
font=lambda n:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',n)
canvas=Image.new('RGB',(1800,1220),'#152322');d=ImageDraw.Draw(canvas)
d.text((26,19),'FLORA DRIVE / finished playable forest study',font=font(34),fill='#eee9d6')
d.text((26,68),'Purchased Flora Paint vegetation + Cloud Paint sky / native deformable mud and interactive water',font=font(20),fill='#b6c7b8')
for x,y,label,file in [(26,115,'YOUR REFERENCE / Flora Paint by Casey Sheep','reference-forest.png'),(915,115,'ACTUAL UNREAL / forest route','06_forest_path.png'),(26,620,'ACTUAL UNREAL / shallow woodland pond','15_pond.png'),(915,620,'ACTUAL UNREAL / drivable mud trail','02_broken_puddles.png')]:
    d.text((x,y),label,font=font(23),fill='#e0d3a1')
    im=ImageOps.contain(Image.open(O/file).convert('RGB'),(855,455),method=Image.Resampling.LANCZOS)
    canvas.paste(im,(x,y+38+(455-im.height)//2))
d.text((26,1152),'Different layout from the reference. All game images are direct Unreal captures; no generated replacement imagery.',font=font(19),fill='#b6c7b8')
canvas.save(O/'scene-complete.jpg',quality=95)
beforeafter=Image.new('RGB',(1680,550),'#152322');d=ImageDraw.Draw(beforeafter)
for x,label,p in [(24,'BEFORE / open test plot',O/'BeforeCompletion/06_forest_path.png'),(852,'AFTER / finished forest route',O/'06_forest_path.png')]:
    d.text((x,20),label,font=font(25),fill='#eee9d6');im=ImageOps.contain(Image.open(p).convert('RGB'),(804,450));beforeafter.paste(im,(x,65))
beforeafter.save(O/'scene-before-after.jpg',quality=95)
checks=[]
for run in c['render_spot_checks']:
    metrics=run['metrics'];gpu=metrics['GPUTime'];frame=metrics['FrameTime']
    checks.append({'view':run['view'],'resolution':run['resolution'],'gpu_median_ms':gpu['median'],'gpu_p95_ms':gpu['p95'],'frame_median_ms':frame['median'],'frame_p95_ms':frame['p95'],'samples':frame['samples'],'scope':run['scope']})
report={'ok':True,'level':b['level'],'source_maps_unchanged':True,'tree_instances':b['tree_instances'],'plant_instances':b['plant_instances'],'lowest_lod_background_trees':b['dressing']['distant_trees_lowest_lod'],'pond_area_m2':b['pond']['wet_area_m2'],'pond_bed_cm':c['pond_bed_cm'],'road_authored_cells_changed':b.get('road_relief',{}).get('changed_road_cells',0),'route_travel_m':f['route']['travel_cm']/100,'max_water_cm':f['route']['max_water_cm'],'max_compression_cm':f['route']['max_compression_cm'],'reset_height_error_cm':f['max_reset_height_error_cm'],'foliage_parent_materials_repaired':len(b['foliage_materials']),'wind_enabled':True,'breeze_max_cm':b['settings']['breeze_cm'],'cloud_representation':'eight distant cards rendered from creator assets; fixed daylight','packaged_performance_verified':False,'render_spot_checks':checks,'reference_exact_match':False}
(O/'completion-report.json').write_text(json.dumps(report,indent=2))
rows=''.join('<tr><td>'+html.escape(x['view'])+'</td><td>'+str(x['resolution'][0])+' × '+str(x['resolution'][1])+'</td><td>%.2f / %.2f ms</td><td>%.2f / %.2f ms</td></tr>'%(x['gpu_median_ms'],x['gpu_p95_ms'],x['frame_median_ms'],x['frame_p95_ms']) for x in checks)
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Flora Drive / finished demo</title><style>*{box-sizing:border-box}body{max-width:1700px;margin:auto;padding:26px;background:#152322;color:#eee9d6;font:17px/1.65 system-ui}h1,h2{font-weight:500}p{max-width:1150px;color:#becbc0}a{color:#e4cf9c}img{display:block;width:100%}.pair{display:grid;grid-template-columns:1fr 1fr;gap:20px}figure{margin:0}figcaption{padding:8px 0}table{border-collapse:collapse}td,th{padding:10px 22px;border-bottom:1px solid #4b6156;text-align:left}.note{border-left:3px solid #d3bc79;padding-left:18px}code{overflow-wrap:anywhere}@media(max-width:850px){.pair{grid-template-columns:1fr}}</style>
<h1>Flora Drive / finished playable study</h1><p>A winding forest route with the purchased Flora Paint assets, native tyre deformation and water, a shallow woodland pond, and Cloud Paint sky elements. The approved POM ground and reduced sunlight remain in place.</p>
<img src="scene-complete.jpg" alt="Actual Unreal forest, pond and drive alongside the supplied Flora Paint reference">
<h2>Drive it</h2><p>Launch <code>C:/GrandTour/Play-FloraDrive.bat</code>. WASD drive · Space brake · C camera · 1 / 2 / 3 recovery points · Backspace fresh scene · V low range · X differential lock · F leave vehicle · F1 driving information.</p>
<h2>From test plot to forest</h2><img src="scene-before-after.jpg" alt="The same forest camera before and after completion"><p>Uneven wooded banks close the visible boundary. Young trees and shrubs connect the tall canopy to the forest floor. Roadside plants grow in groups with open wheel tracks; the wet clearing has a native simulated pond, reed clusters and an open near shore. A few larger rocks mark the bends, with small stones, twigs and fallen leaves nearby.</p>
<div class="pair"><figure><img src="16_woodland_edge.png"><figcaption>Woodland edge and understory</figcaption></figure><figure><img src="17_exit.png"><figcaption>View back from the route exit</figcaption></figure></div>
<h2>Road relief update</h2><p><a href="road-relief-review.html">Latest ground before/after, validation and transfer lessons</a></p><h2>Ground and foliage</h2><div class="pair"><figure><img src="12_parallax.png"><figcaption>Close POM ground</figcaption></figure><figure><img src="08_clouds_canopy.png"><figcaption>Purchased cloud source renders in the Unreal sky</figcaption></figure></div>
<p>Ground POM uses 10–24 steps nearby and fades out over 7–18 m. Approximate height maps are reconstructed from the pack's matching normals. The foliage transparency repair now reaches the actual material-instance parents. A restrained 1.25 cm breeze moves standing foliage, fading with distance; fallen leaves and twigs stay still.</p>
<h2>Checks</h2><p>CHECK_RESULTS</p><p>The new pond changes no authored road cells. The original MudRoad, MudLab, LiDAR and FloraPath maps are unchanged. The final driving check covers the completed scene; review images are separate stationary captures.</p>
<h2>Performance spot checks</h2><table><thead><tr><th>View</th><th>Resolution</th><th>GPU median / p95</th><th>Frame median / p95</th></tr></thead><tbody>PERFORMANCE_ROWS</tbody></table><p class="note">Uncapped stationary PIE samples, with no screenshots or pauses inside the measurement windows. These are editor spot checks, not packaged-game frame-rate guarantees. Background trees use their lowest existing LOD, smaller plants cull with distance, and the distant ground uses a simple material.</p>
<h2>Controls and limits</h2><p><a href="look-settings.json">Map lighting, fog and breeze settings</a> · <a href="completion-report.json">Final validation and counts</a> · <a href="functional-report.json">Driving check</a> · <a href="capture-report.json">Captures and raw timing summaries</a> · <a href="05_overview.png">Full scene overview</a></p>
<p><code>MPC_ForestGround</code> exposes POM enable, normal enable, depth and distance fade. Cloud Paint is represented by eight distant cards with a baked daylight appearance, not traversable volumes. This is a finished small test scene; it is not an exact reconstruction of the reference or a woodland-wide integration.</p>
<p>Original Flora Paint assets: Casey Sheep. Cloud Paint: Casey Sheep / MeiU. <a href="sources-and-transfer.txt">Source documentation and transfer notes</a>. Existing documentation includes <a href="https://superhivemarket.com/products/cloud-paint/docs">the Cloud Paint creator manual</a> and <a href="https://superhivemarket.com/products/flora-paint-stylized-tree-and-plants-library/docs">Flora Paint compatibility notes</a>.</p></html>'''
page=page.replace('PERFORMANCE_ROWS',rows).replace('CHECK_RESULTS','The vehicle completed %.1f m of continuous driving, with %.1f cm maximum soil compression and %.1f cm maximum wheel water depth. Reload restored the checked road heights with %.4f cm error. The pond bed measures %.1f cm below the original ground.'%(report['route_travel_m'],report['max_compression_cm'],report['max_water_cm'],report['reset_height_error_cm'],report['pond_bed_cm']))
(O/'index.html').write_text(page,encoding='utf-8')
print(json.dumps(report,indent=2))
