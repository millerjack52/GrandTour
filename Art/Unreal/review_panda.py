"""Capture the saved Panda import using Unreal's renderer, including glass visibility."""
import unreal as u,json,time,traceback
from pathlib import Path
OUT=Path('C:/GrandTour/Art/Export/VehicleTools/panda-unreal-v01')
MAP='/Game/GrandTour/ArtTests/Panda/L_PandaReview'
u.EditorPythonScripting.set_keep_python_script_alive(True)
phase='load';index=0;last=time.monotonic();started=last
report={'ok':False,'map':MAP,'images':[],'scope':'Static imported assembly and translucent glazing. No Panda driving rig.'}
def finish(error=None):
 if error:report['error']=error
 (OUT/'render-check.json').write_text(json.dumps(report,indent=2))
 u.unregister_slate_post_tick_callback(handle);u.EditorLevelLibrary.editor_end_play();u.SystemLibrary.quit_editor()
def tick(dt):
 global phase,last,index,shot,shot_started,world,pc
 now=time.monotonic()
 try:
  if now-started>360:finish('Capture timed out');return
  if phase=='load':
   phase='loading'
   assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(MAP)
   actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
   car=next(a for a in actors if a.get_actor_label()=='NC_Panda1990')
   components=car.get_components_by_class(u.StaticMeshComponent);assert len(components)==14
   report['components']=len(components)
   glass=next(c for c in components if c.static_mesh.get_name()=='SM_Panda1990_Glass');m=glass.get_material(0)
   assert m.get_editor_property('blend_mode')==u.BlendMode.BLEND_TRANSLUCENT
   assert not glass.get_editor_property('cast_shadow')
   report['glass_material']=m.get_path_name();report['material_blend']=str(m.get_editor_property('blend_mode'))
   report['glass_lighting']=str(m.get_editor_property('translucency_lighting_mode'))
   phase='loaded';last=now
  elif phase=='loaded' and now-last>8:
   phase='playing';last=now;u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play()
  elif phase=='playing' and now-last>18:
   world=u.EditorLevelLibrary.get_game_world()
   if not world:return
   phase='camera_setup'
   pc=u.GameplayStatics.get_player_controller(world,0);assert pc
   cameras=u.GameplayStatics.get_all_actors_of_class(world,u.CameraActor)
   label=['NC_Camera_Panda1990_Front','NC_Camera_Panda1990_Cockpit'][index]
   cam=next(a for a in cameras if a.get_actor_label()==label)
   pc.set_view_target_with_blend(cam,0)
   phase='camera_ready';last=time.monotonic()
  elif phase=='camera_ready' and now-last>4:
   phase='capturing'
   filename=OUT/(['UE_Panda_Exterior.png','UE_Panda_Cockpit.png'][index])
   report['images'].append(str(filename));shot_started=time.time()
   u.SystemLibrary.execute_console_command(world,'HighResShot 1440x900 filename="'+filename.as_posix()+'"',pc)
   phase='shot';last=now
  elif phase=='shot' and now-last>8:
   output=Path(report['images'][-1])
   if not output.exists() or output.stat().st_mtime<shot_started:return
   index+=1
   if index==2:report['ok']=True;finish();return
   phase='playing';last=now-12
 except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
