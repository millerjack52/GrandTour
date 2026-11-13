"""Conservative source repair. Keep original body coordinates; locally replace glazing.
No whole-body generated envelope, subdivision remesh, or generic vehicle dimensions.
"""
import bpy,bmesh,json,math,hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.geometry import convex_hull_2d,delaunay_2d_cdt,barycentric_transform,tessellate_polygon
from mathutils.bvhtree import BVHTree
R=Path('C:/GrandTour/Art/Export/VehicleTools');O=R/'porsche-preserved-repair-v02';O.mkdir(exist_ok=True)
DEST=O/'Porsche_Preserved_Repair.blend';MAN=O/'repair-report.json'
if DEST.exists() and MAN.exists():
 if hashlib.sha256(DEST.read_bytes()).hexdigest()!=json.loads(MAN.read_text()).get('blend_sha256'):raise RuntimeError('Preserve edited model; use a new revision')
bpy.ops.wm.open_mainfile(filepath=str(R/'porsche-source-repair-v01/Porsche_Source_Repaired.blend'));sc=bpy.context.scene
parts=bpy.data.collections['Porsche - repaired original components'];old=bpy.data.objects['Body_original_repaired'];bpy.data.objects.remove(old,do_unlink=True)
src=bpy.data.objects['WORKING - original shape unchanged'];me=src.data.copy();body=bpy.data.objects.new('Porsche original body - locally repaired',me);parts.objects.link(body)
bm=bmesh.new();bm.from_mesh(me);il=bm.faces.layers.int.get('source_island');bmesh.ops.delete(bm,geom=[f for f in bm.faces if f[il]!=0],context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.verts.ensure_lookup_table();bm.verts.index_update()
rawcoords=[v.co.copy() for v in bm.verts];rawtris=[[v.index for v in f.verts] for f in bm.faces];rawtree=BVHTree.FromPolygons(rawcoords,rawtris,all_triangles=True)
uv=bm.loops.layers.uv.active
report={'status':'Source-preserving repair under visual review','source':str(R/'porsche-shape-recovery-v01/Porsche_Source_Locked.blend'),'shape_authority':'Unchanged original Tripo mesh','windows':[],'no_generic_body_profiles':True,'body_fairing':'No broad body deformation: original exterior coordinates retained except sub-mm merge cleanup and glass-specific replacements.'}
def mat(n,c,rough=.4,metal=0):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,1);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*c,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;return m
paint=mat('Porsche ivory enamel',(.63,.66,.62),.38,.12);rubber=mat('Fitted rubber glazing seals',(.023,.032,.036),.65);glass=mat('Porsche clear glass',(.58,.72,.77),.07);glass.diffuse_color=(.15,.24,.28,1);gp=glass.node_tree.nodes.get('Principled BSDF');gp.inputs['Transmission Weight'].default_value=.98;gp.inputs['IOR'].default_value=1.45
steel=mat('Original hardware graphite',(.075,.09,.10),.42,.6);cloth=mat('Original tobacco seats',(.25,.14,.08),.8);lens=mat('Headlamp lenses',(.62,.68,.63),.15,.1)
def active(o):
 for x in bpy.context.selected_objects:x.select_set(False)
 o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
def mesh(name,vs,fs,material):
 me=bpy.data.meshes.new(name);me.from_pydata([Vector(v)*4.5 for v in vs],[],fs);me.update();o=bpy.data.objects.new(name,me);parts.objects.link(o);me.materials.append(material)
 bb=bmesh.new();bb.from_mesh(me);bmesh.ops.recalc_face_normals(bb,faces=list(bb.faces));bb.to_mesh(me);bb.free()
 for f in me.polygons:f.use_smooth=True
 me.set_sharp_from_angle(angle=.85);return o
def tube(name,ps,r,material):
 cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.bevel_depth=r*4.5;cu.bevel_resolution=2;cu.resolution_u=1;cu.use_fill_caps=True;sp=cu.splines.new('POLY');sp.points.add(len(ps)-1)
 for p,q in zip(sp.points,ps):p.co=(*tuple(Vector(q)*4.5),1)
 sp.use_cyclic_u=True;o=bpy.data.objects.new(name,cu);parts.objects.link(o);cu.materials.append(material);active(o);bpy.ops.object.convert(target='MESH');return bpy.context.object
