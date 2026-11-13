"""No driving: native arithmetic, map load, stationary mud/water and reset smoke check."""
import unreal as u
from pathlib import Path
import json,time,math,traceback,sys
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/MudRoad/NativeStage4'
if '-GTMudExitProbe' in u.SystemLibrary.get_command_line():
 import ctypes
 exit_probe=ctypes.WinDLL(str(ROOT/'Art/tools/mud_exit_probe.dll'));exit_probe.Install()
sys.path.insert(0,str(ROOT/'Art/tools'));from make_mud_road import centre,heading
LEVEL='/Game/GrandTour/ArtTests/MudRoad/L_MudRoad';BASE='/Game/GrandTour/ArtTests/MudRoad/NativeStage4'
report=dict(ok=False,images=[]);world=pc=car=surface=sheet=None

def save():(OUT/'playtest-report.json').write_text(json.dumps(report,indent=2))
def bind():
 global world,pc,car,surface,sheet
 world=u.EditorLevelLibrary.get_game_world();pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car();assert car
 surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0];sheet=surface.simulated_water
 assert surface.use_native_substance_response

def capture(name):
 u.GameplayStatics.set_game_paused(world,True);yield 1
 p=OUT/(name+'.png');stamp=time.time();u.SystemLibrary.execute_console_command(world,'HighResShot 1440x900 filename="'+p.as_posix()+'"',pc)
 deadline=time.monotonic()+30
 while not p.exists() or p.stat().st_mtime<stamp:
  assert time.monotonic()<deadline;yield .2
 report['images'].append(str(p));u.GameplayStatics.set_game_paused(world,False)

