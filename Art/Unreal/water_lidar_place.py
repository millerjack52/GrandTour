"""LP2: water that reads as water. Re-runnable after any Install/Polish.
1. The three domain surfaces carry their clone M_<name>Water (never a MID) on the component and the mesh.
2. The clones get the Waimeamea tannin look: parameters and the clone's own expressions only
   (same nodes, same samples, same cost). Every substitution matches any earlier value, so a
   second run re-applies the same numbers. Writes Place/water.json."""
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve()
exec(compile((ROOT/'Art/Unreal/install_lidar_place.py').read_text().split('def run():')[0],'<lidar-place-helpers>','exec'))
report=dict(ok=False,driving_tested=False)

def f3(v):return 'float3(%s)'%','.join(('%.5f'%x).rstrip('0').rstrip('.') if x else '0' for x in v)
# Photos 03-07 (Art/References/Waimeamea): tannin amber, clear over an orange-brown bed in the
# shallows, tea-dark mirror pools. Coefficients are SLW 1/cm along the view ray: ~40 cm of water
# seen at a slant keeps (.55,.25,.07) of the bed; 1.3 m is tea-dark.
LOOK=dict(
 iteration=3,
 sky_light=1.5,                   # owner's choice 2026-10-16 (saved 8.0; Benmore review 1.15); GTWeatherSubsystem takes the saved value as its base
 scalars=dict(WaterTurbidity=.10),
 rough=(.02,.12,.02),            # calm pool, riffle, floor (Benmore: .105,.17,.10)
 opacity=(.03,.10),              # lit film shallow, extra at depth (Benmore: .085,.09)
 colour=((.09,.055,.022),(.05,.03,.012)),          # shallow, deep film colour (Benmore: teal)
 scatter=((.00045,.00065,.00045),(.0030,.0024,.0012)),  # clear, turbid
 absorb=((.0045,.0105,.021),(.012,.024,.045)),          # clear, turbid (it.1 clear .0075,.0173,.033: bed too dim)
 behind=(1.0,.86,.66),           # SLW ColorScaleBehindWater: tannin stain on the bed seen through (it.1-2 1,.96,.90; Benmore .95,.98,.96)
 spec=(.25,.20),                 # near, far reflectance scale; .25 is water's F0 .02 (Benmore: .32,.20)
)
def subs(L):
 r0,r1,rmin=L['rough'];o0,o1=L['opacity'];(cs,cd),(sc,st),(ac,atb)=L['colour'],L['scatter'],L['absorb']
 return [
  ('rough',r'Rough=clamp\(lerp\([\d.]+,[\d.]+,riffle\)\+foam\*\.48,[\d.]+,\.65\)',f'Rough=clamp(lerp({r0},{r1},riffle)+foam*.48,{rmin},.65)'),
  ('opacity',r'Opacity=saturate\(lerp\([\d.]+,\.14,Turbidity\)\+smoothstep\(\.08,1\.1,depth\)\*lerp\([\d.]+,\.14,Turbidity\)',f'Opacity=saturate(lerp({o0},.14,Turbidity)+smoothstep(.08,1.1,depth)*lerp({o1},.14,Turbidity)'),
  ('colour',r'float3 colour=lerp\(float3\([^)]*\),float3\([^)]*\),smoothstep\(\.12,\.8,depth\)\)',f'float3 colour=lerp({f3(cs)},{f3(cd)},smoothstep(.12,.8,depth))'),
  ('scatter',r'Scatter=lerp\(lerp\(float3\([^)]*\),float3\([^)]*\),Turbidity\)',f'Scatter=lerp(lerp({f3(sc)},{f3(st)},Turbidity)'),
  ('absorb',r'Absorb=lerp\(lerp\(float3\([^)]*\),float3\([^)]*\),Turbidity\)',f'Absorb=lerp(lerp({f3(ac)},{f3(atb)},Turbidity)'),
  ('spec',r'Spec=lerp\(\.002,lerp\([\d.]+,[\d.]+,smoothstep\(35,160,dist\)\),wetEdge\)',f'Spec=lerp(.002,lerp({L["spec"][0]},{L["spec"][1]},smoothstep(35,160,dist)),wetEdge)'),
  # Surface threads (the material's white-water term on calm flow) only where the riffle gate is open.
  ('threads_on_riffles',r'float foam=\(flow\.a\*bubble\*\.34\+surfaceThreads\*\.72\)\*flowing\*nearFade[^;]*','float foam=(flow.a*bubble*.34+surfaceThreads*.72)*flowing*nearFade*riffle'),
 ]

