"""Fitted stylized RR cockpit components. Metres, front -Y, original steering -X.

Import is non-destructive; physical ergonomics and operating mechanisms unvalidated.
"""
bl_info={'name':'Grand Tour Cockpit Workshop','author':'Grand Tour','version':(0,1,0),'blender':(5,1,0),'category':'Mesh'}
import bpy,bmesh,math,json,sys
from pathlib import Path
from mathutils import Vector
try:from . import door_window_workshop as dw
except ImportError:
    sys.path.insert(0,str(Path(__file__).resolve().parent));import door_window_workshop as dw
wf=dw.wf
OWNER='GT_COCKPIT_01'
KINDS=['dash','instruments','steering','console','front_seat','rear_bench','door_card','lining']
def spec(side=1,position='front',**kw):
    return dict(center=[0,0,0],side=side,position=position,interface='rr-cabin-v1',**dict(dict(slide=0.,wheel_radius=.176),**kw))
def validate(s,kind):
    if kind not in KINDS or s['interface']!='rr-cabin-v1' or s['center']!=[0,0,0]:raise ValueError('Requires RR cabin v1 interface and origin')
    if s['side'] not in [-1,1] or s['position'] not in ['front','rear']:raise ValueError('Unsupported component mount')
    if not -.035<=s['slide']<=.035:raise ValueError('Seat slide supports -35 to +35 mm')
    if not .165<=s['wheel_radius']<=.185:raise ValueError('Steering radius supports 165 to 185 mm')
def collection(name,s,kind):
    validate(s,kind);c,r=wf.root_collection(name,s,kind);c['gt_owner']=OWNER
    if kind not in ['front_seat','door_card']:r.scale=(1,1,1)
    return c,r
def seal(c):
    for ob in c.objects:ob['gt_owner']=OWNER
    wf.seal(c)
def palette():
    glass=wf.material('Cockpit | clear instrument glass',(.93,.96,.95),.025)
    if not glass.get('initialized'):
        bs=glass.node_tree.nodes.get('Principled BSDF');bs.inputs['Transmission Weight'].default_value=1.;bs.inputs['IOR'].default_value=1.46;glass['initialized']=True
    return dict(dark=wf.material('Cockpit | charcoal moulding',(.035,.044,.043),.69),
        pad=wf.material('Cockpit | padded graphite',(.074,.084,.078),.82),
        fabric=wf.material('Cockpit | warm oatmeal weave',(.30,.245,.168),.92),
        bolster=wf.material('Cockpit | saddle grey vinyl',(.125,.133,.111),.72),
        seam=wf.material('Cockpit | upholstery seams',(.058,.063,.051),.92),
        carpet=wf.material('Cockpit | charcoal carpet',(.044,.051,.044),1.),
        headliner=wf.material('Cockpit | light warm headliner',(.43,.42,.34),.94),
        metal=wf.material('Cockpit | satin fittings',(.22,.25,.23),.43,.6),
        dial=wf.material('Cockpit | dial face',(.009,.015,.016),.60),
        ivory=wf.material('Cockpit | ivory markings',(.76,.75,.62),.57),
        orange=wf.material('Cockpit | orange needles',(.90,.19,.025),.52),
        red=wf.material('Cockpit | buckle red',(.39,.028,.016),.68),glass=glass,
        mirror=wf.material('Doors | mirror silver',(.72,.79,.80),.045,1.))
def rod(name,a,b,radius,mat,c,root,n=12):
    a=Vector(a);d=Vector(b)-a;normal=d.normalized();u=normal.cross(Vector((0,0,1)))
    if u.length<.01:u=normal.cross(Vector((0,1,0)))
    u.normalize();v=normal.cross(u)
    pts=[tuple(a+radius*(math.cos(i*math.tau/n)*u+math.sin(i*math.tau/n)*v)) for i in range(n)]
    return dw.solid(name,pts,tuple(d),mat,c,root)
def rect_y(x,y,z,w,h,b=.009):
    return [(x+a,y,z+c) for a,c in [(-w/2+b,-h/2),(w/2-b,-h/2),(w/2,-h/2+b),(w/2,h/2-b),(w/2-b,h/2),(-w/2+b,h/2),(-w/2,h/2-b),(-w/2,-h/2+b)]]
def text_y(name,body,loc,size,mat,c,r):
    cu=bpy.data.curves.new(name,'FONT');cu.body=body;cu.align_x='CENTER';cu.align_y='CENTER';cu.size=size;cu.extrude=.00008;cu.resolution_u=1
    ob=bpy.data.objects.new(name,cu);c.objects.link(ob);ob.parent=r;ob.location=loc;ob.rotation_euler=(math.pi/2,0,math.pi);cu.materials.append(mat);return ob
