import bpy,json
from pathlib import Path
O=Path('C:/GrandTour/Art/Export/FloraDrive/RockMaster');O.mkdir(parents=True,exist_ok=True)
S='D:/GrandTourAssets/FlippedNormals/Rock Master Tools/DATA.blend'
with bpy.data.libraries.load(S,link=False) as (src,dst):
    inventory={'objects':list(src.objects),'materials':list(src.materials),'node_groups':list(src.node_groups)}
(O/'library-names.json').write_text(json.dumps(inventory,indent=2))
print('ROCK_MASTER_INVENTORY',len(inventory['objects']),len(inventory['materials']))
