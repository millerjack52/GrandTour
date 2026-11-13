"""Matched Blender renders of saved old/new geometry; no image-generated previews."""
import bpy,sys,math,argparse
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
import car_tools as ct
p=argparse.ArgumentParser();p.add_argument('--old',required=True);p.add_argument('--new',required=True);p.add_argument('--output',required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=True)
if (out/'comparison-top.png').exists():raise RuntimeError('Use a new comparison directory')
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED';scene.render.threads=6;scene.view_settings.view_transform='AgX'
scene.world=bpy.data.worlds.new('World');scene.world.color=(.2,.2,.2)
def append_geometry(path,offset,label):
 c=bpy.data.collections.new(label);scene.collection.children.link(c)
 with bpy.data.libraries.load(str(Path(path).resolve()),link=False) as (src,dst):dst.objects=src.objects
 for ob in dst.objects:
  if ob is None:continue
  if ob.get('gt_owner')==ct.OWNER and ob.type=='MESH':
   c.objects.link(ob);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
   data=bpy.data.meshes.new_from_object(ob.evaluated_get(dg),depsgraph=dg)
   copy=bpy.data.objects.new(label+'_'+ob.get('gt_role',ob.name),data);c.objects.link(copy);copy.matrix_world=ob.matrix_world;copy.location.x+=offset
  bpy.data.objects.remove(ob,do_unlink=True)
append_geometry(a.old,-1.37,'BEFORE');append_geometry(a.new,1.37,'AFTER')
c=bpy.data.collections.new('Review');scene.collection.children.link(c)
ct.box('Floor',(0,0,-.05),(200,200,.1),c,ct.mat('ComparisonFloor',(.13,.17,.19)),'studio')
for name,loc,power,size in [('Key',(0,-4,7),1100,7),('Fill',(0,5,6),700,7)]:
 data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
 ob=bpy.data.objects.new(name,data);c.objects.link(ob);ob.location=loc;ob.rotation_euler=(Vector((0,0,.7))-ob.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('MatchedCamera');camera=bpy.data.objects.new('MatchedCamera',data);c.objects.link(camera);scene.camera=camera;data.type='ORTHO'
labels=[]
for name,x in [('BEFORE',-1.37),('AFTER',1.37)]:
 text=bpy.data.curves.new(name,'FONT');text.body=name;text.align_x='CENTER';text.size=.13
 ob=bpy.data.objects.new(name,text);c.objects.link(ob);text.materials.append(ct.mat('Label',(.7,.77,.8)));labels.append((ob,x))
for name,loc,target,scale,res in [('front',(0,-10,.87),(0,0,.87),5.7,(1800,850)),('top',(0,0,10),(0,0,0),6.2,(1800,1600))]:
 camera.location=loc;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();data.ortho_scale=scale
 for ob,x in labels:
  ob.location=(x,-2.5,.01) if name=='top' else (x,-2.4,1.91)
  ob.rotation_euler=(0,0,0) if name=='top' else (math.pi/2,0,0)
 scene.render.resolution_x,scene.render.resolution_y=res;scene.render.resolution_percentage=100
 scene.render.filepath=str(out/('comparison-'+name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Matched_Comparison.blend'))
