"""Prepare an isolated Gaea export graph; never rewrite the artist's source."""
import copy, json, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Art/Export/BigMountain'
source=OUT/'Source/bigmountain.terrain'
j=json.loads(source.read_text()); nodes=j['Assets']['$values'][0]['Terrain']['Nodes']
template=json.loads((ROOT/'Art/Export/BenmoreGaea/review/native-inspection/Inspect.terrain').read_text())['Assets']['$values'][0]['Terrain']['Nodes']['101']
for i,(name,src,port) in enumerate([('HeightRaw',636,'Out'),('LakeWater',636,'Water'),('LakeSurface',636,'Surface'),('LakeDepth',636,'Depth'),('LakeShore',636,'Shore'),('Flow',613,'Flow'),('Deposits',613,'Deposits')],1000):
    n=copy.deepcopy(template);n.update({'$id':str(i),'Id':i,'Name':name,'OutputPath':str(OUT/'Masks'/name)})
    n['SaveDefinition'].update(Node=i,Filename=name)
    for p in n['Ports']['$values']:
        p['Parent']={'$ref':str(i)}
        if 'Record' in p:p['Record'].update(From=src,To=i,FromPort=port)
    nodes[str(i)]=n
(OUT/'Masks').mkdir(exist_ok=True)
(OUT/'Source/bigmountain_exports.terrain').write_text(json.dumps(j,indent=2))
(OUT/'source-manifest.json').write_text(json.dumps({'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'graph_changes':'Added export nodes only; original river wiring preserved.'},indent=2))
