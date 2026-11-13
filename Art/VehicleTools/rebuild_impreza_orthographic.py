"""Reference-traced Impreza rebuild. Independent body constructor; fresh outputs only.
General mesh and wheel construction utilities are reused, not the rejected body.
"""
import bpy,bmesh,math,json,sys,argparse,ast,shutil,hashlib
from pathlib import Path
from mathutils import Vector
from functools import lru_cache
P=argparse.ArgumentParser();P.add_argument('--output',required=True);P.add_argument('--render',default='side,quarter,rear-quarter,front,rear,top');P.add_argument('--shape',action='store_true')
a=P.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output)
if out.exists() and any(out.iterdir()):raise RuntimeError('Fresh output folder required; preserve previous and manual work.')
out.mkdir(parents=True,exist_ok=True)
src=Path('C:/GrandTour/Art/References/Vehicles/Impreza2003/orthographic-reset-v01');S=json.loads((src/'shape-controls.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True);sc=bpy.context.scene;sc.unit_settings.system='METRIC'
def col(n):
 c=bpy.data.collections.new(n);sc.collection.children.link(c);return c
body=col('01 | Traced body and separate panels');cab=col('02 | Fitted cabin and glass');wheelcol=col('03 | Wheels');lin=col('04 | Closed floor and wheelhouses');trim=col('05 | Fitted lighting and trim');rally=col('06 | Rally components');inside=col('07 | Cabin');rigcol=col('08 | Component pivots');studio=col('90 | Studio');cams=col('91 | Fixed review views');guides=col('92 | Reference contours')
groups={};root=None
# Import only audited general-purpose functions by AST. No old model execution.
old=Path(__file__).with_name('build_impreza_gravel.py').read_text()
fnames={'mat','tag','mesh','bevel','box','curve','rod','apply','prism','cut','rr','clip','panel_grid','ring3','revolve','subtract_convex','interp'}
utility=ast.Module(body=[n for n in ast.parse(old).body if isinstance(n,ast.FunctionDef) and n.name in fnames],type_ignores=[])
exec(compile(utility,'mesh_utilities','exec'))
paint=mat('Paint | reference blue',(.008,.145,.56),.55,.05);black=mat('Trim | charcoal',(.014,.019,.025),.72);rubber=mat('Tyre | soft charcoal',(.023,.026,.03),.83);gold=mat('Wheel | gold',(.63,.36,.065),.42,.42);silver=mat('Hardware | satin aluminium',(.48,.50,.51),.40,.65);red=mat('Rubber | red',(.62,.035,.018),.69);cream=mat('Graphics | warm ivory',(.88,.81,.62),.65);white=mat('Optics | warm lens',(.86,.88,.79),.3,.2);amber=mat('Optics | amber',(.85,.29,.035),.42);redlens=mat('Optics | red tail',(.65,.022,.012),.36);glass=mat('Glass | smoke grey',(.043,.055,.066),.22,.15);cloth=mat('Cabin | dark woven cloth',(.035,.044,.054),.92);insert=mat('Cabin | blue cloth',(.022,.082,.18),.9);floor_mat=mat('Cabin | carpet',(.021,.025,.029),.96);dial=mat('Recess | deep black',(.006,.009,.012),.88)
paint.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value=0
paint.node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value=0
paint.diffuse_color=(.005,.073,.40,1);paint.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=paint.diffuse_color
glass.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value=.22
glass.node_tree.nodes['Principled BSDF'].inputs['IOR'].default_value=1.12
def yz(p):return ((p[0]-893)/400,(757-p[1])/400)
def profile(k):return [yz(p) for p in S[k]]
def smooth(x,rows):
 # Monotone cubic Hermite; avoids arbitrary flat section joins and overshoot.
 if x<=rows[0][0]:return rows[0][1]
 if x>=rows[-1][0]:return rows[-1][1]
 d=[(b[1]-aa[1])/(b[0]-aa[0]) for aa,b in zip(rows,rows[1:])]
 ms=[d[0]]+[0 if d[i-1]*d[i]<=0 else 2*d[i-1]*d[i]/(d[i-1]+d[i]) for i in range(1,len(d))]+[d[-1]]
 for i,(aa,b) in enumerate(zip(rows,rows[1:])):
  if aa[0]<=x<=b[0]:
   h=b[0]-aa[0];t=(x-aa[0])/h;return (2*t**3-3*t*t+1)*aa[1]+(t**3-2*t*t+t)*h*ms[i]+(-2*t**3+3*t*t)*b[1]+(t**3-t*t)*h*ms[i+1]
def rounded(poly,amount=.04,steps=5):
 result=[]
 for i,v in enumerate(poly):
  p=Vector(poly[i-1]);v=Vector(v);n=Vector(poly[(i+1)%len(poly)]);da=min(amount,(p-v).length*.24);db=min(amount,(n-v).length*.24);p=v+(p-v).normalized()*da;n=v+(n-v).normalized()*db
  for j in range(steps+1):t=j/steps;result.append(tuple((1-t)**2*p+2*t*(1-t)*v+t*t*n))
 return result
hoodrows=profile('hood_centre_px');beltrows=profile('body_upper_px');roofrows=profile('roof_crown_px');roofedges=profile('roof_edge_px');bootrows=profile('boot_centre_px');cabrows=profile('cabin_side_upper_px')
axles=[yz(p)[0] for p in S['wheel_centres_px']];wheelz=yz(S['wheel_centres_px'][0])[1];track=1.61
arches=[profile('arch_front_px'),profile('arch_rear_px')]
def archz(y):return max([.2725]+[smooth(y,rrr) for rrr in arches if rrr[0][0]<=y<=rrr[-1][0]])
def belt(y):return smooth(y,beltrows)
def width(y,z):
 base=smooth(y,[(-1.97,.76),(-1.75,.86),(-1.27,.882),(-.83,.84),(-.2,.835),(.5,.846),(1.27,.889),(1.7,.86),(2.0925,.76)])
 tuck=smooth(z,[(.24,-.064),(.31,-.035),(.43,-.011),(.68,0),(.91,-.009),(1.09,-.049)])
 # Flare is part of the common skin, smoothly fades into doors and bonnet.
 flare=sum(.045*math.exp(-((y-c)/.42)**4)*math.exp(-((z-.74)/.24)**4) for c in axles)
 # Shallow pressed lower-door waist; broad curved panels remain quiet.
 relief=-.012*math.exp(-((z-.56)/.065)**2)*math.exp(-((y-.05)/1.0)**6)
 return base+tuck+flare+relief
def sidepos(y,z,s,off=0):return (s*(width(y,z)+off),y,z)
def cabtop(y):
 if y<roofedges[0][0]:return interp(y,[(cabrows[0][0],belt(cabrows[0][0])),roofedges[0]])
 if y>roofedges[-1][0]:return interp(y,[roofedges[-1],(cabrows[-1][0],belt(cabrows[-1][0]))])
 return smooth(y,roofedges)
def cw(y,z):
 t=max(0,min(1,(z-belt(y))/max(.001,cabtop(y)-belt(y))));topw=interp(y,[(-.82,width(-.82,belt(-.82))),(-.295,.660),(.45,.661),(.9175,.664),(1.63,width(1.63,belt(1.63)))])
 return width(y,belt(y))*(1-t)+topw*t+.012*math.sin(math.pi*t)
def cabpos(y,z,s,off=0):return (s*(cw(y,z)+off),y,z)
front=-1.97;back=2.0925
def front_edge(z):return smooth(z,[(.24,-1.97),(.65,-1.97),(.75,-1.91),(.85,-1.80),(.95,-1.58),(1.10,-1.20)])
def split_y(z):return smooth(z,sorted((zz,yy) for yy,zz in profile('door_split_px')))
def rear_door_y(z):return smooth(z,sorted((zz,yy) for yy,zz in profile('rear_door_end_px')))
ys=sorted(set([front,back]+[front+(back-front)*i/240 for i in range(241)]+[v[0] for v in beltrows]+[y for ar in arches for y,z in ar]))
zs=[.24+i*.015 for i in range(64)]
for s in [-1,1]:
 sn='L' if s>0 else 'R'
 # Panels are cut from one master skin. Thin seams get an inboard backing.
 for label,lo,hi in [('front fender',front,-.82),('front door',-.82,.29),('rear door',.18,1.16),('rear quarter',.95,back)]:
  gap=.002 if 'door' in label else 0
  limits=[lambda y,z:belt(y)-z,lambda y,z:z-archz(y),lambda y,z:y-front_edge(z)]
  if label=='front door':limits.append(lambda y,z:split_y(z)-.002-y)
  if label=='rear door':limits.extend([lambda y,z:y-split_y(z)-.002,lambda y,z:rear_door_y(z)-.002-y])
  if label=='rear quarter':limits.append(lambda y,z:y-rear_door_y(z))
  panel_grid(sn+' | '+label,[lo+gap]+[y for y in ys if lo+gap<y<hi-gap]+[hi-gap],zs,lambda y,z:sidepos(y,z,s),limits,paint,body,sn+' '+label,.012)
 for fn in [lambda z:-.82,split_y,rear_door_y]:
  pts=[sidepos(fn(z),z,s,-.009) for z in [.275+i*.8/120 for i in range(121)] if archz(fn(z))<=z<=belt(fn(z))]
  curve(sn+' | door seam backing',pts,.005,black,lin)
 # Arch returns use the EXACT aperture curve sampled by body grid.
 for j,ar in enumerate(arches):
  ary=sorted(set([ar[0][0],ar[-1][0]]+[y for y in ys if ar[0][0]<y<ar[-1][0]]));vv=[];ff=[]
  for y in ary:
   z=archz(y);vv.extend([sidepos(y,z,s),(s*.515,y,z),(s*.515,y,z+.015)])
  for i in range(len(ary)-1):k=i*3;ff.append((k,k+3,k+4,k+1))
  mesh(sn+f' | fitted arch return {j}',vv,ff,black,lin,.012,True)
  mesh(sn+f' | closed inner tub {j}',[(s*.515,y,archz(y)) for y in ary],[tuple(range(len(ary)))],black,lin,.016)
  curve(sn+f' | fine arch edge {j}',[sidepos(y,archz(y)+.006,s,.001) for y in ary],.005,paint,body)
 box(sn+' | rounded rocker',(s*.80,.04,.279),(.12,1.66,.095),paint,body,.025)

# Transverse surfaces have coherent crown and broad shoulder roll.
fracs=[-1+i/20 for i in range(41)]
def surface_z(y,f,rows):return smooth(y,rows)+(belt(y)-smooth(y,rows))*smooth(abs(f),[(0,0),(.45,.025),(.70,.18),(.88,.57),(1,1)])
def topgrid(name,rows):
 yy=sorted(set([p[0] for p in rows]+[rows[0][0]+(rows[-1][0]-rows[0][0])*i/55 for i in range(56)]));vv=[];ff=[]
 for y in yy:
  for f in fracs:vv.append((f*width(y,belt(y)),y,surface_z(y,f,rows)))
 for j in range(len(yy)-1):
  for i in range(40):k=j*41+i;ff.append((k,k+1,k+42,k+41))
 return mesh(name,vv,ff,paint,body,.016,True)
hood=topgrid('Bonnet | traced crown and rolling shoulders',hoodrows);boot=topgrid('Boot | rounded deck and rear return',bootrows)
for s in [-1,1]:
 curve('Bonnet | panel seam',[(s*.72*width(y,belt(y)),y,surface_z(y,.72,hoodrows)+.001) for y in [-1.70+i*(hoodrows[-1][0]+1.688)/48 for i in range(49)]],.002,black)

# Cabin skin is a curved master surface minus the two true window openings.
windows=[rounded(profile('front_glass_px'),.045,5),rounded(profile('rear_glass_px'),.043,5)]
for s in [-1,1]:
 sn='L' if s>0 else 'R';vv=[];ff=[]
 cyys=sorted(set([cabrows[0][0]+(cabrows[-1][0]-cabrows[0][0])*i/120 for i in range(121)]+[y for y,z in cabrows]+[y for pp in windows for y,z in pp]));czz=[1.005+i*.013 for i in range(51)]
 for ya,yb in zip(cyys,cyys[1:]):
  for za,zb in zip(czz,czz[1:]):
   pp=clip(clip([(ya,za),(yb,za),(yb,zb),(ya,zb)],lambda y,z:cabtop(y)-z),lambda y,z:z-belt(y));pieces=[pp] if len(pp)>2 else []
   for hole in windows:pieces=[q for p0 in pieces for q in subtract_convex(p0,hole)]
   for pp in pieces:
    if len(pp)>2:k=len(vv);vv.extend(cabpos(y,z,s) for y,z in pp);ff.append(tuple(range(k,len(vv))))
 mesh(sn+' | curved pillars and cabin surround',vv,ff,paint,cab,.013,True)
 for i,outer in enumerate(windows):
  cy=sum(y for y,z in outer)/len(outer);cz=sum(z for y,z in outer)/len(outer);inner=[(cy+(y-cy)*.976,cz+(z-cz)*.954) for y,z in outer]
  ring3(sn+f' | window rubber {i}',[cabpos(y,z,s,.001) for y,z in outer],[cabpos(y,z,s,-.006) for y,z in inner],black,cab,.008)
  # Tessellate the pane on the curved cabin surface; nonplanar ngons caused glare wedges.
  pv=[];pf=[];ymin=min(y for y,z in inner);ymax=max(y for y,z in inner);zmin=min(z for y,z in inner);zmax=max(z for y,z in inner)
  for jj in range(35):
   ya=ymin+(ymax-ymin)*jj/35;yb=ymin+(ymax-ymin)*(jj+1)/35
   for kk in range(22):
    za=zmin+(zmax-zmin)*kk/22;zb=zmin+(zmax-zmin)*(kk+1)/22;q=clip(clip(clip(clip(inner,lambda y,z:y-ya),lambda y,z:yb-y),lambda y,z:z-za),lambda y,z:zb-z)
    if len(q)>2:n=len(pv);pv.extend(cabpos(y,z,s,-.007) for y,z in q);pf.append(tuple(range(n,len(pv))))
  mesh(sn+f' | fitted side glass {i}',pv,pf,glass,cab,.005,True)
 # Clearly separate fixed quarter light, important to GD cabin identity.
 pp=profile('rear_quarter_divider_px');curve(sn+' | quarter light division',[cabpos(y,z,s,.002) for y,z in pp],.012,black,cab)
 curve(sn+' | lower weatherstrip',[cabpos(y,belt(y)+.007,s,.002) for y in [cabrows[0][0]+i*(windows[1][-10][0]-cabrows[0][0])/60 for i in range(61)]],.008,black,cab)

rv=[];rf=[];ry=[roofrows[0][0]+i*(roofrows[-1][0]-roofrows[0][0])/65 for i in range(66)]
for y in ry:
 zc=smooth(y,roofrows);ze=smooth(y,roofedges);x=cw(y,ze)
 for f in fracs:rv.append((f*x,y,zc+(ze-zc)*abs(f)**2.5))
for j in range(65):
 for i in range(40):k=j*41+i;rf.append((k,k+1,k+42,k+41))
mesh('Roof | traced long soft crown',rv,rf,paint,cab,.019,True)
def screenpos(u,t,rear=False):
 ly,lzc,hy,hzc=(1.63,1.1425,.9175,1.5325) if rear else (-.82,1.0825,-.295,1.575)
 ze=smooth(hy,roofedges);lx=width(ly,belt(ly));hx=cw(hy,ze)
 zl=lzc+(belt(ly)-lzc)*abs(u)**2.5;zh=hzc+(ze-hzc)*abs(u)**2.5
 return (u*(lx*(1-t)+hx*t),ly+(hy-ly)*t, zl+(zh-zl)*t+.008*math.sin(math.pi*t)*(1-u*u))
for rear in [False,True]:
 border=[(f,0) for f in fracs]+[(f,1) for f in reversed(fracs)];outer=[screenpos(f,t,rear) for f,t in border];inn=[screenpos(f*.957,.065+t*.87,rear) for f,t in border];small=[screenpos(f*.944,.076+t*.848,rear) for f,t in border];label='Rear screen' if rear else 'Windscreen'
 ring3(label+' | body frame',outer,inn,paint,cab,.014);ring3(label+' | weather seal',inn,small,black,cab,.007)
 vv=[];ff=[]
 for j in range(15):
  for i in range(31):vv.append(screenpos(-.944+1.888*i/30,.076+.848*j/14,rear))
 for j in range(14):
  for i in range(30):k=j*31+i;ff.append((k,k+1,k+32,k+31))
 mesh(label+' | curved pane',vv,ff,glass,cab,.005,True)

# Rounded fascia caps wrap rearward into the fenders. Shared holes and returns.
holes={False:[],True:[]}
def cap_y(x,z,rear=False):
 base=back if rear else front_edge(z);w=width(base,z);t=min(1,abs(x)/w)
 if rear:
  centre=smooth(z,[(.24,2.05),(.32,2.18),(.45,2.23),(.67,2.237),(.76,2.19),(.98,2.10),(1.12,2.08)])
 else:centre=base-.13
 return centre+(base-centre)*t**3
@lru_cache(maxsize=32768)
def topcap(x,rear=False):
 if rear:return surface_z(back,min(1,abs(x)/width(back,belt(back))),bootrows)
 lo=.7;hi=1.1
 for _ in range(25):
  z=(lo+hi)/2;y=cap_y(x,z);f=min(1,abs(x)/width(y,belt(y)))
  if z<surface_z(y,f,hoodrows):lo=z
  else:hi=z
 return (lo+hi)/2
def inset(name,poly,rear,m,depth=.033):
 holes[rear].append(poly);sg=1 if rear else -1;cx=sum(x for x,z in poly)/len(poly);cz=sum(z for x,z in poly)/len(poly);inn=[(cx+(x-cx)*.94,cz+(z-cz)*.94) for x,z in poly]
 outer=[(x,cap_y(x,z,rear)+sg*.002,z) for x,z in poly];ip=[(x,cap_y(x,z,rear)-sg*depth,z) for x,z in inn];N=len(poly)
 mesh(name+' | fitted opening return',outer+ip,[(i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N)],black,trim,.008,True)
 centre=(cx,cap_y(cx,cz,rear)-sg*depth,cz)
 mesh(name+' | recessed cassette',[centre]+ip,[(0,i+1,(i+1)%N+1) for i in range(N)],m,trim,.007,True)
 return ip
for s in [-1,1]:
 poly=rounded([(s*x,z) for x,z in [(.475,.660),(.447,.706),(.463,.830),(.512,.906),(.617,.925),(.724,.87),(.756,.737),(.718,.663)]],.03,4)
 inset('Blobeye '+str(s),poly,False,silver,.018)
 for xx,z,r,mm in [(.539,.716,.058,white),(.672,.719,.055,white),(.594,.846,.037,amber)]:
  x=s*xx;y=cap_y(x,z)-.006;normal=Vector(((cap_y(x+.001,z)-cap_y(x-.001,z))/.002,-1,(cap_y(x,z+.001)-cap_y(x,z-.001))/.002)).normalized();base=Vector((x,y,z))
  rod('Headlight | reflector',base-normal*.013,base+normal*.006,r,black,N=32);rod('Headlight | lens',base+normal*.007,base+normal*.014,r*.78,mm,N=32)
 pp=rounded([(s*x,z) for x,z in [(.49,.762),(.445,.987),(.607,1.048),(.749,.985),(.773,.792),(.699,.750)]],.028,4)
 inset('Tail lamp '+str(s),pp,True,redlens,.006)
 band=[(s*x,z) for x,z in [(.485,.932),(.478,.980),(.604,1.015),(.727,.967),(.735,.917)]];mesh('Tail lamp | cream band',[(x,cap_y(x,z,True)+.003,z) for x,z in band],[tuple(range(len(band)))],white,trim,.006)
inset('Upper grille',rr(0,.827,.83,.115,.024),False,dial,.045)
inset('Lower intake',rr(0,.474,.91,.22,.022),False,dial,.06)
for s in [-1,1]:inset('Bumper corner intake',rr(s*.632,.438,.235,.203,.018),False,dial,.035)
inset('Rear registration recess',rr(0,.584,.67,.172,.022),True,black,.025)
for rear in [False,True]:
 base=back if rear else front;vv=[];ff=[];xs=[-1.005+i*.015 for i in range(135)];zzs=sorted(set([.255+i*.015 for i in range(58)]+[z for pp in holes[rear] for x,z in pp]))
 for xa,xb in zip(xs,xs[1:]):
  for za,zb in zip(zzs,zzs[1:]):
   pp=[(xa,za),(xb,za),(xb,zb),(xa,zb)]
   for fn in [lambda x,z:width(back if rear else front_edge(z),z)-x,lambda x,z:width(back if rear else front_edge(z),z)+x,lambda x,z:topcap(x,rear)-z]:pp=clip(pp,fn) if len(pp)>2 else []
   pieces=[pp] if len(pp)>2 else []
   for hole in holes[rear]:pieces=[q for p0 in pieces for q in subtract_convex(p0,hole)]
   for pp in pieces:
    if len(pp)>2:k=len(vv);vv.extend((x,cap_y(x,z,rear),z) for x,z in pp);ff.append(tuple(range(k,len(vv))))
 mesh(('Rear' if rear else 'Front')+' | wrapped sculpted bumper',vv,ff,paint,body,.016,True)

# Trim the leading bonnet to the same cap surface, preventing paint across optics.
vv=[];ff=[]
for face in hood.data.polygons:
 q=[tuple(hood.data.vertices[i].co) for i in face.vertices];q=clip(q,lambda x,y,z:y-cap_y(x,z))
 if len(q)>2:n=len(vv);vv.extend(q);ff.append(tuple(range(n,len(vv))))
name=hood.name;bpy.data.objects.remove(hood,do_unlink=True);hood=mesh(name,vv,ff,paint,body,.014,True)

# Reuse only revolved wheel construction in its local component frame.
savedS=S;S={'axles':axles,'track':track,'axle_z':wheelz};a.stage='full'
wheelcode=old[old.index('tyreprofile='):old.index('# Fascia apertures')]
wheelcode=wheelcode.replace('range(48):','range(32):').replace('range(4):','range(3):').replace('/48;xx=-.082+lane*.0545','/32;xx=-.070+lane*.070').replace('[-.022,.022]','[-.029,.029]').replace('[-.047,.047]','[-.072,.072]').replace('[0,.009]','[0,.012]')
exec(wheelcode)
for cy in axles:
 for s in [-1,1]:rod('Wheel | dark centre cap',(s*(track/2+.113),cy,wheelz),(s*(track/2+.122),cy,wheelz),.039,black,wheelcol,24)
S=savedS

# Closed shaped pan and dedicated suspension envelopes.
def floorwidth(y):return .51 if any(ar[0][0]<y<ar[-1][0] for ar in arches) else width(y,.30)-.007
fys=sorted(set([front+.12,back-.05]+[front+.12+i*(back-front-.17)/190 for i in range(191)]+[y+d for ar in arches for y in [ar[0][0],ar[-1][0]] for d in [-.001,.001]]));vv=[];ff=[]
for y in fys:vv.extend([(-floorwidth(y),y,.304),(floorwidth(y),y,.304)])
for i in range(len(fys)-1):k=i*2;ff.append((k,k+1,k+3,k+2))
mesh('Floor | full fitted pan',vv,ff,floor_mat,lin,.023)
for y in axles:
 rod('Chassis | axle',(-.76,y,wheelz),(.76,y,wheelz),.035,black,lin)
 box('Chassis | differential',(0,y,wheelz),(.19,.20,.13),black,lin,.04)
for s in [-1,1]:box('Chassis | inner longitudinal rail',(s*.40,.08,.245),(.06,3.62,.085),black,lin,.012)

# All decoration and fitted details are omitted in the independent form render.
if not a.shape:
 for s in [-1,1]:
  sn='L' if s>0 else 'R'
  # Wraparound tail-light section: cut its side-panel opening, then fit a cassette.
  tailpoly=rounded([yz(p) for p in [(1621,356),(1694,357),(1728,377),(1728,437),(1699,450),(1648,438)]],.025,4)
  quarter=bpy.data.objects[sn+' | rear quarter'];qv=[];qf=[]
  for face in quarter.data.polygons:
   pp=[(quarter.data.vertices[i].co.y,quarter.data.vertices[i].co.z) for i in face.vertices]
   for q in subtract_convex(pp,tailpoly):
    if len(q)>2:n=len(qv);qv.extend(sidepos(y,z,s) for y,z in q);qf.append(tuple(range(n,len(qv))))
  qname=quarter.name;bpy.data.objects.remove(quarter,do_unlink=True);mesh(qname,qv,qf,paint,body,.012,True)
  cy=sum(y for y,z in tailpoly)/len(tailpoly);cz=sum(z for y,z in tailpoly)/len(tailpoly);ti=[(cy+(y-cy)*.96,cz+(z-cz)*.94) for y,z in tailpoly]
  ring3(sn+' | tail lamp side seal',[sidepos(y,z,s,.001) for y,z in tailpoly],[sidepos(y,z,s,-.004) for y,z in ti],black,trim,.007)
  vs=[sidepos(cy,cz,s,.001)]+[sidepos(y,z,s,.001) for y,z in ti];mesh(sn+' | tail lamp wrapped side lens',vs,[(0,i+1,(i+1)%len(ti)+1) for i in range(len(ti))],redlens,trim,.008,True)
  pp=[yz(p) for p in [(1634,366),(1688,367),(1717,383),(1717,400),(1646,390)]];mesh(sn+' | tail lamp side cream band',[sidepos(y,z,s,.005) for y,z in pp],[tuple(range(len(pp)))],white,trim,.004,True)
  for y in [.04,.90]:
   z=1.01;box(sn+' | handle recess',(s*(width(y,z)+.003),y,z),(.013,.185,.05),black,b=.018);box(sn+' | door grip',(s*(width(y,z)+.015),y,z+.008),(.035,.155,.027),paint,b=.011)
  # Short triangular mirror foot supports a rounded housing.
  yy=-.665;zz=1.06;rod(sn+' | mirror base',(s*.81,yy,zz),(s*.937,yy-.025,zz+.025),.029,black);box(sn+' | mirror housing',(s*.949,yy-.033,zz+.069),(.155,.205,.133),black,b=.044);box(sn+' | mirror glass',(s*.948,yy+.071,zz+.071),(.123,.005,.099),silver,b=.028)
  gp=[yz(p) for p in [(568,598),(965,506),(953,556),(870,600)]];gp2=[yz(p) for p in [(1003,497),(1221,467),(1137,557),(990,574)]]
  for j,pp in enumerate([gp,gp2]):
   vv=[];ff=[]
   # tessellate decal into surface-conforming columns instead of a flat hovering polygon
   for k in range(70):
    ya=min(y for y,z in pp)+k*(max(y for y,z in pp)-min(y for y,z in pp))/70;yb=ya+(max(y for y,z in pp)-min(y for y,z in pp))/70
    for kk in range(24):
     za=min(z for y,z in pp)+kk*(max(z for y,z in pp)-min(z for y,z in pp))/24;zb=za+(max(z for y,z in pp)-min(z for y,z in pp))/24;q=clip(clip(clip(clip(pp,lambda y,z:y-ya),lambda y,z:yb-y),lambda y,z:z-za),lambda y,z:zb-z)
     if len(q)>2:n=len(vv);vv.extend(sidepos(y,z,s,.0025) for y,z in q);ff.append(tuple(range(n,len(vv))))
   mesh(sn+f' | cream graphic {j}',vv,ff,cream,trim)
  for j,ar in enumerate(arches):
   y=ar[-1][0]-.026;top=.50;box(sn+f' | mudflap hanger {j}',(s*.81,y,top),(.265,.036,.05),black,rally,.004);box(sn+f' | mudflap clamp {j}',(s*.81,y+.026,top-.013),(.258,.016,.026),silver,rally,.003)
   # tilted back below mount, rather than disconnected vertical boards
   poly=[(y+.012,top),(y+.035,top),(y+.079,.138),(y+.052,.138)];bevel(prism(sn+f' | fitted red mudflap {j}',poly,0,s*.81-.132,s*.81+.132,red,rally),.006,2)
   box(sn+f' | mudflap body anchor {j}',(s*.77,y-.014,.524),(.21,.065,.075),black,rally,.009)
   for dx in [-.093,.093]:rod('Flap | bolt',(s*.81+dx,y+.035,top-.008),(s*.81+dx,y+.042,top-.008),.007,black,rally,8)
 # Open scoops with formed shells fitted to the current crown.
 def scoop(name,y0,y1,w,h,roof=False):
  rows=roofrows if roof else hoodrows
  def z(y,x):
   if roof:return smooth(y,roofrows)+(smooth(y,roofedges)-smooth(y,roofrows))*(abs(x)/.66)**2.5
   return surface_z(y,abs(x)/width(y,belt(y)),rows)
  vs=[(x,y,z(y,x)+dz) for x,y,dz in [(-w,y0,0),(w,y0,0),(w*.88,y1,0),(-w*.88,y1,0),(-w*.86,y0+.01,h),(w*.86,y0+.01,h),(w*.78,y1-.035,h*.52),(-w*.78,y1-.035,h*.52)]]
  bevel(mesh(name+' | formed shell',vs,[(0,4,7,3),(1,2,6,5),(4,5,6,7),(3,7,6,2)],paint,rally,.014,True),.007,3)
  base=z(y0,0);mesh(name+' | dark open throat',[(-w*.86,y0+.021,base+.005),(w*.86,y0+.021,base+.005),(w*.81,y0+.021,base+h-.012),(-w*.81,y0+.021,base+h-.012)],[(0,1,2,3)],dial,rally,.007)
  box(name+' | lower lip',(0,y0+.007,base+.003),(w*1.91,.032,.023),paint,rally,.01)
 scoop('Bonnet scoop',-1.435,-1.098,.265,.095);scoop('Roof vent',.07,.409,.17,.085,True)
 # Genuine vent openings with inset beds, all conforming to bonnet curvature.
 ventholes=[[(s*.49,-1.47),(s*.63,-1.47),(s*.63,-1.26),(s*.49,-1.26)] for s in [-1,1]]
 hv=[];hf=[]
 for face in hood.data.polygons:
  pp=[tuple(hood.data.vertices[i].co)[:2] for i in face.vertices];pieces=[pp]
  for hole in ventholes:pieces=[q for p0 in pieces for q in subtract_convex(p0,hole)]
  for q in pieces:
   if len(q)>2:n=len(hv);hv.extend((x,y,surface_z(y,abs(x)/width(y,belt(y)),hoodrows)) for x,y in q);hf.append(tuple(range(n,len(hv))))
 hname=hood.name;bpy.data.objects.remove(hood,do_unlink=True);hood=mesh(hname,hv,hf,paint,body,.014,True)
 for s in [-1,1]:
  pp=[(s*.49,-1.47),(s*.63,-1.47),(s*.63,-1.26),(s*.49,-1.26)];vp=[];vf=[]
  for j in range(17):
   y=-1.47+j*.21/16
   for i in range(7):x=s*(.49+i*.14/6);vp.append((x,y,surface_z(y,abs(x)/width(y,belt(y)),hoodrows)-.016))
  for j in range(16):
   for i in range(6):k=j*7+i;vf.append((k,k+1,k+8,k+7))
  mesh('Bonnet vent | recessed bed',vp,vf,black,rally,.004,True)
  outer=[(x,y,surface_z(y,abs(x)/width(y,belt(y)),hoodrows)) for x,y in pp];inner=[(x,y,z-.017) for x,y,z in outer];ring3('Bonnet vent | fitted return',outer,inner,black,rally,.004)
  for y in [-1.43,-1.395,-1.36,-1.325]:curve('Bonnet vent | recessed louvre',[(x,y,surface_z(y,abs(x)/width(y,belt(y)),hoodrows)-.006) for x in [s*(.495+i*.13/10) for i in range(11)]],.003,black,rally)
 # Rear aerofoil and shaped uprights match side-profile wing silhouette.
 for s in [-1,1]:
  pp=[yz(p) for p in [(1590,303),(1654,300),(1780,177),(1649,184)]]
  pp[:2]=[(y,surface_z(y,.68/width(y,belt(y)),bootrows)+.010) for y,z in pp[:2]]
  bevel(prism('Wing | swept upright',pp,0,s*.68-.025,s*.68+.025,paint,rally),.01,3)
  box('Wing | deck foot',(s*.68,1.83,surface_z(1.83,.68/width(1.83,belt(1.83)),bootrows)+.009),(.095,.25,.039),paint,rally,.013)
 box('Wing | rounded cross aerofoil',(0,2.086,1.435),(1.445,.28,.053),paint,rally,.022)
 # Rally light cluster: simplified octagonal shells and rounded inset lenses.
 box('Rally pod | carrier',(0,-2.090,.651),(1.255,.081,.071),black,rally,.011)
 for x in [-.43,.43]:box('Rally pod | body mounts',(x,-2.00,.661),(.065,.22,.065),black,rally,.009)
 for x in [-.444,-.148,.148,.444]:
  rod('Rally lamp | housing',(x,-1.975,.79),(x,-2.080,.79),.137,black,rally,8)
  rod('Rally lamp | bezel',(x,-2.081,.79),(x,-2.094,.79),.112,silver,rally,12)
  rod('Rally lamp | lens',(x,-2.095,.79),(x,-2.100,.79),.097,cream,rally,12)
  box('Rally lamp | foot',(x,-2.075,.662),(.052,.059,.055),black,rally,.008)
 for y,rear in [(-2.145,False),(2.277,True)]:
  sg=1 if rear else -1;z=.40;vv=[(-.48,y,.272),(.48,y,.272),(.44,y,.493),(-.44,y,.493),(-.40,y-sg*.22,.229),(.40,y-sg*.22,.229)]
  if not rear:vv[0]=(-.48,y,.237);vv[1]=(.48,y,.237)
  guard=mesh(('Rear' if rear else 'Front')+' | folded skid guard',vv,[(0,1,2,3),(0,4,5,1)],silver,rally,.018)
  for x in [-.25,0,.25]:cut(guard,rr(x,.385,.062,.095,.007),1,y-.13,y+.13)
  for x in [-.32,.32]:box('Guard | fixed mounting tab',(x,y-sg*.15,.278),(.055,.20,.054),black,rally,.006)
 for rear in [False,True]:
  xx=.63 if rear else -.64;yy=2.253 if rear else -2.121;zz=.428
  curve('Tow loop | mounted',[(xx+dx,yy,zz+dz) for dx,dz in [(-.038,.035),(-.044,-.03),(-.033,-.08),(.032,-.08),(.046,-.03),(.04,.035)]],.014,red,rally)
  box('Tow loop | mounting eye',(xx,yy+(-.034 if rear else .034),zz+.022),(.07,.09,.046),black,rally,.009)
 for s in [-1,1]:
  for z in [.391,.449,.506]:box('Corner intake | louvre',(s*.632,cap_y(s*.632,z)-.004,z),(.205,.031,.013),black,b=.003)
 for z in [.421,.478,.535]:box('Lower grille | slat',(0,-2.048,z),(.88,.029,.012),black,b=.003)
 for x in [-.38,.34]:
  curve('Wiper | arm',[screenpos(x+.10,.09),screenpos(x-.11,.19),screenpos(x-.20,.215)],.007,black)
  curve('Wiper | blade',[screenpos(x-.38,.18),screenpos(x+.03,.18)],.010,black)
 # Hollow exhaust tip follows the tucked bumper.
 revolve('Exhaust | rolled open tip',[(0,.066),(.18,.070),(.19,.065),(.19,.054),(0,.054)],0,0,0,1,silver,lin,N=32)
 ob=bpy.data.objects['Exhaust | rolled open tip'];ob.rotation_euler.z=math.pi/2;ob.location=(-.60,2.045,.287)
 curve('Exhaust | pipe',[(-.6,1.55,.24),(-.60,1.93,.26),(-.60,2.08,.287)],.038,silver,lin)
 # Fitted cabin; seats avoid occupied rear wheelhouse and remain above full pan.
 for rear in [False,True]:
  for s in [-1,1]:
   x=s*(.26 if rear else .395);y=.65 if rear else -.17;w=.455 if rear else .48;n=('Rear' if rear else 'Front')+' seat '+str(s)
   for dx in [-.15,.15]:
    box(n+' | rail',(x+dx,y,.359),(.032,.40,.027),silver,inside,.006)
    for dy in [-.145,.145]:box(n+' | floor foot',(x+dx,y+dy,.330),(.048,.047,.057),black,inside,.005)
   box(n+' | cushion',(x,y,.442),(w,.46,.133),cloth,inside,.047)
   box(n+' | centre cushion',(x,y-.015,.507),(w*.64,.33,.018),insert,inside,.024)
   pp=[(y+.13,.43),(y+.24,.43),(y+.37,1.11),(y+.245,1.13)];bevel(prism(n+' | backrest',pp,0,x-w*.47,x+w*.47,cloth,inside),.04,4)
   for dx in [-.072,.072]:rod(n+' | headrest stem',(x+dx,y+.32,1.06),(x+dx,y+.32,1.20),.008,silver,inside)
   box(n+' | headrest',(x,y+.32,1.212),(.24,.115,.15),cloth,inside,.04)
 box('Cabin | parcel shelf',(0,1.33,.98),(1.42,.46,.024),cloth,inside,.01)
 box('Cabin | rear bulkhead',(0,1.13,.615),(1.02,.026,.60),black,inside,.007)
 box('Cabin | dashboard',(0,-.675,.979),(1.39,.33,.20),cloth,inside,.045)
 box('Cabin | console',(0,-.08,.447),(.22,.82,.25),black,inside,.038)
 box('Cabin | centre stack',(0,-.48,.823),(.27,.12,.28),black,inside,.025)
 for x in [-.55,-.11,.11,.55]:
  box('Dashboard | vent recess',(x,-.497,.99),(.145,.008,.069),black,inside,.015)
  for z in [.97,.99,1.01]:box('Dashboard | vent slat',(x,-.486,z),(.125,.012,.004),silver,inside,.001)
 for x in [-.07,0,.07]:rod('Dashboard | climate dial',(x,-.416,.80),(x,-.402,.80),.022,silver,inside)
 box('Dashboard | instrument pod',(-.395,-.51,1.073),(.36,.13,.16),black,inside,.028)
 for x,r in [(-.478,.054),(-.32,.049)]:
  rod('Instrument | rim',(x,-.444,1.08),(x,-.431,1.08),r,silver,inside,32);rod('Instrument | dial',(x,-.430,1.08),(x,-.426,1.08),r-.004,black,inside,32)
  for k in range(11):ang=math.radians(210-k*25);curve('Instrument | tick',[(x+math.cos(ang)*r*f,-.423,1.08+math.sin(ang)*r*f) for f in [.74,.89]],.001,white,inside)
  curve('Instrument | needle',[(x,-.421,1.08),(x+.02,-.421,1.10)],.0018,red,inside)
 wc=Vector((-.395,-.27,.94));wn=Vector((0,.92,.392)).normalized();wu=Vector((1,0,0));wv=wn.cross(wu)
 curve('Steering | padded rim',[tuple(wc+(wu*math.cos(i*math.tau/64)+wv*math.sin(i*math.tau/64))*.15) for i in range(65)],.013,black,inside)
 rod('Steering | column',(-.395,-.61,.82),wc,.022,black,inside)
 for ang in [0,math.pi,1.5*math.pi]:rod('Steering | spoke',wc,wc+(wu*math.cos(ang)+wv*math.sin(ang))*.14,.014,silver,inside)
 rod('Steering | boss',wc-wn*.024,wc+wn*.014,.046,black,inside)
 rod('Console | shifter',(0,-.24,.58),(0,-.22,.72),.009,silver,inside);box('Console | gear knob',(0,-.22,.733),(.047,.043,.055),black,inside,.02)
 for s in [-1,1]:
  for ya,yb in [(-.78,.19),(.25,1.12)]:
   panel_grid('Door | shaped inner card',[ya+(yb-ya)*i/45 for i in range(46)],[.32+i*.022 for i in range(32)],lambda y,z:(s*(width(y,z)-.055),y,z),[lambda y,z:z-max(.335,archz(y)+.045),lambda y,z:.99-z],cloth,inside,solid=.012)
   yy=(ya+yb)/2;box('Door | armrest',(s*(width(yy,.79)-.09),yy,.79),(.09,.31,.045),black,inside,.018)

# Control curves record the actual approved outline; hidden from presentation.
for ob in bpy.data.objects:
 if ob.type=='MESH' and len(ob.data.polygons)>100:
  for mod in ob.modifiers:
   if mod.type=='SOLIDIFY':mod.use_rim=False
for key in ['hood_centre_px','roof_crown_px','cabin_side_upper_px','front_glass_px','rear_glass_px','arch_front_px','arch_rear_px']:
 ob=curve('TRACE | '+key,[(1.05,y,z) for y,z in profile(key)],.002,cream,guides);ob.hide_render=True;ob.hide_set(True)
for f in ['01-four-view-sheet.png','02-side-profile.png']:
 im=bpy.data.images.load(str(src/f));im.pack();im.use_fake_user=True
ground=mat('Studio | ivory',(.71,.69,.64),.92);mesh('Studio ground',[(-100,-100,-.009),(100,-100,-.009),(100,100,-.009),(-100,100,-.009)],[(0,1,2,3)],ground,studio)
world=bpy.data.worlds.new('Neutral studio');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.72,.77,.85,1);world.node_tree.nodes['Background'].inputs[1].default_value=.55;sc.world=world
for n,loc,power,size in [('Key',(4,-4,6),1200,5),('Fill',(-4,-1,4),900,4),('Rim',(1,5,5),1250,4)]:
 d=bpy.data.lights.new(n,'AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new(n,d);studio.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,.8))-o.location).to_track_quat('-Z','Y').to_euler()
def cam(n,loc,target,scale,res):
 d=bpy.data.cameras.new(n);o=bpy.data.objects.new(n,d);cams.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();d.type='ORTHO';d.ortho_scale=scale;o['resolution']=res;return o
views={'side':cam('Review | side',(8,0,.90),(0,0,.90),4.85,(1700,790)),'quarter':cam('Review | front quarter',(5.8,-8,3.2),(0,0,.82),5.20,(1400,950)),'rear-quarter':cam('Review | rear quarter',(5.8,8,3.2),(0,0,.82),5.20,(1400,950)),'front':cam('Review | front',(0,-8,.86),(0,0,.86),2.40,(1050,1000)),'rear':cam('Review | rear',(0,8,.86),(0,0,.86),2.40,(1050,1000)),'top':cam('Review | top',(0,0,8),(0,0,0),4.90,(1000,1500)),'underside':cam('Review | underside',(3.5,4.5,-3),(0,0,.65),5.25,(1400,950))}
sc.render.engine='CYCLES';sc.cycles.samples=24;sc.cycles.use_denoising=True;sc.render.threads_mode='FIXED';sc.render.threads=12;sc.view_settings.view_transform='Standard';sc.view_settings.look='None';sc.view_settings.exposure=-.7;sc.render.image_settings.file_format='PNG';sc.render.resolution_percentage=100
sc['vehicle']=S['vehicle'];sc['shape_authority']=str(src/'02-side-profile.png');sc['scope']='Reference-led editable static vehicle. Shape is newly rebuilt. No inherited articulation or game-ready claims.'
readme=bpy.data.texts.new('START HERE');readme.write('Approved orthographic rebuild. Collections separate body panels, glazing, road wheels, rally equipment, cockpit and floor. Reference images are packed. Hidden TRACE curves preserve observed pixel profiles. Static authoring assembly; door animation and game export are not included. Previous rejected blend is untouched.\n')
for name in ['shape-controls.json','01-four-view-sheet.png','02-side-profile.png']:shutil.copy2(src/name,out/name)
shutil.copy2(Path(__file__),out/Path(__file__).name)
shutil.copy2(Path(__file__).with_name('build_impreza_gravel.py'),out/'build_impreza_gravel.py')
shutil.copy2(Path(__file__).with_name('verify_impreza_orthographic.py'),out/'verify_impreza_orthographic.py')
(out/'build-manifest.json').write_text(json.dumps({'authority':str(src/'02-side-profile.png'),'authority_sha256':hashlib.sha256((src/'02-side-profile.png').read_bytes()).hexdigest(),'spec':S,'shape_only':a.shape,'groups':groups,'scope':sc['scope']},indent=2))
sc.camera=views['quarter'];sc.render.resolution_x,sc.render.resolution_y=sc.camera['resolution']
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Impreza_Orthographic_Rebuild.blend'))
for key in a.render.split(','):
 if key not in views:continue
 sc.camera=views[key];sc.render.resolution_x,sc.render.resolution_y=sc.camera['resolution'];sc.render.filepath=str(out/(key+'.png'));bpy.data.objects['Studio ground'].hide_render=key=='underside';bpy.ops.render.render(write_still=True)
bpy.data.objects['Studio ground'].hide_render=False;sc.camera=views['quarter'];sc.render.resolution_x,sc.render.resolution_y=sc.camera['resolution']
for area in bpy.context.screen.areas:
 if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Impreza_Orthographic_Rebuild.blend'));print('REFERENCE_REBUILD_SAVED '+str(out),flush=True)
