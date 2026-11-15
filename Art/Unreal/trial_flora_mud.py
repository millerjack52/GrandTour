"""Four reversible road-material candidates under saved FloraTrail pine lighting."""
import unreal as u,json,sys,time,traceback,math,os,hashlib
from pathlib import Path
R=Path('C:/GrandTour');sys.path[:0]=[str(R/'Art/Unreal'),str(R/'Art')]
from flora_mud_trial_baseline import verify
import flora_mud_trial_materials as mat
O=R/'Art/Export/FloraTrail/MudTrial';D=mat.D;P='/Game/GrandTour/ArtTests/FloraTrail/PineTrial/L_FloraTrail_Pine'
stage=os.environ.get('GT_MUD_TRIAL_STAGE','screen');rows=json.loads((O/'sources.json').read_text())['candidates']
L=u.get_editor_subsystem(u.LevelEditorSubsystem);A=u.get_editor_subsystem(u.EditorActorSubsystem);E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
report={'ok':False,'stage':stage,'images':[],'cases':[],'performance_verified':False};state={'busy':False,'due':0,'frame':0};world=pc=car=camera=None
def save():(O/(stage+'-report.json')).write_text(json.dumps(report,indent=2))

def trial_hashes():
 root=R/'Content/GrandTour/ArtTests/FloraTrail/MudTrial'
 return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
def cmd(s):u.SystemLibrary.execute_console_command(world,s,pc)
def frames(n):
 end=state['frame']+n
 while state['frame']<end:yield 0
def shot(name,settle=100,check_camera=True):
 yield from frames(settle)
 actual=u.GameplayStatics.get_player_camera_manager(world,0).get_camera_location();expected=camera.get_actor_location()
 if check_camera:assert (actual-expected).length()<2,('Camera did not update',actual,expected)
 p=O/(name+'.png');stamp=time.time();cmd('Shot filename="'+p.as_posix()+'" -nosuffix');deadline=time.monotonic()+45
 while not p.exists() or p.stat().st_mtime<stamp:
  assert time.monotonic()<deadline,name;yield .2
 h=p.read_bytes()[:24];report['images'].append({'name':name,'size':[int.from_bytes(h[16:20],'big'),int.from_bytes(h[20:24],'big')]});save()
def centre(x):return 530*math.sin((x+2200)/1050)-150
def look(pos,target):
 camera.set_actor_location(u.Vector(*pos),False,True);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(*pos),u.Vector(*target)),False)
