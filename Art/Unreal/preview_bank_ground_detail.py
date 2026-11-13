import unreal as u,json
from pathlib import Path
root=Path(u.Paths.project_dir()).resolve();qa=root/'Saved/LidarAuthoringQA/RS7Ground'
cam=next(a for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors() if a.get_name()=='CameraActor_5')
u.AutomationLibrary.take_high_res_screenshot(1600,900,str(qa/'editor-ground.png'),camera=cam)
(qa/'texture-loaded.json').write_text(json.dumps({n:{'size':[u.load_asset('/Game/GrandTour/ArtTests/LidarStudy/FirstSection/'+n).blueprint_get_size_x(),u.load_asset('/Game/GrandTour/ArtTests/LidarStudy/FirstSection/'+n).blueprint_get_size_y()],'never_stream':u.load_asset('/Game/GrandTour/ArtTests/LidarStudy/FirstSection/'+n).get_editor_property('never_stream')} for n in ['T_BankSoilColour','T_BankSoilORH']},indent=2))
