"""Finalize standalone startup scenes and correct the library's display lighting."""
import bpy
import shutil
import sys
from pathlib import Path
folder=Path(__file__).resolve().parents[2]/'Art/Export/WillowFamily'/sys.argv[sys.argv.index('--')+1]
for preset in ['young','broad','windswept','weathered']:
    path=folder/(preset+'.blend')
    bpy.ops.wm.open_mainfile(filepath=str(path))
    scene=next(s for s in bpy.data.scenes if s.camera is not None)
    bpy.context.window.scene=scene
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.region_3d.view_perspective='CAMERA'
                area.spaces.active.shading.type='MATERIAL'
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
path=folder/'WillowFamily.blend'
bpy.ops.wm.open_mainfile(filepath=str(path))
scene=bpy.data.scenes['Willow Family']; bpy.context.window.scene=scene
for name,energy in [('Family key',10000),('Family fill',4500),('Family rim',9000)]: bpy.data.lights[name].energy=energy
mat=bpy.data.materials['Label']
next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'].default_value=(.035,.045,.055,1)
scene.render.filepath=str(folder/'Willow_family.png')
bpy.ops.render.render(write_still=True,scene=scene.name)
bpy.ops.wm.save_as_mainfile(filepath=str(path))
shutil.copyfile(Path(__file__).parent/'build_willow_variations.py',folder/'build_willow_variations.py')
print('WILLOW_FAMILY_FINALIZED',flush=True)