def prism_x(name,yz,xa,xb,mat,c,r):return dw.solid(name,[(xa,y,z) for y,z in yz],(xb-xa,0,0),mat,c,r)
def closed_grid(name,front,nu,nv,back,mat,c,r):
    count=len(front);ff=[]
    for j in range(nv-1):
        for i in range(nu-1):
            a=j*nu+i;ff += [(a,a+1,a+1+nu,a+nu),(a+count,a+nu+count,a+nu+1+count,a+1+count)]
    per=list(range(nu))+[j*nu+nu-1 for j in range(1,nv)]+list(range((nv-1)*nu+nu-2,(nv-1)*nu-1,-1))+[j*nu for j in range(nv-2,0,-1)]
    ff += [(a,b,b+count,a+count) for a,b in zip(per,per[1:]+per[:1])]
    return wf.mesh(name,front+back,ff,mat,c,r)
def vent(name,x,y,z,w,h,m,c,r):
    outer=rect_y(x,y,z,w,h,.004);inner=dw.inset(outer,.007)
    dw.ring(name+' | bezel',outer,inner,(0,-.020,0),m['dark'],c,r)
    dw.solid(name+' | recessed cavity',[(x,y-.018,z) for x,y,z in inner],(0,-.004,0),m['dial'],c,r)
    for zz in [-.022,-.011,0,.011,.022]:
        if abs(zz)<h/2-.010:dw.box(name+' | louvre',(x,y-.007,z+zz),(w-.017,.018,.004),m['pad'],c,r,.001)
    dw.box(name+' | direction tab',(x+.018,y+.001,z),(.019,.006,.008),m['metal'],c,r,.001)

def dash(s,name='Dashboard carrier'):
    c,r=collection(name,s,'dash');m=palette()
    yz=[(-.728,1.095),(-.728,1.144),(-.680,1.181),(-.495,1.181),(-.382,1.145),(-.382,1.022),(-.455,.971),(-.650,.982)]
    body=prism_x('Dash | shaped carrier',yz,-.813,.813,m['pad'],c,r)
    # Independent instrument pod seats inside a real carrier opening.
    dw.cut(body,dw.box('Temporary cluster clearance',(-.410,-.485,1.210),(.508,.240,.197),None,c,r))
    dw.box('Dash | instrument mounting shelf',(-.410,-.503,1.104),(.51,.205,.012),m['dark'],c,r)
    for x,w in [(-.716,.125),(.673,.202)]:
        dw.cut(body,dw.box('Temporary vent opening',(x,-.43,1.115),(w-.010,.24,.066),None,c,r))
        vent('Dash vent',x,-.376,1.115,w,.074,m,c,r)
    # Glovebox panel nests in a real shallow aperture.
    dw.cut(body,dw.box('Temporary glovebox recess',(.360,-.377,1.066),(.337,.090,.125),None,c,r))
    outer=rect_y(.360,-.374,1.066,.344,.132,.008);inner=dw.inset(outer,.006)
    dw.ring('Dash | glovebox surround',outer,inner,(0,-.026,0),m['dark'],c,r)
    dw.solid('Dash | glovebox lid',[(x,y-.005,z) for x,y,z in dw.inset(inner,.0015)],(0,-.014,0),m['pad'],c,r)
    dw.box('Dash | recessed glovebox latch',(.36,-.367,1.10),(.073,.010,.018),m['dark'],c,r,.003)
    for side in [-1,1]:
        for i in range(8):dw.box('Dash | demister slot',(side*.52+i*.020-.070,-.681,1.180),(.009,.032,.002),m['dial'],c,r,.001)
    # Lower undertray and footwell structure end before the door cards.
    dw.box('Dash | lower knee rail',(0,-.447,.963),(1.54,.066,.034),m['dark'],c,r,.008)
    seal(c);return c

