"""Authored front-left wing surface study. No remesh, shrinkwrap or donor faces.

Donor is a measurement reference only. The rest of the rejected car stays hidden.
Units in the specification are normalized donor units; output is metres (x4.5).
"""
import bpy,bmesh,json,math,hashlib
from pathlib import Path
from math import sin,cos,pi,sqrt
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path('C:/GrandTour/Art/Export/VehicleTools')
OUT=ROOT/'porsche-wing-study-v01';OUT.mkdir(exist_ok=True)
manifest=OUT/'delivery-manifest.json'
if manifest.exists():
 previous=json.loads(manifest.read_text());saved=OUT/'Porsche_FL_Wing_Study.blend'
 if saved.exists() and hashlib.sha256(saved.read_bytes()).hexdigest()!=previous['blend_sha256']:
  raise RuntimeError('The delivered wing study has been edited. Preserve it and create a new revision.')
S=4.5;YC=-.29126;ZC=.085205;RY=.1055;RZ=.0995
SOURCE=ROOT/'porsche-working-v01/Porsche_Assembly.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));sc=bpy.context.scene
for o in sc.objects:
 if o.type not in {'CAMERA','LIGHT'}:o.hide_render=True;o.hide_set(True)
col=bpy.data.collections.new('NEW - authored left front wing');sc.collection.children.link(col)
guides=bpy.data.collections.new('INTERFACES - adjacent panel samples');sc.collection.children.link(guides)
refcol=bpy.data.collections.new('REFERENCE - isolated donor wing');sc.collection.children.link(refcol)
wheel=[]
for o in sc.objects:
 if o.name.startswith('Wheel_FL'):
  o.hide_render=False;o.hide_set(False)
  if o.type=='MESH':wheel.append(o)
def material(n,c,rough=.44):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,1);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*c,1);p.inputs['Roughness'].default_value=rough;return m
clay=material('Wing - neutral clay',(.48,.53,.55));dark=material('Wheelhouse - dark clay',(.07,.08,.09));guide=material('Interface - neutral darker clay',(.24,.28,.3));wiremat=material('Topology lines',(.018,.023,.027))
def create(name,vs,fs,mat,collection=col):
 me=bpy.data.meshes.new(name);me.from_pydata([tuple(Vector(p)*S) for p in vs],[],fs);me.update();o=bpy.data.objects.new(name,me);collection.objects.link(o);me.materials.append(mat)
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 for p in me.polygons:p.use_smooth=True
 return o
def active(o):
 for a in bpy.context.selected_objects:a.select_set(False)
 o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
def lerp(a,b,t):return a*(1-t)+b*t
def smooth(t):return t*t*(3-2*t)
# Measured sections: y, bonnet lip, inner brow, crest, outer shoulder.
# These are explicit editable observations, not nearest-point projections.
sections=[[-.419,.156,.155,.155,.140],[-.410,.171,.174,.187,.170],[-.400,.176,.190,.206,.181],[-.390,.184,.199,.212,.189],[-.370,.190,.203,.215,.199],[-.350,.195,.207,.217,.208],[-.330,.202,.212,.220,.212],[-.300,.212,.216,.223,.216],[-.270,.219,.220,.225,.218],[-.240,.225,.224,.227,.219],[-.210,.229,.227,.229,.219],[-.180,.233,.231,.230,.217],[-.155,.235,.234,.231,.215]]
def hermite(values,x):
 # Shape-preserving PCHIP slopes avoid invented humps between observed stations.
 xs=[r[0] for r in values];ys=[r[1] for r in values];n=len(xs)
 if x<=xs[0]:return ys[0]
 if x>=xs[-1]:return ys[-1]
 h=[xs[k+1]-xs[k] for k in range(n-1)];d=[(ys[k+1]-ys[k])/h[k] for k in range(n-1)];m=[d[0]]+[0.]*(n-2)+[d[-1]]
 for k in range(1,n-1):
  if d[k-1]*d[k]>0:
   w1=2*h[k]+h[k-1];w2=h[k]+2*h[k-1];m[k]=(w1+w2)/(w1/d[k-1]+w2/d[k])
 k=next(i for i in range(n-1) if xs[i]<=x<=xs[i+1]);t=(x-xs[k])/h[k]
 return (2*t**3-3*t*t+1)*ys[k]+(t**3-2*t*t+t)*h[k]*m[k]+(-2*t**3+3*t*t)*ys[k+1]+(t**3-t*t)*h[k]*m[k+1]
