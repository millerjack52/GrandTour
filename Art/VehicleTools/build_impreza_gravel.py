"""Approved-concept-led Impreza. Authoring meshes, fitted components, inspection rig.
Fresh output only; this builder never opens or overwrites previous vehicle files.
"""
import bpy,bmesh,math,json,sys,argparse,shutil,hashlib
from pathlib import Path
from mathutils import Vector

p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--stage',default='shape');p.add_argument('--render',default='quarter,side,rear-quarter,front')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output)
if out.exists() and any(out.iterdir()):raise RuntimeError('Use a NEW EMPTY output directory; preserve all manual edits.')
out.mkdir(parents=True,exist_ok=True)
src=Path('C:/GrandTour/Art/References/Vehicles/Impreza2003');S=json.loads((src/'approved-shape-spec.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True);sc=bpy.context.scene;sc.unit_settings.system='METRIC'
def col(n):
 c=bpy.data.collections.new(n);sc.collection.children.link(c);return c
body=col('01 | Shared body surfaces');cab=col('02 | Cabin and glazing');wheelcol=col('03 | Road wheels');lin=col('04 | Wheelhouses and floor');trim=col('05 | Lamps and fitted trim');rally=col('06 | Rally equipment');inside=col('07 | Fitted interior');rigcol=col('08 | Controls');studio=col('90 | Studio');cams=col('91 | Review cameras')
groups={};root=None
def mat(n,c,rough=.6,metal=0):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,1);m.use_nodes=True;b=m.node_tree.nodes['Principled BSDF'];b.inputs['Base Color'].default_value=(*c,1);b.inputs['Roughness'].default_value=rough;b.inputs['Metallic'].default_value=metal;return m
paint=mat('Paint | matte rally blue',(.004,.035,.22),.60,.0);black=mat('Trim | charcoal',(.009,.012,.016),.75);rubber=mat('Tyre | soft charcoal',(.022,.024,.028),.85);gold=mat('Wheel | warm gold',(.50,.31,.074),.47,.40);silver=mat('Hardware | satin alloy',(.36,.39,.41),.45,.6);red=mat('Mudflap | vermilion',(.52,.046,.025),.76);cream=mat('Graphic | ivory',(.83,.75,.51),.7);white=mat('Lamp | pale warm lens',(.72,.75,.66),.35,.12);amber=mat('Lamp | amber',(.69,.26,.037),.43);redlens=mat('Lamp | red',(.43,.027,.018),.4);glass=mat('Glass | smoked blue grey',(.030,.043,.053),.38,.0)
paint.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value=.10
black.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value=.18
glass.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value=.40
glass.node_tree.nodes['Principled BSDF'].inputs['IOR'].default_value=1.10
glass.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value=.15
cloth=mat('Seats | dark cloth',(.055,.065,.079),.95);insert=mat('Seats | blue inserts',(.045,.105,.19),.95);floor_mat=mat('Interior | dark carpet',(.033,.037,.042),1);dial=mat('Recess | shadow',(.009,.013,.019),.8)

def interp(x,rows):
 if x<=rows[0][0]:return rows[0][1]
 for (aa,av),(bb,bv) in zip(rows,rows[1:]):
  if x<=bb:return av+(bv-av)*(x-aa)/(bb-aa)
 return rows[-1][1]
def width(y,z):return interp(z,S['body_width_z'])*interp(y,S['length_width'])
def belt(y):return interp(y,S['belt'])
def roof(y):return interp(y,S['roof'])
def cw(y,z):
 t=max(0,min(1,(z-belt(y))/(roof(y)-S['roof_edge_drop']-belt(y))))
 return width(y,belt(y))*(1-t)+S['roof_half_width']*t
def sidepos(y,z,s,off=0):return (s*(width(y,z)+off),y,z)
def cabpos(y,z,s,off=0):return (s*(cw(y,z)+off),y,z)
def tag(o,group):
 if group:groups.setdefault(group,[]).append(o.name);o['assembly_group']=group
 return o
def mesh(n,v,f,m,c=body,solid=0,smooth=False,group=None):
 me=bpy.data.meshes.new(n);me.from_pydata(v,[],f);me.update();o=bpy.data.objects.new(n,me);c.objects.link(o)
 if m:me.materials.append(m)
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 for face in me.polygons:face.use_smooth=smooth
 if solid:mod=o.modifiers.new('Closed sheet thickness','SOLIDIFY');mod.thickness=solid;mod.offset=-1
 return tag(o,group)
def bevel(o,w=.006,seg=2):
 mod=o.modifiers.new('Deliberate softened edges','BEVEL');mod.width=w;mod.segments=seg
 mod=o.modifiers.new('Face weighted normals','WEIGHTED_NORMAL');mod.keep_sharp=True;return o
def box(n,loc,dims,m,c=trim,b=.008,group=None):
 x,y,z=loc;dx,dy,dz=[d/2 for d in dims];v=[(x+i*dx,y+j*dy,z+k*dz) for i,j,k in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]]
 o=mesh(n,v,[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)],m,c,group=group)
 return bevel(o,b) if b else o
