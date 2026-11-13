import bpy,json,hashlib,math
from pathlib import Path
from mathutils import Vector
P=Path('C:/GrandTour/Art/Export/VehicleTools/ferrari288-good-game-v01');R=P.parent/'ferrari288-good-working-v01'
bpy.ops.wm.open_mainfile(filepath=str(P/'Ferrari288_GameReady.blend'));body=bpy.data.objects['Body | original textured shell'];orig=json.loads((R/'body-data.json').read_text());scale=4.5
err=max((body.matrix_world@v.co/scale-Vector(p)).length for v,p in zip(body.data.vertices,orig['verts']));assert err<1e-6
source_mesh=body.data.copy();uvs=[tuple(v.uv) for v in body.data.uv_layers[0].data];original_vcount=len(body.data.vertices);original_fcount=len(body.data.polygons)
source=bpy.data.libraries.load(str(R/'Ferrari288_LowPoly_Working.blend'))
with source as (a,b):b.objects=['Body | original textured shell']
baseline=b.objects[0];kept=json.loads(body['retained_baseline_faces']);baseline_uv=[baseline.data.uv_layers[0].data[li].uv for i in kept for li in baseline.data.polygons[i].loop_indices];uv_error=max((Vector(a)-b).length for a,b in zip(uvs,baseline_uv));assert uv_error<1e-7
assert original_vcount==len(baseline.data.vertices) and original_fcount==len(kept)
report={'body_position_error_m':err*scale,'body_uv_error':uv_error,'body_vertices':original_vcount,'body_triangles':original_fcount,'source_glb_sha256':hashlib.sha256(Path('C:/Users/mille/Downloads/good288.glb').read_bytes()).hexdigest(),'status':'BODY_AND_UVS_PRESERVED'}
(P/'preservation-report.json').write_text(json.dumps(report,indent=2));print(report)
