"""Generate cheap distance meshes from the fitted floor, keeping the source."""
import bpy,sys
from pathlib import Path
ROOT=Path('C:/GrandTour');sys.path.insert(0,str(ROOT/'Art/Blender'))
import native_plant_lib as L
OUT=ROOT/'Art/Export/LidarStudy/FirstSection/PeatMoss'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'peat-moss.blend'))
src=next(o for o in bpy.data.objects if o.type=='MESH')
for lod,ratio in [(1,.48),(2,.18)]:
    ob=src.copy();ob.data=src.data.copy();bpy.context.collection.objects.link(ob);ob.name=f'SM_PM_Floor_LOD{lod}'
    bpy.context.view_layer.objects.active=ob;mod=ob.modifiers.new('DistanceSimplification','DECIMATE');mod.ratio=ratio
    bpy.ops.object.modifier_apply(modifier=mod.name);L.export(ob,out=OUT)
    bpy.data.objects.remove(ob,do_unlink=True)