def curve(n,pts,r,m,c=trim,group=None):
 cu=bpy.data.curves.new(n,'CURVE');cu.dimensions='3D';cu.resolution_u=1;cu.bevel_depth=r;cu.bevel_resolution=2;sp=cu.splines.new('POLY');sp.points.add(len(pts)-1)
 for p,v in zip(sp.points,pts):p.co=(*v,1)
 o=bpy.data.objects.new(n,cu);c.objects.link(o);cu.materials.append(m);return tag(o,group)
def rod(n,a,b,r,m,c=trim,N=20,group=None):
 a=Vector(a);delta=Vector(b)-a;w=delta.normalized();u=w.cross(Vector((0,0,1)))
 if u.length<.01:u=w.cross(Vector((0,1,0)))
 u.normalize();v=w.cross(u);pts=[a+r*(u*math.cos(i*math.tau/N)+v*math.sin(i*math.tau/N)) for i in range(N)];vv=[tuple(p+t*delta) for t in [0,1] for p in pts]
 return mesh(n,vv,[tuple(range(N-1,-1,-1)),tuple(range(N,2*N))]+[(i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N)],m,c,smooth=True,group=group)
def apply(o):
 bpy.context.view_layer.objects.active=o
 for mod in list(o.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)
def prism(n,poly,axis,lo,hi,m=None,c=trim,group=None):
 def q(t,p):return (t,*p) if axis==0 else (p[0],t,p[1])
 N=len(poly);return mesh(n,[q(t,p) for t in [lo,hi] for p in poly],[tuple(range(N-1,-1,-1)),tuple(range(N,2*N))]+[(i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N)],m,c,group=group)
