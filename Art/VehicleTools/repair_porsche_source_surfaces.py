"""Local constrained retriangulation of the actual Tripo surfaces.
Every patch keeps its original boundary vertices. Interior samples come from a
BVH containing ONLY that exterior patch, never the opposite side of a thin shell.
Source accessories, window outlines and silhouette features remain in place.
"""
import bpy,bmesh,json,math,hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import delaunay_2d_cdt, barycentric_transform
from mathutils.kdtree import KDTree
R=Path('C:/GrandTour/Art/Export/VehicleTools');O=R/'porsche-source-repair-v01';O.mkdir(exist_ok=True)
S=4.5
SOURCE=R/'porsche-shape-recovery-v01/Porsche_Source_Locked.blend'
MAN=O/'repair-report.json'
if MAN.exists():
 old=json.loads(MAN.read_text());p=O/'Porsche_Source_Repaired.blend'
 if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()!=old.get('blend_sha256'):raise RuntimeError('Preserve manual changes: choose another output revision')
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));sc=bpy.context.scene
donor=bpy.data.objects['WORKING - original shape unchanged']
donor.hide_render=True;donor.hide_set(True);donor.hide_select=True
parts=bpy.data.collections.new('Porsche - repaired original components');sc.collection.children.link(parts)
report={'source':str(SOURCE),'method':'Boundary-locked local surface patches sampled on original exterior charts. Original accessory meshes retained. No generic body sections.','patches':[],'parts':[]}

def active(o):
 for p in bpy.context.selected_objects:p.select_set(False)
 o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
def newmat(n,c,rough=.4,metal=0):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,1);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*c,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;return m
paint=newmat('Ivory body',(.59,.62,.60),.36,.16)
dark=newmat('Charcoal trim',(.035,.045,.049),.56)
glass=newmat('Clear slightly blue glazing',(.45,.65,.72),.08)
gp=glass.node_tree.nodes.get('Principled BSDF');gp.inputs['Transmission Weight'].default_value=1.;gp.inputs['IOR'].default_value=1.45
names={0:'Body_original_repaired',1:'Rear_axle',2:'Front_bullbar_and_carrier',3:'Suspension_FR',4:'Suspension_FL',5:'Rack_mounts',6:'Wiper_mount_A',7:'Cockpit_controls',8:'Seat_R',9:'Seat_L',10:'Rack_lower_rail',11:'Rack_upper_rail',12:'Wiper_mount_B',13:'Door_handle_R',14:'Mirror_R',15:'Mirror_L',16:'Door_handle_L',17:'Console',18:'Rack_rear_mount',19:'Roof_spare',20:'Exhaust_R',21:'Exhaust_L',22:'Skid_plate',23:'Rack_crossbar_front',24:'Auxiliary_light_R',25:'Auxiliary_light_L',26:'Rack_crossbar_rear',27:'Console_trim',28:'Door_card_R',29:'Door_card_L',30:'Rack_crossbar_middle',31:'Tailpipe_R',32:'Tailpipe_L',33:'Driveshaft',34:'Front_lightbar',35:'Gearlever',36:'Front_undertray',37:'Rear_carrier',38:'Roof_toolcase',49:'Headlamp_R',50:'Headlamp_L'}

def tidy(bm,merge=.000005):
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=merge)
 bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.000001)
 for _ in range(12):
  bad=[e for e in bm.edges if len(e.link_faces)>2]
  if not bad:break
  fs={min(e.link_faces,key=lambda f:f.calc_area()) for e in bad};bmesh.ops.delete(bm,geom=list(fs),context='FACES_ONLY')
 bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
 bm.normal_update()

