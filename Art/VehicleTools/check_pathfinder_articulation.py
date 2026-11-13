import bpy,sys,json,math,hashlib
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
out=Path(sys.argv[sys.argv.index('--')+1]);bpy.ops.wm.open_mainfile(filepath=str(out/'Pathfinder_Articulation.blend'));sc=bpy.context.scene;r=bpy.data.objects['GT | Pathfinder controls'];manifest=json.loads((out/'articulation-manifest.json').read_text());groups=manifest['groups'];props=['left_front_door','right_front_door','left_rear_door','right_rear_door','steer','roll']
def pose(**values):
 for k in props:r[k]=float(values.get(k,0))
 r.update_tag();sc.frame_set(sc.frame_current);bpy.context.view_layer.update()
def mat(n):return bpy.data.objects[n].matrix_world.copy()
pose();cache={};dg=bpy.context.evaluated_depsgraph_get()
for o in sc.objects:
 if o.type not in ['MESH','CURVE'] or (o.hide_render and not o.get('inspection_fixture')) or any('Studio' in c.name for c in o.users_collection):continue
 eo=o.evaluated_get(dg);me=eo.to_mesh();me.calc_loop_triangles()
 if len(me.vertices) and len(me.loop_triangles):cache[o.name]=([v.co.copy() for v in me.vertices],[tuple(t.vertices) for t in me.loop_triangles])
 else:print('EMPTY_GEOMETRY '+o.name)
 eo.to_mesh_clear()
def shape(n):
 v,f=cache[n];m=mat(n);pts=[m@q for q in v];return ([min(v[i] for v in pts) for i in range(3)],[max(v[i] for v in pts) for i in range(3)],pts,f)
def tree(s):return BVHTree.FromPolygons(s[2],s[3],all_triangles=True)
def overlap(a,b):return all(a[0][i]<=b[1][i] and b[0][i]<=a[1][i] for i in range(3))
def contacts(members,fixed,trees):
 hits=[]
 for n in members:
  if n not in cache:continue
  s=shape(n);t=None
  for name,other in fixed.items():
   if not overlap(s,other):continue
   if t is None:t=tree(s)
   if name not in trees:trees[name]=tree(other)
   if t.overlap(trees[name]):hits.append([n,name])
 return hits
checks={};pose();rest=manifest['rest_matrices']
checks['neutral_world_transforms']=max(abs(mat(n)[i][j]-v[i][j]) for n,v in rest.items() for i in range(4) for j in range(4))<1e-6
checks['source_unchanged']=hashlib.sha256(Path(manifest['source']).read_bytes()).hexdigest()==manifest['source_sha256']
fail=[]
for n,wanted in manifest['unchanged_raw_meshes'].items():
 o=bpy.data.objects[n];h=hashlib.sha256()
 for v in o.data.vertices:h.update(str(tuple(v.co)).encode())
 for p in o.data.polygons:h.update(str(tuple(p.vertices)).encode())
 if h.hexdigest()!=wanted:fail.append(n)
checks['unmodified_component_geometry']=not fail
pose(steer=25,roll=90)
checks['ackermann_inner_wheel']=bpy.data.objects['Steer | front_1_wheel'].rotation_euler.z>bpy.data.objects['Steer | front_-1_wheel'].rotation_euler.z>0
checks['both_sides_same_roll']=all(abs(bpy.data.objects['Roll | '+k].rotation_euler.x-math.pi/2)<1e-6 for k in groups if k.endswith('_wheel'))
checks['calipers_do_not_roll']=all(bpy.data.objects[n].parent.name.startswith('Steer |') for k in groups if k.endswith('_wheel') for n in groups[k] if 'caliper' in n)
checks['cabin_wheel_link']=abs(bpy.data.objects['Cabin steering spin'].rotation_euler.z-math.radians(375))<1e-6
checks['wheel_centres_fixed']=all((mat('Roll | '+k).translation-Vector((side*track/2,y,.369))).length<1e-6 for axle,y,track in [('front',-1.35,1.54),('rear',1.35,1.545)] for side in [-1,1] for k in [axle+'_'+str(side)+'_wheel'])
for key in props[:4]:
 pose(**{key:45});names=groups[key];base=Matrix(rest[names[0]]);d=mat(names[0])@base.inverted();checks[key+'_moves_as_group']=all(max(abs((mat(n)@Matrix(rest[n]).inverted())[i][j]-d[i][j]) for i in range(4) for j in range(4))<2e-6 for n in names)
