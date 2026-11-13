"""Preserve the replacement Tripo exterior; fit glazing, cabin and wheel rig interfaces."""
import bpy,bmesh,sys,json,math,hashlib,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools/vendor_geometry')
from shapely.geometry import Polygon,MultiPoint,Point
from shapely.ops import triangulate
ROOT=Path('C:/GrandTour/Art/Export/VehicleTools');SRC=ROOT/'ferrari288-good-working-v01';OUT=ROOT/'ferrari288-good-game-v01';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SRC/'Ferrari288_LowPoly_Working.blend'));sc=bpy.context.scene
col=bpy.data.collections.new('GAME | fitted additions');sc.collection.children.link(col)
sourcecol=bpy.data.collections['Ferrari | preserved source components'];report={'source':'C:/Users/mille/Downloads/good288.glb','source_sha256':hashlib.sha256(Path('C:/Users/mille/Downloads/good288.glb').read_bytes()).hexdigest(),'glazing':{},'scale_m_per_source_unit':4.5,'limits':['Static doors and cockpit controls; no opening-door gameplay or working mirror cameras.','Provisional stylized dimensions and suspension tune.']}
# Remove only the inspected interior fan surfaces that cross the fitted seats.
body=bpy.data.objects['Body | original textured shell'];old=body.data;bad=[]
for p in old.polygons:
 pts=[body.matrix_world@old.vertices[i].co for i in p.vertices];c=sum(pts,Vector())/len(pts)
 anchor=any((abs(abs(v.x)-.1179)<.001 and abs(v.y-.1375)<.001 and abs(v.z-.1558)<.001) or (abs(abs(v.x)-.0576)<.002 and abs(v.y+.179)<.001 and abs(v.z-.18)<.001) for v in pts)
 if anchor and -.20<c.y<.19 and .145<c.z<.26:bad.append(p.index)
keep=[p for p in old.polygons if p.index not in bad];me=bpy.data.meshes.new('Body | retained exterior and returns');me.from_pydata([v.co for v in old.vertices],[],[list(p.vertices) for p in keep]);me.update()
for m in old.materials:me.materials.append(m)
uv=me.uv_layers.new(name='UVMap');normals=[n.vector.copy() for n in old.corner_normals];nn=[]
for p,q in zip(keep,me.polygons):
 q.material_index=p.material_index;q.use_smooth=p.use_smooth
 for a,b in zip(p.loop_indices,q.loop_indices):uv.data[b].uv=old.uv_layers[0].data[a].uv;nn.append(normals[a])
me.normals_split_custom_set(nn);body.data=me;body['retained_baseline_faces']=json.dumps([p.index for p in keep]);global_ids=json.loads(body['source_face_ids']);body['source_face_ids']=json.dumps([global_ids[p.index] for p in keep]);report['removed_interior_placeholder_faces']=bad
def mat(name,color,rough=.5,metal=0):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;return m
rubber=mat('F288_Rubber',(.018,.022,.024),.75);interior=mat('F288_Cabin',(.032,.035,.038),.8);seatmat=mat('F288_Seats',(.19,.105,.055),.83);metal=mat('F288_Metal',(.3,.32,.33),.3,.75);dial=mat('F288_Dials',(.5,.52,.48),.7)
glass=mat('F288_Glass',(.72,.84,.9),.07);gp=glass.node_tree.nodes.get('Principled BSDF');gp.inputs['Metallic'].default_value=1
gn=glass.node_tree.nodes;gl=glass.node_tree.links;tr=gn.new('ShaderNodeBsdfTransparent');mix=gn.new('ShaderNodeMixShader');mix.inputs[0].default_value=.09;gl.new(tr.outputs[0],mix.inputs[1]);gl.new(gp.outputs[0],mix.inputs[2]);gl.new(mix.outputs[0],gn.get('Material Output').inputs['Surface'])
def mesh(name,verts,faces,material,smooth=False):
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();me.materials.append(material)
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 ob=bpy.data.objects.new(name,me);col.objects.link(ob)
 for p in me.polygons:p.use_smooth=smooth
 return ob
