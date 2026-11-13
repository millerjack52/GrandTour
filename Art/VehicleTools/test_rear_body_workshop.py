"""Meaningful rear-part fit, parameter, fault, rollback and persistence probes."""
import bpy,sys,json,argparse
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent));import rear_body_workshop as rb
wf=rb.wf
p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);checks={}
def check(n,v):checks[n]=bool(v);assert v,n
q=rb.quarter(rb.spec());g=rb.lower_gate(rb.spec());u=rb.upper_gate(rb.spec());l=rb.lamp(rb.spec());b=rb.bumper(rb.spec());parts=[q,g,u,l,b]
fit=rb.fit_report(parts);check('nominal_boundaries',max(fit['boundary_error_m'].values())<1e-6);check('selected_meshes_closed',all(fit['closed_selected_meshes'].values()));check('lamp_fits_aperture',not fit['lamp_column_intersections'])
skin=next(o for o in g.objects if 'crowned sheet' in o.name)
visible=[p for p in skin.data.polygons if p.normal.y>.5]
planarity=max(abs((skin.data.vertices[i].co-skin.data.vertices[p.vertices[0]].co).dot(p.normal)) for p in visible for i in p.vertices)
check('tailgate_visible_faces_planar',planarity<1e-6)
check('registration_opening_is_real',wf.tree(skin).ray_cast(Vector((0,2.40,.879)),Vector((0,-1,0)),.25)[0] is None)
leaves=[o for o in g.objects if 'fitted hinge leaf' in o.name];barrels=[o for o in g.objects if 'hinge barrel' in o.name]
check('lower_hinges_seated',len(leaves)==2 and all(wf.tree(h).overlap(wf.tree(skin)) and any(wf.tree(h).overlap(wf.tree(b)) for b in barrels) for h in leaves))
beam=next(o for o in b.objects if 'stepped carrier' in o.name);bed=next(o for o in b.objects if 'upper tread bed' in o.name)
check('tread_bed_seated_on_carrier',bool(wf.tree(beam).overlap(wf.tree(bed))))
frame=next(o for o in u.objects if 'mitred glazed frame' in o.name)
hinges=[o for o in u.objects if 'roof hinge bracket' in o.name]
check('hinges_contact_upper_frame',len(hinges)==2 and all(wf.tree(h).overlap(wf.tree(frame)) for h in hinges))
header=next(o for o in u.objects if 'roof header weather seal' in o.name)
check('roof_header_seated_on_frame',bool(wf.tree(header).overlap(wf.tree(frame))))
before=max(v.co.y for v in skin.data.vertices);others={c.name:wf.fingerprint(c) for c in [q,u,l,b]}
g=rb.rebuild(g,rb.spec(crown=.024));skin=next(o for o in g.objects if 'crowned sheet' in o.name)
check('crown_changes_geometry',max(v.co.y for v in skin.data.vertices)>before+.006)
check('crown_preserves_boundary',max(rb.fit_report([g])['boundary_error_m'].values())<1e-6)
check('crown_preserves_neighbours',all(wf.fingerprint(bpy.data.collections[n])==fp for n,fp in others.items()))
oldverts=sum(len(o.data.vertices) for o in l.objects if o.type=='MESH' and ' lens' in o.name);qfp=wf.fingerprint(q)
l=rb.rebuild(l,rb.spec(lens='smooth'))
check('smooth_lens_is_real_geometry_variant',sum(len(o.data.vertices) for o in l.objects if o.type=='MESH' and ' lens' in o.name)<oldverts/2)
check('lens_variant_preserves_carrier',wf.fingerprint(q)==qfp and not rb.fit_report([q,l])['lamp_column_intersections'])
root=next(o for o in l.objects if o.get('mount'));root.location.x+=.012
check('deliberate_lamp_collision_detected',bool(rb.fit_report([q,l])['lamp_column_intersections']))
root.location.x-=.012;rb.seal(l)
v=skin.data.vertices[0];v.co.y+=.018;check('boundary_fault_detected',max(rb.fit_report([g])['boundary_error_m'].values())>.004)
fp=wf.fingerprint(g)
try:rb.rebuild(g,rb.spec());blocked=False
except RuntimeError:blocked=True
check('manual_edit_preserved',blocked and wf.fingerprint(g)==fp)
fp=wf.fingerprint(l)
try:rb.rebuild(l,rb.spec(lens='unsupported'));blocked=False
except ValueError:blocked=True
check('unsupported_variant_preserves_component',blocked and wf.fingerprint(l)==fp)
original=rb.BUILDERS['lamp'];before=set(bpy.data.collections)
def failed(s,n):
    original(s,n);raise RuntimeError('Injected staging failure')
rb.BUILDERS['lamp']=failed
try:rb.rebuild(l,rb.spec());blocked=False
except RuntimeError:blocked=True
rb.BUILDERS['lamp']=original
check('staging_failure_rolls_back',blocked and set(bpy.data.collections)==before and wf.fingerprint(l)==fp)
rb.register();check('sidebar_registers',hasattr(bpy.types.Scene,'gtrb'));rb.unregister()
parts=[q,g,u,l,b];hashes={c.name:wf.fingerprint(c) for c in parts};bpy.ops.wm.save_as_mainfile(filepath=str(out/'reopen-probe.blend'));bpy.ops.wm.open_mainfile(filepath=str(out/'reopen-probe.blend'))
check('save_reopen_preserves_parts',all(wf.fingerprint(bpy.data.collections[n])==fp for n,fp in hashes.items()))
(out/'tests.json').write_text(json.dumps(dict(checks=checks,fit=fit),indent=2));print('REAR_TESTS '+json.dumps(checks),flush=True)
