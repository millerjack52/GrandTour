"""LC80 replacement: matched panel surfaces, inset glazing, proper rim apertures.
Uses the rejected source only for seats, underbody massing and the studio rig.
Never writes the rejected source. Front -Y; metres; CPU rendering.
"""
import bpy,bmesh,math,json,ast,sys,argparse
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser();ap.add_argument('--version',default='R1');ap.add_argument('--views',default='front,rear,side,cockpit');args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
OUT=ROOT/'Art/Export/LandCruiser'/args.version;OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Art/Export/LandCruiser/05/LandCruiser80.blend'))
scene=bpy.context.scene
for ob in list(bpy.data.objects):
    groups={c.name for c in ob.users_collection}
    keep=bool(groups&{'Studio','Reference','Chassis'}) or ob.name.startswith(('DriverSeat','PassengerSeat','RearBench','RearHeadrest','CargoFloor','Headliner','RearWheelHouse','TransmissionTunnel'))
    if not keep:bpy.data.objects.remove(ob,do_unlink=True)
for ob in bpy.data.objects:
    if ob.name.startswith(('DriverSeat','PassengerSeat')):ob.location.y+=.20
COLS={c.name:c for c in bpy.data.collections};GROUP='Body';PARTS={}
tree=ast.parse((ROOT/'Art/Blender/build_landcruiser.py').read_text())
names={'col','move','P','mat','finish','mesh','box','rod','line','panel','label','loft'}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'vehicle_helpers','exec'))
ivory=bpy.data.materials['LC_IvoryPaint'];trim=bpy.data.materials['LC_Graphite'];rubber=bpy.data.materials['LC_Rubber'];dark=bpy.data.materials['LC_Recess'];steel=bpy.data.materials['LC_Steel'];silver=bpy.data.materials['LC_LampReflector'];amber=bpy.data.materials['LC_AmberLens'];red=bpy.data.materials['LC_RedLens'];glass=bpy.data.materials['LC_Glass'];cloth=bpy.data.materials['LC_Cloth'];dashmat=bpy.data.materials['LC_Dash'];white=bpy.data.materials['LC_Markings'];needle=bpy.data.materials['LC_Needles']
for ma in [ivory,trim,steel,silver]:
    ma.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.43 if ma==ivory else .52
# Paint variation must be continuous in vehicle space, not restarted per panel.
paint_anchor=bpy.data.objects.new('PaintCoordinates',None);col('Reference').objects.link(paint_anchor)
for n in ivory.node_tree.nodes:
    if n.type=='TEX_COORD':
        n.object=paint_anchor
        for link in list(ivory.node_tree.links):
            if link.from_node==n:ivory.node_tree.links.new(n.outputs['Object'],link.to_socket)
    if n.type=='TEX_NOISE':n.inputs['Scale'].default_value=1.25
    if n.type=='VALTORGB':
        n.color_ramp.elements[0].color=(.445,.395,.292,1);n.color_ramp.elements[1].color=(.49,.44,.327,1)
def skin(name,vs,fs,ma,thick=.018):
    o=mesh(name,vs,fs,ma,smooth=True)
    if thick:
        m=o.modifiers.new('Metal thickness','SOLIDIFY');m.thickness=thick
    return o
def side_normals(o,s):
    normals=[]
    for ve in o.data.vertices:
        u,z=-ve.co.y,ve.co.z;d=.002
        du=(width(u+d,z)-width(u-d,z))/(2*d);dz=(width(u,z+d)-width(u,z-d))/(2*d)
        normals.append(tuple(Vector((s,du,-dz)).normalized()))
    o.data.normals_split_custom_set_from_vertices(normals)
def interp(x,pts):
    for (a,b),(c,d) in zip(pts,pts[1:]):
        if x<=c:return b+(d-b)*max(0,(x-a)/(c-a))
    return pts[-1][1]
def width(u,z):
    # A controlled section with level character lines. The old arch-relative
    # rows crossed section changes diagonally, giving the doors a dented look.
    base=interp(z,[(.48,.846),(.56,.873),(.64,.892),(.735,.905),(.80,.914),(.93,.918),(1.07,.918),(1.145,.913),(1.20,.895),(1.25,.874),(1.28,.864)])
    end=.075*max(0,(u-1.91)/.30)**2+.060*max(0,(-u-2.13)/.29)**2
    return base-end