def box(name,loc,size,material,bevel=.002):
 x,y,z=[s/2 for s in size];verts=[(i*x,j*y,k*z) for i,j,k in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]]
 ob=mesh(name,verts,[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)],material);ob.location=loc
 if bevel:md=ob.modifiers.new('Soft manufactured edges','BEVEL');md.width=bevel;md.segments=3
 return ob
def rod(name,a,b,r,material,sides=12):
 a,b=Vector(a),Vector(b);axis=b-a;t=axis.normalized();u=t.cross(Vector((0,0,1)))
 if u.length<.01:u=t.cross(Vector((0,1,0)))
 u.normalize();v=t.cross(u);pts=[list(p+r*(math.cos(i*2*math.pi/sides)*u+math.sin(i*2*math.pi/sides)*v)) for p in [a,b] for i in range(sides)];fs=[tuple(reversed(range(sides))),tuple(range(sides,2*sides))]+[(i,(i+1)%sides,(i+1)%sides+sides,i+sides) for i in range(sides)]
 return mesh(name,pts,fs,material,True)
def glazing(name,data,mirror=False):
 a,b,n=map(Vector,data['axes']);poly=Polygon([(q[0],q[1]) for q in data['ring']]);coef=data['coef'];points=data['ring']
 def dep(x,y):return sum(c*t for c,t in zip(coef,[1,x,y,x*x,x*y,y*y,y**3]))
 def surface(x,y,depth=None):
  p=a*x+b*y+n*(dep(x,y) if depth is None else depth)
  if mirror:p.x=-p.x
  return list(p)
 # Shared fitted pane, gasket, and original aperture lip. Regular sample field avoids fan pinching.
 inner=poly.buffer(-.0014,join_style=1);samples=list(inner.exterior.coords)[:-1];minx,miny,maxx,maxy=inner.bounds
 for x in np.arange(minx,maxx,.009):
  for y in np.arange(miny,maxy,.009):
   if inner.contains(Point(x,y)):samples.append((x,y))
 tris=[t for t in triangulate(MultiPoint(samples)) if inner.buffer(.00001).covers(t)];uv=[];faces=[];ids={}
 for t in tris:
  f=[]
  for xy in list(t.exterior.coords)[:3]:
   key=tuple(round(v,7) for v in xy)
   if key not in ids:ids[key]=len(uv);uv.append(xy)
   f.append(ids[key])
  faces.append(f)
 pane=mesh('Glass | '+name,[surface(x,y) for x,y in uv],faces,glass,True)
 # A single pane surface is intentional; export shader is double sided, no overlapping refractive shells.
 outer=poly.buffer(.0011,join_style=1);inn=poly.buffer(-.0022,join_style=1);N=100;verts=[]
 def edge_depth(q):
  best=None
  for i,p in enumerate(points):
   w=points[(i+1)%len(points)];v=np.array(w[:2])-p[:2];t=float(np.clip(np.dot(np.array(q)-p[:2],v)/max(np.dot(v,v),1e-15),0,1));err=np.linalg.norm(np.array(p[:2])+v*t-q)
   if best is None or err<best[0]:best=(err,p[2]+t*(w[2]-p[2]))
  return best[1]+.00035
 # Match perimeters by ray from common centroid; equal-arclength loops can twist at corners.
 from shapely.geometry import LineString
 center=np.array(poly.centroid.coords[0])
 for shape,outside in [(outer,True),(inn,False)]:
  for i in range(N):
   d=np.array([math.cos(2*math.pi*i/N),math.sin(2*math.pi*i/N)])
   hit=shape.boundary.intersection(LineString([center,center+d]))
   if hit.geom_type=='MultiPoint':hit=min(hit.geoms,key=lambda p:p.distance(Point(center)))
   xy=list(hit.coords)[0]
   verts.append(surface(*xy,edge_depth(xy) if outside else dep(*xy)+.00025))
 seal=mesh('Seal | '+name,verts,[(i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N)],rubber,True)
 report['glazing'][name]={'fit_max_m':data['fit_error_max']*4.5,'triangles':len(faces),'source_aperture_area_m2':poly.area*4.5**2}
