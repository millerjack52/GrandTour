"""Reopen a reference-willow study and verify its saved mesh and packed texture."""
import bpy
import json
import math
import sys
from pathlib import Path

label=sys.argv[sys.argv.index('--')+1]
folder=Path(__file__).resolve().parents[2]/'Art/Export/RoadFordStyle/Iterations'/label
bpy.ops.wm.open_mainfile(filepath=str(folder/'TreeReview.blend'))
ob=bpy.data.objects['SM_RF_Willow_Reference']
result=dict(
    triangles=sum(len(p.vertices)-2 for p in ob.data.polygons),
    leaf_count=ob['leaf_count'],pendant_shoot_count=ob['pendant_shoot_count'],
    finite_vertices=all(math.isfinite(x) for v in ob.data.vertices for x in v.co),
    zero_area_faces=sum(p.area<1e-10 for p in ob.data.polygons),
    collision_hulls=sum(o.name.startswith('UCX_SM_RF_Willow_Reference_') for o in bpy.data.objects),
    textures_packed=all(i.packed_file is not None for i in bpy.data.images if i.source=='FILE'),
    dimensions_m=list(ob.dimensions),
)
(folder/'validation.json').write_text(json.dumps(result,indent=2))
assert result['finite_vertices'] and result['zero_area_faces']==0
assert result['textures_packed'] and result['collision_hulls']==3
print('REFERENCE_WILLOW_OK '+json.dumps(result),flush=True)
