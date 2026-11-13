"""Add fitted light components to a new copy of the wheel/fender review assembly."""
import bpy,sys,json,argparse,shutil,zipfile
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import lamp_grille_workshop as lg
wf=lg.wf
p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--no-render',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output).resolve()
if out.exists() and any(out.iterdir()):raise RuntimeError('Use a new empty output directory')
out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath='C:/GrandTour/Art/Export/VehicleTools/wheel-fender-workshop-v03/RangeRover_Wheel_Fender_Workshop.blend')
sc=bpy.context.scene;cam=sc.camera;sc.cycles.samples=48
sc.render.threads_mode='FIXED';sc.render.threads=10
sc.render.resolution_x=1200;sc.render.resolution_y=900
protected={c.name:wf.fingerprint(c) for c in bpy.data.collections if c.get('gt_owner')==wf.OWNER}
views={'front':((2.5,-5,2.0),(0,-1.96,.88),2.45),
       'whole':((5,-7,3.5),(0,.04,.88),5.65),
       'detail':((1.4,-4,1.3),(.60,-2.02,.930),.79),
       'straight':((0,-6,.91),(0,-2.03,.91),2.05)}
def render(name,key,clay=False):
    loc,target,scale=views[key];cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
    sc.view_layers[0].material_override=wf.material('Workshop | review clay',(.36,.37,.36),.75) if clay else None
    if not a.no_render:sc.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
    sc.view_layers[0].material_override=None
render('01-before-front','front');render('02-before-whole','whole')
car=bpy.data.collections['Range Rover Classic — stylized study']
tokens=['Front grille surround','Grille inset','Grille vertical rib','Grille horizontal edge',
        'Round headlamp bezel','Round ivory headlamp','Indicator housing','Amber indicator','White side lamp']
for ob in list(car.objects):
    if any(ob.name.startswith(token) for token in tokens):bpy.data.objects.remove(ob,do_unlink=True)
cap=lg.adapt_nose(car)
lettering=bpy.data.objects.get('Bonnet lettering')
if lettering:lettering.location.z=1.122;lettering.data.size=.030
parts={}
for side,label in [(1,'Left'),(-1,'Right')]:
    parts[label+' lamp']=lg.lamp(dict(lg.LAMP,center=[side*.690,-2.031,.945],side=side),label+' | headlamp cassette')
    spec=dict(center=[side*.735,-2.031,.724],side=side,interface='rr-indicator-v1')
    parts[label+' indicator']=lg.indicator(spec,label+' | indicator cassette')
parts['Grille']=lg.grille(lg.GRILLE,'Front | grille and carrier')
report=lg.fit_report([parts['Left lamp'],parts['Right lamp']],parts['Grille'])
assert all(r['mount_error_m']<1e-5 and not r['carrier_intersections'] and r['lens_inside_retaining_seat'] for r in report['lamps']),report
report['prior_parts_preserved']={name:wf.fingerprint(bpy.data.collections[name])==fp for name,fp in protected.items()}
assert all(report['prior_parts_preserved'].values()),report
report['components']={name:wf.component_report(c) for name,c in parts.items()}
(out/'fit-report.json').write_text(json.dumps(report,indent=2))
for path in [Path(__file__),Path(lg.__file__),Path(wf.__file__)]:shutil.copy2(path,out/path.name)
with zipfile.ZipFile(out/'GrandTour_Lamp_Grille_Addon.zip','w',zipfile.ZIP_DEFLATED) as z:
    z.write(Path(lg.__file__),'grandtour_lights/__init__.py')
    z.write(Path(wf.__file__),'grandtour_lights/wheel_fender_workshop.py')
for c in parts.values():c.asset_mark();c.asset_data.description='Fitted RR-study lighting component; independent editable geometry; static interface checks.'
bpy.data.libraries.write(str(out/'Lamp_Grille_Components.blend'),set(parts.values()),fake_user=True)
txt=bpy.data.texts.new('START HERE - lighting workshop.py')
txt.write("import sys\nsys.path.insert(0, 'C:/GrandTour/Art/VehicleTools')\nimport lamp_grille_workshop\nlamp_grille_workshop.register()\n")
instructions=bpy.data.texts.new('LIGHTING WORKSHOP - instructions')
instructions.write('Run START HERE - lighting workshop.py once for the GT Parts lighting panel.\nSelect a lamp or grille mesh before using Rebuild. Direct mesh/material edits block regeneration.\nThe headlamp opening is fixed; lens crown and flute pitch are adjustable within tested ranges. Grille slat count supports 4, 5 or 6.\nThe lamp, indicator and grille collections can be appended independently from Lamp_Grille_Components.blend.\nLocal X points forward from each cassette, local Y is car-width direction.\nUnlit review: geometry/materials only. No actual light emitters, optical calibration, UV/LOD/export or driving certification.\nPrior wheel and fender components were preserved.\n')
render('03-after-front','front');render('04-after-whole','whole');render('05-lamp-detail','detail');render('06-front-clay','front',True);render('07-front-straight','straight')
# Separated lamp layers in an isolated review, with real mesh geometry.
left=parts['Left lamp'];keep=set(left.objects);hidden=[]
for o in sc.objects:
    if o.type in ['MESH','FONT','CURVE','SURFACE'] and o not in keep and o.name!='Ground' and not o.hide_render:hidden.append(o);o.hide_render=True
offsets={};groups=[('closed rear shell',-.13),('parabolic reflector',-.03),('outer rubber seat',.035),
                  ('retaining bezel',.145),('lens edge gasket',.080),('curved fluted glass',.100)]
for ob in left.objects:
    for token,dx in groups:
        if token in ob.name:offsets[ob]=ob.location.copy();ob.location.x+=dx
views['exploded']=((1.6,-3,1.5),(.69,-2.06,.945),.86)
render('08-lamp-components','exploded')
for ob,pos in offsets.items():ob.location=pos
for ob in hidden:ob.hide_render=False
for c in parts.values():lg.seal(c)
for name,fp in protected.items():assert wf.fingerprint(bpy.data.collections[name])==fp
loc,target,scale=views['whole'];cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
sc['lighting_scope']='Front lamps, indicators, grille and fitted nose openings. Wheels/fenders preserved. Unlit material/geometry study, no optical or game-ready claim.'
sc['lighting_fit_report']=json.dumps(report)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'RangeRover_Lamp_Grille_Workshop.blend'))
print('LIGHTING_WORKSHOP_SAVED '+str(out),flush=True)
