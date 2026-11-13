"""Save useful viewport framing; geometry and export data are unchanged."""
import bpy,json,hashlib
from pathlib import Path
from mathutils import Vector
P=Path('C:/GrandTour/Art/Export/VehicleTools/ferrari288-good-game-v01')
for file,position,target,distance in [('Ferrari288_GameReady.blend',(6,-8,4),(0,0,.8),6.8),('Ferrari288_GameRig.blend',(800,600,400),(0,0,80),680)]:
 bpy.ops.wm.open_mainfile(filepath=str(P/file));sc=bpy.context.scene;cam=sc.camera;cam.location=position;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='PERSP';cam.data.lens=48
 body=bpy.data.objects.get('Body | original textured shell')
 if body and 'retained_baseline_faces' in body:
  ids=json.loads(body['source_face_ids']);kept=json.loads(body['retained_baseline_faces'])
  if len(ids)!=len(body.data.polygons):body['source_face_ids']=json.dumps([ids[i] for i in kept])
 for screen in bpy.data.screens:
  for area in screen.areas:
   if area.type=='VIEW_3D':
    space=area.spaces.active;space.region_3d.view_location=target;space.region_3d.view_distance=distance;space.region_3d.view_rotation=cam.rotation_euler.to_quaternion();space.shading.color_type='TEXTURE';space.overlay.show_extras=False
 bpy.ops.wm.save_as_mainfile(filepath=str(P/file))
report=json.loads((P/'export-report.json').read_text());report['source_sha256']=hashlib.sha256((P/'Ferrari288_GameReady.blend').read_bytes()).hexdigest();(P/'export-report.json').write_text(json.dumps(report,indent=2))
