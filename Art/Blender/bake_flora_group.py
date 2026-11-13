"""Extend the isolated source-matching sample with pine and two grass shapes."""
import bpy,json,sys,traceback,hashlib
from pathlib import Path
R=Path('C:/GrandTour');P=R/'Art/Export/LidarStudy/FloraPath';O=R/'Art/Export/LidarStudy/FloraGroup'
S=Path('D:/GrandTourAssets/FlippedNormals/Flora_Paint_Bonus_Project_Files/Bonus_Project_Files/001/001.blend')
O.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(R/'Art/Blender'))
from bake_flora_exact import bake_assets
report={'ok':False};before=hashlib.sha256(S.read_bytes()).hexdigest()
try:
 bpy.ops.wm.open_mainfile(filepath=str(S),load_ui=False,use_scripts=False);s=bpy.context.scene
 mats={m.name:m for m in bpy.data.materials}
 for m in mats.values():m.use_fake_user=True
 for image in bpy.data.images:
  if image.source=='FILE':
   path=S.parent/'textures'/Path(image.filepath.replace('\\','/')).name
   if path.is_file():image.filepath=str(path);image.reload()
 for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
 data=json.loads((P/'scene-manifest.json').read_text());recipe={'assets':[]};objects=[]
 for key,name in [('pine','SM_Path_FP_Tree_D_001'),('grass','SM_Path_FP_Grass_001'),('drygrass','SM_Path_FP_Dry_Grass_001')]:
  row=next(x for x in data['meshes'] if x['name']==name)
  bpy.ops.object.select_all(action='DESELECT');bpy.ops.import_scene.fbx(filepath=str(P/(name+'.fbx')),use_anim=False)
  ob=next(o for o in bpy.context.selected_objects if o.type=='MESH');ob.name=key
  indices=[p.material_index for p in ob.data.polygons];names=[]
  for material in ob.data.materials:
   match=row['materials'][0] if len(row['materials'])==1 else next((n for n in sorted(row['materials'],key=len,reverse=True) if material.name==n or material.name.startswith(n+'.')),None)
   assert match,(name,material.name);names.append(match)
  ob.data.materials.clear()
  for n in names:ob.data.materials.append(mats[n])
  for polygon,index in zip(ob.data.polygons,indices):polygon.material_index=index
  for m in ob.data.materials:
   for n in m.node_tree.nodes:
    if n.type=='UVMAP':n.uv_map=ob.data.uv_layers[0].name
  bpy.context.view_layer.objects.active=ob;bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
  ob.location=(0,0,0);ob.hide_render=True;objects.append(ob)
  recipe['assets'].append({'key':key,'mesh':name,'materials':row['materials']})
 bake_assets(s,objects,recipe,O)
 (O/'extra-assets.json').write_text(json.dumps(recipe,indent=2))
 report.update(ok=True,assets=[x['key'] for x in recipe['assets']],source_unchanged=hashlib.sha256(S.read_bytes()).hexdigest()==before)
except Exception:report['error']=traceback.format_exc();raise
finally:(O/'bake-report.json').write_text(json.dumps(report,indent=2))
