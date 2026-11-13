"""Separate, fitted expedition equipment on the accepted GT-painted Ferrari."""
import bpy,math,json,hashlib,sys
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
import numpy as np
sys.path.insert(0,'C:/GrandTour/Art/Blender');from gt_paint import core
BASE=Path('C:/GrandTour/Art/Export/VehicleTools/ferrari288-benmore-paint')
OUT=BASE.parent/'ferrari288-expedition-v01';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'Ferrari288_GT_Painted.blend'))
sc=bpy.context.scene
def fingerprint(o):
 h=hashlib.sha256();h.update(np.array(o.matrix_world).tobytes());h.update(np.array([v.co[:] for v in o.data.vertices]).tobytes());h.update(str([tuple(p.vertices) for p in o.data.polygons]).encode())
 for uv in o.data.uv_layers:h.update(np.array([x.uv[:] for x in uv.data]).tobytes())
 return h.hexdigest()
original={o.name:fingerprint(o) for o in bpy.data.objects if o.type=='MESH'}
body=bpy.data.objects['Body | original textured shell'];bvh=BVHTree.FromPolygons([body.matrix_world@v.co for v in body.data.vertices],[p.vertices[:] for p in body.data.polygons])
root=bpy.data.collections.new('CUSTOM | Expedition equipment');sc.collection.children.link(root)
cols={}
for name in ['01 Roof rack and mounts','02 Spare wheel and restraints','03 Equipment case','04 Canvas duffel']:
 c=bpy.data.collections.new(name);root.children.link(c);cols[name[:2]]=c
parts=[]
def material(name,color,rough=.8):
 m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1);bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=rough;return m
steel=material('Expedition | graphite rack',(.025,.035,.036));rubber=material('Expedition | rubber feet',(.012,.016,.018));case=material('Expedition | sand case',(.30,.235,.14));lid=material('Expedition | warm sand lid',(.40,.325,.21));canvas=material('Expedition | sage canvas',(.11,.16,.13));webbing=material('Expedition | ochre straps',(.50,.265,.065));metal=material('Expedition | zinc fasteners',(.34,.36,.33),.5);seam=material('Expedition | canvas edging',(.047,.069,.055));tag=material('Expedition | cream label',(.58,.53,.41))
def finish(o,name,mat,col):
 o.name=name
 for c in list(o.users_collection):c.objects.unlink(o)
 cols[col].objects.link(o);o.data.materials.append(mat);o['module']='Expedition';o['bone']='Root';parts.append(o);return o
def bevel(o,width,segments=3):
 mod=o.modifiers.new('Soft manufactured edges','BEVEL');mod.width=width;mod.segments=segments
 mod=o.modifiers.new('Weighted face normals','WEIGHTED_NORMAL');mod.keep_sharp=True
def box(name,center,size,mat,col,width=.01):
 bpy.ops.mesh.primitive_cube_add(size=1,location=center);o=bpy.context.object;o.dimensions=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);finish(o,name,mat,col)
 if width:bevel(o,width)
 return o
def rod(name,a,b,r,mat,col,vertices=12):
 d=Vector(b)-Vector(a);bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=r,depth=d.length,location=(Vector(a)+Vector(b))/2);o=bpy.context.object;o.rotation_euler=d.to_track_quat('Z','Y').to_euler();finish(o,name,mat,col);bevel(o,min(r*.2,.002),2);return o
def mesh(name,verts,faces,mat,col):
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);cols[col].objects.link(o);me.materials.append(mat);parts.append(o);o['module']='Expedition';o['bone']='Root';return o
def ribbon(name,path,width,across,mat,col):
 # Rectangular closed webbing along a path: real thickness, separate editable mesh.
 across=Vector(across).normalized();verts=[]
 for i,p in enumerate(path):
  tangent=Vector(path[min(i+1,len(path)-1)])-Vector(path[max(0,i-1)]);n=tangent.cross(across).normalized()
  for u,v in [(-1,-1),(-1,1),(1,1),(1,-1)]:verts.append(Vector(p)+across*u*width/2+n*v*.0017)
 faces=[(0,3,2,1)]
 for i in range(len(path)-1):
  for j in range(4):faces.append((4*i+j,4*(i+1)+j,4*(i+1)+(j+1)%4,4*i+(j+1)%4))
 faces.append(tuple(range(len(verts)-4,len(verts))));return mesh(name,verts,faces,mat,col)
