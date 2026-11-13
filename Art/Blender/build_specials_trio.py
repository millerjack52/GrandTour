"""Three bespoke specials-inspired bodies. Shared construction tools, not stretched LC shells.
Blender 5.1 background CPU. Metres, front -Y, left +X. Versioned, non-destructive.
"""
import bpy,bmesh,math,json,ast,argparse,sys
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser();ap.add_argument('--car',required=True,choices=['KadettA','E39Touring','SJ413']);ap.add_argument('--version',default='R1');ap.add_argument('--views',default='front,rear,side,cockpit');ap.add_argument('--samples',type=int,default=24)
args=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);CAR=args.car
OUT=ROOT/'Art/Export/SpecialsTrio'/CAR/args.version;OUT.mkdir(parents=True,exist_ok=True)
SPECS={
 'KadettA':dict(wb=2.325,track=1.21,r=.285,tw=.145,w=.735,front=1.90,rear=-1.90,belt=.91,roof=1.385,sill=.285,fb=.62,ft=.22,rt=-.94,rb=-1.28,split=-.45,paint=(.40,.28,.115),roofpaint=(.60,.565,.45),drive=-1,doors=2),
 'E39Touring':dict(wb=2.83,track=1.52,r=.323,tw=.215,w=.90,front=2.32,rear=-2.35,belt=1.015,roof=1.455,sill=.27,fb=.70,ft=.03,rt=-1.98,rb=-2.35,split=-.46,rearsplit=-1.40,paint=(.030,.048,.083),roofpaint=(.030,.048,.083),drive=-1,doors=4),
 'SJ413':dict(wb=2.03,track=1.30,r=.345,tw=.205,w=.73,front=1.62,rear=-1.62,belt=1.035,roof=1.67,sill=.49,fb=.53,ft=.28,rt=-1.52,rb=-1.62,split=-.54,paint=(.29,.023,.015),roofpaint=(.29,.023,.015),drive=1,doors=2)
}
C=SPECS[CAR];W=C['w'];B=C['belt'];H=C['roof'];F=C['front'];R=C['rear'];WB=C['wb'];RAD=C['r'];TRACK=C['track'];GAP=.006
bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.unit_settings.system='METRIC'
COLS={};GROUP='Body';PARTS={}
tree=ast.parse((ROOT/'Art/Blender/build_landcruiser.py').read_text())
names={'col','move','P','mat','finish','mesh','box','rod','line','panel','label','loft'}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'vehicle_helpers','exec'))
paint=mat('GT_Paint',C['paint'],.40,.12);roofmat=mat('GT_Roof',C['roofpaint'],.43,.08)
rubber=mat('GT_Rubber',(.018,.023,.026),.8);trim=mat('GT_Trim',(.047,.054,.058),.56);dark=mat('GT_Recess',(.008,.012,.016),.66)
chrome=mat('GT_Chrome',(.48,.54,.57),.26,.75);steel=mat('GT_Steel',(.25,.30,.32),.40,.6);lamp=mat('GT_Lamp',(.63,.69,.65),.25,.3)
red=mat('GT_RedLens',(.36,.015,.009),.28);amber=mat('GT_AmberLens',(.69,.24,.012),.3)
cloth=mat('GT_Cloth',(.14,.09,.055) if CAR=='KadettA' else (.065,.075,.082),.89)
dash=mat('GT_Dash',(.044,.050,.052),.73);white=mat('GT_Markings',(.72,.70,.61),.61);orange=mat('GT_Needles',(.85,.22,.028),.5)
glass=mat('GT_Glass',(.68,.78,.80),.08);bs=glass.node_tree.nodes.get('Principled BSDF');bs.inputs['Transmission Weight'].default_value=.96;bs.inputs['IOR'].default_value=1.45
anchor=bpy.data.objects.new('PaintCoordinates',None);col('Reference').objects.link(anchor)
for ma in [paint,roofmat]:
 nt=ma.node_tree;n=nt.nodes.new('ShaderNodeTexNoise');n.inputs['Scale'].default_value=2.0;n.inputs['Detail'].default_value=0
 co=nt.nodes.new('ShaderNodeTexCoord');co.object=anchor;nt.links.new(co.outputs['Object'],n.inputs['Vector'])
 ramp=nt.nodes.new('ShaderNodeValToRGB');base=ma.diffuse_color[:3]
 ramp.color_ramp.elements[0].color=(*(v*.92 for v in base),1);ramp.color_ramp.elements[1].color=(*(v*1.06 for v in base),1)
 nt.links.new(n.outputs['Fac'],ramp.inputs[0]);nt.links.new(ramp.outputs[0],nt.nodes.get('Principled BSDF').inputs['Base Color'])
def interp(x,pts):
 for (a,b),(c,d) in zip(pts,pts[1:]):
  if x<=c:return b+(d-b)*max(0,(x-a)/(c-a))
 return pts[-1][1]
def width(u,z):
 profile=[(C['sill'],W-.045),(C['sill']+.08,W-.018),(B-.20,W),(B-.075,W),(B,W-.04)]
 end=.055*max(0,(u-(F-.30))/.30)**2+.030*max(0,((R+.25)-u)/.25)**2
 return interp(z,profile)-end
def top(u):
 return B-(.035 if CAR=='SJ413' else .10)*max(0,(u-C['fb'])/(F-C['fb']))
def bottom(u):
 z=C['sill'];ar=RAD+(.042 if CAR!='SJ413' else .065)
 for a in [-WB/2,WB/2]:
  if abs(u-a)<ar:z=max(z,RAD+math.sqrt(max(0,ar*ar-(u-a)**2)))
 return z