def cut(o,poly,axis,lo,hi):
 apply(o)
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 if bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
 bm.to_mesh(o.data);bm.free()
 temp=prism('CUTTER',poly,axis,lo,hi);mod=o.modifiers.new('Actual opening','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=temp;apply(o);bpy.data.objects.remove(temp,do_unlink=True)
def rr(x,z,w,h,r=.02,N=4):
 pts=[]
 for cx,cz,start in [(x+w/2-r,z+h/2-r,0),(x-w/2+r,z+h/2-r,90),(x-w/2+r,z-h/2+r,180),(x+w/2-r,z-h/2+r,270)]:
  for i in range(N+1):ang=math.radians(start+90*i/N);pts.append((cx+r*math.cos(ang),cz+r*math.sin(ang)))
 return pts
def clip(poly,fn):
 pts=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  da,db=fn(*a),fn(*b)
  if da>=-1e-9:pts.append(a)
  if (da>=0)!=(db>=0):t=da/(da-db);pts.append(tuple(x+(y-x)*t for x,y in zip(a,b)))
 return pts
def panel_grid(n,ys,zs,pos,limits,m,c=body,group=None,solid=.014):
 vv=[];ff=[]
 for ya,yb in zip(ys,ys[1:]):
  for za,zb in zip(zs,zs[1:]):
   poly=[(ya,za),(yb,za),(yb,zb),(ya,zb)]
   for fn in limits:
    if len(poly)<3:break
    poly=clip(poly,fn)
   if len(poly)<3:continue
   k=len(vv);vv.extend(pos(y,z) for y,z in poly);ff.append(tuple(range(k,len(vv))))
 return mesh(n,vv,ff,m,c,solid,True,group)

# ONE arch definition drives the body aperture, lip and liner.
archpaths={}
for cy in S['axles']:
 r=S['arch_radius'];z=S['axle_z'];path=[(cy-r,.32)]+[(cy-r*math.cos(i*math.pi/20),z+r*math.sin(i*math.pi/20)) for i in range(21)]+[(cy+r,.32)];archpaths[cy]=path
def bottom(y):
 z=S['sill_z']
 for cy,path in archpaths.items():
  if path[0][0]<y<path[-1][0]:z=max(z,interp(y,path))
 return z
ys=sorted(set([-2.055,2.04,-.77,.27,1.23]+[r[0] for r in S['length_width']+S['belt']]+[round(-2.055+i*.025,6) for i in range(164)]+[y for pts in archpaths.values() for y,z in pts]));ys=[y for y in ys if -2.055<=y<=2.04]
zs=sorted(set([.30,.365,.48,.72,.89,1.02,1.10]+[.30+i*.025 for i in range(34)]))
for s in [-1,1]:
 sn='L' if s>0 else 'R'
 for key,lo,hi in [('Front fender',-2.055,-.77),('front_door',-.77,.27),('rear_door',.27,1.23),('Rear quarter',1.23,2.04)]:
  group=sn+'_'+key if 'door' in key else None;gap=.003 if 'door' in key else 0
  low=.424 if group else S['sill_z']
  o=panel_grid(sn+' | '+key,sorted(set([lo+gap,hi-gap]+[y for y in ys if lo+gap<y<hi-gap])),zs,lambda y,z:sidepos(y,z,s),[lambda y,z:belt(y)-(.014 if group else 0)-z,lambda y,z:z-max(low,bottom(y)+(.003 if group else 0))],paint,group=group)
 # Sill supplies a continuous closed junction with the full floor.
 box(sn+' | sculpted sill',(s*.823,.008,.369),(.105,1.626,.094),paint,body,.024)
 for cy,path in archpaths.items():
  # Shared seating edge at radius R+28 mm. Smooth lip lands exactly on skin.
  vv=[];ff=[]
  for y,z in path:
   d=Vector((y-cy,z-S['axle_z']));d.normalize();yo=y+d.x*.036;zo=max(.365,z+d.y*.036)
   vv.extend([sidepos(yo,zo,s),sidepos(y+d.x*.012,max(.365,z+d.y*.012),s,.018),sidepos(y,z,s,.021),(s*.51,y,z)])
  for i in range(len(path)-1):
   for j in range(3):k=i*4+j;ff.append((k,k+4,k+5,k+1))
  o=mesh(sn+f' | arch lip and tub {cy}',vv,ff,paint,lin,.01,True);o.data.materials.append(black)
  for f in o.data.polygons:
   if f.index%3==2:f.material_index=1
  # Rear-door section of arch is split later for the opening rig.
  mesh(sn+f' | inner wheelhouse {cy}',[(s*.51,y,z) for y,z in path],[tuple(range(len(path)))],black,lin,.012)

# Bonnet and boot surfaces meet their side section, with broad crown/shoulder roll.
fracs=[-1,-.97,-.90,-.80,-.65,-.40,0,.40,.65,.80,.90,.97,1]
def topgrid(n,rows):
 vv=[];ff=[]
 for y,zc in rows:
  for f in fracs:
   t=interp(abs(f),[(0,0),(.4,.025),(.65,.12),(.80,.35),(.90,.65),(.97,.91),(1,1)]);zz=zc+(belt(y)-zc)*t;vv.append((f*width(y,belt(y)),y,zz))
 N=len(fracs)
 for j in range(len(rows)-1):
  for i in range(N-1):k=j*N+i;ff.append((k,k+1,k+N+1,k+N))
 return mesh(n,vv,ff,paint,body,.015,True)
hood=topgrid('Bonnet | crowned centre and shoulder roll',S['hood']);boot=topgrid('Boot | short crowned deck',S['trunk'])
for s in [-1,1]:
 curve('Bonnet | returned side seam '+str(s),[(s*.73,y,interp(y,S['hood'])-.022) for y in [-1.98,-1.85,-1.63,-1.25,-.955]],.0022,black)

def cap_y(x,z,rear=False):
 base=2.04 if rear else -2.055;sg=1 if rear else -1;depth=interp(z,[(.30,.015),(.36,.055),(.50,.11),(.68,.10),(.78,.04),(.88,0),(1.04,0)])
 return base+sg*depth*(1-(abs(x)/max(.001,width(base,z)))**5)
caps={}
for rear in [False,True]:
 base=2.04 if rear else -2.055;rows=[.32,.365,.48,.64,.72,.80,.88];vv=[];ff=[]
 for z in rows:
  for f in fracs:
   x=f*width(base,z);vv.append((x,cap_y(x,z,rear),z))
 for f in fracs:
  zc=(S['trunk'][-1][1] if rear else S['hood'][0][1]);zz=zc+(belt(base)-zc)*interp(abs(f),[(0,0),(.4,.025),(.65,.12),(.8,.35),(.9,.65),(.97,.91),(1,1)]);vv.append((f*width(base,belt(base)),base,zz))
 N=len(fracs)
 for j in range(len(rows)):
  for i in range(N-1):k=j*N+i;ff.append((k,k+1,k+N+1,k+N))
 caps[rear]=mesh(('Rear' if rear else 'Front')+' | shaped bumper and fascia',vv,ff,paint,body,.023,True)

# Cabin: shared curved roof, sloped screens and separately framed side apertures.
vv=[];ff=[]
for y,z in S['roof']:
 for f in fracs:vv.append((S['roof_half_width']*f,y,z-S['roof_edge_drop']*abs(f)**2.7))
N=len(fracs)
for j in range(len(S['roof'])-1):
 for i in range(N-1):k=j*N+i;ff.append((k,k+1,k+N+1,k+N))
mesh('Roof | soft crown',vv,ff,paint,cab,.025,True)
outer_front=[(-.94,1.082),(-.45,1.547),(-.27,1.596),(.265,roof(.265)-.045),(.265,belt(.265))]
outer_rear=[(.275,belt(.275)),(.275,roof(.275)-.045),(.70,1.58),(.85,1.535),(1.40,belt(1.40))]
inner_front=[(-.814,1.110),(-.399,1.510),(-.255,1.55),(.223,1.56),(.223,1.112)]
inner_rear=[(.322,1.113),(.322,1.56),(.665,1.539),(.775,1.485),(1.226,1.122)]
def ring3(n,outer,inner,m,c,solid=.016,group=None):
 N=len(outer);return mesh(n,outer+inner,[(i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N)],m,c,solid,True,group)
for s in [-1,1]:
 sn='L' if s>0 else 'R'
 for label,outer,inner in [('front',outer_front,inner_front),('rear',outer_rear,inner_rear)]:
  group=sn+'_'+label+'_door';out3=[cabpos(y,z,s) for y,z in outer];in3=[cabpos(y,z,s,.001) for y,z in inner]
  ring3(sn+' '+label+' | window frame',out3,in3,paint,cab)
  cy=sum(y for y,z in inner)/len(inner);cz=sum(z for y,z in inner)/len(inner);small=[(cy+(y-cy)*.97,cz+(z-cz)*.966) for y,z in inner]
  ring3(sn+' '+label+' | window gasket',in3,[cabpos(y,z,s,.001) for y,z in small],black,cab,.009)
  pane=[(cy+(y-cy)*.94,cz+(z-cz)*.94) for y,z in small]
  mesh(sn+' '+label+' | window pane',[cabpos(y,z,s,-.007) for y,z in pane],[tuple(range(len(pane)))],glass,cab,.004,True,group)
  # Deep reveal behind the pane perimeter fills the weather-seal shadow.
  ring3(sn+' '+label+' | inner glass reveal',[cabpos(y,z,s,-.018) for y,z in small],[cabpos(y,z,s,-.018) for y,z in pane],black,cab,.005)
 # A-pillar base to body fender; rear pillar closes onto local rear quarter.
 mesh(sn+' | scuttle corner',[sidepos(-.94,belt(-.94),s),sidepos(-.77,belt(-.77),s),cabpos(-.77,1.25,s)],[(0,1,2)],paint,cab,.015,True)
 mesh(sn+' | rear sail junction',[cabpos(1.40,belt(1.40),s),sidepos(1.50,belt(1.50),s),sidepos(1.40,belt(1.40)-.024,s)],[(0,1,2)],paint,cab,.014,True)
def screenpos(u,t,rear=False):
 ly,lz,hy,hz=(1.40,1.121,.85,1.580) if rear else (-.94,1.126,-.45,1.592)
 lowz=lz+(belt(ly)-lz)*abs(u)**2.7;highz=hz-S['roof_edge_drop']*abs(u)**2.7
 return (u*((width(ly,belt(ly)))*(1-t)+S['roof_half_width']*t),ly+(hy-ly)*t,lowz+(highz-lowz)*t)
for rear in [False,True]:
 border=[(f,0) for f in fracs]+[(f,1) for f in reversed(fracs)];outer=[screenpos(f,t,rear) for f,t in border];inner=[screenpos(f*.945,.06+t*.88,rear) for f,t in border];small=[screenpos(f*.924,.079+t*.846,rear) for f,t in border]
 label='Rear screen' if rear else 'Windscreen';ring3(label+' | metal surround',outer,inner,paint,cab,.018);ring3(label+' | seal',inner,small,black,cab,.007)
 vv=[];ff=[]
 for j in range(7):
  for i in range(17):vv.append(screenpos(-.924+1.848*i/16,.079+.846*j/6,rear))
 for j in range(6):
  for i in range(16):k=j*17+i;ff.append((k,k+1,k+18,k+17))
 mesh(label+' | curved glazing',vv,ff,glass,cab,.004,True)

# Floor footprint covers the entire cabin, narrowing only around occupied tubs.
def floor_width(y):
 return .509 if any(abs(y-cy)<S['arch_radius']+.005 for cy in S['axles']) else width(y,.405)-.007
fys=sorted(set([-.94,1.97]+[round(-.94+i*.025,6) for i in range(117)]+[cy+d for cy in S['axles'] for d in [-S['arch_radius']-.006,-S['arch_radius']-.004,S['arch_radius']+.004,S['arch_radius']+.006] if -.94<cy+d<1.97]));fys=[y for y in fys if -.94<=y<=1.97]
vv=[(s*floor_width(y),y,.405) for y in fys for s in [-1,1]];ff=[(i,i+1,i+3,i+2) for i in range(0,len(vv)-2,2)];mesh('Floor | complete shaped pan',vv,ff,floor_mat,lin,.025)
box('Floor | firewall',(0,-.905,.68),(1.04,.035,.56),black,lin,.009)
for s in [-1,1]:box('Underbody | sill beam '+str(s),(s*.45,.32,.344),(.075,2.6,.07),black,lin,.012)

# Wheels are revolved cross-sections; rubber extends beyond both rim lips.
def revolve(n,profile,cx,cy,cz,s,m,c=wheelcol,N=48,group=None):
 vv=[];ff=[]
 for xx,r in profile:
  for j in range(N):ang=j*math.tau/N;vv.append((cx+s*xx,cy+r*math.sin(ang),cz+r*math.cos(ang)))
 for i in range(len(profile)):
  for j in range(N):ff.append((i*N+j,i*N+(j+1)%N,((i+1)%len(profile))*N+(j+1)%N,((i+1)%len(profile))*N+j))
 return mesh(n,vv,ff,m,c,smooth=True,group=group)
tyreprofile=[(-.108,.225),(-.126,.253),(-.129,.294),(-.112,.334),(-.085,.349),(.085,.349),(.112,.334),(.129,.294),(.126,.253),(.108,.225),(.085,.218),(-.085,.218)]
for cy in S['axles']:
 for s in [-1,1]:
  sn='L' if s>0 else 'R';ax='front' if cy<0 else 'rear';g=sn+'_'+ax+'_wheel';cx=s*S['track']/2;cz=S['axle_z']
  revolve(g+' | tyre carcass',tyreprofile,cx,cy,cz,s,rubber,group=g)
  revolve(g+' | dished barrel',[(-.098,.211),(-.098,.226),(-.088,.233),(-.074,.226),(.075,.226),(.108,.233),(.114,.224),(.094,.211)],cx,cy,cz,s,gold,group=g)
  rod(g+' | wheel hub',(cx+s*.061,cy,cz),(cx+s*.113,cy,cz),.067,gold,wheelcol,group=g)
  for k in range(6):
   ang=k*math.tau/6;poly=[]
   for radius,da in [(.057,-.42),(.207,-.14),(.216,.14),(.075,.42)]:aa=ang+da;poly.append((cy+radius*math.sin(aa),cz+radius*math.cos(aa)))
   ob=prism(g+' | spoke '+str(k),poly,0,cx+s*.060,cx+s*.096,gold,wheelcol,g);bevel(ob,.009,2)
  if a.stage!='shape':
   for k in range(5):ang=k*math.tau/5;yy=cy+.048*math.sin(ang);zz=cz+.048*math.cos(ang);rod(g+' | lug',(cx+s*.113,yy,zz),(cx+s*.125,yy,zz),.009,silver,wheelcol,8,g)
   revolve(g+' | sidewall moulding',[(.126,.263),(.130,.267),(.13,.270),(.126,.271)],cx,cy,cz,s,rubber,group=g)
   rod(g+' | brake rotor',(cx+s*.040,cy,cz),(cx+s*.045,cy,cz),.183,silver,wheelcol,40,g)
   # Batched tread blocks maintain rounded shoulders instead of a rectangular sleeve.
   vv=[];ff=[]
   for k in range(48):
    for lane in range(4):
     theta=math.tau*(k+(lane%2)*.43)/48;xx=-.082+lane*.0545
     for dx in [-.022,.022]:
      for da in [-.047,.047]:
       for dr in [0,.009]:
        rad=.349-abs(xx+dx)**3*10+dr;vv.append((cx+s*(xx+dx),cy+rad*math.sin(theta+da),cz+rad*math.cos(theta+da)))
     k0=len(vv)-8
     for ids in [(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]:ff.append(tuple(k0+i for i in ids))
   bevel(mesh(g+' | tread blocks',vv,ff,rubber,wheelcol,group=g),.002,1)

# Fascia apertures and matching fitted housings.
cap_holes={False:[],True:[]}
def inset(n,poly,rear,m,depth=.045):
 cap_holes[rear].append(poly)
 centre=Vector((sum(p[0] for p in poly)/len(poly),sum(p[1] for p in poly)/len(poly)));inner=[tuple(centre+(Vector(p)-centre)*.91) for p in poly];sg=1 if rear else -1
 outer=[(x,cap_y(x,z,rear)+sg*.003,z) for x,z in poly];ins=[(x,cap_y(x,z,rear)-sg*depth,z) for x,z in inner];N=len(poly)
 mesh(n+' | recessed return',outer+ins,[(i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N)],black,trim,.006,True)
 return mesh(n+' | inset',ins,[tuple(range(N))],m,trim,.009)
for s in [-1,1]:
 poly=[(s*x,z) for x,z in [(.435,.786),(.455,.925),(.50,.966),(.64,.962),(.790,.909),(.819,.790),(.737,.762),(.507,.758)]]
 inset('Blobeye '+str(s),poly,False,black,.045)
 for x,z,r in [(.529,.832,.061),(.688,.818,.062),(.56,.925,.025)]:
  x*=s;y=cap_y(x,z)-.005;rod('Headlamp | reflector',(x,y+.018,z),(x,y-.008,z),r,silver,N=24);rod('Headlamp | lens',(x,y-.010,z),(x,y-.017,z),r*.80,white if r>.03 else amber,N=24)
 inset('Rear lamp '+str(s),[(s*x,z) for x,z in [(.46,.806),(.46,.991),(.62,1.034),(.793,.992),(.802,.821),(.71,.798)]],True,redlens,.012)
 poly=[(s*x,z) for x,z in [(.483,.940),(.483,.978),(.617,1.014),(.768,.979),(.772,.946)]];mesh('Rear lamp | ivory band',[(x,cap_y(x,z,True)+.002,z) for x,z in poly],[tuple(range(5))],white,trim,.007)
inset('Upper grille',rr(0,.883,.80,.12,.032),False,dial,.065)
inset('Main intake',rr(0,.559,.94,.205,.024),False,dial,.075)
for s in [-1,1]:inset('Corner intake '+str(s),rr(s*.669,.555,.227,.192,.019),False,dial,.045)
inset('Rear plate recess',rr(0,.789,.475,.177,.02),True,black,.045)
if a.stage!='shape':
 for z in [.513,.56,.606]:box('Intake | horizontal louvre',(0,-2.172,z),(.875,.026,.013),black,b=.003)
 for s in [-1,1]:
  for z in [.51,.56,.61]:box('Corner intake | slat',(s*.664,-2.136,z),(.188,.034,.016),black,b=.003)
 for z in [.854,.895,.927]:box('Upper grille | slat',(0,-2.075,z),(.713,.035,.011),black,b=.002)
 for s in [-1,1]:
  sn='L' if s>0 else 'R'
  for y,g in [(.105,sn+'_front_door'),(1.057,sn+'_rear_door')]:
   z=.986;x=s*(width(y,z)+.006);box(sn+' | handle pocket',(x,y,z),(.010,.143,.054),black,b=.013,group=g);box(sn+' | door handle',(x+s*.011,y,z+.008),(.026,.106,.022),paint,b=.007,group=g)
  g=sn+'_front_door';rod(sn+' | mirror stalk',(s*.861,-.690,1.046),(s*.983,-.68,1.155),.021,black,group=g)
  box(sn+' | mirror housing',(s*.999,-.698,1.187),(.165,.18,.125),black,b=.032,group=g);box(sn+' | mirror lens',(s*.999,-.602,1.187),(.128,.008,.087),silver,b=.015,group=g)
  # Consistent broad graphic, conforming to the actual surface and door splits.
  poly=[(-.46,.48),(.12,.48),(1.04,.90),(.62,.72),(.68,.81)]
  for lo,hi,g in [(-.77,.267,sn+'_front_door'),(.273,1.23,sn+'_rear_door')]:
   pp=clip(clip(poly,lambda y,z:y-lo),lambda y,z:hi-y);pp=clip(pp,lambda y,z:z-bottom(y)-.007)
   if len(pp)>2:mesh(sn+' | ivory graphic',[sidepos(y,z,s,.0018) for y,z in pp],[tuple(range(len(pp)))],cream,trim,group=g)
  for cy in S['axles']:
   yy=cy+.445;box(sn+f' | mudflap hanger {cy}',(s*.791,yy,.470),(.29,.046,.043),black,rally,.004)
   box(sn+f' | mudflap {cy}',(s*.791,yy+.014,.314),(.275,.018,.330),red,rally,.010)
   box(sn+f' | mudflap clamp {cy}',(s*.791,yy+.026,.457),(.272,.016,.027),silver,rally,.003)
   for dx in [-.102,.102]:rod('Mudflap | clamp bolt',(s*.791+dx,yy+.036,.457),(s*.791+dx,yy+.042,.457),.008,black,rally,8)
   box(sn+' | mudflap body bracket',(s*.79,yy-.016,.517),(.23,.050,.082),black,rally,.005)
 # Wipers conform to the sloped windscreen at their local contact height.
 for x in [-.36,.34]:
  curve('Wiper | arm',[(x+.14,-.967,1.147),(x-.01,-.89,1.216),(x-.22,-.867,1.243)],.008,black)
  curve('Wiper | blade',[(x-.36,-.882,1.22),(x+.03,-.882,1.22)],.011,black)

# Bonnet scoop: open front, shaped shell and dark inset throat.
v=[(-.28,-1.59,1.073),(.28,-1.59,1.073),(.255,-1.13,1.117),(-.255,-1.13,1.117),(-.251,-1.565,1.192),(.251,-1.565,1.192),(.24,-1.20,1.202),(-.24,-1.20,1.202)]
bevel(mesh('Scoop | open formed shell',v,[(0,4,7,3),(1,2,6,5),(4,5,6,7),(3,7,6,2)],paint,rally,.016,True),.006)
mesh('Scoop | dark duct',[(-.24,-1.526,1.09),(.24,-1.526,1.09),(.24,-1.526,1.176),(-.24,-1.526,1.176)],[(0,1,2,3)],dial,rally,.01)
box('Scoop | lower lip',(0,-1.574,1.079),(.553,.055,.029),paint,rally,.012)
if a.stage!='shape':
 for s in [-1,1]:
  insetpoly=[(s*.48,-1.63),(s*.62,-1.62),(s*.62,-1.39),(s*.48,-1.40)]
  mesh('Bonnet | vent insert '+str(s),[(x,y,interp(y,S['hood'])-.008) for x,y in insetpoly],[(0,1,2,3)],black,rally,.008)
  for y in [-1.59,-1.55,-1.51,-1.47,-1.43]:box('Bonnet vent | louvre',(s*.55,y,interp(y,S['hood'])-.005),(.115,.012,.01),black,rally,.002)
# Wing mounting plinths physically overlap the deck; shaped uprights, finite aerofoil.
for s in [-1,1]:
 box('Wing | deck plinth '+str(s),(s*.64,1.735,1.104),(.16,.285,.037),paint,rally,.020)
 pp=[(1.65,1.11),(1.80,1.11),(1.94,1.42),(1.83,1.43),(1.67,1.24)]
 bevel(prism('Wing | upright '+str(s),pp,0,s*.64-.034,s*.64+.034,paint,rally),.013,3)
wingprof=[(1.73,1.42),(1.78,1.447),(1.96,1.439),(2.0,1.410),(1.84,1.396)]
bevel(prism('Wing | aerofoil',wingprof,0,-.811,.811,paint,rally),.012,3)
box('Roof | vent base',(0,-.17,1.659),(.285,.31,.026),black,rally,.035)
bevel(prism('Roof | raised vent',[(-.31,1.663),(-.31,1.745),(-.13,1.761),(.02,1.669)],0,-.126,.126,paint,rally),.02)
box('Roof | vent mouth',(0,-.316,1.707),(.192,.006,.040),black,rally,.01)
if a.stage!='shape':
 # Four separate auxiliary lamp housings on a structurally supported carrier.
 box('Rally lights | carrier',(0,-2.217,.765),(1.23,.072,.066),black,rally,.009)
 for x in [-.41,.41]:box('Rally lights | mounting arm',(x,-2.132,.74),(.059,.25,.075),black,rally,.008)
 for x in [-.456,-.152,.152,.456]:
  rod('Rally light | casing',(x,-2.202,.913),(x,-2.278,.913),.137,black,rally,24)
  rod('Rally light | bezel',(x,-2.279,.913),(x,-2.288,.913),.119,silver,rally,24)
  rod('Rally light | lens',(x,-2.289,.913),(x,-2.295,.913),.106,cream,rally,24)
  box('Rally light | stem',(x,-2.226,.779),(.052,.045,.09),black,rally,.006)
 # Guard bends under the nose and mounts to the lower carrier.
 vv=[(-.49,-2.218,.385),(.49,-2.218,.385),(.46,-2.196,.59),(-.46,-2.196,.59),(-.39,-1.91,.285),(.39,-1.91,.285)]
 guard=mesh('Skid plate | folded aluminium',vv,[(0,1,2,3),(0,4,5,1)],silver,rally,.018)
 for x in [-.26,0,.26]:cut(guard,rr(x,.478,.062,.091,.008),1,-2.3,-2.0)
 for x in [-.36,.36]:box('Skid plate | chassis mount',(x,-1.965,.326),(.06,.19,.07),black,rally,.005)
 for x in [-.64,.64]:
  rear=x>0;yy=2.153 if rear else -2.188;zz=.48
  curve('Tow loop | rear' if rear else 'Tow loop | front',[(x+dx,yy,zz+dz) for dx,dz in [(-.04,.052),(-.052,.01),(-.046,-.065),(0,-.083),(.046,-.065),(.052,.01),(.04,.052)]], .017,red,rally)
  box('Tow loop | anchor',(x,yy+(-.048 if rear else .048),zz+.032),(.08,.13,.08),black,rally,.009)
 # Visible hollow exhaust tip; no metallic solid disk at its end.
 curve('Exhaust | pipe',[(-.54,1.34,.31),(-.57,1.86,.29),(-.59,2.145,.315)],.035,silver,lin)
 revolve('Exhaust | rolled open tip',[(0,.063),(.14,.069),(.151,.063),(.151,.054),(0,.051)],0,0,0,1,silver,lin,N=32)
 o=bpy.data.objects['Exhaust | rolled open tip'];o.rotation_euler.z=math.pi/2;o.location=(-.59,2.04,.315)

# Tessellate all fascia apertures from shared 2D boundaries. Subtracting convex
# profiles from small planar cells avoids self-intersecting thin-shell Booleans.
def subtract_convex(poly,hole):
 area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(hole,hole[1:]+hole[:1]));hole=hole if area>0 else list(reversed(hole));insidepoly=poly;pieces=[]
 for aa,bb in zip(hole,hole[1:]+hole[:1]):
  fn=lambda x,z:(bb[0]-aa[0])*(z-aa[1])-(bb[1]-aa[1])*(x-aa[0])
  outside=clip(insidepoly,lambda x,z:-fn(x,z))
  if len(outside)>2:pieces.append(outside)
  insidepoly=clip(insidepoly,fn)
  if len(insidepoly)<3:break
 return pieces
for rear in [False,True]:
 base=2.04 if rear else -2.055;zc=S['trunk'][-1][1] if rear else S['hood'][0][1]
 def topcap(x):
  f=abs(x)/width(base,belt(base));return zc+(belt(base)-zc)*interp(f,[(0,0),(.4,.025),(.65,.12),(.8,.35),(.9,.65),(.97,.91),(1,1)])
 xs=sorted(set([-.85+i*.025 for i in range(69)]+[x for pp in cap_holes[rear] for x,z in pp]));zrows=sorted(set([.32,.365,.48,.64,.72,.78,.80,.88,1.04]+[.32+i*.025 for i in range(30)]+[z for pp in cap_holes[rear] for x,z in pp]));vv=[];ff=[]
 for xa,xb in zip(xs,xs[1:]):
  for za,zb in zip(zrows,zrows[1:]):
   pp=[(xa,za),(xb,za),(xb,zb),(xa,zb)]
   for fn in [lambda x,z:z-.32,lambda x,z:width(base,z)-x,lambda x,z:width(base,z)+x,lambda x,z:topcap(x)-z]:
    if len(pp)<3:break
    pp=clip(pp,fn)
   pieces=[pp] if len(pp)>2 else []
   for hole in cap_holes[rear]:
    if not pieces:break
    pieces=[q for piece in pieces for q in subtract_convex(piece,hole)]
   for pp in pieces:
    area=abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(pp,pp[1:]+pp[:1])))
    if area<1e-10:continue
    k=len(vv);vv.extend((x,cap_y(x,z,rear),z) for x,z in pp);ff.append(tuple(range(k,len(vv))))
 name=caps[rear].name;bpy.data.objects.remove(caps[rear],do_unlink=True);caps[rear]=mesh(name,vv,ff,paint,body,.018,True)