deck=1.81;checks={'roof_mounts':[]}
# Four pads conform to the actual roof. Feet land on metal roof, away from glass.
for side in [-1,1]:
 for y in [-.10,.55]:
  x=side*.49;coords=[]
  for dx,dy in [(-.055,-.070),(.055,-.070),(.055,.070),(-.055,.070)]:
   hit,n,i,d=bvh.ray_cast(Vector((x+dx,y+dy,3)),Vector((0,0,-1)),3);assert hit and hit.z>1.60 and n.z>.75,(x+dx,y+dy,str(hit),str(n))
   coords.append((x+dx,y+dy,hit.z-.001))
  coords +=[(a,b,c+.018) for a,b,c in coords]
  pad=mesh('Mount | conforming rubber pad',coords,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],rubber,'01')
  z=max(v[2] for v in coords);box('Mount | saddle',(x,y,z+.012),(.12,.15,.026),steel,'01',.008)
  box('Mount | riser',(x,y,(z+.02+deck-.018)/2),(.045,.065,deck-.018-z-.02),steel,'01',.005)
  for dy in [-.047,.047]:rod('Mount | hex bolt',(x,y+dy,z+.019),(x,y+dy,z+.030),.009,metal,'01',6)
  checks['roof_mounts'].append({'xy':[x,y],'sampled_roof_z':[v[2]+.001 for v in coords[:4]],'contact_overlap_m':.001})
for y in [-.10,.55]:box('Rack | load crossbar',(0,y,deck-.018),(1.34,.055,.035),steel,'01',.009)
# Low-profile rounded basket, kept within the cabin width.
def rounded_ring(name,z,radius=.10):
 points=[]
 for cx,cy,start in [(.58,.92,0),(-.58,.92,90),(-.58,-.28,180),(.58,-.28,270)]:
  for j in range(5):
   a=math.radians(start+j*90/4);points.append((cx+radius*math.cos(a),cy+radius*math.sin(a),z))
 for a,b in zip(points,points[1:]+points[:1]):rod(name,a,b,.015,steel,'01')
rounded_ring('Rack | lower perimeter',deck)
rounded_ring('Rack | upper perimeter',deck+.14)
for side in [-1,1]:
 for y in [-.25,.10,.52,.90]:rod('Rack | rail upright',(side*.68,y,deck),(side*.68,y,deck+.14),.011,steel,'01')
for y in [-.29,-.12,.05,.22,.39,.56,.73,.90]:box('Rack | deck slat',(0,y,deck),(1.30,.042,.025),steel,'01',.007)
for x in [-.44,0,.44]:rod('Rack | front backstay',(x,-.38,deck),(x,-.38,deck+.14),.011,steel,'01')
# Rear-facing spare: copied real wheel geometry, full diameter, rim facing up.
src=bpy.data.objects['Wheel_FL'];spare=src.copy();spare.data=src.data.copy();cols['02'].objects.link(spare);spare.name='Spare | matching full-size wheel';parts.append(spare)
center=Vector(src['pivot']);rot=Matrix.Rotation(-math.pi/2,4,'Y');transform=rot@Matrix.Translation(-center)@src.matrix_world;spare.data.transform(transform);spare.matrix_world=Matrix.Identity(4)
low=min(v.co.z for v in spare.data.vertices);spare.location=(-.16,.43,deck+.014-low);spare['bone']='Root';spare['module']='Expedition'
if 'pivot' in spare:del spare['pivot']
top=max(v.co.z for v in spare.data.vertices)+spare.location.z;top+=.005
ribbon('Spare | fore-aft restraint',[(-.16,-.06,deck+.018),(-.16,-.005,top-.055),(-.16,.07,top),(-.16,.80,top),(-.16,.89,top-.055),(-.16,.94,deck+.018)],.045,(1,0,0),webbing,'02')
ribbon('Spare | lateral restraint',[(-.64,.43,deck+.018),(-.59,.43,top-.055),(-.53,.43,top+.005),(.22,.43,top+.005),(.28,.43,top-.055),(.32,.43,deck+.018)],.045,(0,1,0),webbing,'02')
for x,y in [(-.16,.12),(.15,.43)]:
 box('Spare | ratchet buckle',(x,y,top+.016),(.065,.075,.021),metal,'02',.006);box('Spare | buckle lever',(x,y,top+.030),(.029,.06,.012),steel,'02',.004)
