import bpy,json,random,math
from pathlib import Path
OUT=Path('C:/GrandTour/Art/Export/LidarStudy/CanopyInterior');OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
random.seed(731)
lobes=[(-1.4,.2,1.3,1.4,1.1,1.6),(.7,-.5,2.1,1.6,1.3,2.2),(1.5,1.1,1.1,1.3,1.1,1.5),(-.3,1.4,1.8,1.2,1.1,1.9),(-1.6,-1.2,.8,.9,1.,1.1),(.5,.2,3.1,1.1,1.,1.4)]
rows=[]
for lod,ids in enumerate([range(6),[0,1,2,3],[0,1,2]]):
 parts=[]
 for i in ids:
  x,y,z,sx,sy,sz=lobes[i]
  bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=1,location=(x,y,z))
  ob=bpy.context.object;ob.scale=(sx,sy,sz)
  for p in ob.data.polygons:p.use_smooth=True
  parts.append(ob)
 bpy.ops.object.select_all(action='DESELECT')
 for ob in parts:ob.select_set(True)
 bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();ob=bpy.context.object
 ob.name=f'SM_ForestInterior_LOD{lod}';bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 bpy.ops.export_scene.fbx(filepath=str(OUT/(ob.name+'.fbx')),use_selection=True,apply_unit_scale=True,axis_forward='-Y',axis_up='Z',bake_anim=False,add_leaf_bones=False)
 rows.append(dict(lod=lod,triangles=len(ob.data.polygons)))
 bpy.data.objects.remove(ob,do_unlink=True)
(OUT/'mesh.json').write_text(json.dumps(rows,indent=2))
