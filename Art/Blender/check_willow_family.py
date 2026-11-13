"""Verify saved standalone variants, portable textures and the reusable family library."""
import bpy
import json
import math
import sys
from pathlib import Path

folder=Path(__file__).resolve().parents[2]/'Art/Export/WillowFamily'/sys.argv[sys.argv.index('--')+1]
records=[]
for preset in ['young','broad','windswept','weathered']:
    bpy.ops.wm.open_mainfile(filepath=str(folder/(preset+'.blend')))
    trees=[o for o in bpy.data.objects if o.name.startswith('SM_Willow_')]
    assert len(trees)==1
    tree=trees[0]
    record=dict(preset=preset,scenes=len(bpy.data.scenes),triangles=sum(len(p.vertices)-2 for p in tree.data.polygons),
                finite=all(math.isfinite(x) for v in tree.data.vertices for x in v.co),
                zero_area_faces=sum(p.area<1e-10 for p in tree.data.polygons),
                collision_hulls=sum(o.name.startswith('UCX_'+tree.name) for o in bpy.data.objects),
                packed_textures=all(i.packed_file is not None for i in bpy.data.images if i.source=='FILE'),
                at_origin=tree.location.length<1e-6,
                has_review_camera=all(s.camera is not None for s in bpy.data.scenes))
    assert record['finite'] and record['zero_area_faces']==0 and record['packed_textures']
    assert record['at_origin'] and record['collision_hulls']==3 and record['has_review_camera']
    assert bpy.context.scene.camera is not None
    records.append(record)
bpy.ops.wm.open_mainfile(filepath=str(folder/'WillowFamily.blend'))
sources=[o for o in bpy.data.objects if o.name.startswith('SM_Willow_')]
assert len(sources)==4 and all(o.location.length<1e-6 for o in sources)
assert len({r['triangles'] for r in records})==4
(folder/'validation.json').write_text(json.dumps(dict(variants=records,library_sources=len(sources)),indent=2))
print('WILLOW_FAMILY_VALIDATION_OK '+json.dumps(records),flush=True)
