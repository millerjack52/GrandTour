import bpy,bmesh,sys,json,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.geometry import barycentric_transform
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools/vendor_geometry')
from shapely.geometry import Polygon
from shapely.ops import triangulate
O=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-completion-v04')
bpy.ops.wm.open_mainfile(filepath=str(O/'Porsche_Safari_Review.blend'));s=bpy.context.scene;body=bpy.data.objects['Porsche original body - locally repaired'];pane=bpy.data.objects['Rear glass'];half=len(pane.data.vertices)//2
edges={}
for f in pane.data.polygons:
 if all(i<half for i in f.vertices):
  v=list(f.vertices)
  for a,b in zip(v,v[1:]+v[:1]):e=tuple(sorted([a,b]));edges[e]=edges.get(e,0)+1
edges={e for e,n in edges.items() if n==1};e=edges.pop();loop=list(e)
while edges:
 hit=next((e for e in edges if loop[-1] in e),None)
 if hit is None:break
 edges.remove(hit);loop.append(hit[1] if hit[0]==loop[-1] else hit[0])
poly=Polygon([(pane.data.vertices[i].co.x,pane.data.vertices[i].co.z) for i in loop]).buffer(.001)
ps=np.array([list(v.co) for v in pane.data.vertices]);x,y,z=ps.T;A=np.column_stack([np.ones(len(x)),x,z,x*x,x*z,z*z]);co=np.linalg.lstsq(A,y,rcond=None)[0]
def depth(p):return float(np.dot(co,[1,p.x,p.z,p.x*p.x,p.x*p.z,p.z*p.z]))
me=body.data;me.calc_loop_triangles();vv=[];ff=[];cut=0
for t in me.loop_triangles:
 ps=[me.vertices[i].co.copy() for i in t.vertices];c=sum(ps,Vector())/3;tp=Polygon([(p.x,p.z) for p in ps])
 if abs(c.y-depth(c))<.045 and tp.area>1e-10 and tp.intersects(poly):
  diff=tp.difference(poly);chunks=[diff] if diff.geom_type=='Polygon' else [g for g in getattr(diff,'geoms',[]) if g.geom_type=='Polygon'];cut+=1;flat=[Vector((p.x,p.z,0)) for p in ps]
  for chunk in chunks:
   for tri in triangulate(chunk):
    if not chunk.covers(tri.representative_point()):continue
    vs=[barycentric_transform(Vector((x,z,0)),*flat,*ps) for x,z in list(tri.exterior.coords)[:-1]]
    if (vs[1]-vs[0]).cross(vs[2]-vs[0]).dot((ps[1]-ps[0]).cross(ps[2]-ps[0]))<0:vs.reverse()
    ff.append(tuple(range(len(vv),len(vv)+3)));vv.extend(vs)
 else:ff.append(tuple(range(len(vv),len(vv)+3)));vv.extend(ps)
new=bpy.data.meshes.new('Source pane opening');new.from_pydata(vv,[],ff);new.update();new.materials.append(me.materials[0]);body.data=new
for f in new.polygons:f.use_smooth=True
new.set_sharp_from_angle(angle=1.4)
print('CUT',cut)
c=s.camera;c.location=(5,7,3.5);c.rotation_euler=(Vector((0,0,.90))-c.location).to_track_quat('-Z','Y').to_euler();c.data.type='ORTHO';c.data.ortho_scale=5.5;s.render.engine='BLENDER_WORKBENCH';s.render.filepath=str(O/'rear-aperture-test.png');bpy.ops.render.render(write_still=True)
