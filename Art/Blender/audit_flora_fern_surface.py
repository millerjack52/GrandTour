"""Read the existing frozen fern's normals/UVs without re-exporting geometry."""
import bpy,json
from pathlib import Path
R=Path('C:/GrandTour');O=R/'Art/Export/FloraTrail/FernSurface';O.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
source=R/'Art/Export/LidarStudy/FloraParity/AssetMatch/meshes/SM_Exact_fern.fbx'
bpy.ops.import_scene.fbx(filepath=str(source),use_anim=False)
obj=next(o for o in bpy.context.selected_objects if o.type=='MESH');mesh=obj.data;mesh.calc_normals_split()
report={'blender':bpy.app.version_string,'source':str(source),'vertices':len(mesh.vertices),'polygons':len(mesh.polygons),'custom_normals':mesh.has_custom_normals,'normals':[[round(c,5) for c in l.normal] for l in mesh.loops],'face_normals':[[round(c,5) for c in p.normal] for p in mesh.polygons],'uv0_bounds':[[min(d.uv[i] for d in mesh.uv_layers[0].data),max(d.uv[i] for d in mesh.uv_layers[0].data)] for i in (0,1)]}
(O/'mesh-audit.json').write_text(json.dumps(report,indent=2));print('FERN_AUDIT_DONE',flush=True)
