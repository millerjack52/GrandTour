import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
P=Path('C:/GrandTour/Art/Export/VehicleTools/ferrari288-good-game-v01');bpy.ops.wm.open_mainfile(filepath=str(P/'Ferrari288_GameReady.blend'));sc=bpy.context.scene
body=bpy.data.objects['Body | original textured shell'];vs=[body.matrix_world@v.co for v in body.data.vertices];fs=[list(p.vertices) for p in body.data.polygons];tree=BVHTree.FromPolygons(vs,fs)
report={'poses':[],'driver_rays':[]}
for tag in ['FL','FR','RL','RR']:
 ob=bpy.data.objects['Wheel_'+tag];c=Vector(ob['pivot']);vertices=[ob.matrix_world@v.co for v in ob.data.vertices];faces=[list(p.vertices) for p in ob.data.polygons]
 for angle in ([-25,0,25] if tag[0]=='F' else [0]):
  for z in [-.06,0,.04]:
   T=Matrix.Translation(c+Vector((0,0,z)))@Matrix.Rotation(math.radians(angle),4,'Z')@Matrix.Translation(-c);bv=BVHTree.FromPolygons([T@v for v in vertices],faces);overlap=tree.overlap(bv)
   report['poses'].append({'wheel':tag,'steer_deg':angle,'travel_m':z,'contacts':len(overlap),'body_faces':sorted(set(a for a,b in overlap))})
print('CONTACTS',[(r['wheel'],r['steer_deg'],r['travel_m'],r['contacts']) for r in report['poses']])
# Driver visibility tests against opaque geometry. Glass and thin seals are excluded.
dg=bpy.context.evaluated_depsgraph_get();opaque=[]
for ob in list(bpy.data.collections['Ferrari | preserved source components'].objects)+list(bpy.data.collections['GAME | fitted additions'].objects):
 if ob.type!='MESH' or ob.name.startswith(('Glass','Seal')):continue
 ev=ob.evaluated_get(dg);me=ev.to_mesh();v=[ob.matrix_world@p.co for p in me.vertices];f=[list(p.vertices) for p in me.polygons];opaque.append((ob.name,BVHTree.FromPolygons(v,f)));ev.to_mesh_clear()
report['seat_body_intersections']={name:len(tree.overlap(t)) for name,t in opaque if name.startswith('Seat |')}
print('SEATS',report['seat_body_intersections'])
eye=Vector((.083,.01,.317))*4.5
for yaw in [-25,0,25]:
 direction=Vector((math.sin(math.radians(yaw)),-math.cos(math.radians(yaw)),0));hits=[]
 for name,t in opaque:
  hit=t.ray_cast(eye,direction,15)
  if hit[0] is not None:hits.append((name,hit[3]))
 report['driver_rays'].append({'yaw':yaw,'hits':sorted(hits,key=lambda p:p[1])[:3]})
(P/'clearance-report.json').write_text(json.dumps(report,indent=2));print('DRIVER',report['driver_rays'])
# Revealing review views, not beauty-only checks.
sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.light='STUDIO';sc.display.shading.color_type='MATERIAL';sc.display.shading.show_shadows=True;sc.display.shading.show_cavity=True;sc.render.resolution_x=1400;sc.render.resolution_y=950
cam=sc.camera;cam.data.type='ORTHO';cam.data.ortho_scale=5.4
def view(name,pos,target):
 cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(P/(name+'.png'));bpy.ops.render.render(write_still=True)
view('qa-side',(8,0,1),(0,0,1));view('qa-underside',(3,-3,-6),(0,0,.7))
for tag in ['FL','FR','RL','RR']:bpy.data.objects['Wheel_'+tag].hide_render=True
view('qa-wheel-off',(6,-7,2),(0,0,.85))
