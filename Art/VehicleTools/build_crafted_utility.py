"""Crafted Utility: a new reference-led static assembly, never overwrites a revision.
Metres, X left, -Y front. Shape data are artistic, derived from the selected image.
Shared envelope drives independently editable panels; previous cars are untouched.
"""
import bpy, bmesh, math, sys, json, argparse, shutil
from pathlib import Path
from mathutils import Vector, Quaternion
sys.path.insert(0, str(Path(__file__).resolve().parent))
import wheel_fender_workshop as wf
import door_window_workshop as dw
import lamp_grille_workshop as lg
import cockpit_workshop as ck

p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--draft',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output)
if out.exists() and any(out.iterdir()): raise RuntimeError('Use a new empty output folder')
out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene;sc.unit_settings.system='METRIC'
S=dict(nose=-1.94,tail=2.18,front_axle=-1.39,rear_axle=1.25,tyre_radius=.405,track=1.59,
       sill=.465,belt=1.225,roof=1.845,scuttle=-.650,roof_front=-.265,roof_rear=1.88,
       lower_half_width=.91,roof_half_width=.778,door_split=.37,rear_door_end=1.215,
       arch_radius=.462,arch_lip_width=.035,panel_gap=.004)
OWNER='GT_CRAFTED_UTILITY_01'
def coll(name):
    c=bpy.data.collections.new(name);sc.collection.children.link(c);c['gt_owner']=OWNER;c['interface']='crafted-utility-v1';return c
def mat(n,col,rough=.5,metal=0):return wf.material('CU | '+n,col,rough,metal)
M=dict(paint=mat('olive enamel',(.085,.097,.050),.55,0),cream=mat('ivory coachline',(.64,.51,.31),.54),
       black=mat('rubber seals',(.014,.016,.015),.78),trim=mat('satin graphite',(.014,.017,.018),.58,.03),
       metal=mat('warm steel',(.44,.41,.32),.38,.65),edge=mat('fine bright trim',(.52,.53,.46),.34,.7),
       amber=mat('amber lens',(.78,.21,.020),.24),red=mat('red lens',(.40,.017,.009),.23),
       clear=mat('clear lamp lens',(.67,.66,.52),.26),glass=mat('light smoke glazing',(.88,.91,.88),.024),
       dark=mat('cavity black',(.009,.012,.011),.92),clay=mat('review clay',(.40,.42,.40),.78))
bs=M['glass'].node_tree.nodes.get('Principled BSDF');bs.inputs['Transmission Weight'].default_value=1.;bs.inputs['IOR'].default_value=1.46
M['paint'].node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value=.28
def mesh(n,v,f,m,c,bevel=0):
    o=wf.mesh(n,v,f,m,c,None,bevel);o['gt_owner']=OWNER;return o
def box(n,loc,dim,m,c,b=0):
    o=dw.box(n,loc,dim,m,c,None,b);o['gt_owner']=OWNER;return o
def solid(n,poly,delta,m,c):
    o=dw.solid(n,poly,delta,m,c,None);o['gt_owner']=OWNER;return o
def ring(n,outer,width,delta,m,c):
    inner=dw.inset(outer,width);o=dw.ring(n,outer,inner,delta,m,c,None);o['gt_owner']=OWNER;return inner
def rod(n,start,end,r,m,c):return ck.rod(n,start,end,r,m,c,None)
def mix(t,rows):return dw.lerp(t,rows)
def width(y,z):
    return mix(y,[(S['nose'],.863),(-1.76,.91),(1.98,.91),(S['tail'],.875)])+mix(z,[(.465,-.035),(.53,-.005),(1.12,0),(1.18,-.007),(1.225,-.040)])
def topz(y):return mix(y,[(S['nose'],1.12),(-1.75,1.16),(S['scuttle'],1.225),(S['tail'],1.225)])
def cabx(z):return mix(z,[(1.225,.870),(1.77,.774),(1.82,.778)])
def arch_z(y):
    r=S['arch_radius'];z=S['sill']
    for axle in [S['front_axle'],S['rear_axle']]:
        if abs(y-axle)<r:z=max(z,.405+math.sqrt(max(0,r*r-(y-axle)**2)))
    return z
