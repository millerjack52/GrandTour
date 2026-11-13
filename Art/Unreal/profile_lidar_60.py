"""PF60: CPU/GPU CSV captures in the real saved map. No asset or level writes."""
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve()
exec(compile((ROOT/'Art/Unreal/stat_lidar_place.py').read_text().split('steps=run();')[0],'<csv-helpers>','exec'))
import lidar_logging_trial as trial
import math
report=dict(ok=False,resolution=[1600,900],tests=[],images=[])
camera=None
LABEL=os.environ.get('GT_PF60_LABEL','baseline')
def save():
 (OUT/'profile60.json').write_text(json.dumps(report,indent=2))
 (OUT/('profile60-'+LABEL+'.json')).write_text(json.dumps(report,indent=2))
def wait_wall(seconds):
 end=time.monotonic()+seconds
 while time.monotonic()<end:yield .01
def measure(name):
 before=csv_files();console('gt.Perf.Reset');console('csvprofile start');yield from wait_wall(8);console('csvprofile stop');console('gt.Perf.Dump PF60_'+name)
 until=time.monotonic()+60;path=None
 while time.monotonic()<until:
  new=sorted(csv_files()-before)
  if new:
   p=CSV_DIR/new[-1];size=p.stat().st_size;yield 1
   if size>0 and p.stat().st_size==size:path=p;break
  else:yield .25
 assert path,'CSV not produced'
 header,body=read_csv(path)
 columns={n:column(header,body,n) for n in header if n in COLUMNS or n.startswith('GPU/')}
 report['tests'].append(dict(name=name,csv=str(path),columns=columns));save()
def run():
 global world,pc,car,camera
 les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(BASE+'/L_LidarStudy');les.editor_set_viewport_realtime(False)
 assert u.GTPlayWindowLibrary.request_play_in_new_window(1600,900)
 until=time.monotonic()+180
 while not world or not car:
  world=u.EditorLevelLibrary.get_game_world()
  if world:pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car() if pc else None
  assert time.monotonic()<until;yield .5
 pc.possess(car);car.disable_input(pc);car.reset_driving_inputs();car.get_chaos_movement().set_handbrake_input(True)
 names=['r.ScreenPercentage','r.VSync','r.VSyncEditor','r.Shadow.Virtual.ResolutionLodBiasDirectional','r.Shadow.Virtual.SMRT.RayCountDirectional','r.Lumen.ScreenProbeGather.DownsampleFactor','r.Lumen.Reflections.DownsampleFactor','r.DynamicRes.OperationMode','r.AntiAliasingMethod']
 report['cvars']={n:u.SystemLibrary.get_console_variable_float_value(n) for n in names}
 for cmd in ['DisableAllScreenMessages','t.MaxFPS 0','t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0','r.VSync 0','r.VSyncEditor 0','r.ScreenPercentage 100','r.DynamicRes.OperationMode 0','r.GPUStatsEnabled 1','r.GPUCsvStatsEnabled 1']:console(cmd)
 for cmd in os.environ.get('GT_PF60_COMMANDS','').split(';'):
  if cmd.strip():console(cmd)
 actors=u.GameplayStatics.get_all_actors_of_class(world,u.Actor)
 author=next(a for a in actors if isinstance(a,u.GTProceduralGround));tiles=[(t.get_actor_location(),t.span_cm,t) for t in author.relief_tiles.values()]
 def ground(x,y):
  for o,s,t in tiles:
   if o.x<=x<o.x+s and o.y<=y<o.y+s:return t.height_at(u.Vector2D(x,y))
  return author.base_height_at(u.Vector2D(x,y))
 path=trial.route(json.loads((OUT/'roads.json').read_text()))
 r=json.loads((OUT/'authoring-reference.json').read_text())['river_points_cm'];p=r[3352];t=r[3330]
 locations=[('river',p[0],p[1],math.degrees(math.atan2(t[1]-p[1],t[0]-p[0])))]
 for station in [214,552]:locations.append(('bog'+str(station),*trial.at(path,station)))
 site=sites[0];locations.append(('access',*site['center'],site['yaw']))
 mesh=car.get_component_by_class(u.SkeletalMeshComponent)
 for name,x,y,yaw in locations:
  z=ground(x,y);car.set_actor_location_and_rotation(u.Vector(x,y,z+90),u.Rotator(yaw=yaw),False,True);mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector())
  if camera:camera.destroy_actor()
  a=math.radians(yaw);pos=u.Vector(x-math.cos(a)*650,y-math.sin(a)*650,z+320);target=u.Vector(x+math.cos(a)*800,y+math.sin(a)*800,z+80)
  camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(location=pos,rotation=u.MathLibrary.find_look_at_rotation(pos,target)),'PF60Camera');camera.camera_component.set_field_of_view(68);pc.set_view_target_with_blend(camera,0)
  yield from wait_wall(10);yield from measure(name)
  if name=='river' and os.environ.get('GT_PF60_AB','1')=='1':
   for label,cmd,undo in [('render75','r.ScreenPercentage 75','r.ScreenPercentage 100'),('no_shadows','r.ShadowQuality 0','r.ShadowQuality 5'),('no_lumen','r.Lumen.DiffuseIndirect.Allow 0','r.Lumen.DiffuseIndirect.Allow 1'),('no_reflections','r.Lumen.Reflections.Allow 0','r.Lumen.Reflections.Allow 1')]:
    console(cmd);yield from wait_wall(5);yield from measure(label);console(undo);yield from wait_wall(3)
 report['ok']=True;save();actors=author=tiles=mesh=None;yield from finish()
steps=run();deadline=0;began=time.monotonic();failed=False
def tick(dt):
 global deadline,busy,steps,failed
 if busy:return
 busy=True
 try:
  assert time.monotonic()-began<1200
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
 except Exception:
  report.update(ok=False,error=traceback.format_exc());save();u.log_error(report['error'])
  if failed:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
  else:failed=True;steps=finish();deadline=time.monotonic()+next(steps)
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
