"""Create the initial map outside a Slate callback; later setup loads it."""
import unreal as u
from pathlib import Path
path='/Game/GrandTour/Demo/BenmoreFullSite/L_Benmore_TerrainReview'
folder=Path(u.Paths.project_content_dir())/'GrandTour/Demo/BenmoreFullSite'
folder.mkdir(parents=True,exist_ok=True)
if not u.EditorAssetLibrary.does_asset_exist(path):
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).new_level(path)
u.log('BENMORE_EMPTY_MAP_READY '+path)
