"""Record rejection and establish an unchanged source-shape workbench.
This is a comparison/reference artifact, not another completed vehicle.
"""
import bpy,json,hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path('C:/GrandTour/Art/Export/VehicleTools')
OUT=ROOT/'porsche-shape-recovery-v01';OUT.mkdir(exist_ok=True)
original=Path('C:/Users/mille/Downloads/porshceoffroadtripo.glb')
inspection=json.loads((ROOT/'porsche-source-v01/inspection.json').read_text())
assert hashlib.sha256(original.read_bytes()).hexdigest()==inspection['sha256'],'Original changed; inspect the newer source before using old measurements.'
dest=OUT/'Porsche_Source_Locked.blend'
if dest.exists():raise RuntimeError('Recovery workbench already exists; preserve it and choose a new revision.')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'porsche-source-v01/Porsche_Analysed.blend'))
sc=bpy.context.scene
donor=next(o for o in sc.objects if o.type=='MESH')
for o in list(sc.objects):
 if o!=donor:bpy.data.objects.remove(o,do_unlink=True)
donor.name='WORKING - original shape unchanged';donor.scale=(4.5,4.5,4.5);donor.hide_render=False;donor.hide_set(False)
refcol=bpy.data.collections.new('LOCKED ORIGINAL - do not edit');sc.collection.children.link(refcol)
ref=donor.copy();ref.data=donor.data.copy();ref.name='REFERENCE - untouched Tripo';refcol.objects.link(ref);ref.hide_render=True;ref.hide_set(True);ref.hide_select=True
reference_hash=hashlib.sha256(b''.join(float(v).hex().encode() for p in donor.data.vertices for v in p.co)).hexdigest()
report={'status':'Original-shape baseline restored; cleanup NOT completed','original_file':str(original),'original_sha256':inspection['sha256'],'working_vertex_displacement_from_original_m':0.0,'working_vertex_hash':reference_hash,'rejected_revision':str(ROOT/'porsche-authored-v01/Porsche_Safari_Complete.blend'),'rejection':'That is terrible, you have changed the original shape way too much','failures':['Approximated body sections changed bonnet/wing relationships','Window outlines and pillar layout were redesigned','Rear spoiler and bumpers were replaced with different shapes','Mechanical/topology checks were passed but shape fidelity was not established'],'repair_constraints':['Original Tripo form is the shape authority, including accessories','Do not reuse rejected body generator as shape authority','Use local patch boundaries and source surface constraints; preserve surrounding source positions','Record local displacement and review same-camera side/front/top/quarter silhouettes and curvature','Do not globally remesh/shrinkwrap thin shells or substitute generic roof/window profiles','Shape deviation must be reviewed independently of topology, coverage and collision results']}
(OUT/'recovery-status.json').write_text(json.dumps(report,indent=2))
note=bpy.data.texts.new('READ ME - original shape baseline');note.write('This is an unchanged working copy of the original Tripo mesh at 4.5 metres per donor unit, plus a hidden locked duplicate. It is NOT a cleaned, corrected or game-ready vehicle. The authored-v01 rebuild was rejected for changing the shape. Preserve original proportions, window outlines, arches, wing/bonnet relationship, spoiler and accessory positions during subsequent local repairs.\n')
bpy.ops.object.camera_add();cam=bpy.context.object;cam.name='Comparison Camera';sc.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=5.6
center=Vector((0,0,.94));cam.location=(5,-7,3.4);cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
sc.render.engine='BLENDER_WORKBENCH';sc.render.resolution_x=1500;sc.render.resolution_y=1250;sc.render.resolution_percentage=100
sc.display.shading.light='STUDIO';sc.display.shading.color_type='OBJECT';sc.display.shading.show_cavity=True;sc.display.shading.cavity_type='BOTH';sc.display.shading.show_shadows=True;sc.display.shading.background_type='WORLD';sc.world.color=(.14,.15,.16)
donor.color=(.52,.56,.58,1)
for o in sc.objects:o.select_set(False)
donor.select_set(True);bpy.context.view_layer.objects.active=donor
for a in bpy.context.screen.areas:
 if a.type=='VIEW_3D':a.spaces.active.region_3d.view_location=center;a.spaces.active.region_3d.view_distance=6;a.spaces.active.shading.type='SOLID';a.spaces.active.overlay.show_extras=False
bpy.ops.wm.save_as_mainfile(filepath=str(dest))
# The rejected model is only appended to this temporary comparison scene.
with bpy.data.libraries.load(str(ROOT/'porsche-authored-v01/Porsche_Safari_Complete.blend'),link=False) as (src,dst):
 dst.objects=[n for n in src.objects if not n.startswith('STUDIO_')]
rejected=[]
for o in dst.objects:
 if o and o.type=='MESH':
  sc.collection.objects.link(o);o.hide_render=False;o.hide_set(False);o.color=(.52,.56,.58,1);rejected.append(o)
 # cameras/lights deliberately not linked
base={o:o.matrix_world.copy() for o in [donor]+rejected}
for o in rejected:
 world=o.matrix_world.copy();o.parent=None;o.matrix_world=world
labels=[]
for txt in ['ORIGINAL TRIPO - SHAPE TO PRESERVE','REJECTED REBUILD - SHAPE CHANGED']:
 cu=bpy.data.curves.new(txt,'FONT');cu.body=txt;cu.size=.11;cu.extrude=0;ob=bpy.data.objects.new(txt,cu);sc.collection.objects.link(ob);ob.color=(.86,.87,.85,1);labels.append(ob)
for name,pos,scale,sep in [('side',(8,0,.94),6.4,1.3),('quarter',(5,-7,3.4),7.7,1.55),('front',(0,-8,.94),6.0,1.3),('top',(0,0,8),10.4,2.55)]:
 cam.location=pos;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
 rot=cam.rotation_euler.to_matrix();up=rot@Vector((0,1,0));right=rot@Vector((1,0,0));forward=rot@Vector((0,0,1))
 for o in [donor]+rejected:
  o.matrix_world=base[o].copy();o.matrix_world.translation+=up*(sep if o==donor else -sep)
 for lab,sgn in zip(labels,[1,-1]):lab.rotation_euler=cam.rotation_euler;lab.location=center+right*(-scale*.36)+up*(sgn*sep+(2.28 if name=='top' else (1.25 if name=='quarter' else 1.03)))+forward*3
 sc.render.filepath=str(OUT/('comparison-'+name+'.png'));bpy.ops.render.render(write_still=True)
print(json.dumps(report,indent=2),flush=True)
