"""Reuse the ground review setup; add deterministic animation and CSV A/B windows."""
from pathlib import Path
import ast
R=Path('C:/GrandTour')
# Execute only the existing runtime builder, never its write/exec footer.
p=R/'Art/Unreal/trial_flora_ground_patches.py';tree=ast.parse(p.read_text());tree.body=tree.body[:-3]
builder={};exec(compile(tree,str(p),'exec'),builder);text=builder['text']
def replace(a,b):
 global text
 assert a in text,a
 text=text.replace(a,b)
replace('from flora_pine_brush_baseline import verify','from flora_motion_baseline import verify')
replace('import flora_ground_patches as ground','import flora_ground_patches as ground\nimport flora_motion as motion\nimport shutil\nsys.path.insert(0,str(R/"Art/tools"))\nfrom benmore_profile_metrics import analyse')
replace('O=ground.O','O=motion.O')
replace('GT_GROUND_PATCH_STAGE','GT_FLORA_MOTION_STAGE')
replace('L.load_level(ground.BASE)','L.load_level(motion.BASE)')
replace('ground.geometry(world)','motion.geometry(world)')
replace('ground.install(world)','motion.install(world)')
replace('ground.MAP','motion.MAP')
replace(" if stage!='verify':\n  motion.install(world)", " if stage!='verify' and not E.does_asset_exist(motion.MAP):\n  motion.install(world)")
replace("root=R/'Content'/ground.D", "root=R/'Content'/motion.D")
replace(" origins={(a,c.get_name(),i):m.get_path_name() for a,c,i,m,role in wood.slots(world)}", " origins={(a,c.get_name(),i):m.get_path_name() for a,c,i,m,role in wood.slots(world)}\n wind_origins={(a,c.get_name(),i):m.get_path_name() for a,c,i,m in motion.slots(world)}")
replace(" assert {(a,c.get_name(),i):m.get_path_name() for a,c,i,m,role in wood.slots(world)}==origins",'''
 for a,c,i,m,role in wood.slots(world):
  source=u.load_asset(origins[(a,c.get_name(),i)])
  if m.get_path_name().startswith(motion.D+'/M_Wind_'):assert motion.signature(m)==motion.signature(source)
  else:assert m==source
 for a,c,i,m in motion.slots(world):
  assert m.get_path_name().startswith(motion.D+'/M_Wind_')
  assert motion.signature(m)==motion.signature(u.load_asset(E.get_metadata_tag(m,'FloraMotionSource')))
 leaves=motion.leaf_components(world);assert len(leaves)==1
 assert leaves[0].get_instance_count()==motion.CFG['leaf_count']
 assert not leaves[0].get_editor_property('cast_shadow')
 report['bounded_falling_leaves']={'instances':leaves[0].get_instance_count(),'cast_shadows':False,'collision':str(leaves[0].get_collision_enabled()),'cull_cm':motion.CFG['leaf_cull_cm'],'cpu_tick':False}
''')
replace("report['foliage_bark_rock_materials_preserved']=True", "report['foliage_surface_outputs_bark_and_rocks_preserved']=True")
replace("cases=[(name,row,1.) for name in ground.PROFILES] if stage=='candidate' else [(ground.CFG['selected'],row,1.)]", "cases=[(name,row,1.) for name in ('baseline','wind','both')] if stage=='candidate' else [('both',row,1.)]")
marker=" assert all(abs(v-ground.SELECTED)<1e-5 for v in report['saved_ground_strength'])"
replace(marker,marker+'''
 live=[];component_motion_defaults={};component_shadow_defaults={}
 for a,c,i,m in motion.slots(world):
  original=u.load_asset(wind_origins[(a,c.get_name(),i)]);assert original
  component_motion_defaults[c.get_path_name()]={k:c.get_editor_property(k) for k in ('evaluate_world_position_offset','world_position_offset_writes_velocity')}
  component_shadow_defaults[c.get_path_name()]=c.get_editor_property('shadow_cache_invalidation_behavior')
  mid=c.create_dynamic_material_instance(i,m);assert mid
  assert abs(mid.get_scalar_parameter_value('FloraTimeOverride')+1.)<1e-5,(a,c.get_name(),m.get_path_name(),mid.get_scalar_parameter_value('FloraTimeOverride'))
  live.append((c,i,original,mid))
 leaves=motion.leaf_components(world);leafmids=[c.create_dynamic_material_instance(0,c.get_material(0)) for c in leaves]
 assert live and all(leafmids)
 def configure(case,t=-1.):
  for c,i,original,mid in live:
   canopy=c.static_mesh.get_name() in ('SM_Exact_tree','SM_Exact_pine_f002')
   usewind=case not in ('baseline','leaves_only') and (case!='canopy_only' or canopy) and (case!='understory_only' or not canopy)
   c.set_editor_property('shadow_cache_invalidation_behavior',u.ShadowCacheInvalidationBehavior.STATIC if 'static' in case else component_shadow_defaults[c.get_path_name()])
   c.set_material(i,mid if usewind else original)
   defaults=component_motion_defaults[c.get_path_name()]
   c.set_evaluate_world_position_offset(False if case=='wind_disabled' else defaults['evaluate_world_position_offset'])
   c.set_editor_property('world_position_offset_writes_velocity',False if 'no_velocity' in case else defaults['world_position_offset_writes_velocity'])
   c.set_editor_property('world_position_offset_disable_distance',motion.CFG['wind_disable_cm'] if usewind else 0)
   mid.set_scalar_parameter_value('FloraTimeOverride',t)
  for c in leaves:c.set_visibility(case in ('both','both_static','leaves_only'))
  for mid in leafmids:mid.set_scalar_parameter_value('FloraTimeOverride',t)
 report['wind_material_slots']=len(live)
 report['component_motion_defaults']=component_motion_defaults
 report['component_shadow_defaults']={k:str(v) for k,v in component_shadow_defaults.items()}
''')
a=text.index(' for name,row,enabled in cases:');b=text.index(" assert report['candidate_hashes']==",a)
text=text[:a]+'''
 report['simulation_paused_for_comparison']=True
 if stage=='diagnose':cases=[]
 views=[(n,p,t) for n,p,t in views if n in ('drive','bank','canopy','valley')]
 views.append(('leaves',[-1250,-700,180],[-400,400,550]))
 for name,row,enabled in cases:
  configure(name,4.)
  report['cases'].append({'name':name,'wind':name!='baseline','falling_leaves':name=='both'})
  for view,pos,target in views:
   look(pos,target);yield from shot(stage+'_'+name+'_'+view)
 # Controlled-time sequence: 4 seconds at 12 animation samples per second.
 # Rendering time is unrelated to playback rate and is never reported as FPS.
 configure('both',4.)
 look([-1250,-700,180],[-400,400,550]);yield from frames(80)
 report['animation_times']=[]
 for frame in range(0 if stage=='diagnose' else 48):
  t=4.+frame/12.;configure('both',t);yield from frames(2)
  yield from shot(stage+'_animation_%03d'%frame,0)
  report['animation_times'].append(t)
 if stage=='verify':
  report['camera_move_samples']=[]
  for frame in range(48):
   alpha=frame/47.;t=8.+frame/12.;configure('both',t)
   pos=[-1250.+alpha*400.,-700.+alpha*200.,180.]
   look(pos,[-400,400,550]);yield from frames(2)
   yield from shot(stage+'_move_%03d'%frame,0)
   report['camera_move_samples'].append({'time':t,'position':pos})
 # Actual continuously running game/shader time for performance captures.
 if stage in ('candidate','diagnose','verify'):
  report['profile_runs']=[];csvdir=R/'Saved/Profiling/CSV'
  look([-1250,-700,180],[-400,400,550]);u.GameplayStatics.set_game_paused(world,False)
  cmd('r.GPUCsvStatsEnabled 1');yield 5
  order=('baseline','wind','both','both','wind','baseline') if stage=='candidate' else ('baseline','wind','wind_disabled','wind_no_velocity','canopy_only','understory_only','leaves_only','baseline')
  if stage=='verify':order=('baseline','leaves_only','leaves_only','baseline')
  if stage=='diagnose' and os.environ.get('GT_FLORA_MOTION_PROFILE_CASES'):order=tuple(os.environ['GT_FLORA_MOTION_PROFILE_CASES'].split(','))
  for index,case in enumerate(order):
   configure(case);yield 6
   before=set(csvdir.glob('*.csv'));cmd('csvprofile start');yield motion.CFG['profile_seconds'];cmd('csvprofile stop');yield 4
   created=set(csvdir.glob('*.csv'))-before;assert len(created)==1,created
   src=created.pop();dest=O/(stage+'_profile_%02d_%s.csv'%(index,case));shutil.copy2(src,dest)
   report['profile_runs'].append({'case':case,'csv':str(dest),'analysis':analyse(dest)})
   save()
  report['profile_scope']='Fixed camera, PIE/offscreen, uncooked; no screenshots in timing windows. Relative A/B only, not sustained driving or Shipping 60 fps.'
  report['relative_performance_measured']=True
  u.GameplayStatics.set_game_paused(world,True)
 configure('both')
''' +text[b:]
replace("motion='48-frame move, 8 samples per candidate; not realtime performance'", "motion='48 deterministic animation samples over 4 seconds; separate CSV profiling uses continuous game time'")
runtime=Path('D:/GrandTourAssets/ReviewEvidence/FloraTrail/Motion/runtime.py');runtime.write_text(text)
exec(compile(text,str(runtime),'exec'),globals())
