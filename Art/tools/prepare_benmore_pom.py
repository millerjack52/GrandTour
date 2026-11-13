"""Fetch matching, unmodified Poly Haven height maps with API hash verification."""
from pathlib import Path
import urllib.request,json,hashlib
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Art/Textures/RoadBenchmark'
rows=[]
def fetch(url):
    return urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=90)
for asset in ['gravel_floor_02','gravel_floor_04']:
    url='https://api.polyhaven.com/files/'+asset
    data=json.load(fetch(url))['Displacement']['2k']['png']
    raw=fetch(data['url']).read()
    assert hashlib.md5(raw).hexdigest()==data['md5']
    path=OUT/(asset+'_disp_2k.png');path.write_bytes(raw)
    rows.append(dict(asset=asset,channel='Displacement',file=path.name,api=url,**data))
(OUT/'pom-download-manifest.json').write_text(json.dumps(rows,indent=2))
print(json.dumps(rows,indent=2))
