"""Driving regression for the real logging hollow, including rendered grid depth."""
import unreal as u,math,json,time
class DepthProbe:
 def __init__(self,world,x,y,z):
  self.world=world;self.n=128;self.frames={}
  self.actor=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.SceneCapture2D,u.Transform(location=u.Vector(x,y,z+1400),rotation=u.Rotator(pitch=-90)),'LidarFloraDepth')
  self.cc=self.actor.capture_component2d;self.rt=u.RenderingLibrary.create_render_target2d(world,self.n,self.n,u.TextureRenderTargetFormat.RTF_RGBA32F)
  for k,v in dict(texture_target=self.rt,capture_every_frame=False,capture_on_movement=False,projection_type=u.CameraProjectionMode.ORTHOGRAPHIC,ortho_width=1000.,capture_source=u.SceneCaptureSource.SCS_SCENE_DEPTH,primitive_render_mode=u.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST).items():self.cc.set_editor_property(k,v)
  self.visual=u.GameplayStatics.get_all_actors_of_class(world,u.GTMudRunnerVisual)[0]
 def measure(self,label):
  self.cc.clear_show_only_components()
  self.components=[c for c in self.visual.get_components_by_class(u.ProceduralMeshComponent) if c.get_name().startswith(('NativeVisualGrid','NativeVisualTile_'))]
  for c in self.components:self.cc.show_only_component(c)
  self.cc.capture_scene();yield .5
  values=[p.r for p in u.RenderingLibrary.read_render_target_raw_pixel_area(self.world,self.rt,0,0,self.n,self.n,False)]
  assert len(values)==self.n*self.n
  assert sum(math.isfinite(v) and 100<v<3000 for v in values)>len(values)*.95,'Rendered deformation grid is missing at the probe'
  self.frames[label]=values
 def result(self):
  changes=[b-a for a,b in zip(self.frames['before'],self.frames['after']) if 100<a<3000 and 100<b<3000]
  return dict(max_depression_cm=max(changes),max_raise_cm=-min(changes),pixels_changed_over_1cm=sum(abs(v)>1 for v in changes),scope='Actual SceneDepth of following native visual grid/tile components; excludes vegetation, water, tread ribbons and vehicle')
 def close(self):
  self.cc.clear_show_only_components();self.cc.texture_target=None;self.actor.destroy_actor();self.components=None;self.visual=self.cc=self.rt=self.actor=None

def run(ns,route,g):
 world,car,pc=ns['world'],ns['car'],ns['pc'];settle=ns['settle'];capture=ns['capture'];T=ns['trial'];report=ns['report'];save=ns['save'];OUT=ns['OUT']
 report['drive']={'ok':False};r=report['drive'];surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0]
 pts=route['points_cm'];cum=[0.]
 for a,b in zip(pts,pts[1:]):cum.append(cum[-1]+math.dist(a,b))
 s0=20400.;end=22400.;x,y,yaw=T.at(route,s0*.01);mesh=car.get_component_by_class(u.SkeletalMeshComponent);mv=car.get_chaos_movement()
 car.reset_driving_inputs();car.set_actor_location_and_rotation(u.Vector(x,y,g.height(x,y)+100),u.Rotator(yaw=yaw),False,True);mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector());mv.set_handbrake_input(True)
 yield from settle(7)
 sx,sy,syaw=T.at(route,214);probe=DepthProbe(world,sx,sy,g.height(sx,sy));yield from probe.measure('before')
 r['before_transect']=ns['rd1_transect'](surface,sx,sy,syaw)
 xcam,ycam,_=T.at(route,209,-1.3);view=[xcam,ycam,g.height(xcam,ycam)+220];target=[sx,sy,g.height(sx,sy)+10]
 yield from capture('drive_fresh',view,target)
 car.get_drivetrain().set_low_range(True);car.get_drivetrain().set_diff_lock(True)
 now=u.GameplayStatics.get_time_seconds(world);ns['drive_cmd']=dict(pts=pts,cum=cum,s=s0,max_off=0.,t0=now,t_last=now-1,trace=[]);ns['drive_on']=True
 mv.set_handbrake_input(False);mv.set_brake_input(0)
 until=time.monotonic()+180
 while ns['drive_cmd']['s']<end:
  if u.GameplayStatics.get_time_seconds(world)-now>50:break
  assert time.monotonic()<until;yield .1
 ns['drive_on']=False;car.reset_driving_inputs();mv.set_handbrake_input(True);yield from settle(2)
 r['station_end_m']=ns['drive_cmd']['s']*.01;r['off_road_max_cm']=ns['drive_cmd']['max_off'];r['trace']=ns['drive_cmd']['trace']
 r['after_transect']=ns['rd1_transect'](surface,sx,sy,syaw);r['visual_binding']=ns['rd1_visual_report'](world);r['tile_binding']=ns['rd1_tile_report'](world,sx,sy)
 yield from probe.measure('after');r['rendered_depth']=probe.result();(OUT/'rendered-depth.json').write_text(json.dumps(probe.frames));probe.close();probe=None
 yield from capture('drive_ruts',view,target);save()
 assert r['station_end_m']>=223,'Vehicle did not complete the real 20m logging-road drive'
 assert r['off_road_max_cm']<230,'Driving left the wheel corridor'
 assert r['after_transect']['max_compression_cm']>r['before_transect']['max_compression_cm']+.1,'No new native soil compression'
 assert r['rendered_depth']['max_depression_cm']>1 and r['rendered_depth']['pixels_changed_over_1cm']>25,'No visible ground deformation in rendered depth'
 r['ok']=True;save()
