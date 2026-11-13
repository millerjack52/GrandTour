"""Full editor runner; StaticMeshEditorSubsystem is unavailable in commandlets."""
from pathlib import Path
import unreal as u
import traceback

try:
    folder = Path('C:/GrandTour/Art/Unreal')
    exec(compile((folder/'import_prado.py').read_text(), str(folder/'import_prado.py'), 'exec'))
    exec(compile((folder/'review_prado.py').read_text(), str(folder/'review_prado.py'), 'exec'))
except Exception:
    Path('C:/GrandTour/Art/Export/VehicleTools/prado-unreal-v01/editor-run-error.txt').write_text(traceback.format_exc())
    u.log_error(traceback.format_exc())
    u.SystemLibrary.quit_editor()