# Piecewise linear arc shared by body, lips and liners, including sill crossings.
arc=[]
ang=math.asin((S['sill']-.405)/S['arch_radius'])
for cy in [S['front_axle'],S['rear_axle']]:
    arc.extend([(cy+S['arch_radius']*math.cos(math.pi-ang-i*(math.pi-2*ang)/20),.405+S['arch_radius']*math.sin(math.pi-ang-i*(math.pi-2*ang)/20)) for i in range(21)])
def bottom(y):
    for i in [0,21]:
        rows=arc[i:i+21]
        if rows[0][0]<=y<=rows[-1][0]:return mix(y,rows)
    return S['sill']
def skin(n,lo,hi,side,c):
    ys=sorted(set([lo,hi]+[y for y,z in arc if lo<y<hi]+[y for y in [-1.76,S['scuttle'],1.98] if lo<y<hi]))
    rows=[.465,.53,.70,.88,1.12,1.18,1.225];v=[];f=[]
    # Clip each planar strip to the shared faceted arch outline and top contour.
    for ya,yb in zip(ys,ys[1:]):
        for za,zb in zip(rows,rows[1:]):
            poly=[(ya,za),(yb,za),(yb,zb),(ya,zb)]
            for boundary,sign in [(bottom,1),(topz,-1)]:
                clipped=[]
                for u,w in zip(poly,poly[1:]+poly[:1]):
                    du=sign*(u[1]-boundary(u[0]));dv=sign*(w[1]-boundary(w[0]))
                    if du>=-1e-8:clipped.append(u)
                    if (du>=0)!=(dv>=0):
                        t=du/(du-dv);clipped.append((u[0]+t*(w[0]-u[0]),u[1]+t*(w[1]-u[1])))
                poly=clipped
                if not poly:break
            clean=[]
            for pt in poly:
                if not clean or math.dist(pt,clean[-1])>1e-7:clean.append(pt)
            if len(clean)>2 and math.dist(clean[0],clean[-1])<1e-7:clean.pop()
            if len(clean)<3:continue
            j=len(v);v += [(side*width(y,z),y,z) for y,z in clean];f.append(tuple(range(j,len(v))))
    o=mesh(n,v,f,M['paint'],c)
    bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    if sum(f.normal.x*f.calc_area() for f in bm.faces)*side<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
    bm.to_mesh(o.data);bm.free();mod=o.modifiers.new('Closed inward sheet and returns','SOLIDIFY');mod.thickness=.012;mod.offset=-1
    bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=mod.name)
    o['shared_envelope']='width/topz/arch profile in shape-spec.json';return o
def strip(n,lo,hi,z,h,side,m,c,offset=.0015):
    ys=sorted(set([lo,hi]+[y for y in [-1.76,1.98] if lo<y<hi]));v=[]
    for y in ys:v += [(side*(width(y,zz)+offset),y,zz) for zz in [z-h/2,z+h/2]]
    o=mesh(n,v,[(i*2,i*2+2,i*2+3,i*2+1) for i in range(len(ys)-1)],m,c)
    mod=o.modifiers.new('Trim thickness','SOLIDIFY');mod.thickness=.0015;return o