def drive_check(world,pc,car,surface,shot,report,save):
    def centre(x):return 530*math.sin((x+2200)/1050)-150
    probes=[u.Vector2D(x,centre(x)+off) for x in range(-2000,2350,100) for off in (-85,85)]
    before=[surface.sample_surface(p).surface_delta_cm for p in probes]
    row={'samples':[],'ok':False};report['driving']=row;save()
    car.set_actor_hidden_in_game(False);pc.set_view_target_with_blend(car,0)
    u.GameplayStatics.set_game_paused(world,False)
    started=u.GameplayStatics.get_time_seconds(world);wall=time.monotonic();captured=set();last=-1
    while car.get_actor_location().x<2370:
        move=car.get_chaos_movement();move.set_handbrake_input(False);move.set_throttle_input(.52);move.set_brake_input(0)
        p=car.get_actor_location();tx=min(p.x+220,2700);ty=centre(tx)
        target=math.degrees(math.atan2(ty-p.y,tx-p.x));delta=(target-car.get_actor_rotation().yaw+180)%360-180
        car.set_raw_steer(max(-.75,min(.75,delta/32)))
        elapsed=u.GameplayStatics.get_time_seconds(world)-started
        assert elapsed<75 and time.monotonic()-wall<300,'Traversal timed out'
        assert abs(p.y-centre(p.x))<260,'Vehicle left the road'
        if elapsed-last>.15:
            last=elapsed
            row['samples'].append({'time':elapsed,'position':p.to_tuple(),'water_cm':[w.water_depth_m*100 for w in car.get_traction().wheels]})
        for tag,x in [('entry',-2100),('puddles',-1000),('middle',0),('flooded_dip',710),('exit',2200)]:
            if p.x>x and tag not in captured:
                captured.add(tag);yield from shot('saved_driving_'+tag,settle=0,check_camera=False)
        yield 0
    car.reset_driving_inputs();car.get_chaos_movement().set_handbrake_input(True)
    row['travel_cm']=sum(math.dist(a['position'][:2],b['position'][:2]) for a,b in zip(row['samples'],row['samples'][1:]))
    row['max_water_cm']=max(v for s in row['samples'] for v in s['water_cm'])
    after=[surface.sample_surface(p).surface_delta_cm for p in probes]
    row['max_height_change_cm']=max(abs(a-b) for a,b in zip(before,after))
    row['surface_report']=surface.get_surface_report()
    sheet=u.GameplayStatics.get_all_actors_of_class(world,u.GTWaterSheet)[0]
    row['water_report']=sheet.mud_water_diagnostics()
    assert row['travel_cm']>4800 and row['max_water_cm']>8 and row['max_height_change_cm']>.2,row
    assert 'native_shader=1' in row['surface_report'] and 'bed_updates=0 ' not in row['water_report']
    row['ok']=True;row['note']='Continuous physical traversal with captures; not a reset regression or a sustained 60 fps test.';save()
    u.GameplayStatics.set_game_paused(world,True)


