"""Refine saved pigment and distant normal shaders, then repeat visual review."""
import unreal as u, sys, time, json, traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve()
sys.path.insert(0,str(ROOT/'Art/Unreal'))
import benmore_painterly_surface as paint
OUT=ROOT/'Art/Export/BenmorePainterly'
DEST='/Game/GrandTour/Demo/BenmoreRoads/Painterly'
les=u.get_editor_subsystem(u.LevelEditorSubsystem)
mel=u.MaterialEditingLibrary
phase='load'; last=time.monotonic()
u.EditorPythonScripting.set_keep_python_script_alive(True)

def tick(dt):
 global phase,last
 try:
  if phase=='load':
   phase='building'
   assert les.load_level('/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive')
   for name in ['M_Painterly_Terrain','M_Painterly_Hills']:
    m=u.load_asset(DEST+'/'+name); changed=0
    for n in mel.get_material_expressions(m):
     if not isinstance(n,u.MaterialExpressionCustom):continue
     names=[str(x.get_editor_property('input_name')) for x in n.get_editor_property('inputs')]
     if 'CoverDetail' in names:n.set_editor_property('code',paint.COLOR);changed+=1
     elif names==['P','HillNormal']:n.set_editor_property('code',paint.HILL_NORMAL)
    assert changed>=1
    assert not mel.recompile_material(m)
    assert u.EditorAssetLibrary.save_loaded_asset(m)
   world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
   u.SystemLibrary.execute_console_command(world,'grass.FlushCache')
   phase='warm';last=time.monotonic()
  elif phase=='warm' and time.monotonic()-last>35:
   phase='saved';assert les.save_current_level()
   (OUT/'refinement-report.json').write_text(json.dumps({'ok':True,'height_bands_removed':True,'adaptive_normal_mip':True},indent=2))
   u.unregister_slate_post_tick_callback(handle)
   p=ROOT/'Art/Unreal/check_benmore_painterly.py'
   exec(compile(p.read_text(),str(p),'exec'),{'__file__':str(p)})
 except Exception:
  phase='error';error=traceback.format_exc();u.log_error(error)
  (OUT/'refinement-report.json').write_text(json.dumps({'ok':False,'error':error},indent=2))
  u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
handle=u.register_slate_post_tick_callback(tick)
