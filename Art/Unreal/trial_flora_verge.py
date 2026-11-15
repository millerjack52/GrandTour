"""Fixed-camera comparison of the underlying terrain's woodland-floor response."""
from pathlib import Path
R=Path('C:/GrandTour');source=R/'Art/Unreal/trial_flora_mud.py';text=source.read_text()
changes={
 'from flora_mud_trial_baseline import verify':'from flora_verge_baseline import verify',
 'import flora_mud_trial_materials as mat':'import flora_mud_trial_materials as mat\nimport flora_verge_materials as verge',
 "O=R/'Art/Export/FloraTrail/MudTrial'":"O=R/'Art/Export/FloraTrail/VergeStudy'",
 "stage=os.environ.get('GT_MUD_TRIAL_STAGE','screen')":"stage=os.environ.get('GT_VERGE_STAGE','candidate')",
 "rows=json.loads((O/'sources.json').read_text())":"rows=json.loads((R/'Art/Export/FloraTrail/MudTrial/sources.json').read_text())",
}
for old,new in changes.items():assert text.count(old)==1,old;text=text.replace(old,new)
a=text.index(" if stage=='screen':");b=text.index(' # Wait for asynchronously',a)
text=text[:a]+'''
 row=next(r for r in rows if r['id']=='brown_mud_02');selected=[row]
 target=D+'/L_FloraTrail_Verge'
 exists=E.does_asset_exist(target)
 assert L.load_level(target if stage=='verify' or exists else D+'/L_FloraTrail_MudFlat');world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 surface=next(a for a in A.get_all_level_actors() if isinstance(a,u.GTLandscapeSurface));landscape=surface.landscape
 report['terrain_source']=landscape.landscape_material.get_path_name()
 if stage!='verify':
  source_material=u.load_asset('/Game/GrandTour/ArtTests/FloraDrive/M_FloraLandscape')
  report['terrain_source_graph']=[{'name':n.get_name(),'desc':str(n.get_editor_property('desc')),'code':str(n.get_editor_property('code')) if isinstance(n,u.MaterialExpressionCustom) else None} for n in M.get_material_expressions(source_material)]
  material=verge.build(source_material);landscape.set_editor_property('landscape_material',material);landscape.set_editor_property('use_dynamic_material_instance',True)
  for c in landscape.get_components_by_class(u.MeshComponent):
   for i in range(c.get_num_materials()):c.set_material(i,material)
  visual=next(a for a in A.get_all_level_actors() if isinstance(a,u.GTMudRunnerVisual));visual.set_editor_property('material',verge.mud_instance())
  assert L.save_current_level() if exists else u.EditorLoadingAndSavingUtils.save_map(world,target)
  assert L.load_level('/Engine/Maps/Entry');assert L.load_level(target);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
  surface=next(a for a in A.get_all_level_actors() if isinstance(a,u.GTLandscapeSurface));landscape=surface.landscape
 assert landscape.landscape_material.get_path_name()==verge.TARGET+'.M_VergeLandscape'
 visual=next(a for a in A.get_all_level_actors() if isinstance(a,u.GTMudRunnerVisual))
 assert visual.material.get_path_name()==D+'/MI_VergeMud.MI_VergeMud'
 report['saved_map']=target;report['saved_ground']=visual.material.get_path_name();report['saved_terrain']=landscape.landscape_material.get_path_name()
 assert surface.simulated_water.get_editor_property('surface_material_path')==D+'/M_WaterFlat.M_WaterFlat'
 original_parent=u.load_asset(D+'/M_MudTrial_Wet');new_parent=u.load_asset(D+'/M_VergeMud')
 for prop in (u.MaterialProperty.MP_WORLD_POSITION_OFFSET,u.MaterialProperty.MP_OPACITY_MASK):
  before=M.get_material_property_input_node(original_parent,prop);after=M.get_material_property_input_node(new_parent,prop)
  assert bool(before)==bool(after)
  if isinstance(before,u.MaterialExpressionCustom):assert str(before.get_editor_property('code'))==str(after.get_editor_property('code'))
 old_codes=[str(n.get_editor_property('code')) for n in M.get_material_expressions(original_parent) if isinstance(n,u.MaterialExpressionCustom)]
 new_codes=[str(n.get_editor_property('code')) for n in M.get_material_expressions(new_parent) if isinstance(n,u.MaterialExpressionCustom)]
 assert all(code in new_codes for code in old_codes)
 report['mud_geometry_programs_unchanged']=True
 report['texture_sample_counts']={}
 for old_material,new_material in [(original_parent,new_parent),(u.load_asset('/Game/GrandTour/ArtTests/FloraDrive/M_FloraLandscape'),landscape.landscape_material)]:
  counts=[sum(isinstance(n,u.MaterialExpressionTextureSample) for n in M.get_material_expressions(m)) for m in (old_material,new_material)]
  assert counts[0]==counts[1],counts
  report['texture_sample_counts'][new_material.get_name()]=counts
 textures={row['id']:{role:u.load_asset(D+'/Textures/T_'+row['id']+'_'+role+'_native') for role in ('color','normal','height','roughness')}}
 cases=[('baseline',row,1.),('woodland_floor',row,1.)] if stage=='candidate' else [('woodland_floor',row,1.)]
 for i in (1,2,3):
  for suffix in ('','N'):
   tex=u.load_asset('/Game/GrandTour/ArtTests/FloraDrive/T_ForestGround_%02d%s'%(i,suffix))
   deadline=time.monotonic()+180
   while tex.blueprint_get_size_x()<2048:
    assert time.monotonic()<deadline;yield .5
''' +text[b:]
old=" report['live_dynamic_materials']=[m.get_path_name() for m in mids]"
text=text.replace(old,old+'''
 landscape=surface.landscape
 report['live_terrain']=landscape.landscape_material.get_path_name()
 terrain_mids=[]
 for c in landscape.get_components_by_class(u.LandscapeComponent):
  material=c.get_material_instance_dynamic(0)
  if material:terrain_mids.append(material)
 assert terrain_mids,'Missing live landscape material instances'
 report['terrain_defaults']=[m.get_scalar_parameter_value('FloraVergeEnabled') for m in terrain_mids]
 assert all(abs(v-1.)<.0001 for v in report['terrain_defaults'])
''')
old=" report['views']=[{'name':n,'position':p,'target':t} for n,p,t in views];report['surface_before']=surface.get_surface_report()"
text=text.replace(old," views.extend([('puddle',[350,centre(350)-280,150],[850,centre(850),-5]),('verge',[150,centre(150)-200,160],[650,centre(650)-500,0])])\n"+old)
old=" for name,row,enabled in cases:"
text=text.replace(old,old+"\n  if stage=='candidate':\n   landscape.set_landscape_material_scalar_parameter_value('FloraVergeEnabled',0. if name=='baseline' else 1.)\n   for mid in mids:mid.set_scalar_parameter_value('FloraVergeEnabled',0. if name=='baseline' else 1.)\n  report.setdefault('terrain_live_controls',{})[name]=[m.get_scalar_parameter_value('FloraVergeEnabled') for m in terrain_mids+mids]")
text=text.replace("   if stage not in ('saved','verify'):mat.bind(mid,row,textures,enabled)","   pass # Ground and water materials remain unchanged.")
text=text.replace(" if stage=='saved':\n  yield from drive_check"," if stage=='verify':\n  yield from drive_check")
runtime=R/'Art/Export/FloraTrail/VergeStudy/candidate-runtime.py';runtime.write_text(text)
exec(compile(text,str(runtime),'exec'),globals())
