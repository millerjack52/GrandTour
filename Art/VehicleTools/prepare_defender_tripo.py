"""Geometry-only, non-destructive separation of the supplied Defender Tripo mesh.

Source surfaces are clipped at measured panel boundaries, not regenerated from
car proportions. Rebuilt wheel components use measured source tyre envelopes.
"""
import bpy,bmesh,json,math,hashlib,os
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.geometry import barycentric_transform
from mathutils.bvhtree import BVHTree
ROOT=Path('C:/GrandTour/Art/Export/VehicleTools')
SRC=ROOT/'defender-tripo-v01'
OUT=ROOT/'defender-separated-v07';OUT.mkdir(exist_ok=True)
DATA=json.loads((SRC/'island-geometry.json').read_text())
SCALE=4.6 # uniform only: retain Tripo shape, approximately 2.8m wheelbase
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath='C:/Users/mille/Downloads/defender110tripo.glb')
original=next(o for o in bpy.context.scene.objects if o.type=='MESH')
bpy.context.view_layer.objects.active=original;bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
sm=original.data;sm.calc_loop_triangles()
source_vertices=[v.co.copy() for v in sm.vertices]
source_tris=[tuple(t.vertices) for t in sm.loop_triangles]
source_normals=[[sm.corner_normals[i].vector.copy() for i in t.loops] for t in sm.loop_triangles]
source_bvh=BVHTree.FromPolygons(source_vertices,source_tris,all_triangles=True)
bpy.data.objects.remove(original,do_unlink=True)
sc=bpy.context.scene;sc.unit_settings.system='METRIC';sc.unit_settings.scale_length=1
cols={}
for name in ['01 Body and roof','02 Opening panels','03 Glazing','04 Wheels','05 Lamps and fittings','06 Chassis and closure','80 Controls','90 Studio','99 Original reference']:
 c=bpy.data.collections.new(name);sc.collection.children.link(c);cols[name]=c
MATS={}
for name,color in [('Body',(.46,.51,.53,1)),('Panel',(.42,.48,.51,1)),('Glass',(.16,.23,.27,1)),('Rubber',(.10,.12,.13,1)),('Metal',(.36,.40,.42,1)),('Light',(.62,.65,.65,1)),('Inner',(.22,.26,.28,1))]:
 m=bpy.data.materials.new('Review | '+name);m.diffuse_color=color;m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=color;p.inputs['Roughness'].default_value=.65;MATS[name]=m
manifest={'source':'C:/Users/mille/Downloads/defender110tripo.glb','source_sha256':hashlib.sha256(Path('C:/Users/mille/Downloads/defender110tripo.glb').read_bytes()).hexdigest(),'scope':'Separated geometry with neutral inspection materials. No textures, UVs, cockpit or Unreal driving setup.','uniform_scale':SCALE,'parts':[],'replaced_source_islands':[],'checks':{}}
controls={};owned=[]
def empty(name,pivot,parent=None):
 o=bpy.data.objects.new(name,None);cols['80 Controls'].objects.link(o);o.location=Vector(pivot)*SCALE;o.empty_display_size=.12;o.empty_display_type='ARROWS'
 if parent:o.parent=parent;o.matrix_parent_inverse=parent.matrix_world.inverted()
 controls[name]=o;return o
vehicle=empty('DEFENDER | assembly',(0,0,0))
def parent_keep(o,p):
 bpy.context.view_layer.update()
 mat=o.matrix_world.copy();o.parent=p;o.matrix_world=mat