def skin(name,vs,fs,ma,thick=.012):
 o=mesh(name,vs,fs,ma,smooth=True)
 if thick:m=o.modifiers.new('Inward sheet thickness','SOLIDIFY');m.thickness=thick;m.offset=-1
 return o
def normals(o,s):
 ns=[];d=.001
 for ve in o.data.vertices:
  u,z=-ve.co.y,ve.co.z;ns.append(tuple(Vector((s,(width(u+d,z)-width(u-d,z))/(2*d),-(width(u,z+d)-width(u,z-d))/(2*d))).normalized()))
 o.data.normals_split_custom_set_from_vertices(ns)
def clip(poly,fn):
 out=[]
 for p,q in zip(poly,poly[1:]+poly[:1]):
  a,b=fn(p),fn(q)
  if a>=0:out.append(p)
  if (a>=0)!=(b>=0):t=a/(a-b);out.append((p[0]+t*(q[0]-p[0]),p[1]+t*(q[1]-p[1])))
 return out
def outline(poly,r=.025):
 out=[]
 for i,p in enumerate(poly):
  p=Vector(p);a=Vector(poly[i-1]);b=Vector(poly[(i+1)%len(poly)])
  start=p+(a-p).normalized()*min(r,(a-p).length*.15);end=p+(b-p).normalized()*min(r,(b-p).length*.15)
  for k in range(4):t=k/3;out.append(tuple((1-t)**2*start+2*(1-t)*t*p+t*t*end))
 return out
def window(name,outer,project,ma=paint):
 # Frame, seal and pane share boundary loops: no solid body behind the glass.
 a=outline(outer,.018);centre=sum((Vector(v) for v in a),Vector((0,0)))/len(a)
 b=[tuple(centre+(Vector(v)-centre)*.91) for v in a];c=[tuple(centre+(Vector(v)-centre)*.98) for v in b];n=len(a)
 frame=skin(name+'_Frame',[project(v,0) for v in a]+[project(v,0) for v in b],[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],ma,.010)
 for f in frame.data.polygons:f.use_smooth=False
 skin(name+'_Seal',[project(v,0) for v in b]+[project(v,-.003) for v in c],[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],rubber,.006)
 panel(name+'_Glass',[project(v,-.005) for v in c],glass,.003,0)
 return b
