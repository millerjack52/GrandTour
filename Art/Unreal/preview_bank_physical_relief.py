import unreal as u
from pathlib import Path
root=Path(u.Paths.project_dir()).resolve()
cam=next(a for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors() if a.get_name()=='CameraActor_5')
u.AutomationLibrary.take_high_res_screenshot(1600,900,str(root/'Saved/LidarAuthoringQA/RS7Relief/editor-B05.png'),camera=cam)
