import bpy,json,sys,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path('C:/GrandTour/Art/Export/VehicleTools');P=R/'graphic-adventure-assembly-v02';S=4.6
d=json.loads((R/'graphic-adventure-source-v01/island-geometry.json').read_text())[0];src=BVHTree.FromPolygons(d['vertices'],d['faces'])
def tree(objects):
 v=[];f=[];dg=bpy.context.evaluated_depsgraph_get()
 for o in objects:
  ev=o.evaluated_get(dg);m=ev.to_mesh();off=len(v);v.extend((o.matrix_world@p.co)/S for p in m.vertices);f.extend(tuple(off+i for i in p.vertices) for p in m.polygons);ev.to_mesh_clear()
 return BVHTree.FromPolygons(v,f)
samples={'bonnet':([(x,y,.4) for y in [-.43,-.40,-.35,-.30,-.20] for x in [0,.08,.14,.18,.20]],(0,0,-1),2,['Bonnet main pressing']), 'roof':([(x,y,.455) for y in [0,.15,.30] for x in [0,.10,.15,.165,.17]],(0,0,-1),2,['Roof crown']), 'rear_face':([(x,.6,z) for x in [.08,.14] for z in [.192,.20,.22,.24,.25,.26,.28,.29]],(0,-1,0),1,['Lower tailgate'])}
results={}
for version in ['v01','v02']:
 bpy.ops.wm.open_mainfile(filepath=str(R/('graphic-adventure-assembly-'+version)/'GraphicAdventure_Assembly.blend'))
 result={}
 for label,(pts,direction,axis,selectors) in samples.items():
  target=tree([o for o in bpy.context.scene.objects if o.type=='MESH' and any(o.name=='RET | '+q for q in selectors)])
  errors=[];miss=[]
  for p in pts:
   a=src.ray_cast(Vector(p),Vector(direction))[0];b=target.ray_cast(Vector(p),Vector(direction))[0]
   if a is None or b is None:miss.append(p)
   else:errors.append(abs(a[axis]-b[axis])*S*1000)
  result[label]={'samples':len(errors),'mean_surface_offset_mm':sum(errors)/len(errors),'max_surface_offset_mm':max(errors),'misses':miss}
 results[version]=result
for k in samples:assert results['v02'][k]['mean_surface_offset_mm']<results['v01'][k]['mean_surface_offset_mm'],(k,results)
(P/'source-shape-comparison.json').write_text(json.dumps({'description':'Measured source surface offsets at fixed registered rays. Local evidence, not whole-car aesthetic certification.','comparisons':results},indent=2));print('SHAPE',json.dumps(results))
# Render all three at the same side-view scale, with wheels registered identically.
bpy.ops.wm.read_factory_settings(use_empty=True)
mat=bpy.data.materials.new('Comparison clay');mat.diffuse_color=(.48,.53,.54,1)
for version,offset in [('source',-5),('v01',0),('v02',5)]:
 path=R/('graphic-adventure-source-v01' if version=='source' else 'graphic-adventure-assembly-'+version)/('GraphicAdventure_Source.blend' if version=='source' else 'GraphicAdventure_Assembly.blend')
 with bpy.data.libraries.load(str(path),link=False) as (a,b):b.objects=[n for n in a.objects if n=='Tripo_GraphicAdventure_Source'] if version=='source' else [n for n in a.objects if n.startswith(('RET |','GA |'))]
 loaded=[o for o in b.objects if o]
 for o in loaded:bpy.context.scene.collection.objects.link(o)
 bpy.context.view_layer.update()
 for o in loaded:
  if o.type!='MESH':continue
  world=o.matrix_world.copy();o.parent=None;o.matrix_world=world
  if version=='source':o.scale*=S
  o.location.y+=offset;o.hide_render=False;o.hide_set(False);o.data.materials.clear();o.data.materials.append(mat)
 for o in loaded:
  if o.type!='MESH':o.hide_render=True
 curve=bpy.data.curves.new('Label '+version,'FONT');curve.body={'source':'TRIPO SOURCE','v01':'PREVIOUS REBUILD','v02':'CORRECTED REVISION'}[version];curve.align_x='CENTER';curve.size=.20
 ob=bpy.data.objects.new('Label '+version,curve);bpy.context.scene.collection.objects.link(ob);ob.location=(2,offset,2.95);ob.rotation_euler=(math.pi/2,0,math.pi/2)
sc=bpy.context.scene;sc.render.engine='BLENDER_WORKBENCH';sc.world=bpy.data.worlds.new('Comparison world');sc.world.color=(.13,.16,.19);sh=sc.display.shading;sh.light='STUDIO';sh.color_type='MATERIAL';sh.show_cavity=True;sh.cavity_type='BOTH';sh.background_type='WORLD'
cam=bpy.data.objects.new('Comparison',bpy.data.cameras.new('Comparison'));sc.collection.objects.link(cam);sc.camera=cam;cam.location=(30,0,1.6);cam.rotation_euler=(Vector((0,0,1.6))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=15.3
sc.render.resolution_x=3000;sc.render.resolution_y=720;sc.render.resolution_percentage=100;sc.render.filepath=str(P/'side-source-comparison.png');bpy.ops.render.render(write_still=True)