zones=[('Wing',C['fb']+GAP,F,'Body'),('FrontDoor',C['split']+GAP,C['fb'],'Door_F')]
if C['doors']==4:zones += [('RearDoor',C['rearsplit']+GAP,C['split'],'Door_R'),('Quarter',R,C['rearsplit'],'Body')]
else:zones += [('Quarter',R,C['split'],'Body')]
pivots={};ar=RAD+(.042 if CAR!='SJ413' else .065)
for s,side in [(1,'L'),(-1,'R')]:
 for name,lo,hi,g in zones:
  GROUP=g+side if g.startswith('Door') else g
  us={lo,hi};us.update(u for u in [i*.08 for i in range(-35,36)]+[a+ar*math.cos(math.pi*k/24) for a in [-WB/2,WB/2] for k in range(25)] if lo<u<hi)
  us=sorted(us);vs=[];fs=[];rows=sorted({C['sill'],C['sill']+.08,B-.20,B-.075,B,B+.06})
  for a,b in zip(us,us[1:]):
   for z0,z1 in zip(rows,rows[1:]):
    poly=clip([(a,z0),(b,z0),(b,z1),(a,z1)],lambda p:p[1]-interp(p[0],[(a,bottom(a)),(b,bottom(b))]))
    if not poly:continue
    poly=clip(poly,lambda p:interp(p[0],[(a,top(a)),(b,top(b))])-p[1])
    if len(poly)<3:continue
    n=len(vs);vs.extend((u,s*width(u,z),z) for u,z in poly);fs.append(tuple(range(n,len(vs))))
  o=skin(name+'Skin_'+side,vs,fs,paint);normals(o,s)
  if g.startswith('Door'):
   pivots[GROUP]=(hi,s*width(hi,B-.06),B-.06)
   u=lo+.16;z=B-.09
   box('HandleRecess_'+GROUP,(u,s*(width(u,z)+.004),z),(.12,.009,.035),dark,.007,2)
   box('Handle_'+GROUP,(u,s*(width(u,z)+.013),z+.006),(.10,.020,.018),chrome if CAR=='KadettA' else trim,.005,2)
   box('DoorCard_'+GROUP,((lo+hi)/2,s*(W-.072),B-.18),(hi-lo-.055,.02,.31),cloth,.012,2)
   box('Armrest_'+GROUP,((lo+hi)/2,s*(W-.11),B-.22),(.29,.065,.04),trim,.014,2)
  if CAR!='SJ413':
   zz=B-.12 if CAR=='KadettA' else B-.25
   # End trim before any wheel opening.
   pts=[(u,s*(width(u,zz)+.007),zz) for u in us if bottom(u)<zz-.02]
   if len(pts)>1 and all(bottom(u)<zz-.02 for u in us):line('SideStrip_'+name+side,pts,.005 if CAR=='KadettA' else .012,chrome if CAR=='KadettA' else trim)
 GROUP='Body'
 # Wheel lip follows the actual cut-out; broad SJ arches taper back to the skin.
 for a,tag in [(WB/2,'F'),(-WB/2,'R')]:
  vs=[]
  for k in range(25):
   angle=math.pi*k/24
   for rr,off in [(ar,.004),(ar+.013,.023 if CAR=='SJ413' else .009),(ar+.045,.002)]:
    u=a+rr*math.cos(angle);z=RAD+rr*math.sin(angle);vs.append((u,s*(width(u,z)+off),z))
  # Split the rear lip at the movable rear door's exact boundary.
  faces=[(k*3+j,k*3+j+1,(k+1)*3+j+1,(k+1)*3+j) for k in range(24) for j in range(2)]
  if C['doors']==4 and tag=='R':
   for isdoor in [False,True]:
    cut=C['rearsplit']+(GAP if isdoor else 0);vv=[];ff=[];GROUP='Door_R'+side if isdoor else 'Body'
    for face in faces:
     poly=[(vs[i][0],vs[i][2]) for i in face];poly=clip(poly,lambda p:(p[0]-cut)*(1 if isdoor else -1))
     if len(poly)<3:continue
     n=len(vv)
     for u,z in poly:
      rad=math.hypot(u-a,z-RAD);off=interp(rad,[(ar,.004),(ar+.013,.009),(ar+.045,.002)])
      vv.append((u,s*(width(u,z)+off),z))
     ff.append(tuple(range(n,len(vv))))
    skin('ArchLip_'+tag+side+str(isdoor),vv,ff,paint,.005)
   GROUP='Body'
  else:skin('ArchLip_'+tag+side,vs,faces,paint,.005)
  vs=[(a+ar*math.cos(math.pi*k/24),s*v,RAD+ar*math.sin(math.pi*k/24)) for k in range(25) for v in [W-.26,W-.03]]
  skin('WheelWell_'+tag+side,vs,[(k*2,k*2+2,k*2+3,k*2+1) for k in range(24)],dark,.005)
 # Glazing outer borders align with side skins and cabin roof perimeter.
 def project(p,off=0):
  u,z=p;return(u,s*(W-.040-(z-B)*(.12 if CAR=='SJ413' else .19)+off),z)
 cabin=[('FrontWindow',[(C['fb'],B+.004),(C['split']+GAP,B+.004),(C['split']+GAP,H-.044),(C['ft'],H-.044)],'Door_F'+side)]
 if C['doors']==4:
  cabin += [('RearWindow',[(C['split'],B+.004),(C['rearsplit']+GAP,B+.004),(C['rearsplit']+GAP,H-.044),(C['split'],H-.044)],'Door_R'+side),('QuarterWindow',[(C['rearsplit'],B+.004),(C['rb'],B+.004),(C['rt'],H-.044),(C['rearsplit'],H-.044)],'Body')]
 else:cabin += [('QuarterWindow',[(C['split'],B+.004),(C['rb'],B+.004),(C['rt'],H-.044),(C['split'],H-.044)],'Body')]
 for name,poly,g in cabin:
  if CAR=='E39Touring' and name=='QuarterWindow':
   poly=[(C['rearsplit'],B+.004),(C['rb']+.10,B+.004),(C['rb']+.16,B+.105),(C['rt'],H-.044),(C['rearsplit'],H-.044)]
  GROUP=g;window(name+'_'+side,poly,project,roofmat if CAR=='KadettA' else trim if CAR=='E39Touring' else paint)
 GROUP='Door_F'+side
 mirror_u=C['fb']-.08;mirror_z=B+.085
 if CAR=='KadettA':
  rod('MirrorStem_'+side,(mirror_u,s*(W-.04),mirror_z-.03),(mirror_u,s*(W+.065),mirror_z+.05),.009,chrome,8)
  rod('MirrorBack_'+side,(mirror_u,s*(W+.075),mirror_z+.052),(mirror_u-.018,s*(W+.075),mirror_z+.052),.045,chrome,20)
  rod('MirrorGlass_'+side,(mirror_u-.020,s*(W+.075),mirror_z+.052),(mirror_u-.023,s*(W+.075),mirror_z+.052),.038,chrome,20)
 else:
  rod('MirrorStem_'+side,(mirror_u,s*(W-.03),mirror_z),(mirror_u-.01,s*(W+.07),mirror_z),.016,trim,8)
  box('MirrorHousing_'+side,(mirror_u-.02,s*(W+.105),mirror_z+.02),(.11,.145,.11),paint if CAR=='E39Touring' else trim,.025,3)
  box('MirrorGlass_'+side,(mirror_u-.078,s*(W+.105),mirror_z+.02),(.004,.115,.083),chrome,.004,2)
 if CAR=='SJ413':
  for zz in [B-.1,B-.41]:box('DoorHinge_'+side+str(zz),(C['fb']-.035,s*(W-.015),zz),(.10,.021,.04),paint,.006,2)
GROUP='Hood';pivots['Hood']=(C['fb']+.01,0,B)
loft('Bonnet',[(u,width(u,top(u))-.008,top(u)-.002,top(u)+rise) for u,rise in [(C['fb']+.012,.026),((C['fb']+F)/2,.036),(F-.12,.031),(F,.008)]],paint)
GROUP='Body';loft('Scuttle',[(C['fb']-.06,W-.048,B+.003,B+.024),(C['fb']+.006,W-.047,B+.003,B+.024)],paint)
rw=W-.040-(H-.044-B)*(.12 if CAR=='SJ413' else .19)
loft('Roof',[(C['rt']-.012,rw-.008,H-.043,H-.021),(C['rt']+.05,rw+.004,H-.02,H),(C['ft']-.045,rw+.004,H-.02,H),(C['ft']+.006,rw-.005,H-.043,H-.021)],roofmat)
def frontproj(p,off=0):
 v,z=p;return (interp(z,[(B,C['fb']),(H-.044,C['ft'])])+off,v,z)
window('Windscreen',[(-W+.04,B+.003),(W-.04,B+.003),(rw,H-.044),(-rw,H-.044)],frontproj,roofmat if CAR=='KadettA' else paint)
for s in [-1,1]:
 pts=[frontproj((s*.16,B+.07),.010),frontproj((s*(W-.15),B+.07),.010)];line('Wiper'+str(s),pts,.006,rubber)
