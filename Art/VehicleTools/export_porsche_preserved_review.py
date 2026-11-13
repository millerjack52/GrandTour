import bpy,json,hashlib
from pathlib import Path
from mathutils import Vector
O=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-preserved-repair-v02')
bpy.ops.wm.open_mainfile(filepath=str(O/'Porsche_Preserved_Repair.blend'))
parts=[o for o in bpy.data.collections['Porsche - repaired original components'].objects if o.type=='MESH']
bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.hide_set(False);o.select_set(True)
def bounds(objects):
 points=[o.matrix_world@Vector(p) for o in objects for p in o.bound_box]
 return [[min(p[k] for p in points) for k in range(3)],[max(p[k] for p in points) for k in range(3)]]
before=bounds(parts);count=len(parts)
dest=O/'Porsche_Preserved_Repair.glb'
bpy.ops.export_scene.gltf(filepath=str(dest),export_format='GLB',use_selection=True,export_apply=True,export_cameras=False,export_lights=False)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(dest))
afterparts=[o for o in bpy.context.scene.objects if o.type=='MESH'];after=bounds(afterparts)
deviation=max(abs(before[j][k]-after[j][k]) for j in range(2) for k in range(3))
assert len(afterparts)==count,(count,len(afterparts))
assert deviation<.0001,deviation
notes={
 'status':'Shape-preserving repair revision; construction refinement remains. Not game-ready.',
 'shape_authority':'Original user-supplied porshceoffroadtripo.glb; rejected generic authored rebuild is not reused.',
 'completed':['Original body positions preserved','Original accessories retained and separated','Clean fitted wheel assemblies','Independent glazing with original boundaries and faired pane interiors','Repaired winding, clipping junctions and small tear loops','Matching side and quarter comparisons','Transparent-glass review','GLB reimport check'],
 'remaining':['Noisy original window trim and accessory topology','Open source sheet boundaries still present; watertight assembly coverage not certified','Rig, suspension travel, collision, LOD and Unreal validation not completed','Materials are provisional; no finished texture work'],
 'reimport':{'mesh_count':count,'bounds_max_difference_m':deviation},
 'blend_sha256':hashlib.sha256((O/'Porsche_Preserved_Repair.blend').read_bytes()).hexdigest(),
 'glb_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),
 'lessons':['Do not substitute a generic body profile for the provided mesh.','Compare same-view original and repaired silhouette plus curved surfaces before calling cleanup successful.','Preserve thin pillars, spoiler and recessed bonnet; voxel remeshing changed them.','Glass replacement must remove opaque source sheets and preserve aperture boundaries.','Locate components geometrically: old island names can be wrong.','Separate source-fidelity, construction and engine-readiness conclusions.']}
(O/'delivery-status.json').write_text(json.dumps(notes,indent=2))
print(json.dumps(notes['reimport']))
