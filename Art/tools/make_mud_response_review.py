"""Build the local review from actual drive/capture reports; no generated imagery."""
import argparse,json
from pathlib import Path

OUT=Path(__file__).resolve().parents[1]/'Export/MudResponse'

def build(headless=False):
    contact_file='contact-report.json' if headless else 'review-report.json'
    review=json.loads((OUT/contact_file).read_text())
    dynamics=json.loads((OUT/'dynamics-after.json').read_text())
    before=json.loads((OUT/'dynamics-before.json').read_text())
    old={r['name']:r for r in before['runs']}
    names={'bog_start':'Full throttle, settled bog','bog_crawl':'45% throttle, settled bog',
           'bog_coast40':'40 km/h coast-down, settled bog','bog_fresh40':'40 km/h on uncompressed bog',
           'bog_reverse':'Reverse from settled bog'}
    rows=[]
    for r in dynamics['runs']:
        if r['name'] not in names:continue
        baseline=f"{old[r['name']]['end_kmh']:.1f}" if r['name'] in old and r['name']!='bog_reverse' else '—'
        rows.append(f"<tr><td>{names[r['name']]}</td><td>{baseline}</td><td>{r['end_kmh']:.1f}</td></tr>")
    captions={'01_vehicle_mud_spray':'Loaded tyres and displaced ground after a real driving pass.',
              '02_coated_tyres':'Tyre burial and coating after the repeated pass.',
              '03_driven_ruts':'Broader rounded tracks, remaining clumps and pooled water.',
              '07_crossing_existing_ruts':'Driving across existing tracks.',
              '04_firm_turf_2cm':'Prescribed 2 cm firm turf study.',
              '05_damp_grass_5cm':'Prescribed 5 cm damp grass study.',
              '06_wet_grass_8cm':'Prescribed 8 cm wet grass study.'}
    cards=[]
    for p in ([] if headless else review['images']):
        path=Path(p);stamp=int(path.stat().st_mtime)
        cards.append(f'<figure><a href="{path.name}"><img src="{path.name}?v={stamp}"></a><figcaption>{captions.get(path.stem,path.stem)}</figcaption></figure>')
    settlement=review.get('loaded_settlement_cm',[])
    depth=f'{min(settlement):.1f}–{max(settlement):.1f} cm' if settlement else 'Not measured'
    perf=''
    profile=OUT/'scalability-driving-report.json'
    if not headless and profile.exists() and profile.stat().st_mtime>(OUT/contact_file).stat().st_mtime:
        p=json.loads(profile.read_text(encoding='utf-8-sig'))
        if p.get('ok'):
            items=[]
            for r in p['runs']:
                m=r['metrics']['FrameTime'];items.append(f"{['Low','Balanced','High'][r['quality']]}: {m['mean_ms']:.1f} ms mean / {m['p99_ms']:.1f} ms p99")
            perf='<p>1440 × 900 short driving profile: '+ '; '.join(items)+'. This is one vehicle in the test scene, not a full Benmore traffic/streaming benchmark.</p>'
    html='''<!doctype html><meta charset="utf-8"><title>Mud contact and driving review</title>
<style>body{background:#20241f;color:#eee8dc;font:17px/1.6 system-ui;margin:36px auto;max-width:1280px;padding:0 24px}h1{font-size:34px}p{max-width:1000px}a{color:#dccea7}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:24px}figure{margin:0}img{width:100%;display:block}figcaption{color:#c4c7ba}table{border-collapse:collapse;margin:24px 0}td,th{text-align:left;padding:8px 22px 8px 0;border-bottom:1px solid #4a5044}</style>
<h1>L_MudResponse: soil contact and driving</h1>
<p>Tyres keep their physical radius. Suspension contacts follow the deformed ground and sink under load; soil grip weakens with wheelspin and local resistance increases with speed and immersion. Automatic shifts now distinguish wheelspin from forward progress. All driving here uses pedal input without a speed cap or automatic speed braking.</p>
<p>Player tracks may reach the depth of existing grooves. The new pressure footprint crushes crowns into a continuous rounded bed and redistributes removed soil into low pockets and shoulders. Subtle directional tread shading reduces the original clump relief in the compressed bed. The system uses bounded local wheel snapshots and the existing tiled surface field. Chassis collision still uses the original landscape; this is a tuned soil approximation.</p>'''
    html+=f'<p>Measured loaded settlement: <strong>{depth}</strong>. Contact and deformation checks: {sum(bool(v) for v in review["checks"].values())}/{len(review["checks"])}. Unrestricted driving checks: {sum(bool(v) for v in dynamics["checks"].values())}/{len(dynamics["checks"])}.</p>'
    if headless:
        html+='<p><strong>Latest visual review and GPU profiling deferred at the owner’s request.</strong> These results are headless physics checks. Existing screenshots predate the latest track shape and material, so they are omitted here. Rendered appearance, subjective driving feel and current frame times remain unverified.</p>'
    else:
        html+='<p>Fresh Unreal captures below use raster shadows/software Lumen for the capture process; saved scene lighting is unchanged.</p>'
    html+='<table><tr><th>Test</th><th>Before: end km/h</th><th>Now: end km/h</th></tr>'+''.join(rows)+'</table><p>Starts run for four seconds; coast-downs for two. The old reverse trial used the wrong pedal and is excluded from comparison. Full throttle and wheelspin can make less progress than a controlled crawl.</p>'
    html+=perf+f'<p><a href="dynamics-after.json">Driving telemetry</a> · <a href="{contact_file}">Contact and deformation checks</a></p><main>'+''.join(cards)+'</main>'
    (OUT/'mud-response.html').write_text(html,encoding='utf-8')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--headless',action='store_true')
    build(parser.parse_args().headless)
