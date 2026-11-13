"""Author fitted cockpit components in a fresh saved rear-body assembly copy."""
import bpy,sys,json,argparse,shutil,zipfile
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent));import cockpit_workshop as ci
wf=ci.wf
p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--no-render',action='store_true');a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output).resolve()
if out.exists() and any(out.iterdir()):raise RuntimeError('Use an empty output directory')
out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath='C:/GrandTour/Art/Export/VehicleTools/rear-body-workshop-v05/RangeRover_Rear_Body_Workshop.blend')
sc=bpy.context.scene;cam=sc.camera;sc.cycles.samples=64;sc.render.threads_mode='FIXED';sc.render.threads=10;sc.render.resolution_x=1200;sc.render.resolution_y=900
owners=[wf.OWNER,'GT_LIGHTS_01','GT_BONNET_BUMPER_01','GT_DOORS_01','GT_REAR_BODY_01'];protected={c.name:wf.fingerprint(c) for c in bpy.data.collections if c.get('gt_owner') in owners}
views={'whole':((5,-7,3.5),(0,.04,.88),5.65,'ORTHO'),
       'driver':((-.410,.260,1.485),(-.410,-.90,1.080),20,'PERSP'),
       'dash':((.05,.470,1.399),(-.10,-.425,1.133),22,'PERSP'),
       'gauges':((-.405,.066,1.359),(-.417,-.372,1.221),48,'PERSP'),
       'seats':((2.8,-3.5,2.5),(.30,.17,1.00),2.30,'ORTHO'),
       'card':((-3.0,-1.5,1.65),(.79,-.26,.86),1.29,'ORTHO'),
       'cabin':((3.7,4.6,3.9),(0,.47,1.08),4.45,'ORTHO'),
       'top':((0,.48,6),(0,.48,0),4.30,'ORTHO'),
       'front':((0,-7,1.05),(0,0,1.05),2.96,'ORTHO'),
       'side':((6,.12,1.05),(0,.12,1.05),5.30,'ORTHO')}
fill_data=bpy.data.lights.new('Cockpit review fill','AREA');fill=bpy.data.objects.new('Cockpit review fill',fill_data);sc.collection.objects.link(fill);fill.location=(0,.43,1.650);fill.rotation_euler=(0,0,0);fill_data.energy=18;fill_data.shape='DISK';fill_data.size=.85;fill.hide_render=True
def view(key):
    loc,target,scale,typ=views[key];cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type=typ
    if typ=='PERSP':cam.data.lens=scale;cam.data.clip_start=.015
    else:cam.data.ortho_scale=scale;cam.data.clip_start=.01
def render(name,key,clay=False):
    view(key);fill.hide_render=key not in ['driver','dash','gauges'];sc.view_layers[0].material_override=wf.material('Workshop | review clay',(.36,.37,.36),.75) if clay else None
    if not a.no_render:sc.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
    sc.view_layers[0].material_override=None;fill.hide_render=True
render('01-before-driver','driver');render('02-before-exterior','whole')
car=bpy.data.collections['Range Rover Classic — stylized study'];removed=[]
for o in list(car.objects):
    if any(o.name.startswith(t) for t in ['Cabin floor','Dashboard mass','Seat cushion','Seat back','Head restraint','Steering silhouette']):removed.append(o.name);bpy.data.objects.remove(o,do_unlink=True)
    elif 'dark wheelhouse' in o.name and sum(v.co.y for v in o.data.vertices)/len(o.data.vertices)>.5:
        removed.append(o.name);bpy.data.objects.remove(o,do_unlink=True)
parts=[ci.dash(ci.spec(),'Cabin | dashboard carrier'),ci.instruments(ci.spec(),'Cabin | instrument cassette'),ci.steering(ci.spec(),'Cabin | steering and pedals'),ci.console(ci.spec(),'Cabin | centre stack and tunnel'),ci.rear_bench(ci.spec(),'Cabin | rear bench'),ci.lining(ci.spec(),'Cabin | floor and lining')]
for side,label in [(1,'Left'),(-1,'Right')]:
    parts.append(ci.front_seat(ci.spec(side),label+' | front seat'))
    for pos in ['front','rear']:parts.append(ci.door_card(ci.spec(side,pos),label+' | '+pos+' door card'))