def signed_area(ps):return sum(a.x*b.y-a.y*b.x for a,b in zip(ps,ps[1:]+ps[:1]))/2
def make_glass(name,boundary,axes,samples,surface_faces=None):
 d=next(k for k in range(3) if k not in axes)
 ps=[Vector((p[axes[0]],p[axes[1]])) for p in boundary]
 if signed_area(ps)<0:boundary.reverse();ps.reverse()
 if surface_faces:
  # Missing donor triangles leave narrow inward spikes in the detected glass
  # perimeter. Remove only sharp re-entrant corners, not its broad curved edges.
  for _ in range(40):
   changed=False
   for i in range(len(boundary)):
    a,b,c=[Vector((boundary[j%len(boundary)][axes[0]],boundary[j%len(boundary)][axes[1]])) for j in (i-1,i,i+1)]
    u=b-a;v=c-b;cross=u.x*v.y-u.y*v.x
    if u.length<1e-7 or v.length<1e-7 or abs(cross)<1e-8:
     boundary.pop(i);changed=True;break
   if not changed:break
  for _ in range(20):
   changed=False
   for i in range(len(boundary)):
    a,b,c=[Vector((boundary[j%len(boundary)][axes[0]],boundary[j%len(boundary)][axes[1]])) for j in (i-1,i,i+1)]
    u=b-a;v=c-b;cross=u.x*v.y-u.y*v.x
    if cross<0 and math.atan2(-cross,u.dot(v))>.7:
     boundary.pop(i);changed=True;break
   if not changed:break
 # Subdivide original boundary segments; no corner relocation.
 boundary2=[]
 for a,b in zip(boundary,boundary[1:]+boundary[:1]):
  count=max(1,math.ceil((b-a).length/.006))
  for j in range(count):boundary2.append(a.lerp(b,j/count))
 boundary=boundary2;ps=[Vector((p[axes[0]],p[axes[1]])) for p in boundary]
 arr=np.array([tuple(p) for p in samples]);uvv=arr[:,axes]
 A=np.column_stack([np.ones(len(arr)),uvv[:,0],uvv[:,1],uvv[:,0]**2,uvv[:,0]*uvv[:,1],uvv[:,1]**2]);coef=np.linalg.lstsq(A,arr[:,d],rcond=None)[0]
 buv=np.array([[p[axes[0]],p[axes[1]]] for p in boundary]);br=np.array([p[d]-float(np.array([1,p[axes[0]],p[axes[1]],p[axes[0]]**2,p[axes[0]]*p[axes[1]],p[axes[1]]**2])@coef) for p in boundary])
 def depth(u,v):
  if surface_faces:
   h=flat_tree.ray_cast(Vector((u,v,1)),Vector((0,0,-1)),2)
   if h[0] is not None:
    tri=surface_faces[h[2]]
    q=barycentric_transform(Vector((u,v,0)),*[Vector((p[axes[0]],p[axes[1]],0)) for p in tri],*tri)
    return float(q[d])
  ds=np.sum((buv-np.array([u,v]))**2,axis=1);w=1/np.maximum(ds,1e-10)**1.5
  return float(np.array([1,u,v,u*u,u*v,v*v])@coef)+float(np.sum(w*br)/np.sum(w))
 if surface_faces:
  ff=[Vector((p[axes[0]],p[axes[1]],0)) for tri in surface_faces for p in tri];flat_tree=BVHTree.FromPolygons(ff,[(i,i+1,i+2) for i in range(0,len(ff),3)],all_triangles=True)
 inp=ps.copy();vs=boundary.copy();lo=np.min(uvv,axis=0);hi=np.max(uvv,axis=0)
 def inside(q):
  result=False
  for a,b in zip(ps,ps[1:]+ps[:1]):
   if (a.y>q.y)!=(b.y>q.y) and q.x<(b.x-a.x)*(q.y-a.y)/(b.y-a.y)+a.x:result=not result
  return result
 for u in np.arange(lo[0]+.003,hi[0],.008):
  for v in np.arange(lo[1]+.003,hi[1],.008):
   q=Vector((u,v))
   if inside(q) and min((q-p).length for p in ps)>.002:
    p=Vector((0,0,0));p[axes[0]]=u;p[axes[1]]=v;p[d]=depth(u,v);inp.append(q);vs.append(p)
 cv,ce,cf,ov,oe,of=delaunay_2d_cdt(inp,[],[list(range(len(ps)))],1,1e-8)
 points=[]
 for k,p in enumerate(cv):
  if ov[k]:points.append(vs[ov[k][0]])
  else:
   q=Vector((0,0,0));q[axes[0]]=p.x;q[axes[1]]=p.y;q[d]=depth(p.x,p.y);points.append(q)
 # Fair the pane only, keeping every source perimeter vertex fixed. Do not
 # reproduce generated dents as optically distorted glass.
 fixed={k for k in range(len(points)) if ov[k] and min(ov[k])<len(boundary)}
 adjacency=[set() for p in points]
 for f in cf:
  for a,b in zip(f,f[1:]+f[:1]):adjacency[a].add(b);adjacency[b].add(a)
 for _ in range(180):
  values={}
  for k,p in enumerate(points):
   if k in fixed or not adjacency[k]:continue
   weights=[(j,1/max((cv[k]-cv[j]).length,1e-7)) for j in adjacency[k]]
   values[k]=p[d]*.25+.75*sum(points[j][d]*w for j,w in weights)/sum(w for j,w in weights)
  for k,v in values.items():points[k][d]=v
 ob=mesh(name,points,cf,glass)
 active(ob);md=ob.modifiers.new('Glass thickness 2 mm','SOLIDIFY');md.thickness=.002;md.offset=-1;bpy.ops.object.modifier_apply(modifier=md.name)
 ob.data.set_sharp_from_angle(angle=.45)
 tube(name+' - original outline gasket',boundary,.00075,rubber)
 error=[abs(depth(arr[i,axes[0]],arr[i,axes[1]])-arr[i,d])*4.5 for i in range(len(arr))]
 report['windows'].append({'name':name,'axes':axes,'boundary_vertices':len(boundary),'boundary_note':'Original perimeter segments retained; sharp inward notches from missing source triangles closed locally.','source_sample_residual_max_m':max(error),'source_sample_residual_mean_m':sum(error)/len(error)})
 return ps,depth