def height(y,k):return hermite([(r[0],r[k]) for r in sections],y)
def catmull(points,steps=4):
 # Coordinate-wise shape-preserving interpolation. Unconstrained Catmull
 # tangents overshoot the tight arch roll and can fold its inner skin.
 curves=[[(i,p[k]) for i,p in enumerate(points)] for k in range(3)]
 return [Vector(tuple(hermite(curves[k],j/steps) for k in range(3))) for j in range((len(points)-1)*steps+1)]
# Angular sampling gives an orderly circular opening without long skinny triangles.
theta0=math.asin((.091-ZC)/RZ)
angles=[theta0+(pi-2*theta0)*i/28 for i in range(29)]
arc=[(YC-RY*cos(a),ZC+RZ*sin(a),a) for a in angles]
ys=[-.419,-.414]+[q[0] for q in arc]+[-.170,-.162,-.155]
ys=sorted(set(ys));rows=[];outer=[];arch_rows=[]
for y in ys:
 arc_i=min(range(len(arc)),key=lambda j:abs(arc[j][0]-y));is_arc=abs(arc[arc_i][0]-y)<1e-7
 if is_arc:
  z=arc[arc_i][1];a=arc[arc_i][2];xo=.214+.0085*sin(a);arch_rows.append(len(rows));ny=-cos(a);nz=sin(a)
 elif y<arc[0][0]:
  ny=0.;nz=1.
  z=.091;xo=lerp(.193,.214,(y+.419)/(arc[0][0]+.419))
 else:
  u=(y-arc[-1][0])/(-.155-arc[-1][0]);ny=0.;nz=1.
  z=.091;xo=lerp(.214,.198,u)
 ny=0.;nz=1.
 zshould=max(height(y,4),z+.020)
 # Broad bonnet valley -> proud wing brow -> shoulder -> soft arch lip.
 controls=[(.125,y,height(y,1)),(.14,y,height(y,2)),(.16,y,height(y,3)),(.176,y,height(y,3)-.001),(.192,y,zshould),(lerp(.192,xo-.003,.48),y+.005*ny,lerp(zshould,z+.014*nz,.55)),(xo-.003,y+.012*ny,z+.012*nz),(xo,y+.006*ny,z+.006*nz),(xo-.0005,y+.002*ny,z+.002*nz),(xo-.003,y,z)]
 row=catmull(controls,4);rows.append(row);outer.append((xo-.003,y,z))
vs=[tuple(p) for row in rows for p in row];N=len(rows[0]);M=len(rows)
fs=[(i*N+j,(i+1)*N+j,(i+1)*N+j+1,i*N+j+1) for i in range(M-1) for j in range(N-1)]
wing=create('Porsche_FL_Wing_Authored',vs,fs,clay)
wing['method']='Authored measured sections and shared rounded arch profile; no donor triangles'
wing['scope']='Single wing component proof; not installed in the rejected whole-car body'
# Explicit inner returns use the exact outer-edge coordinates; no independent fitted strip.
rv=[];rf=[];depths=[0,.002,.005,.010,.017]
for x,y,z in outer:
 for d in depths:rv.append((x-d,y,z+(.0006 if d>0 else 0)))
for i in range(M-1):
 for j in range(len(depths)-1):a=i*len(depths)+j;rf.append((a,a+1,a+1+len(depths),a+len(depths)))
ret=create('Porsche_FL_Arch_Return',rv,rf,clay)
# Backed wheel tub spans the opening to an inboard wall, with the sill as its bottom.
# The first band shares the return's last row exactly. The wall is an inferred hidden surface.
lv=[];lf=[]
for i in arch_rows:
 x,y,z=outer[i]
 for d in [0,.025,.05]:lv.append((x-depths[-1]-d,y,z+.0006))
for i in range(len(arch_rows)-1):
 for j in range(2):a=i*3+j;lf.append((a,a+3,a+4,a+1))
# Closed inner wall uses radial bands to a floor line, staying safely inboard of the tyre.
wallstart=len(lv)
for i in arch_rows:
 x,y,z=outer[i];lv.extend([(x-depths[-1]-.05,y,z+.0006),(.132,y,.070)])
