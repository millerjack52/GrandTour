import bpy,bmesh,json,sys,math,hashlib,ast
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools')
from graphic_adventure_coverage_v05 import inspect,tree,P,S,SPEC
P=Path('C:/GrandTour/Art/Export/VehicleTools/graphic-adventure-rounded-v01')
bpy.ops.wm.open_mainfile(filepath='C:/GrandTour/Art/Export/VehicleTools/graphic-adventure-interior-v01/GraphicAdventure_Interior.blend')
baseline_bad={}
for o in bpy.context.scene.objects:
 if o.type!='MESH' or not o.name.startswith('RET |'):continue
 bm=bmesh.new();bm.from_mesh(o.data)
 invalid={'degenerate':sum(f.calc_area()<1e-11 for f in bm.faces),'loose':sum(not v.link_faces for v in bm.verts),'overconnected':sum(len(e.link_faces)>2 for e in bm.edges)}
 bm.free()
 if any(invalid.values()):baseline_bad[o.name]=invalid
bpy.ops.wm.open_mainfile(filepath=str(P/'GraphicAdventure_Rounded.blend'))
ARCH=[(.155,.134),(.180,.200),(.199,.219),(.316,.219),(.346,.191),(.371,.136)]
from graphic_adventure_coverage_v05 import ip as interp
for node in ast.parse(Path(__file__).with_name('repair_graphic_adventure_v03.py').read_text()).body:
 if isinstance(node,ast.FunctionDef) and node.name in ['intrusion','rear_interface_report','rear_overlap']:
  exec(compile(ast.Module(body=[node],type_ignores=[]),'repair_regressions','exec'))
local_checks={'jamb_intrusion':intrusion(),'rear_corner_gaps':rear_interface_report(),'apron_overlap_height_m':rear_overlap()}
assert sum(v['intrusions'] for v in local_checks['jamb_intrusion'].values())==0
assert max(v['gap_m'] for rs in local_checks['rear_corner_gaps'].values() for v in rs)<.00001
assert max(local_checks['apron_overlap_height_m'].values())<.000001
objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith('RET |')]
def current():return [o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith('RET |')]
from graphic_adventure_coverage_v05 import sx
for node in ast.parse(Path(__file__).with_name('repair_graphic_adventure_v04.py').read_text()).body:
 if isinstance(node,ast.FunctionDef) and node.name=='seam_coverage':exec(compile(ast.Module(body=[node],type_ignores=[]),'door_seam_regression','exec'))
saved_seam=seam_coverage();assert saved_seam['uncovered']==0
for node in ast.parse(Path(__file__).with_name('repair_graphic_adventure_v05.py').read_text()).body:
 if isinstance(node,ast.FunctionDef) and node.name in ['nose','corner_coverage']:
  exec(compile(ast.Module(body=[node],type_ignores=[]),'front_corner_regression','exec'))
saved_corner=corner_coverage();assert saved_corner['uncovered']==0
dg=bpy.context.evaluated_depsgraph_get();bounds={};trees={};bad=[];triangles=0;stats={}
for o in objects:
 bm=bmesh.new();bm.from_mesh(o.data)
 invalid={'degenerate':sum(f.calc_area()<1e-11 for f in bm.faces),'loose':sum(not v.link_faces for v in bm.verts),'overconnected':sum(len(e.link_faces)>2 for e in bm.edges)}
 if any(invalid.values()):bad.append((o.name,invalid))
 bm.free();ev=o.evaluated_get(dg);me=ev.to_mesh();v=[o.matrix_world@p.co for p in me.vertices];f=[tuple(p.vertices) for p in me.polygons]
 assert all(math.isfinite(c) for p in v for c in p)
 trees[o.name]=tree([o]);bounds[o.name]=[[min(p[i] for p in v) for i in range(3)],[max(p[i] for p in v) for i in range(3)]]
 triangles+=sum(len(p)-2 for p in f);stats[o.name]={'base_faces':len(o.data.polygons),'evaluated_triangles':sum(len(p)-2 for p in f)};ev.to_mesh_clear()
