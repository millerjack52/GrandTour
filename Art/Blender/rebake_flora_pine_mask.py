"""Preserve the original 4K foliage coverage before considering any opacity fit."""
import bpy,sys,json,hashlib,traceback
from pathlib import Path
R=Path('C:/GrandTour');O=R/'Art/Export/FloraTrail/PineMatch';(O/'textures').mkdir(exist_ok=True)
sys.path.insert(0,str(R/'Art/Blender'))
from bake_flora_exact import bake_shared_masks
source=Path(json.loads((R/'Art/Export/FloraTrail/PineTrial/export-report.json').read_text())['source'])
report={'ok':False,'source_hash':hashlib.sha256(source.read_bytes()).hexdigest()}
try:
 bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False);s=bpy.context.scene
 mat=bpy.data.materials['Leaf_0.002'];mat.use_fake_user=True
 for im in bpy.data.images:
  if im.source=='FILE':
   p=source.parent/'textures'/Path(im.filepath.replace('\\','/')).name
   if p.is_file():im.filepath=str(p);im.reload()
 for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
 mesh=bpy.data.meshes.new('MaskRecipe');mesh.materials.append(mat);ob=bpy.data.objects.new('MaskRecipe',mesh);s.collection.objects.link(ob)
 s.render.engine='CYCLES';s.cycles.device='CPU';s.render.bake.target='IMAGE_TEXTURES';s.render.bake.use_clear=True
 s.view_settings.view_transform='Standard';s.view_settings.look='None';s.view_settings.exposure=0;s.view_settings.gamma=1
 masks=bake_shared_masks(s,[ob],O,resolution=4096)
 report.update(ok=True,masks=masks,size=[4096,4096],source_unchanged=hashlib.sha256(source.read_bytes()).hexdigest()==report['source_hash'])
except Exception:report['error']=traceback.format_exc();raise
finally:(O/'mask-report.json').write_text(json.dumps(report,indent=2))
