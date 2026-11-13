"""Presentation-only revision. Verify geometry unchanged from the checked source."""
import bpy,sys,shutil,json,hashlib
from pathlib import Path
source=Path(sys.argv[sys.argv.index('--')+1]);out=Path(sys.argv[sys.argv.index('--')+2])
if out.exists() and any(out.iterdir()):raise RuntimeError('Fresh output required')
out.mkdir(parents=True,exist_ok=True);bpy.ops.wm.open_mainfile(filepath=str(source/'Impreza_Orthographic_Rebuild.blend'))
def fingerprint():
 rows=[]
 for ob in sorted(bpy.data.objects,key=lambda o:o.name):
  if ob.type=='MESH':rows.append([ob.name,[list(v.co) for v in ob.data.vertices],[list(p.vertices) for p in ob.data.polygons],[list(row) for row in ob.matrix_world]])
 return hashlib.sha256(json.dumps(rows).encode()).hexdigest()
before=fingerprint();m=bpy.data.materials['Paint | reference blue'];m.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value=0;m.node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value=0
sc=bpy.context.scene;sc.view_settings.exposure=-.7
for f in source.iterdir():
 if f.suffix in ['.json','.py'] or f.name in ['01-four-view-sheet.png','02-side-profile.png']:shutil.copy2(f,out/f.name)
shutil.copy2(Path(__file__),out/Path(__file__).name);shutil.copy2(Path(__file__).with_name('rebuild_impreza_orthographic.py'),out/'rebuild_impreza_orthographic.py')
mapnames={'side':'side','quarter':'front quarter','rear-quarter':'rear quarter','front':'front','rear':'rear','top':'top','underside':'underside'}
for key,name in mapnames.items():
 sc.camera=bpy.data.objects['Review | '+name];sc.render.resolution_x,sc.render.resolution_y=sc.camera['resolution'];sc.render.filepath=str(out/(key+'.png'));bpy.data.objects['Studio ground'].hide_render=key=='underside';bpy.ops.render.render(write_still=True)
bpy.data.objects['Studio ground'].hide_render=False;sc.camera=bpy.data.objects['Review | front quarter'];sc.render.resolution_x,sc.render.resolution_y=sc.camera['resolution'];after=fingerprint();assert before==after
(out/'presentation-preservation.json').write_text(json.dumps({'source':str(source),'before_geometry_sha256':before,'after_geometry_sha256':after,'unchanged_geometry':before==after,'changes':['Paint specular and metal contribution set to zero to remove grazing white glare','Exposure -0.7'], 'assembly_report_source':str(source/'static-review-report.json')},indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Impreza_Orthographic_Rebuild.blend'));print('PRESENTATION_SAVED '+str(out))