# All source-island boundaries remain separated and UV-preserved.
for i in range(112):
 me=donor.data.copy();bm=bmesh.new();bm.from_mesh(me);il=bm.faces.layers.int.get('source_island')
 remove=[f for f in bm.faces if f[il]!=i or (i in (1,3,4) and abs(f.calc_center_median().x)>.145)]
 bmesh.ops.delete(bm,geom=remove,context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
 if not bm.faces:bm.free();bpy.data.meshes.remove(me);continue
 tidy(bm)
 bm.to_mesh(me);bm.free();ob=bpy.data.objects.new(names.get(i,'Original_trim_%03d'%i),me);parts.objects.link(ob);ob['source_island']=i;ob['geometry_role']='Original form retained with duplicate/sliver cleanup'
 report['parts'].append({'name':ob.name,'source_island':i})

body=bpy.data.objects['Body_original_repaired'];bm=bmesh.new();bm.from_mesh(body.data);bm.faces.ensure_lookup_table();bm.verts.ensure_lookup_table()
# Immutable source vertex records make fairing auditable.
original={v:v.co.copy() for v in bm.verts}
body.data.materials.append(paint);paint_id=len(body.data.materials)-1
body.data.materials.append(glass);glass_id=len(body.data.materials)-1
uv=bm.loops.layers.uv.active

def patch(name,predicate,axes,depthsign=1,spacing=.008,cap=.0012):
 """Replace each connected single-valued chart with a regular constrained mesh."""
 candidates={f for f in bm.faces if predicate(f.calc_center_median(),f.normal,f.calc_area())}
 groups=[]
 while candidates:
  seed=candidates.pop();group={seed};q=[seed]
  while q:
   f=q.pop()
   for e in f.edges:
    for g in e.link_faces:
     if g in candidates:candidates.remove(g);group.add(g);q.append(g)
  if len(group)>=6:groups.append(group)
 for gi,fs in enumerate(groups):
  # Avoid resampling folded/stacked sheets: all charts must have consistent normals.
  d=next(k for k in range(3) if k not in axes)
  if min(f.normal[d]*depthsign for f in fs)<.18:continue
  edges={e for f in fs for e in f.edges if sum(g in fs for g in e.link_faces)==1}
  boundary={v for e in edges for v in e.verts}
  degree={v:sum(v in e.verts for e in edges) for v in boundary}
  if not edges or any(n!=2 for n in degree.values()):continue
  vs=list({v for f in fs for v in f.verts});vi={v:i for i,v in enumerate(vs)}
  tris=[];fseq=[]
  for f in fs:
   if len(f.verts)!=3:raise RuntimeError('Expected source triangles')
   tris.append([vi[v] for v in f.verts]);fseq.append(f)
  flat=[Vector((v.co[axes[0]],v.co[axes[1]],0)) for v in vs]
  tree=BVHTree.FromPolygons(flat,tris,all_triangles=True)
  bvs=list(boundary);bidx={v:i for i,v in enumerate(bvs)}
  inputs=[Vector((v.co[axes[0]],v.co[axes[1]])) for v in bvs]
  inputs3=[v.co.copy() for v in bvs]
  ed=[(bidx[e.verts[0]],bidx[e.verts[1]]) for e in edges]
  def sample(u,v):
   hit=tree.ray_cast(Vector((u,v,1)),Vector((0,0,-1)),2)
   if hit[0] is None:return None
   f=fseq[hit[2]];a,b,c=[x.co for x in f.verts]
   q=barycentric_transform(Vector((u,v,0)),*[flat[vi[x]] for x in f.verts],a,b,c)
   return q,f
  # A local weighted polynomial estimates only depth; boundary coordinates remain fixed.
  arr=np.array([list(v.co) for v in vs]);uv_arr=arr[:,axes];dep=arr[:,d]
  def fair(q):
   delta=uv_arr-np.array([q[axes[0]],q[axes[1]]]);dist=np.sum(delta*delta,axis=1);ix=np.argsort(dist)[:min(28,len(vs))]
   dx=delta[ix];rad=max(spacing*2.5,float(np.sqrt(dist[ix[-1]])))
   w=np.exp(-dist[ix]/(rad*rad*.5));A=np.column_stack([np.ones(len(ix)),dx[:,0],dx[:,1],dx[:,0]**2,dx[:,0]*dx[:,1],dx[:,1]**2])
   coef=np.linalg.lstsq(A*np.sqrt(w[:,None]),dep[ix]*np.sqrt(w),rcond=1e-9)[0]
   # Fade the depth correction to zero at the actual interface.
   bd=min(math.hypot(q[axes[0]]-v.co[axes[0]],q[axes[1]]-v.co[axes[1]]) for v in boundary)
   move=max(-cap,min(cap,float(coef[0])-q[d]))*min(1,bd/(spacing*1.5))
   r=q.copy();r[d]+=move;return r,abs(move)
  lo=np.min(uv_arr,axis=0);hi=np.max(uv_arr,axis=0)
  moves=[]
  for u in np.arange(lo[0]+spacing*.5,hi[0],spacing):
   for v in np.arange(lo[1]+spacing*.5,hi[1],spacing):
    q=sample(float(u),float(v))
    if q is None:continue
    if min((Vector((u,v))-p).length for p in inputs[:len(bvs)])<spacing*.32:continue
    p,mv=fair(q[0]);inputs.append(Vector((u,v)));inputs3.append(p);moves.append(mv)
  try:cv,ce,cf,ov,oe,of=delaunay_2d_cdt(inputs,ed,[],0,1e-8)
  except Exception as ex:print('SKIP',name,str(ex),flush=True);continue
  newvs=[]
  for k,p in enumerate(cv):
   originals=ov[k]
   boundary_ids=[j for j in originals if j<len(bvs)]
   if boundary_ids:newvs.append(bvs[boundary_ids[0]])
   elif originals:newvs.append(bm.verts.new(inputs3[originals[0]]))
   else:
    q=sample(p.x,p.y)
    if q is None:newvs.append(None)
    else:newvs.append(bm.verts.new(q[0]))
  pending=[]
  for tri in cf:
   if len(tri)!=3 or any(newvs[k] is None for k in tri):continue
   c=sum((cv[k] for k in tri),Vector((0,0)))/3;q=sample(c.x,c.y)
   if q is None:continue
   ns=[newvs[k] for k in tri];normal=(ns[1].co-ns[0].co).cross(ns[2].co-ns[0].co)
   if normal[d]*depthsign<0:ns.reverse()
   srcf=q[1];srcuv=[Vector((*l[uv].uv,0)) for l in srcf.loops];flatf=[Vector((l.vert.co[axes[0]],l.vert.co[axes[1]],0)) for l in srcf.loops]
   uvs=[barycentric_transform(Vector((p.co[axes[0]],p.co[axes[1]],0)),*flatf,*srcuv) for p in ns]
   pending.append((ns,srcf.material_index,uvs))
  before=len(fs)
  bmesh.ops.delete(bm,geom=list(fs),context='FACES_ONLY')
  made=[]
  for vsf,mi,uvs in pending:
   try:f=bm.faces.new(vsf)
   except ValueError:continue
   f.material_index=mi;made.append(f)
   for l,q in zip(f.loops,uvs):l[uv].uv=(q.x,q.y)
  bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
  bm.normal_update()
  item={'patch':name+'_'+str(gi),'old_triangles':before,'new_triangles':len(made),'locked_boundary_vertices':len(boundary),'boundary_displacement_m':0.0,'max_depth_fairing_m':max(moves,default=0)*S}
  report['patches'].append(item);print('PATCH',item,flush=True)

# Disjoint charts: only broad outer skins. Thin pillars and window borders stay exact.
patch('bonnet',lambda c,n,a:abs(c.x)<.132 and -.419<c.y<-.178 and c.z>.147 and n.z>.4,(0,1),spacing=.006,cap=.0010)
for sign in (1,-1):
 patch('door_'+str(sign),lambda c,n,a:sign*c.x>.18 and -.130<c.y<.136 and .128<c.z<.233 and sign*n.x>.8,(1,2),sign,spacing=.007,cap=.0011)
 patch('wing_top_'+str(sign),lambda c,n,a:sign*c.x>.132 and sign*c.x<.206 and -.405<c.y<-.16 and c.z>.177 and n.z>.58,(0,1),spacing=.006,cap=.0014)
 patch('rear_quarter_'+str(sign),lambda c,n,a:sign*c.x>.193 and .145<c.y<.43 and .14<c.z<.255 and sign*n.x>.63,(1,2),sign,spacing=.0065,cap=.0013)
patch('roof',lambda c,n,a:abs(c.x)<.128 and -.015<c.y<.195 and c.z>.328 and n.z>.8,(0,1),spacing=.009,cap=.0006)
# Export normalized source positions to world metres only once at the end.
tidy(bm)
bm.to_mesh(body.data);bm.free()

# Import only the already measured wheel assemblies, preserving their world matrices.
with bpy.data.libraries.load(str(R/'porsche-working-v01/Porsche_Assembly.blend'),link=False) as (a,b):b.objects=[n for n in a.objects if n.startswith('Wheel_')]
wheel=[]
for ob in b.objects:
 if ob:parts.objects.link(ob);ob.hide_render=False;ob.hide_set(False);wheel.append(ob)
bpy.context.view_layer.update()
for ob in parts.objects:
 if ob in wheel:continue
 if ob.type=='MESH':
  for v in ob.data.vertices:v.co*=S
  for p in ob.data.polygons:p.use_smooth=True
  ob.data.set_sharp_from_angle(angle=.8)
  ob.color=(.52,.56,.58,1)
for ob in wheel:
 if ob.type=='MESH':ob.color=(.075,.085,.09,1)

# Original UVs retained for source parts; new chart vertices use source barycentric UVs.
sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.light='STUDIO';sc.display.shading.color_type='OBJECT';sc.display.shading.show_cavity=False;sc.display.shading.show_shadows=True;sc.display.shading.background_type='WORLD';sc.world.color=(.13,.14,.15)
sc.render.resolution_x=1600;sc.render.resolution_y=1100;sc.render.resolution_percentage=100
cam=sc.camera;cam.data.type='ORTHO';cam.data.ortho_scale=5.65
for name,pos,target in [('quarter',(5.4,-7.2,4.5),(0,0,.85)),('side',(7,0,.92),(0,0,.92)),('front',(0,-7,.92),(0,0,.92)),('rear-quarter',(5.4,7.2,3.8),(0,0,.85)),('top',(0,0,8),(0,0,.85))]:
 cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
cam.location=(5.4,-7.2,3.4);cam.rotation_euler=(Vector((0,0,.85))-cam.location).to_track_quat('-Z','Y').to_euler()
active(body)
for a in bpy.context.screen.areas:
 if a.type=='VIEW_3D':a.spaces.active.region_3d.view_location=(0,0,.8);a.spaces.active.region_3d.view_distance=6;a.spaces.active.overlay.show_extras=False
dest=O/'Porsche_Source_Repaired.blend';bpy.ops.wm.save_as_mainfile(filepath=str(dest))
report['blend_sha256']=hashlib.sha256(dest.read_bytes()).hexdigest();report['status']='Local patch repair in progress; inspect before delivery';MAN.write_text(json.dumps(report,indent=2))
print('SAVED',len(report['patches']),'PATCHES',flush=True)
