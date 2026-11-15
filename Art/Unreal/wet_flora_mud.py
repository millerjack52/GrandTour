"""Reuse the established mud capture/drive harness for a protected wet-shading trial."""
from pathlib import Path
R=Path('C:/GrandTour');source=R/'Art/Unreal/trial_flora_mud.py';text=source.read_text()
changes={
 'from flora_mud_trial_baseline import verify':'from flora_mud_wet_baseline import verify',
 'import flora_mud_trial_materials as mat':'import flora_mud_trial_materials as mat\nimport flora_mud_wet_materials as wet',
 "O=R/'Art/Export/FloraTrail/MudTrial'":"O=R/'Art/Export/FloraTrail/MudWet'",
 "stage=os.environ.get('GT_MUD_TRIAL_STAGE','screen')":"stage=os.environ.get('GT_MUD_WET_STAGE','probe')",
 "rows=json.loads((O/'sources.json').read_text())":"rows=json.loads((R/'Art/Export/FloraTrail/MudTrial/sources.json').read_text())",
}
for old,new in changes.items():
 assert text.count(old)==1,old;text=text.replace(old,new)
a=text.index(" if stage=='screen':");b=text.index(' # Wait for asynchronously',a)
text=text[:a]+'''
 cfg=json.loads((R/'Art/flora_mud_wet_settings.json').read_text())
 row=next(r for r in rows if r['id']=='brown_mud_02');selected=[row]
 target=D+'/L_FloraTrail_MudWet'
 if stage=='verify':
  assert L.load_level(target);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
  mi=u.load_asset(wet.INSTANCE)
 else:
  mi=wet.build();wet.configure(mi,cfg['parameters'],True)
  exists=E.does_asset_exist(target)
  assert L.load_level(target if exists else D+'/L_FloraTrail_Mud');world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
  visual=next(a for a in A.get_all_level_actors() if isinstance(a,u.GTMudRunnerVisual));visual.set_editor_property('material',mi)
  assert L.save_current_level() if exists else u.EditorLoadingAndSavingUtils.save_map(world,target)
  assert L.load_level('/Engine/Maps/Entry');assert L.load_level(target);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 visual=next(a for a in A.get_all_level_actors() if isinstance(a,u.GTMudRunnerVisual));assert visual.material==mi
 report['saved_material']=mi.get_path_name();report['saved_map']=target
 textures={row['id']:{role:u.load_asset(D+'/Textures/T_'+row['id']+'_'+role+'_native') for role in ('color','normal','height','roughness')}}
 cases=[(name,row,1.) for name in wet.PROFILES] if stage=='probe' else [(cfg['selected'],row,1.)]
''' + text[b:]
old="   if stage not in ('saved','verify'):mat.bind(mid,row,textures,enabled)"
assert text.count(old)==1
text=text.replace(old,old+"\n   if stage=='probe':wet.configure(mid,wet.PROFILES[name])\n   values={k:mid.get_scalar_parameter_value('MudWet'+k) for k in wet.PARAMS}\n   if stage!='probe':\n    for k,v in {**wet.PARAMS,**cfg['parameters']}.items():assert abs(values[k]-v)<.0001,(k,values[k],v)\n   report.setdefault('wet_controls',{})[name]=values")
# The probe has saved the configured defaults. Verify their fresh load and drive
# in one read-only process, without re-saving the candidate first.
old=" if stage=='saved':\n  yield from drive_check"
assert text.count(old)==1
text=text.replace(old," if stage in ('saved','verify'):\n  yield from drive_check")
exec(compile(text,str(source),'exec'),globals())