report=ci.report(parts);report['previous_components_preserved']={n:wf.fingerprint(bpy.data.collections[n])==fp for n,fp in protected.items()};report['replaced_placeholders']=removed
(out/'fit-report.json').write_text(json.dumps(report,indent=2))
assert all(report['closed_selected_meshes'].values()) and not report['seat_card_console_intersections'] and all(report['previous_components_preserved'].values()),report
for f in [Path(__file__),Path(ci.__file__),Path(ci.dw.__file__),Path(wf.__file__)]:shutil.copy2(f,out/f.name)
with zipfile.ZipFile(out/'GrandTour_Cockpit_Addon.zip','w',zipfile.ZIP_DEFLATED) as z:
    for f,n in [(ci.__file__,'__init__.py'),(ci.dw.__file__,'door_window_workshop.py'),(wf.__file__,'wheel_fender_workshop.py')]:z.write(f,'grandtour_cockpit/'+n)
for c in parts:c.asset_mark();c.asset_data.description='Fitted RR cockpit component, editable native meshes, static controls and protected rebuild.'
bpy.data.libraries.write(str(out/'Cockpit_Components.blend'),set(parts),fake_user=True)
t=bpy.data.texts.new('START HERE - cockpit workshop.py');t.write("import sys\nsys.path.insert(0, 'C:/GrandTour/Art/VehicleTools')\nimport cockpit_workshop\ncockpit_workshop.register()\n")
t=bpy.data.texts.new('COCKPIT - instructions');t.write('GT Parts: select a front seat to change fore/aft offset or steering mesh to change rim radius.\nRails stay fixed when the seat offset changes; rim and spoke lengths update together.\nDirect edits are protected; preserve manual variants rather than clearing fingerprints.\nThe existing steering position at X=-0.410 is retained.\nDriver review camera is an artistic viewpoint, not a certified eye box or ergonomics test.\nGauges, pedals, levers, belts and seats are static. No gameplay, restraints, collision, UV/LOD or export certification.\n')
render('03-after-driver','driver');render('04-dashboard-detail','dash');render('05-instrument-detail','gauges');render('06-after-exterior','whole');render('07-front-fit','front');render('08-side-fit','side')
def isolate(collections):
    keep={o for c in collections for o in c.objects};hidden=[]
    for o in sc.objects:
        if o.type in ['MESH','FONT','CURVE','SURFACE'] and o not in keep and o.name!='Ground' and not o.hide_render:hidden.append(o);o.hide_render=True
    return hidden
def restore(hidden):
    for o in hidden:o.hide_render=False
hidden=isolate([c for c in parts if c['kind']=='front_seat' and json.loads(c['spec'])['side']==1]);render('09-seat-detail','seats');restore(hidden)
hidden=isolate([c for c in parts if c['kind']=='door_card' and json.loads(c['spec'])['side']==1 and json.loads(c['spec'])['position']=='front']);render('10-door-card','card');restore(hidden)
hidden=isolate(parts)
head=[o for c in parts for o in c.objects if any(t in o.name for t in ['headliner','sun visor','visor hinge','visor support'])]
for o in head:o.hide_render=True
render('11-interior-cutaway','cabin');render('12-interior-top','top');render('13-interior-clay','cabin',True)
for o in head:o.hide_render=False
restore(hidden)
for c in parts:ci.seal(c)
assert all(wf.fingerprint(bpy.data.collections[n])==fp for n,fp in protected.items())
view('whole');sc['cockpit_fit_report']=json.dumps(report);sc['cockpit_driver_camera']=json.dumps(views['driver'])
bpy.ops.wm.save_as_mainfile(filepath=str(out/'RangeRover_Cockpit_Workshop.blend'));print('COCKPIT_SAVED '+str(out),flush=True)

