"""Actual Unreal comparisons, saved-map invariants and bounded performance results."""
from pathlib import Path
import json,hashlib
from PIL import Image,ImageOps,ImageDraw,ImageFont
from html.parser import HTMLParser
import sys
sys.path.insert(0,'C:/GrandTour/Art/Unreal')
from flora_trial_evidence import audited_fingerprint
O=Path('C:/GrandTour/Art/Export/FloraDrive');b=json.loads((O/'build-report.json').read_text());c=json.loads((O/'capture-report.json').read_text());f=json.loads((O/'functional-report.json').read_text())
assert b['ok'] and c['ok'] and f['ok'];assert f['lidar_settings']==b['lidar_mud']['settings']
assert c['trial_packages_sha256']==f['trial_packages_sha256']==audited_fingerprint(),'Rendered evidence does not match the audited assets'
if (O/'shadows-report.json').exists():
    shadow_review=O/'ground-shadows-review.json'
    if not shadow_review.exists() or json.loads(shadow_review.read_text())['trial_packages_sha256']!=c['trial_packages_sha256']:
        import runpy
        runpy.run_path('C:/GrandTour/Art/tools/review_flora_ground_shadows.py',run_name='__main__')
assert b['settings']==json.loads((O/'BeforeLidarMudRocks/look-settings.json').read_text())
assert hashlib.sha256((O/'world-rest.png').read_bytes()).digest()==hashlib.sha256((O/'BeforeLidarMudRocks/world-rest.png').read_bytes()).digest()
protected=json.loads((O/'protected-before.json').read_text());assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in protected.items())
assert all(a['lods']==3 and a['collision_hulls']>0 for a in b['rock_master']['assets'])
font=lambda n:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',n)
canvas=Image.new('RGB',(1800,1130),'#152322');d=ImageDraw.Draw(canvas)
d.text((24,18),'LIDAR MUD + ROCK MASTER / actual Unreal trial',font=font(32),fill='#eee9d6')
d.text((24,65),'Sun/exposure and authored relief retained. LiDAR mud, Rock Master shapes, and added ground-foliage shadows.',font=font(20),fill='#becbc0')
for x,y,label,file in [(24,110,'BEFORE / FloraDrive mud',O/'BeforeLidarMudRocks/02_broken_puddles.png'),(912,110,'AFTER / LiDAR mud character',O/'02_broken_puddles.png'),(24,610,'NEW / embedded Rock Master bank',O/'19_rock_bank.png'),(912,610,'NEW / layered outcrop',O/'20_rock_outcrop.png')]:
    d.text((x,y),label,font=font(23),fill='#e0d3a1');im=ImageOps.contain(Image.open(file).convert('RGB'),(864,462));canvas.paste(im,(x,y+35))
