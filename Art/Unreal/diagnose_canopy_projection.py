import unreal as u,sys,time,json,math,struct,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import canopy_depth as C
from benmore_river_life_materials import props
actors=C.actors;world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();temps=[];N=256;report=[]
def run():
 for instanced in [False,True]:
  for elevated in [False,True]:
   mesh=u.load_asset(C.DEST+'/SM_CD_Canopy_0');base=u.Vector(50000,-70000,-10000)
   if instanced:
    a=actors.spawn_actor_from_class(u.Actor,u.Vector());a.root_component.set_mobility(u.ComponentMobility.STATIC)
    c=u.GTVegetationSubsystem.add_tagged_instances(a,mesh,[u.Transform(location=base,rotation=u.Rotator(yaw=45))],'Probe','NoCollision',False)
   else:
    a=actors.spawn_actor_from_class(u.StaticMeshActor,base);a.set_actor_rotation(u.Rotator(yaw=45),False);c=a.static_mesh_component;c.set_static_mesh(mesh)
   temps.append(a);c.set_forced_lod_model(4);c.set_editor_property('world_position_offset_disable_distance',0)
   centre=base+u.Vector(0,0,1100);d=u.Vector(1,0,.7 if elevated else 0);d=d.normal();pos=centre+d*6000
   cap=actors.spawn_actor_from_class(u.SceneCapture2D,pos);temps.append(cap);cap.set_actor_rotation(u.MathLibrary.find_look_at_rotation(pos,centre),False)
   rt=u.RenderingLibrary.create_render_target2d(world,N,N,u.TextureRenderTargetFormat.RTF_RGBA32F);cc=cap.capture_component2d
   props(cc,texture_target=rt,capture_every_frame=False,capture_on_movement=False,projection_type=u.CameraProjectionMode.ORTHOGRAPHIC,ortho_width=3300,primitive_render_mode=u.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST)
   cc.show_only_component(c);yield 2
   pixels={}
   for key,mode in [('c',u.SceneCaptureSource.SCS_BASE_COLOR),('a',u.SceneCaptureSource.SCS_SCENE_COLOR_HDR)]:
    cc.set_editor_property('capture_source',mode);cc.capture_scene();yield .5
    pixels[key]=u.RenderingLibrary.read_render_target_raw_pixel_area(world,rt,0,0,N,N,False)
   data=bytearray()
   for col,alpha in zip(pixels['c'],pixels['a']):
    a=max(0,min(1,1-alpha.a));rgb=[max(0,min(1,v))**(1/2.2) for v in [col.b,col.g,col.r]]
    data.extend(bytes([round((v*a+.5*(1-a))*255) for v in rgb]+[255]))
   name='projection-%s-%s'%('ism' if instanced else 'static','high' if elevated else 'side')
   (C.QA/(name+'.tga')).write_bytes(struct.pack('<BBBHHBHHHHBB',0,0,2,0,0,0,0,0,N,N,32,40)+data)
   report.append(dict(name=name,wpo=str(c.get_editor_property('evaluate_world_position_offset'))))
   for obj in temps:actors.destroy_actor(obj)
   temps.clear();u.RenderingLibrary.release_render_target2d(rt);yield .1
 (C.QA/'projection.json').write_text(json.dumps(report,indent=2))
busy=False;deadline=0;steps=run()
def tick(dt):
 global busy,deadline
 if busy or time.monotonic()<deadline:return
 busy=True
 try:deadline=time.monotonic()+float(next(steps))
 except StopIteration:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 except Exception:
  (C.QA/'projection-error.txt').write_text(traceback.format_exc());u.log_error(traceback.format_exc());u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