def circle_y(x,y,z,rad,n=48):return [(x+rad*math.cos(i*math.tau/n),y,z+rad*math.sin(i*math.tau/n)) for i in range(n)]
def instruments(s,name='Instrument cassette'):
    c,r=collection(name,s,'instruments');m=palette()
    outer=rect_y(-.410,-.355,1.209,.506,.194,.020);inside=dw.inset(outer,.014)
    dw.ring('Cluster | deep chamfered hood',outer,inside,(0,-.217,0),m['dark'],c,r)
    dw.solid('Cluster | rear shell',[(x,-.573,z) for x,y,z in outer],(0,-.005,0),m['dark'],c,r)
    for x in [-.595,-.225]:dw.box('Cluster | mounting foot',(x,-.50,1.112),(.055,.070,.015),m['dark'],c,r)
    face=dw.solid('Cluster | instrument plate',[(x,-.365,z) for x,y,z in inside],(0,-.011,0),m['pad'],c,r)
    for x,rad,kind in [(-.544,.060,'speed'),(-.370,.060,'rpm'),(-.227,.027,'fuel')]:
        z=1.227 if kind!='fuel' else 1.234
        dw.cut(face,rod('Temporary dial opening',(x,-.40,z),(x,-.32,z),rad+.001,None,c,r,48))
        dw.ring('Gauge | metal rim',circle_y(x,-.356,z,rad+.002),circle_y(x,-.356,z,rad-.004),(0,-.010,0),m['metal'],c,r)
        rod('Gauge | recessed dial',(x,-.380,z),(x,-.372,z),rad-.004,m['dial'],c,r,48)
        for i in range(25 if kind!='fuel' else 9):
            n=24 if kind!='fuel' else 8;a=math.radians(220-260*i/n)
            ro=rad*.84;ri=rad*(.70 if i%3==0 else .77)
            rod('Gauge | scale tick',(x-ri*math.cos(a),-.369,z+ri*math.sin(a)),(x-ro*math.cos(a),-.369,z+ro*math.sin(a)),.0008,m['ivory'],c,r,4)
        angle=math.radians(178 if kind=='speed' else 159 if kind=='rpm' else 84)
        rod('Gauge | orange pointer',(x,-.366,z),(x-rad*.69*math.cos(angle),-.366,z+rad*.69*math.sin(angle)),.0014,m['orange'],c,r,6)
        rod('Gauge | centre pin',(x,-.370,z),(x,-.363,z),.0037,m['dark'],c,r,12)
        if kind!='fuel':
            for i,lab in enumerate(['0','40','80','120','160'] if kind=='speed' else ['0','2','4','6','8']):
                a=math.radians(220-260*i/4);text_y('Gauge | numerals',lab,(x-rad*.53*math.cos(a),-.368,z+rad*.53*math.sin(a)),.0085,m['ivory'],c,r)
            text_y('Gauge | units','km/h' if kind=='speed' else 'x1000',(x,-.368,z-.020),.007,m['ivory'],c,r)
        rod('Gauge | clear inset glass',(x,-.358,z),(x,-.355,z),rad-.005,m['glass'],c,r,48)
    for i in range(4):
        dw.box('Cluster | telltale recess',(-.245+i*.018,-.359,1.161),(.012,.008,.010),m['dial'],c,r,.001)
        dw.box('Cluster | unlit telltale',(-.245+i*.018,-.354,1.161),(.007,.001,.005),m['orange'] if i==0 else m['ivory'],c,r)
    seal(c);return c

WHEEL_CENTER=Vector((-.410,-.154,1.090));WN=Vector((0,.92,.392)).normalized();WU=Vector((1,0,0));WV=Vector((0,-WN.z,WN.y))
def steering(s,name='Steering and pedals'):
    c,r=collection(name,s,'steering');m=palette();center=WHEEL_CENTER;rad=s['wheel_radius'];vv=[];ff=[]
    for i in range(48):
        a=i*math.tau/48;d=WU*math.cos(a)+WV*math.sin(a)
        for j in range(8):
            b=j*math.tau/8;vv.append(tuple(center+d*(rad+.014*math.cos(b))+WN*.014*math.sin(b)))
    for i in range(48):
        for j in range(8):ff.append((i*8+j,((i+1)%48)*8+j,((i+1)%48)*8+(j+1)%8,i*8+(j+1)%8))
    rim=wf.mesh('Steering | shaped rim',vv,ff,m['pad'],c,r)
    for p in rim.data.polygons:p.use_smooth=True
    for angle in [30,150,270]:
        a=math.radians(angle);d=WU*math.cos(a)+WV*math.sin(a);t=-WU*math.sin(a)+WV*math.cos(a)
        pts=[center+d*.030+t*.022,center+d*(rad-.010)+t*.017,center+d*(rad-.010)-t*.017,center+d*.030-t*.022]
        dw.solid('Steering | tapered spoke',[tuple(p+WN*.011) for p in pts],tuple(-WN*.021),m['dark'],c,r)
    rod('Steering | column',(-.410,-.464,.958),tuple(center-WN*.009),.022,m['metal'],c,r)
    rod('Steering | column shroud',tuple(center-WN*.193),tuple(center-WN*.039),.039,m['dark'],c,r,12)
    rod('Steering | hub',tuple(center-WN*.025),tuple(center+WN*.021),.053,m['dark'],c,r,16)
    rod('Steering | horn pad',tuple(center+WN*.019),tuple(center+WN*.037),.041,m['pad'],c,r,12)
    for side in [-1,1]:
        p=center-WN*.118+WU*(side*.029);q=p+WU*(side*.096)+WV*.015
        rod('Steering | control stalk',tuple(p),tuple(q),.0045,m['metal'],c,r,8)
        rod('Steering | stalk grip',tuple(q-WU*side*.022),tuple(q+WU*side*.015),.011,m['dark'],c,r,10)
    for x,w,z in [(-.563,.069,.694),(-.427,.075,.694),(-.289,.034,.703)]:
        rod('Pedal | upper arm',(x,-.713,.910),(x,-.578,z),.009,m['metal'],c,r,8)
        dw.box('Pedal | rubber pad',(x,-.569,z),(w,.026,.092),m['dark'],c,r,.006)
        for dz in [-.027,-.013,0,.013,.027]:dw.box('Pedal | grip rib',(x,-.553,z+dz),(w-.012,.004,.003),m['pad'],c,r)
    seal(c);return c

