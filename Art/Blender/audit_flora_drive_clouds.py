import bpy,json
from pathlib import Path
base=Path('D:/GrandTourAssets/FlippedNormals/stylized_cloud_paint/Assets/Library_assets');r={}
for p in base.glob('*.blend'):
 with bpy.data.libraries.load(str(p),link=False) as (a,b):r[p.name]={'objects':list(a.objects),'collections':list(a.collections),'materials':list(a.materials),'scenes':list(a.scenes)}
out=Path('C:/GrandTour/Art/Export/FloraDrive');out.mkdir(parents=True,exist_ok=True);(out/'cloud-library-audit.json').write_text(json.dumps(r,indent=2))
