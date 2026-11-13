"""RR1 validation and photo-reach captures in the saved LiDAR map."""
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve()
exec(compile((ROOT/'Art/Unreal/check_lidar_place.py').read_text().split('steps=run();')[0],'<lidar-check-helpers>','exec'))
import lidar_logging_trial as trial
report=dict(ok=False,owner_drive_pending=True,images=[],timings={})
last_frame_wall=None
def save():(OUT/'rivercheck.json').write_text(json.dumps(report,indent=2))

def run():
 global world,pc,car,camera
 les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(BASE+'/L_LidarStudy')
 refs=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
 author=next(a for a in refs if isinstance(a,u.GTProceduralGround));tiles=list(author.relief_tiles.values())
 bounds=[(t.get_actor_location().x,t.get_actor_location().y,t.span_cm,t) for t in tiles]
 def ground(x,y):
  for ox,oy,span,t in bounds:
   if ox<=x<ox+span and oy<=y<oy+span:return t.height_at(u.Vector2D(x,y))
  return author.base_height_at(u.Vector2D(x,y))
 sheet=next(a for a in refs if isinstance(a,u.GTWaterSheet) and not a.get_editor_property('mud_initial_domain'))
 offline=json.loads((OUT/'river-validation.json').read_text());assert offline['ok']
 probes=[]
 for p in offline['probes']:
  xy=u.Vector2D(p['x_cm'],p['y_cm']);assert sheet.covers(xy),p
  level=sheet.surface_cm_at(xy);depth=level-ground(p['x_cm'],p['y_cm'])
  assert abs(level-p['water_cm'])<2,(p,level)
  probes.append(dict(station_m=p['station_m'],water_cm=level,collision_depth_cm=depth))
 report['continuity_probes']=probes;report['offline']=dict(offline);report['offline'].pop('probes')
 # Check the entire channel after road construction, not just the nearest
 # baked shoreline pixel (a relief tile can move that fringe by centimetres).
 import struct
 raw=(OUT/'River-domain.bin').read_bytes();_,nx,ny,_,_,ox,oy,cell=struct.unpack('<5i3f',raw[:32])
 actual=set();fringe=[]
 for i,(level,depth,vx,vy) in enumerate(struct.iter_unpack('<4f',raw[32:-1])):
  if depth<=.015:continue
  x=ox+(i%nx+.5)*cell;y=oy+(i//nx+.5)*cell;d=level-ground(x,y)
  if d>1.5:actual.add(i)
  else:fringe.append(dict(x=x,y=y,depth_cm=d,baked_depth_cm=depth*100))
 labels={};component=0
 for start in actual:
  if start in labels:continue
  component+=1;todo=[start];labels[start]=component
  while todo:
   i=todo.pop();ix=i%nx;iy=i//nx
   for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)]:
    if not 0<=ix+dx<nx or not 0<=iy+dy<ny:continue
    j=i+dy*nx+dx
    if j in actual and j not in labels:labels[j]=component;todo.append(j)
 used=set();farthest=0.;r=json.loads((OUT/'authoring-reference.json').read_text())['river_points_cm']
 for station,p in enumerate(r):
  ix=int((p[0]-ox)/cell);iy=int((p[1]-oy)/cell);near=[]
  for dy in range(-4,5):
   for dx in range(-4,5):
    x,y=ix+dx,iy+dy;j=y*nx+x
    if 0<=x<nx and 0<=y<ny and j in labels:near.append((math.hypot(ox+(x+.5)*cell-p[0],oy+(y+.5)*cell-p[1]),labels[j]))
  assert near,('No collision-wet channel near station',station)
  distance,label=min(near);used.add(label);farthest=max(farthest,distance)
 report['collision_continuity']=dict(stations=len(r),course_components=len(used),wet_cells=len(actual),total_components=component,max_distance_cm=farthest,shore_cells_obscured_by_relief=fringe)
 save();assert len(used)==1,('Final collision splits river',used);assert farthest<800
 # Validate the usable mainland connection against final relief collision,
 # including the authored road, rather than just the offline DEM.
 bank=json.loads((OUT/'river-bank-validation.json').read_text())
 by,bx=bank['shape'];bo=bank['origin_m'];bs=bank['step_m'];dry=set();above=[]
 for i,level in enumerate(bank['water_m']):
  x=(bo[0]+i%bx*bs)*100;y=(bo[1]+i//bx*bs)*100
  h=ground(x,y)/100-level;above.append(h)
  if h>.12:dry.add(i)
 safe={i for i in dry if 3<=i%bx<bx-3 and 3<=i//bx<by-3 and all(i+dy*bx+dx in dry for dy in range(-3,4) for dx in range(-3,4))}
 probe_ids=[round((p[1]-bo[1])/bs)*bx+round((p[0]-bo[0])/bs) for p in bank['probes_m']]
 reached=set();todo=[probe_ids[0]] if probe_ids[0] in safe else []
 while todo:
  i=todo.pop()
  if i in reached:continue
  reached.add(i)
  for dy in range(-1,2):
   for dx in range(-1,2):
    j=i+dy*bx+dx
    if j in safe and j not in reached:todo.append(j)
 report['bank_connection']=dict(connected_with_3m_clearance=probe_ids[1] in reached,probe_above_water_m=[above[i] for i in probe_ids])
 save();assert probe_ids[1] in reached,'Final road/terrain detached the gravel bank'
 assert .12<above[probe_ids[0]]<.75,report['bank_connection']
 detail=json.loads((OUT/'riverdetail.json').read_text());groups=[a for a in refs if a.get_actor_label().startswith('LidarStudy_RiverDetail_')]
 assert len(groups)==detail['components'];report['detail']=detail
 assert sum(c.get_instance_count() for a in groups for c in a.get_components_by_class(u.InstancedStaticMeshComponent))==detail['instances']
 report['material_statistics']={}
 for name in ['Terrain','Detail']:
  m=u.load_asset(BASE+'/M_'+name);n=u.MaterialEditingLibrary.get_material_property_input_node(m,u.MaterialProperty.MP_BASE_COLOR)
  assert n.get_editor_property('desc')=='RR1Final';assert u.EditorAssetLibrary.get_metadata_tag(m,'RR1Version')=='RR1-1'
  if os.environ.get('GT_RIVER_ASSET_STATS')=='1':
   stats=u.MaterialEditingLibrary.get_statistics(m)
   report['material_statistics'][name]=dict(samplers=stats.num_samplers,pixel_instructions=stats.num_pixel_shader_instructions)
   assert 0<stats.num_samplers<=32,report['material_statistics'][name]
 report['ground_digest']=str(author.output_digest);save()
 import lidar_homestead as HS
 survey=json.loads((HS.OUT/'ground-survey.json').read_text())
 origin=survey['grid_origin'];step=survey['step_cm']
 error=max(abs(ground(*HS.xy(origin[0]+ix*step,origin[1]+iy*step))-z) for iy,row in enumerate(survey['heights_cm']) for ix,z in enumerate(row))
 report['homestead_ground_preservation']=dict(max_error_cm=error,prior_digest=survey['ground_digest'],new_digest=str(author.output_digest))
 save();assert error<.05,'River correction changed the homestead survey'
 report['texture_bytes']={}
 for asset in (['/Game/GrandTour/ArtTests/DeformableGravel/TA_GV_'+n for n in ['Color','Normal','ORH']]+[BASE+'/RiverDetail/T_RiverDetail']) if os.environ.get('GT_RIVER_ASSET_STATS')=='1' else []:
  t=u.load_asset(asset);size,fmt=u.GTMudArtLibrary.texture_all_mips_bytes(t)
  report['texture_bytes'][t.get_name()]=dict(bytes=size,format=fmt)
 path=trial.route(json.loads((OUT/'roads.json').read_text()))
 r=json.loads((OUT/'authoring-reference.json').read_text())['river_points_cm']
 les.editor_set_viewport_realtime(False);assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900)
 until=time.monotonic()+180
 while not world or not car:
  world=u.EditorLevelLibrary.get_game_world()
  if world:pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car() if pc else None
  assert time.monotonic()<until;yield .5
 pc.possess(car);car.disable_input(pc);car.reset_driving_inputs();car.get_chaos_movement().set_handbrake_input(True)
 for cmd in ['DisableAllScreenMessages','r.MotionBlurQuality 0','t.MaxFPS 0','t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0','gt.Perf.LogSpikes 1','showhud']:u.SystemLibrary.execute_console_command(world,cmd,pc)
 mesh=car.get_component_by_class(u.SkeletalMeshComponent)
 surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0]
 x,y,yaw=trial.at(path,114);q=surface.sample_surface(u.Vector2D(x,y))
 report['gravel_bar_soil']=dict(x_cm=x,y_cm=y,cap_cm=q.sinkage_cap_cm,cohesion=q.cohesion,wetness=q.wetness,clay_weight=q.clay_weight)
 px,py=[v*100 for v in bank['probes_m'][0]]
 car.set_actor_location_and_rotation(u.Vector(px,py-500,ground(px,py-500)+90),u.Rotator(yaw=90),False,True)
 mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector());yield from settle(4)
 q=surface.sample_surface(u.Vector2D(px,py));before=q.surface_delta_cm
 assert q.sinkage_cap_cm>0,'Gravel bank lost its deformable surface'
 surface.apply_review_soil_stroke(u.Vector2D(px-100,py),u.Vector2D(px+100,py),70.,3.,.8)
 yield from settle(6)
 after=surface.sample_surface(u.Vector2D(px,py)).surface_delta_cm
 report['bank_deformation']=dict(point_cm=[px,py],cap_cm=q.sinkage_cap_cm,before_cm=before,after_cm=after)
 save();assert after<before-.1,'Gravel bank did not deform under the review stroke'
 yield from capture('RR2_gravel_deformation',(px-250,py-280,ground(px,py)+160),(px,py,ground(px,py)))
 yield from capture('RR2_attached_bank',(-46300,-37000,6100),(-48500,-34500,4470))
 yield from capture('RR2_bank_from_mainland',(-49800,-35200,4900),(-47600,-34000,4480))
 cameras=[('RR1_ford',3352,3330),('RR1_bar',3310,3324),('RR1_rocky_shallows',3262,3290)]
 for name,station,target in cameras:
  p=r[station];t=r[target];cp=r[(station+target)//2];car.set_actor_location_and_rotation(u.Vector(cp[0],cp[1],ground(*cp[:2])+90),u.Rotator(yaw=math.degrees(math.atan2(t[1]-p[1],t[0]-p[0]))),False,True)
  mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector());yield from settle(5)
  yield from capture(name,(p[0],p[1],max(ground(*p[:2]),p[2])+180),(t[0],t[1],t[2]+40))
  u.SystemLibrary.execute_console_command(world,'gt.Perf.Reset',pc);report['timings'][name]=yield from frame_window(5)
  u.SystemLibrary.execute_console_command(world,'gt.Perf.Dump '+name,pc);save()
 p=r[3430];t=r[3395]
 yield from capture('RR1_continuity',(p[0],p[1],p[2]+6500),(t[0],t[1],t[2]))
 report['live_rut_sheets']=len([a for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTWaterSheet) if a.get_editor_property('mud_initial_domain')]);assert report['live_rut_sheets']==4
 report['ok']=True;report['timing_scope']='Stationary hidden-editor wall-clock tick intervals; not GPU timing or owner drive acceptance';save()
 refs=author=tiles=sheet=groups=mesh=surface=m=n=None
 yield from finish()

steps=run();deadline=0;began=time.monotonic();failed=False
def tick(dt):
 global deadline,busy,steps,failed,last_frame_wall
 now=time.monotonic()
 if measure_frames:
  if last_frame_wall is not None:frame_samples.append(now-last_frame_wall)
  last_frame_wall=now
 else:last_frame_wall=None
 if busy:return
 busy=True
 try:
  assert time.monotonic()-began<1200,'River check timeout'
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
 except Exception:
  report['ok']=False;report['error']=traceback.format_exc();save();u.log_error(report['error'])
  if failed:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
  else:failed=True;steps=finish();deadline=time.monotonic()+next(steps)
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
