"""Reopen actual delivery; inspect full assembly rather than generator intentions."""
import bpy,sys,json,math,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
out=Path(sys.argv[sys.argv.index('--')+1]);bpy.ops.wm.open_mainfile(filepath=str(out/'Impreza_Gravel.blend'));sc=bpy.context.scene;r=bpy.data.objects['GT | Impreza controls'];M=json.loads((out/'build-manifest.json').read_text());groups=M['groups'];S=M['spec'];props=['L_front_door','R_front_door','L_rear_door','R_rear_door','steer','roll']
def pose(**values):
 for p in props:r[p]=float(values.get(p,0))
 r.update_tag();sc.frame_set(1);bpy.context.view_layer.update()
pose();dg=bpy.context.evaluated_depsgraph_get();cache={}
for o in sc.objects:
 if o.type not in ['MESH','CURVE'] or (o.hide_render and not o.get('inspection_fixture')) or any(c.name.startswith('90 |') for c in o.users_collection):continue
 eo=o.evaluated_get(dg);me=eo.to_mesh();me.calc_loop_triangles()
 if len(me.vertices) and len(me.loop_triangles):cache[o.name]=([v.co.copy() for v in me.vertices],[tuple(t.vertices) for t in me.loop_triangles])
 eo.to_mesh_clear()
def shape(n):
 v,f=cache[n];mat=bpy.data.objects[n].matrix_world;pts=[mat@p for p in v];return ([min(p[i] for p in pts) for i in range(3)],[max(p[i] for p in pts) for i in range(3)],pts,f)
def tree(s):return BVHTree.FromPolygons(s[2],s[3],all_triangles=True)
def contacts(moving,fixed,trees):
 hits=[]
 for n in moving:
  if n not in cache:continue
  s=shape(n);t=None
  for other,ss in fixed.items():
   if not all(s[0][i]<=ss[1][i] and ss[0][i]<=s[1][i] for i in range(3)):continue
   if t is None:t=tree(s)
   if other not in trees:trees[other]=tree(ss)
   if t.overlap(trees[other]):hits.append([n,other])
 return hits
neutral={n:shape(n) for n in cache};checks={};detail={}
checks['approved_reference_preserved']=hashlib.sha256(Path(M['approved_reference']).read_bytes()).hexdigest()==M['reference_sha256']
checks['four_wheels_with_correct_centres']=all((bpy.data.objects['Roll | '+sn+'_'+ax+'_wheel'].matrix_world.translation-Vector((s*.79,y,.362))).length<1e-6 for sn,s in [('L',1),('R',-1)] for ax,y in [('front',-1.25),('rear',1.27)])
detail['rim_axial_margins']={}
for sn,s in [('L',1),('R',-1)]:
 for ax in ['front','rear']:
  g=sn+'_'+ax+'_wheel';ty=neutral[g+' | tyre carcass'];ri=neutral[g+' | dished barrel'];detail['rim_axial_margins'][g]=[ri[0][0]-ty[0][0],ty[1][0]-ri[1][0]]
checks['rubber_wider_than_rim_both_sides']=all(min(v)>.009 for v in detail['rim_axial_margins'].values())
# Continuous floor coverage, including a deliberate narrowed-floor negative probe.
pan=neutral['Floor | complete shaped pan'];pt=tree(pan);miss=[];negative=0;count=0
for n in neutral:
 if not n.endswith(' | base') or 'seat' not in n:continue
 lo,hi=neutral[n][:2]
 for i in range(15):
  for j in range(15):
   x=lo[0]+(hi[0]-lo[0])*(i+.5)/15;y=lo[1]+(hi[1]-lo[1])*(j+.5)/15;count+=1
   if pt.ray_cast(Vector((x,y,.49)),Vector((0,0,-1)),.2)[0] is None:miss.append([n,x,y])
negative_tree=BVHTree.FromPolygons([Vector((v.x*.5,v.y,v.z)) for v in pan[2]],pan[3],all_triangles=True)
for x,y in [(.57,-.1),(-.57,-.1),(.44,.85),(-.44,.85)]:
 if negative_tree.ray_cast(Vector((x,y,.49)),Vector((0,0,-1)),.2)[0] is None:negative+=1
checks['floor_covers_all_seat_base_samples']=not miss;checks['floor_negative_probe_detected']=negative>0;detail['floor']={'samples':count,'misses':miss,'negative_probe_misses':negative}
seats=[n for n in cache if ' seat | ' in n and not ('belt buckle' in n or 'red release' in n)];body_names=[n for n in cache if any(c.name.startswith(('01 |','02 |','04 |')) for c in bpy.data.objects[n].users_collection) and not ('Floor | complete' in n or 'Hinge' in n)]
hits=contacts(seats,{n:neutral[n] for n in body_names},{});checks['seat_shell_and_wheelhouse_clearance']=not hits;detail['seat_contacts']=hits
# Forbidden wheelhouse occupied volumes also catch full containment missed by BVH.
contained=[]
for n in seats:
 for v in neutral[n][2]:
  for y in S['axles']:
   if abs(v.x)>.515 and (v.y-y)**2+(v.z-.362)**2<S['arch_radius']**2:contained.append(n);break
