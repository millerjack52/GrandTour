"""Check a saved wood study against the preceding canopy mesh without saving it."""
import bpy
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

root=Path(__file__).resolve().parents[2]/'Art/Export/RoadFordStyle/Iterations'
label=sys.argv[sys.argv.index('--')+1]

def load(folder):
    with bpy.data.libraries.load(str(root/folder/'TreeReview.blend'),link=False) as (src,dst):
        dst.objects=[n for n in src.objects if n=='SM_RF_Willow_Mature' or n.startswith('UCX_SM_RF_Willow_Mature_')]
    tree=next(o for o in dst.objects if not o.name.startswith('UCX'))
    hulls=[o for o in dst.objects if o.name.startswith('UCX')]
    return tree,hulls

def digest(mesh,foliage=False):
    h=hashlib.sha256()
    for p in mesh.polygons:
        if foliage and p.material_index==0: continue
        h.update(struct.pack('<II',p.material_index,len(p.vertices)))
        for i in p.vertices: h.update(struct.pack('<fff',*mesh.vertices[i].co))
    return h.hexdigest()

old,old_hulls=load('canopy-v3-02')
new,new_hulls=load(label)
def material_values(m):
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    return (tuple(p.inputs['Base Color'].default_value),p.inputs['Roughness'].default_value,
            p.inputs['Specular IOR Level'].default_value)
result={
    'foliage_geometry_unchanged':digest(old.data,True)==digest(new.data,True),
    'collision_geometry_unchanged':sorted(digest(o.data) for o in old_hulls)==sorted(digest(o.data) for o in new_hulls),
    'collision_hulls':len(new_hulls),
    'finite_vertices':all(math.isfinite(x) for v in new.data.vertices for x in v.co),
    'zero_area_faces':sum(p.area<1e-10 for p in new.data.polygons),
    'triangles':sum(len(p.vertices)-2 for p in new.data.polygons),
    'bark_material':new.data.materials[0].name,
    'has_bark_flow_uv':new.data.uv_layers.get('BarkFlow') is not None,
    'foliage_materials_unchanged':len(old.data.materials)==len(new.data.materials) and all(material_values(a)==material_values(b) for a,b in zip(old.data.materials[1:],new.data.materials[1:])),
}
(root/label/'wood_validation.json').write_text(json.dumps(result,indent=2))
assert result['foliage_geometry_unchanged'] and result['collision_geometry_unchanged']
assert result['foliage_materials_unchanged']
assert result['finite_vertices'] and result['zero_area_faces']==0 and result['has_bark_flow_uv']
print('WOOD_VALIDATION_OK '+json.dumps(result),flush=True)
