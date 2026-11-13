import bpy,json,sys,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools/vendor_geometry')
from shapely.geometry import Polygon
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
blend=Path(args[0]) if args else Path('C:/GrandTour/Art/Export/VehicleTools/prado-cabin-v07/Prado_Cabin.blend')
P=blend.parent
bpy.ops.wm.open_mainfile(filepath=str(blend));sc=bpy.context.scene;dg=bpy.context.evaluated_depsgraph_get()
with bpy.data.libraries.load('C:/GrandTour/Art/Export/VehicleTools/prado-exterior-v04/Prado_Exterior.blend',link=False) as (src,dst):dst.objects=['Prado | source-fitted body']
source=dst.objects[0];source.parent=None
source.data.calc_loop_triangles();sv=[v.co.copy() for v in source.data.vertices];st=[list(t.vertices) for t in source.data.loop_triangles];original=BVHTree.FromPolygons(sv,st,all_triangles=True)
def tree(obs):
 v=[];f=[]
 for ob in obs:
  ev=ob.evaluated_get(dg);me=ev.to_mesh();k=len(v);v.extend(ev.matrix_world@p.co for p in me.vertices);f.extend([k+i for i in p.vertices] for p in me.polygons);ev.to_mesh_clear()
 return BVHTree.FromPolygons(v,f)
def meshes(col):return [o for o in bpy.data.collections[col].objects if o.type=='MESH']
shell=meshes('01 Body')+meshes('10 Doors and closures')+meshes('11 Panel returns')
assembly=tree(shell);floor=tree(meshes('12 Cabin structure'))
surfaces=[]
for ob in shell:
 if '11 Panel returns' in [c.name for c in ob.users_collection]:continue
 used={i for p in ob.data.polygons for i in p.vertices};d=[original.find_nearest(ob.matrix_world@ob.data.vertices[i].co)[3] for i in used]
 surfaces.append({'object':ob.name,'max_surface_distance_m':max(d),'vertices_over_0_01mm':sum(x>.00001 for x in d)})
print('SOURCE SURFACE',surfaces)
profiles=json.loads(Path('C:/GrandTour/Art/Export/VehicleTools/prado-cabin-v06/build-report.json').read_text())['door_profiles']
seams=[]
for side in [-1,1]:
 for n,pts in profiles.items():
  boundary=Polygon(pts).buffer(-.000125,join_style=2).boundary
  tested=0;miss=[];depth=[]
  for k in range(600):
   y,z=boundary.interpolate(k/600,normalized=True).coords[0]
   start=Vector((side*1.5,y*5,z*5));direc=Vector((-side,0,0));hit=original.ray_cast(start,direc,1.0)[0]
   if hit is None or abs(hit.x)<.137*5:continue
   tested+=1;h=assembly.ray_cast(start,direc,1.0)[0]
   if h is None or (h-hit).length>.035:miss.append([y,z])
   else:depth.append((h-hit).length)
  seams.append({'door':n,'side':side,'samples':tested,'uncovered_or_over_35mm_recess':miss,'max_recess_m':max(depth,default=0)})
print('SEAMS',seams)
coverage=[]
for x,y,label in [(.085,-.038,'Driver'),(-.085,-.038,'Passenger'),(.065,.120,'Rear left'),(-.065,.120,'Rear right')]:
 missing=[];tested=0
 for i in range(15):
  for j in range(17):
   xx=x+(i/14-.5)*(.098 if y<0 else .116);yy=y+(j/16-.5)*.118
   tested+=1;h=floor.ray_cast(Vector((xx*5,yy*5,.220*5)),Vector((0,0,-1)),.7)[0]
   if h is None:missing.append([xx,yy])
 coverage.append({'seat':label,'samples':tested,'uncovered':missing})
print('FLOOR',coverage)
report={'source_surface_preservation':surfaces,'door_reveal_coverage':seams,'floor_coverage_under_seat_footprints':coverage,'scope':'Closed static assembly, sampled coverage. No moving-door or driving test.'}
(P/'assembly-verification.json').write_text(json.dumps(report,indent=2))
# Detailed low-angle and cabin-joint views, using actual working geometry.
bpy.data.objects.remove(source,do_unlink=True)
cam=sc.camera;sc.render.engine='BLENDER_WORKBENCH'
for name,c,d,scale in [('door-seam-close',(.17,.031,.255),(3,-.3,.4),.34),('rear-wheel-low',(.16,.253,.145),(3,.2,-.25),.37),('cabin-upper-trim',(.02,.05,.37),(0,-1,.1),.43)]:
 center=Vector(c)*5;cam.location=center+Vector(d)*5;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale*5;sc.render.filepath=str(P/(name+'.png'));bpy.ops.render.render(write_still=True)