def top(u):return interp(u,[(-2.42,1.24),(-2.20,1.28),(.78,1.28),(1.83,1.23),(2.20,1.125)])
def bottom(u):
    z=.505
    for a in [-1.425,1.425]:
        d=abs(u-a)
        if d<.475:z=max(z,.415+math.sqrt(.475*.475-d*d))
    return z
def contour(poly,r=.05,n=3):
    out=[]
    for i,p in enumerate(poly):
        p=Vector(p);a=Vector(poly[i-1]);b=Vector(poly[(i+1)%len(poly)])
        s=p+(a-p).normalized()*min(r,(a-p).length*.22);e=p+(b-p).normalized()*min(r,(b-p).length*.22)
        for k in range(n+1):
            t=k/n;out.append(tuple((1-t)**2*s+2*(1-t)*t*p+t*t*e))
    return out
def ring(name,a,b,ma):
    n=len(a);return skin(name,a+b,[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],ma,.012)
def glazing(name,outer,inner,project):
    outer=contour(outer,.018,3);inner=contour(inner,.055,3)
    ring(name+'_Frame',[project(p) for p in outer],[project(p) for p in inner],ivory)
    centre=sum((Vector(v) for v in inner),Vector((0,0)))/len(inner)
    inset=[tuple(centre+(Vector(v)-centre)*.958) for v in inner]
    ring(name+'_Seal',[project(p) for p in inner],[project(p,-.003) for p in inset],rubber)
    panel(name+'_Glass',[project(p,-.007) for p in inset],glass,.004,0)

# Side surfaces follow one shared section definition, with small actual panel gaps.
for s,side in [(1,'L'),(-1,'R')]:
    for name,lo,hi,group in [('Wing',.778,2.20,'Body'),('FrontDoor',-.397,.774,'Door_F'+side),('RearDoor',-1.348,-.401,'Door_R'+side),('Quarter',-2.42,-1.352,'Body')]:
        GROUP=group;us={lo,hi}
        for u in [i*.11 for i in range(-23,22)]+[a+.475*math.cos(math.pi*k/20) for a in [-1.425,1.425] for k in range(21)]:
            if lo<u<hi:us.add(u)
        vs=[];fs=[];us=sorted(us)
        rows=[.48,.56,.64,.735,.80,.93,1.07,1.145,1.20,1.25,1.28,1.34]
        def clipped(poly,fn):
            out=[]
            for p,q in zip(poly,poly[1:]+poly[:1]):
                dp,dq=fn(p),fn(q)
                if dp>=0:out.append(p)
                if (dp>=0)!=(dq>=0):
                    t=dp/(dp-dq);out.append((p[0]+t*(q[0]-p[0]),p[1]+t*(q[1]-p[1])))
            return out
        for a,b in zip(us,us[1:]):
            for z0,z1 in zip(rows,rows[1:]):
                poly=[(a,z0),(b,z0),(b,z1),(a,z1)]
                poly=clipped(poly,lambda p:p[1]-interp(p[0],[(a,bottom(a)),(b,bottom(b))]))
                if not poly:continue
                poly=clipped(poly,lambda p:interp(p[0],[(a,top(a)),(b,top(b))])-p[1])
                if len(poly)<3:continue
                start=len(vs);vs.extend((u,s*width(u,z),z) for u,z in poly);fs.append(tuple(range(start,len(vs))))
        body=skin(name+'Skin_'+side,vs,fs,ivory);side_normals(body,s)
        # Trim covers the lower surface; upper boundary is coherent across all panels.
        cvs=[]
        for u in us:
            for z in [bottom(u),max(bottom(u),.735)]:cvs.append((u,s*(width(u,z)+.002),z))
        body=skin(name+'Cladding_'+side,cvs,[(i*2,i*2+2,i*2+3,i*2+1) for i in range(len(us)-1) if abs(cvs[i*2][2]-cvs[i*2+1][2])+abs(cvs[i*2+2][2]-cvs[i*2+3][2])>.0001],trim,.010);side_normals(body,s)
        if 'Door' in name:
            u=lo+.155
            box('HandleWell_'+name+side,(u,s*.919,1.166),(.137,.008,.041),dark,.005)
            box('Handle_'+name+side,(u+.005,s*.928,1.175),(.111,.022,.019),trim,.006,2)
            box('SideMoulding_'+name+side,((lo+hi)/2,s*.918,.785),(hi-lo-.022,.014,.029),trim,.006,2)
            # A narrow rubber wipe at the bottom of the side glass.
            line('WindowWipe_'+name+side,[(lo+.045,s*.861,1.302),(hi-.070,s*.861,1.302)],.005,rubber)
    GROUP='Body'
    for axle,tag in [(1.425,'F'),(-1.425,'R')]:
        # Broad body-coloured compound flare, not a detached black torus.
        vs=[]
        for k in range(23):
            a=.17+(math.pi-.34)*k/22
            for r,v in [(.472,.894),(.480,.942),(.509,.949),(.575,.912),(.610,.89)]:
                u=axle+r*math.cos(a);z=.415+r*math.sin(a)
                v=v if r<.575 else min(v,width(u,z)+.012)
                vs.append((u,s*v,z))
        fs=[(k*5+j,k*5+j+1,(k+1)*5+j+1,(k+1)*5+j) for k in range(22) for j in range(4)]
        # Rear flare is partitioned with the door so it can open cleanly.
        if tag=='R':
            for door in [False,True]:
                GROUP='Door_R'+side if door else 'Body'
                chosen=[f for f in fs if (sum(vs[i][0] for i in f)/4>-1.35)==door]
                o=skin('Flare_'+tag+side+str(door),vs,chosen,ivory)
        else:skin('Flare_'+tag+side,vs,fs,ivory)
        GROUP='Body';vs=[]
        for k in range(23):
            a=math.pi*k/22
            for v in [.55,.91]:vs.append((axle+.474*math.cos(a),s*v,.415+.474*math.sin(a)))
        skin('Liner_'+tag+side,vs,[(k*2,k*2+2,k*2+3,k*2+1) for k in range(22)],rubber,.006)
        box('Mudflap_'+tag+side,(axle-.48,s*.78,.41),(.022,.25,.29),rubber,.005)
    box('Sill_'+side,(-.29,s*.911,.51),(1.70,.102,.068),trim,.015,2)
    box('Step_'+side,(-.40,s*.953,.47),(1.59,.13,.054),trim,.02,2)
    for i in [-.025,.025]:line('StepRib'+side+str(i),[(.34,s*(.953+i),.50),(-1.14,s*(.953+i),.50)],.004,steel)