# Actual separate coachwork panels with visible gaps and no old shell behind them.
parts=[]
for side,label in [(1,'L'),(-1,'R')]:
    for title,lo,hi in [('Front fender',-1.94,-.652),('Front door',-.648,.368),('Rear door',.372,1.213),('Rear quarter',1.217,2.18)]:
        c=coll(label+' | '+title);parts.append(c);ob=skin(title+' | formed closed skin',lo,hi,side,c)
        strip('Cream belt stripe',lo+.002,hi-.002,1.075,.052,side,M['cream'],c)
        if 'door' in title.lower():
            hy=hi-.13;hz=1.162
            aperture=dw.rect_yz(side*1.04,hy,hz,.118,.050,.004)
            dw.cut(ob,solid('Temporary handle cut',aperture,(-side*.26,0,0),None,c))
            hx=side*(width(hy,hz)+.003)
            poly=dw.rect_yz(hx,hy,hz,.132,.064,.006)
            inner=ring('Handle | rubber bezel',poly,.008,(-side*.012,0,0),M['black'],c)
            solid('Handle | recessed pocket',[(x-side*.021,y,z) for x,y,z in inner],(-side*.004,0,0),M['dark'],c)
            box('Handle | silver latch',(hx+side*.003,hy,hz+.008),(.012,.081,.024),M['edge'],c,.003)
        # Fine low body protection, clipped where the arch rises.
        trimlo=lo+.01;trimhi=hi-.01
        ys=sorted(set([trimlo,trimhi]+[y for y,z in arc if trimlo<y<trimhi]))
        for ya,yb in zip(ys,ys[1:]):
            if max(bottom(ya),bottom(yb))<.63:
                strip('Lower protective moulding',ya,yb,.656,.017,side,M['trim'],c,.004)
                strip('Moulding highlight',ya,yb,.662,.003,side,M['edge'],c,.006)
    c=coll(label+' | Jamb backing');parts.append(c)
    for yy in [-.65,.37,1.215]:
        zz=sorted(set([bottom(yy)+.005,.88,1.12,1.18,1.223]));zz=[z for z in zz if bottom(yy)<z<=1.223]
        v=[(side*(width(yy,z)-.017),y,z) for z in zz for y in [yy-.018,yy+.018]]
        ob=mesh('Door gap | recessed dark jamb',v,[(i*2,i*2+1,i*2+3,i*2+2) for i in range(len(zz)-1)],M['black'],c)
        mod=ob.modifiers.new('Jamb thickness','SOLIDIFY');mod.thickness=.009
    c=coll(label+' | Arch lips and wheelhouses');parts.append(c)
    for cy in [S['front_axle'],S['rear_axle']]:
        pts=[p for p in arc if abs(p[0]-cy)<.5];vv=[]
        for layer in range(4):
            for y,z in pts:
                dy=y-cy;dz=z-.405;rr=math.hypot(dy,dz);k=(rr+(.035 if layer in [0,3] else 0))/rr
                yy=cy+dy*k;zz=.405+dz*k
                xx=width(yy,zz)+(.003 if layer==0 else .019 if layer==1 else -.070 if layer==2 else -.013)
                vv.append((side*xx,yy,zz))
        n=len(pts);ff=[(j*n+i,j*n+i+1,((j+1)%4)*n+i+1,((j+1)%4)*n+i) for j in range(4) for i in range(n-1)]+[(0,n,2*n,3*n),(n-1,4*n-1,3*n-1,2*n-1)]
        mesh('Narrow rolled arch lip',vv,ff,M['paint'],c)
        inner=[(side*.625,y,z+.008) for y,z in pts]
        outer=[(side*.875,y,z+.008) for y,z in pts]
        liner=mesh('Wheelhouse | curved liner',inner+outer,[(i,i+1,n+i+1,n+i) for i in range(n-1)],M['dark'],c)
        mod=liner.modifiers.new('Liner wall','SOLIDIFY');mod.thickness=.009
        solid('Wheelhouse | inboard tub',inner+[ (side*.625,pts[-1][0],.38),(side*.625,pts[0][0],.38)],(-side*.012,0,0),M['dark'],c)
    box('Rocker | underside rail',(side*.850,.315,.465),(.074,1.74,.053),M['trim'],c,.008)

# Bonnet uses a long flat central plane, two defined shoulder folds and a turned lip.
c=coll('Bonnet | clamshell');parts.append(c)
ys=[-1.946,-1.885,-1.76,-.72,-.656];fractions=[-1,-.93,-.80,-.69,0,.69,.80,.93,1]
vv=[]
for y in ys:
    w=width(y,topz(y))+.004
    for f in fractions:
        rise=mix(abs(f),[(0,.037),(.69,.037),(.80,.013),(.93,.013),(1,0)])
        vv.append((w*f,y,topz(y)+.006+rise))
ff=[(j*9+i,j*9+i+1,(j+1)*9+i+1,(j+1)*9+i) for j in range(len(ys)-1) for i in range(8)]
o=mesh('Bonnet | sculpted shoulder surface',vv,ff,M['paint'],c);mod=o.modifiers.new('Bonnet sheet','SOLIDIFY');mod.thickness=.014;mod.offset=-1
# Front vertical clamshell lip fits just above fascia.
solid('Bonnet | front folded edge',[(x,-1.946,z) for x,y,z in vv[:9]]+[(vv[8][0],-1.946,1.114),(vv[0][0],-1.946,1.114)],(0,.018,0),M['paint'],c)

# Cabin: structural frame, dark glazing cassettes and shallow crowned roof.
def window(n,poly,delta,c,frame=.029):
    inner=ring(n+' | frame',poly,frame,delta,M['trim'],c)
    inner=ring(n+' | gasket',inner,.008,tuple(Vector(delta)*.6),M['black'],c)
    pane=[tuple(Vector(v)+Vector(delta)*.45) for v in inner]
    solid(n+' | glass',pane,tuple(Vector(delta)*.12),M['glass'],c)
    return inner
