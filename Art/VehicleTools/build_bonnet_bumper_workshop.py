"""Build a new review revision of the bonnet and bumper in the existing assembly."""
import bpy,sys,json,argparse,shutil,zipfile
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bonnet_bumper_workshop as bb
wf=bb.wf
p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--no-render',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output).resolve()
if out.exists() and any(out.iterdir()):raise RuntimeError('Use an empty revision directory')
out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath='C:/GrandTour/Art/Export/VehicleTools/lamp-grille-workshop-v02/RangeRover_Lamp_Grille_Workshop.blend')
sc=bpy.context.scene;cam=sc.camera;sc.cycles.samples=40;sc.render.threads_mode='FIXED';sc.render.threads=10
sc.render.resolution_x=1200;sc.render.resolution_y=900
protected={c.name:wf.fingerprint(c) for c in bpy.data.collections if c.get('gt_owner') in [wf.OWNER,'GT_LIGHTS_01']}
views={'front':((2.5,-5,2.0),(0,-1.96,.88),2.45),'whole':((5,-7,3.5),(0,.04,.88),5.65),
       'top':((0,-1.42,6),(0,-1.42,1.1),2.40),'bumper':((1.6,-4,1.0),(.32,-2.14,.53),1.42),
       'side':((5,-1.55,.75),(0,-1.55,.75),2.05)}
def view(key):
    loc,target,scale=views[key];cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
def render(name,key,clay=False):
    view(key);sc.view_layers[0].material_override=wf.material('Workshop | review clay',(.36,.37,.36),.75) if clay else None
    if not a.no_render:sc.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
    sc.view_layers[0].material_override=None
render('01-before-front','front');render('02-before-whole','whole')
car=bpy.data.collections['Range Rover Classic — stylized study']
for ob in list(car.objects):
    if any(ob.name.startswith(t) for t in ['Broad folded bonnet','Bonnet end fold','Front slim wrap bumper','Front registration plate','Front lower valance']):
        bpy.data.objects.remove(ob,do_unlink=True)
hood=bb.bonnet(bb.HOOD,'Front | bonnet assembly');bumper=bb.bumper(bb.BUMPER,'Front | bumper carrier');inserts=[]
for side,label in [(1,'Left'),(-1,'Right')]:
    s=dict(center=[0,0,0],side=side,interface='rr-bumper-insert-v1',variant='vent')
    inserts.append(bb.insert(s,label+' | bumper insert'))
parts=[hood,bumper]+inserts
report=bb.fit_report(hood,bumper,inserts)
assert report['bonnet_boundary_error_m']<1e-5 and not report['insert_carrier_intersections'],report
report['previous_components_preserved']={n:wf.fingerprint(bpy.data.collections[n])==fp for n,fp in protected.items()}
assert all(report['previous_components_preserved'].values())
report['components']={c.name:wf.component_report(c) for c in parts}
(out/'fit-report.json').write_text(json.dumps(report,indent=2))
for file in [Path(__file__),Path(bb.__file__),Path(wf.__file__)]:shutil.copy2(file,out/file.name)
with zipfile.ZipFile(out/'GrandTour_Bonnet_Bumper_Addon.zip','w',zipfile.ZIP_DEFLATED) as z:
    z.write(bb.__file__,'grandtour_panels/__init__.py');z.write(wf.__file__,'grandtour_panels/wheel_fender_workshop.py')
for c in parts:c.asset_mark();c.asset_data.description='Editable RR bonnet/bumper component, fixed mating interface; static checks only.'
bpy.data.libraries.write(str(out/'Bonnet_Bumper_Components.blend'),set(parts),fake_user=True)
txt=bpy.data.texts.new('START HERE - bonnet bumper workshop.py')
txt.write("import sys\nsys.path.insert(0, 'C:/GrandTour/Art/VehicleTools')\nimport bonnet_bumper_workshop\nbonnet_bumper_workshop.register()\n")
txt=bpy.data.texts.new('BONNET BUMPER - instructions')
txt.write('Use GT Parts after running the START HERE text once.\nSelect a bonnet mesh: crown and centre plateau change its form while the boundary remains fixed.\nSelect a bumper insert mesh: choose vent or blank to swap that insert without rebuilding the carrier.\nDirect edits are preserved by refusing regeneration. Save manual variants instead of overriding protection.\nExisting wheels, fenders and lighting collections remain unchanged.\nThe bonnet has no hinge rig; the bumper is not a crash structure or certified recovery assembly.\nThis is an editable exterior component study, without UV/LOD/export validation.\n')
render('03-after-front','front');render('04-after-whole','whole');render('05-bonnet-top','top');render('06-bumper-detail','bumper');render('07-front-clay','front',True);render('08-side-fit','side')
# Readable separated component view, with typography and context hidden as well.
keep={o for c in parts for o in c.objects};hidden=[]
for o in sc.objects:
    if o.type in ['MESH','FONT','CURVE','SURFACE'] and o not in keep and o.name!='Ground' and not o.hide_render:hidden.append(o);o.hide_render=True
offsets={}
for c in parts:
    root=next(o for o in c.objects if o.get('mount'));offsets[root]=root.location.copy()
    if c==hood:root.location.z+=.18
    elif c in inserts:root.location.y-=.22
views['parts']=((3,-5,2.6),(0,-1.72,.92),2.90)
render('09-separated-parts','parts')
for o,loc in offsets.items():o.location=loc
for o in hidden:o.hide_render=False
for c in parts:bb.seal(c)
assert all(wf.fingerprint(bpy.data.collections[n])==fp for n,fp in protected.items())
view('whole');sc['bonnet_bumper_fit_report']=json.dumps(report)
sc['bonnet_bumper_scope']='Fitted bonnet crown/skin, stepped bumper carrier, corner caps and swappable inserts. Existing wheel/fender/light components preserved; static exterior study.'
bpy.ops.wm.save_as_mainfile(filepath=str(out/'RangeRover_Bonnet_Bumper_Workshop.blend'))
print('BONNET_BUMPER_SAVED '+str(out),flush=True)
