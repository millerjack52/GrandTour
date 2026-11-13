"""Exercise fit, meaningful edits, mirroring, rollback and persisted components."""
import bpy,sys,json,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import door_window_workshop as dw
wf=dw.wf
p=argparse.ArgumentParser();p.add_argument('--output',required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);checks={}
def check(n,v):checks[n]=bool(v);assert v,n
d=dw.door(dw.spec('door'));rear=dw.door(dw.spec('door',1,'rear'));w=dw.window(dw.spec('window'));mirror=dw.mirror(dw.spec('mirror'))
parts=[d,rear,w,mirror];report=dw.fit_report(parts)
check('selected_meshes_closed',all(report['closed_meshes'].values()))
check('skin_boundaries_retained',max(report['boundary_error_m'].values())<1e-6)
skin=next(o for o in d.objects if 'pressed outer skin' in o.name)
tree=wf.tree(skin)
check('handle_aperture_is_open',tree.ray_cast(dw.Vector((1.05,.080,1.058)),dw.Vector((-1,0,0)),.15)[0] is None)
skinrear=next(o for o in rear.objects if 'pressed outer skin' in o.name)
check('rear_door_tracks_arch',all(v.co.z>=dw.bottom(v.co.y,'rear')-.008 for v in skinrear.data.vertices))
others={c.name:wf.fingerprint(c) for c in [rear,w,mirror]}
before=max(v.co.x for v in skin.data.vertices)
d=dw.rebuild(d,dict(dw.spec('door'),relief=1.5));skin=next(o for o in d.objects if 'pressed outer skin' in o.name)
check('relief_changes_geometry',max(v.co.x for v in skin.data.vertices)>before+.003)
check('rebuild_preserves_neighbours',all(wf.fingerprint(bpy.data.collections[n])==fp for n,fp in others.items()))
check('relief_keeps_boundary',max(dw.fit_report([d])['boundary_error_m'].values())<1e-6)
bp=dw.Vector(json.loads(skin['interface_boundary'])[0]);v=min(skin.data.vertices,key=lambda v:(v.co-bp).length)
old=v.co.copy();v.co.x+=.020
check('boundary_fault_detected',max(dw.fit_report([d])['boundary_error_m'].values())>.004)
v.co=old;dw.seal(d)
pane=next(o for o in w.objects if 'inset solid pane' in o.name);area0=sum(p.area for p in pane.data.polygons)
w=dw.rebuild(w,dict(dw.spec('window'),seal_width=.014));pane=next(o for o in w.objects if 'inset solid pane' in o.name)
check('seal_resize_updates_fitted_glass',sum(p.area for p in pane.data.polygons)<area0-.009)
right=dw.door(dw.spec('door',-1),'Right probe');left=dw.door(dw.spec('door',1),'Left probe')
bpy.context.view_layer.update()
ls=next(o for o in left.objects if 'pressed outer skin' in o.name);rs=next(o for o in right.objects if 'pressed outer skin' in o.name)
lp=sorted((round((ls.matrix_world@v.co).x,5),round(v.co.y,5),round(v.co.z,5)) for v in ls.data.vertices)
rp=sorted((round(-(rs.matrix_world@v.co).x,5),round(v.co.y,5),round(v.co.z,5)) for v in rs.data.vertices)
check('left_right_skin_symmetry',lp==rp)
skin.data.vertices[0].co.x+=.005;fp=wf.fingerprint(d)
try:dw.rebuild(d,dw.spec('door'));blocked=False
except RuntimeError:blocked=True
check('manual_edit_preserved',blocked and wf.fingerprint(d)==fp)
fp=wf.fingerprint(w)
try:dw.rebuild(w,dict(dw.spec('window'),seal_width=.04));blocked=False
except ValueError:blocked=True
check('invalid_parameter_preserves_window',blocked and wf.fingerprint(w)==fp)
dw.register();check('sidebar_registers',hasattr(bpy.types.Scene,'gtdw'));dw.unregister()
parts=[d,rear,w,mirror,right,left];hashes={c.name:wf.fingerprint(c) for c in parts}
bpy.ops.wm.save_as_mainfile(filepath=str(out/'reopen-probe.blend'));bpy.ops.wm.open_mainfile(filepath=str(out/'reopen-probe.blend'))
check('saved_parts_reopen_unchanged',all(wf.fingerprint(bpy.data.collections[n])==fp for n,fp in hashes.items()))
(out/'tests.json').write_text(json.dumps(dict(checks=checks,fit=report),indent=2));print('DOOR_WINDOW_TESTS '+json.dumps(checks),flush=True)
