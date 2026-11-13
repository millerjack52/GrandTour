"""Check mesh stability and the terrain's packed material coordinates."""
import bpy, json
from pathlib import Path
root=Path('C:/GrandTour/Art/Export/RoadFordStyle')
now=json.loads((root/'manifest.json').read_text())
old=json.loads((root/'GroundIterations/baseline/manifest.json').read_text())
non_grass=lambda data:[p for p in data['placements'] if 'GrassCarpet' not in p['mesh']]
assert non_grass(now)==non_grass(old), 'Non-grass dressing placement changed'
counts=lambda data:[(a['name'],a['triangles']) for a in data['assets'] if 'GrassCarpet' not in a['name']]
assert counts(now)==counts(old)
rows=[]
shared_normals={}
ridge=bpy.data.objects['SM_RF_BackdropRidge']
assert all(p.use_smooth for p in ridge.data.polygons),'Faceted backdrop'
for obj in bpy.data.objects:
    if obj.type!='MESH' or not any(m and m.name=='M_RF_TerrainBlend' for m in obj.data.materials): continue
    assert [uv.name for uv in obj.data.uv_layers][:2]==['UVMap','SurfaceMasks'],obj.name
    masks=[tuple(d.uv) for d in obj.data.uv_layers[1].data]
    assert all(-.001<=v<=1.001 for uv in masks for v in uv),obj.name
    assert all(p.use_smooth for p in obj.data.polygons),obj.name
    assert obj.data.has_custom_normals,obj.name
    corners={}
    for loop in obj.data.loops:
        vi=loop.vertex_index
        color=tuple(obj.data.color_attributes['Color'].data[loop.index].color)
        if vi in corners: assert color==corners[vi],(obj.name,'face colour discontinuity')
        corners[vi]=color
        key=tuple(round(v,4) for v in obj.data.vertices[vi].co)
        normal=obj.data.corner_normals[loop.index].vector.copy()
        if key in shared_normals: assert (normal-shared_normals[key]).length<.001,(obj.name,'normal seam',key)
        shared_normals[key]=normal
    rows.append(dict(mesh=obj.name,uv_channels=len(obj.data.uv_layers),meadow_range=[min(v[0] for v in masks),max(v[0] for v in masks)],wet_range=[min(v[1] for v in masks),max(v[1] for v in masks)]))
assert len(rows)>=4
report=dict(revision=now['revision'],non_grass_placements_unchanged=True,non_grass_geometry_counts_unchanged=True,continuous_corner_colors=True,continuous_shared_normals=True,terrain=rows)
(root/'ground-validation.json').write_text(json.dumps(report,indent=2))
print('GROUND_VALIDATION_OK '+json.dumps(report))