def console(s,name='Centre stack and tunnel'):
    c,r=collection(name,s,'console');m=palette()
    stack=dw.box('Console | stack carrier',(.030,-.407,1.016),(.262,.103,.279),m['dark'],c,r,.012)
    dw.cut(stack,dw.box('Temporary central vent',(.030,-.380,1.111),(.218,.15,.063),None,c,r));vent('Console vent',.030,-.350,1.111,.232,.073,m,c,r)
    dw.box('Console | radio recess',(.030,-.349,1.031),(.222,.015,.048),m['dial'],c,r,.003)
    dw.box('Console | radio face',(.030,-.338,1.031),(.207,.010,.035),m['pad'],c,r,.002)
    dw.box('Console | radio scale',(.017,-.332,1.040),(.107,.002,.010),m['dark'],c,r)
    text_y('Console | radio marking','FM  88  96  104',(.017,-.329,1.040),.006,m['ivory'],c,r)
    for x in [-.057,.112]:rod('Console | radio knob',(x,-.340,1.031),(x,-.324,1.031),.010,m['dark'],c,r,16)
    for x in [-.05,.03,.11]:
        rod('Console | heater dial',(x,-.368,.967),(x,-.337,.967),.021,m['pad'],c,r,16)
        dw.box('Console | heater pointer',(x,-.334,.977),(.002,.003,.009),m['ivory'],c,r)
    text_y('Console | climate legend','TEMP     FAN     AIR',(.030,-.346,.930),.010,m['ivory'],c,r)
    yz=[(-.350,.875),(-.209,.762),(.302,.713),(.348,.687),(.348,.555),(-.350,.555)]
    prism_x('Console | sloping tunnel',yz,-.137,.146,m['dark'],c,r)
    # Four progressively smaller boot rings give the lever a seated bellows.
    for i in range(4):dw.box('Console | gear boot',(-.035,-.010,.751+i*.011),(.114-i*.017,.110-i*.014,.019),m['pad'],c,r,.006)
    rod('Console | gear lever',(-.035,-.010,.772),(-.044,.008,.945),.009,m['metal'],c,r)
    rod('Console | gear knob',(-.044,.008,.934),(-.044,.008,.967),.025,m['dark'],c,r,16)
    dw.box('Console | transfer boot',(.086,-.105,.793),(.065,.077,.025),m['pad'],c,r,.008)
    rod('Console | transfer lever',(.086,-.105,.796),(.079,-.075,.886),.007,m['metal'],c,r)
    rod('Console | transfer knob',(.079,-.075,.879),(.079,-.075,.902),.018,m['dark'],c,r)
    rod('Console | handbrake',(.088,.137,.735),(.087,.287,.792),.012,m['dark'],c,r)
    dw.box('Console | rear storage rim',(0,.265,.720),(.195,.124,.018),m['pad'],c,r,.006)
    dw.box('Console | storage recess',(0,.265,.731),(.157,.089,.007),m['dial'],c,r,.004)
    seal(c);return c