for i in range(len(arch_rows)-1):a=wallstart+i*2;lf.append((a,a+2,a+3,a+1))
liner=create('Porsche_FL_Wheelhouse',lv,lf,dark)
bm=bmesh.new();bm.from_mesh(liner.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(liner.data);bm.free()
# Merge wing + return into one connected shell: the mating row is literally shared.
active(wing);ret.select_set(True);bpy.ops.object.join();wing=bpy.context.object
bm=bmesh.new();bm.from_mesh(wing.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(wing.data);bm.free()
wing.data.materials.clear();wing.data.materials.append(clay)
for p in wing.data.polygons:p.material_index=0
# Add controlled physical sheet thickness after the primary surface has been authored.
mod=wing.modifiers.new('Sheet thickness 1 mm','SOLIDIFY');mod.thickness=.001;mod.offset=-1;mod.use_even_offset=False;mod.thickness_clamp=.5;mod.use_thickness_angle_clamp=True
active(wing);bpy.ops.object.modifier_apply(modifier=mod.name)
mod=liner.modifiers.new('Wheel tub thickness','SOLIDIFY');mod.thickness=.002;mod.offset=-1
active(liner);bpy.ops.object.modifier_apply(modifier=mod.name)
wing.data.set_sharp_from_angle(angle=.75);liner.data.set_sharp_from_angle(angle=.75)
# Neighbour strips demonstrate fixed interfaces. They are guides, not a finished bonnet/door.
gv=[];gf=[]
for row in rows:
 p=row[0];gv.extend([tuple(p),(.110,p.y,p.z+.0012)])
for i in range(M-1):a=i*2;gf.append((a,a+2,a+3,a+1))
hood=create('Bonnet_interface_SAMPLE',gv,gf,guide,guides)
gv=[];gf=[]
for p in rows[-1]:gv.extend([tuple(p),(p.x,p.y+.012,p.z)])
for j in range(N-1):a=j*2;gf.append((a,a+2,a+3,a+1))
rear=create('Door_interface_SAMPLE',gv,gf,guide,guides)
# Isolate the donor region for matched before/after comparisons, not as a backing mesh.
donor=bpy.data.objects['Body_and_cabin'];ref=donor.copy();ref.data=donor.data.copy();refcol.objects.link(ref);ref.name='Donor wing - comparison only'
bm=bmesh.new();bm.from_mesh(ref.data)
for point,normal in [((.125*S,0,0),(1,0,0)),((0,-.419*S,0),(0,1,0)),((0,-.155*S,0),(0,-1,0)),((0,0,.09*S),(0,0,1)),((0,0,.245*S),(0,0,-1))]:
 bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=point,plane_no=normal,dist=1e-7,clear_inner=True)
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(ref.data);bm.free();ref.data.materials.clear();ref.data.materials.append(clay)
for p in ref.data.polygons:p.material_index=0;p.use_smooth=True
ref.hide_set(True);ref.hide_render=True
# Quantitative checks cover construction, not stylistic approval or vehicle motion.
def bvh(o):
 o.data.calc_loop_triangles();return BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[list(t.vertices) for t in o.data.loop_triangles],all_triangles=True)
wt=bvh(wing);lt=bvh(liner);report={'scope':'Front-left wing component study only','all_primary_surface_faces_quads':all(len(f)==4 for f in fs),'outer_surface_quads':len(fs),'wheel_collisions':{}}
def edge_samples(points):
 return [Vector(a).lerp(Vector(b),t)*S for a,b in zip(points,points[1:]) for t in [0,.25,.5,.75,1]]
def edge_error(points,tree1,tree2):
 return max(max(tree1.find_nearest(p)[3],tree2.find_nearest(p)[3]) for p in edge_samples(points))
interface=[(outer[i][0]-depths[-1],outer[i][1],outer[i][2]+.0006) for i in arch_rows]
report['arch_return_to_tub_sampled_error_m']=edge_error(interface,wt,lt)
report['bonnet_sample_interface_error_m']=edge_error([tuple(row[0]) for row in rows],wt,bvh(hood))
report['rear_sample_interface_error_m']=edge_error([tuple(p) for p in rows[-1]],wt,bvh(rear))
# A 10 mm displaced tub must fail the same geometric seam check.
shift=Vector((-.010,0,0));liner.data.calc_loop_triangles();fault=BVHTree.FromPolygons([v.co+shift for v in liner.data.vertices],[list(t.vertices) for t in liner.data.loop_triangles],all_triangles=True)
report['deliberate_10mm_tub_displacement_error_m']=edge_error(interface,wt,fault)
assert report['deliberate_10mm_tub_displacement_error_m']>.005
assert report['arch_return_to_tub_sampled_error_m']<1e-5
assert report['bonnet_sample_interface_error_m']<1e-5 and report['rear_sample_interface_error_m']<1e-5
for o in wheel:
 if o.name.endswith(('_Tyre','_Tread','_Rim_barrel')):report['wheel_collisions'][o.name]={'wing_tri_pairs':len(wt.overlap(bvh(o))),'liner_tri_pairs':len(lt.overlap(bvh(o)))}