checks['seat_not_inside_wheelhouse_volume']=not contained;detail['seat_containment']=sorted(set(contained))
# Independently check physical flap -> clamp -> hanger -> body bracket contact.
attachment=[]
for sn in ['L','R']:
 for cy in S['axles']:
  for aa,bb in [('mudflap','mudflap clamp'),('mudflap clamp','mudflap hanger')]:
   n=sn+f' | {aa} {cy}';other=sn+f' | {bb} {cy}';attachment.append({'a':n,'b':other,'touches':bool(tree(neutral[n]).overlap(tree(neutral[other])))})
checks['mudflap_clamp_attachment']=all(x['touches'] for x in attachment);detail['attachments']=attachment
glass_mounts=[]
for sn in ['L','R']:
 for ax in ['front','rear']:
  pane=sn+' '+ax+' | window pane';channel=sn+' '+ax+' | closed top channel'
  glass_mounts.append({'pane':pane,'channel':channel,'seated':bool(tree(neutral[pane]).overlap(tree(neutral[channel])))})
checks['frameless_glass_seated_in_door_channels']=all(x['seated'] for x in glass_mounts);detail['glass_mounts']=glass_mounts
# No Boolean subtraction may accidentally introduce cutter extents in a fascia.
checks['front_fascia_stays_in_envelope']=neutral['Front | shaped bumper and fascia'][0][1]>-2.21 and neutral['Front | shaped bumper and fascia'][1][1]<-1.99
checks['rear_fascia_stays_in_envelope']=neutral['Rear | shaped bumper and fascia'][1][1]<2.20 and neutral['Rear | shaped bumper and fascia'][0][1]>1.97
rests={n:bpy.data.objects[n].matrix_world.copy() for n in cache}
pose(steer=20,roll=90)
checks['ackermann_inner_angle']=bpy.data.objects['Steer | L_front_wheel'].rotation_euler.z>bpy.data.objects['Steer | R_front_wheel'].rotation_euler.z>0
checks['consistent_wheel_roll']=all(abs(bpy.data.objects['Roll | '+sn+'_'+ax+'_wheel'].rotation_euler.x-math.pi/2)<1e-6 for sn in ['L','R'] for ax in ['front','rear'])
pose();checks['neutral_restores']=all(max(abs(bpy.data.objects[n].matrix_world[i][j]-m[i][j]) for i in range(4) for j in range(4))<1e-6 for n,m in rests.items())
(out/'assembly-checks.json').write_text(json.dumps({'checks':checks,'details':detail},indent=2));print('ASSEMBLY '+json.dumps(checks),flush=True)
results={}
for key in props[:4]:
 members=groups[key];fixed={n:v for n,v in neutral.items() if n not in members};trees={};rows=[]
 for angle in [i*.25 for i in range(21)]+[10,20,35,45,55]:
  pose(**{key:angle});hits=contacts(members,fixed,trees);intended=[h for h in hits if h[0].startswith('Hinge leaf |') and h[1].startswith('Hinge backing |')]
  rows.append({'angle':angle,'contacts':[h for h in hits if h not in intended],'mount_contacts':intended})
 pose();results[key]=rows;print(key+' '+json.dumps([(v['angle'],len(v['contacts'])) for v in rows]),flush=True)
members=[n for k,g in groups.items() if k.endswith('_wheel') or k.endswith('_wheel_caliper') for n in g];fixed={n:v for n,v in neutral.items() if n not in members};trees={};rows=[]
for steer in range(-25,26,5):
 for roll in [0,1.875,3.75]:
  pose(steer=steer,roll=roll);hits=contacts(members,fixed,trees);rows.append({'steer':steer,'roll':roll,'contacts':hits})
pose();results['wheels']=rows;print('WHEELS '+json.dumps([(v['steer'],len(v['contacts'])) for v in rows]),flush=True)
rows=[]
for sn in ['L','R']:
 for fa in [0,25,55]:
  for ra in [0,25,55]:
   pose(**{sn+'_front_door':fa,sn+'_rear_door':ra});hits=contacts(groups[sn+'_front_door'],{n:shape(n) for n in groups[sn+'_rear_door'] if n in cache},{});rows.append({'side':sn,'front':fa,'rear':ra,'contacts':hits})
pose();results['adjacent_doors']=rows
rows=[];fixed={n:v for n,v in neutral.items() if n not in groups['cabin_steer']};trees={}
for angle in range(-25,26,5):
 pose(steer=angle);hits=contacts(groups['cabin_steer'],fixed,trees);intended=[h for h in hits if h[1]=='Steering | fixed column'];rows.append({'steer':angle,'contacts':[h for h in hits if h not in intended],'shaft_contacts':intended})
pose();results['cabin_steering']=rows
rows=[x for rs in results.values() for x in rs];results['summary']={'sampled_poses':len(rows),'unexpected_contacts':sum(len(x['contacts']) for x in rows),'assembly_pass':all(checks.values())};results['passed']=all(checks.values()) and results['summary']['unexpected_contacts']==0;results['scope']='Evaluated surface intersections at listed samples, floor coverage rays, seat-volume containment and selected attachments. Not continuous collision, suspension or engine export.'
(out/'sweep-report.json').write_text(json.dumps(results,indent=2));print('RESULT '+json.dumps(results['summary']),flush=True)
