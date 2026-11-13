"""Stationary runtime and full-coverage checks. The only driving is the RD1 Drive step (docs/LIDAR_PLACE_PLAN.md RD1): 25 m on the open Riverside stretch and 25 m on the bush climb, after the sites."""
import unreal as u
from pathlib import Path
import json,time,traceback,math,hashlib,re,gc,bisect,os
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/LidarStudy/Place';BASE='/Game/GrandTour/ArtTests/LidarStudy'
data=json.loads((OUT/'prepare.json').read_text());sites=json.loads((OUT/'installed-sites.json').read_text());report=dict(ok=False,driving_tested=False,sites=[],images=[])
world=pc=car=camera=None;busy=False;frame_samples=[];measure_frames=False

def save():(OUT/'check.json').write_text(json.dumps(report,indent=2))
def nums(s):return {k:float(v) for k,v in re.findall(r'(\w+)=(-?\d+(?:\.\d+)?)',s)}
def native_property_node(material,prop):
 """RR1 wraps the existing normal/roughness; verify the exact passthrough pin."""
 mel=u.MaterialEditingLibrary
 node=mel.get_material_property_input_node(material,prop)
 if isinstance(node,u.MaterialExpressionCustom) and str(node.get_editor_property('desc'))=='RR1Final':
  pin,output={u.MaterialProperty.MP_NORMAL:('NativeN','Normal'),u.MaterialProperty.MP_ROUGHNESS:('NativeR','Rough')}[prop]
  assert str(mel.get_material_property_input_node_output_name(material,prop))==output
  names=[str(i.get_editor_property('input_name')) for i in node.get_editor_property('inputs')]
  inputs=list(mel.get_inputs_for_material_expression(material,node))
  assert pin in names and len(inputs)==len(names)
  node=inputs[names.index(pin)];assert node,('RR1 missing native input',pin)
 return node
def settle(seconds):
 start=u.GameplayStatics.get_time_seconds(world);deadline=time.monotonic()+180
 while u.GameplayStatics.get_time_seconds(world)-start<seconds:
  assert time.monotonic()<deadline;yield .1