def mesh_obj(name,polys,col='01 Body and roof',mat='Body',thickness=0,parent=None):
 # Weld identical clip intersections; retain the source outer positions exactly.
 verts=[];faces=[];lookup={}
 for poly in polys:
  ids=[]
  for p in poly:
   key=tuple(round(float(x),8) for x in p)
   if key not in lookup:lookup[key]=len(verts);verts.append(tuple(x*SCALE for x in p))
   ids.append(lookup[key])
  ids=list(dict.fromkeys(ids))
  if len(ids)>2:faces.append(ids)
 if not faces:return None
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
 ob=bpy.data.objects.new(name,me);cols[col].objects.link(ob);me.materials.append(MATS[mat]);owned.append(ob)
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000002);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.000001)
 bmesh.ops.triangulate(bm,faces=list(bm.faces))
 tiny=[f for f in bm.faces if f.calc_area()<1e-12]
 if tiny:bmesh.ops.delete(bm,geom=tiny,context='FACES')
 if thickness:
  branched=[e for e in bm.edges if len(e.link_faces)>2]
  if branched:bmesh.ops.split_edges(bm,edges=branched)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 if thickness:
  # A single imported point can join several unrelated surface fans. Give each
  # fan its own point before building the return walls; positions do not change.
  fanverts=[];corner={}
  for v in bm.verts:
   todo=set(v.link_faces)
   while todo:
    seed=todo.pop();seen={seed};queue=[seed]
    while queue:
     f=queue.pop()
     for e in f.edges:
      if v not in e.verts or len(e.link_faces)!=2:continue
      for g in e.link_faces:
       if g in todo:todo.remove(g);seen.add(g);queue.append(g)
    idx=len(fanverts);fanverts.append(v.co.copy())
    for f in seen:corner[(v,f)]=idx
  fanfaces=[[corner[(v,f)] for v in f.verts] for f in bm.faces]
  me.clear_geometry();me.from_pydata(fanverts,[],fanfaces);me.update()
 else:bm.to_mesh(me)
 bm.free()
 for p in me.polygons:p.use_smooth=True
 if not name.startswith(('Rebuilt','SOURCE','Cabin |')):
  custom=[]
  if name.startswith('Glass'):
   avg=sum((p.normal*p.area for p in me.polygons),Vector()).normalized()
   custom=[avg]*len(me.loops)
  else:
   for loop in me.loops:
    point=me.vertices[loop.vertex_index].co/SCALE
    hit,normal,idx,dist=source_bvh.find_nearest(point)
    if idx is None:custom.append(loop.normal);continue
    tri=source_tris[idx];norms=source_normals[idx]
    custom.append(barycentric_transform(hit,*[source_vertices[k] for k in tri],*norms).normalized())
  me.normals_split_custom_set(custom)
 if thickness:
  # Build a bounded inward extrusion explicitly. Imported T junctions make
  # Blender's averaged solidify directions unreliable on these thin panels.
  frontverts=[v.co.copy() for v in me.vertices];frontfaces=[list(p.vertices) for p in me.polygons]
  normals=[Vector() for v in me.vertices]
  loopnormals=[n.vector.copy() for n in me.corner_normals]
  for p in me.polygons:
   for li in p.loop_indices:normals[me.loops[li].vertex_index]+=loopnormals[li]*max(p.area,1e-8)
  normals=[n.normalized() if n.length>1e-8 else Vector((0,0,1)) for n in normals]
  nv=len(frontverts);newverts=frontverts+[p-n*thickness for p,n in zip(frontverts,normals)]
  newfaces=list(frontfaces)+[[idx+nv for idx in reversed(f)] for f in frontfaces]
  uses={}
  for f in frontfaces:
   for a,b in zip(f,f[1:]+f[:1]):uses.setdefault(tuple(sorted((a,b))),[]).append((a,b))
  for es in uses.values():
   if len(es)==1:
    a,b=es[0];newfaces.append([b,a,a+nv,b+nv])
  newme=bpy.data.meshes.new(name+' | closed thickness');newme.from_pydata(newverts,[],newfaces);newme.materials.append(MATS[mat]);newme.update()
  newnormals=[];at=0
  for p in me.polygons:newnormals.extend(loopnormals[i] for i in p.loop_indices)
  for p in me.polygons:newnormals.extend(-loopnormals[i] for i in reversed(p.loop_indices))
  for p in list(newme.polygons)[len(frontfaces)*2:]:newnormals.extend([p.normal.copy()]*len(p.vertices))
  for p in newme.polygons:p.use_smooth=True
  newme.normals_split_custom_set(newnormals)
  ob.data=newme;bpy.data.meshes.remove(me);me=newme
  ob['closed_thickness_m']=thickness
  ob['preserved_outer_vertex_count']=nv
 ob['source_surface']='Tripo geometry retained' if 'Rebuilt' not in name else 'Rebuilt measured component'
 parent_keep(ob,parent or vehicle)
 manifest['parts'].append({'name':name,'collection':col,'source_faces':len(polys),'thickness_m':thickness})
 return ob