def run():
 global world,pc,car,camera
 verify()
 if stage=='verify':report['trial_hashes_before']=trial_hashes()
 assert L.load_level(P);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 for c in json.loads((R/'Art/flora_trail_settings.json').read_text())['console']:cmd(c)
 yield 8
 visual=next(a for a in A.get_all_level_actors() if isinstance(a,u.GTMudRunnerVisual));original=visual.material;tread=visual.track_material
 report['original_ground']=original.get_path_name();report['original_tread']=tread.get_path_name()
 report['source_graph']=[{'name':n.get_name(),'desc':str(n.get_editor_property('desc')),'type':n.get_class().get_name(),'code':str(n.get_editor_property('code')) if isinstance(n,u.MaterialExpressionCustom) else None} for n in M.get_material_expressions(original)]
 if stage=='screen':
  ground=mat.build(original,rows[0],'ground')
  textures={r['id']:{role:mat.texture(r,role) for role in ('color','normal','height','roughness')} for r in rows}
  target=D+'/L_FloraTrail_Mud';exists=E.does_asset_exist(target)
  if exists:
   assert L.load_level(target);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();visual=next(a for a in A.get_all_level_actors() if isinstance(a,u.GTMudRunnerVisual))
  visual.set_editor_property('material',ground)
  report['saved_trial_map']=target
  assert L.save_current_level() if exists else u.EditorLoadingAndSavingUtils.save_map(world,target)
  selected=rows;cases=[('baseline',rows[0],0.)]+[(r['id'],r,1.) for r in rows]
 else:
  cfg=json.loads((R/'Art/flora_mud_trial_settings.json').read_text());ids=cfg['review_candidates'] if stage=='native' else [cfg['selected']];selected=[r for r in rows if r['id'] in ids];assert selected
  assert L.load_level(D+'/L_FloraTrail_Mud');world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
  if stage=='verify':
   textures={r['id']:{role:u.load_asset(D+'/Textures/T_'+r['id']+'_'+role+'_native') for role in ('color','normal','height','roughness')} for r in selected}
   instances={r['id']:u.load_asset(D+'/MI_MudTrial_'+r['id']) for r in selected}
   visual=next(a for a in A.get_all_level_actors() if isinstance(a,u.GTMudRunnerVisual));assert visual.material==instances[cfg['selected']];report['saved_material']=visual.material.get_path_name()
  else:
   textures={r['id']:{role:mat.texture(r,role,True) for role in ('color','normal','height','roughness')} for r in selected}
   instances={r['id']:mat.instance(r,textures) for r in selected}
  report['instances']={k:v.get_path_name() for k,v in instances.items()}
  if stage=='saved':
   visual=next(a for a in A.get_all_level_actors() if isinstance(a,u.GTMudRunnerVisual));visual.set_editor_property('material',instances[cfg['selected']]);assert L.save_current_level()
   assert L.load_level('/Engine/Maps/Entry');assert L.load_level(D+'/L_FloraTrail_Mud');world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
   visual=next(a for a in A.get_all_level_actors() if isinstance(a,u.GTMudRunnerVisual));assert visual.material.get_path_name()==instances[cfg['selected']].get_path_name();report['saved_material']=visual.material.get_path_name()
  cases=([('baseline',selected[0],0.)] if stage=='native' else [])+[(r['id']+'_'+stage,r,1.) for r in selected]
 # Wait for asynchronously imported/resident textures before any quality judgement.
 cmd('r.Streaming.FullyLoadUsedTextures 1');deadline=time.monotonic()+180
 for r in selected:
  for role,t in textures[r['id']].items():
   expected=1024 if stage=='screen' else r['files'][role]['size'][0]
   while t.blueprint_get_size_x()!=expected:
    assert time.monotonic()<deadline,(r['id'],role,t.blueprint_get_size_x(),expected);yield .5
 report['texture_sizes']={k:{role:[t.blueprint_get_size_x(),t.blueprint_get_size_y()] for role,t in ts.items()} for k,ts in textures.items()}
 report['texture_import']={k:{role:{'asset':t.get_path_name(),'srgb':t.get_editor_property('srgb'),'compression':str(t.get_editor_property('compression_settings')),'flip_green':t.get_editor_property('flip_green_channel'),'revision':E.get_metadata_tag(t,'MudTrialSourceRevision')} for role,t in ts.items()} for k,ts in textures.items()};save()
 yield 8;u.GTPlayWindowLibrary.request_play_in_new_window(1600,900);yield 12
 world=u.EditorLevelLibrary.get_game_world();pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car();car.disable_input(pc);car.get_chaos_movement().set_handbrake_input(True);car.set_actor_hidden_in_game(True)
 for c in ['DisableAllScreenMessages','r.MotionBlurQuality 0','r.ScreenPercentage 100','r.DynamicRes.OperationMode 0','r.VSync 0','t.MaxFPS 0','r.Streaming.FullyLoadUsedTextures 1']:cmd(c)
 visual=u.GameplayStatics.get_all_actors_of_class(world,u.GTMudRunnerVisual)[0];surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0]
 grid=next(c for c in visual.get_components_by_class(u.ProceduralMeshComponent) if c.get_name()=='NativeVisualGrid')
 mids=[grid.get_material(0)];assert all(isinstance(m,u.MaterialInstanceDynamic) for m in mids)
 report['live_dynamic_materials']=[m.get_path_name() for m in mids]
 camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(location=u.Vector()),'MudTrialCamera');camera.camera_component.set_field_of_view(65);camera.camera_component.set_editor_property('constrain_aspect_ratio',False);pc.set_view_target_with_blend(camera,0);cmd('ShowHUD');yield 10
 def height(x,y):return surface.contact_height_cm(u.Vector2D(x,y),False)
 x=-1850;y=centre(x);z=height(x,y);target_x=-500;target_y=centre(target_x)
 views=[('drive',[x,y,z+150],[target_x,target_y,height(target_x,target_y)+60]),('close',[-1500,centre(-1500)-180,height(-1500,centre(-1500))+150],[-1200,centre(-1200),height(-1200,centre(-1200))]),('distance',[-2750,centre(-2750),height(-2750,centre(-2750))+150],[0,centre(0),height(0,centre(0))+40]),('context',[-2350,-470,210],[900,150,640])]
 report['views']=[{'name':n,'position':p,'target':t} for n,p,t in views];report['surface_before']=surface.get_surface_report()
 # The same two deterministic tyre strokes for every texture, with native soil response.
 for off in (-78,78):
  a=u.Vector2D(-1650,centre(-1650)+off);b=u.Vector2D(-450,centre(-450)+off)
  surface.apply_review_soil_stroke(a,b,28,8,.35)
 yield 3;pc.set_tickable_when_paused(True);pc.set_editor_property('should_perform_full_tick_when_paused',True);camera.set_tickable_when_paused(True);u.GameplayStatics.set_game_paused(world,True)
 report['simulation_paused_for_comparison']=True
 report['review_strokes']='Two native 28 cm wide, 8 cm depth requests, slip .35; identical live state for all textures. Not a driving regression.'
 for name,row,enabled in cases:
  for mid in mids:
   if stage not in ('saved','verify'):mat.bind(mid,row,textures,enabled)
   for param,role in [('Colour','color'),('Normal','normal'),('Roughness','roughness'),('Height','height')]:assert mid.get_texture_parameter_value('MudTrial'+param)==textures[row['id']][role]
   assert abs(mid.get_scalar_parameter_value('MudTrialTileCm')-row['tile_cm'])<.01
   assert mid.get_scalar_parameter_value('MudTrialEnabled')==enabled
  report['cases'].append({'name':name,'candidate':row['id'],'enabled':enabled,'tile_cm':row['tile_cm'],'relief_cm':2.8,'resolution':'1K common screening' if stage=='screen' else 'native source'});yield 3
  for view,pos,target in views:
   look(pos,target);yield from shot(stage+'_'+name+'_'+view)
  # A continuous short forward move at 150 cm above the deformation reference.
  for i in range(48):
   xx=-1900+i*5;yy=centre(xx);look([xx,yy,height(xx,yy)+150],[xx+1500,centre(xx+1500),height(xx+1500,centre(xx+1500))+60]);yield from frames(1)
   if i%6==0:yield from shot(stage+'_'+name+'_motion_%02d'%i,0)
 if stage=='saved':
  yield from drive_check(world,pc,car,surface,shot,report,save)
 report['surface_after']=surface.get_surface_report();report['visual_after']=visual.get_research_report()
 u.GameplayStatics.set_game_paused(world,False);yield 2
 pc.set_view_target_with_blend(car,0);u.EditorLevelLibrary.editor_end_play();yield 4
 verify()
 if stage=='verify':
  after=trial_hashes();assert report['trial_hashes_before']==after;report['trial_packages_unchanged']=True
 report.update(ok=True,protected_unchanged=True,motion='48-frame move, 8 samples per candidate; not realtime performance');save()
 assert L.load_level('/Engine/Maps/Entry');world=pc=car=camera=None;yield 3
def close():
 # AssetTools is a UObject held by the imported helper module, beyond script globals.
 # Release it while the engine is alive, before Python module teardown.
 mat.T=None
 for key,value in list(globals().items()):
  if not key.startswith('__') and key not in ('u','time'):globals()[key]=None
 value=None
 import gc
 gc.collect();u.SystemLibrary.collect_garbage();globals()['quit_at']=time.monotonic()+3
 def shutdown(dt):
  if time.monotonic()>quit_at:u.unregister_slate_post_tick_callback(quit_handle);u.EditorPythonScripting.set_keep_python_script_alive(False);u.SystemLibrary.quit_editor()
 globals()['quit_handle']=u.register_slate_post_tick_callback(shutdown)
steps=run()
def tick(dt):
 global steps
 if state['busy']:return
 state['busy']=True;state['frame']+=1
 try:
  if time.monotonic()>=state['due']:state['due']=time.monotonic()+next(steps)
 except StopIteration:steps=None;u.unregister_slate_post_tick_callback(handle);close()
 except Exception:
  report['error']=traceback.format_exc();save();u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);close()
 finally:
  if state is not None:state['busy']=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