# Source-based selectors identify broad glass sheets, then use their actual convex perimeter.
windows=[
 ('Windscreen',(0,2),lambda c,n,a:abs(c.x)<.155 and -.166<c.y<-.032 and .24<c.z<.33 and n.dot(Vector((0,-.62,.78)))>.80 and a>.00013 and abs(c.z-(.244+.77*(c.y+.165)-.030*(c.x/.14)**2))<.009),
 ('Rear glass',(0,2),lambda c,n,a:abs(c.x)<.132 and .217<c.y<.349 and .251<c.z<.327 and n.dot(Vector((0,.63,.78)))>.89 and a>.00013),
 ('Quarter glass L',(1,2),lambda c,n,a:c.x>.15 and .143<c.y<.247 and .242<c.z<.305 and n.x>.92 and a>.00010),
 ('Quarter glass R',(1,2),lambda c,n,a:c.x<-.15 and .143<c.y<.247 and .242<c.z<.305 and n.x<-.92 and a>.00010)
]
# Keep source triangles with interpolated UVs; replace only the glass volume.
faces=[([v.co.copy() for v in f.verts],[l[uv].uv.copy() for l in f.loops],f.material_index) for f in bm.faces]
for name,axes,pred in windows:
 chosen=[f for f in bm.faces if pred(f.calc_center_median(),f.normal,f.calc_area())]
 if len(chosen)<3:print('GLASS_SKIP',name,len(chosen),flush=True);continue
 samples=list({v for f in chosen for v in f.verts});ss=[v.co.copy() for v in samples];coords2=[Vector((v.co[axes[0]],v.co[axes[1]])) for v in samples];vid={v:i for i,v in enumerate(samples)};tri=[[vid[v] for v in f.verts] for f in chosen]
 cv,ce,cf,ov,oe,of=delaunay_2d_cdt(coords2,[],tri,1,1e-8)
 ec={}
 for f in cf:
  for a,b in zip(f,f[1:]+f[:1]):
   key=tuple(sorted((a,b)));ec[key]=ec.get(key,0)+1
 es={e for e,n in ec.items() if n==1};loops=[]
 while es:
  a,b=es.pop();loop=[a,b]
  while loop[-1]!=loop[0]:
   candidates=[e for e in es if loop[-1] in e]
   if not candidates:break
   e=candidates[0];es.remove(e);loop.append(e[0] if e[1]==loop[-1] else e[1])
  if len(loop)>3 and loop[-1]==loop[0]:loops.append(loop[:-1])
 if not loops:raise RuntimeError('No source glass perimeter: '+name)
 loop=max(loops,key=lambda q:abs(signed_area([cv[k] for k in q])))
 flat=BVHTree.FromPolygons([Vector((p.x,p.y,0)) for p in coords2],tri,all_triangles=True)
 boundary=[]
 for k in loop:
  q=cv[k];h=flat.find_nearest(Vector((q.x,q.y,0)));fi=tri[h[2]];boundary.append(barycentric_transform(Vector((q.x,q.y,0)),*[Vector((coords2[j].x,coords2[j].y,0)) for j in fi],*[ss[j] for j in fi]))
 poly,depth=make_glass(name,boundary,axes,ss,[[v.co.copy() for v in f.verts] for f in chosen]);d=next(k for k in range(3) if k not in axes)
 cut_triangles=[[poly[p].copy() if isinstance(p,int) else Vector((p.x,p.y)) for p in t] for t in tessellate_polygon([[Vector((p.x,p.y,0)) for p in poly]])]
 for t in cut_triangles:
  if signed_area(t)<0:t.reverse()
 newfaces=[];removed=0
 for xyz,uvs,mi in faces:
  center=sum(xyz,Vector())/len(xyz)
  if any(max(p[axes[k]] for p in xyz)<min(q[k] for q in poly)-1e-8 or min(p[axes[k]] for p in xyz)>max(q[k] for q in poly)+1e-8 for k in (0,1)):
   newfaces.append((xyz,uvs,mi));continue
  if abs(center[d]-depth(center[axes[0]],center[axes[1]]))>(.035 if name in ('Windscreen','Rear glass') else .018):
   newfaces.append((xyz,uvs,mi));continue
  # Subtract the actual concave outline as a union of its triangulated regions.
  pieces=[list(zip(xyz,uvs))]
  for cut in cut_triangles:
   remaining=[]
   for candidate in pieces:
    if any(all((b.x-a.x)*(p[axes[1]]-a.y)-(b.y-a.y)*(p[axes[0]]-a.x)<-1e-10 for p,u in candidate) for a,b in zip(cut,cut[1:]+cut[:1])):
     remaining.append(candidate);continue
    outside=[]
    for a,b in zip(cut,cut[1:]+cut[:1]):
     if not candidate:break
     def distance(p):return (b.x-a.x)*(p[axes[1]]-a.y)-(b.y-a.y)*(p[axes[0]]-a.x)
     ins=[];outs=[]
     for (p,pu),(q,qu) in zip(candidate,candidate[1:]+candidate[:1]):
      dp=distance(p);dq=distance(q);pin=dp>=0;qin=dq>=0
      (ins if pin else outs).append((p,pu))
      if pin!=qin:
       t=max(0.,min(1.,dp/(dp-dq)));hit=(p.lerp(q,t),pu.lerp(qu,t));ins.append(hit);outs.append(hit)
     if len(outs)>=3:outside.append(outs)
     candidate=ins
    if candidate:removed+=1
    remaining.extend(outside)
   pieces=remaining
   if not pieces:break
  for chunk in pieces:newfaces.append(([p for p,q in chunk],[q for p,q in chunk],mi))
 faces=newfaces;print('GLASS',name,'seeds',len(chosen),'removed',removed,flush=True)
