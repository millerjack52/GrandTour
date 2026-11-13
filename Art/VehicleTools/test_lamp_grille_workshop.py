"""Independent light-interface and rebuild probes, without loading any user model."""
import bpy,sys,json,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import lamp_grille_workshop as lg
wf=lg.wf
p=argparse.ArgumentParser();p.add_argument('--output',required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);results={}
def check(name,val):
    results[name]=bool(val)
    assert val,name
left=lg.lamp(lg.LAMP,'Left lamp');right=lg.lamp(dict(lg.LAMP,center=[-.69,-2.031,.945],side=-1),'Right lamp');g=lg.grille(lg.GRILLE)
report=lg.fit_report([left,right],g)
check('nominal_lamp_to_carrier_fit',all(r['mount_error_m']<1e-5 and not r['carrier_intersections'] and r['lens_inside_retaining_seat'] for r in report['lamps']))
root=next(o for o in left.objects if o.get('mount'));root.location.x+=.03
bad=lg.fit_report([left],g)['lamps'][0]
check('deliberate_mount_error_detected',bad['mount_error_m']>.029)
check('deliberate_carrier_collision_detected',bool(bad['carrier_intersections']))
root.location.x-=.03;lg.seal(left)
protected=[wf.fingerprint(right),wf.fingerprint(g)]
glass=next(o for o in left.objects if 'curved fluted glass' in o.name);oldmax=max(v.co.x for v in glass.data.vertices)
left=lg.rebuild(left,dict(lg.LAMP,lens_crown=.022))
glass=next(o for o in left.objects if 'curved fluted glass' in o.name)
check('crown_edit_changes_actual_lens_surface',max(v.co.x for v in glass.data.vertices)>oldmax+.004)
check('lamp_rebuild_preserves_other_lamp_and_grille',protected==[wf.fingerprint(right),wf.fingerprint(g)])
fp=wf.fingerprint(left)
try:lg.rebuild(left,dict(lg.LAMP,radius=.14));blocked=False
except ValueError:blocked=True
check('incompatible_opening_refused_and_preserved',blocked and wf.fingerprint(left)==fp)
glass.data.vertices[0].co.x+=.001;fp=wf.fingerprint(left)
try:lg.rebuild(left,lg.LAMP);blocked=False
except RuntimeError:blocked=True
check('manual_lens_edits_protected',blocked and wf.fingerprint(left)==fp)
glass.data.vertices[0].co.x-=.001;lg.seal(left)
lamp_hash=wf.fingerprint(left)
g=lg.rebuild(g,dict(lg.GRILLE,slats=4))
check('grille_variant_has_four_real_slats',sum('shaped horizontal slat' in o.name for o in g.objects)==4)
check('grille_variant_preserves_lamp',wf.fingerprint(left)==lamp_hash)
# Rebuild failure after creating geometry must leave the original intact.
fp=wf.fingerprint(left);colls=set(bpy.data.collections);saved_lens=lg.lens
def fail(*args):raise RuntimeError('Injected lens-construction failure')
lg.lens=fail
try:lg.rebuild(left,lg.LAMP);blocked=False
except RuntimeError:blocked=True
finally:lg.lens=saved_lens
check('failed_stage_rolls_back',blocked and wf.fingerprint(left)==fp and set(bpy.data.collections)==colls)
lg.register();check('lighting_panel_registers',hasattr(bpy.types.Scene,'gtlg'));lg.unregister()
hashes={c.name:wf.fingerprint(c) for c in [left,right,g]}
bpy.ops.wm.save_as_mainfile(filepath=str(out/'reopen-probe.blend'))
bpy.ops.wm.open_mainfile(filepath=str(out/'reopen-probe.blend'))
check('save_reopen_preserves_components',all(wf.fingerprint(bpy.data.collections[name])==fp for name,fp in hashes.items()))
(out/'tests.json').write_text(json.dumps({'checks':results,'nominal_fit':report},indent=2))
print('LIGHTING_TESTS '+json.dumps(results),flush=True)