for region,rings in json.loads((SRC/'apertures.json').read_text()).items():
 for i,r in enumerate(rings):
  glazing(region+str(i)+' L' if region=='side' else region,r)
  if region=='side':glazing(region+str(i)+' R',r,True)
# The long opening aft of the roof includes the engine deck. A sealed ribbed
# service cover finishes its lower half; the upper half is the rear backlight.
stations=[(.265,.123,.353),(.30,.127,.346),(.35,.132,.331),(.389,.128,.290)]
vv=[(sign*w,y,z) for y,w,z in stations for sign in [-1,1]]
cover=mesh('Engine | fitted rear service cover',vv,[(2*i,2*i+1,2*i+3,2*i+2) for i in range(3)],interior)
solid=cover.modifiers.new('Closed deck thickness','SOLIDIFY');solid.thickness=.003
for y in np.linspace(.276,.378,12):
 for j in range(len(stations)-1):
  ya,wa,za=stations[j];yb,wb,zb=stations[j+1]
  if ya<=y<=yb:
   t=(y-ya)/(yb-ya);w=wa+t*(wb-wa);z=za+t*(zb-za);slope=(zb-za)/(yb-ya);break
 ob=box('Engine | transverse louvre',(0,y,z+.0015),(w*1.88,.006,.003),rubber,.001);ob.rotation_euler.x=math.atan(slope)
# Cabin fits within the preserved body, away from the rear wheelhouses/engine compartment.
box('Cabin | closed floor',(0,-.025,.155),(.350,.365,.016),interior)
box('Chassis | sealed centre tunnel',(0,.015,.115),(.23,.43,.008),rubber,.003)
box('Cabin | front bulkhead',(0,-.20,.20),(.318,.025,.105),interior)
box('Cabin | rear firewall',(0,.125,.23),(.32,.018,.15),interior)
box('Cabin | rear shelf',(0,.17,.286),(.31,.10,.013),interior)
box('Cabin | dashboard',(0,-.157,.248),(.322,.085,.039),interior,.007)
# Close the cowl exposed by removal of the sloping source cabin placeholders.
# Its front edge follows the measured windscreen lip rather than a flat box.
cowl=[(-.172,-.149,.269),(-.15354,-.17170,.2763),(-.10669,-.18725,.2793),(-.06274,-.19453,.2813),(.00073,-.19842,.2827),(.06470,-.19454,.2817),(.10815,-.18725,.2798),(.15599,-.17121,.2768),(.172,-.149,.269),(.172,-.114,.267),(-.172,-.114,.267)]
cowl.append((0,-.158,.274));pad=mesh('Cabin | fitted cowl pad',cowl,[(11,i,(i+1)%11) for i in range(11)],interior,True);md=pad.modifiers.new('Cowl thickness','SOLIDIFY');md.thickness=.002
box('Cabin | console',(0,-.02,.184),(.042,.235,.04),interior,.005)
for side in [-1,1]:
 x=side*.083
 box('Seat | cushion '+str(side),(x,.018,.194),(.111,.118,.037),seatmat,.01)
 back=box('Seat | back '+str(side),(x,.070,.25),(.108,.032,.113),seatmat,.009);back.rotation_euler.x=math.radians(9)
 box('Seat | headrest '+str(side),(x,.08,.314),(.068,.028,.038),seatmat,.008)
 for dx in [-.04,.04]:box('Seat | rail',(x+dx,.02,.170),(.009,.13,.014),metal,.001)
 for dx in [-.043,.043]:box('Seat | bolster',(x+dx,.00,.214),(.018,.10,.022),seatmat,.006)
 card=box('Cabin | door card '+str(side),(side*.172,-.016,.225),(.020,.285,.10),interior,.004)
 box('Cabin | armrest '+str(side),(side*.153,-.006,.235),(.018,.09,.018),seatmat,.003)
 box('Cabin | door pull '+str(side),(side*.148,-.045,.25),(.009,.035,.012),metal,.002)
 # Dashboard side vents with recessed dark slots.
 for dy in range(4):box('Dash | vent '+str(side),(side*.137,-.110,.252+dy*.0025),(.024,.0015,.001),rubber,0)