bm.free()
# Recreate the unchanged remaining skins and share every coincident seam vertex.
nb=bmesh.new();nuv=nb.loops.layers.uv.new('Source UV');keymap={}
for xyz,uvs,mi in faces:
 vv=[]
 for p in xyz:
  key=tuple(round(float(t),8) for t in p)
  if key not in keymap:keymap[key]=nb.verts.new(p)
  vv.append(keymap[key])
 if len(set(vv))<3:continue
 try:f=nb.faces.new(vv)
 except ValueError:continue
 f.material_index=mi
 for l,q in zip(f.loops,uvs):l[nuv].uv=q
bmesh.ops.remove_doubles(nb,verts=list(nb.verts),dist=.00001);bmesh.ops.dissolve_degenerate(nb,edges=list(nb.edges),dist=.000001)
for _ in range(12):
 bad=[e for e in nb.edges if len(e.link_faces)>2]
 if not bad:break
 bmesh.ops.delete(nb,geom=list({min(e.link_faces,key=lambda f:f.calc_area()) for e in bad}),context='FACES_ONLY')
bmesh.ops.delete(nb,geom=[v for v in nb.verts if not v.link_faces],context='VERTS');bmesh.ops.recalc_face_normals(nb,faces=list(nb.faces))
# Resolve clipping T-junctions without moving the surface: split long edges at
# already-existing coincident vertices, then weld those exact pairs.
from mathutils.kdtree import KDTree
splits=0
for repair in range(2):
 vv=list({v for e in nb.edges if e.is_boundary for v in e.verts});kd=KDTree(len(vv))
 for i,v in enumerate(vv):kd.insert(v.co,i)
 kd.balance();made=0
 for edge in list(nb.edges):
  if not edge.is_valid or not edge.is_boundary:continue
  a,b=edge.verts;delta=b.co-a.co;length=delta.length
  if length<.00001:continue
  hits=[]
  for p,i,dist in kd.find_range((a.co+b.co)/2,length/2+.000003):
   v=vv[i]
   if v in (a,b) or not v.is_valid:continue
   t=(p-a.co).dot(delta)/(length*length)
   if .00001<t<.99999 and (p-a.co-delta*t).length<.000002:hits.append((t,p.copy()))
  start=a;end=b;current=edge;previous=0
  for t,p in sorted(hits,key=lambda x:x[0]):
   if t-previous<1e-6:continue
   newedge,newv=bmesh.utils.edge_split(current,start,(t-previous)/(1-previous));newv.co=p;made+=1
   current=next(e for e in newv.link_edges if end in e.verts);start=newv;previous=t
 bmesh.ops.remove_doubles(nb,verts=list(nb.verts),dist=.000002);bmesh.ops.dissolve_degenerate(nb,edges=list(nb.edges),dist=.0000003);splits+=made
 if not made:break