def run():
 global world,pc,car,surface,sheet
 assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(LEVEL)
 ew=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 u.SystemLibrary.execute_console_command(ew,'Automation RunTests GrandTour.MudRunner');ew=None;yield 14
 while u.AutomationLibrary.are_automated_tests_running():yield .25
 u.GTPlayWindowLibrary.request_play_in_new_window(1440,900);yield 12;bind()
 for cmd in ['DisableAllScreenMessages','r.MotionBlurQuality 0','t.MaxFPS 60']:u.SystemLibrary.execute_console_command(world,cmd,pc)
 expected=json.loads((OUT/'mud-color-oracle.json').read_text())['pixels']
 rt=u.RenderingLibrary.create_render_target2d(world,8,8,u.TextureRenderTargetFormat.RTF_RGBA16F,u.LinearColor(),False,False)
 mat=u.load_asset(BASE+'/M_NativeColorOracle');assert mat
 u.RenderingLibrary.draw_material_to_render_target(world,rt,mat);yield 1
 colours=[u.RenderingLibrary.read_render_target_raw_pixel(world,rt,x,y,False) for y in range(8) for x in range(8)]
 report['native_colour_max_error']=max(abs(v-e) for c,p in zip(colours,expected) for v,e in zip([c.r,c.g,c.b],p));assert report['native_colour_max_error']<.005
 rt=mat=colours=None
 expected=json.loads((OUT/'grade-oracle.json').read_text())['pixels']
 rt=u.RenderingLibrary.create_render_target2d(world,8,8,u.TextureRenderTargetFormat.RTF_RGBA16F,u.LinearColor(),False,False)
 mat=u.load_asset(BASE+'/M_NativeGradeOracle');assert mat
 u.RenderingLibrary.draw_material_to_render_target(world,rt,mat);yield 1
 colours=[u.RenderingLibrary.read_render_target_raw_pixel(world,rt,x,y,False) for y in range(8) for x in range(8)]
 report['native_grade_max_error']=max(abs(v-e) for c,p in zip(colours,expected) for v,e in zip([c.r,c.g,c.b],p));assert report['native_grade_max_error']<.005
 rt=mat=colours=None
 yield from capture('01_native_start')
 visual=u.GameplayStatics.get_all_actors_of_class(world,u.GTMudRunnerVisual)[0]
 visual.add_review_tread(u.Vector(-2250,centre(-2250)-85,0),u.Vector(-1950,centre(-1950)-85,0),25,0)
 visual.add_review_tread(u.Vector(-2250,centre(-2250)+85,0),u.Vector(-1950,centre(-1950)+85,0),25,1)
 yield 2
 report['tread_fixture']=visual.get_research_report();assert 'tread_segments=0' not in report['tread_fixture']
 visual=None
 camera_pos=u.Vector(-2110,centre(-2110)-400,420);target=u.Vector(-2110,centre(-2110),0)
 review_camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(location=camera_pos,rotation=u.MathLibrary.find_look_at_rotation(camera_pos,target)),'NativeTread_ReviewCamera')
 review_camera.get_component_by_class(u.CameraComponent).set_field_of_view(60)
 pc.set_view_target_with_blend(review_camera,0);yield 2
 yield from capture('03_native_tread_fixture')
 pc.set_view_target_with_blend(car,0);review_camera.destroy_actor();review_camera=None
 # Fill and wrap the bounded geometry store with synthetic strips, without driving.
 visual=u.GameplayStatics.get_all_actors_of_class(world,u.GTMudRunnerVisual)[0]
 for row in range(40):
  visual.add_review_tread(u.Vector(-1800,centre(-1800)-100+row*5,0),u.Vector(-300,centre(-300)-100+row*5,0),25,row%2)
 yield 2
 report['tread_capacity_fixture']=visual.get_research_report()
 assert 'tread_segments=4096' in report['tread_capacity_fixture'] and 'tread_sections=16' in report['tread_capacity_fixture']
 visual=None
 report['start_response']=car.get_chaos_movement().native_substance_report()
 # Place in the dip and hold the brakes. This is a system smoke check, not a driving assessment.
 pc.select_lane(3);car.set_actor_location_and_rotation(u.Vector(650,centre(650),100),u.Rotator(yaw=heading(650)),False,True)
 car.disable_input(pc);car.get_chaos_movement().set_handbrake_input(True);yield 6
 report['pond_response']=car.get_chaos_movement().native_substance_report()
 report['pond_position']=car.get_actor_location().to_tuple();report['pond_speed_cm_s']=car.get_velocity().length()
 report['water_cm']=[w.water_depth_m*100 for w in car.get_traction().wheels]
 report['physical_mud']=[dict(q_cm=surface.sample_surface(u.Vector2D(w.contact_point.x,w.contact_point.y)).native_extrude_cm,h_cm=surface.sample_surface(u.Vector2D(w.contact_point.x,w.contact_point.y)).native_upper_cm) for w in car.get_traction().wheels]
 assert all(math.isfinite(v) for v in report['pond_position']) and report['pond_speed_cm_s']<200,'Unstable stationary response'
 assert 'native_steps=0' not in report['pond_response']
 assert max(report['water_cm'])>5,'Standing water query failed'
 assert all(p['q_cm']>0 for p in report['physical_mud']),'Physical mud field not bound'
 probe=u.Vector2D(1800,centre(1800));dry=u.Vector2D(3000,3000)
 before=surface.sample_surface(probe);dry_before=surface.sample_surface(dry)
 for _ in range(8):surface.apply_review_native_contact(probe,1.)
 surface.apply_review_native_contact(dry,1.)
 after=surface.sample_surface(probe);dry_after=surface.sample_surface(dry)
 report['physical_field_fixture']=dict(q_before=before.native_extrude_cm,q_after=after.native_extrude_cm,h_change=after.native_upper_cm-before.native_upper_cm,visual_change=after.surface_delta_cm-before.surface_delta_cm,dry_q=dry_after.native_extrude_cm)
 assert after.native_extrude_cm>before.native_extrude_cm and after.native_upper_cm==before.native_upper_cm
 assert after.surface_delta_cm==before.surface_delta_cm and dry_after.native_extrude_cm==0
 before=after=dry_before=dry_after=None
 report['water']=sheet.mud_water_diagnostics();report['surface']=surface.get_surface_report()
 yield from capture('02_native_pond')
 visual=u.GameplayStatics.get_all_actors_of_class(world,u.GTMudRunnerVisual)[0];report['visual']=visual.get_research_report();visual=None
 pc.reset_lab();world=pc=car=surface=sheet=None;yield 12;bind()
 assert abs(car.get_actor_location().x+2450)<120
 report['reset_response']=car.get_chaos_movement().native_substance_report()
 report['reset_physical_q']=surface.sample_surface(probe).native_extrude_cm
 assert abs(report['reset_physical_q']-report['physical_field_fixture']['q_before'])<.00001,'Physical mud reset failed'
 reset_visual=u.GameplayStatics.get_all_actors_of_class(world,u.GTMudRunnerVisual)[0]
 report['reset_visual']=reset_visual.get_research_report();reset_visual=None
 assert 'tread_segments=4096' not in report['reset_visual'] and 'tread_sections=16' not in report['reset_visual'],'Tread storage survived level reset'
 report['ok']=True;save();yield from finish()

def finish():
 global world,pc,car,surface,sheet
 u.EditorLevelLibrary.editor_end_play();yield 4
 world=pc=car=surface=sheet=None
 u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Engine/Maps/Entry');u.SystemLibrary.collect_garbage();yield 3
steps=run();deadline=0;busy=False;began=time.monotonic()
def tick(dt):
 global deadline,busy,steps
 if busy:return
 busy=True
 try:
  assert time.monotonic()-began<400,'Smoke deadline'
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:
  steps=None;import gc;gc.collect();u.SystemLibrary.collect_garbage();u.unregister_slate_post_tick_callback(handle);u.EditorPythonScripting.set_keep_python_script_alive(False)
  # Let -ExecutePythonScript's own tick destroy its FAsyncTaskNotification and
  # defer exit. Calling quit_editor here sets IsEngineExitRequested first, so
  # EditorPythonExecuter skips that cleanup and retains Slate text until teardown.
 except Exception:
  report['ok']=False;report['error']=traceback.format_exc();save();u.log_error(report['error'])
  if world:u.GameplayStatics.set_game_paused(world,False)
  steps=finish();deadline=time.monotonic()+next(steps)
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
