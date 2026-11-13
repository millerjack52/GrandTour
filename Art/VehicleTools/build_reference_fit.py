"""Build a non-destructive diagnostic copy of the rejected Crafted Utility model."""
import bpy,json,sys,math,shutil,hashlib,argparse
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT));import reference_fit_workbench as fit
base=Path('C:/GrandTour/Art/Export/VehicleTools/reference-fit-v01')
parser=argparse.ArgumentParser();parser.add_argument('--output',default=str(base))
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
out=Path(args.output)
if (out/'Crafted_Utility_Reference_Fit.blend').exists():raise RuntimeError('Workbench may contain manual edits. Use --output NEW_FOLDER; never rebuild over it.')
out.mkdir(parents=True,exist_ok=True)
if out.resolve()!=base.resolve():
    for name in ['reference-observations.json','side-reference.png','front-reference.png','original-a-reference.png']:shutil.copy2(base/name,out/name)
source=Path('C:/GrandTour/Art/Export/VehicleTools/crafted-utility-v05/Crafted_Utility.blend')
source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
obs=json.loads((out/'reference-observations.json').read_text())
bpy.ops.wm.open_mainfile(filepath='C:/GrandTour/Art/Export/VehicleTools/crafted-utility-v05/Crafted_Utility.blend')
sc=bpy.context.scene;sc['shape_status']='v05 shape rejected. Diagnostic workbench; no corrected-car claim.'
pres=bpy.data.collections.new('FIT | Preserved rejected v05');sc.collection.children.link(pres)
for c in list(sc.collection.children):
    if c==pres:continue
    sc.collection.children.unlink(c);pres.children.link(c)
for ob in sc.objects:ob.hide_select=True
pres.hide_render=True;pres.hide_viewport=True
work=bpy.data.collections.new('FIT | Editable forms');sc.collection.children.link(work)
guides=bpy.data.collections.new('FIT | Traced targets');sc.collection.children.link(guides)
cams=bpy.data.collections.new('FIT | Cameras');sc.collection.children.link(cams)
# Temporarily evaluate the preserved scene before hiding it; flatten transforms,
# copy mesh data, and keep source names for measurements. No original is edited.
pres.hide_viewport=False;bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
prefixes=['Front fender | formed','Front door | formed','Rear door | formed','Rear quarter | formed',
          'Narrow rolled arch lip','Bonnet |','Roof | shallow','Front door window | frame','Rear door window | frame',
          'Cargo window | frame','Windscreen | frame','Upper tailgate | frame','Rear sail pillar','Lower tailgate | closed',
          'Front | apertured fascia','Bumper | chamfered carrier','Rear | bumper','Rocker | underside',
          'Tyre | shaped carcass','Rim | barrel','Rim | pressed steel','Wheel | centre hub']
for ob in list(sc.objects):
    if ob.type!='MESH' or not any(ob.name.startswith(p) for p in prefixes):continue
    eo=ob.evaluated_get(dg);me=bpy.data.meshes.new_from_object(eo,depsgraph=dg)
    for v in me.vertices:v.co=ob.matrix_world@v.co
    new=bpy.data.objects.new('EDIT | '+ob.name,me);work.objects.link(new);new['fit_source']=ob.name;new.hide_select=False
pres.hide_viewport=True
mat=bpy.data.materials.new('FIT | contour cyan');mat.diffuse_color=(.015,.56,.68,1);mat.use_nodes=True
nodes=mat.node_tree.nodes;nodes.clear();em=nodes.new('ShaderNodeEmission');em.inputs[0].default_value=(.02,.55,.70,1);em.inputs[1].default_value=1
output=nodes.new('ShaderNodeOutputMaterial');mat.node_tree.links.new(em.outputs[0],output.inputs[0])
gold=bpy.data.materials.new('FIT | target gold');gold.diffuse_color=(1,.50,.025,1)
for ob in work.objects:
    ob.data.materials.clear();ob.data.materials.append(mat);ob.show_wire=False

def curve(name,pts,view):
    cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.resolution_u=1;cu.bevel_depth=.002;cu.bevel_resolution=0
    sp=cu.splines.new('POLY');sp.points.add(len(pts)-1)
    for p,v in zip(sp.points,pts):p.co=(*v,1)
    ob=bpy.data.objects.new(name,cu);guides.objects.link(ob);cu.materials.append(gold);ob['fit_view']=view;ob.show_in_front=True;ob.hide_render=True;return ob
for name,pixels in obs['side']['traces'].items():
    s=obs['side'];scale=s['pixels_per_metre']
    pts=[(1.25,s['axle_front_world']+(u-s['front_hub_px'][0])/scale,s['axle_z']+(s['front_hub_px'][1]-v)/scale) for u,v in pixels]
    curve('TARGET | side | '+name,pts,'side')
for name,pixels in obs['front']['traces'].items():
    s=obs['front'];pts=[((u-s['center_u'])/s['pixels_per_metre'],-2.35,(s['ground_v']-v)/s['pixels_per_metre']) for u,v in pixels]
    curve('TARGET | front | '+name,pts,'front')
