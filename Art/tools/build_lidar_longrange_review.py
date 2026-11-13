"""Present the unmodified, current Unreal long-range captures."""
import json,html
from pathlib import Path
O=Path('C:/GrandTour/Art/Export/LidarStudy/FloraIntegration')
r=json.loads((O/'longrange-report.json').read_text());assert r['ok']
page='''<!doctype html><meta charset="utf-8"><title>LiDARStudy — long-range views</title><style>body{margin:30px auto;max-width:1920px;background:#101b1b;color:#e5ede7;font:18px system-ui}p,figcaption,h1{padding:0 20px}figure{margin:35px 0}img{width:100%;height:auto}a{color:#a6dac9}</style><h1>LiDARStudy — current long-range views</h1><p>Actual Unreal captures at 1920 × 1080. Current lighting, exposure and fog. The Flora Paint / Rock Master integration remains confined to the logging-road section; the surrounding map retains its existing forest.</p>'''
for v in r['views']:
 name='longrange_'+v['name']+'.png';assert (O/name).exists()
 page+='<figure><figcaption>'+html.escape(v['description'])+'</figcaption><a href="'+name+'"><img src="'+name+'"></a></figure>'
page+='<p><a href="longrange-report.json">Capture details</a> · <a href="review.html">Ground-level comparisons</a></p>'
(O/'longrange.html').write_text(page,encoding='utf-8')
print(O/'longrange.html')
