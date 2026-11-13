import bpy,json,shutil
from pathlib import Path
src=Path('C:/GrandTour/Art/References/Vehicles/Pathfinder2002')
out=Path('C:/GrandTour/Art/Export/VehicleTools/pathfinder-2002-shape-v03')
bpy.ops.wm.open_mainfile(filepath=str(out/'Pathfinder_2002_Shape.blend'))
for name in ['shape-map.json']:
    text=(src/name).read_text();bpy.data.texts[name].clear();bpy.data.texts[name].write(text);(out/name).write_text(text)
manifest={'vehicle':'2002 Nissan Pathfinder R50 SE','stage':'First independent native form study','style_approved':True,'model_shape_approved':False,'latest_file':'Pathfinder_2002_Shape.blend','fine_details_pending':['cockpit','tyre tread','wheel hardware','optics','working pivots/rig','engine export'],'review_images':['side.png','quarter.png','rear-quarter.png','front.png','rear.png','top.png','underside.png'],'saved_checks':'saved-shape-checks.json','known_failing_baseline':'v02-floor-regression.json'}
(out/'review-status.json').write_text(json.dumps(manifest,indent=2))
for name in ['verify_pathfinder_shape.py','build_pathfinder_shape.py']:shutil.copy2(Path('C:/GrandTour/Art/VehicleTools')/name,out/name)
shutil.copy2(out.parent/'pathfinder-2002-shape-v02/saved-shape-checks.json',out/'v02-floor-regression.json')
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Pathfinder_2002_Shape.blend'))