if CAR=='KadettA':GROUP='Body'
else:GROUP='Tailgate'
def rearproj(p,off=0):
 v,z=p;return(interp(z,[(B,C['rb']),(H-.044,C['rt'])])-off,v,z)
window('RearWindow',[(-W+.04,B+.003),(W-.04,B+.003),(rw,H-.044),(-rw,H-.044)],rearproj,roofmat if CAR=='KadettA' else paint)
if CAR=='KadettA':
 GROUP='Trunk';pivots['Trunk']=(C['rb']-.01,0,B)
 loft('BootLid',[(R,W-.078,B-.018,B+.008),(R+.12,W-.050,B-.008,B+.028),(C['rb']-.008,W-.047,B-.001,B+.028)],paint)
else:pivots['Tailgate']=(R,-W+.045,B) if CAR=='SJ413' else (C['rt'],0,H-.044)
# Fitted front and rear closure sheets. Details sit ahead, never coplanar.
for front in [True,False]:
 GROUP='Body' if front or CAR=='KadettA' else 'Tailgate';u=F if front else R;sg=1 if front else -1
 ztop=top(u)-.003 if front else B-.008;zbot=C['sill']+.025
 vs=[(u+sg*.004,t*width(u,z),z) for t in [-1,-.94,-.7,0,.7,.94,1] for z in [zbot,ztop]]
 o=skin(('Front' if front else 'Rear')+'Closure',vs,[(k*2,k*2+1,k*2+3,k*2+2) for k in range(6)],paint,.012)
 for f in o.data.polygons:f.use_smooth=False
 GROUP='Body';bz=C['sill']+(.25 if CAR=='E39Touring' else .12)
 # One wrapped bumper shell: continuous corner returns, no overlapping end cubes.
 bh=.075 if CAR=='KadettA' else .145;vs=[];fractions=[-1,-.98,-.94,-.86,-.64,0,.64,.86,.94,.98,1]
 for t in fractions:
  centeru=u+sg*(.040-.155*abs(t)**9)
  for du,dz in [(-.052,-bh*.5),(.032,-bh*.5),(.069,-bh*.28),(.069,bh*.28),(.032,bh*.5),(-.052,bh*.5)]:vs.append((centeru+sg*du,t*(W+.014),bz+dz))
 fs=[(i*6+j,i*6+(j+1)%6,(i+1)*6+(j+1)%6,(i+1)*6+j) for i in range(len(fractions)-1) for j in range(6)]+[tuple(range(5,-1,-1)),tuple(range((len(fractions)-1)*6,len(fractions)*6))]
 bumper=mesh(('Front' if front else 'Rear')+'Bumper',vs,fs,chrome if CAR=='KadettA' else trim,smooth=True)
 mod=bumper.modifiers.new('Controlled bumper normals','WEIGHTED_NORMAL');mod.keep_sharp=True
 if CAR=='E39Touring':
  box(('Front' if front else 'Rear')+'BumperSkirt',(u+sg*.024,0,bz-.12),(.14,2*W-.04,.12),paint,.022,3)
  box(('Front' if front else 'Rear')+'BumperUpper',(u+sg*.020,0,bz+.096),(.15,2*W-.025,.071),paint,.018,3)
 if front and CAR=='E39Touring':
  box('LowerAirIntake',(F+.107,0,bz-.060),(.025,.91,.073),dark,.009,2)
  for v in [-.30,-.15,0,.15,.30]:box('IntakeRib'+str(v),(F+.123,v,bz-.060),(.012,.009,.059),trim,.002)
 if CAR=='KadettA':
  for s in [-1,1]:box(('Front' if front else 'Rear')+'BumperOverrider'+str(s),(u+sg*.109,s*.43,bz+.015),(.043,.035,.13),chrome,.011,3)
 if not front:
  GROUP='Body' if CAR=='KadettA' else 'Tailgate';platez=B-.19
  box('RearPlateRecess',(R-.022,0,platez),(.014,.40,.14),dark,.009,2);box('RearPlate',(R-.032,0,platez),(.004,.31,.089),white,.004)
  label('RearPlateText','GRAND TOUR',(R-.036,0,platez),.022,dark,False)
  box('RearHandle',(R-.030,0,B-.068),(.025,.19,.025),chrome if CAR=='KadettA' else trim,.006,2)
GROUP='Body'
if CAR=='E39Touring':
 # Twin recessed kidney apertures and pre-facelift twin lamp units.
 for s in [-1,1]:
  box('KidneyRim'+str(s),(F+.017,s*.125,B-.215),(.026,.213,.165),chrome,.027,3)
  box('KidneyDark'+str(s),(F+.032,s*.125,B-.215),(.008,.180,.133),dark,.021,3)
  for k in range(6):box('KidneySlat'+str(s)+str(k),(F+.040,s*.125+(k-2.5)*.026,B-.215),(.012,.008,.107),trim,.003,2)
  box('HeadlampSeat'+str(s),(F+.015,s*.549,B-.213),(.023,.45,.172),dark,.025,3)
  for v in [s*.445,s*.603]:
   rod('LampReflector'+str(v),(F+.029,v,B-.213),(F+.039,v,B-.213),.065,chrome,24)
   rod('LampLens'+str(v),(F+.040,v,B-.213),(F+.044,v,B-.213),.052,lamp,24)
  box('HeadlampIndicator'+str(s),(F+.029,s*.754,B-.213),(.02,.070,.147),amber,.014,2)
  box('FogRecess'+str(s),(F+.102,s*.64,C['sill']+.18),(.016,.18,.073),dark,.012,2)
  box('FogLens'+str(s),(F+.114,s*.64,C['sill']+.18),(.006,.106,.045),lamp,.007,2)
  line('RoofRail'+str(s),[(C['ft']-.19,s*(rw-.065),H+.032),(C['rt']+.2,s*(rw-.065),H+.032)],.017,trim)
  for u in [C['ft']-.2,C['rt']+.2]:rod('RailMount'+str(s)+str(u),(u,s*(rw-.065),H-.008),(u,s*(rw-.065),H+.035),.021,trim)
