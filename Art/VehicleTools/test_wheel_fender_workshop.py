"""Meaningful component/fit/edit-safety probes in an independent empty Blender scene."""
import bpy,sys,json,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import wheel_fender_workshop as wf
p=argparse.ArgumentParser();p.add_argument('--output',required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
results={}
def check(name,value):
    results[name]=bool(value)
    if not value:raise AssertionError(name)
s=dict(wf.DEFAULT);wc=wf.wheel(s,'Test wheel');fc=wf.fender(s,'Test fender')
report=wf.fit_report(wc,fc)
check('nominal_static_fit',not report['intersections'] and report['skin_to_lip_boundary_error_m']<1e-6)
skin=next(o for o in fc.objects if 'shoulder and lower' in o.name)
errors=[]
for index in skin['primary_panels']:
    poly=skin.data.polygons[index]
    pts=[skin.data.vertices[i].co for i in poly.vertices]
    normal=(pts[1]-pts[0]).cross(pts[2]-pts[0]).normalized()
    errors.append(abs((pts[3]-pts[0]).dot(normal)))
check('broad_fender_panels_are_planar',max(errors)<1e-6)
edge=next(o for o in fc.objects if 'bonnet edge return' in o.name)
points=[edge.data.vertices[i].co for i in range(len(edge.data.vertices)//2)]
error=0
for a,b in zip(points,points[1:]):
    for t in [0,.25,.5,.75,1]:
        pnt=a.lerp(b,t);yy=pnt.y+s['center'][1]
        width=.875+.045*max(0,min(1,(yy+2.03)/.19))
        error=max(error,abs(pnt.x+s['center'][0]-(width-.035)))
check('bonnet_edge_tracks_taper_between_stations',error<1e-6)
lip=next(o for o in fc.objects if 'arch chamfer' in o.name)
lip.data.vertices[2].co.x+=.004
check('deliberate_boundary_mismatch_detected',wf.fit_report(wc,fc)['skin_to_lip_boundary_error_m']>.0039)
lip.data.vertices[2].co.x-=.004;wf.seal(fc)
# Purposeful bad fit must be detected, rather than a check that merely passes itself.
root=next(o for o in wc.objects if o.get('mount'));root.location.z+=.16
bad=wf.fit_report(wc,fc);check('deliberate_tyre_fender_collision_detected',bool(bad['intersections']))
root.location.z-=.16;bpy.context.view_layer.update();wf.seal(wc)
fender_hash=wf.fingerprint(fc)
# Supported profile input change affects the wheel while preserving neighbouring geometry.
guide=next(o for o in wc.objects if o.get('profile_guide'));guide.data.splines[0].points[3].co.x*=.96
old_carcass=next(o for o in wc.objects if 'shaped carcass' in o.name)
old_vertex=old_carcass.data.vertices[3*64].co.copy();wc=wf.rebuild(wc,s)
new_carcass=next(o for o in wc.objects if 'shaped carcass' in o.name)
new_vertex=new_carcass.data.vertices[3*64].co
check('profile_edit_changes_wheel',abs(new_vertex.x-old_vertex.x*.96)<1e-6 and abs(new_vertex.x-old_vertex.x)>.001)
check('wheel_rebuild_preserves_fender',wf.fingerprint(fc)==fender_hash)
ob=next(o for o in wc.objects if o.type=='MESH');ob.data.vertices[0].co.x+=.002
edited=wf.fingerprint(wc)
try:wf.rebuild(wc,s);blocked=False
except RuntimeError:blocked=True
check('hand_mesh_edit_refused_and_preserved',blocked and wf.fingerprint(wc)==edited)
ob.data.vertices[0].co.x-=.002;wf.seal(wc)
unchanged=wf.fingerprint(wc)
try:wf.rebuild(wc,dict(s,radius=.48));blocked=False
except ValueError:blocked=True
check('unsupported_size_preserves_part',blocked and wf.fingerprint(wc)==unchanged)
# Cause an error after staging has started and ensure old data survives.
guide=next(o for o in wc.objects if o.get('profile_guide'));saved=guide.data.splines[0].points[0].co.copy()
guide.data.splines[0].points[0].co.z=1.0
colls=set(bpy.data.collections)
try:wf.rebuild(wc,s);blocked=False
except ValueError:blocked=True
check('failed_stage_preserves_original_and_cleans_collection',blocked and wf.fingerprint(wc)==unchanged and set(bpy.data.collections)==colls)
guide.data.splines[0].points[0].co=saved
# Shared shader edits should also prevent accidental procedural replacement.
mat=ob.data.materials[0];bs=mat.node_tree.nodes.get('Principled BSDF');savedrough=bs.inputs['Roughness'].default_value
bs.inputs['Roughness'].default_value=.432
try:wf.rebuild(wc,s);blocked=False
except RuntimeError:blocked=True
check('shader_edit_refused',blocked)
bs.inputs['Roughness'].default_value=savedrough;wf.seal(wc)
# Settings at the declared size extremes must fit their independently generated fenders.
for i,(r,w,g) in enumerate([(.36,.24,.05),(.39,.29,.075)]):
    spec=dict(s,radius=r,width=w,clearance=g)
    ww=wf.wheel(spec,'Limit wheel '+str(i));ff=wf.fender(spec,'Limit fender '+str(i))
    rr=wf.fit_report(ww,ff);check('static_fit_at_limit_'+str(i),not rr['intersections'])
    wf.remove_collection(ww);wf.remove_collection(ff)
wf.register();check('sidebar_registered',hasattr(bpy.types.Scene,'gtwf'));wf.unregister()
namew=wc.name;namef=fc.name;hashw=wf.fingerprint(wc);hashf=wf.fingerprint(fc)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'reopen-probe.blend'))
bpy.ops.wm.open_mainfile(filepath=str(out/'reopen-probe.blend'))
check('save_reopen_preserves_wheel',wf.fingerprint(bpy.data.collections[namew])==hashw)
check('save_reopen_preserves_fender',wf.fingerprint(bpy.data.collections[namef])==hashf)
(out/'tests.json').write_text(json.dumps({'checks':results,'nominal_fit':report,'deliberate_collision':bad},indent=2))
print('WORKSHOP_TESTS '+json.dumps(results),flush=True)