for key,file in [('side','side-reference.png'),('front','front-reference.png'),('hero','original-a-reference.png')]:
    s=obs[key];data=bpy.data.cameras.new('FIT | '+key);ob=bpy.data.objects.new('FIT | '+key,data);cams.objects.link(ob)
    if key=='side':
        scale=s['pixels_per_metre'];cy=s['axle_front_world']+(s['width']/2-s['front_hub_px'][0])/scale;cz=s['axle_z']+(s['front_hub_px'][1]-s['height']/2)/scale
        ob.location=(8,cy,cz);target=Vector((0,cy,cz));data.type='ORTHO';data.ortho_scale=s['width']/scale
    elif key=='front':
        cx=(s['width']/2-s['center_u'])/s['pixels_per_metre'];cz=(s['ground_v']-s['height']/2)/s['pixels_per_metre'];ob.location=(cx,-8,cz);target=Vector((cx,0,cz));data.type='ORTHO';data.ortho_scale=s['width']/s['pixels_per_metre']
    else:
        ob.location=s['location'];target=Vector(s['target']);data.type='PERSP';data.lens=s['lens_mm'];data.sensor_width=s['sensor_mm'];data.sensor_fit='HORIZONTAL';data.shift_x=s['shift_x'];data.shift_y=s['shift_y']
    ob.rotation_euler=(target-ob.location).to_track_quat('-Z','Y').to_euler();ob.lock_location=(True,)*3;ob.lock_rotation=(True,)*3;ob.lock_scale=(True,)*3
    data.show_background_images=True;bg=data.background_images.new();bg.image=bpy.data.images.load(str(out/file));bg.image.pack();bg.image.use_fake_user=True;bg.alpha=.65;bg.display_depth='FRONT';bg.frame_method='STRETCH'
    ob['registration_status']=s.get('status',s.get('projection',''))
t=bpy.data.texts.new('FIT | observations.json');t.write(json.dumps(obs,indent=2))
fit.register();fit.choose_view(bpy.context,'side');bpy.context.view_layer.update()
# Verify the camera projection numerically, not by guessing from a render.
checks={};s=obs['side'];errs=[]
for y,expected in [(s['axle_front_world'],s['front_hub_px']),(s['axle_rear_world'],s['rear_hub_px'])]:
    pt=world_to_camera_view(sc,sc.camera,Vector((.935,y,s['axle_z'])));actual=(pt.x*s['width'],(1-pt.y)*s['height']);errs.append(math.dist(actual,expected))
checks['side_hub_max_projection_error_px']=max(errs);assert max(errs)<.01
fit.choose_view(bpy.context,'hero');bpy.context.view_layer.update();s=obs['hero'];errs=[]
for p,expected in zip(s['points'],s['predicted']):
    pt=world_to_camera_view(sc,sc.camera,Vector(p));actual=(pt.x*s['width'],(1-pt.y)*s['height']);errs.append(math.dist(actual,expected))
checks['hero_numpy_vs_blender_max_px']=max(errs);assert max(errs)<.02
baseline=fit.measure();(out/'baseline-contour-errors.json').write_text(json.dumps(baseline,indent=2))
# The diagnostic must react to an actual mesh edit, not echo a spec value.
roof=next(o for o in work.objects if o.get('fit_source','').startswith('Roof | shallow'))
for v in roof.data.vertices:v.co.z+=.10
roof.data.update();bpy.context.view_layer.update();probe=fit.measure()
for v in roof.data.vertices:v.co.z-=.10
roof.data.update();bpy.context.view_layer.update()
deltas=[b['model_v']-a['model_v'] for a,b in zip(baseline['roof_crown']['samples'],probe['roof_crown']['samples']) if a['model_v'] is not None and b['model_v'] is not None]
checks['raised_roof_mean_pixel_change']=sum(deltas)/len(deltas);checks['expected_raise_pixel_change']=-.1*obs['side']['pixels_per_metre']
assert abs(checks['raised_roof_mean_pixel_change']-checks['expected_raise_pixel_change'])<.02
checks['work_meshes']=len(work.objects);checks['source_sha256']=source_hash
checks['original_file_modified']=hashlib.sha256(source.read_bytes()).hexdigest()!=source_hash
assert not checks['original_file_modified']
(out/'workbench-checks.json').write_text(json.dumps(checks,indent=2))
txt=bpy.data.texts.new('RUN ME - Reference Fit tools.py');txt.write((ROOT/'reference_fit_workbench.py').read_text())
txt=bpy.data.texts.new('START HERE - Reference Fit');txt.write('The previous shape was rejected. This is a diagnostic copy, not a corrected car.\n\nRun the text RUN ME - Reference Fit tools.py to enable the GT Shape sidebar after reopening; nothing autoruns.\nChoose Original A, Side, or Front. Reference opacity controls the image over the model. Cameras are locked.\nEdit only the meshes in FIT | Editable forms. Yellow curves are editable observed targets, not geometry drivers.\nMeasure edited bonnet and roof writes JSON from evaluated geometry; negative pixel errors mean too high.\nThe original A perspective is authoritative; its fitted camera is provisional. Generated side/front are secondary.\nPreserved rejected v05 is hidden and locked in its own collection. Details remain there for later refitting.\nResolve bonnet drop/crown, roof crown/end, shoulder section, body tuck and window opening shapes before details.\n')
sc.render.engine='CYCLES';sc.cycles.samples=1;sc.cycles.use_denoising=False;sc.render.film_transparent=True;sc.view_settings.view_transform='Standard';sc.view_settings.look='None';sc.view_settings.exposure=0
for key in ['side','hero','front']:
    fit.choose_view(bpy.context,key);sc.render.filepath=str(out/(key+'-baseline-mask.png'));bpy.ops.render.render(write_still=True)
fit.choose_view(bpy.context,'side')
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.shading.type='SOLID';area.spaces.active.shading.color_type='MATERIAL';area.spaces.active.overlay.show_floor=False
            area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.region_3d.view_camera_zoom=0
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Crafted_Utility_Reference_Fit.blend'))
for name in ['reference_fit_workbench.py','build_reference_fit.py','prepare_reference_fit.py']:shutil.copy2(ROOT/name,out/name)
print(json.dumps(checks,indent=2));print('REFERENCE_FIT_READY',flush=True)
