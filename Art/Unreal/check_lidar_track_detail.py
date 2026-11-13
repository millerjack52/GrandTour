"""Inspect/capture the real saved logging route, never a separate study map."""
from pathlib import Path
import os
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve()
exec(compile((ROOT/'Art/Unreal/check_lidar_place.py').read_text().split('steps=run();')[0],'<lidar-check-helpers>','exec'))
import lidar_logging_trial as trial
PHASE=os.environ.get('GT_TRACK_DETAIL_PHASE','after')
report=dict(ok=False,phase=PHASE,images=[],timings={},materials={})

def save():
 (OUT/'trackdetailcheck.json').write_text(json.dumps(report,indent=2))
 (OUT/('trackdetail-'+PHASE+'.json')).write_text(json.dumps(report,indent=2))

def run():
 global world,pc,car,camera
 les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(BASE+'/L_LidarStudy')
 refs=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
 author=next(a for a in refs if isinstance(a,u.GTProceduralGround));tiles=list(author.relief_tiles.values())
 report['ground_digest']=str(author.output_digest);report['pool_cells']=author.road_pool_wet_samples
 def ground(x,y):
  for t in tiles:
   o=t.get_actor_location()
   if o.x<=x<o.x+t.span_cm and o.y<=y<o.y+t.span_cm:return t.height_at(u.Vector2D(x,y))
  return author.base_height_at(u.Vector2D(x,y))
 path=trial.route(json.loads((OUT/'roads.json').read_text()));assert path
 mel=u.MaterialEditingLibrary
 for name in ['Terrain','Detail']:
  m=u.load_asset(BASE+'/M_'+name);nodes=[]
  for n in mel.get_material_expressions(m):
   if isinstance(n,u.MaterialExpressionCustom):nodes.append(dict(name=n.get_name(),tag=str(n.get_editor_property('desc')),code=n.get_editor_property('code'),inputs=[str(i.get_editor_property('input_name')) for i in n.get_editor_property('inputs')]))
  props={}
  for prop in ['BASE_COLOR','EMISSIVE_COLOR','NORMAL','ROUGHNESS']:
   node=mel.get_material_property_input_node(m,getattr(u.MaterialProperty,'MP_'+prop))
   props[prop]=node.get_name() if node else None
  report['materials'][name]=dict(shading=str(m.get_editor_property('shading_model')),tangent=bool(m.get_editor_property('tangent_space_normal')),outputs=props,nodes=nodes)
 save()
 if PHASE!='before':
  import lidar_track_detail as detail
  report['validation']=detail.validate(refs)
  report['texture_bytes']={}
  for asset in u.EditorAssetLibrary.list_assets(BASE+'/TrackDetail',recursive=False,include_folder=False):
   t=u.load_asset(asset)
   if isinstance(t,u.Texture):
    size,fmt=u.GTMudArtLibrary.texture_all_mips_bytes(t)
    report['texture_bytes'][t.get_name()]=dict(bytes=size,format=fmt)
  prior=json.loads((OUT/'trackdetail-before.json').read_text())
  report['unchanged_surface_programs']={}
  for name in ['Terrain','Detail']:
   current={n['name']:n['code'] for n in report['materials'][name]['nodes']}
   changed=[n['name'] for n in prior['materials'][name]['nodes'] if current.get(n['name'])!=n['code']]
   assert changed==['MaterialExpressionCustom_1'],('Non-colour surface program changed',name,changed)
   report['unchanged_surface_programs'][name]=True
 les.editor_set_viewport_realtime(False);assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900)
 until=time.monotonic()+180
 while not world or not car:
  world=u.EditorLevelLibrary.get_game_world()
  if world:
   pc=u.GameplayStatics.get_player_controller(world,0)
   car=pc.get_car() if pc else None
  assert time.monotonic()<until;yield .5
 pc.possess(car);car.disable_input(pc);car.reset_driving_inputs();mv=car.get_chaos_movement();mv.set_handbrake_input(True)
 for cmd in ['DisableAllScreenMessages','r.MotionBlurQuality 0','t.MaxFPS 0','t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0','gt.Perf.LogSpikes 1','showhud']:u.SystemLibrary.execute_console_command(world,cmd,pc)
 mesh=car.get_component_by_class(u.SkeletalMeshComponent)
 for label,s in [('firm',247.),('crest',432.),('bog',551.)]:
  x,y,yaw=trial.at(path,s-7);car.set_actor_location_and_rotation(u.Vector(x,y,ground(x,y)+80),u.Rotator(yaw=yaw),False,True)
  mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector());yield from settle(6)
  cx,cy,_=trial.at(path,s);tx,ty,_=trial.at(path,s+9)
  yield from capture('TrackDetail_'+PHASE+'_'+label,(cx,cy,ground(cx,cy)+160),(tx,ty,ground(tx,ty)+20))
  u.SystemLibrary.execute_console_command(world,'gt.Perf.Reset',pc)
  report['timings'][label]=yield from frame_window(5)
  u.SystemLibrary.execute_console_command(world,'gt.Perf.Dump LT4_'+PHASE+'_'+label,pc)
  save()
 u.SystemLibrary.execute_console_command(world,'gt.Perf.LogSpikes 0',pc)
 report['ok']=True;report['timing_scope']='Stationary hidden-editor tick intervals, same map/camera; not GPU timing or owner drive acceptance';save()
 refs=author=tiles=ground=path=m=nodes=node=mel=mesh=mv=None
 yield from finish()

steps=run();deadline=0;began=time.monotonic();failed=False
def tick(dt):
 global deadline,busy,steps,failed
 if measure_frames and dt>0:frame_samples.append(dt)
 if busy:return
 busy=True
 try:
  assert time.monotonic()-began<1200,'Track detail check timeout'
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:
  u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
 except Exception:
  report['ok']=False;report['error']=traceback.format_exc();save();u.log_error(report['error'])
  if failed:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
  else:failed=True;steps=finish();deadline=time.monotonic()+next(steps)
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
