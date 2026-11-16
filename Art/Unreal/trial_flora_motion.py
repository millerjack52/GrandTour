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
replace("root=R/'Content'/ground.D", "root=R/'Content'/motion.D")
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
 live=[]
 for a,c,i,m in motion.slots(world):
  original=u.load_asset(E.get_metadata_tag(m,'FloraMotionSource'));assert original
  mid=c.create_dynamic_material_instance(i,m);assert mid
  assert abs(mid.get_scalar_parameter_value('FloraTimeOverride')+1.)<1e-5
  live.append((c,i,original,mid))
 leaves=motion.leaf_components(world);leafmids=[c.create_dynamic_material_instance(0,c.get_material(0)) for c in leaves]
 assert live and all(leafmids)
 def configure(case,t=-1.):
  for c,i,original,mid in live:
   c.set_material(i,original if case=='baseline' else mid)
   c.set_editor_property('world_position_offset_disable_distance',0 if case=='baseline' else motion.CFG['wind_disable_cm'])
   mid.set_scalar_parameter_value('FloraTimeOverride',t)
  for c in leaves:c.set_visibility(case=='both')
  for mid in leafmids:mid.set_scalar_parameter_value('FloraTimeOverride',t)
 report['wind_material_slots']=len(live)
''')
a=text.index(' for name,row,enabled in cases:');b=text.index(" assert report['candidate_hashes']==",a)
text=text[:a]+'''
 report['simulation_paused_for_comparison']=True
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
 for frame in range(48):
  t=4.+frame/12.;configure('both',t);yield from frames(2)
  yield from shot(stage+'_animation_%03d'%frame,0)
  report['animation_times'].append(t)
 # Actual continuously running game/shader time for performance captures.
 if stage=='candidate':
  report['profile_runs']=[];csvdir=R/'Saved/Profiling/CSV'
  look([-1250,-700,180],[-400,400,550]);u.GameplayStatics.set_game_paused(world,False)
  cmd('csvGpuStats 1');yield 5
  for index,case in enumerate(('baseline','wind','both','both','wind','baseline')):
   configure(case);yield 6
   before=set(csvdir.glob('*.csv'));cmd('csvprofile start');yield motion.CFG['profile_seconds'];cmd('csvprofile stop');yield 4
   created=set(csvdir.glob('*.csv'))-before;assert len(created)==1,created
   src=created.pop();dest=O/('profile_%02d_%s.csv'%(index,case));shutil.copy2(src,dest)
   report['profile_runs'].append({'case':case,'csv':str(dest),'analysis':analyse(dest)})
   save()
  report['profile_scope']='Fixed camera, PIE/offscreen, uncooked; no screenshots in timing windows. Relative A/B only, not sustained driving or Shipping 60 fps.'
  u.GameplayStatics.set_game_paused(world,True)
 configure('both')
''' +text[b:]
replace("motion='48-frame move, 8 samples per candidate; not realtime performance'", "motion='48 deterministic animation samples over 4 seconds; separate CSV profiling uses continuous game time'")
runtime=Path('D:/GrandTourAssets/ReviewEvidence/FloraTrail/Motion/runtime.py');runtime.write_text(text)
exec(compile(text,str(runtime),'exec'),globals())
