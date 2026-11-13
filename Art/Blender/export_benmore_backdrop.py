import bpy,json,array
from pathlib import Path
ROOT=Path('C:/GrandTour');OUT=ROOT/'Art/Export/BenmoreEnvironment';data=json.loads((OUT/'backdrop.json').read_text())
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for part in data['parts']:
    raw=array.array('f');raw.frombytes((OUT/(part['name']+'.f32')).read_bytes());verts=[(raw[i],-raw[i+1],raw[i+2]) for i in range(0,len(raw),3)];faces=[];cols=part['columns']
    for j in range(part['rows']-1):
        for i in range(cols-1):
            k=j*cols+i;faces.extend([(k,k+cols,k+cols+1),(k,k+cols+1,k+1)])
    mesh=bpy.data.meshes.new(part['name']);mesh.from_pydata(verts,[],faces);mesh.update();ob=bpy.data.objects.new(part['name'],mesh);bpy.context.collection.objects.link(ob)
    # Ensure upward normals after changing handedness.
    bpy.context.view_layer.objects.active=ob;ob.select_set(True);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
    if sum(p.normal.z for p in mesh.polygons)<0:
        bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.flip_normals();bpy.ops.object.mode_set(mode='OBJECT')
    for p in mesh.polygons:p.use_smooth=True
    bpy.ops.export_scene.fbx(filepath=str(OUT/(part['name']+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,bake_anim=False)
    ob.select_set(False)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Benmore_Backdrop.blend'))
