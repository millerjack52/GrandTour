"""Package fresh owned-process evidence, without inferring handling approval from tests."""
import html,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/RutInteraction'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
r=read(OUT/'review-report.json');setup=read(OUT/'setup-report.json');tests=read(ROOT/'Saved/Automation/RutInteraction/index.json');benchmark=read(OUT/'benchmark-report.json')
assert r['ok'] and setup['ok'] and benchmark['ok'] and tests['failed']==0 and tests['succeeded']==11
for mode in ['setup','tests','review','benchmark']:
    s=read(OUT/(mode+'-run-status.json'));assert s['fresh'] and s['report_ok'] and s['exit_code']==0
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest for p,digest in setup['baseline_hashes'].items())
for item in r['images']:assert (OUT/item['file']).stat().st_size>40000
e=html.escape;worked=next(c for c in r['cases'] if c['name']=='worked')
rows=''.join(f"<tr><th>{e(c['name'].title())}</th><td>{r['settlement_cm'][c['name']]:.1f} cm</td><td>{c['travel_cm']/100:.2f} m</td><td>{c['bank_work_j']:.0f} J<br><small>{c['after']['bank']['lateral_j']-c['before']['bank']['lateral_j']:.0f} J lateral</small></td><td>{c['after']['soil']['observe_mean_ms']:.2f} / {c['after']['soil']['observe_peak_ms']:.2f} ms</td></tr>" for c in r['cases'])
checks=''.join(f'<li>{e(k.replace("_"," "))}: <b>{"PASS" if v else "FAIL"}</b></li>' for k,v in r['checks'].items())
profile=worked.get('frame_profile',{})
frames=''.join(f'<tr><th>{e(k)}</th><td>{v["mean_ms"]:.2f} ms</td><td>{v["p99_ms"]:.2f} ms</td></tr>' for k,v in profile.items())
matched=''.join(f'<tr><th>{e(c["name"].title())} · {e(k)}</th><td>{v["mean_ms"]:.2f} ms</td><td>{v["p99_ms"]:.2f} ms</td></tr>' for c in benchmark['cases'] for k,v in c['frames'].items())
bank=worked['after']['bank']
doc=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Mud • tyre work and rut handling</title>
<style>body{{margin:0;background:#161b19;color:#e6e7dd;font:17px/1.55 system-ui}}main{{max-width:1200px;margin:auto;padding:40px 24px}}h1{{font-size:42px;line-height:1.15}}h2{{margin-top:48px}}p{{max-width:850px;color:#c1c9c0}}small,figcaption{{color:#b8c1b8}}.pair{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}figure{{margin:0}}img{{width:100%;border-radius:8px}}table{{border-collapse:collapse;width:100%;font-size:15px}}td,th{{text-align:left;padding:12px;border-bottom:1px solid #39463d}}code{{color:#d7dfa6}}.tag{{color:#b5d79a}}a{{color:#badba5}}li{{margin:6px 0}}@media(max-width:760px){{.pair{{grid-template-columns:1fr}}h1{{font-size:32px}}table{{font-size:12px}}td,th{{padding:6px}}}}</style>
<main><span class="tag">PRIVATE DRIVING COMPARISON · 11 NATIVE TESTS PASSED</span><h1>Tyres working the mud</h1>
<p>Rolling now pushes a low bow ahead of the tyre. Driven wheelspin moves soil toward the heel. Irregular shoulders yield locally, while the vehicle does extra work to push into the actual rut walls. The approved sinking and traction settings remain the starting point.</p>
<p>Open <code>/Game/GrandTour/ArtTests/RutInteraction/L_RutInteraction</code>. Also try <code>L_RutInteraction_Firm</code> and <code>L_RutInteraction_Deep</code> in the same folder. These are comparable copies of the same crossing, each with the shared water simulation.</p>
<figure><img src="worked_tracks.png" alt="Close view of the mud after the new tyre response"><figcaption>New response: actual driven track, with shared water in the depressions. Vehicle hidden for ground inspection.</figcaption></figure>
<h2>Matched driving input</h2><p>Both runs start in fresh terrain, use 60% throttle in low range with the differential locked, then apply the same steering input after five seconds. Their final positions can differ. The control disables the new response in the private scene.</p>
<div class="pair"><figure><img src="control_after.png" alt="Control pass"><figcaption>Accepted response · control</figcaption></figure><figure><img src="worked_after.png" alt="New response pass"><figcaption>Directional soil flow and rut resistance</figcaption></figure></div>
<h2>Track shape</h2><div class="pair"><figure><img src="control_tracks.png" alt="Control tyre tracks"><figcaption>Control · vehicle hidden for inspection</figcaption></figure><figure><img src="worked_tracks.png" alt="Worked tyre tracks"><figcaption>New flow · same inspection camera</figcaption></figure></div>
<h2>Firm and deep</h2><div class="pair"><figure><img src="firm_after.png" alt="Firm mud"><figcaption>Firm · layer 0.65, bearing 1.6</figcaption></figure><figure><img src="deep_after.png" alt="Deep soft mud"><figcaption>Deep · layer 1.28, bearing 0.6</figcaption></figure></div>
<h2>Measured response</h2><table><tr><th>Run</th><th>Standing settlement</th><th>9-second net progress</th><th>Bank work</th><th>Wheel observation mean / peak</th></tr>{rows}</table>
<p>Bank work is energy removed by the added bank resistance, recorded on the physics thread. It is zero in the control. Along a level rut adds no bank resistance; climbing its walls does. This pass does not add a speed cap or a steering spring.</p>
<p>The bank calculation cost averaged {bank['mean_ms']:.4f} ms per active wheel step, peaking at {bank['peak_ms']:.4f} ms. Wheel observation includes contact sampling and all terrain stamps for the vehicle, at up to 30 Hz. These CPU costs exclude water, texture upload and rendering.</p>
<h2>Rendered performance comparison</h2><table><tr><th>Matched driving sample</th><th>Mean</th><th>99th percentile</th></tr>{matched}</table><p>Fresh PIE worlds, old-world garbage collected before eight seconds of warmup, then eight seconds of unpaused offscreen driving at a 60 FPS cap. Both runs stay on the mud. These are short local editor samples, not whole-map or multi-vehicle scalability certification.</p>
<p>The original review run below included a garbage-collection event and larger frame spikes. It is preserved here; this pass does not claim to eliminate all rendering or collection hitches.</p><details><summary>Original review profile, including frame spikes</summary><table><tr><th>Metric</th><th>Mean</th><th>99th percentile</th></tr>{frames}</table></details>
<h2>Validation and scope</h2><ul>{checks}</ul><p>The native suite also checks actual soil volume, finite depth, reverse travel, wheelspin direction, diagonal rut crossings, and that bank forces cannot create kinetic energy. Accepted map hashes are unchanged.</p>
<p>Soil flow and bank yielding only run around loaded tyres. No new world-wide terrain scan, particles, mesh collision rebuild or separate water solver is introduced. Local bank relaxation happens while the tyre works the soil; lingering collapse after departure, erosion and transported sediment are later work.</p>
<p>Rendered images have a separate visual review; driving feel still needs your judgement. This is an approximation inspired by the references, not a reconstruction of MudRunner's proprietary solver.</p>
<p><a href="review-report.json">Full vehicle evidence</a> · <a href="benchmark-report.json">Matched performance evidence</a> · <a href="setup-report.json">Map settings and baseline hashes</a></p></main></html>'''
(OUT/'rut-interaction.html').write_text(doc,encoding='utf-8')
print(OUT/'rut-interaction.html')
