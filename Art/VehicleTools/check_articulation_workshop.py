"""Saved-rig kinematics, content preservation and sampled surface sweep audit."""
import bpy,sys,json,argparse,math,shutil
from pathlib import Path
from types import SimpleNamespace
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent));import articulation_workshop as ar;import wheel_fender_workshop as wf
p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--quick',action='store_true');a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output)
bpy.ops.wm.open_mainfile(filepath=str(out/'RangeRover_Articulation_Workshop.blend'))
sc=bpy.context.scene;r=ar.root();groups=json.loads(r['groups']);checks={}
def check(n,v):checks[n]=bool(v);assert v,n
def point(n):o=bpy.data.objects[n];return o.matrix_world@o.data.vertices[0].co
def matrix(n):return bpy.data.objects[n].matrix_world.copy()
ar.neutral();world=json.loads(sc['articulation_rest_matrices']);source=json.loads(sc['articulation_source_hashes'])
check('post_fit_mesh_material_modifier_and_local_transform_content_preserved',all(wf.fingerprint(SimpleNamespace(objects=[o for o in bpy.data.collections[n].objects if not o.get('gt_rig_guard')]))==fp for n,fp in source.items()))
check('neutral_world_transforms_preserved',max(abs(matrix(n)[i][j]-m[i][j]) for n,m in world.items() for i in range(4) for j in range(4))<1e-6)
check('old_static_rebuilds_guarded',all(wf.fingerprint(bpy.data.collections[n])!=source[n] for n in json.loads(r['guarded_collections'])))
before={n:matrix(n) for n in world};ar.set_controls(left_front_door=45.)
skin=bpy.data.objects[groups['left_front_door'][0]];centroid=sum((v.co for v in skin.data.vertices),Vector())/len(skin.data.vertices)
check('front_door_opens_outward',(matrix(skin.name)@centroid).x>(before[skin.name]@centroid).x+.10)
changes=[matrix(n)@before[n].inverted() for n in groups['left_front_door']]
check('door_window_mirror_and_card_move_as_one',max(abs(m[i][j]-changes[0][i][j]) for m in changes for i in range(4) for j in range(4))<2e-6)
check('other_door_stays_fixed',all(max(abs(matrix(n)[i][j]-before[n][i][j]) for i in range(4) for j in range(4))<1e-6 for n in groups['right_front_door']+groups['left_rear_door']))
ar.neutral();ar.set_controls(steer=25.,roll=90.)
left=bpy.data.objects['Steer pivot | left_front_wheel'].evaluated_get(bpy.context.evaluated_depsgraph_get()).rotation_euler.z
right=bpy.data.objects['Steer pivot | right_front_wheel'].evaluated_get(bpy.context.evaluated_depsgraph_get()).rotation_euler.z
check('ackermann_inner_angle_larger',left>right>0)
check('wheel_centres_stay_fixed',all((matrix('Roll pivot | '+k).translation-Vector((.78 if k.startswith('left') else -.78,-1.36 if 'front' in k else 1.27,.38))).length<1e-6 for k in groups if k.endswith('_wheel') and k!='steering_wheel'))
check('same_world_roll_direction_both_sides',all(abs(bpy.data.objects['Roll pivot | '+k].evaluated_get(bpy.context.evaluated_depsgraph_get()).rotation_euler.x-math.pi/2)<1e-6 for k in groups if k.endswith('_wheel') and k!='steering_wheel'))
check('steering_wheel_ratio_linked',abs(bpy.data.objects['Steering wheel rotation'].evaluated_get(bpy.context.evaluated_depsgraph_get()).rotation_euler.z-math.radians(375))<1e-6)
fixed_controls=[o.name for o in bpy.data.collections['Cabin | steering and pedals'].objects if o.type=='MESH' and o.name not in groups['steering_wheel']]
check('stalks_shroud_pedals_stay_fixed',all(max(abs(matrix(n)[i][j]-before[n][i][j]) for i in range(4) for j in range(4))<1e-6 for n in fixed_controls))
ar.neutral();ar.set_controls(steer=-25.)
left=bpy.data.objects['Steer pivot | left_front_wheel'].evaluated_get(bpy.context.evaluated_depsgraph_get()).rotation_euler.z;right=bpy.data.objects['Steer pivot | right_front_wheel'].evaluated_get(bpy.context.evaluated_depsgraph_get()).rotation_euler.z
check('ackermann_reverses_inner_wheel',right<left<0)
ar.neutral();check('reset_restores_all_parts',max(abs(matrix(n)[i][j]-m[i][j]) for n,m in world.items() for i in range(4) for j in range(4))<1e-6)
wheel_keys=[k for k in groups if k.endswith('_wheel') and k!='steering_wheel'];samples={k:point(groups[k][0]) for k in wheel_keys};ar.set_controls(roll=90.)
check('rolling_moves_actual_geometry_correctly_on_both_sides',all((point(groups[k][0])-(matrix('Roll pivot | '+k).translation+Matrix.Rotation(math.pi/2,3,'X')@(samples[k]-matrix('Roll pivot | '+k).translation))).length<2e-6 for k in wheel_keys))
ar.neutral();ar.set_controls(left_front_door=500.,steer=500.)
check('door_driver_clamps_above_limit',abs(bpy.data.objects['Hinge | left_front_door'].rotation_euler.z+math.radians(70))<1e-6)
check('steering_driver_clamps_above_limit',abs(bpy.data.objects['Steering wheel rotation'].rotation_euler.z-math.radians(450))<1e-6)
ar.neutral();count=len(bpy.data.objects)
try:ar.build();blocked=False
except RuntimeError:blocked=True
check('duplicate_rig_build_refused_without_changes',blocked and len(bpy.data.objects)==count)
sys.path.insert(0,str(out/'GrandTour_Articulation_Addon.zip'));import grandtour_articulation as packaged
packaged.register();check('packaged_sidebar_registers',hasattr(bpy.types,'GTA_PT_panel'));packaged.unregister()
(out/'kinematic-tests.json').write_text(json.dumps(checks,indent=2));print('KINEMATIC_TESTS '+json.dumps(checks),flush=True)
if a.quick:sys.exit(0)
# Cache evaluated local meshes once. Current matrices are refreshed for each pose.
cache={};dg=bpy.context.evaluated_depsgraph_get()
for o in sc.objects:
    if o.type!='MESH' or o.hide_render or o.name=='Ground':continue
    eo=o.evaluated_get(dg);me=eo.to_mesh();me.calc_loop_triangles();cache[o.name]=([v.co.copy() for v in me.vertices],[tuple(t.vertices) for t in me.loop_triangles]);eo.to_mesh_clear()
