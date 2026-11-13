"""Original-Lua oracle, solid clod contact, synthetic spray. No test driving."""
import unreal as u
from pathlib import Path
import json,time,traceback,sys,re
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/MudRoad/NativeInteractions'
sys.path.insert(0,str(ROOT/'Art/tools'));from make_mixed_route import ground,route_y
report=dict(ok=False,images=[]);world=pc=car=fx=camera=None
def save():(OUT/'check-report.json').write_text(json.dumps(report,indent=2))
def settle(t):
 start=u.GameplayStatics.get_time_seconds(world)
 while u.GameplayStatics.get_time_seconds(world)-start<t:yield 0
def capture(name,pos,target,delay=1):
 global camera
 if camera:camera.destroy_actor()
 p=u.Vector(*pos);t=u.Vector(*target)
 camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(location=p,rotation=u.MathLibrary.find_look_at_rotation(p,t)),'NativeReview')
 camera.get_component_by_class(u.CameraComponent).set_field_of_view(65);camera.get_component_by_class(u.CameraComponent).set_editor_property('constrain_aspect_ratio',False);pc.set_view_target_with_blend(camera,0);yield from settle(delay)
 u.GameplayStatics.set_game_paused(world,True);yield .3
 f=OUT/(name+'.png');stamp=time.time();u.SystemLibrary.execute_console_command(world,'HighResShot 1440x900 filename="'+f.as_posix()+'"',pc)
 end=time.monotonic()+30
 while not f.exists() or f.stat().st_mtime<stamp:assert time.monotonic()<end;yield .2
 report['images'].append(str(f));u.GameplayStatics.set_game_paused(world,False);save()
