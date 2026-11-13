"""Render comparison from saved baseline without modifying either model file."""
import bpy
from pathlib import Path
from mathutils import Vector
ROOT=Path('C:/GrandTour/Art/Export/VehicleTools');OUT=ROOT/'porsche-shape-recovery-v01'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Porsche_Source_Locked.blend'))
sc=bpy.context.scene;cam=sc.camera;donor=bpy.data.objects['WORKING - original shape unchanged'];center=Vector((0,0,.94))
with bpy.data.libraries.load(str(ROOT/'porsche-authored-v01/Porsche_Safari_Complete.blend'),link=False) as (src,dst):dst.objects=[n for n in src.objects if not n.startswith('STUDIO_')]
rejected=[]
for o in dst.objects:
 if o and o.type in {'MESH','EMPTY'}:
  sc.collection.objects.link(o);o.hide_render=False;o.hide_set(False)
  if o.type=='MESH':o.color=(.52,.56,.58,1);rejected.append(o)
# Evaluate parent transforms before capturing imported object's world-space matrices.
bpy.context.view_layer.update()
base={o:o.matrix_world.copy() for o in [donor]+rejected}
for o in rejected:o.parent=None;o.matrix_world=base[o]
bpy.context.view_layer.update()
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
print('Comparison rendered; model files unchanged.',len(rejected),'rejected mesh components',flush=True)
