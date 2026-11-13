"""Publish the measured route comparison without presenting old renders as current."""
import json
from pathlib import Path
OUT=Path(__file__).resolve().parents[1]/'Export/MudVariants'
setup=json.loads((OUT/'response-setup-report.json').read_text())
check=json.loads((OUT/'response-check-report.json').read_text())
runs={r['key']:r for r in check['runs']}
rows=[]
for p in setup['profiles']:
    r=runs[p['key']];sink=sum(r['settled']['settlement'])/4
    rows.append(f"<tr><td>{p['title'][4:]}</td><td>{p['start']/100:g}–{p['end']/100:g} m</td><td>{sink:.1f} cm</td><td>{r['end_kmh']:.1f} km/h</td></tr>")
html='''<!doctype html><meta charset="utf-8"><title>Mud variants driving route</title>
<style>body{max-width:1060px;margin:48px auto;padding:0 24px;background:#20241f;color:#eee8dc;font:18px/1.6 system-ui}h1{font-size:38px}td,th{text-align:left;padding:12px 24px 12px 0;border-bottom:1px solid #626652}table{border-collapse:collapse;width:100%;margin:30px 0}a{color:#dbcb9a}.note{padding:20px;background:#30392c;border-left:4px solid #a1ab75}code{font-size:15px}</style>
<h1>L_MudVariants · driving route</h1>
<p>Four 25 m surfaces, separated by gravel. Start at the original 5 m position and drive forward through the signs. Existing winch posts remain beyond each section.</p>
<table><tr><th>Surface</th><th>Route position</th><th>Loaded settlement</th><th>Speed after 4 s</th></tr>'''+''.join(rows)+'''</table>
<p>Measurements use the same car, low range and differential lock, at 65% throttle. These are short trials, not top-speed limits. Clay gives shallow compression and dry plates; wet mud uses the approved response; the deeper bogs yield more and strongly resist progress.</p>
<p>The last section has three broad puddles, approximately 6–8 m long. Shallow elliptical bowls and level underlying terrain let the water connect across the hollows. Rut water now fills deeper depressions, has wet edges, a smoother reflective surface, sediment colour and disturbance-driven ripples.</p>
<p>Spray launches above the actual mud or water surface. The old code applied the rut depression twice and could bury the emitters. Saturated pools favour finer muddy spray over large clods.</p>'''
html+=f'<p>Headless checks: {sum(check["checks"].values())}/{len(check["checks"])}. First pool probe: {check["puddle_probe"]["wet_area_m2"]:.1f} m² covered by more than 1 cm of water.</p>'
html+='''<p class="note">Fresh rendered review and GPU profiling remain deferred. These results verify the saved scene, vehicle response and effect triggering; they do not establish final visual quality or frame rate.</p>
<p><code>/Game/GrandTour/ArtTests/MudVariants/L_MudVariants</code></p>
<p><a href="response-check-report.json">Vehicle and puddle checks</a> · <a href="response-setup-report.json">Setup and backup details</a></p>'''
(OUT/'mud-variants-response.html').write_text(html,encoding='utf-8')
