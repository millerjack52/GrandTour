"""Linear subdivision preserves the installed river silhouette and bed heights."""
import bpy,bmesh,json
from pathlib import Path
OUT=Path(__file__).resolve().parents[2]/'Art/Export/BenmoreGaea/WaterSurface_20261011'
report={'ok':False,'surfaces':[]}
for label in ['Benmore_RL_Stream','Benmore_RL_Outlet']:
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.fbx(filepath=str(OUT/(label+'.fbx')))
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
    assert len(objects)==1,(label,len(objects))
    obj=objects[0];bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    before=len(obj.data.polygons);bounds=[list(v) for v in obj.bound_box]
    # Split each source triangle into 16, without smoothing or remodelling.
    bm=bmesh.new();bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001)
    bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=3,use_grid_fill=True)
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    bm.to_mesh(obj.data);bm.free();obj.data.update()
    assert all(abs(a-b)<.001 for aa,bb in zip(bounds,obj.bound_box) for a,b in zip(aa,bb))
    for p in obj.data.polygons:p.use_smooth=True
    name='SM_SurfaceDetail_'+label.removeprefix('Benmore_RL_');obj.name=name;obj.data.name=name
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,apply_unit_scale=True,axis_forward='-Y',axis_up='Z',bake_anim=False,add_leaf_bones=False)
    report['surfaces'].append(dict(label=label,name=name,faces_before=before,faces_after=len(obj.data.polygons),vertices=len(obj.data.vertices),bounds_preserved=True))
report['ok']=True;(OUT/'mesh-report.json').write_text(json.dumps(report,indent=2));print(report)
