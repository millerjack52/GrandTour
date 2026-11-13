"""Local glazing rebuild tools. Preserve interfaces; fit surface depth independently.
No execution on import. All coordinates in this module are normalized Tripo units.
"""
import bpy,bmesh,math,json,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools/vendor_geometry')
import numpy as np
from shapely import constrained_delaunay_triangles
from shapely.geometry import Polygon,Point,LineString,box
from shapely.ops import triangulate,nearest_points
S=5.

def preserve_faces(ob,kept):
 """Rebuild a subset while preserving retained face-corner normals/materials."""
 me=ob.data;kept=set(kept);polys=[p for p in me.polygons if p.index in kept]
 used=sorted({v for p in polys for v in p.vertices});ids={v:i for i,v in enumerate(used)}
 verts=[me.vertices[i].co.copy() for i in used];fs=[[ids[i] for i in p.vertices] for p in polys]
 norms=[me.corner_normals[i].vector.copy() for p in polys for i in p.loop_indices]
 new=bpy.data.meshes.new(ob.name+' repaired');new.from_pydata(verts,[],fs);new.update()
 for mat in me.materials:new.materials.append(mat)
 for p,q in zip(new.polygons,polys):p.material_index=q.material_index;p.use_smooth=q.use_smooth
 new.normals_split_custom_set(norms);ob.data=new

def remove_source_patch(objects,source,faceids):
 vv=[Vector(p)*S for p in source['verts']];ff=[source['polys'][i] for i in faceids]
 patch=BVHTree.FromPolygons(vv,ff);changed=[]
 for ob in objects:
  removed=[]
  for p in ob.data.polygons:
   if patch.find_nearest(p.center)[3]>.00002:continue
   if all(patch.find_nearest(ob.data.vertices[i].co)[3]<.00002 for i in p.vertices):removed.append(p.index)
  if removed:preserve_faces(ob,[p.index for p in ob.data.polygons if p.index not in set(removed)]);changed.append({'object':ob.name,'removed_faces':len(removed)})
 return changed

def make(n,verts,faces,mat,col='17 Glazing correction',thick=0,outnormal=None,smooth=True):
 if col not in bpy.data.collections:
  co=bpy.data.collections.new(col);bpy.context.scene.collection.children.link(co)
 me=bpy.data.meshes.new(n);me.from_pydata([Vector(p)*S for p in verts],[],faces);me.update()
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-7);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 if outnormal and sum((f.normal*f.calc_area() for f in bm.faces),Vector()).dot(Vector(outnormal))<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
 for f in bm.faces:f.smooth=smooth
 bm.to_mesh(me);bm.free();me.materials.append(bpy.data.materials['Prado | '+mat]);ob=bpy.data.objects.new(n,me);bpy.data.collections[col].objects.link(ob);ob.parent=bpy.data.objects['PRADO | working assembly'];ob.color=me.materials[0].diffuse_color
 if thick:
  mod=ob.modifiers.new('Thin inward sheet','SOLIDIFY');mod.thickness=thick*S;mod.offset=-1
 return ob

def fit_surface(ring,bow=0,outsign=1,offset=0):
 arr=np.array(ring);xs=arr[:,0];zs=arr[:,2];z0=float(zs.min());dz=float(zs.max()-z0);width=max(abs(xs))
 matrix=np.array([[1,(z-z0)/dz,((z-z0)/dz)**2,(x/width)**2] for x,y,z in ring]);coeff=np.linalg.lstsq(matrix,arr[:,1],rcond=None)[0]
 def fn(x,z):
  t=(z-z0)/dz
  return float(coeff@np.array([1,t,t*t,(x/width)**2]))+outsign*(offset+bow*max(0,1-(x/width)**2)*max(0,4*t*(1-t)))
 return fn

def edge_y(ring,x,z):
 point=Vector((x,z));best=None
 for a,b in zip(ring,ring[1:]+ring[:1]):
  aa=Vector((a[0],a[2]));bb=Vector((b[0],b[2]));d=bb-aa;t=max(0,min(1,(point-aa).dot(d)/max(d.length_squared,1e-15)));q=aa+d*t;dist=(q-point).length_squared
  if best is None or dist<best[0]:best=(dist,a[1]+(b[1]-a[1])*t)
 return best[1]

def resample(poly,step=.003):
 coords=list(poly.exterior.coords)[:-1];points=[]
 for a,b in zip(coords,coords[1:]+coords[:1]):
  dist=math.dist(a,b);count=max(1,math.ceil(dist/step))
  points.extend((a[0]+(b[0]-a[0])*j/count,a[1]+(b[1]-a[1])*j/count) for j in range(count))
 return points

def ring_strip(name,outer,inner,outer_y,inner_y,mat,outsign=1,thick=.0008):
 assert outer.buffer(.0000001).covers(inner),f'{name}: inner ring outside fixed aperture'
 annulus=Polygon(resample(outer),[resample(inner)]);vs=[];fs=[]
 for tri in constrained_delaunay_triangles(annulus).geoms:
  k=len(vs)
  for x,z in list(tri.exterior.coords)[:3]:
   p=Point(x,z);a=nearest_points(p,outer.boundary)[1];b=nearest_points(p,inner.boundary)[1]
   da=p.distance(a);db=p.distance(b);t=da/(da+db) if da+db>1e-12 else 0
   y=(1-t)*outer_y(a.x,a.y)+t*inner_y(b.x,b.y);vs.append((x,y,z))
  fs.append((k,k+1,k+2))
 return make(name,vs,fs,mat,thick=thick,outnormal=(0,outsign,0))