report['clipping_edge_junctions_resolved']=splits
zero=[f for f in nb.faces if f.calc_area()<1e-13]
if zero:bmesh.ops.delete(nb,geom=zero,context='FACES_ONLY')
bmesh.ops.delete(nb,geom=[v for v in nb.verts if not v.link_faces],context='VERTS')
# Cap isolated small tears only; window apertures and wheel openings are retained.
edges={e for e in nb.edges if e.is_boundary};caps=0
while edges:
 e=edges.pop();group={e};todo=list(e.verts);vv=set(e.verts)
 while todo:
  v=todo.pop()
  for ee in v.link_edges:
   if ee in edges:edges.remove(ee);group.add(ee);vv.update(ee.verts);todo.extend(ee.verts)
 ext=max(max(v.co[k] for v in vv)-min(v.co[k] for v in vv) for k in range(3))
 if ext<.018 and len(group)<=24 and all(sum(v in e.verts for e in group)==2 for v in vv):
  bmesh.ops.holes_fill(nb,edges=list(group),sides=24);caps+=1
report['small_tear_loops_closed']=caps
# Pair only nearly coplanar compatible triangles. This does not move the body.
bmesh.ops.join_triangles(nb,faces=[f for f in nb.faces if len(f.verts)==3],angle_face_threshold=.15,angle_shape_threshold=.5,cmp_uvs=True)
# Clipping can create hairline slivers at coincident source sheets. Remove only
# sub-micron-width faces, then separate overlapping sheets without moving them.
slivers=[f for f in nb.faces if f.calc_area()<5e-10]
if slivers:bmesh.ops.delete(nb,geom=slivers,context='FACES_ONLY')
bmesh.ops.recalc_face_normals(nb,faces=list(nb.faces))
ambiguous=[e for e in nb.edges if len(e.link_faces)>2 or (e.is_manifold and not e.is_contiguous)]
report['overlapping_source_sheet_edges_separated']=len(ambiguous)
if ambiguous:bmesh.ops.split_edges(nb,edges=ambiguous)
bmesh.ops.recalc_face_normals(nb,faces=list(nb.faces))
nb.to_mesh(me);nb.free()
me.materials.clear();me.materials.append(paint)
for v in me.vertices:v.co*=4.5
for f in me.polygons:f.material_index=0;f.use_smooth=True
me.set_sharp_from_angle(angle=1.65)
active(body);md=body.modifiers.new('Area weighted panel normals - geometry unchanged','WEIGHTED_NORMAL');md.keep_sharp=True;md.weight=35;md.mode='FACE_AREA_WITH_ANGLE';bpy.ops.object.modifier_apply(modifier=md.name)

