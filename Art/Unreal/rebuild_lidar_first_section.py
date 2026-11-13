"""Rebuild or validate the bounded first section, with backup and reload proof."""
import unreal as u,sys,json,time,traceback,shutil,gc,os
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import lidar_first_section as section
QA=section.QA;les=u.get_editor_subsystem(u.LevelEditorSubsystem)
mode=os.environ.get('GT_RS7_MODE','Validate');report={'ok':False,'mode':mode};busy=False;deadline=0
def persist():(QA/('runner-'+mode.lower()+'.json')).write_text(json.dumps(report,indent=2))
def run():
 assert les.load_level(section.BASE+'/L_LidarStudy');yield 4
 if mode=='Rebuild':
  source=json.loads((QA/'survey.json').read_text())
  author=next(a for a in section.actors.get_all_level_actors() if isinstance(a,u.GTProceduralGround))
  assert str(author.output_digest)==source['ground_digest'],'Terrain changed; resurvey before rebuilding the fitted surface'
  backup=ROOT/'Saved/LidarAuthoringBackups'/('RS7-Rebuild-'+str(time.time_ns()));backup.mkdir(parents=True)
  shutil.copy2(ROOT/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap',backup/'L_LidarStudy.umap')
  shutil.copytree(ROOT/'Content/GrandTour/ArtTests/LidarStudy/FirstSection',backup/'FirstSection')
  report['backup']=str(backup)
  section.import_assets();section.apply();section.tree_palette();section.local_exposure();section.ground_communities();yield 4
  before=section.snapshot();section.apply();section.tree_palette();section.local_exposure();section.ground_communities()
  assert section.snapshot()==before;report['deterministic_rebuild']=True
  report['before_save']=section.validate();persist()
  assert les.save_current_level();yield 2
  assert les.load_level('/Engine/Maps/Entry');gc.collect();yield 2
  assert les.load_level(section.BASE+'/L_LidarStudy');yield 4
  report['after_reload']=section.validate();assert report['after_reload']['snapshot']==report['before_save']['snapshot']
 else:report['validation']=section.validate()
 report['ok']=True;persist();yield 1
steps=run()
def tick(dt):
 global busy,deadline
 if busy:return
 busy=True
 try:
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 except Exception:
  report['error']=traceback.format_exc();persist();u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
