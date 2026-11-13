"""Continue the saved RR assembly in a fresh, non-overwriting revision."""
import bpy,bmesh,sys,json,argparse,shutil,zipfile
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import door_window_workshop as dw
wf=dw.wf
p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--no-render',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output).resolve()
if out.exists() and any(out.iterdir()):raise RuntimeError('Use an empty revision directory')
out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath='C:/GrandTour/Art/Export/VehicleTools/bonnet-bumper-workshop-v04/RangeRover_Bonnet_Bumper_Workshop.blend')
sc=bpy.context.scene;cam=sc.camera;sc.cycles.samples=40;sc.render.threads_mode='FIXED';sc.render.threads=10
sc.render.resolution_x=1200;sc.render.resolution_y=900
protected={c.name:wf.fingerprint(c) for c in bpy.data.collections if c.get('gt_owner') in [wf.OWNER,'GT_LIGHTS_01','GT_BONNET_BUMPER_01']}
views={'whole':((5,-7,3.5),(0,.04,.88),5.65),
       'side':((6,.55,1.03),(0,.55,1.03),3.55),
       'doors':((5,-1.6,2.2),(.90,.10,1.00),2.32),
       'mirror':((3,1.25,2.05),(1.015,-.62,1.29),.71),
       'handle':((4,-.35,1.85),(.917,.05,1.056),.42),
       'window':((5,-.7,2.2),(.84,.25,1.48),2.27)}
def view(key):
    loc,target,scale=views[key];cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
def render(name,key,clay=False):
    view(key);sc.view_layers[0].material_override=wf.material('Workshop | review clay',(.36,.37,.36),.75) if clay else None
    if not a.no_render:sc.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
    sc.view_layers[0].material_override=None
render('01-before-whole','whole');render('02-before-side','side')
car=bpy.data.collections['Range Rover Classic — stylized study'];removed=[]
for ob in list(car.objects):
    tags=['front side window','rear door window','cargo window','door reveal','door handle','mirror foot','mirror']
    if any(ob.name.startswith(label+' '+tag) for label in ['Left','Right'] for tag in tags) or ('body rubbing strip' in ob.name and ob.location.y<1 and max((ob.matrix_world@v.co).y for v in ob.data.vertices)<1):
        removed.append(ob.name);bpy.data.objects.remove(ob,do_unlink=True)
    elif 'connected body and flares' in ob.name:
        bm=bmesh.new();bm.from_mesh(ob.data)
        for co,no in [((0,1.17,0),(0,1,0)),((0,0,.505),(0,0,1))]:
            bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=co,plane_no=no)
        faces=[f for f in bm.faces if max(v.co.y for v in f.verts)<=1.17001 and min(v.co.y for v in f.verts)>=-.77001 and min(v.co.z for v in f.verts)>=.50499 and max(abs(v.co.x) for v in f.verts)<=.92001]
        bmesh.ops.delete(bm,geom=faces,context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
        bm.to_mesh(ob.data);bm.free();removed.append(ob.name+' door skin faces replaced')
parts=[]
for side,label in [(1,'Left'),(-1,'Right')]:
    for pos in ['front','rear']:
        parts.append(dw.door(dw.spec('door',side,pos),label+' | '+pos+' door assembly'))
    for pos in ['front','rear','cargo']:
        parts.append(dw.window(dw.spec('window',side,pos),label+' | '+pos+' window cassette'))
    parts.append(dw.mirror(dw.spec('mirror',side),label+' | mirror assembly'))
    # Fixed jamb backing behind real panel gaps; body-only, outside the editable doors.
    for yy in [-.77,.23,1.17]:
        z0=.505 if yy<.7 else dw.bottom(yy,'rear')-.003
        zs=[z0,1.130,1.157]
        profile=[(side*(dw.edge_x(z)-.014),yy-.015,z) for z in zs]
        profile += [(side*(dw.edge_x(z)-.039),yy-.015,z) for z in reversed(zs)]
        dw.solid(label+' fixed door jamb',profile,(0,.030,0),dw.palette()['shadow'],car,None)
report=dw.fit_report(parts);report['previous_components_preserved']={n:wf.fingerprint(bpy.data.collections[n])==fp for n,fp in protected.items()}
report['components']={c.name:wf.component_report(c) for c in parts};report['replaced_source_parts']=removed
assert all(report['previous_components_preserved'].values()),report
assert max(report['boundary_error_m'].values())<1e-5,report
assert all(report['closed_meshes'].values()),report
(out/'fit-report.json').write_text(json.dumps(report,indent=2))
for f in [Path(__file__),Path(dw.__file__),Path(wf.__file__)]:shutil.copy2(f,out/f.name)
with zipfile.ZipFile(out/'GrandTour_Doors_Windows_Addon.zip','w',zipfile.ZIP_DEFLATED) as z:
    z.write(dw.__file__,'grandtour_doors/__init__.py');z.write(wf.__file__,'grandtour_doors/wheel_fender_workshop.py')
for c in parts:c.asset_mark();c.asset_data.description='Fitted static RR side component; edit protection, shared body/window boundary.'
bpy.data.libraries.write(str(out/'Door_Window_Components.blend'),set(parts),fake_user=True)
t=bpy.data.texts.new('START HERE - doors windows workshop.py')
t.write("import sys\nsys.path.insert(0, 'C:/GrandTour/Art/VehicleTools')\nimport door_window_workshop\ndoor_window_workshop.register()\n")
t=bpy.data.texts.new('DOORS WINDOWS - instructions')
t.write('GT Parts: select a door and adjust pressing relief, or a window and adjust seal width, then rebuild.\nEach of four doors, six window cassettes and two mirrors is independently authored.\nActual handle apertures and recessed cups, frame thickness, inset solid panes and open-backed mirror housings.\nDirect edits are protected by refusing rebuilds. Save manual variants or migrate edits into the source deliberately.\nStatic fit only. Doors have no operating hinge rig. The original interior is still a placeholder.\nNo UV, LOD, animation clearance or game-export validation.\n')
render('03-after-whole','whole');render('04-after-side','side');render('05-door-detail','doors')
render('06-handle-detail','handle');render('07-mirror-detail','mirror');render('08-window-detail','window');render('09-side-clay','doors',True)
keep={o for c in parts if c.name.startswith('Left') for o in c.objects};hidden=[]
for o in sc.objects:
    if o.type in ['MESH','FONT','CURVE','SURFACE'] and o not in keep and o.name!='Ground' and not o.hide_render:hidden.append(o);o.hide_render=True
offsets={}
for c in parts:
    if not c.name.startswith('Left'):continue
    root=next(o for o in c.objects if o.get('mount'));offsets[root]=root.location.copy()
    if c['kind']=='window':root.location.z+=.13
    if c['kind']=='mirror':root.location.x+=.18;root.location.y-=.16
views['parts']=((5,-2,2.7),(.9,.55,1.12),3.95)
render('10-separated-parts','parts')
for o,loc in offsets.items():o.location=loc
for o in hidden:o.hide_render=False
for c in parts:dw.seal(c)
assert all(wf.fingerprint(bpy.data.collections[n])==fp for n,fp in protected.items())
view('whole');sc['door_window_fit_report']=json.dumps(report)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'RangeRover_Doors_Windows_Workshop.blend'))
print('DOORS_WINDOWS_SAVED '+str(out),flush=True)
