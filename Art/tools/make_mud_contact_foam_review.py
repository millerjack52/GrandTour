"""Package native captures without retouching them."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
out=root/'Art/Export/MudContactFoam'
r=json.loads((out/'review-report.json').read_text())
status=json.loads((out/'review-run-status.json').read_text(encoding='utf-8-sig'))
assert r['ok'] and status['exit_code']==0 and status['fresh'] and status['report_ok']
for stem in ['clods','tyres','stone']:
    for suffix in ['on','off']:assert (out/f'{stem}_{suffix}.png').stat().st_size>40000
ms=r['after']['water']['foam_mean_ms']
html='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mud water · contact foam</title><style>
*{box-sizing:border-box}body{margin:0;background:#151914;color:#e9e6dc;font:16px/1.55 system-ui}main{max-width:1200px;margin:auto;padding:35px 24px}h1{font-size:34px;margin:8px 0}p{max-width:860px;color:#c1c8b9}nav{display:flex;gap:10px;margin:24px 0}button{border:1px solid #6b7664;background:#262e24;color:inherit;border-radius:5px;padding:10px 18px;cursor:pointer}button.active{background:#cbd6b7;color:#172015}.frame{position:relative;aspect-ratio:8/5;background:#090c09;overflow:hidden;border-radius:8px}.frame img{position:absolute;width:100%;height:100%;object-fit:contain}.frame .on{clip-path:inset(0 0 0 50%)}.line{position:absolute;top:0;bottom:0;left:50%;width:2px;background:#e1e6ce}.label{position:absolute;bottom:16px;padding:5px 12px;background:#182116d9;border-radius:5px}.before{left:16px}.after{right:16px}input{width:100%;margin:20px 0}small{color:#a7b39d}a{color:#d5e4be}
</style><main><small>SHARED MUD WATER / CONTACT FOAM</small><h1>Foam where the water meets the ground.</h1>
<p>Broken cream-coloured patches collect around mud clumps and immersed meshes. Tyre and hull movement generate a drifting, fading trail in the existing water simulation.</p>
<nav><button class="active" data-view="clods">Mud clumps</button><button data-view="tyres">Tyres</button><button data-view="stone">Immersed stone</button></nav>
<div class="frame"><img id="off" src="clods_off.png" alt="Contact foam disabled"><img id="on" class="on" src="clods_on.png" alt="Contact foam enabled"><div class="line"></div><span class="label before">Foam off</span><span class="label after">Foam on</span></div>
<label for="compare">Drag to compare</label><input id="compare" type="range" min="0" max="100" value="50">
<p>Drive <strong>L_RutInteraction</strong>, including Firm and Deep, or <strong>L_MudWater</strong>. These maps share the updated water material. The stone above is a temporary review prop; no level geometry was changed.</p>
<p>Native and live checks passed. Cosmetic foam simulation: MEASURE ms mean per update in this pond, capped at 30 updates/second. This measures simulation cost, not total GPU cost. Water and soil response are unchanged.</p>
<small><a href="review-report.json">Live review data</a> · <a href="tests-run-status.json">Native test status</a></small>
</main><script>
const slider=document.getElementById('compare');slider.oninput=()=>{document.getElementById('on').style.clipPath=`inset(0 0 0 ${slider.value}%)`;document.querySelector('.line').style.left=slider.value+'%'};
document.querySelectorAll('button').forEach(b=>b.onclick=()=>{document.querySelectorAll('button').forEach(x=>x.classList.toggle('active',x===b));for(const s of ['on','off'])document.getElementById(s).src=b.dataset.view+'_'+s+'.png'});
</script></html>'''.replace('MEASURE',f'{ms:.3f}')
(out/'contact-foam.html').write_text(html,encoding='utf-8')
print(out/'contact-foam.html')
