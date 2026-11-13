"""Run with Blender --background --python this_file -- --output NEW_DIRECTORY."""
import argparse,json,sys,math
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import car_tools as ct

def studio():
 scene=bpy.context.scene
 if bpy.data.collections.get('GT_ReviewStudio') and bpy.data.objects.get('ReviewCamera'):
  return bpy.data.objects['ReviewCamera']
 scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=24
 scene.cycles.use_denoising=True;scene.render.threads_mode='FIXED';scene.render.threads=6
 scene.render.resolution_x=1400;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
 if not scene.world:scene.world=bpy.data.worlds.new('ReviewWorld')
 scene.world.color=(.20,.20,.20)
 scene.view_settings.view_transform='AgX'
 scene.view_settings.exposure=0
 coll=bpy.data.collections.new('GT_ReviewStudio');scene.collection.children.link(coll)
 floor=ct.box('StudioFloor',(0,0,-.05),(200,200,.1),coll,ct.mat('Studio',(.13,.17,.19)),'studio')
 del floor['gt_owner']
 for name,loc,power,size in [('Key',(-3,-4,6),650,4),('Fill',(4,-1,4),230,5),('Rim',(0,4,5),500,3)]:
  data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
  ob=bpy.data.objects.new(name,data);coll.objects.link(ob);ob.location=loc
  ob.rotation_euler=(Vector((0,-.7,.7))-ob.location).to_track_quat('-Z','Y').to_euler()
 data=bpy.data.cameras.new('ReviewCamera');ob=bpy.data.objects.new('ReviewCamera',data);coll.objects.link(ob);scene.camera=ob
 return ob

def render_views(out):
 camera=studio();scene=bpy.context.scene
 views=[('three-quarter',(4,-5,3.0),(0,-.85,.75),3.7),('side',(6,-.90,.82),(0,-.90,.82),3.3),('front',(0,-7,.85),(0,-.8,.85),2.6),('top',(0,-.9,7),(0,-.9,0),4.2),('panel-closeup',(2.5,-3.1,1.9),(.52,-1.42,.69),1.8)]
 if json.loads(scene['gt_car_spec']).get('shape_study'):
  views=[('three-quarter',(5,-7,3.3),(0,0,.72),5.6),('side',(7,0,.78),(0,0,.78),5),('front',(0,-7,.78),(0,0,.78),2.65),('top',(0,0,7),(0,0,0),6.5),('rear-quarter',(5,7,3),(0,0,.75),5.6)]
  views.extend([('sill-arch-closeup',(3,1.7,1.0),(.91,.87,.44),.80),('indicator-closeup',(2.2,-4,1.6),(.70,-1.94,.70),.75)])
 for name,loc,target,scale in views:
  camera.location=loc;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=scale
  scene.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
 camera.location=views[0][1];camera.rotation_euler=(Vector(views[0][2])-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=views[0][3]

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--spec',default=str(Path(__file__).parent/'specs/estate_front_v1.json'));p.add_argument('--output',required=True);p.add_argument('--input');p.add_argument('--parts',nargs='*');p.add_argument('--no-render',action='store_true')
 args=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
 out=Path(args.output).resolve()
 if out.exists() and any(out.iterdir()):raise RuntimeError('Use a new output directory; existing review evidence is preserved')
 out.mkdir(parents=True,exist_ok=True)
 if args.input:bpy.ops.wm.open_mainfile(filepath=str(Path(args.input).resolve()))
 else:bpy.ops.wm.read_factory_settings(use_empty=True)
 s=json.loads(Path(args.spec).read_text());changed=ct.rebuild(s,args.parts)
 ct.setup_references(s,Path(__file__).resolve().parents[2]);ct.refresh_landmarks(s)
 report=ct.fit_report();report['rebuilt']=changed
 (out/'fit-report.json').write_text(json.dumps(report,indent=2));(out/'spec.json').write_text(json.dumps(s,indent=2))
 blend_name='Estate_Shape_Study.blend' if s.get('shape_study') else 'Estate_Front_Construction.blend'
 bpy.ops.wm.save_as_mainfile(filepath=str(out/blend_name))
 if not args.no_render:
  render_views(out);bpy.ops.wm.save_as_mainfile(filepath=str(out/blend_name))
 print('GTCT_RESULT '+json.dumps(report))
 if not report['ok']:raise RuntimeError('Fit checks failed: inspect fit-report.json')