# Trace original open door windows by rays into the body-only reference.
for sign,kind in [(1,'Door'),(-1,'Door'),(1,'Vent'),(-1,'Vent')]:
 center=Vector((.040,.278) if kind=='Door' else (-.056,.260));boundary=[]
 def hit_side(y,z):
  hit=rawtree.ray_cast(Vector((sign*.5,y,z)),Vector((-sign,0,0)),1.)
  if hit[0] is None:return None
  p=hit[0];expected=.176-.33*(z-.24)
  if sign*p.x<expected-.007:return None
  return p
 for j in range(96):
  a=2*math.pi*j/96;v=Vector((math.cos(a),math.sin(a)));last=0.;found=None
  for r in np.arange(.0008,.18,.0008):
   q=center+v*r;h=hit_side(q.x,q.y)
   if h is not None:
    lo=last;hi=float(r)
    for _ in range(12):
     mid=(lo+hi)/2;q=center+v*mid
     if hit_side(q.x,q.y) is None:lo=mid
     else:hi=mid
    q=center+v*hi;found=hit_side(q.x,q.y);break
   last=float(r)
  if found is not None:boundary.append(found)
 if len(boundary)==96:
  # Ray trace uses the actual aperture, including its curved upper corners.
  coords=[Vector((p.y,p.z)) for p in boundary];h=convex_hull_2d(coords);bs=[boundary[i] for i in h]
  make_glass(kind+' glass '+('L' if sign>0 else 'R'),bs,(1,2),boundary)

# Preserve original accessories. Correct winding before smooth shading; no location changes.
for ob in parts.objects:
 if ob.type!='MESH' or ob==body or ob.name.startswith(('Windscreen','Rear glass','Quarter glass','Door glass','Vent glass')):continue
 bb=bmesh.new();bb.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bb,faces=list(bb.faces));bb.to_mesh(ob.data);bb.free()
 if ob.name.startswith('Wheel_'):continue
 if ob.get('source_island') in (8,9):m=cloth
 elif ob.get('source_island') in (47,50,24,25):m=lens
 elif ob.get('source_island') in (14,15,38):m=paint
 else:m=steel
 ob.data.materials.clear();ob.data.materials.append(m)
 for f in ob.data.polygons:f.material_index=0;f.use_smooth=True
 ob.data.set_sharp_from_angle(angle=.72)

sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.light='STUDIO';sc.display.shading.color_type='MATERIAL';sc.display.shading.show_cavity=False;sc.display.shading.show_shadows=True;sc.display.shading.background_type='WORLD';sc.world.color=(.13,.14,.15)
sc.render.resolution_x=1600;sc.render.resolution_y=1100;sc.render.resolution_percentage=100
cam=sc.camera;cam.data.type='ORTHO';cam.data.ortho_scale=5.65
for name,pos,target,scale in [('quarter',(5.4,-7.2,3.7),(0,0,.92),5.65),('side',(7,0,.92),(0,0,.92),5.65),('rear',(5.4,7.2,3.8),(0,0,.92),5.65),('front',(0,-8,.92),(0,0,.92),4.4),('top',(0,0,8),(0,0,.92),5.65),('windscreen',(3,-4,2.6),(0,-.38,1.30),2.6)]:
 cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale;sc.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
cam.location=(5.4,-7.2,3.7);cam.rotation_euler=(Vector((0,0,.92))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=5.65
active(body);bpy.ops.wm.save_as_mainfile(filepath=str(DEST));report['blend_sha256']=hashlib.sha256(DEST.read_bytes()).hexdigest();MAN.write_text(json.dumps(report,indent=2))
print('SOURCE_PRESERVED_REPAIR_SAVED',flush=True)
