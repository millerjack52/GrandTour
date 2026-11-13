"""Cockpit geometry, adjustable interfaces and preservation probes."""
import bpy,sys,json,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent));import cockpit_workshop as ci
wf=ci.wf
p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);checks={}
def check(n,v):checks[n]=bool(v);assert v,n
def verts(c,token):return [tuple(v.co) for o in c.objects if o.type=='MESH' and token in o.name for v in o.data.vertices]
seat=ci.front_seat(ci.spec());wheel=ci.steering(ci.spec());cards=[ci.door_card(ci.spec(1,pos)) for pos in ['front','rear']];console=ci.console(ci.spec());lining=ci.lining(ci.spec());dash=ci.dash(ci.spec());dials=ci.instruments(ci.spec());rear=ci.rear_bench(ci.spec())
parts=[seat,wheel,*cards,console,lining,dash,dials,rear];fit=ci.report(parts)
check('selected_structural_meshes_closed',all(fit['closed_selected_meshes'].values()));check('nominal_seat_clearance',not fit['seat_card_console_intersections']);check('finite_geometry',all(x['finite'] for x in fit['components'].values()))
floors=[o for o in lining.objects if o.type=='MESH' and any(t in o.name for t in ['centre floor','front floor wing','cargo floor wing'])]
def xybox(o):return [min(v.co.x for v in o.data.vertices),max(v.co.x for v in o.data.vertices),min(v.co.y for v in o.data.vertices),max(v.co.y for v in o.data.vertices)]
bb=[xybox(o) for o in floors]
check('floor_faces_do_not_overlap',all(min(a[1],b[1])-max(a[0],b[0])<1e-6 or min(a[3],b[3])-max(a[2],b[2])<1e-6 for i,a in enumerate(bb) for b in bb[i+1:]))
feet=[o for o in seat.objects if 'fixed floor foot' in o.name];rails_ob=[o for o in seat.objects if 'fixed floor rail' in o.name]
check('feet_join_floor_to_rails',len(feet)==4 and all(any(wf.tree(o).overlap(wf.tree(f)) for f in floors) and any(wf.tree(o).overlap(wf.tree(r)) for r in rails_ob) for o in feet))
rails=verts(seat,'fixed floor rail');cushion=verts(seat,'sculpted cushion');others={c.name:wf.fingerprint(c) for c in parts if c!=seat}
seat=ci.rebuild(seat,ci.spec(slide=.035));moved=verts(seat,'sculpted cushion')
check('seat_offset_moves_real_cushion',len(cushion)==len(moved) and all(abs(b[1]-a[1]-.035)<1e-6 for a,b in zip(cushion,moved)))
check('seat_offset_keeps_floor_rails_fixed',verts(seat,'fixed floor rail')==rails)
check('seat_offset_preserves_other_components',all(wf.fingerprint(bpy.data.collections[n])==fp for n,fp in others.items()))
check('forward_limit_clearance',not ci.report([seat,*cards,console])['seat_card_console_intersections'])
seat=ci.rebuild(seat,ci.spec(slide=-.035));check('rearward_limit_clearance',not ci.report([seat,*cards,console])['seat_card_console_intersections'])
before=verts(wheel,'shaped rim');spokes=verts(wheel,'spoke');wheel=ci.rebuild(wheel,ci.spec(wheel_radius=.185))
check('radius_changes_rim_geometry',verts(wheel,'shaped rim')!=before);check('radius_changes_spoke_geometry',verts(wheel,'spoke')!=spokes)
fp=wf.fingerprint(seat)
try:ci.rebuild(seat,ci.spec(slide=.4));blocked=False
except ValueError:blocked=True
check('invalid_offset_preserves_component',blocked and wf.fingerprint(seat)==fp)
original=ci.BUILDERS['front_seat'];collections=set(bpy.data.collections)
def failed(s,n):original(s,n);raise RuntimeError('Injected staging failure')
ci.BUILDERS['front_seat']=failed
try:ci.rebuild(seat,ci.spec());blocked=False
except RuntimeError:blocked=True
ci.BUILDERS['front_seat']=original
check('failed_staging_rolls_back',blocked and set(bpy.data.collections)==collections and wf.fingerprint(seat)==fp)
skin=next(o for o in seat.objects if o.type=='MESH' and 'sculpted cushion' in o.name);skin.data.vertices[0].co.z+=.01;fp=wf.fingerprint(seat)
try:ci.rebuild(seat,ci.spec());blocked=False
except RuntimeError:blocked=True
check('manual_edit_refused_and_preserved',blocked and wf.fingerprint(seat)==fp)
ci.register();check('sidebar_registers',hasattr(bpy.types.Scene,'gtci'));ci.unregister()
hashes={c.name:wf.fingerprint(c) for c in bpy.data.collections if c.get('gt_owner')==ci.OWNER};bpy.ops.wm.save_as_mainfile(filepath=str(out/'reopen-probe.blend'));bpy.ops.wm.open_mainfile(filepath=str(out/'reopen-probe.blend'))
check('save_reopen_preserves_components',all(wf.fingerprint(bpy.data.collections[n])==fp for n,fp in hashes.items()))
(out/'tests.json').write_text(json.dumps(dict(checks=checks,fit=fit),indent=2));print('COCKPIT_TESTS '+json.dumps(checks),flush=True)