z0=1.229;zt=1.778
for side,label in [(1,'L'),(-1,'R')]:
    c=coll(label+' | Glazing and pillars');parts.append(c)
    sections=[(-.650,-.269),(.37,.37),(1.215,1.165),(2.161,1.892)]
    for i,((b0,t0),(b1,t1)) in enumerate(zip(sections,sections[1:])):
        poly=[(side*cabx(z0),b0+.003,z0),(side*cabx(z0),b1-.003,z0),(side*cabx(zt),t1-.003,zt),(side*cabx(zt),t0+.003,zt)]
        window(['Front door window','Rear door window','Cargo window'][i],poly,(-side*.029,0,0),c,.032 if i<2 else .048)
    # Tail pillar is deliberately broader than the thin door divisions.
    solid('Rear sail pillar',[(side*cabx(z0),2.048,z0),(side*cabx(z0),2.180,z0),(side*cabx(zt),1.90,zt),(side*cabx(zt),1.796,zt)],(-side*.025,0,0),M['trim'],c)
    for i in range(5):
        y=2.075-i*.011;z=1.30+i*.020
        rod('Pillar vent rib',(side*(cabx(z)+.002),y-.047,z),(side*(cabx(z)+.002),y+.02,z),.004,M['black'],c)
    # Door belt seal and shallow paint ledge below glass.
    rod('Continuous belt weatherstrip',(side*.873,-.645,1.229),(side*.873,2.16,1.229),.007,M['black'],c)
c=coll('Windscreen and wipers');parts.append(c)
poly=[(-cabx(z0),-.654,z0),(cabx(z0),-.654,z0),(cabx(zt),-.273,zt),(-cabx(zt),-.273,zt)]
window('Windscreen',poly,(0,.025,0),c,.032)
for x in [-.43,.36]:
    rod('Wiper | pivot',(x,-.661,1.247),(x,-.680,1.255),.014,M['trim'],c)
    rod('Wiper | arm',(x,-.680,1.255),(x-.18,-.644,1.301),.006,M['trim'],c)
    rod('Wiper | blade',(x-.36,-.627,1.312),(x+.02,-.627,1.312),.009,M['black'],c)
c=coll('Roof | crown and gutters');parts.append(c)
roofys=[(-.318,1.809),(-.24,1.839),(1.81,1.839),(1.947,1.805)]
v=[]
for y,z in roofys:
    v += [(x,y,z+dz) for x,dz in [(-.802,-.010),(-.740,.006),(0,.010),(.740,.006),(.802,-.010)]]
o=mesh('Roof | shallow pressed crown',v,[(j*5+i,j*5+i+1,(j+1)*5+i+1,(j+1)*5+i) for j in range(3) for i in range(4)],M['paint'],c)
mod=o.modifiers.new('Roof folded thickness','SOLIDIFY');mod.thickness=.034;mod.offset=-1
for side in [-1,1]:
    rod('Roof | dark gutter',(side*.803,-.316,1.796),(side*.803,1.945,1.796),.012,M['trim'],c)
    rod('Roof | painted drip edge',(side*.809,-.311,1.810),(side*.809,1.940,1.810),.007,M['paint'],c)

# Front uses real lamp openings, deep grille and separately generated optics.
c=coll('Front | grille carrier');parts.append(c)
carrier=box('Front | apertured fascia',(0,-1.918,.962),(1.738,.05,.314),M['trim'],c,.005)
dw.cut(carrier,box('Temporary grille opening',(0,-1.935,.962),(.98,.20,.267),None,c))
for side in [-1,1]:
    dw.cut(carrier,rod('Temporary lamp aperture',(side*.651,-2.05,.962),(side*.651,-1.80,.962),.142,None,c))
    lamp=lg.lamp(dict(lg.LAMP,center=[side*.651,-1.901,.962]),'CU '+('L' if side==1 else 'R')+' | Headlamp');parts.append(lamp)
box('Grille | radiator shadow',(0,-1.840,.962),(.978,.025,.267),M['dark'],c)
for z in [.850,.895,.940,.985,1.030,1.075]:
    poly=[(-.481,-1.966,z-.007),(-.481,-1.958,z+.007),(-.481,-1.923,z+.004),(-.481,-1.923,z-.009)]
    solid('Grille | folded horizontal blade',poly,(.962,0,0),M['trim'],c)