def front_seat(s,name='Front seat'):
    c,r=collection(name,s,'front_seat');m=palette();x=.432;t=s['slide'];xs=[-.275,-.225,-.180,0,.180,.225,.275];heights=[0,.026,.012,0,.012,.026,0]
    for dx in [-.170,.170]:
        for yy in [-.168,.200]:
            ob=dw.box('Seat | fixed floor foot',(x+dx,yy,.540),(.059,.069,.020),m['metal'],c,r,.002);ob['fixed_mount']=True
        ob=dw.box('Seat | fixed floor rail',(x+dx,.018,.562),(.042,.472,.035),m['metal'],c,r,.004);ob['fixed_mount']=True
        dw.box('Seat | sliding runner',(x+dx,.023+t,.596),(.046,.395,.034),m['dark'],c,r,.004)
    dw.box('Seat | base frame',(x,.017+t,.643),(.485,.424,.065),m['dark'],c,r,.009)
    rows=[(-.230,.720),(-.195,.775),(.185,.763),(.240,.724)]
    front=[(x+dx,y+t,z+h) for y,z in rows for dx,h in zip(xs,heights)];back=[(xx,yy,.671) for xx,yy,zz in front]
    ob=closed_grid('Seat | sculpted cushion',front,7,4,back,m['bolster'],c,r);ob.data.materials.append(m['fabric'])
    for j in range(3):
        for i in [2,3]:ob.data.polygons[2*(j*6+i)].material_index=1
    zrows=[(.739,.212),(.791,.220),(1.243,.337),(1.304,.354)];offset=[0,-.029,-.032,-.005,-.032,-.029,0]
    front=[(x+dx,y+t+o,z) for z,y in zrows for dx,o in zip(xs,offset)];back=[(xx,yy+.086,zz) for xx,yy,zz in front]
    ob=closed_grid('Seat | contoured backrest',front,7,4,back,m['bolster'],c,r);ob.data.materials.append(m['fabric'])
    for j in range(3):
        for i in [2,3]:ob.data.polygons[2*(j*6+i)].material_index=1
    for dx in [-.120,-.060,0,.060,.120]:
        h=dw.lerp(dx,list(zip(xs,heights)))
        rod('Seat | cushion stitched channel',(x+dx,-.169+t,.775+(-.169+.195)*(-.012/.380)+h+.0007),(x+dx,.158+t,.775+(.158+.195)*(-.012/.380)+h+.0007),.0009,m['seam'],c,r,4)
    for dx in [-.155,.155]:
        o=dw.lerp(dx,list(zip(xs,offset)))
        rod('Seat | backrest seam',(x+dx,.220+(.840-.791)*(.117/.452)+t+o-.0007,.840),(x+dx,.220+(1.21-.791)*(.117/.452)+t+o-.0007,1.21),.001,m['seam'],c,r,4)
    for dx in [-.092,.092]:rod('Seat | headrest post',(x+dx,.388+t,1.287),(x+dx,.388+t,1.390),.006,m['metal'],c,r)
    dw.solid('Seat | formed headrest',rect_y(x,.350+t,1.417,.324,.163,.021),(0,.088,0),m['bolster'],c,r)
    dw.solid('Seat | headrest insert',rect_y(x,.349+t,1.417,.251,.113,.016),(0,-.003,0),m['fabric'],c,r)
    wf.cylinder('Seat | recline wheel',x+.290,.240+t,.755,.032,.021,m['dark'],c,r,16)
    rod('Seat | buckle stalk',(x-.255,.232+t,.668),(x-.279,.233+t,.788),.007,m['dark'],c,r)
    dw.box('Seat | buckle housing',(x-.279,.233+t,.797),(.033,.043,.049),m['dark'],c,r,.004)
    dw.box('Seat | buckle release',(x-.279,.233+t,.825),(.022,.026,.006),m['red'],c,r,.001)
    seal(c);return c

def rear_bench(s,name='Rear bench'):
    c,r=collection(name,s,'rear_bench');m=palette()
    dw.box('Bench | raised pedestal',(0,.84,.675),(1.10,.46,.283),m['carpet'],c,r,.012)
    for x in [-.477,0,.477]:
        # Separate pads and chamfered bolsters preserve seat divisions in clay.
        dw.box('Bench | cushion bolster',(x,.852,.858),(.469,.527,.085),m['bolster'],c,r,.025)
        dw.box('Bench | inset cloth cushion',(x,.837,.902),(.350,.433,.012),m['fabric'],c,r,.009)
        yz=[(1.083,.863),(1.163,.863),(1.294,1.440),(1.203,1.440)]
        prism_x('Bench | reclined back pad',yz,x-.232,x+.232,m['bolster'],c,r)
        pts=[(x-.170,1.082,.928),(x+.170,1.082,.928),(x+.170,1.182,1.388),(x-.170,1.182,1.388)]
        # Match the front plane of the reclined back exactly rather than floating it.
        pts=[(xx,1.083+(zz-.863)*(.120/.577)-.002,zz) for xx,yy,zz in pts]
        dw.solid('Bench | cloth back panel',pts,(0,.007,0),m['fabric'],c,r)
        for dx in [-.085,.085]:rod('Bench | headrest post',(x+dx,1.247,1.423),(x+dx,1.247,1.508),.005,m['metal'],c,r)
        dw.solid('Bench | headrest',rect_y(x,1.208,1.531,.269,.141,.018),(0,.077,0),m['bolster'],c,r)
        dw.box('Bench | buckle',(x+.175,.993,.924),(.030,.043,.032),m['dark'],c,r,.004)
        dw.box('Bench | release button',(x+.175,.993,.942),(.021,.025,.005),m['red'],c,r)
    seal(c);return c