rod('Controls | steering column',(.083,-.14,.225),(.083,-.085,.270),.007,interior)
# Steering wheel in a plane normal to a gently inclined column.
centre=Vector((.083,-.083,.272));u=Vector((1,0,0));v=Vector((0,.20,.98)).normalized();normal=u.cross(v);R=.037;N=36;K=8
pts=[list(centre+(R+.004*math.cos(j*2*math.pi/K))*(math.cos(i*2*math.pi/N)*u+math.sin(i*2*math.pi/N)*v)+normal*.004*math.sin(j*2*math.pi/K)) for i in range(N) for j in range(K)]
mesh('Controls | steering rim',pts,[(i*K+j,((i+1)%N)*K+j,((i+1)%N)*K+(j+1)%K,i*K+(j+1)%K) for i in range(N) for j in range(K)],rubber,True)
for angle in [0,math.pi,math.pi*1.5]:rod('Controls | steering spoke',centre,centre+R*(math.cos(angle)*u+math.sin(angle)*v),.003,metal,8)
rod('Controls | steering hub',centre-normal*.006,centre+normal*.006,.009,interior)
for x,r in [(.065,.010),(.092,.010),(.043,.006),(.113,.006)]:
 rod('Dash | instrument bezel',(x,-.111,.266),(x,-.105,.266),r,metal,20)
 rod('Dash | instrument face',(x,-.1048,.266),(x,-.104,.266),r*.88,rubber,20)
 rod('Dash | needle',(x,-.1035,.266),(x+r*.5,-.1035,.266+r*.4),.0006,dial,6)
rod('Controls | gear lever',(0,-.016,.204),(0,-.02,.232),.002,metal)
box('Controls | gear knob',(0,-.02,.233),(.01,.01,.01),interior,.003)
for x in [.061,.083,.105]:box('Controls | pedal',(x,-.153,.182),(.014,.023,.005),rubber,.002)
# Fair tyre surfaces around their own pivots; retain the UV-mapped central rim geometry.
inventory=json.loads((SRC/'separation-report.json').read_text())['parts'];report['wheels']={}
for i,tag in enumerate(['FL','FR','RL','RR'],1):
 ob=bpy.data.objects[f'Source component {i:02d}'];bb=inventory[i]['bounds'];c=Vector([(bb[0][j]+bb[1][j])/2 for j in range(3)]);radius=(bb[1][2]-bb[0][2])/2;width=bb[1][0]-bb[0][0]
 ob.name='Wheel_'+tag;world=ob.matrix_world.copy();inverse=world.inverted();changed=0
 for vtx in ob.data.vertices:
  p=world@vtx.co;q=p-c;r=math.hypot(q.y,q.z)
  if r<radius*.70:continue
  axial=abs(q.x)/(width/2);target=radius*(1-.065*min(1,axial)**4)
  # Keep rim/tyre interface stable, progressively circularize the shoulder and tread.
  strength=min(1,max(0,(r/radius-.70)/.17));nr=r*(1-strength)+target*strength
  q.y*=nr/r;q.z*=nr/r;vtx.co=inverse@(c+q);changed+=1
 ob.data.update()
 # Imported normals describe the lumpy source tyre, not its repaired shape.
 # Replace only tyre corner normals with the fitted rotational surface normals.
 normals=[nn.vector.copy() for nn in ob.data.corner_normals]
 for loop in ob.data.loops:
  q=world@ob.data.vertices[loop.vertex_index].co-c;r=math.hypot(q.y,q.z)
  if r<radius*.73:continue
  axial=min(1,abs(q.x)/(width/2));n=Vector(((1 if q.x>=0 else -1)*axial**4*3,q.y/r,q.z/r)).normalized()
  normals[loop.index]=(world.to_3x3().transposed()@n).normalized()
 ob.data.normals_split_custom_set(normals)
 ob['bone']='Wheel_'+tag;ob['pivot']=list(c);report['wheels'][tag]={'centre':list(c),'radius':radius,'width':width,'faired_vertices':changed}