# Additional construction, interior and rig are loaded explicitly in full stage.
if a.stage!='shape':
 continuation=Path(__file__).with_name('impreza_cockpit_rig.py')
 if continuation.exists():exec(compile(continuation.read_text(),str(continuation),'exec'))

# Review lighting and fixed cameras are intentionally shared between revisions.
ground=mat('Studio | warm stone',(.42,.40,.355),.95);mesh('Studio ground',[(-100,-100,-.008),(100,-100,-.008),(100,100,-.008),(-100,100,-.008)],[(0,1,2,3)],ground,studio)
world=bpy.data.worlds.new('Soft studio');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.66,.70,.75,1);world.node_tree.nodes['Background'].inputs[1].default_value=.5;sc.world=world
for name,loc,power,size in [('Key',(4,-4,6),1050,5),('Fill',(-4,-1,4),700,4),('Rim',(1,4,5),1050,4)]:
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);studio.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,.8))-o.location).to_track_quat('-Z','Y').to_euler()
def cam(n,loc,target,scale,res):
 d=bpy.data.cameras.new(n);o=bpy.data.objects.new(n,d);cams.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();d.type='ORTHO';d.ortho_scale=scale;o['resolution']=res;return o
views={'quarter':cam('Review | front quarter',(5.8,-8.0,3.25),(0,0,.82),5.3,(1250,850)),'rear-quarter':cam('Review | rear quarter',(5.7,8,3.1),(0,0,.85),5.3,(1250,850)), 'side':cam('Review | side',(8,0,.85),(0,0,.85),4.9,(1450,650)), 'front':cam('Review | front',(0,-8,.88),(0,0,.88),2.55,(950,900)), 'rear':cam('Review | rear',(0,8,.88),(0,0,.88),2.55,(950,900)), 'top':cam('Review | top',(0,0,8),(0,0,0),4.95,(850,1300)), 'underside':cam('Review | underside',(3.7,4.7,-2.9),(0,0,.65),5.35,(1250,850))}
sc.render.engine='CYCLES';sc.cycles.samples=24;sc.cycles.use_denoising=True;sc.render.threads_mode='FIXED';sc.render.threads=12;sc.view_settings.view_transform='AgX';sc.render.image_settings.file_format='PNG';sc.render.resolution_percentage=100
im=bpy.data.images.load(str(src/S['authority']));im.pack();im.use_fake_user=True
sc['vehicle']=S['vehicle'];sc['approved_style_reference']=S['authority'];sc['stage']=a.stage;sc['scope']='Stylized Blender authoring model. No export, LOD, physics or factory-dimension certification.'
for fn in [Path(__file__),src/'approved-shape-spec.json']:
 shutil.copy2(fn,out/fn.name)
if a.stage!='shape' and continuation.exists():shutil.copy2(continuation,out/continuation.name)
manifest={'approved_reference':str(src/S['authority']),'reference_sha256':hashlib.sha256((src/S['authority']).read_bytes()).hexdigest(),'groups':groups,'spec':S,'stage':a.stage}
(out/'build-manifest.json').write_text(json.dumps(manifest,indent=2))
for key in a.render.split(','):
 if key not in views:continue
 sc.camera=views[key];sc.render.resolution_x,sc.render.resolution_y=sc.camera['resolution'];sc.render.filepath=str(out/(key+'.png'));bpy.data.objects['Studio ground'].hide_render=key=='underside';bpy.ops.render.render(write_still=True)
bpy.data.objects['Studio ground'].hide_render=False;sc.camera=views['quarter'];sc.render.resolution_x,sc.render.resolution_y=sc.camera['resolution']
for area in bpy.context.screen.areas:
 if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Impreza_Gravel.blend'));print('IMPREZA_SAVED '+str(out),flush=True)