def door_card(s,name='Interior door card'):
    c,r=collection(name,s,'door_card');m=palette();pos=s['position'];lo,hi=dw.limits(pos);lo+=.024;hi-=.019
    ys=sorted(set([lo,hi]+[y for y,z in dw.ARCH if lo<y<hi]))
    lower=[(.814,y,max(.555,dw.bottom(y,pos)+.028)) for y in ys]
    outline=lower+[(.814,hi,1.143),(.814,lo,1.143)]
    dw.solid('Door card | fitted backing',outline,(.035,0,0),m['dark'],c,r)
    cy=(lo+hi)/2
    dw.solid('Door card | upholstered upper insert',dw.rect_yz(.810,cy,.987,hi-lo-.070,.172,.018),(-.012,0,0),m['fabric'],c,r)
    dw.box('Door card | upper padded rail',(.799,cy,1.116),(.041,hi-lo-.016,.040),m['pad'],c,r,.007)
    arm_y=cy+.048;dw.box('Door card | armrest',(.771,arm_y,.849),(.088,.383,.057),m['bolster'],c,r,.009)
    rod('Door card | pull handle',(.754,arm_y-.132,.898),(.754,arm_y+.073,.948),.012,m['pad'],c,r)
    for yy,zz in [(arm_y-.132,.898),(arm_y+.073,.948)]:rod('Door card | pull standoff',(.807,yy,zz),(.753,yy,zz),.012,m['dark'],c,r)
    release_y=lo+.16;release_z=1.060
    base=next(o for o in c.objects if 'fitted backing' in o.name)
    dw.cut(base,dw.solid('Temporary inner release opening',dw.rect_yz(.88,release_y,release_z,.115,.045),(-.12,0,0),None,c,r))
    # Insert is cut too, so the recess remains real through both material layers.
    pad=next(o for o in c.objects if 'upholstered upper insert' in o.name)
    dw.cut(pad,dw.solid('Temporary fabric release opening',dw.rect_yz(.88,release_y,release_z,.115,.045),(-.12,0,0),None,c,r))
    outer=dw.rect_yz(.794,release_y,release_z,.130,.056,.005);inner=dw.inset(outer,.008)
    dw.ring('Door card | release bezel',outer,inner,(.019,0,0),m['dark'],c,r)
    back=[(.841,y,z) for x,y,z in inner]
    wf.mesh('Door card | release cup',inner+back,[(i,(i+1)%8,(i+1)%8+8,i+8) for i in range(8)]+[tuple(range(8,16))],m['dark'],c,r)
    dw.box('Door card | inner release lever',(.798,release_y,release_z+.007),(.010,.078,.011),m['metal'],c,r,.002)
    # Winder is a visible static assembly, not an operating window mechanism.
    wy=cy+.150;wf.cylinder('Door card | winder pivot',.789,wy,.993,.016,.022,m['pad'],c,r)
    rod('Door card | winder arm',(.775,wy,.993),(.775,wy+.052,.966),.007,m['metal'],c,r,8)
    wf.cylinder('Door card | winder knob',.763,wy+.052,.966,.014,.028,m['dark'],c,r)
    if pos=='front':
        py=cy+.048;pz=.653
        dw.box('Door card | pocket outer wall',(.814,py,pz),(.009,.500,.105),m['dark'],c,r,.004)
        dw.box('Door card | pocket front wall',(.751,py,pz-.004),(.012,.500,.091),m['pad'],c,r,.004)
        dw.box('Door card | pocket bottom',(.780,py,pz-.053),(.065,.500,.009),m['pad'],c,r,.003)
        for yy in [py-.246,py+.246]:dw.box('Door card | pocket end',(.780,yy,pz),(.065,.009,.105),m['pad'],c,r,.002)
        sy=lo+.133;sz=.744;wf.cylinder('Door card | speaker backing',.807,sy,sz,.051,.014,m['dial'],c,r,32)
        ob=wf.revolve('Door card | speaker rim',[(.792,.049),(.798,.054),(.812,.054),(.812,.047),(.792,.047)],m['pad'],c,r,32)
        # Revolve is centred on its own axis; translate this decorative ring to its seat.
        ob.location.y=sy;ob.location.z=sz
        for zz in [-.036,-.024,-.012,0,.012,.024,.036]:
            length=2*math.sqrt(.045**2-zz**2)
            dw.box('Door card | speaker grille bar',(.791,sy,sz+zz),(.007,length,.004),m['pad'],c,r,.001)
    seal(c);return c