def run():
 global world,pc,car,fx,camera
 assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GrandTour/ArtTests/MudRoad/L_MudRoad')
 ew=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 u.SystemLibrary.execute_console_command(ew,'Automation RunTests GrandTour.MudRunner');ew=None;yield 15
 while u.AutomationLibrary.are_automated_tests_running():yield .25
 u.GTPlayWindowLibrary.request_play_in_new_window(1440,900);yield 12
 world=u.EditorLevelLibrary.get_game_world();pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car();car.disable_input(pc)
 car.get_chaos_movement().set_handbrake_input(True)
 for cmd in ['DisableAllScreenMessages','r.MotionBlurQuality 0','t.MaxFPS 60','showhud']:u.SystemLibrary.execute_console_command(world,cmd,pc)
 fx=u.GameplayStatics.get_all_actors_of_class(world,u.GTMudRunnerWheelEffects)[0]
 expected=json.loads((OUT/'terrain-overlay-oracle.json').read_text())['pixels']
 rt=u.RenderingLibrary.create_render_target2d(world,8,8,u.TextureRenderTargetFormat.RTF_RGBA16F,u.LinearColor(),False,False)
 mat=u.load_asset('/Game/GrandTour/ArtTests/MudRoad/NativeInteractions/M_TerrainOverlayOracle');assert mat
 u.RenderingLibrary.draw_material_to_render_target(world,rt,mat);yield 1
 colours=[u.RenderingLibrary.read_render_target_raw_pixel(world,rt,x,y,False) for y in range(8) for x in range(8)]
 report['terrain_overlay_gpu_max_error']=max(abs(v-e) for c,p in zip(colours,expected) for v,e in zip([c.r,c.g,c.b],p))
 assert report['terrain_overlay_gpu_max_error']<.002,report['terrain_overlay_gpu_max_error']
 rt=mat=colours=None
 clods=u.GameplayStatics.get_all_actors_of_class(world,u.GTMudRunnerClod);assert len(clods)==275,len(clods)
 yield from settle(2)
 report['clods']=dict(count=len(clods),released=sum(int(a.released) for a in clods),masses=sorted(set(round(a.body.get_mass(),2) for a in clods)))
 assert report['clods']['masses']==[10.,20.],report['clods']
 assert report['clods']['released']==0,report['clods']
 a=clods[0];start=a.get_actor_location();bounds=a.get_actor_bounds(False)
 hit=u.SystemLibrary.line_trace_single(world,bounds[0]+u.Vector(0,0,100),bounds[0]-u.Vector(0,0,100),u.TraceTypeQuery.TRACE_TYPE_QUERY1,False,[],u.DrawDebugTrace.NONE,False)
 assert hit
 parts=hit.to_tuple();hit_actor=next((v for v in parts if isinstance(v,u.Actor)),None)
 report['clods']['visibility_hit']=bool(parts[0]);report['clods']['hit_actor']=hit_actor.get_name() if hit_actor else None
 assert parts[0] and hit_actor==a,report['clods']
 hit_actor=None
 report['clods']['suspension_query_hit']=car.get_chaos_movement().review_suspension_obstacle(a)
 assert report['clods']['suspension_query_hit'],report['clods']
 car_body=car.get_component_by_class(u.SkeletalMeshComponent)
 # EngineTypes.h exposes ECollisionResponse as CollisionResponseType; the
 # similarly named CollisionResponse is a separate reflected struct.
 report['clods']['vehicle_body_blocks']=car_body.get_collision_response_to_channel(u.CollisionChannel.ECC_DESTRUCTIBLE)==u.CollisionResponseType.ECR_BLOCK
 assert report['clods']['vehicle_body_blocks'] and a.body.get_collision_response_to_channel(car_body.get_collision_object_type())==u.CollisionResponseType.ECR_BLOCK
 car_body=None
 parts=hit=None
 a.review_impulse(u.Vector(120,0,60));yield from settle(.35)
 report['clods']['released_after_impulse']=a.released;report['clods']['moved_cm']=(a.get_actor_location()-start).length()
 assert a.released and report['clods']['moved_cm']>5
 a=None;clods=[]
 pc.select_lane(4);car.get_chaos_movement().set_handbrake_input(True);yield from settle(4)
 x=4350;y=route_y(x);z=ground(x,y)
 yield from capture('01_wet_sand',(x-500,y-650,z+360),(x,y-200,z))
 # Same fixed tyre fixture for wet mud and partially submerged water.
 fx.review_wheel(u.Vector(x,y-230,z+33),6.,28.,.3,0.,3.)
 yield from capture('02_native_mud_fling',(x+60,y-470,z+110),(x+60,y-230,z+50),.65)
 report['mud_fx']=fx.effect_report();assert re.search(r'mud_small=[1-9]',report['mud_fx'])
 fx.clear_review();pc.select_lane(6);car.get_chaos_movement().set_handbrake_input(True);yield from settle(5)
 fx.review_wheel(u.Vector(7300,-800,5),5.,24.,0.,.3,3.)
 yield from capture('03_native_water_spray',(6940,-1250,170),(7300,-800,30),.35)
 report['water_fx']=fx.effect_report();assert re.search(r'water_small=[1-9]',report['water_fx']) and re.search(r'water_fluid=[1-9]',report['water_fx'])
 fx.clear_review();yield from settle(2)
 report['wheel_centres']=[car.get_chaos_movement().soil_wheel_centre(i).to_tuple() for i in range(4)]
 assert all(abs(v[0]-car.get_actor_location().x)<300 for v in report['wheel_centres']),report['wheel_centres']
 report['native_response']=car.get_chaos_movement().native_substance_report();assert re.search(r'water_steps=[1-9]',report['native_response']),report['native_response']
 assert float(re.search(r'linear_ns=([\d.]+)',report['native_response'])[1])>0,report['native_response']
 report['ok']=True;save();yield from finish()
def finish():
 global world,pc,car,fx,camera
 if world:u.GameplayStatics.set_game_paused(world,False)
 u.EditorLevelLibrary.editor_end_play();yield 4
 world=pc=car=fx=camera=None
 u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Engine/Maps/Entry');u.SystemLibrary.collect_garbage();yield 3
steps=run();deadline=0;busy=False;began=time.monotonic()
def tick(dt):
 global steps,deadline,busy
 if busy:return
 busy=True
 try:
  assert time.monotonic()-began<420,'Deadline'
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:
  steps=None;import gc;gc.collect();u.SystemLibrary.collect_garbage();u.unregister_slate_post_tick_callback(handle);u.EditorPythonScripting.set_keep_python_script_alive(False)
 except Exception:
  report['ok']=False;report['error']=traceback.format_exc();save();u.log_error(report['error']);steps=finish();deadline=time.monotonic()+next(steps)
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