def record_polys(rec):return [[Vector(rec['vertices'][i]) for i in f] for f in rec['faces']]
def clip(poly,n,d):
 inside=[];outside=[]
 if all(abs(n.dot(p)-d)<1e-9 for p in poly):return poly,[]
 for i,a in enumerate(poly):
  b=poly[(i+1)%len(poly)];da=n.dot(a)-d;db=n.dot(b)-d
  if da>=-1e-9:inside.append(a)
  if da<=1e-9:outside.append(a)
  if (da>1e-9 and db<-1e-9) or (da<-1e-9 and db>1e-9):
   q=a+(b-a)*(da/(da-db));inside.append(q);outside.append(q)
 return inside,outside
def partition(polys,planes):
 kept=[];rest=[]
 for poly in polys:
  cur=poly
  for n,d in planes:
   cur,other=clip(cur,Vector(n),d)
   if len(other)>=3:rest.append(other)
   if len(cur)<3:break
  if len(cur)>=3:kept.append(cur)
 return kept,rest
def plane(axis,value,greater=True):
 n=[0,0,0];n[axis]=1 if greater else -1;return n,value if greater else -value
def polyplanes(poly,axes):
 area=sum(poly[i][0]*poly[(i+1)%len(poly)][1]-poly[(i+1)%len(poly)][0]*poly[i][1] for i in range(len(poly)))
 if area<0:poly=list(reversed(poly))
 result=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  n=[0,0,0];n[axes[0]]=-(b[1]-a[1]);n[axes[1]]=b[0]-a[0];result.append((n,n[axes[0]]*a[0]+n[axes[1]]*a[1]))
 return result
remaining=record_polys(DATA[0])
def take(name,planes,col,mat,thickness,parent=None):
 global remaining
 kept,remaining=partition(remaining,planes)
 assert kept,'Empty source region '+name
 return mesh_obj(name,kept,col,mat,thickness,parent)
door_parents={}
for side,sign in [('L',1),('R',-1)]:
 for row,y in [('Front',-.195),('Rear',.023)]:door_parents[(side,row)]=empty('Hinge | '+side+' '+row+' door',(sign*.219,y,.29))
rearhinge=empty('Hinge | Rear door',(-.139,.447,.28))
hoodhinge=empty('Hinge | Bonnet',(0,-.203,.295))
roofmount=empty('Mount | Roof cap',(0,0,0))
for side,sign in [('L',1),('R',-1)]:
 sideplane=plane(0,.17*sign,sign>0)
 for row,outline in [
  ('Front',[(-.177,.326),(-.131,.414),(-.011,.414),(-.011,.326)]),
  ('Rear',[(.032,.326),(.032,.414),(.168,.414),(.168,.326)]),
  ('Cargo',[(.211,.337),(.211,.407),(.397,.407),(.397,.337)])]:
  take('Glass | '+side+' '+row, [sideplane]+polyplanes(outline,(1,2)),'03 Glazing','Glass',.003,door_parents.get((side,row)))
 # The side door perimeter follows the sloped A pillar and rear arch crossover.
 for row,outline in [
  ('Front',[(-.195,.150),(.007,.150),(.007,.440),(-.134,.440),(-.195,.314)]),
  ('Rear',[(.026,.150),(.108,.150),(.180,.234),(.180,.440),(.026,.440)])]:
  take('Door | '+side+' '+row,[sideplane]+polyplanes(outline,(1,2)),'02 Opening panels','Panel',.020,door_parents[(side,row)])
for side,sign in [('L',1),('R',-1)]:
 take('Glass | Windscreen '+side,[plane(0,.009*sign,sign>0),plane(0,.172*sign,sign<0),plane(2,.334),plane(2,.427,False),plane(1,-.12,False)],'03 Glazing','Glass',.003)
