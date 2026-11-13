"""Build a new rear-body revision without overwriting the earlier assembly."""
import bpy,bmesh,sys,json,argparse,shutil,zipfile
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent));import rear_body_workshop as rb
wf=rb.wf
p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--no-render',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output).resolve()
if out.exists() and any(out.iterdir()):raise RuntimeError('Use an empty revision directory')
out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath='C:/GrandTour/Art/Export/VehicleTools/door-window-workshop-v02/RangeRover_Doors_Windows_Workshop.blend')
sc=bpy.context.scene;cam=sc.camera;sc.cycles.samples=40;sc.render.threads_mode='FIXED';sc.render.threads=10
sc.render.resolution_x=1200;sc.render.resolution_y=900
protected={c.name:wf.fingerprint(c) for c in bpy.data.collections if c.get('gt_owner') in [wf.OWNER,'GT_LIGHTS_01','GT_BONNET_BUMPER_01','GT_DOORS_01']}
views={'rear':((4.5,7,3.3),(0,.1,.90),5.65),'rearface':((0,7,1.03),(0,2.2,1.03),2.8),
       'detail':((2.7,5.5,2.35),(0,2.20,.98),2.45),'lamp':((1.6,4.4,1.39),(.817,2.23,.92),.69),
       'quarter':((5,3.3,2.0),(.9,1.55,.98),2.0),'fuel':((-5,3.4,2.0),(-.9,1.78,1.00),1.7),
       'side':((6,.10,1.04),(0,.10,1.04),5.3),'top':((0,.12,7),(0,.12,0),6.5),
       'front':((0,-7,1.04),(0,0,1.04),2.95),'whole':((5,-7,3.5),(0,.04,.88),5.65)}
def view(key):
    loc,target,scale=views[key];cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
def render(name,key,clay=False):
    view(key);sc.view_layers[0].material_override=wf.material('Workshop | review clay',(.36,.37,.36),.75) if clay else None
    if not a.no_render:sc.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
    sc.view_layers[0].material_override=None
render('01-before-rear','rear');render('02-before-rear-face','rearface')
car=bpy.data.collections['Range Rover Classic — stylized study'];removed=[]
for ob in list(car.objects):
    if any(ob.name.startswith(t) for t in ['Tailgate','Rear screen','Rear wiper','Rear lamp','Rear slim wrap bumper','Rear registration panel']) or 'body rubbing strip' in ob.name:
        removed.append(ob.name);bpy.data.objects.remove(ob,do_unlink=True)
    elif 'connected body and flares' in ob.name:
        bm=bmesh.new();bm.from_mesh(ob.data)
        bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=(0,1.17,0),plane_no=(0,1,0))
        faces=[f for f in bm.faces if min(v.co.y for v in f.verts)>=1.16999 or (min(v.co.y for v in f.verts)>.79 and (max(abs(v.co.x) for v in f.verts)>.930 or min(abs(v.co.x) for v in f.verts)<.870))]
        bmesh.ops.delete(bm,geom=faces,context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(ob.data);bm.free()
parts=[]
for side,label in [(1,'Left'),(-1,'Right')]:
    parts.append(rb.quarter(rb.spec(side),label+' | rear quarter assembly'))
    parts.append(rb.lamp(rb.spec(side),label+' | rear lamp cassette'))
parts += [rb.lower_gate(rb.spec(),'Rear | lower tailgate'),rb.upper_gate(rb.spec(),'Rear | upper glazed tailgate'),rb.bumper(rb.spec(),'Rear | step bumper')]
report=rb.fit_report(parts);report['previous_components_preserved']={n:wf.fingerprint(bpy.data.collections[n])==fp for n,fp in protected.items()}
report['components']={c.name:wf.component_report(c) for c in parts};report['replaced_source_parts']=removed
(out/'fit-report.json').write_text(json.dumps(report,indent=2))
assert all(report['previous_components_preserved'].values()) and all(report['closed_selected_meshes'].values()) and not report['lamp_column_intersections'] and max(report['boundary_error_m'].values())<1e-5,report
for f in [Path(__file__),Path(rb.__file__),Path(rb.dw.__file__),Path(wf.__file__)]:shutil.copy2(f,out/f.name)
with zipfile.ZipFile(out/'GrandTour_Rear_Body_Addon.zip','w',zipfile.ZIP_DEFLATED) as z:
    for source,target in [(rb.__file__,'__init__.py'),(rb.dw.__file__,'door_window_workshop.py'),(wf.__file__,'wheel_fender_workshop.py')]:z.write(source,'grandtour_rear/'+target)
for c in parts:c.asset_mark();c.asset_data.description='Independent RR rear-body component, fixed interface and protected rebuild. Static exterior study.'
bpy.data.libraries.write(str(out/'Rear_Body_Components.blend'),set(parts),fake_user=True)
t=bpy.data.texts.new('START HERE - rear body workshop.py');t.write("import sys\nsys.path.insert(0, 'C:/GrandTour/Art/VehicleTools')\nimport rear_body_workshop\nrear_body_workshop.register()\n")
t=bpy.data.texts.new('REAR BODY - instructions');t.write('GT Parts: select lower tailgate to change crown, or a rear lamp to switch ribbed/smooth lenses.\nSeven separate collections: two quarters, two lamps, lower tailgate, glazed upper tailgate, step bumper.\nDirect edits are protected. Save manual variants rather than clearing fingerprints.\nThis is a static exterior assembly: hinge details do not imply a working rig or checked opening sweep.\nExisting 27 workshop components are preserved. Interior, UV/LOD/export and game preparation remain separate.\n')
for name,key,clay in [('03-after-rear','rear',False),('04-after-rear-face','rearface',False),('05-tailgate-detail','detail',False),('06-lamp-detail','lamp',False),('07-quarter-joint','quarter',False),('08-fuel-side','fuel',False),('09-rear-clay','detail',True),('10-side-fit','side',False),('11-top-fit','top',False),('12-front-fit','front',False),('13-whole-car','whole',False)]:render(name,key,clay)
keep={o for c in parts for o in c.objects};hidden=[];offsets={}
for o in sc.objects:
    if o.type in ['MESH','FONT','CURVE','SURFACE'] and o not in keep and o.name!='Ground' and not o.hide_render:hidden.append(o);o.hide_render=True
for c in parts:
    root=next(o for o in c.objects if o.get('mount'));offsets[root]=root.location.copy()
    if c['kind']=='upper_gate':root.location.z+=.18
    if c['kind']=='lamp':root.location.y+=.21
    if c['kind']=='lower_gate':root.location.y+=.10
    if c['kind']=='bumper':root.location.z-=.14
views['parts']=((3.8,6,2.7),(0,1.80,1.0),3.50);render('14-separated-parts','parts')
for ob,loc in offsets.items():ob.location=loc
for ob in hidden:ob.hide_render=False
for c in parts:rb.seal(c)
assert all(wf.fingerprint(bpy.data.collections[n])==fp for n,fp in protected.items())
view('rear');sc['rear_body_fit_report']=json.dumps(report)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'RangeRover_Rear_Body_Workshop.blend'));print('REAR_BODY_SAVED '+str(out),flush=True)