def frame_window(seconds):
 """Game-time window of per-tick frame times (the editor's own tick under -RenderOffScreen, hidden): returns mean, p50, p95 in ms and the sample count."""
 global measure_frames
 frame_samples.clear();measure_frames=True
 yield from settle(seconds)
 measure_frames=False;s=sorted(frame_samples);n=len(s)
 return dict(ms_mean=1000*sum(s)/max(1,n),ms_p50=1000*s[n//2] if n else None,ms_p95=1000*s[min(n-1,int(n*.95))] if n else None,samples=n)

def capture(name,pos,target):
 global camera
 if camera:camera.destroy_actor()
 p=u.Vector(*pos);t=u.Vector(*target);camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(location=p,rotation=u.MathLibrary.find_look_at_rotation(p,t)),'LiDARReview')
 camera.camera_component.set_field_of_view(68);camera.camera_component.set_editor_property('constrain_aspect_ratio',False);pc.set_view_target_with_blend(camera,0);yield from settle(3)
 path=OUT/(name+'.png');stamp=time.time();u.GameplayStatics.set_game_paused(world,True);yield .3
 u.SystemLibrary.execute_console_command(world,'HighResShot 1440x900 filename="'+path.as_posix()+'"',pc)
 until=time.monotonic()+45
 while not path.exists() or path.stat().st_mtime<stamp:assert time.monotonic()<until;yield .3
 u.GameplayStatics.set_game_paused(world,False);report['images'].append(str(path));save()

# RD1 Drive step (docs/LIDAR_PLACE_PLAN.md RD1; owner 2026-10-19: "the roads ... don't deform at all"). The only place the Check drives: the car is teleported onto the open Riverside access stretch (prepare's Clay_track_open spot, about 300 m from the gate) and onto the bush climb (prepare's Bush_track spot,
# 400 m before the house), driven 25 m along the road at a fixed throttle by pure pursuit on the road polyline (the mud-route check's lane_drive steering gain, low range and diff lock as its lane_run), braked, and the track behind it is read back and captured from 4 m up and 8 m behind the car.
# Readbacks: the surface across the track (SurfaceDeltaCm, CompressionCm, MudHeightAboveBaseCm) before and after, the relief tile under the car (mesh material class and name, whether its dynamic MID exists and what MR_VisualWindow / MR_ActiveGrid / GTLS_* it carries), the visual grid's own MID for comparison,
# and the displacement chains (World Position Offset, displacement, opacity mask, normal) of the LiDAR M_Detail and M_Terrain clones against the ProceduralGround template. GT_CHECK_DRIVE_ONLY=1 in the calling shell runs only this step (about 4 minutes) while it is being developed.
DRIVE_ONLY=os.environ.get('GT_CHECK_DRIVE_ONLY')=='1';DRIVE_EVIDENCE_HIDE_TILES=os.environ.get('GT_CHECK_HIDE_TILES')=='1'   # RD1 diagnosis aid: also capture the bush trail with the relief tiles hidden
PERF=os.environ.get('GT_CHECK_PERF')=='1'   # PF1 (docs/LIDAR_PLACE_PLAN.md PF1): gt.Perf.LogSpikes 1 for the whole run, an idle window and a Dump per drive leg, and (with GT_CHECK_DRIVE_ONLY=1) the 40 m NE paddock leg; off by default so the normal Check is unchanged
PERF_PADDOCK_RUN_CM=4000.;PERF_PADDOCK_START_CM=1200.   # the run starts 12 m from the trough (the three hay bales sit within 6 m of it)
drive_on=False;drive_cmd={}
RD1_THROTTLE=.5;RD1_RUN_CM=2500.;RD1_LOOK_CM=600.;RD1_MAX_S=45.
def rd1_path(name):
 hc=data['captures']['House_yard']['anchor_cm'];pts=[list(p) for p in next(r['points'] for r in json.loads((OUT/'roads.json').read_text()) if r['name']==name)]
 if math.dist(pts[0],hc)<math.dist(pts[-1],hc):pts=pts[::-1]   # prepare's captures run from the end farthest from the house toward it
 cum=[0.]
 for a,b in zip(pts,pts[1:]):cum.append(cum[-1]+math.dist(a,b))
 return pts,cum
def rd1_at(pts,cum,s):
 s=min(max(s,0.),cum[-1]);k=max(1,min(bisect.bisect_right(cum,s),len(cum)-1));a,b=pts[k-1],pts[k];f=(s-cum[k-1])/max(1e-9,cum[k]-cum[k-1]);return a[0]+(b[0]-a[0])*f,a[1]+(b[1]-a[1])*f
def rd1_project(pts,cum,x,y,lo=0.,hi=None):
 """(station, distance) in cm of the closest point to (x,y) on the segments whose stations lie in [lo, hi]."""
 hi=cum[-1] if hi is None else hi;best=(None,1e18);k0=max(1,bisect.bisect_left(cum,lo));k1=min(len(cum)-1,bisect.bisect_right(cum,hi)+1)
 for k in range(k0,k1+1):
  a,b=pts[k-1],pts[k];dx,dy=b[0]-a[0],b[1]-a[1];l2=dx*dx+dy*dy or 1e-9;t=max(0.,min(1.,((x-a[0])*dx+(y-a[1])*dy)/l2));d=math.hypot(x-(a[0]+dx*t),y-(a[1]+dy*t))
  if d<best[1]:best=(cum[k-1]+t*math.sqrt(l2),d)
 return best
def drive_ctrl():
 """Per tick while drive_on: steer at the road polyline RD1_LOOK_CM ahead of the car's projection (lane_drive's gain), fixed throttle, and a 4 Hz trace."""
 d=drive_cmd;p=car.get_actor_location();s,off=rd1_project(d['pts'],d['cum'],p.x,p.y,max(0.,d['s']-1500.),d['s']+3500.);d['s']=s;d['max_off']=max(d['max_off'],off)
 tx,ty=rd1_at(d['pts'],d['cum'],s+RD1_LOOK_CM);yaw=car.get_actor_rotation().yaw;err=(math.degrees(math.atan2(ty-p.y,tx-p.x))-yaw+180)%360-180
 car.set_raw_steer(max(-.65,min(.65,err/24)));mv=car.get_chaos_movement();mv.set_throttle_input(RD1_THROTTLE);mv.set_brake_input(0)
 now=u.GameplayStatics.get_time_seconds(world)
 if now-d['t_last']>=.25:d['t_last']=now;d['trace'].append(dict(t=round(now-d['t0'],2),x=round(p.x,1),y=round(p.y,1),yaw=round(yaw,1),s=round(s,1),off_cm=round(off,1),speed_mps=round(car.get_velocity().length()*.01,3)))
def rd1_sample(surface,x,y):
 q=surface.sample_surface(u.Vector2D(x,y));return dict(x=round(x,1),y=round(y,1),surface_delta_cm=round(q.surface_delta_cm,3),compression_cm=round(q.compression_cm,3),mud_height_above_base_cm=round(q.mud_height_above_base_cm,3),sinkage_cap_cm=round(q.sinkage_cap_cm,2))
def rd1_across(surface,cx,cy,yaw_deg,offsets=(-170,-85,0,85,170)):
 """Five samples across the track at (cx,cy): offsets in cm along the left normal of the heading."""
 fx,fy=math.cos(math.radians(yaw_deg)),math.sin(math.radians(yaw_deg))
 return [dict(offset_cm=o,**rd1_sample(surface,cx-fy*o,cy+fx*o)) for o in offsets]
def rd1_transect(surface,cx,cy,yaw_deg,half=250,step=5):
 """Every 5 cm across +-250 cm: the lowest surface delta, the largest compression and mud height above base (and where)."""
 fx,fy=math.cos(math.radians(yaw_deg)),math.sin(math.radians(yaw_deg));low=(0.,None);comp=(0.,None);mud=(0.,None);rows=[]
 for o in range(-half,half+1,step):
  q=surface.sample_surface(u.Vector2D(cx-fy*o,cy+fx*o))
  if q.surface_delta_cm<low[0]:low=(q.surface_delta_cm,o)
  if q.compression_cm>comp[0]:comp=(q.compression_cm,o)
  if q.mud_height_above_base_cm>mud[0]:mud=(q.mud_height_above_base_cm,o)
 return dict(lowest_surface_delta_cm=round(low[0],3),lowest_at_offset_cm=low[1],max_compression_cm=round(comp[0],3),max_compression_at_offset_cm=comp[1],max_mud_above_base_cm=round(mud[0],3),max_mud_at_offset_cm=mud[1])
RD1_MID_SCALARS=('MR_ActiveGrid','MR_VisualGrid','GTLS_Ready','GTLS_DepthScale','GTLS_POMEnabled','GTLS_DisplacementEnabled');RD1_MID_VECTORS=('MR_VisualWindow','GTLS_Window','GTLS_PaintWindow');RD1_MID_TEXTURES=('GTLS_Field','GTLS_Water','GTLS_Paint')
def rd1_mid(m):
 """What a mesh's material slot is: class, name, parent, the base material's parameter names that matter, and (for a dynamic instance) the values of the MR_* and GTLS_* parameters it carries."""
 mel=u.MaterialEditingLibrary;r=dict(cls=m.get_class().get_name(),name=m.get_name(),is_dynamic_instance=isinstance(m,u.MaterialInstanceDynamic))
 try:par=m.get_editor_property('parent');r['parent']=par.get_name() if par else None;r['parent_path']=par.get_path_name() if par else None
 except Exception as err:par=None;r['parent']='unreadable '+repr(err)[:90]
 if par is not None:
  try:
   sn=[str(n) for n in mel.get_scalar_parameter_names(par)];vn=[str(n) for n in mel.get_vector_parameter_names(par)];tn=[str(n) for n in mel.get_texture_parameter_names(par)]
   r['base_has']=dict(MR_VisualWindow='MR_VisualWindow' in vn,MR_ActiveGrid='MR_ActiveGrid' in sn,GTLS_Field='GTLS_Field' in tn,GTLS_Ready='GTLS_Ready' in sn,GTLS_Window='GTLS_Window' in vn);r['base_parameters']=dict(scalar=[n for n in sn if n.startswith(('MR_','GTLS_'))],vector=[n for n in vn if n.startswith(('MR_','GTLS_'))],texture=[n for n in tn if n.startswith(('MR_','GTLS_'))])
  except Exception as err:r['base_has']='unreadable '+repr(err)[:90]
 if r['is_dynamic_instance']:
  def get(fns,n,fmt):
   for fn in fns:
    if hasattr(m,fn):
     try:return fmt(getattr(m,fn)(n))
     except Exception as err:return 'unreadable '+repr(err)[:70]
   return 'no accessor '+'/'.join(fns)
  r['scalars']={n:get(('get_scalar_parameter_value','k2_get_scalar_parameter_value'),n,float) for n in RD1_MID_SCALARS}
  r['vectors']={n:get(('get_vector_parameter_value','k2_get_vector_parameter_value'),n,lambda v:[round(v.r,1),round(v.g,1),round(v.b,1),round(v.a,2)]) for n in RD1_MID_VECTORS}
  r['textures']={n:get(('get_texture_parameter_value','k2_get_texture_parameter_value'),n,lambda t:t.get_name() if t else None) for n in RD1_MID_TEXTURES}
 return r
def rd1_tile_under(world_,x,y):
 for t in u.GameplayStatics.get_all_actors_of_class(world_,u.GTRoadReliefTile):
  o=t.get_actor_location()
  if o.x<=x<o.x+t.span_cm and o.y<=y<o.y+t.span_cm:return t
 return None
def rd1_tile_report(world_,x,y):
 t=rd1_tile_under(world_,x,y)
 if t is None:return dict(tile=None)
 m=t.mesh.get_material(0);r=dict(tile=t.get_actor_label(),origin_cm=[round(t.get_actor_location().x,1),round(t.get_actor_location().y,1)],span_cm=t.span_cm,material=rd1_mid(m) if m else None)
 return r
def rd1_visual_report(world_):
 vis=u.GameplayStatics.get_all_actors_of_class(world_,u.GTMudRunnerVisual)
 if not vis:return dict(visual=None)
 v=vis[0];out=dict(location_cm=[round(v.get_actor_location().x,1),round(v.get_actor_location().y,1)])
 for pn in ('bFollowPlayerGrid','bHideWholeLandscape','half_size_cm'):
  try:out[pn]=v.get_editor_property(pn)
  except Exception as err:out[pn]='unreadable '+repr(err)[:70]
 grid=[c for c in v.get_components_by_class(u.ProceduralMeshComponent) if c.get_name()=='NativeVisualGrid'];gm=grid[0].get_material(0) if grid else None;out['material']=rd1_mid(gm) if gm else None
 return out
RD1_CHAIN_PROPS=('MP_WORLD_POSITION_OFFSET','MP_DISPLACEMENT','MP_OPACITY_MASK','MP_NORMAL','MP_BASE_COLOR','MP_ROUGHNESS')
def rd1_chain(mat,prop,limit=600):
 """Everything upstream of one material property: node counts by class, parameter names, textures, custom nodes (desc, input names, whether the code mentions the field / ready / window), and the GTLS_Field texture parameter upstream or not."""
 mel=u.MaterialEditingLibrary;root=mel.get_material_property_input_node(mat,prop)
 if root is None:return dict(root=None)
 seen={};order=[];queue=[root]
 while queue and len(order)<limit:
  n=queue.pop(0);k=n.get_name()
  if k in seen:continue
  seen[k]=1;order.append(n)
  try:queue+=[x for x in mel.get_inputs_for_material_expression(mat,n) if x]
  except Exception:pass
 classes={};params=set();textures=set();customs=[];sig=[]
 for n in order:
  c=n.get_class().get_name();classes[c]=classes.get(c,0)+1
  try:desc=str(n.get_editor_property('desc'))
  except Exception:desc=''
  pn=''
  try:pn=str(n.get_editor_property('parameter_name'))
  except Exception:pass
  if pn and pn!='None':params.add(pn)
  tx=''
  try:
   t=n.get_editor_property('texture');tx=t.get_name() if t else ''
  except Exception:pass
  if tx:textures.add(tx)
  if isinstance(n,u.MaterialExpressionCustom):
   code=str(n.get_editor_property('code'));customs.append(dict(desc=desc,inputs=[str(i.get_editor_property('input_name')) for i in n.get_editor_property('inputs')],code_chars=len(code),mentions=[w for w in ('Field','Ready','Window','DepthScale') if w in code]))
  sig.append((c,desc,pn,tx))
 return dict(root=dict(cls=root.get_class().get_name(),desc=str(root.get_editor_property('desc'))),nodes=len(order),truncated=len(order)>=limit,classes=dict(sorted(classes.items())),parameters=sorted(params),textures=sorted(textures),custom_nodes=customs,
  field_param_upstream='GTLS_Field' in params,window_param_upstream='GTLS_Window' in params,ready_param_upstream='GTLS_Ready' in params,visual_window_upstream='MR_VisualWindow' in params,signature=sorted(sig))
def rd1_materials():
 """The displacement-relevant chains of the LiDAR clones and the template; clone-only / template-only nodes show what the wrappers added to each chain."""
 out={};named=dict(clone_Detail=BASE+'/M_Detail',clone_Terrain=BASE+'/M_Terrain',template_Detail='/Game/GrandTour/ArtTests/ProceduralGround/M_Detail',template_Terrain='/Game/GrandTour/ArtTests/ProceduralGround/M_Terrain')
 for key,path in named.items():
  m=u.load_asset(path);row=dict(path=path,blend_mode=str(m.get_editor_property('blend_mode')),chains={})
  for pn in RD1_CHAIN_PROPS:
   prop=getattr(u.MaterialProperty,pn,None)
   if prop is None:row['chains'][pn]='no such property in this build';continue
   try:row['chains'][pn]=rd1_chain(m,prop)
   except Exception as err:row['chains'][pn]='unreadable '+repr(err)[:120]
  out[key]=row
 for kind in ('Detail','Terrain'):
  for pn in RD1_CHAIN_PROPS:
   a=out['clone_'+kind]['chains'].get(pn);b=out['template_'+kind]['chains'].get(pn)
   if isinstance(a,dict) and isinstance(b,dict) and a.get('signature') is not None and b.get('signature') is not None:
    sa=[tuple(x) for x in a['signature']];sb=[tuple(x) for x in b['signature']];ca={};cb={}
    for x in sa:ca[x]=ca.get(x,0)+1
    for x in sb:cb[x]=cb.get(x,0)+1
    a['clone_only']=sorted(str(k) for k in ca if ca[k]>cb.get(k,0));a['template_only']=sorted(str(k) for k in cb if cb[k]>ca.get(k,0))
 for row in out.values():
  for v in row['chains'].values():
   if isinstance(v,dict):v.pop('signature',None)
 return out
def perf_grass():return next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTMixedGroundDetails) if a.generate_around_player)
def drive_run(key,capname,spot,ground,restore):
 global drive_on,drive_cmd
 surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0];mesh=car.get_component_by_class(u.SkeletalMeshComponent);mv=car.get_chaos_movement();rep=report['drive']['runs'][key]=dict(spot=dict(spot),capture=str(OUT/(capname+'.png')))
 pts,cum=rd1_path('Riverside access');px,py=spot['pos_cm'][:2];s0,off0=rd1_project(pts,cum,px,py);rep['road']=dict(name='Riverside access',spot_off_road_cm=round(off0,1),start_station_m=round(s0/100,1),length_m=round(cum[-1]/100,1))
 x0,y0=rd1_at(pts,cum,s0);x1,y1=rd1_at(pts,cum,s0+RD1_LOOK_CM);yaw0=math.degrees(math.atan2(y1-y0,x1-x0));z0=ground(x0,y0)
 car.set_actor_location_and_rotation(u.Vector(x0,y0,z0+100),u.Rotator(yaw=yaw0),False,True);mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector());car.reset_driving_inputs();mv.set_throttle_input(0);mv.set_brake_input(0);mv.set_handbrake_input(True)
 yield from settle(8)
 sx,sy=rd1_at(pts,cum,s0+1500);tx_,ty_=rd1_at(pts,cum,s0+1600);yaw_s=math.degrees(math.atan2(ty_-sy,tx_-sx))
 before=dict(station_15m=rd1_across(surface,sx,sy,yaw_s),transect_15m=rd1_transect(surface,sx,sy,yaw_s),surface_report=surface.get_surface_report(),at_start=surface.sample_surface(u.Vector2D(x0,y0)))
 q=before.pop('at_start');rep['physics_at_start']=dict(clay_weight=q.clay_weight,friction_scale=q.friction_scale,cohesion=q.cohesion,wetness=q.wetness,softness=q.softness,native_friction=q.native_friction,native_linear_resistance=q.native_linear_resistance,native_push_resistance=q.native_push_resistance,sinkage_cap_cm=q.sinkage_cap_cm,surface_tag=str(q.surface_tag),soil_shear=bool(q.get_editor_property('bSoilShearResponse')),granular=bool(q.get_editor_property('bGranularResponse')),native_substance=bool(q.get_editor_property('bNativeSubstanceResponse')))
 rep['before']=before;rep['tile_before']=rd1_tile_report(world,x0,y0);rep['visual_before']=rd1_visual_report(world);save()
 car.get_drivetrain().set_low_range(True);car.get_drivetrain().set_diff_lock(True)
 if PERF:
  u.SystemLibrary.execute_console_command(world,'gt.Perf.LogSpikes 1',pc);u.SystemLibrary.execute_console_command(world,'gt.Perf.Reset',pc);yield from settle(10);u.SystemLibrary.execute_console_command(world,'gt.Perf.Dump idle_'+key,pc);u.SystemLibrary.execute_console_command(world,'gt.Perf.Reset',pc);rep['perf_grass_idle']=perf_grass().grass_report()
 now=u.GameplayStatics.get_time_seconds(world);drive_cmd=dict(pts=pts,cum=cum,s=s0,max_off=0.,t0=now,t_last=now-1,trace=[]);mv.set_handbrake_input(False);mv.set_brake_input(0);drive_on=True;t_end=None;reached=False
 while True:
  p=car.get_actor_location();trav=math.hypot(p.x-x0,p.y-y0);el=u.GameplayStatics.get_time_seconds(world)-drive_cmd['t0']
  if trav>=RD1_RUN_CM:reached=True;t_end=el;break
  if el>RD1_MAX_S:t_end=el;break
  yield .1
 drive_on=False
 if PERF:u.SystemLibrary.execute_console_command(world,'gt.Perf.Dump drive_'+key,pc)
 mv.set_throttle_input(0);mv.set_brake_input(0);mv.set_handbrake_input(True);car.set_raw_steer(0);yield from settle(2.5)   # handbrake, not the brake pedal: a held pedal at rest engages reverse and the first run backed 15 m down the road
 for _ in range(10):
  if car.get_velocity().length()<15.:break
  yield from settle(.5)
 yield from settle(1.5)
 if PERF:rep['perf_grass_after_drive']=perf_grass().grass_report();rep['perf_stream_consistency']=perf_grass().streaming_consistency(True)
 cp=car.get_actor_location();cyaw=car.get_actor_rotation().yaw;fx,fy=math.cos(math.radians(cyaw)),math.sin(math.radians(cyaw));tr=drive_cmd['trace']
 tuning=car.get_component_by_class(u.GTVehicleTuningComponent).get_current()
 s_max=max([r['s'] for r in tr],default=s0);rep['drive']=dict(reached_25m=reached,seconds=round(t_end,2),travelled_cm=round(math.hypot(cp.x-x0,cp.y-y0),1),road_cm_to_last_trace=round(s_max-s0,1),reversed_cm_after_stop=round(max(0.,s_max-rd1_project(pts,cum,cp.x,cp.y,max(0.,s_max-6000.),s_max+3000.)[0]),1),peak_speed_mps=max([r['speed_mps'] for r in tr],default=0.),mean_speed_mps=round((s_max-s0)*.01/max(t_end,.01),3),max_off_road_cm=round(drive_cmd['max_off'],1),throttle=RD1_THROTTLE,low_range=True,diff_lock=True,
  end_pose_cm=[round(cp.x,1),round(cp.y,1),round(cp.z,1)],end_yaw=round(cyaw,1),wheel_sink_cm_at_stop=[round(float(w.sinkage_cm),2) for w in tuning.wheels],trace_rows=len(tr),trace_every_4th=tr[::4][:20])
 # the trail 3 m and 10 m behind the car: the recorded pose when the car was that far back along the road (the trace), five samples across it and the 5 cm transect; and the same five at the path stations 15 m from the start (the 'before' points) so the two are comparable
 after=dict(surface_report=surface.get_surface_report());s_end=tr[-1]['s'] if tr else drive_cmd['s']
 for lab,back in (('behind_3m',300.),('behind_10m',1000.)):
  row=min(tr,key=lambda r:abs(r['s']-(s_end-back))) if tr else None
  if row:after[lab]=dict(trace_pose=row,across=rd1_across(surface,row['x'],row['y'],row['yaw']),transect=rd1_transect(surface,row['x'],row['y'],row['yaw']))
 after['path_station_15m']=dict(across=rd1_across(surface,sx,sy,yaw_s),transect=rd1_transect(surface,sx,sy,yaw_s))
 rep['after']=after;rep['tile_after']=rd1_tile_report(world,cp.x,cp.y);rep['visual_after']=rd1_visual_report(world)
 va=rep['visual_after'].get('material',{}).get('vectors',{}).get('MR_VisualWindow') if isinstance(rep['visual_after'].get('material'),dict) else None
 if isinstance(va,list):rep['car_inside_visual_window']=max(abs(cp.x-va[0]),abs(cp.y-va[1]))<va[2]-va[3]
 b=nums(before['surface_report']);a_=nums(after['surface_report']);rep['field']={k:dict(before=b.get(k),after=a_.get(k)) for k in ('excavated_cm3','deposited_cm3','push_cells','native_cells','decay_cells','tiles')};save()
 aim_x,aim_y=cp.x-fx*300,cp.y-fy*300
 yield from capture(capname,(cp.x-fx*800,cp.y-fy*800,cp.z+400),(aim_x,aim_y,ground(aim_x,aim_y)))
 report['drive']['runs'][key]['capture_camera']=dict(camera_cm=[round(cp.x-fx*800,1),round(cp.y-fy*800,1),round(cp.z+400,1)],aim_cm=[round(aim_x,1),round(aim_y,1)],note='4 m up, 8 m behind the car, aimed at the track 3 m behind it')
 save()
 if key=='bush' and DRIVE_EVIDENCE_HIDE_TILES:
  # evidence only: the same view with every relief tile mesh hidden, so what is left is the visual grid and the landscape; ruts that appear only now are being covered by the tiles
  tl_=u.GameplayStatics.get_all_actors_of_class(world,u.GTRoadReliefTile)
  for t_ in tl_:t_.mesh.set_visibility(False)
  yield from capture(capname+'_tiles_hidden',(cp.x-fx*800,cp.y-fy*800,cp.z+400),(aim_x,aim_y,ground(aim_x,aim_y)))
  for t_ in tl_:t_.mesh.set_visibility(True)
  report['drive']['runs'][key]['tiles_hidden_capture']=str(OUT/(capname+'_tiles_hidden.png'));save()