# Keep all source texture and UV data. Source wheelhouse backs and undertray remain retained.
report['body_vertices_changed']=0
for ob in sourcecol.objects:ob['bone']=ob.get('bone','Root')
for ob in col.objects:ob['bone']='Root'
# UVs for small solid-material additions; preserved source atlas is never repacked.
for ob in col.objects:
 if ob.type!='MESH':continue
 uv=ob.data.uv_layers.new(name='UVMap')
 for p in ob.data.polygons:
  for li in p.loop_indices:
   co=ob.data.vertices[ob.data.loops[li].vertex_index].co;uv.data[li].uv=(co.x+.5,co.y+.5)
sc.unit_settings.system='METRIC';sc.unit_settings.scale_length=1
bpy.context.view_layer.update()
for ob in list(sourcecol.objects)+list(col.objects):
 ob.matrix_world=Matrix.Scale(4.5,4)@ob.matrix_world
 if 'pivot' in ob:ob['pivot']=[x*4.5 for x in ob['pivot']]
# Texture extraction for engine import.
img=next(i for i in bpy.data.images if i.name.startswith('tripo_rgb'));img.filepath_raw=str(OUT/'T_F288_Source.png');img.file_format='PNG';img.save()
report['texture']={'file':str(OUT/'T_F288_Source.png'),'resolution':list(img.size),'note':'Original packed Tripo colour atlas; original UVs retained.'}
sc.render.engine='CYCLES';sc.cycles.samples=32;sc.cycles.use_denoising=True
sc.world.use_nodes=True;bg=sc.world.node_tree.nodes.get('Background');bg.inputs[0].default_value=(.22,.25,.30,1);bg.inputs[1].default_value=.45
for name,pos,power,size in [('Key',(4,-6,8),1700,6),('Fill',(-4,-1,4),1000,5),('Rim',(0,5,7),1500,5)]:
 data=bpy.data.lights.new(name,'AREA');data.energy=power;data.size=size;obj=bpy.data.objects.new(name,data);sc.collection.objects.link(obj);obj.location=pos;obj.rotation_euler=(Vector((0,0,.8))-obj.location).to_track_quat('-Z','Y').to_euler()
sc.render.resolution_x=1440;sc.render.resolution_y=960;sc.render.resolution_percentage=100
cam=sc.camera;cam.data.type='PERSP';cam.data.lens=48
def view(name,pos,target):
 cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
cam.location=(6,-8,4);cam.rotation_euler=(Vector((0,0,.8))-cam.location).to_track_quat('-Z','Y').to_euler()
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   space=area.spaces.active;space.region_3d.view_location=(0,0,.8);space.region_3d.view_distance=6.8;space.region_3d.view_rotation=cam.rotation_euler.to_quaternion();space.shading.color_type='TEXTURE';space.overlay.show_extras=False
(OUT/'build-report.json').write_text(json.dumps(report,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Ferrari288_GameReady.blend'))
view('front-quarter',(6,-8,4),(0,0,.8));view('rear-quarter',(-6,8,3.6),(0,0,.8))
cam.data.lens=20;view('cockpit',(.083*4.5,.01*4.5,.317*4.5),(.083*4.5,-2,.9))
print('BUILD_COMPLETE',json.dumps(report))
