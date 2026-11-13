import unreal as u,json,traceback
from pathlib import Path
root=Path(u.Paths.project_dir()).resolve();out=root/'Art/Export/LidarStudy/FloraMatch';dest='/Game/GrandTour/ArtTests/FloraMatch'
report={'ok':False,'texture_only':True}
try:
 rows=json.loads((out/'source-colour-manifest.json').read_text());tasks=[]
 for row in rows:
  task=u.AssetImportTask();task.filename=str(out/row['colour_atlas']);task.destination_path=dest;task.destination_name='T_'+row['source']+'_Colour';task.automated=True;task.replace_existing=True;task.save=True;tasks.append(task)
 u.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
 report['ok']=True;report['textures']=[t.destination_name for t in tasks]
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(out/'colour-refresh.json').write_text(json.dumps(report,indent=2))
def finish(dt):
 u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(finish)