for x in [-.34,0,.34]:box('Grille | rear support',(x,-1.904,.962),(.011,.015,.259),M['black'],c)
for side in [-1,1]:
    cc=coll(('L' if side==1 else 'R')+' | Marker cluster');parts.append(cc)
    box('Marker | black surround',(side*.826,-1.935,.961),(.090,.07,.310),M['black'],cc,.006)
    for z,h,m in [(1.045,.106,M['amber']),(.94,.077,M['amber']),(.858,.063,M['clear'])]:
        box('Marker | inset lens',(side*.826,-1.976,z),(.073,.012,h),m,cc,.004)
        for i in range(6):box('Marker | fine lens flute',(side*.826+(i-2.5)*.010,-1.984,z),(.002,.002,h-.01),m,cc,.0005)
    box('Fender | small side repeater',(side*.916,-1.68,1.03),(.009,.053,.026),M['amber'],cc,.003)

# Slim stepped bumpers and plain lower valance. No expedition hardware.
c=coll('Front | bumper and valance');parts.append(c)
outline=[(-.86,-2.11),(.86,-2.11),(.94,-2.05),(.94,-1.87),(.88,-1.82),(-.88,-1.82),(-.94,-1.87),(-.94,-2.05)]
solid('Bumper | chamfered carrier',[(x,y,.635) for x,y in outline],(0,0,.151),M['trim'],c)
for side in [-1,1]:box('Bumper | vertical overrider',(side*.54,-2.125,.709),(.084,.038,.161),M['black'],c,.009)
box('Valance | upper rail',(0,-1.973,.599),(1.49,.081,.045),M['trim'],c,.008)
box('Valance | lower rail',(0,-1.942,.482),(1.34,.065,.044),M['trim'],c,.008)
for x in [-.49,0,.49]:box('Valance | opening divider',(x,-1.965,.54),(.049,.073,.112),M['trim'],c,.005)
for side in [-1,1]:
    box('Fog lamp | inset housing',(side*.728,-1.982,.55),(.199,.11,.114),M['black'],c,.009)
    box('Fog lamp | rim',(side*.728,-2.044,.55),(.158,.014,.09),M['metal'],c,.007)
    box('Fog lamp | warm lens',(side*.728,-2.054,.55),(.135,.007,.066),M['clear'],c,.005)

# Rear closure follows the same side/top interface; registration is an actual pocket.
c=coll('Rear | split tailgate');parts.append(c)
poly=[(cabx(z0),2.180,z0),(-cabx(z0),2.180,z0),(-cabx(zt),1.949,zt),(cabx(zt),1.949,zt)]
window('Upper tailgate',poly,(0,-.025,0),c,.041)
tail=box('Lower tailgate | closed panel',(0,2.167,.938),(1.53,.034,.557),M['paint'],c,.009)
dw.cut(tail,box('Temporary registration recess',(0,2.19,.987),(.56,.053,.20),None,c,.009))
box('Registration | pocket backing',(0,2.162,.987),(.555,.010,.195),M['paint'],c,.009)
box('Tailgate | split seal',(0,2.190,1.226),(1.60,.009,.009),M['black'],c,.002)
box('Tailgate | release',(0,2.194,1.137),(.11,.012,.035),M['trim'],c,.004)
for side in [-1,1]:
    box('Tailgate | corner post',(side*.820,2.147,.948),(.108,.06,.560),M['paint'],c,.007)
    box('Tail lamp | surround',(side*.819,2.188,.978),(.125,.021,.33),M['black'],c,.005)
    for z,h,m in [(1.079,.10,M['amber']),(.965,.106,M['red']),(.865,.065,M['clear'])]:
        box('Tail lamp | lens',(side*.819,2.204,z),(.105,.012,h),m,c,.004)
        for i in range(8):box('Tail lamp | lens flute',(side*.819+(i-3.5)*.012,2.211,z),(.002,.002,h-.010),m,c,.0005)
    box('Tailgate | lower hinge',(side*.55,2.194,.668),(.089,.029,.026),M['trim'],c,.004)