# Bonnet cross-sections have a domed centre and rolled leading edge.
GROUP='Hood'
loft('Bonnet',[(u,width(u,top(u))-.003,top(u)-.001,top(u)+rise) for u,rise in [(.79,.037),(1.03,.055),(1.65,.060),(1.92,.054),(2.08,.041),(2.165,.028),(2.20,.019)]],ivory)
GROUP='Body';loft('Scuttle',[(.695,.867,1.291,1.325),(.787,.856,1.281,1.319)],ivory)
# Nose fascia curved around both corners as a continuous 3D surface.
vs=[]
for v in [-.88,-.845,-.79,-.64,0,.64,.79,.845,.88]:
    u=2.22-.17*(abs(v)/.88)**6
    for z in [.76,.805,1.11,1.16-.045*(abs(v)/.88)**3]:vs.append((u,v,z))
skin('NoseFascia',vs,[(k*4+j,k*4+j+1,k*4+j+5,k*4+j+4) for k in range(8) for j in range(3)],ivory)
box('FrontBumper',(2.20,0,.68),(.26,1.89,.20),trim,.07,3)
box('BumperLower',(2.16,0,.551),(.21,1.71,.075),rubber,.026,2)
box('RearBumper',(-2.405,0,.651),(.215,1.87,.215),trim,.06,3)
for n in ['FrontBumper','BumperLower','RearBumper']:
    for p in bpy.data.objects[n].data.polygons:p.use_smooth=True
# The bumper has a recessed centre intake and distinct end caps, rather than
# reading as a single faceted block.
box('BumperIntake',(2.332,0,.719),(.008,.80,.039),dark,.006,2)
for v in [-.27,0,.27]:box('BumperIntakeRib'+str(v),(2.340,v,.719),(.009,.016,.032),trim,.002)
for s in [-1,1]:
    box('BumperCapSeam'+str(s),(2.330,s*.788,.685),(.006,.008,.095),rubber,.002)
    box('RearBumperTread'+str(s),(-2.388,s*.515,.762),(.128,.465,.006),rubber,.002)
