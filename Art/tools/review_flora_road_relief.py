"""Review actual game captures of road relief, not generated replacement images."""
from pathlib import Path
import json,hashlib
from PIL import Image,ImageDraw,ImageFont,ImageOps
O=Path('C:/GrandTour/Art/Export/FloraDrive');ROOT=Path('C:/GrandTour')
b=json.loads((O/'build-report.json').read_text());c=json.loads((O/'capture-report.json').read_text());f=json.loads((O/'functional-report.json').read_text())
assert b['ok'] and c['ok'] and f['ok']
protected=json.loads((O/'protected-before.json').read_text())
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in protected.items())
assert b['settings']==json.loads((O/'BeforeRoadRelief/look-settings.json').read_text())
font=lambda n:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',n)
board=Image.new('RGB',(1800,1140),'#152322');d=ImageDraw.Draw(board)
d.text((24,18),'ROAD RELIEF / actual Unreal before and after',font=font(32),fill='#eee9d6')
d.text((24,65),'Same lighting, exposure and POM depth. Upper row: same chase checkpoint; suspension pose can differ.',font=font(20),fill='#becbc0')
for x,y,label,p in [(24,110,'BEFORE / chase camera',O/'BeforeRoadRelief/02_broken_puddles.png'),(912,110,'AFTER / chase camera',O/'02_broken_puddles.png'),(24,610,'BEFORE / fixed ground camera',O/'BeforeRoadRelief/09_ground_detail.png'),(912,610,'AFTER / fixed ground camera',O/'09_ground_detail.png')]:
    d.text((x,y),label,font=font(24),fill='#e0d3a1');im=ImageOps.contain(Image.open(p).convert('RGB'),(864,462));board.paste(im,(x,y+36))
board.save(O/'road-relief-before-after.jpg',quality=95)
metrics=[]
for row in c['render_spot_checks']:
    metrics.append({'view':row['view'],'resolution':row['resolution'],'gpu_median_ms':row['metrics']['GPUTime']['median'],'gpu_p95_ms':row['metrics']['GPUTime']['p95'],'frame_median_ms':row['metrics']['FrameTime']['median'],'scope':row['scope']})
report={'ok':True,'source_maps_unchanged':True,'lighting_unchanged':True,'road_authoring':b['road_relief'],'runtime_cross_sections':c['road_cross_sections'],'drive_metres':f['route']['travel_cm']/100,'max_compression_cm':f['route']['max_compression_cm'],'max_water_cm':f['route']['max_water_cm'],'reset_height_error_cm':f['max_reset_height_error_cm'],'render_spot_checks':metrics,'packaged_performance_verified':False,'chase_pom_disabled_capture':'18_chase_without_parallax.png','initial_failed_check_archived':'road-relief-first-check-failed.json'}
(O/'road-relief-review.json').write_text(json.dumps(report,indent=2))
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Flora Drive / road relief</title><style>body{max-width:1800px;margin:auto;padding:24px;background:#152322;color:#eee9d6;font:18px/1.6 system-ui}img{width:100%;display:block}p{max-width:1150px}a{color:#e0d3a1}.pair{display:grid;grid-template-columns:1fr 1fr;gap:20px}@media(max-width:800px){.pair{grid-template-columns:1fr}}</style><h1>Road relief / actual Unreal</h1><p>Wandering wheel troughs, a broken centre and shoulders now use the same rest-height field as the tyres and water. Grouped embedded stones replace the old rows. Ground colour and roughness follow the authored shapes; lighting and POM depth are unchanged.</p><img src="road-relief-before-after.jpg" alt="Before and after from the chase checkpoint and identical fixed ground camera"><p>The chase camera settles with the car, so its exact pose can differ. The lower row uses identical world coordinates and lens.</p><h2>Geometry with parallax disabled</h2><img src="18_chase_without_parallax.png" alt="Actual chase view with POM disabled"><p>This isolates the broad terrain relief from the close texture-depth effect. Normals and lighting remain enabled.</p><h2>Validation</h2><p>RESULTS</p><p>Performance: METRICS. These are warmed, uncapped stationary editor samples, not packaged-game frame-rate guarantees. The existing terrain grid is reused, physical clods are reduced from 275 to 64, and decorative stones are instanced without collision.</p><h2>Transfer record</h2><p><a href="../../../..//docs/FOREST_ROAD_RELIEF_LESSONS.txt">Lessons and production-map integration rules</a> · <a href="road-relief-review.json">Measured checks</a> · <a href="functional-report.json">Full driving report</a> · <a href="index.html">Forest scene review</a></p><p>Launch C:/GrandTour/Play-FloraDrive.bat to drive the isolated demo. Actual game maps remain unchanged. Map-wide integration still needs road-spline coordinates, per-map dimensions and moving-view performance/LOD checks.</p></html>'''
page=page.replace('../../../..//docs/','../../../docs/').replace('RESULTS','Continuous drive: %.1f m; maximum compression %.1f cm; maximum water depth %.1f cm; reset height error %.4f cm. Native shader-oracle checks passed. Source maps and approved lighting are unchanged.'%(report['drive_metres'],report['max_compression_cm'],report['max_water_cm'],report['reset_height_error_cm']))
page=page.replace('METRICS','; '.join('%s GPU median %.2f ms / p95 %.2f ms at %s × %s'%(x['view'],x['gpu_median_ms'],x['gpu_p95_ms'],*x['resolution']) for x in metrics))
(O/'road-relief-review.html').write_text(page,encoding='utf-8')
from html.parser import HTMLParser
class Links(HTMLParser):
    def handle_starttag(self,tag,attrs):
        for key,value in attrs:
            if key in ('src','href'):
                assert (O/value).exists(),value
Links().feed(page)
print(json.dumps({k:v for k,v in report.items() if k not in ['road_authoring','runtime_cross_sections']},indent=2))
