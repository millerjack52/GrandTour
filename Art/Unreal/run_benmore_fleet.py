import unreal as u
from pathlib import Path
assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview')
p=Path('C:/GrandTour/Art/Unreal/place_benmore_fleet.py')
exec(compile(p.read_text(),str(p),'exec'))
u.SystemLibrary.quit_editor()