box('Rear | bumper',(0,2.243,.600),(1.88,.205,.169),M['trim'],c,.028)
box('Rear | tread step',(0,2.235,.688),(1.20,.15,.013),M['black'],c,.005)
for i in range(14):box('Rear | step rib',((i-6.5)*.077,2.235,.697),(.006,.128,.004),M['trim'],c,.001)
for i in range(9):
    z=1.33+i*.042;y=2.18+(z-z0)*(1.949-2.18)/(zt-z0)+.002
    rod('Rear glass | demister',(-.70,y,z),(.70,y,z),.00035,mat('demister copper',(.075,.030,.009),.7),c)

# Mirrors include an inset reflective rear surface.
for side,label in [(1,'L'),(-1,'R')]:
    c=coll(label+' | Mirror');parts.append(c)
    rod('Mirror | stalk',(side*.869,-.539,1.29),(side*.969,-.536,1.31),.020,M['trim'],c)
    box('Mirror | shaped cap',(side*1.014,-.539,1.348),(.168,.108,.116),M['trim'],c,.014)
    mirror=mat('mirror silver',(.67,.73,.71),.055,1)
    box('Mirror | inset silver',(side*1.014,-.481,1.348),(.139,.005,.088),mirror,c,.009)

# Reuse the detailed wheel construction at its supported size, then uniformly scale
# the complete component about its mount. This does not claim the old fender fit.
for cy,axle in [(S['front_axle'],'Front'),(S['rear_axle'],'Rear')]:
    for side,label in [(1,'L'),(-1,'R')]:
        s=dict(wf.DEFAULT,center=[side*S['track']/2,cy,.405],side=side,width=.250)
        c=wf.wheel(s,'CU '+axle+' '+label+' | Wheel');parts.append(c)
        root=next(o for o in c.objects if o.get('mount'))
        # A quieter pressed-steel web with twelve smaller round ventilation holes.
        old=next(o for o in c.objects if o.name.startswith('Rim | dished web'))
        bpy.data.objects.remove(old,do_unlink=True);pm=wf.palette();offset=.250/2-.136
        disk=wf.revolve('Rim | pressed steel web with twelve vents',[(x+offset,rr) for x,rr in [(.100,.050),(.094,.095),(.120,.17),(.139,.201),(.126,.205),(.106,.173),(.080,.096),(.086,.050)]],pm['steel'],c,root,64,True)
        for i in range(12):
            angle=i*math.tau/12
            cutter=wf.cylinder('Temporary wheel vent',offset+.11,.158*math.sin(angle),.158*math.cos(angle),.018,.24,None,c,root,20)
            dw.cut(disk,cutter)
        mod=disk.modifiers.new('Rolled vent edges','BEVEL');mod.width=.002;mod.segments=2
        mod=disk.modifiers.new('Web normals','WEIGHTED_NORMAL');mod.keep_sharp=True
        k=.405/.38;root.scale=(side*k,k,k)
        c['adapted_to']='crafted-utility-v1';c['adaptation']='Uniform scale 0.405/0.38, new axle frame; old fender clearance invalid'

for name,color in [('Workshop | warm satin alloy',(.27,.24,.185)),('Workshop | machined edge',(.36,.34,.27))]:
    m=bpy.data.materials.get(name);m.diffuse_color=(*color,1);bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=.48
# Seats and dashboard preserve authored detail, mounted inside the new envelope.
for func,title in [(ck.dash,'Dashboard'),(ck.instruments,'Instruments'),(ck.steering,'Steering'),(ck.console,'Console'),(ck.rear_bench,'Rear bench')]:
    c=func(ck.spec(),'CU cabin | '+title);parts.append(c)
    root=next(o for o in c.objects if o.get('mount'));root.location.y=.09;root.location.z=.034
    c['adapted_to']='crafted-utility-v1';c['fit_status']='Static exterior-visible cabin; no motion or ergonomics certification'
for side,label in [(1,'L'),(-1,'R')]:
    c=ck.front_seat(ck.spec(side=side),'CU cabin | '+label+' front seat');parts.append(c)
    root=next(o for o in c.objects if o.get('mount'));root.location.y=.09;root.location.z=.034
# Warm leather tones, limited to the new scene.
for name,color in [('Cockpit | saddle grey vinyl',(.24,.17,.105)),('Cockpit | warm oatmeal weave',(.33,.255,.17))]:
    m=bpy.data.materials.get(name);m.diffuse_color=(*color,1);m.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(*color,1)