take('Glass | Rear',[plane(0,-.105),plane(0,.105,False),plane(2,.334),plane(2,.413,False),plane(1,.40)],'03 Glazing','Glass',.003,rearhinge)
take('Roof | Complete cap',[plane(2,.4418)],'01 Body and roof','Body',.012,roofmount)
take('Bonnet | Source pressing',polyplanes([(-.105,-.476),(.105,-.476),(.187,-.203),(-.187,-.203)],(0,1))+[plane(2,.277)],'02 Opening panels','Panel',.018,hoodhinge)
take('Door | Rear',[plane(0,-.123),plane(0,.123,False),plane(2,.162),plane(2,.438,False),plane(1,.421)],'02 Opening panels','Panel',.020,rearhinge)
# Extract the round lens surfaces from the fused front wing faces.
for side,sign in [('L',1),('R',-1)]:
 circle=[(sign*.147+.015*math.cos(t*math.tau/16),.226+.015*math.sin(t*math.tau/16)) for t in range(16)]
 take('Lamp | '+side+' main lens',polyplanes(circle,(0,2))+[plane(1,-.460,False)],'05 Lamps and fittings','Light',.003)
body=mesh_obj('Body | Retained source shell',remaining,'01 Body and roof','Body',.012)
def bbox(rec):
 a,b=[Vector(p) for p in rec['bounds']];return a,b,(a+b)/2,b-a
wheel_records=[]
for rec in DATA[1:]:
 a,b,c,d=bbox(rec);side='L' if c.x>0 else 'R'
 if len(rec['vertices'])==265 and ((d.z>.18 and d.y>.17) or d.z>.18 and c.y>.44):
  wheel_records.append(rec);manifest['replaced_source_islands'].append(rec['id']);continue
 name='Fitting';col='05 Lamps and fittings';mat='Metal';par=None
 if c.z<.165 and c.y>-.46 and c.y<.44: name='Chassis';col='06 Chassis and closure';mat='Inner'
 if d.x>.4 and c.y<-.45:name='Bumper | Front'
 elif d.x>.4 and c.y>.43:name='Bumper | Rear'
 elif abs(c.x)>.215 and -.19<c.y<-.15:
  name='Mirror | '+side;par=door_parents[(side,'Front')]
 elif c.y<-.46:
  name='Grille' if abs(c.x)<.11 else 'Lamp | '+side+' front marker';mat='Inner' if abs(c.x)<.11 else 'Light'
 elif c.z>.44 and abs(c.x)>.17:name='Glass | '+side+' alpine';mat='Glass';col='03 Glazing';par=roofmount
 elif abs(c.x)>.20 and -.205<c.y<.18 and .15<c.z<.31:
  row='Front' if c.y<.007 else 'Rear';name='Door hardware | '+side+' '+row;par=door_parents[(side,row)]
 elif c.y>.425:
  if abs(c.x)>.155:name='Lamp | '+side+' rear marker';mat='Light'
  else:name='Rear door hardware';par=rearhinge
 elif -.22<c.y<-.12 and c.z>.30:name='Wiper and cowl fitting'
 elif abs(c.x)>.19 and c.z>.31:
  # Flat ghost-seat fragments in the original opaque windows are not real seats.
  manifest['replaced_source_islands'].append(rec['id']);continue
 else:name='Body fitting'
 thickness=.003 if rec['boundary_edges'] else 0
 ob=mesh_obj(name+' | '+str(rec['id']).zfill(3),record_polys(rec),col,mat,thickness,par)
 ob['source_island']=rec['id']
def lathe(name,profile,centre,axis,col,mat,parent,segments=48):
 c=Vector(centre);polys=[];rings=[]
 for axial,r in profile:
  ring=[]
  for i in range(segments):
   t=i*math.tau/segments
   p=c+(Vector((axial,r*math.cos(t),r*math.sin(t))) if axis=='X' else Vector((r*math.cos(t),axial,r*math.sin(t))))
   ring.append(p)
  rings.append(ring)
 for j in range(len(rings)):
  nxt=(j+1)%len(rings)
  for i in range(segments):polys.append([rings[j][i],rings[j][(i+1)%segments],rings[nxt][(i+1)%segments],rings[nxt][i]])
 return mesh_obj(name,polys,col,mat,0,parent)
