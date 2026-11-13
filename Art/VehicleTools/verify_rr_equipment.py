"""Saved geometry evidence for the fitted accessory set, including movement keep-outs."""
import bpy,bmesh,json,math,sys,hashlib
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
OUT=Path(sys.argv[sys.argv.index('--')+1]).resolve();ROOT=Path('C:/GrandTour');checks=[]
bpy.ops.wm.open_mainfile(filepath=str(OUT/'RangeRover_Equipment_Fit.blend'))
def check(name,ok,detail=None):checks.append(dict(name=name,passed=bool(ok),detail=detail))
def data(obs):
 v=[];f=[];dg=bpy.context.evaluated_depsgraph_get()
 for o in obs:
  e=o.evaluated_get(dg);me=e.to_mesh();n=len(v);v += [o.matrix_world@p.co for p in me.vertices];f += [tuple(n+i for i in p.vertices) for p in me.polygons];e.to_mesh_clear()
 return v,f
def tree(obs):return BVHTree.FromPolygons(*data(obs))
parts=[c for c in bpy.data.collections if c.get('kind')=='equipment'];obs=[o for c in parts for o in c.objects if o.type=='MESH'];et=tree(obs)
report=json.loads((OUT/'verification.json').read_text());check('Source car file preserved',hashlib.sha256((ROOT/'Art/rangerover.blend').read_bytes()).hexdigest()==report['source_sha256'])
check('Three independent assets',len(parts)==3)
for c in parts:
 for o in c.objects:
  if o.type!='MESH':continue
  bm=bmesh.new();bm.from_mesh(o.data);check(o.name+' saved closed topology',all(e.is_manifold for e in bm.edges) and all(f.calc_area()>1e-12 for f in bm.faces));bm.free()
for row in report['contacts']:
 p=Vector(row['point']);body=bpy.data.objects.get(row['surface']);nearest,normal,_,distance=et.find_nearest(p);signed=(p-nearest).dot(normal)
 # Mount surfaces may intentionally overlap their receiver; distinguish embedded points from air gaps.
 check(row['part']+' attachment at '+str(row['point']),signed<.003 and distance<.015 and tree([body]).find_nearest(p)[3]<.0001,dict(equipment_distance_m=distance,signed_gap_m=signed))
for i,c in enumerate(parts):
 for d in parts[i+1:]:check(c.name+' clears '+d.name,not tree(list(c.objects)).overlap(tree(list(d.objects))))
head=tree([o for o in obs if o.name.startswith('Snorkel |')])
check('Intake aperture is open between louvres',head.ray_cast(Vector((.81,-.9,1.861)),Vector((0,1,0)),.23)[0] is None)
check('Intake aperture probe detects grille control',head.ray_cast(Vector((.81,-.9,1.872)),Vector((0,1,0)),.23)[0] is not None)
check('Intake has recessed backing',head.ray_cast(Vector((.81,-.9,1.861)),Vector((0,1,0)),.4)[0] is not None)
# Match runtime per-side door bounds: front edge in -Y, outer skin in +/-X, rotation about Z.
for name in ['frontDoors','passengerDoors']:
 o=bpy.data.objects.get(name);v,f=data([o])
 for side in [-1,1]:
  faces=[p for p in f if all(v[i].x*side>0 for i in p)];used=set(i for p in faces for i in p)
  hinge=Vector((max(v[i].x*side for i in used)*side,min(v[i].y for i in used),0))
  for angle in [0,15,30,45,60,75]:
   tr=Matrix.Translation(hinge)@Matrix.Rotation(math.radians(-side*angle),4,'Z')@Matrix.Translation(-hinge)
   hits=BVHTree.FromPolygons([tr@p for p in v],faces).overlap(et)
   check(name+' side '+str(side)+' angle '+str(angle)+' clears equipment',not hits,len(hits))
# Convex envelope of all three actual tread meshes, retaining only hull vertices for fast pose tests.
tyres=[c for c in bpy.data.collections if c.name.startswith('TYRE |')]
with bpy.data.libraries.load(str(ROOT/'Art/Export/VehicleTools/rr-wheels-tyres-v04/GT_RangeRover_Wheel_Components.blend')) as (src,dst):dst.collections=[n for n in src.collections if n.startswith('TYRE |')]
for c in dst.collections:sc=bpy.context.scene;sc.collection.children.link(c)
bpy.context.view_layer.update();v,f=data([o for c in dst.collections for o in c.objects if o.type=='MESH'])
bm=bmesh.new()
for p in v:bm.verts.new(p)
bmesh.ops.convex_hull(bm,input=list(bm.verts),use_existing_faces=False)
bmesh.ops.delete(bm,geom=[p for p in bm.verts if not p.link_faces],context='VERTS');bm.verts.ensure_lookup_table();bm.verts.index_update()
v=[p.co.copy() for p in bm.verts];f=[tuple(p.index for p in face.verts) for face in bm.faces];bm.free()
spec=json.loads((ROOT/'Art/Export/VehicleTools/rr-wheels-tyres-v04/spec.json').read_text());count=0;bad=[]
for centre in spec['measured_hub_centres_m']:
 for bump in [-.21,-.18,-.16,-.10,-.05,0]+([.025] if centre[1]>0 else []):
  for yaw in (range(-35,36,5) if centre[1]<0 else [0]):
   tr=Matrix.Translation(Vector(centre)+Vector((0,0,bump)))@Matrix.Rotation(math.radians(yaw),4,'Z');count+=1
   hits=BVHTree.FromPolygons([tr@p for p in v],f).overlap(et)
   if hits:bad.append(dict(centre=centre,bump=bump,steer=yaw,hits=len(hits)))
check('Tyre steering and travel clear equipment',not bad,dict(poses=count,collisions=bad))
result=dict(ok=all(c['passed'] for c in checks),checks=checks,scope='Saved topology, 11 recorded body attachments, accessory pair clearance, real intake openings, 24 door poses and sampled convex tyre sweep. No crash deformation or continuous clearance certification.')
(OUT/'saved-fit-check.json').write_text(json.dumps(result,indent=2));print('EQUIPMENT_FIT',result['ok'],len(checks),[c for c in checks if not c['passed']])
assert result['ok'],'See saved-fit-check.json'