collisions=[]
for corner,side,axle in [('LF','L','Front'),('RF','R','Front'),('LR','L','Rear'),('RR','R','Rear')]:
 for rubber in ['tyre','tread']:
  for n in ['RET | '+side+' '+axle+' enclosed wheelhouse','RET | '+side+' '+axle+' arch flare','RET | Fitted cabin floor','RET | '+side+' sill return','RET | '+side+' rocker','RET | '+side+' Rear door jamb']:
   overlap=trees['RET | '+corner+' '+rubber].overlap(trees[n])
   if overlap:collisions.append({'wheel':corner,'rubber':rubber,'part':n,'intersections':len(overlap)})
report={'coverage':inspect(objects),'mesh_errors':bad,'static_tyre_intersections':collisions,'meshes':len(objects),'evaluated_triangles':triangles,'part_statistics':stats}
report['local_repair_checks']=local_checks
report['saved_rear_door_seam']=saved_seam
report['saved_front_corner']=saved_corner
report['wheel_pivot_errors_m']={k:(bpy.data.objects['GA | Wheel '+k].matrix_world.translation-Vector(v)*S).length for k,v in SPEC['wheel_centres'].items()}
report['source_unchanged']=hashlib.sha256(Path(SPEC['source']).read_bytes()).hexdigest()==SPEC['source_sha256']
# Negative control removes real protective surfaces, demonstrating the probes detect missing coverage.
negative=[o for o in objects if not any(k in o.name for k in ['enclosed wheelhouse','Fitted cabin floor','Windscreen glass'])]
neg=inspect(negative);report['negative_control']={'removed':['wheelhouse shells','cabin floor','windscreen glass'],'uncovered':neg['uncovered'],'regions':neg['regions']}
(P/'verification.json').write_text(json.dumps(report,indent=2))
print('GEOMETRY',json.dumps({k:v for k,v in report.items() if k not in ['coverage','part_statistics','negative_control']}))
print('COVERAGE',report['coverage']['uncovered'],{k:v for k,v in report['coverage']['regions'].items() if v['uncovered']})
changed=set(json.loads((P/'repair-manifest.json').read_text())['changed'])
new_bad=[(n,issue) for n,issue in bad if n in changed or baseline_bad.get(n)!=issue]
report['inherited_unchanged_mesh_warnings']=bad
report['new_mesh_errors']=new_bad
assert not new_bad,new_bad
assert report['coverage']['uncovered']==0
assert not collisions,collisions
assert report['source_unchanged']
assert max(report['wheel_pivot_errors_m'].values())<.00001
assert neg['uncovered']>100
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(P/'GraphicAdventure_Rounded.glb'))
got=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert len(got)==len(objects)
maximum=0
for o in got:
 v=[o.matrix_world@p.co for p in o.data.vertices];bb=[[min(p[i] for p in v) for i in range(3)],[max(p[i] for p in v) for i in range(3)]]
 maximum=max(maximum,max(abs(bb[j][i]-bounds[o.name][j][i]) for j in range(2) for i in range(3)))
assert maximum<.0001,maximum
exported=inspect(got);assert exported['uncovered']==0
exported_corner=corner_coverage();assert exported_corner['uncovered']==0
report['exported_front_corner']=exported_corner
exported_seam=seam_coverage();assert exported_seam['uncovered']==0
report['exported_rear_door_seam']=exported_seam
exported_intrusion=intrusion();assert sum(v['intrusions'] for v in exported_intrusion.values())==0
report['exported_jamb_intrusion']=exported_intrusion
report.update(export_coverage=exported,export_bounds_max_error_m=maximum,status='PASS for scoped static mesh, coverage, tyre fit, pivots and GLB roundtrip checks',not_certified=['Steering/suspension and opening-panel travel','UVs, textures and livery','LOD, collision and Unreal integration'])
(P/'verification.json').write_text(json.dumps(report,indent=2));print('VERIFIED',len(got),triangles,maximum)