assert all(v==0 for pair in report['wheel_collisions'].values() for v in pair.values())
for o in [wing,liner]:
 bm=bmesh.new();bm.from_mesh(o.data);report[o.name]={'vertices':len(bm.verts),'faces':len(bm.faces),'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'zero_area_faces':sum(f.calc_area()<1e-11 for f in bm.faces)};bm.free()
 assert report[o.name]['nonmanifold_edges']==0 and report[o.name]['zero_area_faces']==0
data=json.loads((ROOT/'porsche-source-v01/islands.json').read_text())[0];donorbvh=BVHTree.FromPolygons(data['verts'],data['polys']);distances=[donorbvh.find_nearest(Vector(p))[3]*S for p in vs];report['surface_to_donor_distance_m']={'mean':sum(distances)/len(distances),'p95':sorted(distances)[int(len(distances)*.95)],'max':max(distances),'note':'Deliberate fairing removes donor dents; nearest distance is not a silhouette proof'}
report['not_tested']=['Full-car integration','Opening doors','Steering/suspension travel','UV/LOD/collision/export/Unreal']
(OUT/'construction-report.json').write_text(json.dumps(report,indent=2))
spec={'source':str(SOURCE),'source_geometry':'Tripo used for broad section heights and wheel datum only; rejected body topology is not reused','units_scale':S,'wheel_centre':[.2,YC,ZC],'arch_y_radius':RY,'arch_z_radius':RZ,'sections':sections,'shared_edges':'Skin and lip merged; return and tub mating positions generated from outer[]','status':'Component review; not whole-car completion'}
(OUT/'wing-spec.json').write_text(json.dumps(spec,indent=2))
sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.light='STUDIO';sc.display.shading.studiolight_rotate_z=.35;sc.display.shading.color_type='MATERIAL';sc.display.shading.show_cavity=True;sc.display.shading.cavity_type='BOTH';sc.display.shading.show_shadows=True;sc.display.shading.background_type='WORLD';sc.world.color=(.14,.14,.14)
sc.render.resolution_x=1400;sc.render.resolution_y=1000;sc.render.resolution_percentage=100
cam=sc.camera;cam.data.type='ORTHO';cam.data.ortho_scale=2.10;target=Vector((.81,-1.26,.58))
def render(name,pos,tar=target):
 cam.location=pos;cam.rotation_euler=(Vector(tar)-cam.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
poses={'quarter':(3.2,-3,1.56),'side':(4,-1.26,.58),'front':(.81,-4,.58),'top':(.81,-1.26,4)}
for n,p in poses.items():render('after-'+n,p)
for o in [wing,liner,hood,rear]:o.hide_render=True
ref.hide_render=False
for n in ['quarter','side']:render('before-'+n,poses[n])
ref.hide_render=True
for o in [wing,liner,hood,rear]:o.hide_render=False
# Render actual quad edges as curves; no generated conceptual wireframe image.
cu=bpy.data.curves.new('Authored cage edges','CURVE');cu.dimensions='3D';cu.bevel_depth=.00055;cu.bevel_resolution=0
for e in wing.data.edges:
 a,b=[wing.data.vertices[i].co for i in e.vertices];spl=cu.splines.new('POLY');spl.points.add(1);spl.points[0].co=(*a,1);spl.points[1].co=(*b,1)
wo=bpy.data.objects.new('Topology overlay - hide for clay',cu);col.objects.link(wo);cu.materials.append(wiremat)
render('wireframe',poses['quarter']);wo.hide_render=True;wo.hide_set(True)
for o in wheel:o.hide_render=True
render('wheel-off',poses['quarter']);render('inside',(0,-1.4,.3),(.75,-1.3,.60))
for o in wheel:o.hide_render=False
cam.location=poses['quarter'];cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
for o in sc.objects:o.select_set(False)
wing.select_set(True);bpy.context.view_layer.objects.active=wing
for a in bpy.context.screen.areas:
 if a.type=='VIEW_3D':a.spaces.active.region_3d.view_location=target;a.spaces.active.region_3d.view_distance=2.2;a.spaces.active.shading.type='SOLID';a.spaces.active.overlay.show_extras=False
note=bpy.data.texts.new('READ ME - wing component proof');note.write('One authored front-left wing and arch. Primary surface built from explicit section curves, not cleaned donor triangles. Original rejected whole-car body remains hidden. Adjacent bonnet and door strips are interface samples only. Read construction-report.json for limits. No complete car or game-readiness claim.\n')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Porsche_FL_Wing_Study.blend'))
manifest.write_text(json.dumps({'status':'Isolated authored wing study - not a whole-car replacement','blend_sha256':hashlib.sha256((OUT/'Porsche_FL_Wing_Study.blend').read_bytes()).hexdigest(),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'body_rebuild_method':'Explicit measured cross-sections and angular arch stations; no remesh/shrinkwrap/donor faces','construction_report':'construction-report.json','pending':'User visual review, lamp/nose transition, full-car mating surfaces and remaining body panels'},indent=2))
print(json.dumps(report,indent=2),flush=True)