c=coll('Cabin | floor, cards and roof liner');parts.append(c)
box('Floor | cabin centre',(0,.43,.560),(1.23,2.27,.027),M['dark'],c)
for side in [-1,1]:box('Floor | front outer wing',(side*.695,.02,.56),(.16,1.40,.027),M['dark'],c)
box('Floor | cargo',(0,1.953,.590),(1.37,.440,.035),M['dark'],c)
for side in [-1,1]:
    for lo,hi in [(-.61,.34),(.40,1.18)]:
        ys=sorted(set([lo,hi]+[y for y,z in arc if lo<y<hi]))
        poly=[(side*.844,y,max(.793,bottom(y)+.018)) for y in ys]+[(side*.844,hi,1.173),(side*.844,lo,1.173)]
        solid('Door | interior card',poly,(-side*.024,0,0),M['trim'],c)
        box('Door | padded armrest',(side*.816,(lo+hi)/2,.931),(.075,.38,.052),M['black'],c,.012)
box('Roof | interior liner',(0,.82,1.778),(1.47,2.03,.012),mat('headlining',(.39,.37,.29),.95),c,.015)
# Visible underbody gives the stance weight without floating parts.
c=coll('Chassis and suspension');parts.append(c)
for side in [-1,1]:box('Chassis | longitudinal rail',(side*.49,.20,.399),(.075,3.47,.088),M['dark'],c,.01)
for cy in [S['front_axle'],S['rear_axle']]:
    rod('Axle | casing',(-.75,cy,.39),(.75,cy,.39),.043,M['trim'],c)
    box('Axle | differential',(0,cy,.39),(.22,.23,.18),M['trim'],c,.055)
    for side in [-1,1]:
        rod('Suspension | damper',(side*.60,cy,.41),(side*.56,cy+.13,.70),.021,M['trim'],c)
        box('Wheel | rear mudflap',(side*.80,cy+.448,.32),(.25,.012,.28),M['black'],c,.009)
pipe=rod('Exhaust | tailpipe',(-.61,1.55,.37),(-.61,2.19,.37),.026,M['metal'],c)
dw.cut(pipe,rod('Temporary exhaust bore',(-.61,1.66,.37),(-.61,2.21,.37),.019,None,c))

# Packed source image and text keep the design target with the editable assembly.
ref=Path('C:/GrandTour/Art/References/Vehicles/BoardDerived_2026-09-30/01-crafted-utility-views.png')
im=bpy.data.images.load(str(ref));im.use_fake_user=True;im.pack()
txt=bpy.data.texts.new('START HERE — Crafted Utility')
txt.write('Crafted Utility / reference-led static assembly\nSource: '+str(ref)+'\n\nAll exterior panels, optics, wheels and cabin modules are separate collections.\nThe selected reference is packed as an image. Units are metres; front -Y.\nThe shape specification is an artistic interpretation, not factory measurements.\nNo opening rig, LODs, collision or engine export is certified in this revision.\nOld prototypes remain untouched. Generated parts use new interfaces; old rebuild operators must not be applied to adapted components.\n')
for c in parts:
    # Adapted components are deliberately detached from old rebuild ownership.
    c['source_owner']=c.get('gt_owner','');c['gt_owner']=OWNER
    for ob in c.objects:ob['gt_owner']=OWNER

