"""Source-preserving Ferrari safari assembly. Local glazing replacement, not a generic body rebuild."""
import bpy,bmesh,math,json,hashlib,sys,ast
from pathlib import Path
from mathutils import Vector,Matrix
import numpy as np
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools/vendor_geometry')
from shapely.geometry import Polygon,Point
from shapely.ops import triangulate,unary_union
P=Path('C:/GrandTour/Art/Export/VehicleTools/ferrari288-source-v01')
OUT=P.parent/'ferrari288-prepared-v03';OUT.mkdir(exist_ok=True)
S=4.5
A=json.loads((P/'islands.json').read_text());G=json.loads((P/'glass-selections.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene;sc.unit_settings.system='METRIC'
cols={}
for n in ['01 Body','02 Glass','03 Road wheels','04 Interior','05 Front equipment','06 Roof rack and cargo','07 Side equipment','08 Underbody','09 Small fittings','90 Source reference','99 Review']:
 c=bpy.data.collections.new(n);sc.collection.children.link(c);cols[n]=c
M={}
palette={'Paint':(.75,.685,.51,1),'Red':(.46,.068,.037,1),'Rubber':(.027,.033,.035,1),'Metal':(.095,.115,.119,1),'Wheel':(.34,.225,.11,1),'Glass':(.30,.45,.50,1),'Lens':(.80,.84,.79,1),'Case':(.38,.265,.145,1),'Board':(.54,.30,.07,1),'Amber':(.95,.23,.012,1),'Lamp red':(.65,.009,.005,1),'Seat':(.13,.024,.020,1),'Carpet':(.027,.023,.022,1),'Chrome':(.49,.54,.54,1)}
for n,c in palette.items():
 m=bpy.data.materials.new('Ferrari safari | '+n);m.diffuse_color=c;m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=c;p.inputs['Roughness'].default_value=.38
 if n in ['Metal','Wheel','Chrome']:p.inputs['Metallic'].default_value=.7
 if n in ['Rubber','Seat','Carpet','Case']:p.inputs['Roughness'].default_value=.76
 if n=='Glass':p.inputs['Transmission Weight'].default_value=1;p.inputs['Roughness'].default_value=.075;p.inputs['IOR'].default_value=1.46
 if n in ['Amber','Lamp red','Lens']:p.inputs['Coat Weight'].default_value=.5;p.inputs['Roughness'].default_value=.23
 M[n]=m
root=bpy.data.objects.new('FERRARI 288 GTO | Safari assembly',None);cols['01 Body'].objects.link(root)
root['scale_note']='4.5m working overall length; preserves normalized source proportions, not a factory measurement.'
objects=[]
# Reuse only neutral construction helpers; no Prado selectors or shapes.
tree=ast.parse(Path('C:/GrandTour/Art/VehicleTools/prepare_prado_v01.py').read_text())
for node in tree.body:
 if isinstance(node,ast.FunctionDef) and node.name in ['mesh','subset','at_origin','revolve']:
  exec(compile(ast.Module(body=[node],type_ignores=[]),'shared vehicle helper','exec'))
def box(n,c,d,mat,col='04 Interior',bevel=.0015):
 x,y,z=c;a,b,k=[t/2 for t in d]
 v=[(x+u*a,y+w*b,z+t*k) for u,w,t in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
 o=mesh(n,v,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],col,mat)
 if bevel:
  mod=o.modifiers.new('Soft manufactured edges','BEVEL');mod.width=bevel*S;mod.segments=3
 return o
def rod(n,a,b,r,mat,col='04 Interior',segments=16):
 a,b=Vector(a),Vector(b);axis=(b-a).normalized();u=axis.cross(Vector((0,0,1)))
 if u.length<.1:u=axis.cross(Vector((0,1,0)))
 u.normalize();v=axis.cross(u)
 return revolve(n,[(0,0),(0,r),((b-a).length,r),((b-a).length,0)],col,mat,lambda p:a+axis*p[0]+u*p[1]+v*p[2],segments)
def curve(n,pts,r,mat,col='02 Glass',closed=False):
 cu=bpy.data.curves.new(n,'CURVE');cu.dimensions='3D';cu.resolution_u=1;cu.bevel_depth=r*S;cu.bevel_resolution=2
 sp=cu.splines.new('POLY');sp.points.add(len(pts)-1)
 for p,co in zip(sp.points,pts):p.co=(*[x*S for x in co],1)
 sp.use_cyclic_u=closed;ob=bpy.data.objects.new(n,cu);cols[col].objects.link(ob);ob.parent=root;cu.materials.append(M[mat]);ob.color=M[mat].diffuse_color;return ob
# Side apertures follow measured source frame vertices, not generic rectangles.
polys={
 'Door':[(-.038330,.243652),(.023193,.248047),(.095459,.252930),(.104248,.272461),(.115479,.297852),(.117920,.316895),(.059326,.318848),(.002197,.317383),(-.009033,.311523),(-.016846,.293457),(-.028564,.267090)],
 'Vent':[(-.102783,.241700),(-.047119,.242676),(-.035400,.267090),(-.023682,.293945),(-.015869,.312012),(-.030518,.317383),(-.057373,.298828),(-.094482,.272461)],
 'Quarter':[(.131104,.2548),(.184,.259),(.207275,.270508),(.196,.286),(.161,.311035),(.131104,.312500)]}
holes={n:Polygon(p).buffer(.00035,join_style=2) for n,p in polys.items()}
mask=unary_union(list(holes.values()))
src=A[0];verts=[Vector(p) for p in src['verts']];frontids=set(G['Windscreen']['faces'])
adj={}
for a,b in G['Windscreen']['edges']:adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
unseen=set(adj);loops=[]
while unseen:
 loop=[unseen.pop()];prev=None
 while True:
  nxt=next(x for x in adj[loop[-1]] if x!=prev)
  if nxt==loop[0]:break
  prev=loop[-1];loop.append(nxt);unseen.discard(nxt)
 loops.append(loop)
loop=max(loops,key=lambda l:Polygon([(verts[i].x,verts[i].y) for i in l]).area)
# Discard erroneous inward spikes from the source pane boundary, while preserving
# the bowed lower and upper aperture edges. These are measured source landmarks.
border=[Vector(p) for p in [(-.18286,-.15210,.23389),(-.13257,-.17017,.23877),(-.10669,-.17554,.24072),(-.05786,-.18140,.24170),(0,-.18433,.24268),(.04614,-.18188,.24219),(.10181,-.17603,.24072),(.13257,-.17017,.23877),(.18188,-.15210,.23389),(.17310,-.12720,.25098),(.16821,-.09448,.27246),(.15063,-.05737,.29883),(.13647,-.03052,.31738),(.13306,-.02710,.31982),(.12769,-.02515,.32178),(.11255,-.02612,.32422),(.09155,-.02954,.32568),(.04614,-.03442,.32764),(0,-.03589,.32812),(-.04614,-.03442,.32764),(-.09155,-.02954,.32568),(-.11255,-.02612,.32422),(-.12817,-.02515,.32178),(-.13306,-.02710,.31982),(-.13696,-.03052,.31738),(-.15063,-.05737,.29883),(-.16821,-.09448,.27246),(-.17310,-.12720,.25098)]]
frontoutline=Polygon([(p.x,p.y) for p in border])
newv=[];newf=[];changed=[];removed=[]
for i,face in enumerate(src['polys']):
 if i in frontids:removed.append(i);continue
 vv=[verts[j] for j in face];c=sum(vv,Vector())/len(vv)
 if all(abs(v.x)<.165 and -.165<v.y<.175 and .124<v.z<.294 for v in vv):removed.append(i);continue
 # Cut every source layer at the windshield, including inward-folded slivers.
 if -.191<c.y<-.018 and .230<c.z<.339:
  projected=Polygon([(v.x,v.y) for v in vv])
  if projected.is_valid and projected.area>1e-12 and projected.intersects(frontoutline):
   remaining=projected.difference(frontoutline)
   if remaining.area<projected.area-1e-12:
    changed.append(i)
    if remaining.area<1e-12:removed.append(i);continue
    basis=np.array([[v.x,v.y,1] for v in vv]);fc=np.linalg.lstsq(basis,np.array([v.z for v in vv]),rcond=None)[0]
    parts=list(remaining.geoms) if hasattr(remaining,'geoms') else [remaining]
    for part in parts:
     if part.geom_type!='Polygon':continue
     for tr in triangulate(part):
      if not part.covers(tr.representative_point()):continue
      k=len(newv);newv.extend((x,y,float(fc@[x,y,1])) for x,y in list(tr.exterior.coords)[:3]);newf.append((k,k+1,k+2))
    continue
 # Limit cuts to lateral cabin faces. All layers of folded pane geometry are removed.
 relevant=abs(c.x)>.070 and -.13<c.y<.23 and .231<c.z<.324 and all(v.x*c.x>0 for v in vv)
 projected=Polygon([(v.y,v.z) for v in vv]) if relevant else None
 if relevant and projected.is_valid and projected.area>1e-12 and projected.intersects(mask):
  remaining=projected.difference(mask)
  if remaining.area<projected.area-1e-12:
   changed.append(i)
   if remaining.area<1e-12:removed.append(i);continue
   basis=np.array([[v.y,v.z,1] for v in vv]);coef=np.linalg.lstsq(basis,np.array([v.x for v in vv]),rcond=None)[0]
   parts=list(remaining.geoms) if hasattr(remaining,'geoms') else [remaining]
   for part in parts:
    if part.geom_type!='Polygon':continue
    for tr in triangulate(part):
     if not part.covers(tr.representative_point()):continue
     k=len(newv);newv.extend((float(coef@[y,z,1]),y,z) for y,z in list(tr.exterior.coords)[:3]);newf.append((k,k+1,k+2))
   continue
 k=len(newv);newv.extend(vv);newf.append(tuple(range(k,k+len(vv))))
body=mesh('Body | source silhouette, repaired apertures',newv,newf,'01 Body','Paint',weighted=False)
body['source_shape']='Source triangles retained except local glazing cuts; no global remesh or scale deformation.'
# Crisp livery boundaries use actual topology cuts, not triangle-centre colour stepping.
bm=bmesh.new();bm.from_mesh(body.data)
for z in [.098,.166,.172,.175]:
 bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-8,plane_co=(0,0,z*S),plane_no=(0,0,1),clear_inner=False,clear_outer=False)
for m in ['Red','Rubber','Metal']:body.data.materials.append(M[m])
for f in bm.faces:
 c=f.calc_center_median()/S
 f.material_index=1 if .098<c.z<.166 or .172<c.z<.175 else 0
 if all(v.co.y/S>.470 and abs(v.co.x/S)<.190 and .190<v.co.z/S<.238 for v in f.verts):f.material_index=2
 if c.z<.096:f.material_index=2
 # Inner wheel tubs remain opaque and dark, not cream slabs visible behind tyres.
 if abs(c.x)<.165 and c.z<.22 and f.normal.z<.3 and (abs(c.y+.2666)<.107 or abs(c.y-.3066)<.107):f.material_index=2
for e in bm.edges:e.smooth=len(e.link_faces)==2 and e.calc_face_angle()<math.radians(48)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(body.data);bm.free()
mod=body.modifiers.new('Panel normal weighting','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=30
# Side panes: shallow fair surface, correctly seated behind a continuous seal.
def sx(y,z):return .3500-.647*z+.022*y
def sheet(n,poly,xf,col,mat):
 v=[];f=[]
 for tri in triangulate(poly):
  if not poly.covers(tri.representative_point()):continue
  k=len(v);v.extend(xf(y,z) for y,z in list(tri.exterior.coords)[:3]);f.append((k,k+1,k+2))
 o=mesh(n,v,f,col,mat,weighted=False);sol=o.modifiers.new('Physical thickness','SOLIDIFY');sol.thickness=.0005*S;sol.offset=-1;return o
for side in [-1,1]:
 for name,p in holes.items():
  label=('Left ' if side>0 else 'Right ')+name
  inner=p.buffer(-.0011,join_style=2)
  # Black seal lies over exact cut outline; flange backs the source frame lip.
  outer=p.buffer(.0011,join_style=2)
  sheet('Seal | '+label,outer.difference(inner),lambda y,z:(side*(sx(y,z)+.0003),y,z),'02 Glass','Rubber')
  sheet('Glass | '+label,inner,lambda y,z:(side*sx(y,z),y,z),'02 Glass','Glass')
# Windscreen boundary loop extracted from the actual removed patch.
center=sum(border,Vector())/len(border)
# Fit curved depth Z(X,Y); retain exact perimeter through black seating flange.
samples=border
coef=np.linalg.lstsq(np.array([[1,p.x,p.y,p.x*p.x,p.x*p.y,p.y*p.y] for p in samples]),np.array([p.z for p in samples]),rcond=None)[0]
def fair(p):return Vector((p.x,p.y,.2427+.578*(p.y+.18433)-.83*p.x*p.x))
rv=[];rf=[];N=len(border)
for t in [1,.977,.75,.50,.25,0]:
 for p in border:
  q=center+(p-center)*t;rv.append(p if t==1 else fair(q))
for j in range(5):
 for k in range(N):rf.append((j*N+k,j*N+(k+1)%N,(j+1)*N+(k+1)%N,(j+1)*N+k))
seal=mesh('Seal | windscreen shared boundary',rv[:2*N],rf[:N],'02 Glass','Rubber',weighted=False)
glass=mesh('Glass | curved windscreen',rv[N:],[[i-N for i in f] for f in rf[N:]],'02 Glass','Glass',weighted=False)
sol=glass.modifiers.new('Laminated glass thickness','SOLIDIFY');sol.thickness=.0008*S;sol.offset=-1
# Keep sound accessory parts and their source locations. Replace road wheels and exhaust tips.
skip={0,1,2,5,6,16,17,26,27,32,41}
for i,a in enumerate(A):
 if i in skip:continue
 lo,hi=Vector(a['min']),Vector(a['max']);c=(lo+hi)/2
 if i>70 and abs(c.x)>.18 and (abs(c.y+.2666)<.065 or abs(c.y-.3066)<.065) and c.z<.145:continue
 col='09 Small fittings';mat='Metal'
 if c.z>.331:col='06 Roof rack and cargo'
 elif c.z<.13:col='08 Underbody'
 elif c.y<-.44:col='05 Front equipment'
 elif abs(c.x)>.20:col='07 Side equipment'
 if i==10:mat='Case'
 if i in [3,4]:mat='Board'
 if i in [18,19]:mat='Rubber'
 if i in [21,22]:mat='Paint'
 if i in [20,23,24]:mat='Red'
 if i in [28,29,30,31]:mat='Paint'
 if i in [46,49,69,70]:mat='Amber'
 if i in [44,45,97,104]:mat='Rubber'
 o=mesh(f'Equipment | source {i:03d}',a['verts'],a['polys'],col,mat);o['source_component']=i
 # Covered round auxiliary lamps are reference-correct opaque cream covers.
 if i in [28,29,30,31]:o.name='Front auxiliary covered lamp | '+str(i)
# Five-spoke off-road wheels, retaining original wheel envelopes and pivots.
wheelreports=[]
for name,idx in [('Front left',1),('Front right',2),('Rear left',5),('Rear right',6)]:
 a=A[idx];lo,hi=Vector(a['min']),Vector(a['max']);c=(lo+hi)/2;h=(hi.x-lo.x)/2;r=(hi.z-lo.z)/2;sign=1 if c.x>0 else -1
 def xf(p):return c+Vector((sign*p[0],p[1],p[2]))
 pivot=bpy.data.objects.new('Wheel pivot | '+name,None);cols['03 Road wheels'].objects.link(pivot);pivot.parent=root;pivot.location=c*S;pivot.empty_display_size=.08
 start=len(objects)
 revolve(name+' | tyre',[(-.80*h,.51*r),(-h,.68*r),(-.96*h,.85*r),(-.72*h,.964*r),(0,.973*r),(.72*h,.964*r),(.96*h,.85*r),(h,.68*r),(.80*h,.51*r),(.68*h,.485*r),(-.68*h,.485*r)],'03 Road wheels','Rubber',xf,64)
 revolve(name+' | bronze rim',[(-.76*h,.49*r),(-.76*h,.535*r),(-.64*h,.52*r),(.68*h,.52*r),(.81*h,.548*r),(.85*h,.53*r),(.85*h,.485*r)],'03 Road wheels','Wheel',xf,64)
 revolve(name+' | ventilated brake rotor',[(-.08*h,0),(-.08*h,.46*r),(.12*h,.46*r),(.12*h,0)],'03 Road wheels','Metal',xf,48)
 revolve(name+' | centre hub',[(.26*h,0),(.26*h,.17*r),(.84*h,.17*r),(.89*h,.14*r),(.89*h,0)],'03 Road wheels','Wheel',xf,32)
 for k in range(5):
  t=2*math.pi*k/5;u=Vector((0,math.cos(t),math.sin(t)));v=Vector((0,-math.sin(t),math.cos(t)))
  vv=[]
  for x in [.40*h,.71*h]:
   for rr,w in [(.14*r,-.056*r),(.51*r,-.040*r),(.51*r,.040*r),(.14*r,.056*r)]:vv.append(xf(Vector((x,0,0))+u*rr+v*w))
  o=mesh(name+f' | spoke {k+1}',vv,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],'03 Road wheels','Wheel')
  b=o.modifiers.new('Spoke edge radius','BEVEL');b.width=.0008*S;b.segments=2
  off=u*(.125*r)
  revolve(name+f' | lug {k+1}',[(.85*h,0),(.85*h,.024*r),(.94*h,.024*r),(.94*h,0)],'03 Road wheels','Chrome',lambda p:xf(Vector(p)+off),6)
 vv=[];ff=[]
 for station in range(40):
  for row,(aa,bb) in enumerate([(-.76,-.30),(-.25,.25),(.30,.76)]):
   t=2*math.pi*(station+(row%2)*.5)/40;dt=math.pi/40*.70;pp=[(aa*h,t-dt*.7),(aa*h+.002,t-dt),(bb*h-.002,t-dt),(bb*h,t-dt*.7),(bb*h,t+dt*.7),(bb*h-.002,t+dt),(aa*h+.002,t+dt),(aa*h,t+dt*.7)];k=len(vv)
   for rr in [.952*r,r]:vv.extend(xf((x,rr*math.cos(th),rr*math.sin(th))) for x,th in pp)
   ff+=[tuple(k+j for j in reversed(range(8))),tuple(k+8+j for j in range(8))]+[(k+j,k+(j+1)%8,k+8+(j+1)%8,k+8+j) for j in range(8)]
 mesh(name+' | all-terrain tread',vv,ff,'03 Road wheels','Rubber',weighted=False)
 for o in objects[start:]:at_origin(o,c);o.parent=pivot;o.location=(0,0,0)
 wheelreports.append({'name':name,'center_raw':list(c),'radius_raw':r,'width_raw':2*h,'rim_outer_face_inside_tyre_mm':.15*h*S*1000})
# Rear lamp cassettes seat into the preserved flat source rear panel.
for side in [-1,1]:
 for j,x in enumerate([.110,.158]):
  c=Vector((side*x,.476,.213))
  xf=lambda p:c+Vector((p[1],p[0],p[2]))
  revolve(f'Rear lamp housing {side} {j}',[(-.001,0),(-.001,.018),(.002,.018),(.003,.016),(.003,0)],'09 Small fittings','Rubber',xf,48)
  revolve(f'Rear lamp lens {side} {j}',[(.002,0),(.002,.0153),(.004,.0153),(.005,.0135),(.005,0)],'09 Small fittings','Lamp red' if j==0 else 'Amber',xf,48)
 for dx in [-.012,.012]:
  c=Vector((side*.11+dx,.462,.117));xf=lambda p:c+Vector((p[1],p[0],p[2]))
  revolve('Rear exhaust | rolled metal tip',[(0,.008),(.032,.008),(.034,.007),(.034,.0058),(.029,.0058),(0,.0058)],'08 Underbody','Chrome',xf,32)
  revolve('Rear exhaust | recessed dark bore',[(.010,0),(.010,.0057),(.011,.0057),(.011,0)],'08 Underbody','Rubber',xf,24)
# Fitted enclosed two-seat cabin, under the original roof and behind the glass.
box('Cabin | full-width floor',(0,.015,.119),(.354,.385,.012),'Carpet',bevel=.002)
box('Cabin | rear bulkhead',(0,.167,.180),(.338,.015,.124),'Carpet',bevel=.004)
box('Cabin | dashboard',(0,-.116,.224),(.335,.068,.025),'Rubber',bevel=.006)
box('Cabin | lower firewall',(0,-.158,.170),(.335,.015,.097),'Carpet',bevel=.002)
box('Cabin | centre tunnel',(0,.005,.151),(.046,.280,.050),'Rubber',bevel=.006)
for side in [-1,1]:
 x=side*.091
 box('Seat | base',(x,.036,.151),(.117,.116,.038),'Seat',bevel=.010)
 ob=box('Seat | back',(x,.091,.208),(.111,.031,.119),'Seat',bevel=.010)
 box('Seat | head restraint',(x,.107,.280),(.064,.024,.034),'Seat',bevel=.008)
 for dx in [-.056,.056]:
  box('Seat | cushion bolster',(x+dx,.037,.169),(.015,.100,.026),'Rubber',bevel=.006)
 box('Seat | fixed pedestal',(x,.04,.130),(.085,.074,.013),'Metal',bevel=.001)
 box('Door card',(side*.173,.014,.183),(.009,.224,.103),'Carpet',bevel=.004)
 box('Door pull',(side*.163,.006,.214),(.012,.063,.012),'Metal',bevel=.003)
 curve('Seat | shoulder harness',[(x-.026,.107,.267),(x-.026,.068,.207),(x-.018,-.007,.163)],.0033,'Rubber','04 Interior')
 curve('Seat | shoulder harness',[(x+.026,.107,.267),(x+.026,.068,.207),(x+.018,-.007,.163)],.0033,'Rubber','04 Interior')
 # restrained door sill highlights
 box('Cabin | sill cover',(side*.179,.012,.137),(.012,.30,.020),'Metal',bevel=.003)
rod('Steering column',(.092,-.126,.199),(.092,-.064,.239),.006,'Rubber')
steer=Vector((.092,-.061,.241));axis=Vector((0,.90,.435)).normalized();u=Vector((1,0,0));v=axis.cross(u)
pts=[steer+.035*(u*math.cos(t*2*math.pi/64)+v*math.sin(t*2*math.pi/64)) for t in range(64)]
curve('Steering wheel | rim',pts,.0036,'Rubber','04 Interior',True)
for k in range(3):
 t=math.pi/2+k*2*math.pi/3;rod('Steering | spoke',steer,steer+.032*(u*math.cos(t)+v*math.sin(t)),.002,'Metal')
rod('Steering | hub',steer-axis*.004,steer+axis*.004,.009,'Metal')
for x,r in [(.068,.009),(.092,.012),(.118,.009)]:
 c=Vector((x,-.100,.243));xf=lambda p:c+Vector((p[1],p[0],p[2]))
 revolve('Dashboard | gauge bezel',[(0,0),(0,r),(.003,r),(.004,r*.90),(.004,0)],'04 Interior','Metal',xf,32)
 revolve('Dashboard | gauge dial',[(.004,0),(.004,r*.81),(.0045,r*.81),(.0045,0)],'04 Interior','Rubber',xf,32)
 rod('Dashboard | gauge needle',(x,-.095,.243),(x+r*.55,-.095,.243+r*.2),.0006,'Lens')
rod('Gear lever',(0,-.018,.174),(0,-.017,.207),.0021,'Chrome');box('Gear knob',(0,-.017,.209),(.012,.012,.012),'Rubber',bevel=.004)
for x in [.063,.083,.104]:box('Pedal',(x,-.126,.145),(.013,.012,.025),'Metal',bevel=.002)
# Hidden source object in matching coordinate system, available for comparisons.
ref=mesh('REFERENCE | untouched source body',src['verts'],src['polys'],'90 Source reference','Paint',cleanup=False,weighted=False)
cols['90 Source reference'].hide_render=True;cols['90 Source reference'].hide_viewport=True
for o in cols['90 Source reference'].objects:o.hide_set(True);o.hide_select=True
sc.world=bpy.data.worlds.new('Ferrari review studio');sc.world.use_nodes=True;sc.world.node_tree.nodes.get('Background').inputs[0].default_value=(.17,.20,.24,1);sc.world.node_tree.nodes.get('Background').inputs[1].default_value=.45
sc.render.engine='BLENDER_WORKBENCH';sc.render.resolution_x=1600;sc.render.resolution_y=1050;sc.render.resolution_percentage=100
sh=sc.display.shading;sh.light='STUDIO';sh.color_type='MATERIAL';sh.show_shadows=True;sh.show_cavity=True;sh.cavity_type='BOTH';sh.background_type='WORLD';sc.world.color=(.105,.12,.14)
bpy.ops.object.camera_add();cam=bpy.context.object;cam.name='REVIEW camera';sc.camera=cam;cam.data.type='ORTHO';cam.data.clip_end=200
for c in list(cam.users_collection):c.objects.unlink(cam)
cols['99 Review'].objects.link(cam)
def render(n,d,center=(0,0,.205),scale=1.17):
 c=Vector(center)*S;cam.location=c+Vector(d)*S;cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale*S;sc.render.filepath=str(OUT/(n+'.png'));bpy.ops.render.render(write_still=True)
for n,d in [('quarter',(2,-3,1.4)),('side',(3,0,0)),('front',(0,-3,0)),('rear',(0,3,0)),('rear-quarter',(-2,3,1)),('underside',(0,0,-3))]:render(n,d)
render('glazing-close',(2,-3,.9),(0,-.045,.27),.55)
render('cockpit',(1,-1,2),(0,.015,.19),.42)
report={'source_sha256':hashlib.sha256(Path('C:/Users/mille/Downloads/288gtotripo.glb').read_bytes()).hexdigest(),'working_scale':S,'source_body_faces':len(src['polys']),'local_glazing_faces_cut':changed,'removed_pane_faces':removed,'wheels':wheelreports,'status':'Blender review assembly. Not engine validated. No rig, LODs or collision yet. Body retains source topology outside local aperture repairs.'}
(OUT/'preparation-report.json').write_text(json.dumps(report,indent=2));bpy.data.texts.new('README - scope and source preservation').write(json.dumps(report,indent=2))
render('quarter',(2,-3,1.4))
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   area.spaces.active.shading.color_type='MATERIAL';area.spaces.active.overlay.show_overlays=False;rv=area.spaces.active.region_3d;rv.view_distance=6.5;rv.view_location=Vector((0,0,.21))*S;rv.view_rotation=cam.rotation_euler.to_quaternion()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Ferrari288_Safari.blend'))
print('SAVED',OUT)