canvas.save(O/'lidar-mud-rocks-comparison.jpg',quality=95)
perf=[dict(view=r['view'],resolution=r['resolution'],gpu_median_ms=r['metrics']['GPUTime']['median'],gpu_p95_ms=r['metrics']['GPUTime']['p95'],frame_median_ms=r['metrics']['FrameTime']['median']) for r in c['render_spot_checks']]
report=dict(ok=True,source_maps_unchanged=True,rest_height_unchanged=True,sun_exposure_unchanged=True,ground_foliage_shadows_added=True,lidar_settings_match=True,road_relief_minimum_cm=c['minimum_runtime_crown_to_trough_cm'],mud_transfer=json.loads((O/'LidarMud/transfer.json').read_text()),rock_master=b['rock_master'],drive_metres=f['route']['travel_cm']/100,compression_cm=f['route']['max_compression_cm'],water_cm=f['route']['max_water_cm'],reset_error_cm=f['max_reset_height_error_cm'],performance=perf,packaged_performance_verified=False)
(O/'lidar-mud-rocks-review.json').write_text(json.dumps(report,indent=2))
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>LiDAR mud and Rock Master trial</title><style>body{max-width:1800px;margin:auto;padding:24px;background:#152322;color:#eee9d6;font:18px/1.6 system-ui}img{width:100%;display:block}p{max-width:1150px}a{color:#e0d3a1}.pair{display:grid;grid-template-columns:1fr 1fr;gap:22px}figure{margin:0}figcaption{padding:8px 0}@media(max-width:800px){.pair{grid-template-columns:1fr}}</style><h1>LiDAR mud + Rock Master / isolated trial</h1><p>The demo uses LiDAR's native mud response settings and local copies of its road pigment/tread shaders. The new physical troughs, raised ground, close POM and matching normals remain. The logging track's dry/wet character is transferred into this shorter route; its layout, pond and retained ground shapes are different.</p><img src="lidar-mud-rocks-comparison.jpg" alt="Actual before and after mud, and Rock Master bank/outcrop in Unreal"><p>The chase camera settles with the vehicle, so pose can differ. Lighting and exposure are unchanged. All game views are actual Unreal captures.</p><h2>Rock Master source selection</h2><p>Three large shapes and two medium rocks from MeiU's purchased library, baked to colour, normal and roughness maps, reduced to about 18k / 6.5k triangles at LOD0. Three LODs per mesh, collision, and twenty embedded placements across four groups. Existing plants are cleared from solid rock cores.</p><div class="pair"><figure><img src="RockMaster/source-contact-sheet.jpg"><figcaption>Purchased library previews used to choose the trial shapes</figcaption></figure><figure><img src="06_forest_path.png"><figcaption>Actual Unreal route with the new banks</figcaption><img src="15_pond.png"><figcaption>Retained native pond</figcaption></figure></div><h2>Checks</h2><p>CHECKS</p><p>PERF. These are stationary editor spot checks, not a packaged FPS guarantee.</p><p><a href="lidar-mud-rocks-review.json">Complete results</a> · <a href="LidarMud/reference.json">Saved LiDAR reference</a> · <a href="LidarMud/transfer.json">Transfer boundaries</a> · <a href="../../../docs/FLORA_LIDAR_MUD_ROCK_TRIAL.txt">Implementation and rollout notes</a></p><p>The existing ground shapes need extra layer thickness beneath some troughs; that adjustment is recorded rather than claiming identical terrain. The original LiDARStudy map remains unchanged. Whole-map integration should start with one actual road/bank section, preserving its soil profiles and water topology.</p><p>Drive: C:/GrandTour/Play-FloraDrive.bat. WASD · Space brake · C camera · 1/2/3 recovery · Backspace reset.</p><p>Rock Master Tools: MeiU. Flora Paint: Casey Sheep. <a href="https://superhivemarket.com/products/rock-master-tools/docs">Rock Master documentation</a>. Its linked Notion manual was unavailable; conversion is based on inspected source assets.</p></html>'''
page=page.replace('<h2>Rock Master source selection</h2>','<p>The archived mud baseline uses an earlier vehicle appearance. Sun intensity and exposure are unchanged; ground-foliage cast/contact shadows were added in the current pass.</p><h2>Ground foliage shadows</h2><img src="ground-shadows-comparison.jpg" alt="Fixed Unreal camera before and after ground foliage shadows"><p>Broadleaf plants now cast shadows. Fine foliage uses short screen-space contact shadows; these cannot account for off-screen blockers. <a href="ground-shadows-review.json">Shadow settings and paired GPU spot checks</a>.</p><h2>Rock Master source selection</h2>')
page=page.replace('CHECKS','Exact exported LiDAR response settings verified; %.1f m continuously driven, %.1f cm maximum compression, %.1f cm maximum water depth, %.4f cm reset-height error. Authored relief, sun/exposure and protected source-map hashes are unchanged.'%(report['drive_metres'],report['compression_cm'],report['water_cm'],report['reset_error_cm']))
page=page.replace('PERF','; '.join('%s GPU median %.2f ms / p95 %.2f ms at %s × %s'%(r['view'],r['gpu_median_ms'],r['gpu_p95_ms'],*r['resolution']) for r in perf))
(O/'lidar-mud-rocks-review.html').write_text(page,encoding='utf-8')
class Links(HTMLParser):
    def handle_starttag(self,tag,attrs):
        for k,v in attrs:
            if k in ['href','src'] and not v.startswith('https:'):assert (O/v).exists(),v
Links().feed(page)
print(json.dumps({k:v for k,v in report.items() if k not in ['mud_transfer','rock_master']},indent=2))
