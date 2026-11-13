"""Restore the established grass weights after material GrassInput reassignment."""
import unreal as u,json,time,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmorePainterly'
les=u.get_editor_subsystem(u.LevelEditorSubsystem);mel=u.MaterialEditingLibrary
phase='load';last=time.monotonic();report={'ok':False}
u.EditorPythonScripting.set_keep_python_script_alive(True)
def tick(dt):
 global phase,last
 try:
  if phase=='load':
   phase='repairing';assert les.load_level('/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive')
   m=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Painterly/M_Painterly_Terrain')
   nodes=list(mel.get_material_expressions(m));gout=next(n for n in nodes if isinstance(n,u.MaterialExpressionLandscapeGrassOutput))
   report['before_connections']=[n.get_name() if n else None for n in mel.get_inputs_for_material_expression(m,gout)]
   mask=next(n for n in nodes if isinstance(n,u.MaterialExpressionTextureSample) and n.get_editor_property('texture') and n.get_editor_property('texture').get_name()=='T_Benmore_VegetationMask')
   for entry in gout.get_editor_property('grass_types'):
    name=str(entry.get_editor_property('name'));channel='R' if name=='LowGrass' else ('B' if name=='TallClumps' else 'G')
    assert mel.connect_material_expressions(mask,channel,gout,name)
   report['after_connections']=[n.get_name() if n else None for n in mel.get_inputs_for_material_expression(m,gout)]
   assert len(report['after_connections'])==5 and all(report['after_connections'])
   assert not mel.recompile_material(m);assert u.EditorAssetLibrary.save_loaded_asset(m)
   world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
   u.SystemLibrary.execute_console_command(world,'grass.FlushCache')
   phase='warm';last=time.monotonic()
  elif phase=='warm' and time.monotonic()-last>45:
   phase='saving';assert les.save_current_level();report['ok']=True
   (OUT/'grass-connections-report.json').write_text(json.dumps(report,indent=2))
   u.unregister_slate_post_tick_callback(handle)
   p=ROOT/'Art/Unreal/check_benmore_painterly.py'
   exec(compile(p.read_text(),str(p),'exec'),{'__file__':str(p)})
 except Exception:
  phase='error';report['error']=traceback.format_exc();u.log_error(report['error'])
  (OUT/'grass-connections-report.json').write_text(json.dumps(report,indent=2))
  u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
handle=u.register_slate_post_tick_callback(tick)