else:
 z=B-(.17 if CAR=='SJ413' else .22);half=.38 if CAR=='SJ413' else .43
 box('GrilleBorder',(F+.013,0,z),(.025,half*2,.20),trim if CAR=='SJ413' else chrome,.012,2)
 box('GrilleRecess',(F+.029,0,z),(.008,half*2-.025,.174),dark,.006)
 for k in range(6):box('GrilleSlat'+str(k),(F+.038,0,z+(k-2.5)*.027),(.014,half*2-.045,.005),trim if CAR=='SJ413' else chrome,.002)
 for s in [-1,1]:
  v=s*(W-.16);radius=.102 if CAR=='SJ413' else .104
  rod('HeadlightBezel'+str(s),(F+.012,v,z),(F+.037,v,z),radius,trim if CAR=='SJ413' else chrome,32)
  rod('HeadlightReflector'+str(s),(F+.038,v,z),(F+.046,v,z),radius*.84,chrome,32)
  rod('HeadlightLens'+str(s),(F+.047,v,z),(F+.053,v,z),radius*.72,lamp,32)
  for k in range(-3,4):
   vv=v+k*.018;hh=math.sqrt(max(0,(radius*.68)**2-(k*.018)**2));line('LensFlute'+str(s)+str(k),[(F+.054,vv,z-hh),(F+.054,vv,z+hh)],.0012,steel)
  box('FrontIndicator'+str(s),(F+.127,s*(W-.18),C['sill']+.12),(.009,.105,.043),amber,.006,2)
for s in [-1,1]:
 if CAR=='E39Touring':
  box('TailLampHousing'+str(s),(R-.009,s*(W-.17),B-.155),(.020,.274,.263),trim,.014,2)
  for zz,h,ma in [(B-.07,.070,amber),(B-.146,.055,lamp),(B-.225,.086,red)]:box('TailLamp'+str(s)+str(zz),(R-.019,s*(W-.17),zz),(.031,.25,h),ma,.012,2)
 else:
  box('TailLampHousing'+str(s),(R-.010,s*(W-.085),B-.151),(.020,.085,.245),chrome if CAR=='KadettA' else trim,.007,2)
  for zz,h,ma in [(B-.085,.055,amber),(B-.151,.065,red),(B-.219,.046,lamp)]:box('TailLamp'+str(s)+str(zz),(R-.020,s*(W-.085),zz),(.025,.068,h),ma,.005,2)
 box('SideMarker'+str(s),(WB/2-.25,s*(W+.004),B-.14),(.055,.012,.022),amber,.004)
GROUP='Body';plate_z=C['sill']+(.25 if CAR=='E39Touring' else .12);box('FrontPlate',(F+.126,0,plate_z),(.005,.30,.079),white,.003);label('FrontPlateText','GRAND TOUR',(F+.130,0,plate_z),.021,dark)
if CAR=='KadettA':
 rod('GrilleEmblem',(F+.047,0,B-.22),(F+.053,0,B-.22),.026,chrome,20)
 line('GrilleEmblemBar',[(F+.055,-.038,B-.226),(F+.055,.038,B-.214)],.003,chrome)
elif CAR=='E39Touring':
 rod('NoseBadge',(F+.009,0,B-.129),(F+.014,0,B-.129),.018,chrome,20)
 rod('NoseBadgeInsert',(F+.015,0,B-.129),(F+.017,0,B-.129),.014,paint,20)