def perf_paddock(ground):
 """PF1: 40 m across the NE paddock (paddock 1) at the Drive step's throttle, from 12 m beside the trough toward the nearest fence run that leaves the whole 40 m clear of other farm hardware; straight-line pursuit of a far point on that ray. gt.Perf.Dump 'paddock' at the end."""
 global drive_on,drive_cmd
 hwj=json.loads((OUT/'hardware.json').read_text());trough=next(i for i in hwj if i['mesh']=='SM_NZ_Trough' and i['tag']=='paddock 1 trough');tx,ty=trough['p'][0],trough['p'][1]
 fences=[i for i in hwj if i['tag']=='paddock 1 fence'];others=[i for i in hwj if i['tag']!='paddock 1 fence']
 def along(i,dx,dy):
  rx,ry=i['p'][0]-tx,i['p'][1]-ty;return rx*dx+ry*dy,abs(-rx*dy+ry*dx)
 best=None
 for a in range(0,360,5):
  dx,dy=math.cos(math.radians(a)),math.sin(math.radians(a));fd=min([s for i in fences for s,d in [along(i,dx,dy)] if s>500 and d<300],default=None)
  if fd is None or fd<PERF_PADDOCK_START_CM+PERF_PADDOCK_RUN_CM+500:continue
  if any(PERF_PADDOCK_START_CM-600<s<fd and d<500 for i in others for s,d in [along(i,dx,dy)]) or any(math.hypot(i['p'][0]-tx-dx*PERF_PADDOCK_START_CM,i['p'][1]-ty-dy*PERF_PADDOCK_START_CM)<600 for i in others):continue
  if best is None or fd<best[1]:best=(a,fd)
 assert best,'no clear 40 m ray from the paddock 1 trough to its fence'
 a,fd=best;dx,dy=math.cos(math.radians(a)),math.sin(math.radians(a));sx,sy=tx+dx*PERF_PADDOCK_START_CM,ty+dy*PERF_PADDOCK_START_CM;L=PERF_PADDOCK_RUN_CM+1500;pts=[[sx,sy],[sx+dx*L,sy+dy*L]];cum=[0.,L]
 surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0];mesh=car.get_component_by_class(u.SkeletalMeshComponent);mv=car.get_chaos_movement()
 rep=report.setdefault('perf',{})['paddock']=dict(trough_cm=[tx,ty],heading_deg=a,fence_ray_cm=fd,start_cm=[sx,sy],run_cm=PERF_PADDOCK_RUN_CM,surface_at_start=rd1_sample(surface,sx,sy))
 car.set_actor_location_and_rotation(u.Vector(sx,sy,ground(sx,sy)+100),u.Rotator(yaw=float(a)),False,True);mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector());car.reset_driving_inputs();mv.set_throttle_input(0);mv.set_brake_input(0);mv.set_handbrake_input(True)
 yield from settle(10)
 car.get_drivetrain().set_low_range(True);car.get_drivetrain().set_diff_lock(True)
 u.SystemLibrary.execute_console_command(world,'gt.Perf.LogSpikes 1',pc);u.SystemLibrary.execute_console_command(world,'gt.Perf.Reset',pc)
 now=u.GameplayStatics.get_time_seconds(world);drive_cmd=dict(pts=pts,cum=cum,s=0.,max_off=0.,t0=now,t_last=now-1,trace=[]);mv.set_handbrake_input(False);mv.set_brake_input(0);drive_on=True;reached=False;t_end=None
 while True:
  p=car.get_actor_location();trav=math.hypot(p.x-sx,p.y-sy);el=u.GameplayStatics.get_time_seconds(world)-drive_cmd['t0']
  if trav>=PERF_PADDOCK_RUN_CM:reached=True;t_end=el;break
  if el>RD1_MAX_S+15:t_end=el;break
  yield .1
 drive_on=False;u.SystemLibrary.execute_console_command(world,'gt.Perf.Dump paddock',pc)
 mv.set_throttle_input(0);mv.set_brake_input(0);mv.set_handbrake_input(True);car.set_raw_steer(0);tr=drive_cmd['trace']
 rep['drive']=dict(reached=reached,seconds=round(t_end,2),travelled_cm=round(math.hypot(p.x-sx,p.y-sy),1),max_off_line_cm=round(drive_cmd['max_off'],1),peak_speed_mps=max([r['speed_mps'] for r in tr],default=0.),mean_speed_mps=round(PERF_PADDOCK_RUN_CM*.01/max(t_end,.01),3),trace_every_4th=tr[::4][:20]);save()
 yield from settle(2.5)
 rep['grass_after_drive']=perf_grass().grass_report();rep['stream_consistency']=perf_grass().streaming_consistency(True)
def drive_step(ground,restore):
 """Both drives, then the car goes back to where it was (the later captures use its position)."""
 report['drive']=dict(materials=rd1_materials(),runs={'open':{},'bush':{}},note='RD1: fixed throttle %.2f for %d m of road by pure pursuit; see the file header of the RD1 block'%(RD1_THROTTLE,RD1_RUN_CM/100));save()
 yield from drive_run('open','Ruts_open',data['captures']['Clay_track_open'],ground,restore)
 yield from drive_run('bush','Ruts_bush',data['captures']['Bush_track'],ground,restore)
 mesh=car.get_component_by_class(u.SkeletalMeshComponent);mv=car.get_chaos_movement();loc,rot=restore
 car.set_actor_location_and_rotation(loc,rot,False,True);mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector());car.reset_driving_inputs();mv.set_throttle_input(0);mv.set_brake_input(0);mv.set_handbrake_input(True);yield from settle(8)
 # RD1 checks: the tiles take M_Terrain (the material the tile code is written for) with its MR_ActiveGrid parameter set to 1 and the visual window bound, both drives covered 25 m, and the bush climb shows real ruts in the soil field. The open gravel stretch is recorded, not asserted
 # (RD1 found its soil layer 0.8-1.7 cm at mud 4, under the native mud update's gate: paint depth / 3 > .75, i.e. 2.25 cm, so the field wrote nothing there). RD1b raised the gravel mud depth (private 9, public 5); report['drive']['summary'] holds the numbers both stretches now give and open_in_target (1.5 to 3 cm after one pass, a target, not an assert).
 def _tr(k,lab):return runs_[k]['after'].get(lab,{}).get('transect',{})
 runs_=report['drive']['runs'];report['drive']['summary']={k:dict(lowest_surface_delta_cm_behind_3m=_tr(k,'behind_3m').get('lowest_surface_delta_cm'),lowest_surface_delta_cm_behind_10m=_tr(k,'behind_10m').get('lowest_surface_delta_cm'),max_compression_cm_behind_3m=_tr(k,'behind_3m').get('max_compression_cm'),max_mud_above_base_cm_behind_3m=_tr(k,'behind_3m').get('max_mud_above_base_cm'),excavated_cm3=runs_[k]['field']['excavated_cm3'],excavated_delta_cm3=round((runs_[k]['field']['excavated_cm3']['after'] or 0.)-(runs_[k]['field']['excavated_cm3']['before'] or 0.),1),push_cells_delta=(runs_[k]['field']['push_cells']['after'] or 0.)-(runs_[k]['field']['push_cells']['before'] or 0.)) for k in ('open','bush')}
 _o=report['drive']['summary']['open']['lowest_surface_delta_cm_behind_3m'];report['drive']['summary']['open_in_target']=bool(_o is not None and 1.5<=-_o<=3.);report['drive']['summary']['open_target_cm']=[1.5,3.];save()
 runs=report['drive']['runs'];ck=dict(
  tiles_use_terrain=all(runs[k]['tile_before']['material']['parent']=='M_Terrain' for k in runs),
  tile_material_has_active_grid_and_window=all(runs[k]['tile_before']['material']['base_has']['MR_ActiveGrid'] is True and runs[k]['tile_before']['material']['base_has']['MR_VisualWindow'] is True for k in runs),
  tile_active_grid_is_1=all(runs[k]['tile_after']['material']['scalars']['MR_ActiveGrid']==1.0 for k in runs),
  tile_window_equals_visual_window=all(runs[k]['tile_after']['material']['vectors']['MR_VisualWindow']==runs[k]['visual_after']['material']['vectors']['MR_VisualWindow'] for k in runs),
  drove_25m=all(runs[k]['drive']['reached_25m'] and runs[k]['drive']['road_cm_to_last_trace']>=2000. and runs[k]['drive']['reversed_cm_after_stop']<200. for k in runs),
  bush_field_has_ruts=runs['bush']['after']['behind_3m']['transect']['lowest_surface_delta_cm']<=-1.5 and runs['bush']['after']['behind_3m']['transect']['max_compression_cm']>=1.)
 report['drive']['checks']=ck;save();assert all(ck.values()),ck
 report['driving_tested']=True;save()

