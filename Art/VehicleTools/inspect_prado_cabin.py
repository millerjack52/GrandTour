import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path('C:/GrandTour/Art/Export/VehicleTools/prado-exterior-v04')
bpy.ops.wm.open_mainfile(filepath=str(P/'Prado_Exterior.blend'))
o=bpy.data.objects['Prado | source-fitted body'];tree=BVHTree.FromPolygons([v.co/5 for v in o.data.vertices],[list(p.vertices) for p in o.data.polygons])
out={'floors':[],'sidewalls':[]}
for y in [-.18,-.14,-.08,0,.06,.10,.14,.18,.22,.28,.34,.37]:
 out['floors'].append({'y':y,'heights':[(x, list(p) if (p:=tree.ray_cast(Vector((x,y,.295)),Vector((0,0,-1)),.3)[0]) else None) for x in [0,.06,.10,.13,.16]]})
for z in [.17,.22,.27,.31,.36,.40]:
 out['sidewalls'].append({'z':z,'sides':[(y,list(p) if (p:=tree.ray_cast(Vector((0,y,z)),Vector((1,0,0)),.3)[0]) else None) for y in [-.16,-.08,0,.08,.16,.23,.32]]})
print(json.dumps(out,indent=2));(P/'cabin-measurements.json').write_text(json.dumps(out,indent=2))
# Bare shell / no glazing / interior inspection.
for obj in bpy.context.scene.objects:
 if obj.type=='MESH' and obj!=o:obj.hide_render=True
sc=bpy.context.scene;cam=sc.camera
for n,c,d,scale in [('cabin-empty',(0,.05,.28),(2,-1,3),.84),('body-side-grid',(0,0,.27),(3,0,0),1.04)]:
 center=Vector(c)*5;cam.location=center+Vector(d)*5;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale*5;sc.render.filepath=str(P/(n+'.png'));bpy.ops.render.render(write_still=True)