box('GrilleFrame',(2.234,0,1.003),(.027,.915,.263),steel,.010,2)
box('GrilleRecess',(2.252,0,1.003),(.012,.870,.228),dark,.004,2)
for z in [.927,.977,1.027,1.077]:box('GrilleBar'+str(z),(2.268,0,z),(.020,.855,.013),trim,.006,2)
for v in [-.30,-.15,0,.15,.30]:box('GrilleBrace'+str(v),(2.261,v,1.003),(.012,.008,.208),trim,.003)
box('BadgeBase',(2.281,0,1.008),(.010,.253,.055),dark,.004)
label('Badge','TOYOTA',(2.289,0,1.008),.041,steel)
box('FrontNumberPlate',(2.338,0,.664),(.008,.29,.084),white,.003)
label('PlateText','GRAND TOUR',(2.344,0,.664),.027,dark)
for s in [-1,1]:
    # Broad rectangular lenses, integrated into fascia rather than four exposed cylinders.
    box('HeadlampGasket'+str(s),(2.208,s*.636,1.012),(.034,.323,.232),rubber,.014,2)
    box('HeadlampReflector'+str(s),(2.229,s*.629,1.02),(.018,.283,.203),silver,.007,2)
    for i in range(11):box('LensFlute'+str(s)+str(i),(2.240,s*.629+(i-5)*.024,1.02),(.002,.001,.172),steel,.0003)
    for z in [.969,1.022,1.071]:box('LensCross'+str(s)+str(z),(2.24,s*.629,z),(.002,.265,.001),steel,.0003)
    box('CornerLamp'+str(s),(2.168,s*.824,1.026),(.055,.087,.206),silver,.018,2)
    box('AmberMarker'+str(s),(2.204,s*.638,.849),(.018,.207,.05),amber,.008,2)
    box('SideMarker'+str(s),(.99,s*.916,1.17),(.068,.015,.029),amber,.005)

# Glazing/frame apertures are built together from rounded contours.
def side_project(s):
    def project(p,off=0):
        u,z=p;v=interp(z,[(1.25,.868),(1.32,.865),(1.75,.797),(1.85,.765)])
        return (u,s*(v+off),z)
    return project
for s,side in [(1,'L'),(-1,'R')]:
    project=side_project(s)
    GROUP='Door_F'+side
    glazing('DoorFrontWindow_'+side,[(.77,1.276),(-.397,1.276),(-.397,1.823),(.278,1.810)],[(.676,1.319),(-.352,1.319),(-.352,1.771),(.243,1.766)],project)
    GROUP='Door_R'+side
    glazing('DoorRearWindow_'+side,[(-.401,1.276),(-1.348,1.276),(-1.348,1.827),(-.401,1.823)],[(-.447,1.319),(-1.295,1.319),(-1.295,1.771),(-.447,1.771)],project)
    GROUP='Body'
    glazing('QuarterWindow_'+side,[(-1.352,1.276),(-2.409,1.26),(-2.278,1.80),(-1.352,1.827)],[(-1.416,1.324),(-2.320,1.305),(-2.221,1.745),(-1.416,1.774)],project)
    line('RainGutter_'+side,[(.25,s*.784,1.82),(-2.26,s*.784,1.82)],.009,trim)
    GROUP='Door_F'+side
    box('MirrorHousing_'+side,(.60,s*1.036,1.343),(.115,.179,.135),trim,.033,3)
    box('MirrorGlass_'+side,(.536,s*1.036,1.343),(.006,.147,.108),silver,.002,2)
    rod('MirrorMount_'+side,(.658,s*.863,1.319),(.615,s*.993,1.323),.021,trim,8)
    panel('MirrorBase_'+side,[(.685,s*.868,1.314),(.537,s*.868,1.314),(.565,s*.851,1.451)],trim,.010,.003)