def run():
 global world,pc,car,measure_frames
 les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(BASE+'/L_LidarStudy')
 install=json.loads((OUT/'install.json').read_text());assert install['ok'] and install['terrain_source_unchanged']
 for path,digest in install['protected_before'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
 actors=u.get_editor_subsystem(u.EditorActorSubsystem);refs=actors.get_all_level_actors();author=next(a for a in refs if isinstance(a,u.GTProceduralGround))
 assert author.relief_tiles and author.allow_large_sparse_road_bounds
 report['authoring']=dict(data.get('authoring',{}))
 report['authoring']['height_readbacks']=[]
 for x,y,z in data.get('authoring',{}).get('height_probes_cm',[]):
  got=author.base_height_at(u.Vector2D(x,y));assert abs(got-z)<1,('authored river bed height',x,y,z,got)
  report['authoring']['height_readbacks'].append(dict(x=x,y=y,expected_cm=z,actual_cm=got))
 if DRIVE_ONLY:
  # RD1 development mode (GT_CHECK_DRIVE_ONLY=1): nothing but the Drive step (about 4 minutes). The readbacks and captures above and below are skipped; the heights come from the built relief tiles exactly as the corridor check reads them.
  les.editor_set_viewport_realtime(False);assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900);deadline=time.monotonic()+180
  while not world:
   world=u.EditorLevelLibrary.get_game_world();assert time.monotonic()<deadline;yield .5
  pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car();assert isinstance(car,u.GTCarPawn);pc.possess(car)
  car.disable_input(pc);car.reset_driving_inputs();mv_=car.get_chaos_movement();mv_.set_brake_input(0);mv_.set_throttle_input(0);mv_.set_handbrake_input(True)
  for cmd in ['DisableAllScreenMessages','r.MotionBlurQuality 0','t.MaxFPS 60','t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0','showhud']+(['gt.Perf.LogSpikes 1'] if PERF else []):u.SystemLibrary.execute_console_command(world,cmd,pc)
  tl=[(t.get_actor_location(),t.span_cm,t) for t in author.relief_tiles.values() if t];base_h=author.base_height_at;cell_=max([sp for _,sp,_ in tl]+[1.]);gd={}
  for o,sp,t in tl:
   for i in range(math.floor(o.x/cell_),math.floor((o.x+sp)/cell_)+1):
    for j in range(math.floor(o.y/cell_),math.floor((o.y+sp)/cell_)+1):gd.setdefault((i,j),[]).append((o.x,o.y,sp,t))
  def ground_(gx,gy):
   xy=u.Vector2D(gx,gy)
   for ox,oy,sp,t in gd.get((math.floor(gx/cell_),math.floor(gy/cell_)),()):
    if ox<=gx<ox+sp and oy<=gy<oy+sp:return t.height_at(xy)
   return base_h(xy)
  yield from drive_step(ground_,(car.get_actor_location(),car.get_actor_rotation()))
  if PERF:
   yield from perf_paddock(ground_);u.SystemLibrary.execute_console_command(world,'gt.Perf.LogSpikes 0',pc)
  report['ok']=True;report['drive_only']=True;save();yield from finish();return
 counts={}
 for a in refs:
  if a.get_actor_label() in ['LidarStudy_Forest','LidarStudy_Understory','LidarStudy_Farm']:
   comps=[c for c in a.get_components_by_class(u.InstancedStaticMeshComponent) if c.static_mesh];counts[a.get_actor_label()]={m:sum(c.get_instance_count() for c in comps if c.static_mesh.get_name()==m) for m in sorted({c.static_mesh.get_name() for c in comps})}
 report['instances']=counts;report['relief_triangles']=author.relief_triangles;report['road_pool_wet_samples']=author.road_pool_wet_samples
 # LP3: the canopy is four kit species (SM_Canopy_k <- prepare tree_kinds), the understory a list of kit meshes (prepare understory_by_mesh); sums across components
 forest_counts=counts['LidarStudy_Forest'];canopy={k:forest_counts.get('SM_Canopy_'+str(i),0) for i,k in enumerate(data['tree_kinds'])}
 expected_trees=dict(data['tree_kinds']);expected_under=dict(data['understory_by_mesh'])
 if any(a.get_actor_label()=='LidarStudy_Homestead_GarageDoor' for a in refs):
  import lidar_homestead as HS
  names=list(expected_trees)
  for tree in json.loads((OUT/'trees.json').read_text()):
   if HS.clears_vegetation(*tree[:2]):expected_trees[names[int(tree[3])]]-=1
  for plant in json.loads((OUT/'understory.json').read_text()):
   if HS.clears_vegetation(*plant['p'][:2]):expected_under[plant['kind']]-=1
 report['homestead_clearance_counts']=dict(canopy=data['trees']-sum(expected_trees.values()),understory=data['understory']-sum(expected_under.values()))
 if (OUT/'rocky-bank.json').exists():
  rs6=json.loads((ROOT/'Saved/LidarAuthoringQA/RS6/install.json').read_text());assert rs6['ok']
  expected_inventory=rs6['owner_inventory']
  expected_trees={k:expected_inventory['LidarStudy_Forest'].get('SM_Canopy_'+str(i),0) for i,k in enumerate(data['tree_kinds'])}
  expected_under=expected_inventory['LidarStudy_Understory'];report['vegetation_checkpoint']='RS6 rocky bank'
 assert canopy==expected_trees,(canopy,expected_trees)
 assert forest_counts.get('Cylinder',0)==sum(expected_trees.values()),('trunk cylinders',forest_counts.get('Cylinder'))
 under_counts=counts['LidarStudy_Understory'];assert under_counts==expected_under,{k:(under_counts.get(k),expected_under.get(k)) for k in set(under_counts)|set(expected_under) if under_counts.get(k)!=expected_under.get(k)}
 # LP4: the farm hardware, one ISM component per mesh, counts exactly prepare's hardware.json (hardware_by_mesh); every component collides (QUERY_AND_PHYSICS) through the mesh's own hulls
 farm=counts['LidarStudy_Farm'];hw_expected=data['hardware_by_mesh'];assert farm==hw_expected,{k:(farm.get(k),hw_expected.get(k)) for k in set(farm)|set(hw_expected) if farm.get(k)!=hw_expected.get(k)}
 assert sum(farm.values())==data['hardware']['total'] and json.loads((OUT/'hardware.json').read_text()).__len__()==data['hardware']['total']
 farm_actor=next(a for a in refs if a.get_actor_label()=='LidarStudy_Farm');farm_rows={}
 def cullof(c):
  try:return [float(c.get_editor_property('instance_start_cull_distance')),float(c.get_editor_property('instance_end_cull_distance'))]
  except Exception as err:return 'unreadable: '+repr(err)
 for c in farm_actor.get_components_by_class(u.InstancedStaticMeshComponent):
  if not c.static_mesh:continue
  hulls=len(c.static_mesh.get_editor_property('body_setup').get_editor_property('agg_geom').get_editor_property('convex_elems'));farm_rows[c.static_mesh.get_name()]=dict(instances=c.get_instance_count(),collision=str(c.get_collision_enabled()),hulls=hulls,cull_cm=cullof(c))
  assert hulls>0 and 'QUERY_AND_PHYSICS' in str(c.get_collision_enabled()),(c.static_mesh.get_name(),farm_rows[c.static_mesh.get_name()])
 assert len(farm_rows)==len(hw_expected),(sorted(farm_rows),sorted(hw_expected))
 report['farm']=dict(by_mesh=farm,total=sum(farm.values()),components=farm_rows,expected_total=data['hardware']['total'],culverts=len(data['hardware']['info']['culverts']),culvert_threshold_cells=data['hardware']['info']['culvert_threshold_cells'],paddock_areas_m2=[p['area_m2'] for p in data['paddocks']['polygons']])
 report['lp3_counts']=dict(canopy=canopy,trunk_cylinders=forest_counts.get('Cylinder',0),understory_by_mesh=under_counts,understory_total=sum(under_counts.values()),regimes=data['understory_regimes'])
 # LP3c readback from the saved level: tint instances sit on the kit's Foliage slots (and the spar's Bark slot), bark elsewhere is the kit's own material,
 # and both LiDAR ground colour programs carry the peat block exactly once.
 mel=u.MaterialEditingLibrary;lp3c=dict(components={},ground={})
 for a in refs:
  if a.get_actor_label() not in ['LidarStudy_Forest','LidarStudy_Understory']:continue
  for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
   if not c.static_mesh:continue
   nm=c.static_mesh.get_name();src=[(s.get_editor_property('material_interface').get_name() if s.get_editor_property('material_interface') else None) for s in c.static_mesh.get_editor_property('static_materials')]
   if nm=='Cylinder':continue
   now=[(c.get_material(i).get_name() if c.get_material(i) else None) for i in range(len(src))]
   spar=nm=='SM_Canopy_3';fern=nm.replace('SM_NZ_','').startswith(('CrownFern','TwigLitter','LeafLitter','RootTangle','MossHummock','Log_','Stump','TreeFern','Kiokio'))
   canopy_leaf=nm in ('SM_Canopy_0','SM_Canopy_1','SM_Canopy_2')   # LP3e: the three beech kinds wear MI_NZ_Foliage_Canopy on the Foliage slot; the spar keeps its bark tint only
   want=['MI_NZ_Bark_Spar' if (spar and n=='M_NZ_Bark') else 'MI_NZ_Foliage_Bush' if (fern and n=='M_NZ_Foliage') else 'MI_NZ_Foliage_Canopy' if (canopy_leaf and n=='M_NZ_Foliage') else n for n in src]
   lp3c['components'][nm]=dict(source=src,applied=now,expected=want,ok=now==want);assert now==want,('LP3c tint slots',nm,src,now,want)
 for n in ['M_Terrain','M_Detail']:
  m=u.load_asset('/Game/GrandTour/ArtTests/LidarStudy/'+n);hits=sum('LP3c forest-floor peat' in str(e.get_editor_property('code')) for e in mel.get_material_expressions(m) if isinstance(e,u.MaterialExpressionCustom))
  lp3c['ground'][n]=hits;assert hits==1,('LP3c peat block',n,hits)
 report['lp3c']=lp3c
 # LP3d readback from the saved level: the pasture block sits once in each LiDAR ground colour program, the cover tint carries the (.70,1.0,.55) high-grass multiplier,
 # the near grass material the GrassBaseTint (.48,.88,.42), the distance cover the Diffuse multiply (.60,.95,.55), and the grass actor's spacing is what Polish set.
 lp3d=dict(ground={},cover_tint={},grass={})
 for n in ['M_Terrain','M_Detail']:
  m=u.load_asset('/Game/GrandTour/ArtTests/LidarStudy/'+n);cs=[e for e in mel.get_material_expressions(m) if isinstance(e,u.MaterialExpressionCustom)]
  hits=sum('LP3d grazed pasture' in str(e.get_editor_property('code')) for e in cs);pas=[str(e.get_editor_property('code')) for e in cs if 'LP3d grazed pasture' in str(e.get_editor_property('code'))]
  lp3d.setdefault('program_pasture_noise_removed',{})[n]=bool(pas and not any(t in pas[0] for t in ('pasCol','pasLum','pasMown','pasV=','float3(.11,.20,.045)','materialXY/12.+157.')))   # GP2c: the colour program returns the ground colour and the peat only
  assert pas and lp3d['program_pasture_noise_removed'][n] and pas[0].rstrip().endswith('return lerp(pow(max(rich,0),2.2),peatCol,peatMask);'),('GP2c: pasture noise still in the colour program',n);tint=[str(e.get_editor_property('code')) for e in cs if str(e.get_editor_property('desc'))=='LidarCoverTint']
  lp3d['ground'][n]=hits;assert hits==1,('LP3d pasture block',n,hits)
  lp3d['cover_tint'][n]=tint[0].split('return ')[-1] if tint else None;assert len(tint)==1 and 'float3(0.85,1.0,0.7)' in tint[0],('LP3e cover tint',n,tint)
 g_actor=next(a for a in refs if isinstance(a,u.GTMixedGroundDetails) and a.generate_around_player)
 # GP2: grass_material is now the clump material, card_grass_material keeps M_LidarGrass (the cards fallback), rank_material is M_LidarRank; the LP3d/LP3e card readbacks below use the card material.
 for prop,mname in [('card_grass_material','M_LidarGrass'),('grass_material','M_LidarClump'),('rank_material','M_LidarRank'),('distant_grass_material','M_LidarGrassDistance')]:
  gm=g_actor.get_editor_property(prop);assert gm and gm.get_name()==mname,(prop,gm)
  tints=[[round(e.get_editor_property('default_value').r,3),round(e.get_editor_property('default_value').g,3),round(e.get_editor_property('default_value').b,3)] for e in mel.get_material_expressions(gm) if isinstance(e,u.MaterialExpressionVectorParameter) and str(e.get_editor_property('parameter_name'))=='GrassBaseTint']
  mult=[e for e in mel.get_material_expressions(gm) if isinstance(e,u.MaterialExpressionCustom) and 'Diffuse*float3(0.62,0.88,0.46)' in str(e.get_editor_property('code'))]
  lp3d['grass'][mname]=dict(base_tint=tints,diffuse_multiply_nodes=len(mult))
 assert lp3d['grass']['M_LidarGrass']['base_tint']==[[.52,.82,.36]],lp3d['grass'];assert lp3d['grass']['M_LidarGrassDistance']['diffuse_multiply_nodes']==1,lp3d['grass']
 lp3d['grass']['spacing_cm']=float(g_actor.get_editor_property('grass_spacing_cm'));assert lp3d['grass']['spacing_cm']==45.   # GP2: the card fallback's spacing (LP3e was 35)
 report['lp3d']=lp3d
 # LP3e readback from the saved level: spacing 35 cm (the C++ floor is 30), BladeScale .8, RankBandScale 1.4 on the grass actor; the near grass material's BaseColor is the LP3eStraw node, which takes the old colour node
 # and a PerInstanceCustomData with index 3; MI_NZ_Foliage_Canopy (parent M_NZ_Foliage, Tint .55,.62,.50) sits on the Foliage slot of the three beech components and nowhere else; the far cards carry the same tint.
 lp3e=dict(grass=dict(spacing_cm=lp3d['grass']['spacing_cm'],blade_scale=float(g_actor.get_editor_property('blade_scale')),rank_band_scale=float(g_actor.get_editor_property('rank_band_scale'))),straw={},canopy={})
 assert abs(lp3e['grass']['blade_scale']-.8)<1e-4 and abs(lp3e['grass']['rank_band_scale']-1.4)<1e-4,lp3e['grass']
 gm=g_actor.get_editor_property('card_grass_material');base=mel.get_material_property_input_node(gm,u.MaterialProperty.MP_BASE_COLOR)
 idx3=[e for e in mel.get_inputs_for_material_expression(gm,base) if isinstance(e,u.MaterialExpressionPerInstanceCustomData) and int(e.get_editor_property('data_index'))==3] if base is not None and isinstance(base,u.MaterialExpressionCustom) else []
 lp3e['straw']=dict(base_colour_node=str(base.get_editor_property('desc')) if base is not None else None,inputs=[str(i.get_editor_property('input_name')) for i in base.get_editor_property('inputs')] if base is not None and isinstance(base,u.MaterialExpressionCustom) else None,custom_data_3_nodes=len(idx3),multiplier_in_code='float3(1.25,1.05,0.55)' in str(base.get_editor_property('code')) if base is not None and isinstance(base,u.MaterialExpressionCustom) else False)
 assert lp3e['straw']['base_colour_node']=='LP3eStraw' and lp3e['straw']['inputs']==['Base','Straw'] and lp3e['straw']['custom_data_3_nodes']==1 and lp3e['straw']['multiplier_in_code'],lp3e['straw']
 mi=u.load_asset('/Game/GrandTour/ArtTests/LidarStudy/MI_NZ_Foliage_Canopy');assert mi and mi.get_editor_property('parent').get_name()=='M_NZ_Foliage',mi
 tv=mel.get_material_instance_vector_parameter_value(mi,'Tint');lp3e['canopy']=dict(instance=mi.get_name(),parent=mi.get_editor_property('parent').get_name(),tint=[round(tv.r,3),round(tv.g,3),round(tv.b,3)],components={})
 assert lp3e['canopy']['tint']==[.55,.62,.5],lp3e['canopy']
 for a in refs:
  if a.get_actor_label()!='LidarStudy_Forest':continue
  for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
   if not c.static_mesh or not c.static_mesh.get_name().startswith('SM_Canopy_'):continue
   nm=c.static_mesh.get_name();mats=[(c.get_material(i).get_name() if c.get_material(i) else None) for i in range(len(c.static_mesh.get_editor_property('static_materials')))];lp3e['canopy']['components'][nm]=mats
   if nm in ('SM_Canopy_0','SM_Canopy_1','SM_Canopy_2'):assert mats.count('MI_NZ_Foliage_Canopy')==1,(nm,mats)
   else:assert 'MI_NZ_Foliage_Canopy' not in mats,(nm,mats)
 for k in (0,1,2,3):
  fm=u.load_asset('/Game/GrandTour/ArtTests/LidarStudy/CanopyKit/M_FirFar_'+str(k));bc=mel.get_material_property_input_node(fm,u.MaterialProperty.MP_BASE_COLOR);lp3e['canopy'].setdefault('far_cards',{})[str(k)]=str(bc.get_editor_property('desc')) if bc is not None else None
  assert lp3e['canopy']['far_cards'][str(k)]=='LP3cTint',('far card tint',k,lp3e['canopy']['far_cards'])
 report['lp3e']=lp3e
 # GP2 readback from the saved level: the clump meshes (PastureClump_L, RankClump_A), ClumpSpacingCm 40 (GP2d: the C++ floor), the clump and rank materials (tints .88,.96,.60 / 1,1,1) take the mesh vertex colour in their colour node (no texture sample feeds it, no 2.2 power),
 # the opacity mask has no texture alpha, the LP3eStraw wrapper is still the base colour, and both ground colour programs carry the 15% desaturation.
 # GP4b: the pasture is the three patch meshes (one component each), spacing 55 cm, scale .8 to 1.25, streaming radius 40 m, cull 30 to 38 m, LOD1 10 m, LOD2 22 m (the meshes' LOD2 screen size is set by Install so the two give that ratio).
 sme=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);pasture_names=[g_actor.get_editor_property(n).get_name() for n in ('pasture_clump_mesh','pasture_clump_mesh_b','pasture_clump_mesh_c')]
 gp2=dict(meshes=dict(pasture=pasture_names,rank=g_actor.get_editor_property('rank_clump_mesh').get_name()),clump_spacing_cm=float(g_actor.get_editor_property('clump_spacing_cm')),card_spacing_cm=lp3d['grass']['spacing_cm'],lod1_distance_cm=float(g_actor.get_editor_property('clump_lod1_distance_cm')),
  lod2_distance_cm=float(g_actor.get_editor_property('clump_lod2_distance_cm')),clump_scale=[float(g_actor.get_editor_property('clump_scale_min')),float(g_actor.get_editor_property('clump_scale_max'))],stream_radius_cm=float(g_actor.get_editor_property('clump_stream_radius_cm')),
  cull_cm=[float(g_actor.get_editor_property('grass_cull_start_cm')),float(g_actor.get_editor_property('grass_cull_end_cm'))],patch_lod_screen_sizes={n:[round(float(v),4) for v in sme.get_lod_screen_sizes(g_actor.get_editor_property(p_))] for n,p_ in zip(pasture_names,('pasture_clump_mesh','pasture_clump_mesh_b','pasture_clump_mesh_c'))},materials={},ground_desaturation={})
 assert gp2['meshes']==dict(pasture=['SM_NZ_GrassPatch_A','SM_NZ_GrassPatch_B','SM_NZ_GrassPatch_C'],rank='SM_NZ_RankClump_A') and gp2['clump_spacing_cm']==55. and gp2['lod1_distance_cm']==1000. and gp2['lod2_distance_cm']==2200. and all(abs(a-b)<1e-4 for a,b in zip(gp2['clump_scale'],[.8,1.25])) and gp2['stream_radius_cm']==4000. and gp2['cull_cm']==[3000.,3800.],gp2
 assert all(len(v)>=3 and abs(v[1]*1000./v[2]-2200.)<8. for v in gp2['patch_lod_screen_sizes'].values()),('GP4b patch LOD screen sizes do not give LOD1 10 m / LOD2 22 m',gp2['patch_lod_screen_sizes'])
 for prop,mname,want in [('grass_material','M_LidarClump',[.88,.96,.6]),('rank_material','M_LidarRank',[1.,1.,1.])]:
  gm=g_actor.get_editor_property(prop);ex=list(mel.get_material_expressions(gm));vcs=[e for e in ex if isinstance(e,u.MaterialExpressionVertexColor)]
  col=[e for e in ex if isinstance(e,u.MaterialExpressionCustom) and [str(i.get_editor_property('input_name')) for i in e.get_editor_property('inputs')]==['Diffuse','Tint'] and all(x is not None for x in mel.get_inputs_for_material_expression(gm,e))]   # the live colour node (the card material also carries an orphaned unwired copy)
  fed=bool(vcs and col and any(x.get_name()==vcs[0].get_name() for x in mel.get_inputs_for_material_expression(gm,col[0]) if x));mask=mel.get_material_property_input_node(gm,u.MaterialProperty.MP_OPACITY_MASK)
  mask_in=[x for x in mel.get_inputs_for_material_expression(gm,mask)] if mask is not None else []
  tints=[[round(e.get_editor_property('default_value').r,3),round(e.get_editor_property('default_value').g,3),round(e.get_editor_property('default_value').b,3)] for e in ex if isinstance(e,u.MaterialExpressionVectorParameter) and str(e.get_editor_property('parameter_name'))=='GrassBaseTint']
  base=mel.get_material_property_input_node(gm,u.MaterialProperty.MP_BASE_COLOR)
  row=dict(base_tint=tints,vertex_colour_nodes=len(vcs),colour_node_fed_by_vertex_colour=fed,colour_code=str(col[0].get_editor_property('code')).split(chr(10))[-1] if col else None,opacity_mask_inputs=[type(x).__name__ if x else None for x in mask_in],texture_samples=sum(isinstance(e,u.MaterialExpressionTextureSample) and any(x and x.get_name()==e.get_name() for x in mel.get_inputs_for_material_expression(gm,col[0])) for e in ex) if col else None,base_colour_node=str(base.get_editor_property('desc')) if base is not None else None)
  gp2['materials'][mname]=row;assert row['base_tint']==[want] and len(vcs)==1 and fed and row['colour_code']=='return max(Diffuse*Tint,0);' and row['texture_samples']==0 and row['base_colour_node']=='LP3eStraw' and not any(x and isinstance(x,u.MaterialExpressionTextureSample) for x in mask_in),(mname,row)
 # GP4b material nodes: both clump materials fade with the GP4Dither node (PerInstanceFadeAmount and the screen pixel), M_LidarClump takes its wind weight from the vertex alpha (GP4Wind: recovered program, per-instance custom data 2, vertex alpha from Parameters.VertexColor) at NativeGrassWindScale 2;
 # M_LidarRank keeps the recovered wind unchanged.
 gp2['gp4_nodes']={}
 for prop,mname,wind in [('grass_material','M_LidarClump',True),('rank_material','M_LidarRank',False)]:
  gm=g_actor.get_editor_property(prop);ex=list(mel.get_material_expressions(gm));mask=mel.get_material_property_input_node(gm,u.MaterialProperty.MP_OPACITY_MASK);wpo=mel.get_material_property_input_node(gm,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
  scales=[float(e.get_editor_property('default_value')) for e in ex if isinstance(e,u.MaterialExpressionScalarParameter) and str(e.get_editor_property('parameter_name'))=='NativeGrassWindScale']
  row=dict(dither_node=str(mask.get_editor_property('desc')) if mask is not None else None,dither_inputs=[type(x).__name__ if x else None for x in mel.get_inputs_for_material_expression(gm,mask)] if mask is not None else [],
   wind_node=str(wpo.get_editor_property('desc')) if wpo is not None else None,wind_inputs=[type(x).__name__ if x else None for x in mel.get_inputs_for_material_expression(gm,wpo)] if wpo is not None else [],wind_scale=scales,clip_value=float(gm.get_editor_property('opacity_mask_clip_value')))
  gp2['gp4_nodes'][mname]=row;assert row['dither_node']=='GP4Dither' and row['dither_inputs']==['MaterialExpressionPerInstanceFadeAmount','MaterialExpressionScreenPosition'],(mname,row)
  if wind:assert row['wind_node']=='GP4Wind' and row['wind_inputs']==['MaterialExpressionCustom','MaterialExpressionPerInstanceCustomData'] and set(row['wind_scale'])=={2.0},(mname,row)   # the recovered material carries two NativeGrassWindScale parameter nodes (one orphaned); both are set
  else:assert row['wind_node']!='GP4Wind',(mname,row)
 for n in ['M_Terrain','M_Detail']:
  m=u.load_asset('/Game/GrandTour/ArtTests/LidarStudy/'+n);cs=[str(e.get_editor_property('code')) for e in mel.get_material_expressions(m) if isinstance(e,u.MaterialExpressionCustom) and 'LP3d grazed pasture' in str(e.get_editor_property('code'))]
  gp2['ground_desaturation'][n]=bool(cs and 'pasLum' in cs[0]);assert not gp2['ground_desaturation'][n],(n,'GP2c: the 15% pasture desaturation must be gone')
 report['gp2']=gp2
 # CL1 readback from the saved level: each LiDAR ground material has the CL1Colour node feeding the rock mix and the CL1Rough node feeding the Roughness property,
 # every input of both wired (clay atlas included), and the installed road conditions are the prepare segment table.
 cl1=dict(ground={},conditions={})
 for n in ['M_Terrain','M_Detail']:
  m=u.load_asset('/Game/GrandTour/ArtTests/LidarStudy/'+n);ex=mel.get_material_expressions(m);cs=[e for e in ex if isinstance(e,u.MaterialExpressionCustom)]
  colour=[e for e in cs if str(e.get_editor_property('desc'))=='CL1Colour'];rough=native_property_node(m,u.MaterialProperty.MP_ROUGHNESS)
  rock=[e for e in cs if 'lerp(Native,r,s.a)' in str(e.get_editor_property('code'))];rd1g=[e for e in cs if str(e.get_editor_property('desc'))=='RD1Gravel'];cl1r=[e for e in cs if str(e.get_editor_property('desc'))=='CL1Rough']
  clay_objs=[e for e in ex if isinstance(e,u.MaterialExpressionTextureObject) and e.get_editor_property('texture') and e.get_editor_property('texture').get_name()=='T_clay']
  row=dict(colour_nodes=len(colour),colour_inputs=[str(i.get_editor_property('input_name')) for i in colour[0].get_editor_property('inputs')] if colour else [],colour_inputs_wired=len([x for x in mel.get_inputs_for_material_expression(m,colour[0]) if x]) if colour else 0,
   rock_takes_colour=bool(colour and rd1g and rock and any(x.get_name()==rd1g[0].get_name() for x in mel.get_inputs_for_material_expression(m,rock[0]) if x) and any(x.get_name()==colour[0].get_name() for x in mel.get_inputs_for_material_expression(m,rd1g[0]) if x)),   # RD1: the rock mix takes RD1Gravel, which takes CL1Colour

   roughness_node=str(rough.get_editor_property('desc')) if rough is not None else None,clay_texture_objects=len(clay_objs),peat_blocks=lp3c['ground'][n])
  if rough is not None and str(rough.get_editor_property('desc'))=='RD1Rough':row['rough_inputs_wired']=len([x for x in mel.get_inputs_for_material_expression(m,rough) if x]);row['rough_inputs']=[str(i.get_editor_property('input_name')) for i in rough.get_editor_property('inputs')];row['rough_takes_cl1rough']=bool(cl1r and any(x is not None and x.get_name()==cl1r[0].get_name() for x in mel.get_inputs_for_material_expression(m,rough)))   # RD1: the Roughness property is RD1Rough, which takes CL1Rough
  cl1['ground'][n]=row;assert len(colour)==1 and row['colour_inputs_wired']==len(row['colour_inputs']) and row['rock_takes_colour'] and row['roughness_node']=='RD1Rough' and row['rough_takes_cl1rough'] and row['rough_inputs_wired']==len(row['rough_inputs']) and len(clay_objs)==4+int(not install['gp2c']['nodes'][n[2:]].get('normal','skipped').startswith('skipped')),('CL1 ground',n,row)
 for a in refs:
  if isinstance(a,u.GTProceduralRoad):cl1['conditions'][a.get_actor_label()]=[dict(name=str(c.name),start_m=round(float(c.start_metres),1),end_m=round(float(c.end_metres),1),mud_depth_cm=float(c.mud_depth_cm),rut_depth_cm=float(c.rut_depth_cm),firmness=round(float(c.firmness),3),wetness=float(c.wetness)) for c in a.conditions]
 # RD1b: the installed condition rows are the raised gravel depths (owner 2026-10-19: roads should deform; RD1 found the open stretch wrote nothing at mud 4). Private roads: Gravel track mud 9 / rut 3 / firmness .80 over the whole road and the Damp hollow unchanged (28 / 9 / .32 / wet .8);
 # public roads: Firm gravel mud 5 / rut 2 / firmness .90. Every row is also stored in check.json cl1.conditions with rut and firmness.
 rd1b_want={'Gravel track':(9.,3.,.80),'Firm gravel':(5.,2.,.90),'Damp hollow':(28.,9.,.32)};rd1b_bad=[]
 design_roads={('LidarStudy_'+r['name']):r for r in json.loads((OUT/'roads.json').read_text()) if r.get('authoring')}
 for lab_,rows_ in cl1['conditions'].items():
  if lab_ in design_roads:
   draft=design_roads[lab_]['authoring'];assert rows_[0]['name']=='Mud track'
   assert abs(rows_[0]['mud_depth_cm']-draft['mud_depth_cm'])<.01 and abs(rows_[0]['rut_depth_cm']-draft['rut_depth_cm'])<.01
   assert len(rows_)==1+len(draft.get('conditions',[]))
   for got,want in zip(rows_[1:],draft.get('conditions',[])):
    assert got['name']==want['name']
    for key in ['mud_depth_cm','rut_depth_cm','firmness','wetness']:assert abs(got[key]-want[key])<.01,(lab_,key)
   continue
  names_=[r['name'] for r in rows_];allowed_=['Gravel track','Damp hollow'] if 'Riverside access' in lab_ or 'Pond field spur' in lab_ else ['Firm gravel']
  if sorted(names_)!=sorted(allowed_):rd1b_bad.append((lab_,'rows',names_))
  for r in rows_:
   w=rd1b_want.get(r['name']);got=(r['mud_depth_cm'],r['rut_depth_cm'],r['firmness'])
   if w is None or max(abs(g-v) for g,v in zip(got,w))>.005:rd1b_bad.append((lab_,r['name'],got,w))
 cl1['rd1b_conditions_wanted']=rd1b_want;cl1['rd1b_conditions_ok']=not rd1b_bad;assert not rd1b_bad,('RD1b: installed road conditions are not the raised gravel depths',rd1b_bad)
 report['cl1']=cl1
 # GP2c readback from the saved level: each LiDAR ground material has ONE GP2cPasture node (inputs Native, P, Style, GrassA, GrassB, Dry, all wired) between the colour program and CL1Colour, fed by the colour program, the Grass tile twice (1.5 m and 5.3 m UV nodes)
 # and the DryGrass tile once, all three TextureSample nodes on the shared wrap sampler; the tint triples in its code are the ones Install measured; GP2cNormal (when Install wrapped the Normal property) is the node feeding Normal with Grass_01_N through a TextureSample.
 gp2c=dict(ground={});ig=install['gp2c']
 for n in ['M_Terrain','M_Detail']:
  m=u.load_asset('/Game/GrandTour/ArtTests/LidarStudy/'+n);ex=list(mel.get_material_expressions(m));cs=[e for e in ex if isinstance(e,u.MaterialExpressionCustom)]
  def tg(tag):return [e for e in cs if str(e.get_editor_property('desc'))==tag]
  pas=tg('GP2cPasture');nrm=tg('GP2cNormal');cl1n=tg('CL1Colour');prog=[e for e in cs if 'LP3c forest-floor peat' in str(e.get_editor_property('code'))]
  assert len(pas)==1 and len(cl1n)==1 and len(prog)==1,('GP2c nodes',n,len(pas),len(cl1n),len(prog))
  ins=list(mel.get_inputs_for_material_expression(m,pas[0]));names=[str(i.get_editor_property('input_name')) for i in pas[0].get_editor_property('inputs')];code=str(pas[0].get_editor_property('code'))
  tex=[(x.get_editor_property('texture').get_name(),str(x.get_editor_property('sampler_source'))) for x in ins if isinstance(x,u.MaterialExpressionTextureSample)]
  tints=re.findall(r'macro\*float3\(([^)]*)\)',code);tint_nums=[[float(v) for v in t.split(',')] for t in tints]
  row=dict(pasture_nodes=len(pas),inputs=names,inputs_wired=len([x for x in ins if x]),program_feeds=any(x is not None and x.get_name()==prog[0].get_name() for x in ins),clay_takes_pasture=any(x is not None and x.get_name()==pas[0].get_name() for x in mel.get_inputs_for_material_expression(m,cl1n[0])),
   texture_samples=sorted(t for t,_ in tex),sampler_sources=sorted({s_ for _,s_ in tex}),tint_in_code=dict(grass=tint_nums[0] if tint_nums else None,dry=tint_nums[1] if len(tint_nums)>1 else None),macro='clamp((pas.noise(P.xy/1200.+71.)-.5)*3.,-1,1)' in code,
   dry_mix='max(.25*mown,.60*rank)' in code and 'smoothstep(.74,.80,pas.noise(P.xy/800.+211.))' in code,no_noise_octaves=not any(t in code for t in ('pasA','pasB','pasC','pasLum')))
  want=[ig['tiles']['grass']['tint'],ig['tiles']['dry']['tint']]
  assert row['inputs']==['Native','P','Style','GrassA','GrassB','Dry'] and row['inputs_wired']==6 and row['program_feeds'] and row['clay_takes_pasture'],('GP2c pasture wiring',n,row)
  assert row['texture_samples']==['T_Landscape_DryGrass_01_A','T_Landscape_Grass_01_A','T_Landscape_Grass_01_A'] and len(row['sampler_sources'])==1 and 'WRAP_WORLD_GROUP' in row['sampler_sources'][0] and row['macro'] and row['dry_mix'] and row['no_noise_octaves'],('GP2c pasture content',n,row)
  assert len(tint_nums)==2 and all(abs(a-b)<2e-4 for t_,w_ in zip(tint_nums,want) for a,b in zip(t_,w_)),('GP2c tint differs from the measured one',n,tint_nums,want)
  nmode=ig['nodes'][n[2:]].get('normal','skipped');row['normal_install']=nmode
  if nmode.startswith('skipped'):assert not nrm,('GP2cNormal present though Install skipped it',n)
  else:
   nn=native_property_node(m,u.MaterialProperty.MP_NORMAL);nins=list(mel.get_inputs_for_material_expression(m,nrm[0])) if nrm else []
   row['normal']=dict(nodes=len(nrm),is_normal_property_node=bool(nn is not None and nrm and nn.get_name()==nrm[0].get_name()),inputs=[str(i.get_editor_property('input_name')) for i in nrm[0].get_editor_property('inputs')] if nrm else None,inputs_wired=len([x for x in nins if x]),
    normal_texture=[x.get_editor_property('texture').get_name() for x in nins if isinstance(x,u.MaterialExpressionTextureSample)],strength_in_code='.5*(1-saturate((length(Camera-P)*.01-20)/20))' in (str(nrm[0].get_editor_property('code')) if nrm else ''))
   assert len(nrm)==1 and row['normal']['is_normal_property_node'] and row['normal']['inputs']==['Base','P','Camera','Style','LidarClay','GrassN'] and row['normal']['inputs_wired']==6 and row['normal']['normal_texture']==['T_Landscape_Grass_01_N'] and row['normal']['strength_in_code'],('GP2c normal wrapper',n,row['normal'])
  gp2c['ground'][n]=row
 report['gp2c']=gp2c;save()
 # RD1 readback from the saved level: T_gravel (sRGB, wrap), and in each ground material ONE RD1Gravel node (inputs Native, P, Style, LidarClay, GravelA, GravelB, all wired; the rock mix takes it, it takes CL1Colour; both gravel samples are the T_gravel texture on the shared wrap sampler)
 # and ONE RD1Rough node (inputs Base, P, Style, LidarClay) that is the Roughness property and takes CL1Rough.
 rd1=dict(ground={});irr=install['rd1'];gt=u.load_asset(BASE+'/T_gravel');assert gt,'RD1: T_gravel missing'
 rd1['texture']=dict(path=gt.get_path_name(),srgb=bool(gt.get_editor_property('srgb')),address=[str(gt.get_editor_property('address_x')),str(gt.get_editor_property('address_y'))],power_of_two=str(gt.get_editor_property('power_of_two_mode')),max_size=int(gt.get_editor_property('max_texture_size')));assert rd1['texture']['srgb'] and all('WRAP' in a for a in rd1['texture']['address']),rd1['texture']
 for n in ['M_Terrain','M_Detail']:
  m=u.load_asset('/Game/GrandTour/ArtTests/LidarStudy/'+n);ex=list(mel.get_material_expressions(m));cs=[e for e in ex if isinstance(e,u.MaterialExpressionCustom)]
  def tg(tag):return [e for e in cs if str(e.get_editor_property('desc'))==tag]
  g_=tg('RD1Gravel');r_=tg('RD1Rough');cl1c=tg('CL1Colour');cl1r=tg('CL1Rough');assert len(g_)==1 and len(r_)==1 and len(cl1c)==1 and len(cl1r)==1,('RD1 nodes',n,len(g_),len(r_))
  gi=list(mel.get_inputs_for_material_expression(m,g_[0]));ri=list(mel.get_inputs_for_material_expression(m,r_[0]));tex=[(x.get_editor_property('texture').get_name(),str(x.get_editor_property('sampler_source'))) for x in gi if isinstance(x,u.MaterialExpressionTextureSample)];rn=native_property_node(m,u.MaterialProperty.MP_ROUGHNESS)
  code=str(g_[0].get_editor_property('code'));rcode=str(r_[0].get_editor_property('code'))
  row=dict(gravel_nodes=len(g_),inputs=[str(i.get_editor_property('input_name')) for i in g_[0].get_editor_property('inputs')],inputs_wired=len([x for x in gi if x]),texture_samples=sorted(t for t,_ in tex),sampler_sources=sorted({s_ for _,s_ in tex}),takes_cl1colour=any(x is not None and x.get_name()==cl1c[0].get_name() for x in gi),
   rough_nodes=len(r_),rough_inputs=[str(i.get_editor_property('input_name')) for i in r_[0].get_editor_property('inputs')],rough_wired=len([x for x in ri if x]),rough_is_roughness_property=bool(rn is not None and rn.get_name()==r_[0].get_name()),rough_takes_cl1rough=any(x is not None and x.get_name()==cl1r[0].get_name() for x in ri),
   code=dict(corridor='smoothstep(2.0,2.6,ad)' in code,wheel_lines='abs(ad-0.820)' in code,darker='gr*=1-0.250*wl' in code,blend='lerp(GravelA,GravelB,0.300)' in code,saturation=('lerp(lum.xxx,gr,%.3f)'%irr['saturation']) in code,rough_lower='0.850*(1-0.150*wl)' in rcode))
  assert row['inputs']==['Native','P','Style','LidarClay','GravelA','GravelB'] and row['inputs_wired']==6 and row['takes_cl1colour'] and row['texture_samples']==['T_gravel','T_gravel'] and len(row['sampler_sources'])==1 and 'WRAP_WORLD_GROUP' in row['sampler_sources'][0] and all(row['code'].values()),('RD1 gravel node',n,row)
  assert row['rough_inputs']==['Base','P','Style','LidarClay'] and row['rough_wired']==4 and row['rough_is_roughness_property'] and row['rough_takes_cl1rough'],('RD1 rough node',n,row)
  rd1['ground'][n]=row
 mt=u.load_asset('/Game/GrandTour/ArtTests/LidarStudy/M_Tread');tn=[e for e in mel.get_material_expressions(mt) if isinstance(e,u.MaterialExpressionCustom) and str(e.get_editor_property('desc'))=='RD1Tread'];em=mel.get_material_property_input_node(mt,u.MaterialProperty.MP_EMISSIVE_COLOR)
 rd1['tread']=dict(nodes=len(tn),is_emissive_property=bool(em is not None and tn and em.get_name()==tn[0].get_name()),inputs=[str(i.get_editor_property('input_name')) for i in tn[0].get_editor_property('inputs')] if tn else None,inputs_wired=len([x for x in mel.get_inputs_for_material_expression(mt,tn[0]) if x]) if tn else 0);assert rd1['tread']['nodes']==1 and rd1['tread']['is_emissive_property'] and rd1['tread']['inputs']==['Base','P','LidarClay'] and rd1['tread']['inputs_wired']==3,rd1['tread']
 rd1['install']=dict(version=irr['version'],relief_material=irr['relief_material'],tint=irr['tint'],wheel=irr['wheel'],tiling_cm=irr['tiling_cm']);report['rd1']=rd1;save()
 sheet=next(a for a in refs if isinstance(a,u.GTWaterSheet) and not a.get_editor_property('mud_initial_domain'));assert len(sheet.get_editor_property('domain_surfaces'))==3
 root=sheet.get_editor_property('water_domain');children=list(root.road_patches);assert len(children)==3+int(bool(install.get('logging_trial')))
 assert not root.set_child_domains([root]) and list(root.road_patches)==children
 assert not children[0].set_child_domains([root]) and not children[0].road_patches
 for a in sheet.get_editor_property('domain_surfaces'):assert a.static_mesh_component.get_material(0) and a.static_mesh_component.get_material(0).get_path_name().startswith(BASE)
 assert u.load_asset(sheet.get_editor_property('surface_material_path'))
 report['water_queries']=[]
 for patch in data['water']:
  x,y,z=patch['probe'];xy=u.Vector2D(x,y);assert sheet.covers(xy),patch['name'];assert abs(sheet.surface_cm_at(xy)-z)<2
  sheet.preview_water_at(xy,0,True);before=sheet.surface_cm_at(xy);added=sheet.add_impulse(xy,120,3);sheet.preview_water_at(xy,.2,False);after=sheet.surface_cm_at(xy)
  report['water_queries'].append(dict(name=patch['name'],surface_cm=before,disturbed_cm=after,added_m3=added));assert added>0 and abs(after-before)>.01
 les.editor_set_viewport_realtime(False);assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900)
 deadline=time.monotonic()+180
 while not world:
  world=u.EditorLevelLibrary.get_game_world();assert time.monotonic()<deadline;yield .5
 pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car();assert isinstance(car,u.GTCarPawn);pc.possess(car)
 car.disable_input(pc);car.reset_driving_inputs();move=car.get_chaos_movement();move.set_brake_input(0);move.set_throttle_input(0);move.set_handbrake_input(True)
 mesh=car.get_component_by_class(u.SkeletalMeshComponent)
 for cmd in ['DisableAllScreenMessages','r.MotionBlurQuality 0','t.MaxFPS 60','t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0','showhud']:u.SystemLibrary.execute_console_command(world,cmd,pc)
 surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0]
 grass=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTMixedGroundDetails) if a.generate_around_player)
 import sys
 sys.path.insert(0,str(ROOT/'Art/Unreal'))
 import lidar_gravel_dust
 lidar_gravel_dust.validate(world)
 # CL2 readback on the PIE surface: the clay weight and the response the soil contact takes from it, at the middle of the open Clay track stretch, the middle of the
 # Clay slurry bush climb (both Riverside access, prepare's roads.json segments [start_m,end_m,bush]) and the middle of Waimeamea Road (public gravel, no clay).
 cl2_roads=json.loads((OUT/'roads.json').read_text())
 def cl2_road(name):return next(r for r in cl2_roads if r['name']==name)
 def cl2_at(name,s_m):
  pts=cl2_road(name)['points'];cum=[0.]
  for a,b in zip(pts,pts[1:]):cum.append(cum[-1]+math.dist(a,b))
  s=min(max(s_m*100.,0.),cum[-1]);k=max(1,min(bisect.bisect_right(cum,s),len(cum)-1));a,b=pts[k-1],pts[k];f=(s-cum[k-1])/max(1e-9,cum[k]-cum[k-1]);return a[0]+(b[0]-a[0])*f,a[1]+(b[1]-a[1])*f
 def cl2_mid(name,bush):seg=next(g for g in cl2_road(name)['segments'] if g[2]==bush);return (seg[0]+seg[1])/2
 report['cl2']=dict(atlas_report=surface.get_surface_report(),points={})
 for label,name,s_m,limit in [('clay_track_open','Riverside access',cl2_mid('Riverside access',0),'<.05'),('clay_slurry_bush','Riverside access',cl2_mid('Riverside access',1),'<.05'),('public_road','Waimeamea Road',cl2_road('Waimeamea Road')['length_m']/2,'<.05')]:
  x,y=cl2_at(name,s_m);q=surface.sample_surface(u.Vector2D(x,y))
  report['cl2']['points'][label]=dict(road=name,station_m=round(s_m,1),xy_cm=[round(x,1),round(y,1)],limit=limit,clay_weight=q.clay_weight,friction_scale=q.friction_scale,clay_friction_scale=q.clay_friction_scale,cohesion=q.cohesion,wetness=q.wetness,
   native_friction=q.native_friction,native_linear_resistance=q.native_linear_resistance,native_push_resistance=q.native_push_resistance,soil_shear=bool(q.get_editor_property('bSoilShearResponse')),granular=bool(q.get_editor_property('bGranularResponse')),
   native_substance=bool(q.get_editor_property('bNativeSubstanceResponse')),sinkage_cap_cm=q.sinkage_cap_cm,surface_tag=str(q.surface_tag))
 save();cl2_pts=report['cl2']['points']
 # RD1: every road is gravel, so the carriageway of both private stretches carries no clay either; the cut band (prepare's probe: the middle of 15 m of continuous band on Riverside access, outside the paddocks) keeps its .8
 cut_=data['clay']['cut']['stats']['Riverside access'];cbx,cby=cut_['probe_cm'];qb=surface.sample_surface(u.Vector2D(cbx,cby))
 cl2_pts['cut_band']=dict(road='Riverside access',station_m=cut_['probe_station_m'],xy_cm=[round(cbx,1),round(cby,1)],limit='>.3',clay_weight=qb.clay_weight,friction_scale=qb.friction_scale,clay_friction_scale=qb.clay_friction_scale,cohesion=qb.cohesion,wetness=qb.wetness,
  native_friction=qb.native_friction,native_linear_resistance=qb.native_linear_resistance,native_push_resistance=qb.native_push_resistance,soil_shear=bool(qb.get_editor_property('bSoilShearResponse')),granular=bool(qb.get_editor_property('bGranularResponse')),native_substance=bool(qb.get_editor_property('bNativeSubstanceResponse')),sinkage_cap_cm=qb.sinkage_cap_cm,surface_tag=str(qb.surface_tag))
 assert cl2_pts['clay_track_open']['clay_weight']<.05 and cl2_pts['clay_slurry_bush']['clay_weight']<.05 and cl2_pts['public_road']['clay_weight']<.05 and cl2_pts['cut_band']['clay_weight']>.3,cl2_pts
 report['cl2']['ok']=True;save()

 # GP2c firm paddocks (owner screenshot 13: HUD sink 14.6 cm on grazed pasture): prepare sets paint depth 1.0 cm (GP2d; GP2c 1.5 cm; x LayerDepthScale 2.48 = 2.43 cm), firmness .90 and softness .22 inside the paddocks off the track. SampleSurface reads sinkage_cap_cm straight from paint channel 0 (x50 cm), so the
 # PIE surface at the NE paddock trough (Place/hardware.json 'paddock 1 trough', about 90 m inside paddock 1) must report <= 4 cm; the numbers go into check.json before the assert.
 hw0=json.loads((OUT/'hardware.json').read_text());tr0=next(i for i in hw0 if i['mesh']=='SM_NZ_Trough' and i['tag']=='paddock 1 trough');q0=surface.sample_surface(u.Vector2D(tr0['p'][0],tr0['p'][1]));hw0=None
 report['gp2c_firm']=dict(trough_cm=[tr0['p'][0],tr0['p'][1]],sinkage_cap_cm=q0.sinkage_cap_cm,softness=q0.softness,sinkage_rate_cm_per_s=q0.sinkage_rate_cm_per_s,layer_depth_scale=float(surface.get_editor_property('layer_depth_scale')),authored=bool(q0.get_editor_property('bAuthored')),surface_tag=str(q0.surface_tag),limit_cm=4.,softness_want=.22,note='prepare: paddock paint depth 1.0 cm, firmness .90, softness (paint channel 3) .22 (before GP2c: mean 7.6 cm, .205, softness .53; texture depth 1.0 cm x LayerDepthScale 2.48 = 2.43 cm)');save()
 assert q0.sinkage_cap_cm<=4. and abs(q0.softness-.22)<=.02,('GP2c/GP2d: the NE paddock trough is still soft',report['gp2c_firm'])   # GP2d: softness is paint channel 3 (.22 written by prepare, 8-bit .2196)
 report['gp2c_firm']['ok']=True;save()
 for site in sites:
  x,y=site['center'];z=site['center_height_cm'];car.set_actor_location_and_rotation(u.Vector(x,y,z+100),u.Rotator(yaw=site['yaw']),False,True);mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector());yield from settle(12)
  frame_samples.clear();measure_frames=True
  poses=[]
  for _ in range(5):
   yield from settle(.4);p=car.get_actor_location();r=car.get_actor_rotation();poses.append(dict(z=p.z,pitch=r.pitch,roll=r.roll,speed=car.get_velocity().length(),contacts=sum(bool(u.ChaosWheeledVehicleMovementComponent.break_wheel_status(move.get_wheel_state(k))[0]) for k in range(4))))
  measure_frames=False
  native=nums(move.native_substance_report());sample=surface.sample_surface(u.Vector2D(x,y));row=dict(name=site['name'],poses=poses,native=native,mud_depth_cm=sample.sinkage_cap_cm,grass=grass.near_grass_count(),near_a=grass.grass.get_instance_count(),near_b=grass.grass_b.get_instance_count(),near_c=grass.grass_c.get_instance_count(),distant_grass=grass.distant_grass.get_instance_count(),body=nums(move.body_soil_report()),grass_report=grass.grass_report());row['editor_frame_ms_mean']=1000*sum(frame_samples)/max(1,len(frame_samples));row['frame_samples']=len(frame_samples)
  # GP2: clump mode readout. near = the pasture clumps (Grass), rank = the rank band (RankGrass), distant = the distant card layer; mode/near/rank/distant also come from GrassReport.
  rep=row['grass_report'];row.update(mode=re.search(r'mode=(\w+)',rep).group(1),rank_grass=grass.rank_grass.get_instance_count(),pasture_mesh=grass.grass.static_mesh.get_name() if grass.grass.static_mesh else None,pasture_meshes=[c.static_mesh.get_name() if c.static_mesh else None for c in (grass.grass,grass.grass_b,grass.grass_c)],rank_mesh=grass.rank_grass.static_mesh.get_name() if grass.rank_grass.static_mesh else None,near_total=row['grass']+grass.rank_grass.get_instance_count())
  row['report_counts']=dict(near=int(nums(rep)['near']),rank=int(nums(rep)['rank']),distant=int(nums(rep)['distant']));report['sites'].append(row);save()
  # PF1: the incrementally streamed grass against the old full refresh: the live instances must be exactly the cells a from-scratch pass over the disc accepts (no job may be in flight), with consistent bookkeeping
  for _ in range(60):
   row['stream_consistency']=grass.streaming_consistency(True)
   if row['stream_consistency']!='busy':break
   yield from settle(.5)
  sc=row['stream_consistency'];row['stream_rebuild_diff']=sum(int(v) for v in re.findall(r'rebuild_(?:missing|extra)=(\d+)',sc));save()
  assert sc.startswith('ok') and row['stream_rebuild_diff']==0,('PF1 streaming consistency',row['name'],sc)
  rg=nums(row['grass_report']);row['report_gp4b']={k:int(rg[k]) for k in ('layers','near_a','near_b','near_c','stream_radius_cm','cull_start_cm','cull_end_cm','lod1_cm','lod2_cm')}
  row['patch_share']=[round(v/max(1,row['grass']),3) for v in (row['near_a'],row['near_b'],row['near_c'])];save()
  assert row['mode']=='clumps' and row['pasture_meshes']==['SM_NZ_GrassPatch_A','SM_NZ_GrassPatch_B','SM_NZ_GrassPatch_C'] and row['rank_mesh']=='SM_NZ_RankClump_A' and row['report_counts']==dict(near=row['grass'],rank=row['rank_grass'],distant=row['distant_grass']),row
  assert row['grass']==row['near_a']+row['near_b']+row['near_c'] and row['report_gp4b']==dict(layers=3,near_a=row['near_a'],near_b=row['near_b'],near_c=row['near_c'],stream_radius_cm=4000,cull_start_cm=3000,cull_end_cm=3800,lod1_cm=1000,lod2_cm=2200),row
  assert row['grass']<1000 or min(row['patch_share'])>.2,row   # the three variants mix (a third each, hash-picked)
  if site is sites[0]:
   # GP2 cost probe (first site only): the same position and car, clump mode, then gt.Grass.Clumps 0 (cards at the actor's GrassSpacingCm, 45), then clump mode again. 4 s windows after 15 s of streaming. The editor runs hidden
   # (-RenderOffScreen), so these are the editor+PIE tick times: comparable inside this run, not a measure of play cost.
   def cmd(c):u.SystemLibrary.execute_console_command(world,c,pc)
   probe=dict(caveat='hidden -RenderOffScreen editor; per-tick times include the editor and PIE overhead and are comparable only within this run',spacing_cm=dict(cards=float(grass.grass_spacing_cm),clumps=float(grass.clump_spacing_cm)))
   def snap():return dict(mode=re.search(r'mode=(\w+)',grass.grass_report()).group(1),near=grass.near_grass_count(),rank=grass.rank_grass.get_instance_count(),distant=grass.distant_grass.get_instance_count())
   w=yield from frame_window(4);probe['clumps_first']=dict(snap(),**w)
   cmd('gt.Grass.Clumps 0');yield from settle(15);assert snap()['mode']=='cards',snap()
   w=yield from frame_window(4);probe['cards']=dict(snap(),**w)
   cmd('gt.Grass.Clumps 1');yield from settle(15);assert snap()['mode']=='clumps',snap()
   w=yield from frame_window(4);probe['clumps_again']=dict(snap(),**w)
   a_,b_=probe['cards'],probe['clumps_first'];c_=probe['clumps_again'];probe['near_ratio_cards_over_clumps']=a_['near']/max(1,b_['near']+b_['rank']);probe['ms_delta_cards_minus_clumps_mean']=a_['ms_mean']-0.5*(b_['ms_mean']+c_['ms_mean'])
   report['grass_cost_probe']=probe;save()
  yaw=math.radians(site['yaw']);fx,fy=math.cos(yaw),math.sin(yaw)
  yield from capture(site['name'].replace(' ','_'),(x-fx*800-fy*220,y-fy*800+fx*220,z+450),(x+fx*900,y+fy*900,z+100))
  assert all(q['contacts']>=3 and abs(q['roll'])<25 and abs(q['pitch'])<30 for q in poses[-3:]),row
  assert row['grass']>100,row   # GP2: no distant-count floor; paddock interiors have no distant cards in clump mode (the near>1000 floor is asserted after all sites, below)
  gr=nums(row['grass_report']);assert gr['custom_floats']==4 and gr['instances']==row['grass'],row   # LP3e: the streamed grass carries the Straw float in PIE
  row['straw_cards']=int(gr['straw'])
  assert abs(car.get_drivetrain().get_drive_input())<.001
 # LP1 corridor: cross-slope across the car track (+-90cm) and the road edge
 # (+-190cm) every 10m along each installed road line, read from the built
 # relief tiles exactly as install reads site heights (base height off-tile).
 try:tiles=[(t.get_actor_location(),t.span_cm,t) for t in author.relief_tiles.values() if t];base=author.base_height_at
 except Exception:tiles=[(t.get_actor_location(),t.span_cm,t) for t in u.GameplayStatics.get_all_actors_of_class(world,u.GTRoadReliefTile)];base=u.GameplayStatics.get_all_actors_of_class(world,u.GTProceduralGround)[0].base_height_at
 cell=max([span for _,span,_ in tiles]+[1.]);grid={}
 for o,span,t in tiles:
  for i in range(math.floor(o.x/cell),math.floor((o.x+span)/cell)+1):
   for j in range(math.floor(o.y/cell),math.floor((o.y+span)/cell)+1):grid.setdefault((i,j),[]).append((o.x,o.y,span,t))
 def ground(gx,gy):
  xy=u.Vector2D(gx,gy)
  for ox,oy,span,t in grid.get((math.floor(gx/cell),math.floor(gy/cell)),()):
   if ox<=gx<ox+span and oy<=gy<oy+span:return t.height_at(xy)
  return base(xy)
 def pct(v,q):
  v=sorted(v);f=(len(v)-1)*q/100;i=int(f);return v[i]+(v[min(i+1,len(v)-1)]-v[i])*(f-i)
 report['corridor']={}
 for road in json.loads((OUT/'roads.json').read_text()):
  pts=road['points'];cum=[0.]
  for a,b in zip(pts,pts[1:]):cum.append(cum[-1]+math.dist(a,b))
  L=cum[-1]
  def at(s):
   s=min(max(s,0.),L);k=max(1,min(bisect.bisect_right(cum,s),len(cum)-1));a,b=pts[k-1],pts[k];f=(s-cum[k-1])/max(1e-9,cum[k]-cum[k-1]);return a[0]+(b[0]-a[0])*f,a[1]+(b[1]-a[1])*f
  ss=[k*1000. for k in range(int(L//1000)+1)]
  if L-ss[-1]>1e-3:ss.append(L)
  rows=[]
  for s in ss:
   px,py=at(s);qx,qy=at(s+1000);rx,ry=at(s-1000);tx,ty=qx-rx,qy-ry;n=math.hypot(tx,ty) or 1.;nx,ny=-ty/n,tx/n
   h=lambda d:ground(px+nx*d,py+ny*d)
   rows.append((px,py,math.degrees(math.atan((h(90)-h(-90))/180)),math.degrees(math.atan((h(190)-h(-190))/380))))
  tr=[abs(r[2]) for r in rows];ed=[abs(r[3]) for r in rows]
  report['corridor'][road['name']]=dict(stations=len(rows),track_p50=pct(tr,50),track_p95=pct(tr,95),track_max=max(tr),edge_p95=pct(ed,95),over_10=sum(v>10 for v in tr),worst=[[round(r[0],1),round(r[1],1),round(r[2],2)] for r in sorted(rows,key=lambda r:-abs(r[2]))[:5]],over_5=[[round(r[0],1),round(r[1],1),round(r[2],2)] for r in sorted(rows,key=lambda r:-abs(r[2])) if abs(r[2])>5])
  yield .05
 # LP3 on-foot captures at 1.6m eye height: the bush climb of Riverside access and the house yard. The car is parked 8m behind the camera so the ground cover streams around it.
 def on_foot(name,pos_xy,target_xy,target_up):
  px,py=pos_xy;tx,ty=target_xy;gz=ground(px,py);dx,dy=tx-px,ty-py;n=math.hypot(dx,dy) or 1.;dx,dy=dx/n,dy/n;bx,by=px-dx*800,py-dy*800
  car.set_actor_location_and_rotation(u.Vector(bx,by,ground(bx,by)+100),u.Rotator(yaw=math.degrees(math.atan2(dy,dx))),False,True);mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector())
  yield from settle(10)
  yield from capture(name,(px,py,gz+160),(tx,ty,ground(tx,ty)+target_up));report.setdefault('lp3_captures',{})[name]=dict(camera_cm=[px,py,gz+160],target_cm=[tx,ty,ground(tx,ty)+target_up],ground_cm=gz)
 bt=data['captures']['Bush_track'];yield from on_foot('Bush_track',bt['pos_cm'],bt['target_cm'],120)
 hy=data['captures']['House_yard'];yield from on_foot('House_yard',hy['pos_cm'],hy['anchor_cm'],250)
 cto=data['captures']['Clay_track_open'];yield from on_foot('Clay_track_open',cto['pos_cm'],cto['target_cm'],100)
 pg=data['captures']['Paddock_gate'];yield from on_foot('Paddock_gate',pg['pos_cm'],pg['target_cm'],pg['target_up_cm'])
 en=data['captures']['Entrance'];yield from on_foot('Entrance',en['pos_cm'],en['target_cm'],en['target_up_cm'])
 # LP3d Paddock_middle (owner photo 09): 1.6 m on foot in the NE paddock (paddock 1, the 3.98 ha field at the Pond spur), standing 4 m before its trough and 2 m to one side so the trough sits ahead in frame,
 # looking at the nearest bush-wall tree (nearest entry of trees.json, outside every paddock by LP4) at mid-canopy height. Trough position from Place/hardware.json ('paddock 1 trough').
 hwj=json.loads((OUT/'hardware.json').read_text());trough=next(i for i in hwj if i['mesh']=='SM_NZ_Trough' and i['tag']=='paddock 1 trough');tx,ty=trough['p'][0],trough['p'][1]
 treesj=json.loads((OUT/'trees.json').read_text());wall_d,wall=min((math.hypot(t[0]-tx,t[1]-ty),t) for t in treesj);treesj=None
 ddx,ddy=(wall[0]-tx)/wall_d,(wall[1]-ty)/wall_d;pm=(tx-ddx*400-ddy*200,ty-ddy*400+ddx*200)
 yield from on_foot('Paddock_middle',pm,(wall[0],wall[1]),700);report['lp3_captures']['Paddock_middle'].update(trough_cm=[tx,ty],nearest_bush_wall_tree_cm=[wall[0],wall[1]],wall_distance_cm=wall_d)

 # GP2c Paddock_chase (owner screenshot 13): the car at the NE paddock trough + 6 m along +X, facing the nearest bush-wall tree (Paddock_middle's look direction), settled 6 s; the camera is 5 m above and 9 m behind the car (opposite its forward),
 # looks along the car's heading pitched 25 degrees down, FOV 68. The sink (the HUD's number: the worst wheel SinkageCm), the surface under the car and the car's height over the built ground go into check.json before the assert.
 # The brief's +6 m put the car 1.3 m from 'bale by trough 1' (the first Check showed it propped on the bale, tilted, 3 wheels down), so the spot slides along +X in 1 m steps from +6 m until every hardware item is 6 m away; the offset used goes into check.json.
 off_m=6
 while any(math.hypot(i['p'][0]-(tx+off_m*100.),i['p'][1]-ty)<600. for i in hwj) and off_m<40:off_m+=1
 cxx,cyy=tx+off_m*100.,ty;ddx2,ddy2=wall[0]-cxx,wall[1]-cyy;hyaw=math.degrees(math.atan2(ddy2,ddx2))
 car.set_actor_location_and_rotation(u.Vector(cxx,cyy,ground(cxx,cyy)+100),u.Rotator(yaw=hyaw),False,True);mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector())
 yield from settle(6)
 cp=car.get_actor_location();cyaw=math.radians(car.get_actor_rotation().yaw);fx,fy=math.cos(cyaw),math.sin(cyaw);pit=math.radians(25.)
 cam=(cp.x-fx*900,cp.y-fy*900,cp.z+500);aim=(cam[0]+fx*math.cos(pit)*1000,cam[1]+fy*math.cos(pit)*1000,cam[2]-math.sin(pit)*1000)
 tuning=car.get_component_by_class(u.GTVehicleTuningComponent).get_current();sinks=[float(w.sinkage_cm) for w in tuning.wheels];qc=surface.sample_surface(u.Vector2D(cp.x,cp.y))
 report['gp2c_chase']=dict(offset_from_trough_m=off_m,nearest_hardware_m=min(math.hypot(i['p'][0]-cp.x,i['p'][1]-cp.y) for i in hwj)/100.,car_cm=[cp.x,cp.y,cp.z],car_yaw_deg=math.degrees(cyaw),camera_cm=list(cam),aim_cm=list(aim),pitch_deg=25.,fov_deg=68.,trough_cm=[tx,ty],car_over_ground_cm=cp.z-ground(cp.x,cp.y),hud_sink_cm=max(sinks),wheel_sink_cm=sinks,
  surface_sinkage_cap_cm=qc.sinkage_cap_cm,surface_softness=qc.softness,hud_sink_target_cm=3.,hud_sink_under_target=max(sinks)<3.,wheel_contacts=sum(bool(u.ChaosWheeledVehicleMovementComponent.break_wheel_status(move.get_wheel_state(k))[0]) for k in range(4)),speed_cm_s=car.get_velocity().length());save()
 yield from capture('Paddock_chase',cam,aim);report['gp2c_chase']['image']=str(OUT/'Paddock_chase.png');report['gp2c_chase']['grass_report']=grass.grass_report();save()
 assert report['gp2c_chase']['wheel_contacts']>=3 and qc.sinkage_cap_cm<=4. and abs(qc.softness-.22)<=.05,report['gp2c_chase']   # GP2d: the worst-wheel sink is recorded (hud_sink_cm, target under 3 cm), not asserted
 # RD1 Drive: the car leaves the chase spot, drives the two roads and comes back (the Paddock_contact capture below needs it there)
 yield from drive_step(ground,(car.get_actor_location(),car.get_actor_rotation()))
 save();tiles=grid=ground=base=None
 for name,c in report['corridor'].items():
  if 'LidarStudy_'+name in design_roads:
   # A new 4WD route has its own owner gate; do not apply the public-road 4-degree criterion.
   c['owner_drive_required']=True
   assert c['track_max']<=20,('new track cross-slope exceeds 20 degrees; revise its controls',name,c)
   continue
  if name in ['Riverside access','Pond field spur']:assert c['track_p95']<=5 and c['track_max']<=10,('corridor',name,c)
  else:assert c['track_p95']<=4,('corridor',name,c)
 # Stationary pond view; no driving or vehicle steering inputs.
 pond=next(p for p in data['water'] if p['name']=='AccessPond');x,y,z=pond['probe']
 yield from capture('Access_pond',(x-3300,y+2800,z+2000),(x,y,z))
 x,y,z=data['river_house_probe'];yield from capture('River_beside_house',(x+600,y+900,z+1100),(x,y-500,z))
 # Overview from the priority access road.
 
 site=sites[0];x,y=site['center'];z=site['center_height_cm']
 yield from capture('Woodland_overview',(x-22000,y+22000,z+28000),(x,y-27000,z-2000))
 # GP4b contact bookkeeping across the three pasture components (run last: it leaves bent and removed patches in the world): nine contacts 60 cm apart on a line 5 m ahead of the car at the chase spot, the odd ones removing (as a deep wheel contact does),
 # then a capture. Every component must report bent and removed instances (a contact reaches whichever mesh the lattice cell picked).
 gp_=car.get_actor_location();yw_=math.radians(car.get_actor_rotation().yaw);cfx,cfy=math.cos(yw_),math.sin(yw_);cr0=nums(grass.grass_report())
 cpts=[(gp_.x+cfx*500-cfy*(i-4)*60,gp_.y+cfy*500+cfx*(i-4)*60) for i in range(9)]
 for i,(px_,py_) in enumerate(cpts):grass.apply_review_grass_contact(u.Vector2D(px_,py_),i%2==1)
 yield from settle(2)
 cr1=nums(grass.grass_report());keys=['bent_a','bent_b','bent_c','removed_a','removed_b','removed_c']
 report['gp4_contact']=dict(points=len(cpts),removing=4,centre_cm=[gp_.x+cfx*500,gp_.y+cfy*500],before={k:int(cr0[k]) for k in keys},after={k:int(cr1[k]) for k in keys});save()
 yield from capture('Paddock_contact',(gp_.x+cfx*950,gp_.y+cfy*950,gp_.z+210),(gp_.x+cfx*500,gp_.y+cfy*500,gp_.z-30))   # from beyond the line looking back at it (the car and its shadow are behind the line);report['gp4_contact']['image']=str(OUT/'Paddock_contact.png');save()
 assert all(cr1[k]>0 for k in keys),report['gp4_contact']
 report['surface']=surface.get_surface_report();report['protected_unchanged']=len(install['protected_before'])
 # GP2 counts, asserted last so every capture and number is saved first: near+rank clumps above 1000 at every site; pasture clumps alone above 1000 at the sites with paddock or verge cover. Riverside house (the bush
 # site: most of its cover is the rank band, 574 pasture + 465 rank in the first run) is recorded, not held to the pasture-only floor.
 low=[r['name'] for r in report['sites'] if r['near_total']<=1000 or (r['name']!='Riverside house' and r['grass']<=1000)];report['near_not_above_1000']=[r['name'] for r in report['sites'] if r['grass']<=1000];save();assert not low,('GP2 clump counts below the floor at',low,[(r['name'],r['grass'],r['rank_grass']) for r in report['sites']])
 report['ok']=True;save()
 refs=author=sheet=root=children=a=surface=grass=mesh=move=None;gc.collect();yield from finish()

def finish():
 global world,pc,car,camera
 if world:u.GameplayStatics.set_game_paused(world,False)
 u.EditorLevelLibrary.editor_end_play();yield 4
 world=pc=car=camera=None;gc.collect()
 u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Engine/Maps/Entry');world=None;yield 2
steps=run();deadline=0;began=time.monotonic();failed=False
def tick(dt):
 global deadline,busy,steps,failed
 if measure_frames and 0<dt<1:frame_samples.append(dt)
 if drive_on and car:
  try:drive_ctrl()
  except Exception:report.setdefault('drive_errors',[]).append(traceback.format_exc());globals()['drive_on']=False
 if busy:return
 busy=True
 try:
  assert time.monotonic()-began<1700,'Check timeout'
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:
  u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
 except Exception:
  report['ok']=False;report['error']=traceback.format_exc();save();u.log_error(report['error'])
  if failed:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
  else:failed=True;steps=finish();deadline=time.monotonic()+next(steps)
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