wheel_info=[]
for rec in wheel_records:
 a,b,c,d=bbox(rec);spare=c.y>.44;axis='Y' if spare else 'X';r=d.z/2;width=d.y if spare else d.x
 corner='Spare' if spare else ('L' if c.x>0 else 'R')+('F' if c.y<0 else 'R')
 par=empty('Wheel pivot | '+corner,c)
 if spare:parent_keep(par,rearhinge)
 sign=1 if spare or c.x>0 else -1
 inner=r*.59;w=width/2
 profile=[(-w*.85,inner),(-w,inner*1.14),(-w,r*.86),(-w*.68,r*.985),(w*.68,r*.985),(w,r*.86),(w,inner*1.14),(w*.85,inner)]
 tyre=lathe('Rebuilt tyre | '+corner,profile,c,axis,'04 Wheels','Rubber',par)
 rimprofile=[(-w*.88,inner*.94),(-w*.88,inner*1.03),(w*.87,inner*1.03),(w*.87,inner*.94)]
 lathe('Rebuilt rim barrel | '+corner,rimprofile,c,axis,'04 Wheels','Metal',par)
 # Closed steel wheel dish, with modest mechanical geometry instead of texture.
 dish=[(w*.73*sign,.003),(w*.73*sign,inner*.45),(w*.58*sign,inner*.72),(w*.84*sign,inner*.94),(w*.65*sign,inner*.94),(w*.4*sign,inner*.72),(w*.55*sign,.003)]
 lathe('Rebuilt wheel dish | '+corner,dish,c,axis,'04 Wheels','Metal',par)
 lathe('Rebuilt hub | '+corner,[(w*.55*sign,.003),(w*.98*sign,.003),(w*.98*sign,inner*.24),(w*.55*sign,inner*.24)],c,axis,'04 Wheels','Inner',par,24)
 for k in range(5):
  t=k*math.tau/5;off=Vector((0,inner*.36*math.cos(t),inner*.36*math.sin(t))) if axis=='X' else Vector((inner*.36*math.cos(t),0,inner*.36*math.sin(t)))
  lathe('Rebuilt lug | '+corner+' '+str(k),[(w*.71*sign,.0001),(w*.87*sign,.0001),(w*.87*sign,.003),(w*.71*sign,.003)],c+off,axis,'04 Wheels','Light',par,6)
 wheel_info.append({'corner':corner,'centre_m':list(c*SCALE),'radius_m':r*SCALE,'width_m':width*SCALE})
manifest['wheels']=wheel_info
# Continuous inner floor above the retained underside: does not stretch through wheel tubs.
floor_outline=[(-.208,-.196),(.208,-.196),(.208,.169),(.151,.20),(.151,.352),(.208,.383),(.208,.426),(-.208,.426),(-.208,.383),(-.151,.352),(-.151,.20),(-.208,.169)]
floor=mesh_obj('Cabin | Continuous floor pan',[[Vector((x,y,.153)) for x,y in floor_outline]],'06 Chassis and closure','Inner',.025)
for p in floor.data.polygons:p.use_smooth=False
for side,sign in [('L',1),('R',-1)]:
 # Wheelhouse inner walls keep the tyre volumes outside the empty cabin.
 polys=[]
 for j in range(16):
  t0=j*math.pi/16;t1=(j+1)*math.pi/16
  p0=Vector((sign*.158,.265+.105*math.cos(t0),.10+.105*math.sin(t0)))
  p1=Vector((sign*.158,.265+.105*math.cos(t1),.10+.105*math.sin(t1)))
  polys.append([p0,p1,p1+Vector((sign*.060,0,0)),p0+Vector((sign*.060,0,0))])
 polys.append([Vector((sign*.158,.265+.105*math.cos(j*math.pi/16),.10+.105*math.sin(j*math.pi/16))) for j in range(17)])
 mesh_obj('Cabin | '+side+' rear wheel tub',polys,'06 Chassis and closure','Inner',.008)
# Retain an exact hidden original at the same uniform scale for future comparison.
for rec in DATA:
 ob=mesh_obj('SOURCE | '+str(rec['id']),record_polys(rec),'99 Original reference','Body')
 ob.hide_render=True;ob.hide_set(True);owned.remove(ob)
cols['99 Original reference'].hide_render=True;cols['99 Original reference'].hide_viewport=True
manifest['parts']=[p for p in manifest['parts'] if not p['name'].startswith('SOURCE')]
for o in controls.values():
 if o!=vehicle and o.parent is None:parent_keep(o,vehicle)
