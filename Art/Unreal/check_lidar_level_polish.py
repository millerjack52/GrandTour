"""LP6 regression in the saved LiDAR level, including a newly opened river shore."""
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve()
exec(compile((ROOT/'Art/Unreal/check_lidar_place.py').read_text().split('steps=run();')[0],'<lidar-check-helpers>','exec'))
from lidar_grounding import GroundSampler
QA=ROOT/'Saved/LidarAuthoringQA/LP6';QA.mkdir(parents=True,exist_ok=True)
report=dict(ok=False,images=[],grounding=[],owner_accepted=False)
def save():(QA/'check.json').write_text(json.dumps(report,indent=2))
def run():
 global world,pc,car,camera
 les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(BASE+'/L_LidarStudy')
 refs=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
 ground=GroundSampler(next(a for a in refs if isinstance(a,u.GTProceduralGround)))
 for a in refs:
  if a.get_actor_label() not in ['LidarStudy_Forest','LidarStudy_Understory']:continue
  for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
   if not c.static_mesh:continue
   name=c.static_mesh.get_name()
   if not (name.startswith('SM_Canopy') or any(s in name for s in ['Fern','Kiokio','Coprosma','Harakeke','Kanuka','TiKouka','Matagouri','Rush','Grass','Tussock'])):continue
   errors=[]
   for i in range(0,c.get_instance_count(),97):
    p=c.get_instance_transform(i,True).translation;errors.append(abs(p.z-ground.height(p.x,p.y)+3))
   assert not errors or max(errors)<.2,(name,max(errors))
   report['grounding'].append(dict(mesh=name,samples=len(errors),max_error_cm=max(errors,default=0)))
 # Pure C++ regressions run separately under NullRHI. Do not queue them behind
 # the hidden editor's interactive-framerate gate and accidentally skip them.
 les.editor_set_viewport_realtime(False);assert u.GTPlayWindowLibrary.request_play_in_new_window(1600,900)
 until=time.monotonic()+180
 while not world or not car:
  world=u.EditorLevelLibrary.get_game_world()
  if world:pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car() if pc else None
  assert time.monotonic()<until;yield .5
 car.reset_driving_inputs();car.get_chaos_movement().set_handbrake_input(True)
 assert pc.exit_car();walker=pc.get_player_character();assert walker
 surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0]
 sheet=next(s for s in u.GameplayStatics.get_all_actors_of_class(world,u.GTWaterSheet) if s.get_editor_property('domain_ground_surface'))
 for cmd in json.loads((ROOT/'Art/lidar_performance.json').read_text())['commands']+['DisableAllScreenMessages','showhud','gt.Perf.LogSpikes 1']:u.SystemLibrary.execute_console_command(world,cmd,pc)
 r=json.loads((OUT/'authoring-reference.json').read_text())['river_points_cm']
 for name,i,j in [('LP6_ford_walk',3352,3330),('LP6_bar_walk',3310,3324),('LP6_shallows_walk',3262,3290)]:
  p,t=r[i],r[j];walker.set_actor_location(u.Vector(p[0],p[1],ground.height(*p[:2])+100),False,True);yield from settle(3)
  yield from capture(name,(p[0],p[1],ground.height(*p[:2])+170),(t[0],t[1],t[2]+60))
 dressing=u.GameplayStatics.get_all_actors_of_class(world,u.GTGroundedDressing)
 assert dressing,'Missing deformation-following dressing'
 bound=[]
 for a in dressing:
  for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
   assert c.get_collision_enabled()==u.CollisionEnabled.NO_COLLISION
   for material in c.get_editor_property('override_materials'):
    if isinstance(material,u.MaterialInstanceDynamic):bound.append(material.get_scalar_parameter_value('GTLS_Ready'))
 assert bound and min(bound)>.5,('Unbound live dressing',bound)
 report['live_dressing']=dict(actors=len(dressing),bound_materials=len(bound),min_ready=min(bound))
 candidates=[]
 for i in range(3260,3370,4):
  p=r[i]
  for dx in range(-1100,1101,25):
   for dy in range(-1100,1101,25):
    x,y=p[0]+dx,p[1]+dy;q=u.Vector2D(x,y)
    if sheet.covers(q):continue
    soil=surface.sample_surface(q)
    if soil.sinkage_cap_cm<2:continue
    for vx,vy in [(25,0),(-25,0),(0,25),(0,-25)]:
     w=u.Vector2D(x+vx,y+vy)
     if not sheet.covers(w):continue
     gap=ground.height(x,y)+soil.surface_delta_cm-sheet.surface_cm_at(w)
     available=soil.sinkage_cap_cm+soil.surface_delta_cm-gap
     if .3<gap<6 and available>1:candidates.append((-available,gap,x,y,w.x,w.y))
  if candidates:break
 assert candidates,'No valid erodible river margin for deformation check'
 _,gap,x,y,wx,wy=min(candidates);q=u.Vector2D(x,y)
 walker.set_actor_location(u.Vector(x+200,y+200,ground.height(x+200,y+200)+100),False,True);yield from settle(3)
 before=surface.sample_surface(q).surface_delta_cm;was_wet=sheet.covers(q)
 assert not was_wet
 for _ in range(4):
  surface.apply_review_soil_stroke(u.Vector2D(wx,wy),u.Vector2D(x+(x-wx)*3,y+(y-wy)*3),100.,35.,.8)
  # Native contacts MAX-composite within a frame, then StepNative consumes them.
  yield .15
 yield from settle(2)
 live_soil=surface.sample_surface(q);after=live_soil.surface_delta_cm
 # Use the runtime ground query, as wheel immersion does. The authoring sampler
 # is suitable for seating assets but differs at triangle interpolation edges.
 # Instantaneous waves can also sit below the authored mean coverage threshold.
 report['deformation']=dict(point=[x,y],gap_cm=gap,before_cm=before,after_cm=after,wet_before=was_wet,wet_after=sheet.covers(q),depth_cm=live_soil.water_depth_cm,authoring_depth_cm=sheet.surface_cm_at(q)-ground.height(x,y)-after,diagnostics=sheet.water_diagnostics())
 save();assert after<before-.5 and report['deformation']['wet_after'] and report['deformation']['depth_cm']>.5,report['deformation']
 yield from capture('LP6_opened_river_rut',(x+270,y+220,ground.height(x,y)+190),(x,y,ground.height(x,y)-10))
 # Same framing at a distance and across the forest, with the actual river window following the walker.
 p,t=r[3338],r[3339];dx,dy=t[0]-p[0],t[1]-p[1]
 walker.set_actor_location(u.Vector(p[0],p[1],ground.height(*p[:2])+100),False,True)
 yield from capture('LP6_forest_across',(p[0],p[1],ground.height(*p[:2])+170),(p[0]-dy*30,p[1]+dx*30,p[2]+1000))
 report['ok']=True;save();refs=surface=sheet=walker=ground=None
 yield from finish()
steps=run();deadline=0;began=time.monotonic()
def tick(dt):
 global busy,deadline,steps
 if busy:return
 busy=True
 try:
  assert time.monotonic()-began<1200
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
 except Exception:
  report.update(ok=False,error=traceback.format_exc());save();u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