# Slim hard case alongside spare; hinges/latches/handles fitted to its faces.
cx,cy=.485,.46;base=deck+.013
box('Case | moulded shell',(cx,cy,base+.14),(.27,.76,.28),case,'03',.035)
box('Case | gasket',(cx,cy,base+.266),(.274,.766,.012),rubber,'03',.005)
box('Case | overlapping lid',(cx,cy,base+.286),(.292,.782,.043),lid,'03',.015)
for y in [.16,.75]:
 box('Case | lid reinforcement',(cx,y,base+.312),(.23,.031,.016),case,'03',.006)
 for x in [.348,.622]:box('Case | latch',(x,y,base+.25),(.025,.061,.062),steel,'03',.006)
for y in [.23,.66]:
 ribbon('Case | securing webbing',[(.31,y,deck+.02),(.35,y,base+.25),(.365,y,base+.318),(.60,y,base+.318),(.63,y,base+.25),(.65,y,deck+.02)],.033,(0,1,0),webbing,'03')
box('Case | end handle grip',(cx,.053,base+.15),(.13,.022,.025),steel,'03',.006)
for x in [.42,.55]:box('Case | handle hinge',(x,.064,base+.15),(.026,.037,.032),steel,'03',.006)
box('Case | label',(cx,.46,base+.309),(.115,.13,.002),tag,'03',.003)
# Soft transverse duffel at the front, separate from the spare tyre.
box('Duffel | rounded canvas bag',(-.075,-.215,base+.105),(1.06,.275,.21),canvas,'04',.055)
for x in [-.57,.42]:box('Duffel | stitched end panel',(x,-.215,base+.105),(.026,.253,.188),seam,'04',.035)
for x in [-.37,.20]:
 ribbon('Duffel | compression strap',[(x,-.37,deck+.012),(x,-.35,base+.13),(x,-.31,base+.215),(x,-.12,base+.215),(x,-.082,base+.13),(x,-.062,deck+.012)],.036,(1,0,0),webbing,'04')
 box('Duffel | front clasp',(x,-.354,base+.13),(.060,.023,.047),steel,'04',.006)
ribbon('Duffel | carry handle',[(-.20,-.215,base+.215),(-.16,-.215,base+.255),(.015,-.215,base+.255),(.06,-.215,base+.215)],.025,(0,1,0),seam,'04')
box('Duffel | cream patch',(-.075,-.354,base+.11),(.12,.003,.075),tag,'04',.006)
# Fit restraints to each cargo object's evaluated convex silhouette so they
# remain outside rounded corners instead of disappearing through the surface.
bpy.context.view_layer.update()
def fitted_restraint(name,obj,axis,fixed,anchors,width,col,lift=.005):
 evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());me=evaluated.to_mesh()
 points=sorted(set((round((evaluated.matrix_world@v.co)[axis],6),round((evaluated.matrix_world@v.co).z,6)) for v in me.vertices));evaluated.to_mesh_clear()
 def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
 hull=[]
 for point in reversed(points):
  while len(hull)>=2 and cross(hull[-2],hull[-1],point)<=0:hull.pop()
  hull.append(point)
 hull.reverse();mid=(points[0][0]+points[-1][0])/2
 zmid=(min(p[1] for p in points)+max(p[1] for p in points))/2
 path=[anchors[0]]
 for a,z in hull:
  direction=Vector((a-mid,z-zmid)).normalized();a+=direction.x*lift;z+=direction.y*lift
  path.append((a,fixed,z) if axis==0 else (fixed,a,z))
 path.append(anchors[1])
 return ribbon(name,path,width,(0,1,0) if axis==0 else (1,0,0),webbing,col)
for o in list(parts):
 if any(o.name.startswith(prefix) for prefix in ['Spare | fore-aft restraint','Spare | lateral restraint','Case | securing webbing','Duffel | compression strap']):
  parts.remove(o);bpy.data.objects.remove(o,do_unlink=True)
fitted_restraint('Spare | fore-aft restraint',spare,1,-.16,[(-.16,-.06,deck+.018),(-.16,.94,deck+.018)],.045,'02')
fitted_restraint('Spare | lateral restraint',spare,0,.43,[(-.64,.43,deck+.018),(.32,.43,deck+.018)],.045,'02',.010)
# Case shell and lid share a combined outline to keep straps continuous.
case_objs=[bpy.data.objects['Case | moulded shell'],bpy.data.objects['Case | overlapping lid']]
vv=[];ff=[]
for obj in case_objs:
 ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();offset=len(vv)
 vv.extend([ev.matrix_world@v.co for v in me.vertices]);ff.extend([tuple(offset+i for i in f.vertices) for f in me.polygons]);ev.to_mesh_clear()
