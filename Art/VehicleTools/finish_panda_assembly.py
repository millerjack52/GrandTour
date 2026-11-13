import bpy,bmesh,json,ast,math
from pathlib import Path
from mathutils import Vector,Matrix
S=3.6;OUT=Path('C:/GrandTour/Art/Export/VehicleTools/panda-assembly-v02')
if (OUT/'delivery-manifest.json').exists():raise RuntimeError('Delivered revision is protected. Make a new revision and preserve user edits before further repairs.')
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Panda_Assembly.blend'))
spec=json.loads((OUT/'vehicle-spec.json').read_text());WIDTH=spec['width_profile'];ARCH=spec['arches'];sc=bpy.context.scene
cols={c.name:c for c in bpy.data.collections};M={m.name.split(' | ')[-1]:m for m in bpy.data.materials if m.name.startswith('Panda | ')};root=bpy.data.objects['PANDA | assembly'];owned=[]
module=ast.parse(Path('C:/GrandTour/Art/VehicleTools/build_panda_assembly.py').read_text())
for node in module.body:
 if isinstance(node,ast.FunctionDef) and node.name in ['parent_keep','make','orient','grid','ring','sidep','interp','sx','strip','aperture','box']:
  exec(compile(ast.Module(body=[node],type_ignores=[]),'panda_shared','exec'))
doorpoly=[(-.184,aperture(-.184))]+[(y,z) for y,z in ARCH['F'] if y>-.184]+[(.13,.135),(.13,.455),(-.041,.455),(-.184,.322)]
for label,sign in [('L',1),('R',-1)]:
 name=label+' full door reveal backing';old=bpy.data.objects.get(name)
 if old:bpy.data.objects.remove(old,do_unlink=True)
 strip(name,doorpoly,sign)
 old=bpy.data.objects.get(label+' sill')
 if old:bpy.data.objects.remove(old,do_unlink=True)
 box(label+' sill',(sign*.2165,-.0185,.135),(.015,.297,.009),mat='Rubber',bevel=.002)
for name in ['Firewall','Firewall upper','Firewall lower']:
 old=bpy.data.objects.get(name)
 if old:bpy.data.objects.remove(old,do_unlink=True)
box('Firewall upper',(0,-.196,.260),(.415,.012,.097),'Underbody','Inner',.002)
box('Firewall lower',(0,-.196,.173),(.277,.012,.077),'Underbody','Inner',.002)
for o in owned:
 bpy.context.view_layer.objects.active=o;o.select_set(True)
 for mod in list(o.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)
 o['component_group']=o.users_collection[0].name
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.015);bpy.ops.object.mode_set(mode='OBJECT');o.select_set(False)
# Group tread geometry with its carcass, keeping four independent tyre components.
for code in ['LF','RF','LR','RR']:
 group=[o for o in bpy.data.objects if o.type=='MESH' and (o.name==code+' tyre' or o.name.startswith(code+' tread '))]
 bpy.ops.object.select_all(action='DESELECT')
 for o in group:o.select_set(True)
 bpy.context.view_layer.objects.active=bpy.data.objects[code+' tyre']
 if len(group)>1:bpy.ops.object.join()
# Modest modelling foot height is the tyres' bottom; do not distort body/wheel spacing.
# Ground plane for review is placed at that actual bottom rather than moving geometry.
spec['door_outline']=doorpoly;spec['revision_notes']=['User identified small-wheel/large-arch imbalance. Tyre diameter increased 6.3%, wheel centres unchanged.','Arch crown reduced from .233 to .216 raw units; opening length reduced from .255 to .244.','Door backing follows every new arch bend, upper rear corner wraps close hatch-to-quarter transition.','Tyre treads consolidated with carcasses into four named components.']
(OUT/'vehicle-spec.json').write_text(json.dumps(spec,indent=2));(OUT/'build-script.py').write_text(Path('C:/GrandTour/Art/VehicleTools/build_panda_assembly.py').read_text())
meshes=[o for o in sc.objects if o.type=='MESH' and not o.name.startswith('SOURCE')]
for o in sc.objects:o.select_set(False)
for o in meshes+[o for o in sc.objects if o.type=='EMPTY' and not o.name.startswith('SOURCE')]:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'Panda_Assembly.glb'),export_format='GLB',use_selection=True,export_apply=True,export_extras=True)
bpy.ops.export_scene.fbx(filepath=str(OUT/'Panda_Assembly.fbx'),use_selection=True,object_types={'MESH','EMPTY'},apply_unit_scale=True,axis_forward='-Y',axis_up='Z',add_leaf_bones=False)
bpy.ops.object.select_all(action='DESELECT')
center=Vector((0,0,.268))*S;cam=sc.camera
views=[('side',(3,0,.268),1.20),('quarter',(1.7,-2.7,1.35),1.28),('rear-quarter',(1.8,2.6,1.1),1.28),('wheel-off',(2,-.1,.16),1.2)]
for name,pos,scale in views:
 cols['Wheels'].hide_render=name=='wheel-off';cam.location=Vector(pos)*S;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale*S;sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
cols['Wheels'].hide_render=False
cam.location=Vector((1.7,-2.7,1.35))*S;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=1.28*S
report={'objects':len(meshes),'triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in meshes),'uv_meshes':sum(bool(o.data.uv_layers) for o in meshes),'scope':'Geometry review, basic cockpit, UVs and inspection materials. Not rigged, textured or Unreal tested.'}
(OUT/'build-report.json').write_text(json.dumps(report,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Panda_Assembly.blend'));print(json.dumps(report))
