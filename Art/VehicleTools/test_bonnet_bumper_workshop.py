"""Meaningful fixed-boundary, insert-variant and edit-preservation probes."""
import bpy,bmesh,sys,json,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bonnet_bumper_workshop as bb
wf=bb.wf
p=argparse.ArgumentParser();p.add_argument('--output',required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);results={}
def check(name,v):results[name]=bool(v);assert v,name
h=bb.bonnet(bb.HOOD);b=bb.bumper(bb.BUMPER)
spec=dict(center=[0,0,0],side=1,interface='rr-bumper-insert-v1',variant='vent');i=bb.insert(spec)
rep=bb.fit_report(h,b,[i]);check('nominal_fit',rep['bonnet_boundary_error_m']<1e-6 and not rep['insert_carrier_intersections'])
guard=next(o for o in b.objects if 'folded lower guard' in o.name)
beam=next(o for o in b.objects if 'stepped carrier' in o.name)
tabs=[o for o in b.objects if 'lower guard mounting tab' in o.name]
check('guard_tabs_contact_guard_and_carrier',len(tabs)==2 and all(wf.tree(t).overlap(wf.tree(guard)) and wf.tree(t).overlap(wf.tree(beam)) for t in tabs))
skin=next(o for o in h.objects if 'crowned folded skin' in o.name)
bm=bmesh.new();bm.from_mesh(skin.data);check('bonnet_skin_closed',all(e.is_manifold for e in bm.edges));bm.free()
check('leading_edge_stays_level',max(v.co.z for v in list(skin.data.vertices)[:6])-min(v.co.z for v in list(skin.data.vertices)[:6])<1e-6)
pad=next(o for o in h.objects if 'latch mounting pad' in o.name)
pad_error=0
for v in list(pad.data.vertices)[:4]:
    y=v.co.y;lift=bb.RISE[0]+(bb.RISE[1]-bb.RISE[0])*(y-bb.STATIONS[0])/(bb.STATIONS[1]-bb.STATIONS[0])
    pad_error=max(pad_error,abs(v.co.z-(bb.shoulder(y)+.006+bb.HOOD['crown']*lift-.004)))
check('latch_pad_follows_underside',pad_error<1e-6)
oldmax=max(v.co.z for v in skin.data.vertices);bh=wf.fingerprint(b);ih=wf.fingerprint(i)
h=bb.rebuild(h,dict(bb.HOOD,crown=.068,plateau=.60));rep=bb.fit_report(h,b,[i])
skin=next(o for o in h.objects if 'crowned folded skin' in o.name)
check('crown_changes_surface',max(v.co.z for v in skin.data.vertices)>oldmax+.014)
check('crown_preserves_mating_boundary',rep['bonnet_boundary_error_m']<1e-6)
check('bonnet_rebuild_preserves_bumper_and_insert',bh==wf.fingerprint(b) and ih==wf.fingerprint(i))
hh=wf.fingerprint(h);i=bb.rebuild(i,dict(spec,variant='blank'))
check('blank_insert_is_real_variant',any('blank cover' in o.name for o in i.objects) and not any('recessed louvre' in o.name for o in i.objects))
check('insert_swap_preserves_carrier_and_bonnet',wf.fingerprint(b)==bh and wf.fingerprint(h)==hh)
check('blank_variant_fits',not bb.fit_report(h,b,[i])['insert_carrier_intersections'])
root=next(o for o in i.objects if o.get('mount'));root.location.x+=.012
check('deliberate_insert_collision_detected',bool(bb.fit_report(h,b,[i])['insert_carrier_intersections']))
root.location.x-=.012;bb.seal(i)
skin.data.vertices[0].co.x+=.003
check('deliberate_bonnet_edge_error_detected',bb.fit_report(h,b,[i])['bonnet_boundary_error_m']>.0029)
fp=wf.fingerprint(h)
try:bb.rebuild(h,bb.HOOD);blocked=False
except RuntimeError:blocked=True
check('manual_edit_preserved',blocked and wf.fingerprint(h)==fp)
skin.data.vertices[0].co.x-=.003;bb.seal(h);fp=wf.fingerprint(h)
try:bb.rebuild(h,dict(bb.HOOD,crown=.15));blocked=False
except ValueError:blocked=True
check('unsupported_crown_preserved',blocked and wf.fingerprint(h)==fp)
bb.register();check('sidebar_registers',hasattr(bpy.types.Scene,'gtbb'));bb.unregister()
hashes={c.name:wf.fingerprint(c) for c in [h,b,i]}
bpy.ops.wm.save_as_mainfile(filepath=str(out/'reopen-probe.blend'));bpy.ops.wm.open_mainfile(filepath=str(out/'reopen-probe.blend'))
check('save_reopen_preserves_parts',all(wf.fingerprint(bpy.data.collections[n])==fp for n,fp in hashes.items()))
(out/'tests.json').write_text(json.dumps({'checks':results,'nominal_fit':rep},indent=2))
print('BONNET_BUMPER_TESTS '+json.dumps(results),flush=True)
