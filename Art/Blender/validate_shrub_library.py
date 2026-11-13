"""Round-trip every FBX, then make the saved source scene easy to browse."""
import bpy,json,math
from pathlib import Path
OUT=Path(__file__).resolve().parents[2]/'Art/Export/ShrubLibrary/v01'
data=json.loads((OUT/'manifest.json').read_text()); checks=[]
for row in data['models']:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(OUT/(row['name']+'.fbx')),use_custom_normals=True)
    obs=[o for o in bpy.context.scene.objects if o.type=='MESH']; assert len(obs)==1
    ob=obs[0]; mesh=ob.data; mesh.calc_loop_triangles()
    actual=list(ob.dimensions); expected=row['size_m']
    assert all(abs(a-b)<.001 for a,b in zip(sorted(actual),sorted(expected))), (row['name'],actual,expected)
    assert len(mesh.loop_triangles)==row['triangles']
    assert len(mesh.color_attributes)>0 and len(mesh.uv_layers)>0
    assert len(mesh.materials)==1 and ob.location.length<.0001
    assert all(math.isfinite(x) for v in mesh.vertices for x in v.co)
    checks.append(dict(name=row['name'],triangles=len(mesh.loop_triangles),dimensions_m=actual,vertex_colors=True,uv=True,ground_origin=True))
for asset in {r['asset'] for r in data['models']}:
    rows=sorted([r for r in data['models'] if r['asset']==asset],key=lambda r:r['lod'])
    assert rows[0]['triangles']>rows[1]['triangles']>rows[2]['triangles']
    assert all((OUT/(r['name']+'.glb')).stat().st_size>1000 for r in rows)
bpy.ops.wm.open_mainfile(filepath=str(OUT/'GrandTour_ShrubLibrary.blend'))
scene=bpy.data.scenes['Shrub Assets - metres']; bpy.context.window.scene=scene
for i,row in enumerate([r for r in data['models'] if r['lod']==0]):
    ob=bpy.data.objects[row['name']]; ob.hide_render=False; ob.hide_set(False); ob.location=(i%4*3.05,i//4*3.6,0)
bpy.context.window.scene=bpy.data.scenes['Shrub Library Review']
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'GrandTour_ShrubLibrary.blend'))
(OUT/'validation-report.json').write_text(json.dumps(dict(ok=True,fbx_roundtrips=checks,lod_counts_descend=True,glb_files_present=36),indent=2))
print('SHRUB_VALIDATION_OK',len(checks))
