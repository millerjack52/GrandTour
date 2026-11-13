"""Reopen the cockpit, retain exterior checks, then test seating and enclosure."""
from pathlib import Path
import sys,json,hashlib
out=Path(sys.argv[sys.argv.index('--')+1])
# Run the established exterior contracts on this saved file, not on its source.
s=Path('C:/GrandTour/Art/VehicleTools/verify_pathfinder_bonnet_wheels.py').read_text().replace('Pathfinder_Bonnet_Wheels.blend','Pathfinder_Cockpit.blend')
exec(compile(s,'<retained exterior checks>','exec'))
cockpit=json.loads((out/'cockpit-manifest.json').read_text());fail=[]
for name,wanted in cockpit['protected_hashes'].items():
 ob=bpy.data.objects.get(name)
 if not ob:fail.append(name);continue
 h=hashlib.sha256()
 for v in ob.data.vertices:h.update(str(tuple(v.co)).encode())
 for f in ob.data.polygons:h.update(str(tuple(f.vertices)).encode())
 h.update(str(tuple(tuple(r) for r in ob.matrix_world)).encode())
 if h.hexdigest()!=wanted:fail.append(name)
source_same=hashlib.sha256(Path(cockpit['source']).read_bytes()).hexdigest()==cockpit['source_sha256']
obs=[o for o in bpy.context.scene.objects if o.type=='MESH' and any(x in o.name for x in ['continuous tub','wheelhouse wall','shared body skin','continuous cabin frame','recessed glass','Windscreen | glass','Rear screen | glass','Roof | shallow'])]
trees={o.name:bvh(o) for o in obs};seats=list(bpy.data.collections['16 | Pathfinder mounted seats'].objects);collisions=[];keepouts=[]
for ob in seats:
 if ob.type!='MESH':continue
 t=bvh(ob);vs,_=geom(ob)
 for name,tree in trees.items():
  if t.overlap(tree):collisions.append([ob.name,name])
 # Containment test supplements surface overlap: rear tyre housing occupies
 # x beyond +/- .594 inside its longitudinal arch below its upper profile.
 for v in vs:
  pts=S['arches_uv']['Rear']
  if pts[0][0]<=U(v.y)<=pts[-1][0] and .431<v.z<Z(interp(U(v.y),pts)) and abs(v.x)>.594:
   keepouts.append(ob.name);break
coverage=0;missing=[]
for seat in cockpit['seat_specs']:
 xa,xb,ya,yb=seat['footprint']
 for i in range(17):
  for j in range(21):
   xx=xa+(xb-xa)*i/16;yy=ya+(yb-ya)*j/20;coverage+=1
   if pan.ray_cast(Vector((xx,yy,.20)),Vector((0,0,1)),.25)[0] is None:missing.append([seat['name'],xx,yy])
foot_gaps=[];detached=[]
rails=[(o,bvh(o)) for o in seats if '| rail' in o.name and o.type=='MESH']
for name in cockpit['mount_feet']:
 ob=bpy.data.objects[name];vs,_=geom(ob);x=sum(v.x for v in vs)/len(vs);y=sum(v.y for v in vs)/len(vs);bottom=min(v.z for v in vs)
 hit=pan.ray_cast(Vector((x,y,.6)),Vector((0,0,-1)),.3)[0];distance=abs(bottom-hit.z) if hit is not None else 99;foot_gaps.append(distance)
 if not any(bvh(ob).overlap(t) for _,t in rails):detached.append(name)
interior=[o for o in bpy.data.collections['15 | Pathfinder fitted cockpit'].objects if o.type=='MESH'];intrusions=[]
for ob in interior:
 t=bvh(ob)
 for name,tree in trees.items():
  if t.overlap(tree):intrusions.append([ob.name,name])
roofrail=[o for o in bpy.context.scene.objects if o.name.startswith('Roof rail')]
clamps=[o for o in bpy.data.collections['18 | Pathfinder remaining fittings'].objects if 'clamp' in o.name];unseated=[]
for ob in clamps:
 if not any(bvh(ob).overlap(bvh(rail)) for rail in roofrail):unseated.append(ob.name)
detached_belts=[]
for side,label in [(-1,'Right'),(1,'Left')]:
 belt=bpy.data.objects.get('Belt | flat webbing '+str(side))
 if not belt:continue
 upper=bpy.data.objects['Belt | upper anchor '+str(side)];lower=bpy.data.objects['Belt | lower anchor '+str(side)];pillar=bpy.data.objects[label+' | continuous cabin frame']
 for a,b in [(belt,upper),(belt,lower),(upper,pillar)]:
  if not bvh(a).overlap(bvh(b)):detached_belts.append([a.name,b.name])
result={'source_unchanged':source_same,'protected_raw_mesh_count':len(cockpit['protected_hashes']),'protected_raw_mesh_mismatches':fail,'seat_exterior_intersections':collisions,'seat_wheelhouse_containment':keepouts,'seat_floor_projection':{'rays':coverage,'missing':len(missing),'examples':missing[:5]},'floor_mount_max_gap_m':max(foot_gaps),'detached_seat_feet':detached,'dashboard_exterior_intersections':intrusions,'unseated_roof_clamps':unseated,'retained_exterior_checks_passed':report['passed'],'limits':['Static assembly only; no seated-human ergonomics validation','No steering/suspension/door motion or export certification']}
result['detached_belt_mounts']=detached_belts
result['passed']=report['passed'] and source_same and not fail and not collisions and not keepouts and not missing and max(foot_gaps)<.001 and not detached and not intrusions and not unseated and not detached_belts
(out/'cockpit-assembly-checks.json').write_text(json.dumps(result,indent=2));print('COCKPIT CHECKS '+json.dumps(result,indent=2));assert result['passed']
