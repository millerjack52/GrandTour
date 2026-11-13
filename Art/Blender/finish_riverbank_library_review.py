"""Adjust display-only scrub floor contact and rerender the saved library scene."""
import bpy
from pathlib import Path
root=Path(__file__).resolve().parents[2]
out=root/'Art/Export/RoadFordStyle'
bpy.ops.wm.open_mainfile(filepath=str(out/'RiverbankVegetation.blend'))
scene=bpy.data.scenes['Riverbank Vegetation Review']
for ob in scene.objects:
    if ob.name.startswith('SM_RF_Scrub') and not ob.hide_render: ob.location.z=-.10
library={scene,*[ob for ob in bpy.data.objects if ob.name.startswith(('SM_RF_','UCX_'))]}
bpy.data.libraries.write(str(out/'RiverbankVegetation.blend'),library)
scene.render.filepath=str(out/'Riverbank_asset_review.png')
bpy.ops.render.render(write_still=True,scene=scene.name)
print('LIBRARY_REVIEW_OK')