pose(steer=500,left_front_door=500);checks['clamps']=abs(bpy.data.objects['Hinge | left_front_door'].rotation_euler.z+math.radians(60))<1e-6 and abs(bpy.data.objects['Cabin steering spin'].rotation_euler.z-math.radians(450))<1e-6
pose();checks['neutral_restored']=max(abs(mat(n)[i][j]-v[i][j]) for n,v in rest.items() for i in range(4) for j in range(4))<1e-6
(out/'kinematic-checks.json').write_text(json.dumps(checks,indent=2));print('KINEMATICS '+json.dumps(checks),flush=True)
results={};neutral={n:shape(n) for n in cache}
for key in props[:4]:
 members=groups[key];fixed={n:s for n,s in neutral.items() if n not in members};trees={};rows=[]
 for angle in [i*.25 for i in range(21)]+[10,20,30,40,50,60]:
  pose(**{key:angle});hits=contacts(members,fixed,trees)
  intended=[h for h in hits if h[0].startswith('Hinge leaf |') and h[1].startswith('Hinge backing |')]
  rows.append({'angle':angle,'contacts':[h for h in hits if h not in intended],'hinge_mount_contacts':intended})
 pose();results[key]=rows;print(key+' '+json.dumps([(x['angle'],len(x['contacts'])) for x in rows]),flush=True)
members=[n for k,g in groups.items() if k.endswith('_wheel') for n in g];fixed={n:s for n,s in neutral.items() if n not in members};trees={};rows=[]
for steer in range(-30,31,5):
 for roll in [0,1.875,3.75]:
  pose(steer=steer,roll=roll);rows.append({'steer':steer,'roll':roll,'contacts':contacts(members,fixed,trees)})
pose();results['road_wheels']=rows;print('WHEELS '+json.dumps([(x['steer'],len(x['contacts'])) for x in rows]),flush=True)
members=groups['cabin_steering'];fixed={n:s for n,s in neutral.items() if n not in members};trees={};rows=[]
for steer in range(-30,31,5):
 pose(steer=steer);hits=contacts(members,fixed,trees);intended=[h for h in hits if h[0]=='Steering | horn boss' and h[1] in ['Steering | column','Steering | shroud']];rows.append({'steer':steer,'contacts':[h for h in hits if h not in intended],'shaft_contacts':intended})
pose();results['cabin_steering']=rows
rows=[]
for side in ['left','right']:
 for front in [0,20,40,60]:
  for rear in [0,20,40,60]:
   pose(**{side+'_front_door':front,side+'_rear_door':rear});fixed={n:shape(n) for n in groups[side+'_rear_door'] if n in cache};rows.append({'side':side,'front':front,'rear':rear,'contacts':contacts(groups[side+'_front_door'],fixed,{})})
pose();results['adjacent_doors']=rows
allrows=[p for rows in results.values() for p in rows];results['summary']={'sampled_poses':len(allrows),'unexpected_contact_pairs':sum(len(p['contacts']) for p in allrows),'kinematic_pass':all(checks.values())};results['scope']='Evaluated triangle contacts at listed samples, not continuous collision, containment or suspension travel. Intentional hinge and steering shaft contacts reported separately.'
results['passed']=all(checks.values()) and results['summary']['unexpected_contact_pairs']==0
(out/'sweep-report.json').write_text(json.dumps(results,indent=2));print('SWEEP '+json.dumps(results['summary']),flush=True)
assert results['passed'],'Motion contacts remain; inspect the saved report.'