def glass_grid(name,poly,yfunc,outsign=1):
 x0,z0,x1,z1=poly.bounds;vs=[];fs=[];nx=48;nz=22
 for j in range(nz):
  za=z0+(z1-z0)*j/nz;zb=z0+(z1-z0)*(j+1)/nz
  for i in range(nx):
   xa=x0+(x1-x0)*i/nx;xb=x0+(x1-x0)*(i+1)/nx;cell=box(xa,za,xb,zb);clipped=poly.intersection(cell)
   if clipped.is_empty:continue
   if clipped.geom_type!='Polygon':continue
   pp=list(clipped.exterior.coords)[:-1]
   if len(pp)==4:
    k=len(vs);vs.extend((x,yfunc(x,z),z) for x,z in pp);fs.append(tuple(range(k,k+4)))
   else:
    for tri in triangulate(clipped):
     if not clipped.covers(tri.representative_point()):continue
     k=len(vs);vs.extend((x,yfunc(x,z),z) for x,z in list(tri.exterior.coords)[:3]);fs.append((k,k+1,k+2))
 ob=make(name,vs,fs,'Glass',col='02 Glass',thick=.00065,outnormal=(0,outsign,0))
 # Apply physical thickness, then separate edge-wall normals from the pane.
 bpy.context.view_layer.objects.active=ob
 bpy.ops.object.modifier_apply(modifier=ob.modifiers[0].name)
 bm=bmesh.new();bm.from_mesh(ob.data)
 for e in bm.edges:e.smooth=e.is_manifold and e.calc_face_angle()<math.radians(35)
 bm.to_mesh(ob.data);bm.free();ob.data.update()
 ob['surface_method']='Regular clipped quad grid with analytic shallow curvature; sharp edge-wall normals'
 return ob

def repair_rear(source,contract,objects):
 ring=[p['co'] for p in contract['rear_outer_ring']]
 removed=remove_source_patch(objects,source,contract['rear_tunnel_source_faces_to_remove'])
 old=bpy.data.objects.get('Glass | RearWindow')
 if old:bpy.data.objects.remove(old,do_unlink=True)
 outer=Polygon([(x,z) for x,y,z in ring]);inner=outer.buffer(-.0011,join_style=2)
 fitted=fit_surface(ring,bow=.00045,outsign=1,offset=-.00065)
 ring_strip('Rear glass | fitted rubber seal',outer,inner,lambda x,z:edge_y(ring,x,z),fitted,'Rubber',1)
 ob=glass_grid('Glass | RearWindow',inner,fitted,1)
 return {'removed_deep_reveal':removed,'outer_ring_raw':ring,'pane_depth_below_rim_raw':.00065,'seal_width_raw':.0011,'new_pane':ob.name}

def repair_front(source,contract,objects):
 ring=[p['co'] for p in contract['outer_ring']]
 removed=remove_source_patch(objects,source,contract['surround_source_faces_to_remove'])
 for name in ['Glass | Windscreen','CAB | aperture-fitted dashboard cowl']:
  old=bpy.data.objects.get(name)
  if old:bpy.data.objects.remove(old,do_unlink=True)
 outer=Polygon([(x,z) for x,y,z in ring]);points=[]
 def bez(a,b,c,n):
  for i in range(n):
   t=i/n;points.append(((1-t)**2*a[0]+2*t*(1-t)*b[0]+t*t*c[0],(1-t)**2*a[1]+2*t*(1-t)*b[1]+t*t*c[1]))
 bez((-.148,.313), (0,.314),(.148,.313),40)
 bez((.148,.313),(.155,.313),(.154,.320),8)
 bez((.154,.320),(.146,.360),(.138,.399),24)
 bez((.138,.399),(.1368,.406),(.131,.407),8)
 bez((.131,.407),(0,.415),(-.131,.407),40)
 bez((-.131,.407),(-.1368,.406),(-.138,.399),8)
 bez((-.138,.399),(-.146,.360),(-.154,.320),24)
 bez((-.154,.320),(-.155,.313),(-.148,.313),8)
 seal_outer=Polygon(points)
 assert outer.covers(seal_outer),f'Windscreen boundary exceeds fixed surround {seal_outer.difference(outer).area}'
 pane=seal_outer.buffer(-.0010,join_style=1)
 shape=fit_surface(ring,bow=.0007,outsign=-1,offset=-.00065)
 seal_y=lambda x,z:shape(x,z)-.00035
 ring_strip('Windscreen | fitted painted surround',outer,seal_outer,lambda x,z:edge_y(ring,x,z),seal_y,'Paint',-1,.0008)
 ring_strip('Windscreen | continuous rubber seal',seal_outer,pane,seal_y,shape,'Rubber',-1,.0006)
 ob=glass_grid('Glass | Windscreen',pane,shape,-1)
 # Fitted cowl ends behind the lower glass edge, then joins below dash top.
 vs=[];fs=[]
 for i in range(49):
  x=-.148+.296*i/48
  cross=pane.intersection(LineString([(x,.29),(x,.335)]))
  z=min(p[1] for p in cross.coords) if cross.geom_type=='LineString' and not cross.is_empty else .312
  vs.extend([(x,shape(x,z)+.0015,z-.0010),(x,-.153,.3058)])
 for i in range(48):a=2*i;fs.append((a,a+2,a+3,a+1))
 make('CAB | aperture-fitted dashboard cowl',vs,fs,'Cabin',col='14 Dashboard',thick=.0006,outnormal=(0,0,1))
 return {'removed_surround':removed,'fixed_outer_ring_raw':ring,'smooth_seal_outline_raw':points,'regular_grid':True,'new_pane':ob.name}
