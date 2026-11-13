"""Package measured soil comparisons with their actual Unreal captures."""
import html,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/MudProvingGround'
r=json.loads((OUT/'propertiesreview-report.json').read_text())
status=json.loads((OUT/'propertiesreview-run-status.json').read_text(encoding='utf-8-sig'))
assert r['ok'] and status['fresh'] and status['exit_code']==0
log=(ROOT/'Saved/Logs/MudProvingGround-PropertiesReview.log').read_text(errors='replace')
warnings=log.count('Non-Nanite Marking Job Queue overflow')
render_note=(f'The rendered check logged {warnings} shadow-map marking overflow warnings. Scene performance remains an open check.' if warnings else 'This is a handling/render comparison; full scene performance and streaming remain separate checks.')
cards=[]
for p in r['profiles']:
    balance=re.search(r'balance_cm3=([-\d.]+)',p['surface_report'])
    assert balance and abs(float(balance.group(1)))<.01
    assert 'displacement_scale_valid=1' in p['surface_report']
    name=p['name'];images=[]
    for kind in ['loaded','tracks']:
        path=OUT/f'properties_{name}_{kind}.png';assert path.exists() and path.stat().st_size>40000
        images.append(f'<a href="{path.name}"><img src="{path.name}" alt="{name} {kind}"></a>')
    cards.append(f'''<article><h2>{html.escape(name.replace('_',' ').title())}</h2>
<p>Layer ×{p['depth_scale']:.2f} · bearing strength {p['bearing_strength']:.2f}</p>
<p><strong>{p['standing_mean_settlement_cm']:.1f} cm</strong> settlement under standing load</p>
{''.join(images)}<p>8-second crawl: {p['travel_cm']/100:.2f} m · wheel contact {p['contact_fraction']:.0%}</p>
<code>{html.escape(p['level'].split('/')[-1])}</code></article>''')
page='''<!doctype html><meta charset="utf-8"><title>Mud soil properties</title>
<style>body{margin:32px;background:#161c1d;color:#e8e4d9;font:17px/1.55 system-ui}h1{font-size:34px}p{max-width:1000px}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:22px}article{background:#252e2e;padding:18px;border-radius:12px}img{width:100%;margin:8px 0}code{font-size:12px;overflow-wrap:anywhere}a{color:#abc9c0}strong{color:#e8d599;font-size:24px}@media(max-width:1000px){.grid{grid-template-columns:1fr}}</style>
<h1>Same ground. Different support.</h1><p>Actual Unreal captures. The loaded views use the same world camera, car and starting position. Track views follow the same eight seconds of 60% throttle in low range with the differential locked. This compares soil properties, not different visual biomes.</p>
<div class="grid">'''+''.join(cards)+'''</div>
<p><b>Tuning:</b> select ProvingGround_Surface → Landscape Surface → Soil Properties before Play. Depth sets the firm base; bearing strength sets how far the car yields under load. Settlement Speed Scale controls the time taken by additional loaded sinking. Restart Play after edits.</p>
<p>The existing baseline is retained. The current layer limit is 50 cm below the reference plane; tyre size also bounds support. These captures demonstrate immersion and deformation, not acceptance of the final handling or frame rate.</p>
<p><b>Water is next:</b> feed the deformed bed into the existing water solver, then use its surface height/current for rendering, wheel drag, buoyancy and spray. These pools still use the prototype water material; fluid coupling is not completed by this pass.</p>
<p><a href="propertiesreview-report.json">Vehicle measurements</a> · <a href="mud-proving-ground.html">Original proving-ground review</a></p>'''
page+='<p>'+html.escape(render_note)+'</p>'
(OUT/'mud-soil-properties.html').write_text(page,encoding='utf-8')
print(OUT/'mud-soil-properties.html')
