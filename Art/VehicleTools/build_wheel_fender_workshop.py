"""Build an isolated revision, matched comparisons, component library and fit evidence."""
import bpy, bmesh, sys, json, argparse, shutil
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import wheel_fender_workshop as wf

p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--no-render',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output).resolve()
if out.exists() and any(out.iterdir()):raise RuntimeError('Use a new empty revision directory')
out.mkdir(parents=True,exist_ok=True)
source=Path('C:/GrandTour/Art/Export/VehicleTools/stylized-rangerover-v02/Stylized_RangeRoverClassic.blend')
bpy.ops.wm.open_mainfile(filepath=str(source));sc=bpy.context.scene;cam=sc.camera
sc.render.resolution_x=1200;sc.render.resolution_y=900;sc.cycles.samples=32
sc.render.threads_mode='FIXED';sc.render.threads=10
views={'detail':((3.5,-3.4,1.65),(.84,-1.32,.67),1.68),
       'whole':((5,-7,3.5),(0,.04,.88),5.65),
       'side':((5,-1.36,.60),(.85,-1.36,.60),1.90),
       'parts':((3,-3,1.9),(.80,-1.36,.75),2.3)}
def view(key):
    loc,target,scale=views[key];cam.location=loc
    cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
def render(name,key,clay=False):
    view(key);sc.view_layers[0].material_override=wf.material('Workshop | review clay',(.36,.37,.36),.75) if clay else None
    if not a.no_render:
        sc.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
    sc.view_layers[0].material_override=None

render('01-before-detail','detail');render('02-before-whole','whole');render('03-before-clay','detail',True)
car=bpy.data.collections.get('Range Rover Classic — stylized study')
# Original body contains an exact station at scuttle -0.77: retain all rear faces.
for sign,label in [(1,'Left'),(-1,'Right')]:
    ob=bpy.data.objects[label+' connected body and flares']
    bm=bmesh.new();bm.from_mesh(ob.data)
    remove=[f for f in bm.faces if max(v.co.y for v in f.verts)<=-.77+.00001]
    bmesh.ops.delete(bm,geom=remove,context='FACES')
    loose=[v for v in bm.verts if not v.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    bm.to_mesh(ob.data);bm.free()
    for old in list(car.objects):
        if (old.name.startswith(label+' front ') or old.name.startswith(label+' rear ')) and any(
            token in old.name for token in ['tyre','alloy','wheel recess','centre cap','hub badge']):
            bpy.data.objects.remove(old,do_unlink=True)
        elif old.name.startswith(label+' clamshell seam'):
            bpy.data.objects.remove(old,do_unlink=True)
        elif old.name.startswith(label+' dark wheelhouse') and old.type=='MESH' and sum(v.co.y for v in old.data.vertices)/len(old.data.vertices)<0:
            bpy.data.objects.remove(old,do_unlink=True)

parts={}
for side,label in [(1,'Left'),(-1,'Right')]:
    for cy,axle in [(-1.36,'front'),(1.27,'rear')]:
        s=dict(wf.DEFAULT,side=side,center=[side*.78,cy,.38])
        parts[label+' '+axle+' wheel']=wf.wheel(s,label+' '+axle+' | workshop wheel')
    s=dict(wf.DEFAULT,side=side,center=[side*.78,-1.36,.38])
    parts[label+' front fender']=wf.fender(s,label+' front | workshop fender')
reports={label:wf.fit_report(parts[label+' front wheel'],parts[label+' front fender']) for label in ['Left','Right']}
for report in reports.values():
    if report['intersections'] or report['skin_to_lip_boundary_error_m']>1e-5:raise RuntimeError(str(report))
reports['components']={k:wf.component_report(v) for k,v in parts.items()}
reports['assembly_scope']='Front fenders and all four wheels only. Rear arch retains original shape. Other body, cockpit and fittings remain baseline placeholders. No articulation or engine export.'
(out/'fit-report.json').write_text(json.dumps(reports,indent=2))
(out/'spec.json').write_text(json.dumps(wf.DEFAULT,indent=2))
for path in [Path(__file__),Path(wf.__file__)]:shutil.copy2(path,out/path.name)

# Embed the optional sidebar source for explicit Run Script, never autorun it.
txt=bpy.data.texts.new('START HERE - workshop.py');txt.write(Path(wf.__file__).read_text())
readme=bpy.data.texts.new('WORKSHOP - instructions')
readme.write('Wheel and Fender Workshop 0.1\n\nRun START HERE - workshop.py in the Text Editor to enable the GT Parts sidebar.\nSelect a wheel mesh, toggle the profile guide, edit its points, then select a wheel mesh again and Rebuild.\nRebuild uses sidebar settings; meshes/materials/modifiers edited by hand refuse regeneration. Save a variant for those edits.\nEach wheel and fender is a separate collection. Parts use metre-scale mount coordinates and an explicit RR front interface.\nCheck Fit after rebuilding; it is a static surface check, not a steering/suspension guarantee.\nLibrary contains only the left front wheel and fender. Existing vehicle source was loaded read-only and saved to a new revision.\nThis is a component study, not a finished vehicle.\n')
for key in ['Left front wheel','Left front fender']:
    parts[key].asset_mark();parts[key].asset_data.description='Editable wheel/fender workshop v0.1; RR front interface; static fit checked.'
bpy.data.libraries.write(str(out/'Wheel_Fender_Components.blend'),{parts['Left front wheel'],parts['Left front fender']},fake_user=True)
render('04-after-detail','detail');render('05-after-whole','whole');render('06-after-clay','detail',True);render('07-after-side','side')

# Exploded component study: hide contextual vehicle and other corners temporarily.
hidden=[]
keep={o for k in ['Left front wheel','Left front fender'] for o in parts[k].objects}
for ob in list(car.objects)+[o for c in parts.values() for o in c.objects]:
    if ob not in keep and not ob.hide_render:hidden.append(ob);ob.hide_render=True
wc=parts['Left front wheel'];fc=parts['Left front fender']
root=next(o for o in wc.objects if o.get('mount'));original=root.location.copy();root.location.x+=.36
render('08-components','parts');root.location=original
for ob in hidden:ob.hide_render=False
view('whole');bpy.context.view_layer.update()
for c in parts.values():wf.seal(c)
sc['workshop_scope']=reports['assembly_scope']
sc['workshop_fit_report']=json.dumps(reports)
for ob in bpy.context.selected_objects:ob.select_set(False)
target=next(o for o in fc.objects if 'shoulder and lower' in o.name)
target.select_set(True);bpy.context.view_layer.objects.active=target
bpy.ops.wm.save_as_mainfile(filepath=str(out/'RangeRover_Wheel_Fender_Workshop.blend'))
print('WORKSHOP_SAVED '+str(out),flush=True)
