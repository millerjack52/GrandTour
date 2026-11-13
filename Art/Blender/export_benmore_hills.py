"""Export the regular-grid geographic backdrop without height exaggeration."""
from pathlib import Path
import bpy, json, array
OUT=Path('C:/GrandTour/Art/Export/BenmoreHills')
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for part in json.loads((OUT/'hills.json').read_text())['parts']:
    a=array.array('f');a.frombytes((OUT/(part['name']+'.f32')).read_bytes())
    verts=[(a[i],-a[i+1],a[i+2]) for i in range(0,len(a),3)];cols=part['columns'];faces=[]
    for j in range(part['rows']-1):
        for i in range(cols-1):
            k=j*cols+i;faces.extend([(k,k+cols,k+cols+1),(k,k+cols+1,k+1)])
    mesh=bpy.data.meshes.new(part['name']);mesh.from_pydata(verts,[],faces);mesh.update()
    ob=bpy.data.objects.new(part['name'],mesh);bpy.context.collection.objects.link(ob);bpy.context.view_layer.objects.active=ob;ob.select_set(True)
    for p in mesh.polygons:p.use_smooth=True
    assert sum(p.normal.z for p in mesh.polygons)>0
    bpy.ops.export_scene.fbx(filepath=str(OUT/(part['name']+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,bake_anim=False)
    ob.select_set(False)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Benmore_Hills.blend'))
