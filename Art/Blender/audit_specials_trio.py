"""Visible intersection checks in the source plus source articulation evidence.
Checks explicit risky pairs, not a claim that every intentional assembly contact is absent.
"""
import bpy,json,sys,argparse,math
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser();ap.add_argument('--car',required=True);ap.add_argument('--source',default='R6');args=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
OUT=ROOT/'Art/Export/SpecialsTrio'/args.car/args.source
bpy.ops.wm.open_mainfile(filepath=str(OUT/(args.car+'.blend')));scene=bpy.context.scene
deps=bpy.context.evaluated_depsgraph_get();trees={};tris={}
for ob in scene.objects:
 if ob.type not in {'MESH','CURVE','FONT'} or any(c.name in {'Studio','Reference','Pivots'} for c in ob.users_collection):continue
 ev=ob.evaluated_get(deps);me=ev.to_mesh();me.calc_loop_triangles()
 vs=[ev.matrix_world@v.co for v in me.vertices];fs=[tuple(t.vertices) for t in me.loop_triangles]
 if fs:trees[ob.name]=BVHTree.FromPolygons(vs,fs,all_triangles=True);tris[ob.name]=len(fs)
 ev.to_mesh_clear()
checks=[]
def check(a,b):
 pairs=trees[a].overlap(trees[b]);checks.append({'a':a,'b':b,'triangle_intersections':len(pairs)})
skins=[n for n in trees if 'Skin_' in n]
for wheel in [n for n in trees if n.startswith(('Tyre_','Tread_'))]:
 for body in skins+['Bonnet']+[n for n in trees if n.startswith(('CabinFloor','WideFootwell','InnerSill','RaisedCargoFloor','EngineBayFloor','SeatBase','RearSeat'))]:check(wheel,body)
for seat in [n for n in trees if n.startswith(('SeatBase','SeatBack','RearSeat','Headrest'))]:
 for shell in [n for n in trees if n.endswith('_Glass') or n=='Roof']:check(seat,shell)
for i,a in enumerate(skins):
 for b in skins[i+1:]:check(a,b)
report={'scope':'Straight wheels versus outer body skins and bonnet; seats versus glass/roof; outer skin panels versus each other. Intentional fittings and joined edges not classified as defects. Articulation visual review separate.','triangles_total':sum(tris.values()),'checks':checks,'failures':[c for c in checks if c['triangle_intersections']],'status':'PASS' if not any(c['triangle_intersections'] for c in checks) else 'FAIL'}
(OUT/'intersection_report.json').write_text(json.dumps(report,indent=2))
print('TRIO_INTERSECTION '+json.dumps({k:v for k,v in report.items() if k!='checks'}),flush=True)
for group,axis,angle in [('Door_FL','Z',-48),('Door_FR','Z',48),('Door_RL','Z',-42),('Door_RR','Z',42),('Hood','X',-38),('Trunk','X',40)]:
 ob=bpy.data.objects.get(group+'_Pivot')
 if ob:ob.rotation_euler['XYZ'.index(axis)]=math.radians(angle)
bpy.context.view_layer.update();scene.cycles.device='CPU';scene.cycles.samples=24
scene.render.filepath=str(OUT/'articulation.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(args.car+'_ArticulationReview.blend')))
assert report['status']=='PASS','Intersection failures: inspect report and fix source before packaging'