def lining(s,name='Cabin floor and lining'):
    c,r=collection(name,s,'lining');m=palette()
    dw.box('Cabin | centre floor',(0,.670,.514),(1.220,2.790,.038),m['carpet'],c,r)
    for side in [-1,1]:
        dw.box('Cabin | front floor wing',(side*.7175,.048,.514),(.215,1.538,.038),m['carpet'],c,r)
        dw.box('Cabin | cargo floor wing',(side*.7175,1.891,.514),(.215,.338,.038),m['carpet'],c,r)
    dw.box('Cabin | rear raised floor lip',(0,2.125,.586),(1.540,.130,.026),m['carpet'],c,r)
    dw.box('Cabin | firewall',(0,-.720,.798),(1.606,.020,.552),m['carpet'],c,r)
    for side in [-1,1]:
        yz=[(1.27+.455*math.cos(math.pi-i*math.pi/12),max(.529,.38+.455*math.sin(math.pi-i*math.pi/12))) for i in range(13)]
        prism_x('Cabin | rear wheel tub inner cap',yz,side*.595,side*.611,m['carpet'],c,r)
        vv=[]
        for x,rad in [(.611,.455),(.829,.455),(.829,.448),(.611,.448)]:
            vv.extend([(side*x,1.27+rad*math.cos(math.pi-i*math.pi/12),max(.529,.38+rad*math.sin(math.pi-i*math.pi/12))) for i in range(13)])
        ff=[(j*13+i,j*13+i+1,((j+1)%4)*13+i+1,((j+1)%4)*13+i) for j in range(4) for i in range(12)]
        ff += [(0,13,26,39),(12,51,38,25)]
        wf.mesh('Cabin | rear wheel tub hollow arch',vv,ff,m['carpet'],c,r)
        dw.box('Cabin | footwell mat',(side*.424,-.393,.538),(.494,.416,.010),m['dark'],c,r,.012)
        for j in range(7):dw.box('Cabin | mat rib',(side*.424,-.548+j*.049,.545),(.436,.012,.004),m['pad'],c,r,.002)
        # Internal pillar trim lies inboard of the protected exterior frames.
        for ya,yb in [(-.694,-.380),(.230,.230),(1.160,1.078)]:
            a=(side*(dw.cp(0,1.184)[0]-.040),ya,1.184);b=(side*(dw.cp(0,1.704)[0]-.040),yb,1.704)
            rod('Cabin | pillar trim',a,b,.015,m['pad'],c,r,8)
        rod('Cabin | parked belt',(side*.777,.248,1.490),(side*.805,.251,.606),.009,m['dark'],c,r,4)
        wf.cylinder('Cabin | belt upper guide',side*.781,.248,1.493,.024,.018,m['dark'],c,r,12)
    cross=[(-.731,1.714),(-.670,1.757),(.670,1.757),(.731,1.714)]
    vv=[(x,y,z) for y in [-.415,1.898] for x,z in cross]
    head=wf.mesh('Cabin | fitted headliner',vv,[(i,i+1,5+i,4+i) for i in range(3)],m['headliner'],c,r)
    bpy.context.view_layer.objects.active=head;mod=head.modifiers.new('Headliner backing','SOLIDIFY');mod.thickness=.009;bpy.ops.object.modifier_apply(modifier=mod.name)
    for x in [-.405,.405]:
        dw.box('Cabin | sun visor',(x,-.398,1.697),(.421,.036,.102),m['headliner'],c,r,.012)
        rod('Cabin | visor hinge',(x-.16,-.400,1.749),(x+.16,-.400,1.749),.006,m['pad'],c,r)
        for xx in [x-.15,x+.15]:rod('Cabin | visor support',(xx,-.400,1.732),(xx,-.400,1.764),.005,m['pad'],c,r)
    rod('Cabin | mirror stalk',(0,-.416,1.749),(0,-.416,1.612),.008,m['dark'],c,r)
    outer=rect_y(0,-.397,1.590,.236,.077,.008);inner=dw.inset(outer,.007)
    dw.ring('Cabin | interior mirror housing',outer,inner,(0,-.025,0),m['dark'],c,r)
    dw.solid('Cabin | interior mirror glass',[(x,y-.003,z) for x,y,z in inner],(0,-.003,0),m['mirror'],c,r)
    seal(c);return c

