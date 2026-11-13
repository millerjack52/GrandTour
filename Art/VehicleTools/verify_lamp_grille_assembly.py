"""Reopen final light assembly, check fitted nose openings and packaged add-on."""
import bpy,bmesh,sys,json,argparse,shutil
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import lamp_grille_workshop as lg
wf=lg.wf
p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--render-parts',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output)
bpy.ops.wm.open_mainfile(filepath=str(out/'RangeRover_Lamp_Grille_Workshop.blend'))
parts=[c for c in bpy.data.collections if c.get('gt_owner')==lg.OWNER]
preserved={c.name:wf.fingerprint(c)==c.get('fingerprint') for c in parts};assert all(preserved.values())
earlier=[c for c in bpy.data.collections if c.get('gt_owner')==wf.OWNER]
previous={c.name:wf.fingerprint(c)==c.get('fingerprint') for c in earlier};assert all(previous.values())
cap=bpy.data.objects['Nose fascia | fitted apertures'];cap_tree=wf.tree(cap);contacts=[]
for c in parts:
    for ob in c.objects:
        if ob.type=='MESH' and 'mounting tab' not in ob.name:
            if cap_tree.overlap(wf.tree(ob)):contacts.append([c.name,ob.name])
assert not contacts,contacts
closed={}
for c in parts:
    if c['kind']=='lamp':
        lens=next(o for o in c.objects if 'curved fluted glass' in o.name)
        bm=bmesh.new();bm.from_mesh(lens.data);closed[c.name]=all(e.is_manifold for e in bm.edges);bm.free()
assert all(closed.values()),closed
sys.path.insert(0,str(out/'GrandTour_Lamp_Grille_Addon.zip'))
import grandtour_lights
grandtour_lights.register();registered=hasattr(bpy.types.Scene,'gtlg');grandtour_lights.unregister();assert registered
report=dict(light_components_preserved=preserved,wheel_fender_components_preserved=previous,
            unintended_component_nose_cap_intersections=contacts,closed_manifold_lens_shells=closed,
            packaged_addon_registers=registered,
            scope='Static saved assembly, nose-cap surface fit, closed lens topology and packaged panel registration. Tabs are intended mounts. No full mechanical or optical certification.')
(out/'assembly-reopen-check.json').write_text(json.dumps(report,indent=2))
if a.render_parts:
    left=bpy.data.collections['Left | headlamp cassette'];keep=set(left.objects)
    for o in bpy.context.scene.objects:
        if o.type in ['MESH','FONT','CURVE','SURFACE'] and o not in keep and o.name!='Ground':o.hide_render=True
    groups=[('closed rear shell',-.13),('parabolic reflector',-.03),('outer rubber seat',.035),
            ('retaining bezel',.145),('lens edge gasket',.080),('curved fluted glass',.100)]
    for ob in left.objects:
        for token,dx in groups:
            if token in ob.name:ob.location.x+=dx
    sc=bpy.context.scene;cam=sc.camera;cam.location=(1.6,-3,1.5)
    cam.rotation_euler=(Vector((.69,-2.06,.945))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=.86
    sc.render.filepath=str(out/'08-lamp-components.png');bpy.ops.render.render(write_still=True)
    # Review-only temporary transforms; never save them over the assembled file.
shutil.copy2(__file__,out/Path(__file__).name)
shutil.copy2(Path(__file__).with_name('build_lamp_grille_workshop.py'),out/'build_lamp_grille_workshop.py')
print('LIGHTS_ASSEMBLY_VERIFIED '+json.dumps(report),flush=True)