proxy=mesh('Temporary case envelope',vv,ff,case,'03')
for y in [.23,.66]:fitted_restraint('Case | securing webbing',proxy,0,y,[(.31,y,deck+.02),(.65,y,deck+.02)],.033,'03',.009)
parts.remove(proxy);bpy.data.objects.remove(proxy,do_unlink=True)
for x in [-.37,.20]:fitted_restraint('Duffel | compression strap',bpy.data.objects['Duffel | rounded canvas bag'],1,x,[(x,-.37,deck+.012),(x,-.062,deck+.012)],.036,'04')

# Shared GT Paint colour treatment on new manufactured parts, no artificial chips.
preset=json.loads((BASE/'preset.json').read_text());core.build_group(preset)
for m in [steel,rubber,case,lid,canvas,webbing,metal,seam,tag]:core.build_material(m,None,tuple(m.diffuse_color),preset,(1.6,2.2))
for o in parts:
 if not o.data.uv_layers:
  uv=o.data.uv_layers.new(name='UVMap')
  for p in o.data.polygons:
   for li in p.loop_indices:
    co=o.data.vertices[o.data.loops[li].vertex_index].co;uv.data[li].uv=(co.x,co.y)
assert all(fingerprint(bpy.data.objects[name])==h for name,h in original.items())
# Verify deck clearance over the roof and spare/case separation geometrically.
roof_heights=[]
for x in np.linspace(-.5,.5,11):
 for y in np.linspace(-.1,.55,12):
  hit,n,i,d=bvh.ray_cast(Vector((float(x),float(y),3)),Vector((0,0,-1)),3)
  if hit and hit.z>1.5:roof_heights.append(hit.z)
checks['minimum_deck_roof_clearance_m']=deck-.025-max(roof_heights);assert checks['minimum_deck_roof_clearance_m']>.06
sparemax=max((spare.matrix_world@v.co).x for v in spare.data.vertices);checks['spare_to_case_gap_m']=cx-.292/2-sparemax;assert checks['spare_to_case_gap_m']>.04
sparemin=min((spare.matrix_world@v.co).y for v in spare.data.vertices);checks['spare_to_duffel_gap_m']=sparemin-(-.215+.275/2);assert checks['spare_to_duffel_gap_m']>.03
checks['source_geometry_uv_preserved']=True;checks['objects_added']=len(parts)
checks['new_equipment_top_m']=base+.318;checks['status']='BLENDER_CUSTOMIZATION_REVIEW';checks['limits']=['Static fitted assembly; this equipment has not been exported or added to the Unreal rig yet.','Not an engineering/load-rating certification.']
(OUT/'assembly-checks.json').write_text(json.dumps(checks,indent=2));(OUT/'spec.json').write_text(json.dumps({'source':str(BASE/'Ferrari288_GT_Painted.blend'),'deck_m':deck,'rack_width_m':1.36,'rack_length_m':1.4,'equipment':['Matching full-size spare','Strapped sand equipment case','Strapped sage canvas duffel'],'paint':'Shared GT Paint group on new parts; accepted car material retained'},indent=2))
# Save the editable composition and show a useful uncluttered material viewport.
bpy.ops.object.select_all(action='DESELECT')
sc.camera.data.lens=48;target=Vector((0,0,1.05));sc.camera.location=(5.5,-7,4.3);sc.camera.rotation_euler=(target-sc.camera.location).to_track_quat('-Z','Y').to_euler()
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   space=area.spaces.active;space.shading.type='MATERIAL';space.overlay.show_extras=False;space.region_3d.view_location=target;space.region_3d.view_distance=6.8;space.region_3d.view_rotation=sc.camera.rotation_euler.to_quaternion()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Ferrari288_Expedition.blend'))
sc.render.engine='CYCLES';sc.cycles.samples=32;sc.render.resolution_x=1440;sc.render.resolution_y=1000;sc.render.resolution_percentage=100
def render(name,pos,target,lens=48):
 cam=sc.camera;cam.data.type='PERSP';cam.data.lens=lens;cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
render('front-quarter',(5.5,-7,4.3),(0,0,1.05))
render('rear-quarter',(-5.5,6.8,4.1),(0,.1,1.05))
render('rack-detail',(2.7,-2.8,3.5),(0,.30,1.86),58)
print('EXPEDITION_COMPLETE',json.dumps(checks),flush=True)