BUILDERS=dict(dash=dash,instruments=instruments,steering=steering,console=console,front_seat=front_seat,rear_bench=rear_bench,door_card=door_card,lining=lining)
def rebuild(c,s):
    if wf.fingerprint(c)!=c.get('fingerprint'):raise RuntimeError('Manual edits detected; preserve this component as a variant')
    old=json.loads(c['spec']);s=dict(s,center=old['center'],side=old['side'],position=old['position']);kind=c['kind'];validate(s,kind);before=set(bpy.data.collections);name=c.name
    try:
        new=BUILDERS[kind](s,name+' STAGED')
        if not wf.component_report(new)['finite']:raise RuntimeError('Invalid staged component')
    except Exception:
        for cc in set(bpy.data.collections)-before:wf.remove_collection(cc)
        raise
    wf.remove_collection(c);new.name=name;seal(new);return new
def report(parts):
    bpy.context.view_layer.update();closed={};contacts=[]
    for c in parts:
        for o in c.objects:
            if o.type=='MESH' and any(t in o.name for t in ['shaped carrier','deep chamfered hood','sculpted cushion','contoured backrest','fitted backing','shaped rim','rear wheel tub']):
                bm=bmesh.new();bm.from_mesh(o.data);closed[o.name]=all(e.is_manifold for e in bm.edges);bm.free()
    # Moving-seat controls must remain clear of cards and centre console.
    fixed=[o for c in parts if c['kind'] in ['door_card','console'] for o in c.objects if o.type=='MESH'];trees={o:wf.tree(o) for o in fixed}
    for c in [c for c in parts if c['kind']=='front_seat']:
        for o in c.objects:
            if o.type!='MESH':continue
            tr=wf.tree(o)
            for other,tree in trees.items():
                if tr.overlap(tree):contacts.append([o.name,other.name])
    return dict(closed_selected_meshes=closed,seat_card_console_intersections=contacts,components={c.name:wf.component_report(c) for c in parts},
        scope='Static cockpit geometry and selected seat/console/card surfaces. No human ergonomics, steering sweep, restraints, operating controls or game export certification.')
class GTCI_Settings(bpy.types.PropertyGroup):
    slide:bpy.props.FloatProperty(name='Front seat offset',default=0,min=-.035,max=.035,unit='LENGTH')
    wheel_radius:bpy.props.FloatProperty(name='Steering radius',default=.176,min=.165,max=.185,unit='LENGTH')
class GTCI_OT_Rebuild(bpy.types.Operator):
    bl_idname='gtci.rebuild';bl_label='Rebuild selected cockpit part';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        c=next((c for c in context.active_object.users_collection if c.get('gt_owner')==OWNER),None) if context.active_object else None
        if not c:self.report({'ERROR'},'Select a cockpit component');return {'CANCELLED'}
        s=json.loads(c['spec'])
        if c['kind']=='front_seat':s['slide']=context.scene.gtci.slide
        if c['kind']=='steering':s['wheel_radius']=context.scene.gtci.wheel_radius
        try:rebuild(c,s)
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
        return {'FINISHED'}
class GTCI_PT_Panel(bpy.types.Panel):
    bl_label='Cockpit Workshop';bl_idname='GTCI_PT_panel';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='GT Parts'
    def draw(self,context):
        l=self.layout;l.prop(context.scene.gtci,'slide');l.prop(context.scene.gtci,'wheel_radius');l.operator('gtci.rebuild');l.label(text='Static fit; direct edits protected.')
CLASSES=[GTCI_Settings,GTCI_OT_Rebuild,GTCI_PT_Panel]
def register():
    if hasattr(bpy.types.Scene,'gtci'):return
    for cls in CLASSES:bpy.utils.register_class(cls)
    bpy.types.Scene.gtci=bpy.props.PointerProperty(type=GTCI_Settings)
def unregister():
    if hasattr(bpy.types.Scene,'gtci'):del bpy.types.Scene.gtci
    for cls in reversed(CLASSES):bpy.utils.unregister_class(cls)
if __name__=='__main__':register()


