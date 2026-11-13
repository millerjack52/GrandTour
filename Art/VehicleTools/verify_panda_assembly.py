"""Scoped saved-assembly and actual GLB checks; not a game-readiness certificate."""
import bpy,bmesh,json,math,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
OUT=Path(sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'C:/GrandTour/Art/Export/VehicleTools/panda-assembly-v02');S=3.6
spec=json.loads((OUT/'vehicle-spec.json').read_text())
def get_bvh(obs):
 vv=[];ff=[]
 for o in obs:
  start=len(vv);vv.extend(o.matrix_world@v.co for v in o.data.vertices);ff.extend(tuple(start+i for i in p.vertices) for p in o.data.polygons)
 return BVHTree.FromPolygons(vv,ff) if ff else None
def lerp(t,ps):
 if t<=ps[0][0]:return ps[0][1]
 for (a,b),(c,d) in zip(ps,ps[1:]):
  if t<=c:return b+(d-b)*(t-a)/(c-a)
 return ps[-1][1]
def checks():
 obs=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.name.startswith('SOURCE')]
 stats={'objects':len(obs),'triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in obs),'bad_meshes':[],'no_uv':[],'bounds':[]}
 for o in obs:
  bm=bmesh.new();bm.from_mesh(o.data)
  issues={'zero_area':sum(f.calc_area()<1e-12 for f in bm.faces),'wire_edges':sum(e.is_wire for e in bm.edges),'overconnected':sum(len(e.link_faces)>2 for e in bm.edges),'boundary_edges':sum(e.is_boundary for e in bm.edges)}
  if any(issues[k] for k in ['zero_area','wire_edges','overconnected']):stats['bad_meshes'].append({'name':o.name,**issues})
  if not o.data.uv_layers:stats['no_uv'].append(o.name)
  bm.free()
 pts=[o.matrix_world@v.co for o in obs for v in o.data.vertices]
 stats['bounds']=[[min(p[i] for p in pts) for i in range(3)],[max(p[i] for p in pts) for i in range(3)]]
 shell=[o for o in obs if o.get('component_group','') in ['Body','Doors','Bonnet','Tailgate','Glazing','Underbody'] or any(w in o.name for w in ['skin','wing','quarter','floor','wheelhouse','backing','surround','glass','gasket','Roof cap','Scuttle','pressing'])]
 tree=get_bvh(shell);misses=[];count=0
 def ray(label,pos,d,length):
  nonlocal count
  count+=1;hit=tree.ray_cast(Vector(pos)*S,Vector(d).normalized(),length*S)
  if hit[0] is None:misses.append({'label':label,'pos':list(pos),'dir':list(d)})
 # Multiple positions across both long door reveals, oblique as well as normal rays.
 for sign in [-1,1]:
  for i in range(55):
   z=.14+i*(.308/54)
   leading=lerp(z,[(.135,-.184),(.322,-.184),(.455,-.041)])
   for seam in [leading,.13]:
    lower=max([.135]+[lerp(seam,ar) for ar in spec['arches'].values() if ar[0][0]<=seam<=ar[-1][0]])
    if z<lower+.001:continue
    for offset in [-.001,0,.001]:
     for oblique in [-.3,0,.3]:
      target=Vector((sign*lerp(z,spec['width_profile']),seam+offset,z));direction=Vector((-sign,oblique,0)).normalized();ray('door reveal',target-direction*.07,direction,.15)
  for ar in spec['arches'].values():
   for (ya,za),(yb,zb) in zip(ar,ar[1:]):
    for i in range(1,8):
     t=i/8;y=ya+(yb-ya)*t;z=za+(zb-za)*t
     if z>.151:ray('wheelhouse backing',(sign*.30,y,z-.008),(-sign,0,0),.20)
  for j in range(24):
   z=.327+j*.116/23;edge=lerp(z,spec['width_profile']);gate=lerp(z,[(.322,.1818),(.455,.179)]);y=lerp(z,spec['tail_profile'])
   for f in [.25,.5,.75]:ray('rear upper corner',(sign*(gate+(edge-gate)*f),y+.03,z),(0,-1,0),.055)
 # Floor coverage including wings out to the sill; wheel openings are deliberate exclusions.
 for iy in range(70):
  y=-.418+iy*.879/69;inarch=any(ar[0][0]<y<ar[-1][0] for ar in spec['arches'].values());width=.138 if inarch else .208
  for ix in range(25):ray('floor',(-width+ix*width*2/24,y,.015),(0,0,1),.145)
 from collections import Counter
 stats['coverage']={'samples':count,'misses':len(misses),'by_label':dict(Counter(m['label'] for m in misses)),'examples':misses[:60]}
 # Coverage alone can accept a door jamb across an arch: probe forbidden outer space separately.
 jambtree=get_bvh([o for o in obs if 'door reveal backing' in o.name or o.name.endswith(' sill')]);intrusions=[];arch_samples=0
 for sign in [-1,1]:
  for ar in spec['arches'].values():
   for j in range(55):
    y=ar[0][0]+(ar[-1][0]-ar[0][0])*(j+.5)/55;top=lerp(y,ar)
    for k in range(12):
     z=.139+(top-.149)*(k+.5)/12
     if z>=top-.008:continue
     arch_samples+=1
     if jambtree.ray_cast(Vector((sign*.265,y,z))*S,Vector((-sign,0,0)),.075*S)[0] is not None:intrusions.append((sign,y,z))
 stats['arch_forbidden_space']={'samples':arch_samples,'unwanted_hits':len(intrusions),'examples':intrusions[:10]}
 # Wheel components must fit within rubber axially, with positive body clearance at rest.
 bodytree=get_bvh([o for o in shell if 'shock' not in o.name and 'axle' not in o.name.lower()]);wheel_checks=[]
 for w in spec['wheels']:
  tyre=next(o for o in obs if o.name==w['name']+' tyre');tiretree=get_bvh([tyre]);hardware=[o for o in obs if o.name.startswith(w['name']+' ') and any(k in o.name for k in ['rim barrel','steel wheel web','hub','lug'])]
  tv=[(tyre.matrix_world@v.co).x for v in tyre.data.vertices];hv=[(o.matrix_world@v.co).x for o in hardware for v in o.data.vertices]
  intersections=bodytree.overlap(tiretree);margins=[min(hv)-min(tv),max(tv)-max(hv)]
  wheel_checks.append({'wheel':w['name'],'hardware_axial_margins_m':margins,'static_shell_intersections':len(intersections)})
 stats['wheel_fit']=wheel_checks
 # Seat bases wholly within cabin and outside the wheelhouse forbidden volumes.
 badseat=[]
 for o in obs:
  if not any(t in o.name for t in ['seat cushion','seat back','bench cushion','bench back']):continue
  for v in o.data.vertices:
   p=(o.matrix_world@v.co)/S
   for ar in spec['arches'].values():
    if abs(p.x)>.139 and ar[0][0]<p.y<ar[-1][0] and .13<p.z<lerp(p.y,ar):badseat.append(o.name);break
 stats['seat_wheelhouse_intrusions']=sorted(set(badseat))
 stats['pass']=not(stats['bad_meshes'] or stats['no_uv'] or misses or badseat or intrusions or any(min(w['hardware_axial_margins_m'])<0 or w['static_shell_intersections'] for w in wheel_checks))
 return stats
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Panda_Assembly.blend'));saved=checks()
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(OUT/'Panda_Assembly.glb'));exported=checks()
source_exported=[o.name for o in bpy.context.scene.objects if o.name.startswith('SOURCE')]
report={'saved_blend':saved,'glb_roundtrip':exported,'unwanted_source_in_export':source_exported,'limits':'Static fit and sampled coverage. No moving suspension/steering, rig, LOD, collision or Unreal validation.','pass':saved['pass'] and exported['pass'] and not source_exported}
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