# Explicit neutral inspection controls; opening is a pose aid, not certified vehicle rigging.
for key,o in controls.items():
 if key.startswith('Hinge'):o['purpose']='Panel pivot; use local rotation. Clearance review required before gameplay animation.'
sc.render.engine='CYCLES';sc.cycles.samples=32
sc.render.resolution_x=1300;sc.render.resolution_y=950;sc.render.resolution_percentage=100
sc.world=bpy.data.worlds.new('Review World');sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs[0].default_value=(.23,.23,.23,1);sc.world.node_tree.nodes['Background'].inputs[1].default_value=.65
for name,pos,power,size in [('Key',(5,-6,8),1800,6),('Fill',(-5,-1,6),1300,5),('Rim',(0,6,7),1700,5)]:
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);cols['90 Studio'].objects.link(o);o.location=pos;o.rotation_euler=(Vector((0,0,1))-o.location).to_track_quat('-Z','Y').to_euler()
cd=bpy.data.cameras.new('Review');cam=bpy.data.objects.new('Review',cd);cols['90 Studio'].objects.link(cam);sc.camera=cam;cd.type='ORTHO'
def render(name,pos,scale=6.7,target=(0,0,1.1)):
 if os.environ.get('DEFENDER_FAST'):return
 cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cd.ortho_scale=scale;sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
render('quarter',(7,-9,4.7))
render('side',(9,0,1.15),6.4)
render('front',(0,-9,1.15),4.2)
render('rear',(0,9,1.15),4.2)
render('underside',(6,-7,-5),6.8)
render('top',(0,0,9),6.4)
# Exploded inspection makes actual component separation visible.
saved={o:o.location.copy() for o in controls.values()}
for (side,row),p in door_parents.items():p.location.x+=(1 if side=='L' else -1)*1.15
hoodhinge.location.z+=1.1;rearhinge.location.y+=1.3
roofmount.location.z+=1.25
for name,p in controls.items():
 if name.startswith('Wheel pivot') and 'Spare' not in name:p.location.x+=(1 if 'L' in name else -1)*.65
render('exploded',(8,-10,7),9)
for o,loc in saved.items():o.location=loc
dg=bpy.context.evaluated_depsgraph_get();triangles=0;bad=[]
for o in owned:
 ev=o.evaluated_get(dg);me=ev.to_mesh();triangles+=sum(len(p.vertices)-2 for p in me.polygons)
 if any(not math.isfinite(x) for v in me.vertices for x in v.co):bad.append(o.name)
 ev.to_mesh_clear()
assert not bad,bad
manifest['checks'].update({'finite_geometry':True,'mesh_objects':len(owned),'evaluated_triangles':triangles,'source_hash_unchanged':hashlib.sha256(Path(manifest['source']).read_bytes()).hexdigest()==manifest['source_sha256'],'opening_panels':6,'road_wheels':4,'spare_wheels':1})
manifest['limitations']=['Neutral materials only; no UV/texture work as requested.','Empty enclosed cabin; Tripo did not contain a usable interior.','Source shape retained, including its stylized proportions and some soft reconstructed details.','Panel pivots supplied; no tested animated rig, suspension, collision or Unreal import in this geometry stage.']
for o in bpy.context.selected_objects:o.select_set(False)
for o in owned:o.select_set(True)
for o in controls.values():o.select_set(True)
bpy.context.view_layer.objects.active=body
bpy.ops.export_scene.gltf(filepath=str(OUT/'Defender_Separated.glb'),export_format='GLB',use_selection=True,export_apply=True,export_animations=False,export_extras=True)
cam.location=(7,-9,4.7);cam.rotation_euler=(Vector((0,0,1.1))-cam.location).to_track_quat('-Z','Y').to_euler();cd.ortho_scale=6.7
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':area.spaces.active.region_3d.view_distance=7;area.spaces.active.region_3d.view_location=(0,0,1.1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Defender_Separated.blend'))
(OUT/'geometry-report.json').write_text(json.dumps(manifest,indent=2))
print('DEFENDER_GEOMETRY_COMPLETE',manifest['checks'])