def apply_look(m):
 rows={};main=None
 for e in mel.get_material_expressions(m):
  if isinstance(e,u.MaterialExpressionCustom) and 'Scatter' in [str(o.get_editor_property('output_name')) for o in e.get_editor_property('additional_outputs')]:
   assert main is None,'two water programs';main=e
  if isinstance(e,u.MaterialExpressionScalarParameter):
   name=str(e.get_editor_property('parameter_name'))
   if name in LOOK['scalars']:rows[name]=dict(before=e.get_editor_property('default_value'),after=LOOK['scalars'][name]);e.set_editor_property('default_value',LOOK['scalars'][name])
 assert main,'no SLW program in '+m.get_name()
 slw=next(e for e in mel.get_material_expressions(m) if isinstance(e,u.MaterialExpressionSingleLayerWaterMaterialOutput))
 behind=[x for x in mel.get_inputs_for_material_expression(m,slw) if isinstance(x,u.MaterialExpressionConstant3Vector)]
 assert len(behind)==1,'ColorScaleBehindWater constant';c=behind[0].get_editor_property('constant')
 rows['ColorScaleBehindWater']=dict(before=[round(c.r,4),round(c.g,4),round(c.b,4)],after=list(LOOK['behind']));behind[0].set_editor_property('constant',u.LinearColor(*LOOK['behind'],1))
 code=str(main.get_editor_property('code'))
 for key,pattern,new in subs(LOOK):
  found=re.findall(pattern,code);assert len(found)==1,(m.get_name(),key,len(found))
  rows[key]=dict(before=found[0],after=new);code=re.sub(pattern,lambda _:new,code)
 main.set_editor_property('code',code)
 assert not mel.recompile_material(m),m.get_name();assert assets.save_loaded_asset(m)
 return rows

def run():
 before=protected();backup=ROOT/'Saved/LidarStudyBackups'/('Water-'+str(time.time_ns()));shutil.copytree(ROOT/'Content/GrandTour/ArtTests/LidarStudy',backup);report['backup']=str(backup);prune_backups(backup.parent)
 assert les.load_level(LEVEL);refs=actors.get_all_level_actors();sheet=next(a for a in refs if isinstance(a,u.GTWaterSheet) and not a.get_editor_property('mud_initial_domain'))
 import lidar_logging_trial
 repaired=lidar_logging_trial.repair_legacy_polish(refs,sheet)
 report['logging_pool_repair']=repaired
 surfaces=list(sheet.get_editor_property('domain_surfaces'));assert len(surfaces)==3
 report['binding']={};level_changed=bool(repaired)
 for a in surfaces:
  c=a.static_mesh_component;mesh=c.static_mesh;name=mesh.get_name()[3:-5];clone=u.load_asset(BASE+f'/M_{name}Water');assert clone
  cur=c.get_material(0);row=dict(component_before=cur.get_path_name() if cur else None,mesh_before=mesh.get_material(0).get_path_name() if mesh.get_material(0) else None)
  # An editor-world bind (PreviewWaterAt) leaves a MID outered to the sheet; never save one.
  if cur!=clone:c.set_material(0,clone);level_changed=True
  if mesh.get_material(0)!=clone:mesh.set_material(0,clone);assert assets.save_loaded_asset(mesh)
  row.update(component_after=c.get_material(0).get_path_name(),mesh_after=mesh.get_material(0).get_path_name());report['binding'][a.get_actor_label()]=row
 # Sky light: the weather subsystem captures the saved intensity at begin play and scales it, so the
 # level actor is the source of truth; set it through the property system so the level saves it.
 skies=[a for a in refs if isinstance(a,u.SkyLight)];assert len(skies)==1,len(skies);sky=skies[0].light_component
 report['sky_light']=dict(before=sky.get_editor_property('intensity'),target=LOOK['sky_light'])
 if abs(report['sky_light']['before']-LOOK['sky_light'])>1e-3:sky.set_editor_property('intensity',LOOK['sky_light']);level_changed=True
 report['sky_light']['after']=sky.get_editor_property('intensity')
 yield 1
 report['look']=dict(iteration=LOOK['iteration'],materials={})
 for name in ['MappedPond','AccessPond','River']:
  report['look']['materials']['M_'+name+'Water']=apply_look(u.load_asset(BASE+f'/M_{name}Water'));(OUT/'water.json').write_text(json.dumps(report,indent=2,default=str));yield 1
 if level_changed:assert les.save_current_level()
 report['level_saved']=level_changed
 for a in surfaces:assert isinstance(a.static_mesh_component.get_material(0),u.Material),a.get_actor_label()
 assert protected()==before;report.update(ok=True,protected_unchanged=len(before));(OUT/'water.json').write_text(json.dumps(report,indent=2,default=str))
 refs=sheet=surfaces=a=c=mesh=clone=cur=skies=sky=None;gc.collect();yield 2;les.load_level('/Engine/Maps/Entry');yield 4

steps=run();deadline=0;began=time.monotonic()
def tick(dt):
 global deadline,busy,steps
 if busy:return
 busy=True
 try:
  assert time.monotonic()-began<1500,'Water timeout'
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
 except Exception:
  report['error']=traceback.format_exc();(OUT/'water.json').write_text(json.dumps(report,indent=2,default=str));u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