GROUP='Body'
loft('Roof',[(-2.300,.720,1.79,1.815),(-2.223,.776,1.83,1.877),(-1.90,.787,1.835,1.890),(.195,.780,1.826,1.888),(.293,.731,1.791,1.824)],ivory)
def front_proj(p,off=0):
    v,z=p;u=interp(z,[(1.27,.760),(1.82,.268)])+.028*(1-(abs(v)/.82)**2)
    return (u+off,v,z)
glazing('Windscreen',[(-.874,1.282),(.874,1.282),(.767,1.817),(-.767,1.817)],[(-.813,1.315),(.813,1.315),(.717,1.767),(-.717,1.767)],front_proj)
for s in [-1,1]:
    line('WiperArm'+str(s),[(.76,s*.42,1.31),(.717,s*.26,1.352)],.006,trim)
    line('WiperBlade'+str(s),[(.714,s*.06,1.355),(.714,s*.46,1.355)],.008,rubber)
GROUP='TailgateUpper'
def rear_proj(p,off=0):v,z=p;return (-2.438+(z-1.26)*.244-off,v,z)
glazing('RearGlass',[(-.867,1.261),(.867,1.261),(.751,1.817),(-.751,1.817)],[(-.795,1.332),(.795,1.332),(.700,1.754),(-.700,1.754)],rear_proj)
line('RearWiper',[(-2.435,-.19,1.33),(-2.416,.25,1.389)],.010,trim)
GROUP='TailgateLower'
box('Tailgate',(-2.423,0,1.046),(.065,1.61,.427),ivory,.025,3)
box('RearPlateWell',(-2.461,0,1.035),(.008,.398,.16),trim,.003)
box('RearPlate',(-2.467,0,1.035),(.005,.318,.101),white,.002)
label('RearPlateText','GRAND TOUR',(-2.472,0,1.035),.025,dark,False)
box('GateHandle',(-2.466,0,1.185),(.021,.39,.039),trim,.008,2)
GROUP='Body'
for s,side in [(1,'L'),(-1,'R')]:
    # Short continuation of the waist moulding on the fixed quarter panel.
    line('QuarterMoulding_'+side,[(-1.94,s*.919,.785),(-2.26,s*.913,.785)],.011,trim)
# Recessed fuel flap, sized to read without a heavy outline.
fuel=[(-1.95,1.08),(-2.20,1.08),(-2.20,1.12),(-2.20,1.16),(-2.20,1.20),(-2.20,1.22),(-1.95,1.22),(-1.95,1.20),(-1.95,1.16),(-1.95,1.12)]
line('FuelFlapSeam',[(u,width(u,z)+.002,z) for u,z in fuel+[fuel[0]]],.0018,trim)
for s in [-1,1]:
    box('RearCorner'+str(s),(-2.385,s*.817,1.04),(.09,.144,.445),ivory,.032,3)
    box('TailLampSeat'+str(s),(-2.441,s*.813,1.035),(.021,.144,.375),dark,.008,2)
    for z,h,ma in [(1.171,.072,amber),(1.093,.061,silver),(1.003,.104,red),(.909,.063,red)]:box('TailLens'+str(s)+str(z),(-2.456,s*.813,z),(.018,.127,h),ma,.006,2)
    box('BumperReflector'+str(s),(-2.518,s*.68,.655),(.008,.093,.035),red,.003)
    rod('TowLoop'+str(s),(2.135,s*.52,.459),(2.18,s*.52,.459),.033,steel,8)

# Proper recessed rims. Model one wheel and instance its finished mesh at the four hubs.
GROUP='Wheel_FL';u=1.425;v=.80;z=.415
def radial(name,profile,n,ma):
    vs=[(u+r*math.cos(math.tau*k/n),v+d,z+r*math.sin(math.tau*k/n)) for d,r in profile for k in range(n)]
    fs=[(j*n+k,j*n+(k+1)%n,((j+1)%len(profile))*n+(k+1)%n,((j+1)%len(profile))*n+k) for j in range(len(profile)) for k in range(n)]
    return mesh(name,vs,fs,ma,smooth=True)