GROUP='Body' if CAR=='KadettA' else 'Tailgate'
label('RearModelBadge',{'KadettA':'KADETT','E39Touring':'528i','SJ413':'SJ413'}[CAR],(R-.035,-W*.53,B-.25),.027,chrome,False)
# Wheels are closed lathed profiles with actual open spoke spaces.
def wheel(key,u,v,z):
 global GROUP
 GROUP='Wheel_'+key;s=1 if v>0 else -1;tw=C['tw'];rr=RAD*.60
 def lathe(name,profile,ma,n=32):
  vs=[(u+r*math.cos(math.tau*k/n),v+s*d,z+r*math.sin(math.tau*k/n)) for d,r in profile for k in range(n)]
  return mesh(name,vs,[(j*n+k,j*n+(k+1)%n,((j+1)%len(profile))*n+(k+1)%n,((j+1)%len(profile))*n+k) for j in range(len(profile)) for k in range(n)],ma,smooth=True)
 lathe('Tyre_'+key,[(-tw*.48,rr),(-tw*.5,RAD*.80),(-tw*.36,RAD*.98),(tw*.36,RAD*.98),(tw*.5,RAD*.80),(tw*.48,rr)],rubber)
 lathe('RimLip_'+key,[(-tw*.40,rr),(tw*.47,rr),(tw*.53,rr*.95),(tw*.47,rr*.88),(-tw*.40,rr*.88)],chrome if CAR=='KadettA' else steel)
 rod('Brake_'+key,(u,v+s*tw*.12,z),(u,v+s*tw*.17,z),rr*.86,dark,24)
 n=14 if CAR=='E39Touring' else 0
 for k in range(n):
  a=math.tau*k/n;rod('Spoke_'+key+str(k),(u+rr*.22*math.cos(a),v+s*tw*.41,z+rr*.22*math.sin(a)),(u+rr*.91*math.cos(a),v+s*tw*.46,z+rr*.91*math.sin(a)),.013 if CAR=='E39Touring' else .025,steel,6)
 if CAR in ['SJ413','KadettA']:
  disc=rod('SteelDish_'+key,(u,v+s*tw*.34,z),(u,v+s*tw*.43,z),rr*.94,steel,32)
  for k in range(8):
   a=math.tau*k/8;uu=u+rr*.72*math.cos(a);zz=z+rr*.72*math.sin(a)
   cut=rod('WheelHoleCutter',(uu,v+s*tw*.20,zz),(uu,v+s*tw*.55,zz),rr*.11,dark,10)
   mod=disc.modifiers.new('True steel wheel aperture','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cut;bpy.context.view_layer.objects.active=disc;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cut,do_unlink=True)
  mod=disc.modifiers.new('Stamped edge','BEVEL');mod.width=.001;mod.segments=1;disc.modifiers.new('Dish normals','WEIGHTED_NORMAL')
 rod('Hub_'+key,(u,v+s*tw*.38,z),(u,v+s*tw*.52,z),rr*(.66 if CAR=='KadettA' else .30),chrome if CAR=='KadettA' else steel,32)
 for k in range(0 if CAR=='KadettA' else 5):
  a=math.tau*k/5;rod('Lug_'+key+str(k),(u+rr*.18*math.cos(a),v+s*tw*.58,z+rr*.18*math.sin(a)),(u+rr*.18*math.cos(a),v+s*tw*.61,z+rr*.18*math.sin(a)),.008,chrome,6)
 vs=[];fs=[]
 for k in range(32):
  for row in [-1,1]:
   a=math.tau*(k+.22*(row<0))/32;start=len(vs)
   for r in [RAD*.971,RAD]:
    for da,d in [(-.065,row*.01),(.061,row*.01),(.071,row*tw*.37),(-.054,row*tw*.37)]:vs.append((u+r*math.cos(a+da),v+d,z+r*math.sin(a+da)))
   for face in [(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]:fs.append(tuple(start+i for i in face))
 mesh('Tread_'+key,vs,fs,rubber);pivots[GROUP]=(u,v,z)
for key,u,v in [('FL',WB/2,TRACK/2),('FR',WB/2,-TRACK/2),('RL',-WB/2,TRACK/2),('RR',-WB/2,-TRACK/2)]:wheel(key,u,v,RAD)
GROUP='Chassis';box('CabinFloor',((C['fb']+R)/2,0,C['sill']+.07),(C['fb']-R,2*(W-.27),.06),dark,.015)
floorlo=-WB/2+ar+.025;floorhi=min(C['fb'],WB/2-ar-.025)
box('WideFootwell',((floorlo+floorhi)/2,0,C['sill']+.072),(floorhi-floorlo,2*(W-.054),.05),dark,.005)
for s in [-1,1]:box('InnerSill'+str(s),((floorlo+floorhi)/2,s*(W-.061),C['sill']+.155),(floorhi-floorlo,.033,.15),trim,.009)
box('RaisedCargoFloor',((R-WB/2)/2,0,RAD+ar+.025),(-WB/2-R,2*(W-.08),.035),trim,.007)
for a in [-WB/2,WB/2]:rod('Axle'+str(a),(a,-TRACK/2,RAD),(a,TRACK/2,RAD),.038,trim,12)
for s in [-1,1]:box('ChassisRail'+str(s),(-.1,s*.38,C['sill']+.016),(F-R-.3,.075,.11),trim,.008)
# Distinct cabin proportions and controls. Cluster and hands are kept apart.
GROUP='Interior';DU=C['fb']-.25;DZ=B-.025;DV=C['drive']*W*.51;seat_u=DU-.55
box('Dashboard',(DU+.07,0,DZ),(.30,2*(W-.09),.18),dash,.030,3)
box('Firewall',(DU+.23,0,(B+C['sill'])/2),(.025,2*(W-.07),B-C['sill']-.08),dark,.006)
box('DashboardFascia',(DU-.088,0,DZ-.015),(.017,2*(W-.105),.12),paint if CAR=='KadettA' else dash,.007,2)
box('Glovebox',(DU-.101,-DV,DZ-.022),(.009,.43,.085),cloth if CAR=='KadettA' else trim,.006,2)
box('GloveboxCatch',(DU-.108,-DV,DZ+.007),(.011,.055,.012),chrome,.003)
GROUP='Instruments';needle_pivots={}
def dial(name,v,z,r,maxvalue):
 rod(name+'Bezel',(DU-.108,v,z),(DU-.119,v,z),r,chrome if CAR=='KadettA' else trim,28)
 rod(name+'Face',(DU-.120,v,z),(DU-.126,v,z),r*.89,dark,28)
 for k in range(9):
  a=math.radians(-35+k*31);line(name+'Tick'+str(k),[(DU-.127,v+r*.72*math.cos(a),z+r*.72*math.sin(a)),(DU-.127,v+r*.83*math.cos(a),z+r*.83*math.sin(a))],.0014,white)
  if r>.048:label(name+'Numeral'+str(k),str(round(k*maxvalue/8)),(DU-.130,v+r*.52*math.cos(a),z+r*.52*math.sin(a)),.009,white,False)
 global GROUP
 GROUP='Needle_'+name;needle_pivots[GROUP]=(DU-.136,v,z);line(name+'Pointer',[(DU-.136,v,z),(DU-.136,v+r*.66,z-r*.19)],.0018,orange);GROUP='Instruments'
if CAR=='KadettA':
 box('LongCluster',(DU-.104,DV,DZ+.015),(.010,.34,.10),chrome,.015,3)
 box('LongClusterFace',(DU-.115,DV,DZ+.015),(.008,.31,.076),dark,.006,2)
 for k in range(9):
  v=DV+.13-k*.0325;line('SpeedTick'+str(k),[(DU-.122,v,DZ+.018),(DU-.122,v,DZ+.038)],.0015,white);label('SpeedNumber'+str(k),str(k*20),(DU-.124,v,DZ+.002),.009,white,False)
 GROUP='Needle_Speedometer';needle_pivots[GROUP]=(DU-.131,DV+.12,DZ+.001);line('SpeedPointer',[(DU-.131,DV+.12,DZ-.009),(DU-.131,DV+.10,DZ+.032)],.0018,orange);GROUP='Instruments'
 dial('Fuel',DV+.215,DZ,.029,1)
else:
 box('ClusterHood',(DU+.018,DV,DZ+.065),(.23,.45,.20),dash,.030,3)
 for n,v in [('Speedometer',DV-.089),('Tachometer',DV+.089)]:dial(n,v,DZ+.072,.076,220 if n=='Speedometer' else 8)
 dial('Fuel',DV+.198,DZ+.033,.026,1);dial('Coolant',DV-.198,DZ+.033,.026,1)
GROUP='Interior'
for v in [-C['drive']*(W-.17),0]:
 box('Vent'+str(v),(DU-.113,v,DZ+.028),(.015,.105,.041),dark,.005,2)
 for k in range(3):box('VentLouvre'+str(v)+str(k),(DU-.124,v,DZ+.016+k*.012),(.008,.092,.0025),trim,.001)
box('Radio',(DU-.115,0,DZ-.052),(.02,.22,.045),dark,.004,2)
for v in [-.086,.086]:rod('RadioKnob'+str(v),(DU-.13,v,DZ-.052),(DU-.145,v,DZ-.052),.011,trim,12)
for v in [-.03,.03]:box('RadioDisplay'+str(v),(DU-.128,v,DZ-.045),(.004,.045,.008),white,.001)
if CAR=='E39Touring':
 box('ClimateControl',(DU-.10,0,DZ-.125),(.045,.23,.075),trim,.01,2)
 for k in range(6):
  for zz in [DZ-.103,DZ-.138]:box('ClimateButton'+str(k)+str(zz),(DU-.125,(k-2.5)*.032,zz),(.007,.024,.011),dark,.002)
 for s in [-1,1]:box('ClimateDisplay'+str(s),(DU-.130,s*.048,DZ-.118),(.004,.067,.009),orange,.001)
centre=(DU-.39,DV,DZ-.048);GROUP='Steering';pivots['Steering']=centre;vs=[]
for k in range(32):
 a=math.tau*k/32
 for j in range(6):
  b=math.tau*j/6;r=.17+(.009 if CAR=='KadettA' else .013)*math.cos(b);vs.append((centre[0]+.013*math.sin(b)-r*math.sin(a)*.28,centre[1]+r*math.cos(a),centre[2]+r*math.sin(a)*.96))
mesh('SteeringRim',vs,[(k*6+j,((k+1)%32)*6+j,((k+1)%32)*6+(j+1)%6,k*6+(j+1)%6) for k in range(32) for j in range(6)],rubber,smooth=True)
box('SteeringHub',centre,(.044,.16,.058 if CAR=='KadettA' else .09),chrome if CAR=='KadettA' else trim,.018,3)
for a in ([0,math.pi] if CAR=='KadettA' else [0,math.pi,math.pi*1.23,math.pi*1.77] if CAR=='E39Touring' else [0,math.pi,math.pi*1.5]):rod('SteeringSpoke'+str(a),centre,(centre[0]-.17*math.sin(a)*.28,centre[1]+.16*math.cos(a),centre[2]+.16*math.sin(a)*.96),.008 if CAR=='KadettA' else .019,chrome if CAR=='KadettA' else trim,6)
GROUP='Interior';rod('SteeringColumn',(DU+.01,DV,DZ-.13),centre,.025,trim,12)
floor=C['sill']+.13;sz=floor+.14
for s in [-1,1]:
 v=s*W*.48
 box('SeatBase'+str(s),(seat_u-.04,v,sz),(.48,W*.65,.13),cloth,.042,3)
 box('SeatBack'+str(s),(seat_u-.29,v,sz+.27),(.115,W*.65,.46),cloth,.045,3)
 if CAR!='KadettA':box('Headrest'+str(s),(seat_u-.29,v,sz+.54),(.10,.23,.15),cloth,.034,3)
 for k in [-2,-1,0,1,2]:line('SeatPleat'+str(s)+str(k),[(seat_u-.23,v+k*.052,sz+.067),(seat_u+.16,v+k*.052,sz+.067)],.0018,trim)
rear_seat_u=-WB/2+(.34 if CAR=='KadettA' else .08)
rear_halfwidth=min(W-.14,TRACK/2-C['tw']/2-.042)
box('RearSeat',(rear_seat_u,0,sz+.03),(.40,2*rear_halfwidth,.14),cloth,.04,3)
box('RearSeatBack',(rear_seat_u-.20,0,sz+.29),(.10,2*rear_halfwidth,.43),cloth,.04,3)
box('TransmissionTunnel',(-.25,0,floor+.045),(1.30,.23,.10),trim,.03,2)
rod('GearLever', (DU-.28,0,floor+.08),(DU-.39,0,floor+.33),.009,steel,8);box('GearKnob',(DU-.39,0,floor+.34),(.037,.038,.032),trim,.013,3)
if CAR=='SJ413':rod('TransferLever',(DU-.48,-.11,floor+.08),(DU-.55,-.11,floor+.26),.009,steel,8);box('TransferKnob',(DU-.55,-.11,floor+.27),(.035,.035,.03),trim,.01,2)
for dv in [-.1,0,.1]:box('Pedal'+str(dv),(DU+.10,DV+dv,floor+.04),(.075,.055,.018),rubber,.004)
box('InteriorMirror',(C['ft']-.025,0,H-.135),(.032,.18,.055),trim,.009,2);box('InteriorMirrorGlass',(C['ft']-.043,0,H-.135),(.003,.155,.040),chrome,.002)
GROUP='Engine';box('EngineBayFloor',((F+C['fb'])/2,0,C['sill']+.12),(F-C['fb']-.05,2*(W-.27),.025),dark,.006)
box('Engine',((F+C['fb'])/2,0,(B+C['sill'])/2),(.52,.35,.22),trim,.034,2);box('EngineCover',((F+C['fb'])/2,0,(B+C['sill'])/2+.12),(.52,.30,.05),steel,.018,2)
box('Radiator',(F-.08,0,B-.22),(.035,2*(W-.17),.21),dark,.008)
if CAR=='SJ413':
 # Spare is separate from the hatch skin, with its mounting bracket behind it.
 GROUP='Tailgate';box('SpareBracket',(R-.08,.14,B-.02),(.12,.20,.20),trim,.012)
 transform=Matrix.Translation(P((R-.20,.14,B+.04)))@Matrix.Rotation(math.pi/2,4,'Z')@Matrix.Translation(-P((WB/2,TRACK/2,RAD)))
 for src in list(col('Wheel_FL').objects):
  dup=src.copy();dup.data=src.data.copy();col('Tailgate').objects.link(dup);dup.name='Spare_'+src.name;dup.matrix_world=transform@src.matrix_world
# Parent each rigid assembly to its actual hinge centre.
pivots.update(needle_pivots)
for group,p in pivots.items():
 pa=bpy.data.objects.new(group+'_Pivot',None);col('Pivots').objects.link(pa);pa.location=P(p);bpy.context.view_layer.update()
 for ob in list(col(group).objects):ob.parent=pa;ob.matrix_parent_inverse=pa.matrix_world.inverted()
for ob in bpy.data.objects:
 if ob.type=='MESH' and any(m.type=='BEVEL' for m in ob.modifiers):
  for poly in ob.data.polygons:poly.use_smooth=True
# Studio and evidence cameras.
GROUP='Studio';box('StudioGround',(0,0,-.051),(200,200,.10),mat('StudioFloor',(.12,.145,.16),.85),0)
scene.world=bpy.data.worlds.new('StudioWorld');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.48,.57,.68,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.38
def light(name,loc,power,size):
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);col('Studio').objects.link(o);o.location=P(loc);o.rotation_euler=(P((0,0,.8))-o.location).to_track_quat('-Z','Y').to_euler()
light('Key',(3,4,6),1100,4);light('Fill',(1,-4,3.5),650,4);light('Rim',(-4,1,4),1250,3);light('CabinReviewFill',(seat_u,0,H-.1),6,1);bpy.data.objects['CabinReviewFill'].hide_render=True
cd=bpy.data.cameras.new('ReviewCamera');cam=bpy.data.objects.new('ReviewCamera',cd);col('Studio').objects.link(cam);scene.camera=cam;cd.clip_start=.01
length=F-R;views={'front':((length*1.3,length*1.22,H*1.6),(0,0,H*.50),57),'rear':((-length*1.3,-length*1.2,H*1.6),(-.1,0,H*.50),57),'side':((0,8,H*.51),(0,0,H*.51),55),'cockpit':((DU-.80,DV,H-.22),(DU+.4,0,DZ-.025),19)}
def setview(name):
 pos,target,lens=views[name];cam.location=P(pos);cam.rotation_euler=(P(target)-cam.location).to_track_quat('-Z','Y').to_euler();cd.lens=lens;cd.type='ORTHO' if name=='side' else 'PERSP';cd.ortho_scale=length+1
 bpy.data.objects['CabinReviewFill'].hide_render=name!='cockpit';bpy.data.objects['StudioGround'].hide_render=name=='side'
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=args.samples;scene.cycles.use_denoising=True;scene.render.threads_mode='FIXED';scene.render.threads=6
scene.render.resolution_x=1200;scene.render.resolution_y=800;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=-.45
ref=ROOT/'Art/References/Vehicles/SpecialsTrio'/(CAR+'_reference.png');im=bpy.data.images.load(str(ref));im.pack();ob=bpy.data.objects.new('ReferenceSheet',None);col('Reference').objects.link(ob);ob.empty_display_type='IMAGE';ob.data=im;ob.hide_render=True;ob.hide_viewport=True
scene['Vehicle']=CAR;scene['SourceRevision']=args.version;scene['Spec']=json.dumps(C);scene['Pivots']=json.dumps(pivots);scene['ReviewViews']=json.dumps(views);scene['Status']='Source model; export validation separate'
setview('front');bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(CAR+'.blend')))
(OUT/'build_spec.json').write_text(json.dumps({'car':CAR,'revision':args.version,'spec':C,'pivots':pivots,'views':views},indent=2))
for name in args.views.split(','):
 if not name:continue
 setview(name);scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True);print('TRIO_RENDER '+CAR+' '+name,flush=True)
print('TRIO_BUILD_OK '+str(OUT),flush=True)
