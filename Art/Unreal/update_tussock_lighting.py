import unreal as u,json,sys,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve(); OUT=ROOT/'Art/Export/TussockStyle'
sys.path.insert(0,str(ROOT/'Art/Unreal'))
from tussock_style_lighting import configure
report={'ok':False,'levels':[]}
try:
    les=u.get_editor_subsystem(u.LevelEditorSubsystem)
    for name in ['L_TussockStyle','L_TussockStyle_Overview']:
        path='/Game/GrandTour/ArtTests/TussockStyle/'+name
        assert les.load_level(path)
        world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
        result=configure(world)
        assert u.EditorLoadingAndSavingUtils.save_map(world,path)
        report['levels'].append(dict(path=path,lighting=result))
    report['ok']=True
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
finally:
    (OUT/'lighting-report.json').write_text(json.dumps(report,indent=2));u.SystemLibrary.quit_editor()