radial('Tyre',[(-.138,.23),(-.145,.315),(-.12,.381),(-.075,.407),(.075,.407),(.12,.381),(.145,.315),(.138,.23)],32,rubber)
radial('RimBarrel',[(-.13,.227),(.14,.227),(.158,.218),(.13,.206),(-.13,.206)],32,steel)
disc=rod('SteelDish',(u,v+.11,z),(u,v+.127,z),.212,steel,32)
bpy.context.view_layer.objects.active=disc
for k in range(6):
    a=math.tau*k/6;uu=u+.146*math.cos(a);zz=z+.146*math.sin(a)
    cutter=rod('CUT',(uu,v+.06,zz),(uu,v+.18,zz),.040,dark,10)
    mod=disc.modifiers.new('Rim aperture','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cutter
    bpy.context.view_layer.objects.active=disc;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
mod=disc.modifiers.new('Stamped hole edges','BEVEL');mod.width=.0025;mod.segments=1
mod=disc.modifiers.new('Rim normals','WEIGHTED_NORMAL')
rod('RecessBehindRim',(u,v+.058,z),(u,v+.062,z),.205,dark,32)
for k in range(6):
    a=math.tau*k/6;uu=u+.072*math.cos(a);zz=z+.072*math.sin(a)
    rod('Lug'+str(k),(uu,v+.127,zz),(uu,v+.14,zz),.012,steel,6)
rod('Hub',(u,v+.123,z),(u,v+.166,z),.052,trim,12)
vs=[];fs=[]
for k in range(32):
    for row in [-1,1]:
        a=math.tau*(k+.27*(row<0))/32;start=len(vs)
        for r in [.400,.415]:
            for da,d in [(-.066,row*.006),(.066,row*.019),(.077,row*.11),(-.051,row*.115)]:vs.append((u+r*math.cos(a+da),v+d,z+r*math.sin(a+da)))
        for f in [(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]:fs.append(tuple(start+i for i in f))
mesh('Tread',vs,fs,rubber)
bpy.ops.object.select_all(action='DESELECT')
for o in col(GROUP).objects:o.select_set(True)
bpy.context.view_layer.objects.active=disc;bpy.ops.object.convert(target='MESH');bpy.ops.object.join();wheel=bpy.context.object;wheel.name='Wheel_FL'
scene.cursor.location=P((u,v,z));bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
for key,pos in {'FR':(1.425,-.80,.415),'RL':(-1.425,.80,.415),'RR':(-1.425,-.80,.415)}.items():
    o=wheel.copy();o.data=wheel.data;col('Wheel_'+key).objects.link(o);o.name='Wheel_'+key;o.location=P(pos)
    if key.endswith('R'):o.rotation_euler=(Matrix.Rotation(math.pi,4,'Z')@wheel.rotation_euler.to_matrix().to_4x4()).to_euler()
# Underbody spare, no duplicated full tread model.
GROUP='Chassis';box('SpareCradle',(-1.94,0,.408),(.49,.56,.04),trim,.008)
bpy.ops.mesh.primitive_torus_add(major_segments=24,minor_segments=6,location=P((-1.97,0,.435)),major_radius=.295,minor_radius=.105)
o=bpy.context.object;o.name='SpareTyre';finish(o,rubber,smooth=True)

# RHD cockpit: continuous dashboard shell and an inset cluster with legible dial graphics.
GROUP='Interior'
box('DashboardCowl',(.59,0,1.245),(.52,1.64,.075),dashmat,.018,2)
vs=[]
for v in [-.82,-.76,-.53,-.22,.10,.40,.73,.82]:
    for u,z in [(.52,1.27),(.35,1.30),(.20,1.27),(.115,1.19),(.14,.99),(.25,.92),(.42,.96)]:vs.append((u,v,z))
skin('DashboardShell',vs,[(i*7+j,i*7+(j+1)%7,(i+1)*7+(j+1)%7,(i+1)*7+j) for i in range(7) for j in range(7)],dashmat,.018)
box('PassengerGlovebox',(.127,.47,1.071),(.014,.58,.142),trim,.005,2)
box('GloveboxCatch',(.115,.46,1.121),(.009,.076,.018),rubber,.003)
box('CentreConsole',(.08,.12,1.077),(.10,.34,.24),dashmat,.025,3)
for v in [-.747,.034,.223,.743]:
    box('VentOpening'+str(v),(.095,v,1.23),(.013,.128,.055),dark,.004,2)
    for k in range(3):box('VentSlat'+str(v)+str(k),(.086,v,1.212+k*.014),(.009,.115,.003),trim,.001)
box('HVACFace',(.022,.12,1.132),(.012,.292,.06),dark,.004)
box('RadioFace',(.022,.12,1.028),(.012,.292,.058),dark,.004)
box('CassetteSlot',(.011,.12,1.039),(.005,.16,.010),trim,.001)
for v in [-.005,.245]:rod('RadioDial'+str(v),(.007,v,1.028),(.019,v,1.028),.012,trim,12)
for v in [.035,.12,.205]:box('HVACSlider'+str(v),(.009,v,1.13),(.007,.03,.01),white,.002)
box('ClusterHood',(.22,-.447,1.27),(.30,.525,.264),dashmat,.035,3)
box('ClusterFace',(.061,-.447,1.28),(.010,.470,.195),dark,.003,2)
GROUP='Instruments'
def dial(v,z,r,name,maxval,unit):
    rod(name+'_Bezel',(.049,v,z),(.057,v,z),r,trim,32)
    rod(name+'_Face',(.043,v,z),(.048,v,z),r*.91,dark,32)
    steps=9 if name=='Speedometer' else 6 if name=='Tachometer' else 8
    for k in range(steps+1):
        a=math.radians(-40+260*k/steps)
        line(name+'_Tick'+str(k),[(.039,v+math.cos(a)*r*.75,z+math.sin(a)*r*.75),(.039,v+math.cos(a)*r*.86,z+math.sin(a)*r*.86)],.0015,white)
        if r>.04:label(name+'_Number'+str(k),str(round(maxval*k/steps)),(.037,v+math.cos(a)*r*.55,z+math.sin(a)*r*.55),.010,white,False)
    if unit:label(name+'_Unit',unit,(.038,v,z-r*.34),.007,white,False)
    GROUPsave=globals()['GROUP'];globals()['GROUP']='Needle_'+name
    a=math.radians(-33)
    o=line('Needle_'+name,[(.031,v,z),(.031,v+math.cos(a)*r*.72,z+math.sin(a)*r*.72)],.002,needle)
    origin=P((.031,v,z))
    for sp in o.data.splines:
        for p in sp.points:p.co=(*(Vector(p.co[:3])-origin),1)
    o.location=origin
    globals()['GROUP']=GROUPsave
    rod(name+'_Pin',(.026,v,z),(.033,v,z),.004,trim,8)
dial(-.545,1.28,.074,'Speedometer',180,'km/h');dial(-.365,1.28,.074,'Tachometer',6,'x1000')
for v,names in [(-.647,['Fuel','Voltage']),(-.259,['Coolant','Oil'])]:
    for z,n in zip([1.329,1.237],names):dial(v,z,.026,n,1,'')
GROUP='Steering';centre=Vector((-.24,-.455,1.206));vs=[];fs=[]
for k in range(32):
    a=math.tau*k/32
    for j in range(6):
        b=math.tau*j/6;r=.172+.015*math.cos(b);vs.append((centre.x+.015*math.sin(b)-r*math.sin(a)*.26,centre.y+r*math.cos(a),centre.z+r*math.sin(a)*.966))
for k in range(32):
    for j in range(6):fs.append((k*6+j,((k+1)%32)*6+j,((k+1)%32)*6+(j+1)%6,k*6+(j+1)%6))
mesh('SteeringRim',vs,fs,rubber,smooth=True)
box('SteeringHorn',tuple(centre),(.051,.198,.083),trim,.018,3)
for s in [-1,1]:
    skin('WheelSpoke'+str(s),[(centre.x,centre.y+s*.07,centre.z+.022),(centre.x,centre.y+s*.16,centre.z+.031),(centre.x+.028,centre.y+s*.111,centre.z-.115),(centre.x+.018,centre.y+s*.045,centre.z-.068)],[(0,1,2,3)],trim,.02)
GROUP='Interior';rod('SteeringColumn',(.13,-.455,1.09),tuple(centre),.026,trim,12)
for s,side in [(1,'L'),(-1,'R')]:
    for u,g in [(.12,'Door_F'+side),(-.88,'Door_R'+side)]:
        GROUP=g;box('DoorCard'+g,(u,s*.851,1.045),(.79,.025,.39),dashmat,.011,2)
        box('DoorInsert'+g,(u,s*.832,1.13),(.60,.016,.13),cloth,.006,2)
        box('Armrest'+g,(u,s*.788,1.045),(.42,.11,.053),trim,.022,3)
        box('InnerHandle'+g,(u+.21,s*.817,1.165),(.089,.015,.034),dark,.006,2)
        rod('Speaker'+g,(u+.24,s*.829,.936),(u+.24,s*.824,.936),.048,trim,16)
GROUP='Interior'
for u,v,z,n in [(-.14,.018,1.035,'GearLever'),(-.075,-.11,.948,'TransferLever')]:
    box(n+'Boot',(-.02,v,.883),(.12,.086,.064),rubber,.016,2);rod(n+'Shaft',(-.02,v,.895),(u,v,z),.009,steel,8);box(n+'Knob',(u,v,z),(.04,.043,.035),trim,.014,3)
rod('Handbrake',(-.53,-.16,.827),(-.24,-.16,.865),.014,trim,8)
for v in [-.60,-.46,-.30]:box('Pedal'+str(v),(.36,v,.728),(.089,.062,.018),rubber,.005,2)
box('CabinMirror',(.45,0,1.65),(.048,.208,.062),trim,.015,2);box('CabinMirrorGlass',(.422,0,1.65),(.004,.179,.044),silver,.001)
# Keep planar faces calm while bevel strips catch a controlled soft highlight.
for ob in bpy.data.objects:
    if ob.type=='MESH' and ob.name.startswith(('ClusterHood','CentreConsole','SteeringHorn','MirrorHousing','RadioDial','DoorCard','Armrest','GloveboxCatch')):
        for p in ob.data.polygons:p.use_smooth=True
# A closed engine-bay mass prevents seeing through the wheel wells; useful when hood opens.
GROUP='Engine';box('EngineBayFloor',(1.30,0,.735),(1.50,1.52,.04),trim,.01)
box('EngineBlock',(1.25,-.06,.91),(.82,.43,.31),trim,.05,2);box('EngineCover',(1.25,-.06,1.103),(.87,.34,.085),steel,.032,2)
box('Radiator',(1.966,0,.955),(.063,1.15,.32),trim,.014)
box('Battery',(1.29,-.635,.994),(.30,.23,.20),rubber,.02,2);box('Airbox',(1.41,.60,.984),(.37,.29,.21),trim,.03,2)

# Part pivots; all groups use rigid weighting in the export stage.
pivots={'Door_FL':(.774,.868,1.14),'Door_FR':(.774,-.868,1.14),'Door_RL':(-.40,.868,1.14),'Door_RR':(-.40,-.868,1.14),'Hood':(.79,0,1.28),'TailgateUpper':(-2.30,0,1.80),'TailgateLower':(-2.42,0,.835),'Steering':tuple(centre)}
for g,p in pivots.items():
    pa=bpy.data.objects.new(g+'_Pivot',None);col('Pivots').objects.link(pa);pa.location=P(p);bpy.context.view_layer.update()
    for ob in col(g).objects:ob.parent=pa;ob.matrix_parent_inverse=pa.matrix_world.inverted()
scene['Status']='LC80 rebuilt source; export validation separate'
cam=scene.camera;camdata=cam.data
views={'front':((6.2,6.0,3.0),(-.05,0,.98),57),'rear':((-6.6,-5.9,3.0),(-.25,0,1.0),57),'side':((0,8,1.1),(0,0,1.1),55),'cockpit':((-.64,-.455,1.57),(.70,-.22,1.12),18)}
def view(name):
    pos,target,lens=views[name];cam.location=P(pos);cam.rotation_euler=(P(target)-cam.location).to_track_quat('-Z','Y').to_euler();camdata.lens=lens;camdata.type='ORTHO' if name=='side' else 'PERSP';camdata.ortho_scale=5.7
    bpy.data.objects['StudioGround'].hide_render=(name=='side');bpy.data.objects['CabinReviewFill'].hide_render=(name!='cockpit')
view('front');scene.cycles.samples=32;camdata.clip_end=10000
bpy.data.objects['StudioGround'].scale.x=10;bpy.data.objects['StudioGround'].scale.y=10
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'LandCruiser80.blend'))
for name in args.views.split(','):
    view(name);scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True);print('LC_REBUILD_RENDER '+name,flush=True)
print('LC_REBUILD_OK '+str(OUT),flush=True)