def shape(n):
    verts,faces=cache[n];m=matrix(n);pts=[m@v for v in verts];lo=[min(v[i] for v in pts) for i in range(3)];hi=[max(v[i] for v in pts) for i in range(3)]
    return (lo,hi,pts,faces)
def overlaps(a,b):return all(a[0][i]<=b[1][i] and b[0][i]<=a[1][i] for i in range(3))
def contacts(members,others):
    moving={n:shape(n) for n in members if n in cache};hits=[];trees={}
    for n,s in moving.items():
        nt=None
        for name,other in others.items():
            if not overlaps(s,other):continue
            if nt is None:nt=BVHTree.FromPolygons(s[2],s[3],all_triangles=True)
            if name not in trees:trees[name]=BVHTree.FromPolygons(other[2],other[3],all_triangles=True)
            pairs=nt.overlap(trees[name])
            if pairs:hits.append([n,name,len(pairs)])
    return hits
results={};ar.neutral()
for key in ar.DOORS:
    members=set(groups[key]);others={n:shape(n) for n in cache if n not in members};poses=[]
    for angle in [i*.5 for i in range(11)]+list(range(10,(70 if 'front' in key else 65)+1,5)):
        ar.set_controls(**{key:float(angle)});hits=contacts(members,others);poses.append(dict(degrees=angle,contacts=hits))
    ar.neutral();results[key]=poses;print('DOOR_SWEEP '+key+' '+json.dumps([(p['degrees'],len(p['contacts'])) for p in poses]),flush=True)
wheel_names={n for k in groups if k.endswith('_wheel') and k!='steering_wheel' for n in groups[k]}
fixed={n:shape(n) for n in cache if n not in wheel_names};wheel_poses=[]
for steer in range(-30,31,5):
    for roll in [0,2.25,4.5,6.75]:
        ar.set_controls(steer=float(steer),roll=float(roll));hits=contacts(wheel_names,fixed);wheel_poses.append(dict(steer=steer,roll=roll,contacts=hits))
ar.neutral();results['wheels']=wheel_poses;print('WHEEL_SWEEP '+json.dumps([(p['steer'],p['roll'],len(p['contacts'])) for p in wheel_poses]),flush=True)
# Independent front/rear openings on each side: detect door-to-door contacts.
combined=[]
for side in ['left','right']:
    f=side+'_front_door';b=side+'_rear_door'
    for front in [0,15,30,45,60,70]:
        for rear in [0,15,30,45,60,65]:
            ar.set_controls(**{f:float(front),b:float(rear)});hits=contacts(groups[f],{n:shape(n) for n in groups[b] if n in cache});combined.append(dict(side=side,front=front,rear=rear,contacts=hits))
    ar.neutral()
results['adjacent_doors']=combined
ar.neutral();members=set(groups['steering_wheel']);others={n:shape(n) for n in cache if n not in members};column_poses=[]
for steer in range(-30,31,2):
    ar.set_controls(steer=float(steer));hits=contacts(members,others)
    mounts=[h for h in hits if h[0].startswith('Steering | hub') and h[1]=='Steering | column']
    column_poses.append(dict(steer=steer,intentional_shaft_hub_contacts=mounts,contacts=[h for h in hits if h not in mounts]))
ar.neutral();results['steering_wheel']=column_poses
results['scope']='Evaluated mesh triangle surface contacts. Doors sampled individually against all other visible vehicle meshes; adjacent doors additionally checked at 36 angle pairs per side including maximum opening. Wheels checked at 13 steering inputs and four tread phases per input against non-wheel meshes. Existing neutral contacts are retained, not silently waived. No continuous collision, suspension, human, load, minimum-gap or physics validation.'
results['steering_wheel_scope']='Cabin wheel sampled at 31 steering inputs over -450 to +450 degrees of wheel rotation; only the designed hub/column shaft connection is separated as intentional.'
poses=[p for k in ar.DOORS+['wheels','adjacent_doors','steering_wheel'] for p in results[k]]
results['summary']=dict(pose_checks=len(poses),unexpected_contact_pairs=sum(len(p['contacts']) for p in poses),intentional_shaft_hub_contacts=sum(len(p.get('intentional_shaft_hub_contacts',[])) for p in poses))
(out/'sweep-report.json').write_text(json.dumps(results,indent=2));shutil.copy2(__file__,out/Path(__file__).name);print('SWEEP_SAVED',flush=True)
assert not results['summary']['unexpected_contact_pairs'],results['summary']