# Studio lighting and repeatable review views.
c=coll('Studio | lights and ground')
mesh('Studio ground',[(-200,-200,0),(200,-200,0),(200,200,0),(-200,200,0)],[(0,1,2,3)],mat('studio sand',(.51,.47,.41),.9),c)
# A circular studio sweep removes the distracting horizon in every review view.
v=[];profile=[(11,0),(12,.12),(13,.55),(14,1.5),(14.7,3.2),(15,6),(15,15)];n=128
for rr,z in profile:v += [(rr*math.cos(i*math.tau/n),rr*math.sin(i*math.tau/n),z) for i in range(n)]
o=mesh('Studio cyclorama',v,[(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(len(profile)-1) for i in range(n)],bpy.data.materials['CU | studio sand'],c)
for poly in o.data.polygons:poly.use_smooth=True
world=bpy.data.worlds.new('Warm neutral world');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.65,.61,.54,1);world.node_tree.nodes['Background'].inputs[1].default_value=.6;sc.world=world
for name,loc,energy,size in [('Key',(4,-4.5,6),950,5),('Fill',(-4,-1.5,3),600,4),('Rim',(-3,3.5,6),1000,3)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=energy;data.shape='DISK';data.size=size
    ob=bpy.data.objects.new(name,data);c.objects.link(ob);ob.location=loc;ob.rotation_euler=(Vector((0,0,1))-ob.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('Review camera');cam=bpy.data.objects.new('Review camera',data);sc.collection.objects.link(cam);sc.camera=cam
sc.render.engine='CYCLES';sc.cycles.samples=20 if a.draft else 32;sc.cycles.use_denoising=True
sc.cycles.max_bounces=8;sc.cycles.transmission_bounces=6;sc.render.threads_mode='FIXED';sc.render.threads=12
sc.render.resolution_x=1100 if a.draft else 1500;sc.render.resolution_y=825 if a.draft else 1125;sc.render.resolution_percentage=100
sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium High Contrast'
views={'quarter':((5.2,-8.3,2.75),(0,.15,.91),5.45),'side':((8,.12,1.0),(0,.12,1.0),4.9),'front':((0,-8,.97),(0,0,.97),2.80),
       'rear':((0,8,1.0),(0,0,1.0),2.8),'top':((0,.1,8),(0,.1,0),4.85),'rear-quarter':((4,6,2.9),(0,.15,1.0),5.4),
       'front-detail':((2.8,-4,1.65),(0,-1.34,.87),2.7)}
def render(key,clay=False):
    loc,target,size=views[key];cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=size
    if key=='top':cam.rotation_euler=(cam.rotation_euler.to_quaternion() @ Quaternion((0,0,1),math.pi/2)).to_euler()
    if key in ['quarter','rear-quarter']:cam.data.type='PERSP';cam.data.lens=60 if key=='quarter' else 46
    sc.view_layers[0].material_override=M['clay'] if clay else None
    sc.render.filepath=str(out/(key+('-clay' if clay else '')+'.png'));bpy.ops.render.render(write_still=True);sc.view_layers[0].material_override=None

# Audit closed evaluated meshes, actual tyre envelope, visible body gaps and extents.
bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();issues=[];count=0;verts=0
for c in parts:
    for ob in c.objects:
        if ob.type!='MESH':continue
        eo=ob.evaluated_get(dg);me=eo.to_mesh();bm=bmesh.new();bm.from_mesh(me)
        bad=sum(not e.is_manifold for e in bm.edges)
        if bad:issues.append(dict(object=ob.name,nonmanifold_edges=bad))
        verts+=len(me.vertices);count+=1;bm.free();eo.to_mesh_clear()
report=dict(mesh_objects=count,evaluated_vertices=verts,nonmanifold_objects=issues,
    nominal_radial_arch_clearance_m=S['arch_radius']-S['tyre_radius'],
    nominal_panel_gap_m=S['panel_gap'],wheelbase_m=S['rear_axle']-S['front_axle'],
    scope='Static reference-led assembly. Manifold audit is not a full collision or moving-fit certification.')
(out/'geometry-review.json').write_text(json.dumps(report,indent=2))
(out/'shape-spec.json').write_text(json.dumps(dict(spec=S,arch_profile=arc,reference=str(ref),status='Crafted Utility selected; this 3D interpretation awaits visual review'),indent=2))
shutil.copy2(__file__,out/Path(__file__).name)
for name in ['wheel_fender_workshop.py','door_window_workshop.py','lamp_grille_workshop.py','cockpit_workshop.py']:shutil.copy2(Path(__file__).parent/name,out/name)
render('quarter');bpy.ops.wm.save_as_mainfile(filepath=str(out/'Crafted_Utility.blend'))
for key in (['side','front'] if a.draft else ['side','front','rear','top','rear-quarter','front-detail']):render(key)
if not a.draft:
    for key in ['quarter','side','front']:render(key,True)
# Save the useful quarter view as the opening camera and solid viewport orientation.
loc,target,size=views['quarter'];cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=size;cam.data.type='PERSP';cam.data.lens=60
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_distance=6.5;area.spaces.active.region_3d.view_location=(0,.15,.9)
            area.spaces.active.region_3d.view_rotation=cam.rotation_euler.to_quaternion();area.spaces.active.shading.color_type='MATERIAL'
sc['review_status']='Crafted Utility static model; visual review, not final shape approval or game readiness'
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Crafted_Utility.blend'))
print('CRAFTED_UTILITY_COMPLETE '+str(out),flush=True)
