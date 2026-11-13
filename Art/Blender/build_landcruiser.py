"""Independent low-poly 80-series study. Metres; front -Y; vehicle left +X.
Run only in a factory-startup background Blender. Never opens the Range Rover.
CPU Cycles previews, separate articulated groups, deterministic geometry.
"""
import bpy, bmesh, math, json, sys, argparse
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser()
ap.add_argument('--version', default='01')
ap.add_argument('--views', default='front,rear,side,cockpit')
ap.add_argument('--samples', type=int, default=32)
args = ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
OUT = ROOT / 'Art/Export/LandCruiser' / args.version
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for c in list(bpy.data.collections):
    if c.name != 'Collection': bpy.data.collections.remove(c)
scene=bpy.context.scene
scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=1
COLS={}; GROUP='Body'; PARTS={}
def col(name):
    if name not in COLS:
        c=bpy.data.collections.new(name); scene.collection.children.link(c); COLS[name]=c
    return COLS[name]
def move(o, group=None):
    g=group or GROUP
    for c in list(o.users_collection): c.objects.unlink(o)
    col(g).objects.link(o); PARTS[o.name]=g
    return o
def P(p): return Vector((p[1],-p[0],p[2]))
def mat(name,c,rough=.5,metal=0):
    m=bpy.data.materials.new(name); m.diffuse_color=(*c,1); m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*c,1)
    bs.inputs['Roughness'].default_value=rough; bs.inputs['Metallic'].default_value=metal
    return m
ivory=mat('LC_IvoryPaint',(.61,.565,.43),.37,.08)
trim=mat('LC_Graphite',(.068,.079,.083),.58)
rubber=mat('LC_Rubber',(.021,.025,.026),.79)
dark=mat('LC_Recess',(.009,.014,.018),.65)
steel=mat('LC_Steel',(.32,.36,.38),.33,.7)
silver=mat('LC_LampReflector',(.63,.7,.73),.23,.72)
red=mat('LC_RedLens',(.32,.019,.01),.26)
amber=mat('LC_AmberLens',(.72,.24,.017),.3)
cloth=mat('LC_Cloth',(.17,.185,.18),.94)
dashmat=mat('LC_Dash',(.075,.089,.09),.74)
white=mat('LC_Markings',(.69,.74,.7),.6)
needle=mat('LC_Needles',(.86,.22,.037),.47)
glass=mat('LC_Glass',(.68,.80,.86),.07)
bs=glass.node_tree.nodes.get('Principled BSDF'); bs.inputs['Transmission Weight'].default_value=.96; bs.inputs['IOR'].default_value=1.46
# Very broad subtle painted variation, no micro bump or post filter.
ns=ivory.node_tree.nodes; ls=ivory.node_tree.links
noise=ns.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value=3.8; noise.inputs['Detail'].default_value=0
tex=ns.new('ShaderNodeTexCoord'); ls.new(tex.outputs['Generated'],noise.inputs['Vector'])
ramp=ns.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].color=(.40,.36,.265,1); ramp.color_ramp.elements[1].color=(.53,.475,.35,1)
ls.new(noise.outputs['Fac'],ramp.inputs[0]);ls.new(ramp.outputs[0],ns.get('Principled BSDF').inputs['Base Color'])

def finish(o,m,bevel=0,segments=1,smooth=False):
    o.data.materials.append(m)
    if smooth:
        for f in o.data.polygons:f.use_smooth=True
    if bevel:
        mod=o.modifiers.new('Small manufactured edge','BEVEL');mod.width=bevel;mod.segments=segments
        mod=o.modifiers.new('Weighted panel normals','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=40
    return move(o)
def mesh(name,vs,fs,m,bevel=0,smooth=False):
    me=bpy.data.meshes.new(name); me.from_pydata([P(v) for v in vs],[],fs);me.update()
    bm=bmesh.new();bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.0000001)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    o=bpy.data.objects.new(name,me);col(GROUP).objects.link(o)
    return finish(o,m,bevel,smooth=smooth)
def box(name,p,d,m,b=.01,seg=1):
    bpy.ops.mesh.primitive_cube_add(size=1,location=P(p));o=bpy.context.object;o.name=name
    o.dimensions=(d[1],d[0],d[2]);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return finish(o,m,min(b,min(d)*.40),seg)
def rod(name,a,b,r,m,n=8):
    av,bv=P(a),P(b);diff=bv-av
    bpy.ops.mesh.primitive_cylinder_add(vertices=n,radius=r,depth=diff.length,location=(av+bv)/2)
    o=bpy.context.object;o.name=name;o.rotation_euler=diff.to_track_quat('Z','Y').to_euler()
    finish(o,m)
    for f in o.data.polygons:f.use_smooth=(len(f.vertices)==4)
    return o
def line(name,pts,r,m):
    cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.resolution_u=1;cu.bevel_depth=r;cu.bevel_resolution=0
    sp=cu.splines.new('POLY');sp.points.add(len(pts)-1)
    for p,co in zip(sp.points,pts):p.co=(*P(co),1)
    o=bpy.data.objects.new(name,cu);col(GROUP).objects.link(o);cu.materials.append(m);PARTS[o.name]=GROUP;return o
def panel(name,pts,m,thick=.012,bevel=.007):
    o=mesh(name,pts,[tuple(range(len(pts)))],m)
    mod=o.modifiers.new('Panel thickness','SOLIDIFY');mod.thickness=thick
    if bevel:
        mod=o.modifiers.new('Panel edge','BEVEL');mod.width=min(bevel,thick*.40);mod.segments=1
        mod=o.modifiers.new('Panel normals','WEIGHTED_NORMAL')
    return o
def label(name,text,p,size,m,front=True):
    cu=bpy.data.curves.new(name,'FONT');cu.body=text;cu.align_x='CENTER';cu.align_y='CENTER';cu.size=size;cu.extrude=.00025;cu.resolution_u=1
    o=bpy.data.objects.new(name,cu);col(GROUP).objects.link(o);o.location=P(p);o.rotation_euler=(math.pi/2 if front else math.pi/2,0,0 if front else math.pi);cu.materials.append(m);return o
def window(name,pts):
    panel(name,pts,glass,.006,.008)
    line(name+'_Seal',pts+[pts[0]],.018,rubber)
def loft(name,sections,m):
    # sections: longitudinal station, width, edge height, centre height
    vs=[]
    for u,w,ze,zc in sections:
        for t in [-1,-.95,-.78,0,.78,.95,1]:
            z=ze+(zc-ze)*(1-abs(t)**5)
            vs.append((u,t*w,z))
    fs=[]
    for i in range(len(sections)-1):
        for j in range(6):a=i*7+j;fs.append((a,a+1,a+8,a+7))
    o=mesh(name,vs,fs,m,smooth=True);mo=o.modifiers.new('Shell thickness','SOLIDIFY');mo.thickness=.025
    mo=o.modifiers.new('Panel normals','WEIGHTED_NORMAL');return o
def sidewidth(z):
    return .935 if z<1.10 else .935-(z-1.10)*.23
def bodywidth(u,z):
    return sidewidth(z)-.072*max(0,min(1,(u-1.80)/.45))-.026*max(0,min(1,(-u-2.05)/.23))
def bodytop(u):
    return 1.25-.085*max(0,min(1,(u-.62)/1.63))
def lower(u):
    z=.49
    for wc in [-1.425,1.425]:
        d=abs(u-wc)
        if d<.48:z=max(z,.40+math.sqrt(.48**2-d*d))
    return z

# Body side patches explicitly stop at arch openings. No intersecting cubes across tyres.
zones=[('FrontWing',.62,2.25),('FrontDoor',-.43,.615),('RearDoor',-1.32,-.44),('RearQuarter',-2.28,-1.33)]
for side,s in [('L',1),('R',-1)]:
    for zone,lo,hi in zones:
        GROUP=('Door_F'+side if zone=='FrontDoor' else 'Door_R'+side if zone=='RearDoor' else 'Body')
        us={lo,hi}
        for wc in [-1.425,1.425]:
            for k in range(19):
                v=wc+.48*math.cos(math.pi*k/18)
                if lo<v<hi:us.add(v)
        us=sorted(us);vs=[]
        for u in us:
            for z in [lower(u),max(lower(u),.71),.93,1.10,bodytop(u)]:
                vs.append((u,s*bodywidth(u,z),z))
        fs=[]
        for i in range(len(us)-1):
            for j in range(4):
                a=i*5+j
                if (Vector(vs[a])-Vector(vs[a+1])).length+(Vector(vs[a+5])-Vector(vs[a+6])).length>.0001:fs.append((a,a+5,a+6,a+1))
        o=mesh(zone+'_'+side,vs,fs,ivory)
        o.data.materials.append(trim)
        for f in o.data.polygons:
            if max(o.data.vertices[k].co.z for k in f.vertices)<.711:f.material_index=1
        mo=o.modifiers.new('Sheet metal','SOLIDIFY');mo.thickness=.025
        # Lower side rub strip and body crease, deliberately broad enough to read.
        if 'Door' in zone:
            box(zone+'_RubStrip_'+side,((lo+hi)/2,s*.943,.755),(hi-lo-.015,.018,.09),trim,.008)
            line(zone+'_Shoulder_'+side,[(lo,s*.937,1.10),(hi,s*.937,1.10)],.006,ivory)
            box(zone+'_HandleRecess_'+side,(lo+.18,s*.945,1.18),(.145,.012,.065),dark,.012)
            box(zone+'_Handle_'+side,(lo+.18,s*.958,1.184),(.116,.020,.038),steel,.009)
    GROUP='Body'
    for wc,tag in [(1.425,'Front'),(-1.425,'Rear')]:
        vs=[]
        for k in range(19):
            a=.13+(math.pi-.26)*k/18
            for r,v in [(.48,.937),(.49,.995),(.56,.990),(.57,.936)]:
                vs.append((wc+r*math.cos(a),s*v,.40+r*math.sin(a)))
        fs=[]
        for i in range(18):
            for j in range(3):a=i*4+j;fs.append((a,a+4,a+5,a+1))
        o=mesh(tag+'_ArchFlare_'+side,vs,fs,trim,smooth=True);mo=o.modifiers.new('Flare shell','SOLIDIFY');mo.thickness=.012
        # Black inner wheel tub.
        vs=[]
        for k in range(19):
            a=math.pi*k/18
            for v in [.57,.94]:vs.append((wc+.479*math.cos(a),s*v,.40+.479*math.sin(a)))
        mesh(tag+'_WheelLiner_'+side,vs,[(2*k,2*k+1,2*k+3,2*k+2) for k in range(18)],rubber)
        box(tag+'_Mudflap_'+side,(wc-.49,s*.81,.375),(.028,.29,.27),rubber,.005)
    box('SideStep_'+side,(-.40,s*.969,.465),(1.62,.17,.075),trim,.022)
    for i in [-.048,0,.048]:line('StepGrip_'+side+str(i),[(.35,s*(.969+i),.508),(-1.13,s*(.969+i),.508)],.007,rubber)

GROUP='Hood'
loft('Hood',[(.62,.90,1.25,1.29),(.80,.921,1.235,1.28),(1.85,.907,1.215,1.25),(2.24,.855,1.165,1.20)],ivory)
GROUP='Body'
loft('Cowl',[(.48,.899,1.265,1.30),(.61,.90,1.25,1.29)],ivory)
box('FrontFace',(2.215,0,1.02),(.09,1.72,.31),ivory,.055,2)
box('FrontValance',(2.222,0,.824),(.08,1.735,.112),ivory,.028,2)
box('FrontBumper',(2.28,0,.66),(.26,1.89,.25),trim,.065,2)
box('FrontBumperLip',(2.29,0,.515),(.22,1.70,.06),rubber,.015)
box('RearBumper',(-2.30,0,.62),(.22,1.87,.22),trim,.05,2)
box('RearBodyLower',(-2.235,0,.865),(.08,1.75,.26),ivory,.025)
box('GrilleSurround',(2.272,0,1.03),(.036,.99,.29),steel,.023)
box('GrilleInset',(2.296,0,1.032),(.018,.938,.244),dark,.015)
for z in [.94,.987,1.034,1.081,1.128]:box('GrilleSlat_'+str(z),(2.31,0,z),(.022,.92,.014),trim,.005)
box('GrilleBadgeBase',(2.328,0,1.034),(.012,.323,.073),dark,.006)
label('ToyotaBadge','TOYOTA',(2.34,0,1.034),.052,steel)
box('FrontPlate',(2.418,0,.67),(.008,.32,.115),dark,.005)
for s in [-1,1]:
    box('BumperAirSlot'+str(s),(2.417,s*.41,.665),(.009,.20,.07),dark,.01)
    box('FrontLampHousing'+str(s),(2.258,s*.685,1.036),(.045,.368,.251),rubber,.021)
    box('FrontLampLens'+str(s),(2.286,s*.663,1.046),(.016,.264,.205),silver,.018)
    for j in [-1,1]:
        v=s*.663+j*.066
        rod('Reflector'+str(s)+str(j),(2.296,v,1.046),(2.303,v,1.046),.073,steel,12)
        rod('LampCentre'+str(s)+str(j),(2.303,v,1.046),(2.308,v,1.046),.053,silver,12)
    box('FrontIndicator'+str(s),(2.289,s*.842,1.045),(.028,.073,.205),amber,.009)
    box('FrontPositionLamp'+str(s),(2.28,s*.66,.866),(.017,.263,.046),silver,.008)
    box('WingIndicator'+str(s),(.91,s*.941,1.113),(.105,.018,.044),amber,.008)
    rod('TowEye'+str(s),(2.22,s*.58,.405),(2.28,s*.58,.405),.042,steel,8)

# Roof and pillars. Four side openings plus rear quarter glass.
GROUP='Body'
loft('Roof',[(-2.17,.757,1.77,1.795),(-2.06,.80,1.82,1.865),(-.05,.80,1.825,1.88),(.12,.758,1.77,1.80)],ivory)
for s,side in [(1,'L'),(-1,'R')]:
    line('RoofGutter_'+side,[(-2.12,s*.805,1.806),(-.10,s*.805,1.811),(.15,s*.779,1.752)],.015,trim)
    rod('A_Pillar_'+side,(.59,s*.885,1.26),(.105,s*.781,1.775),.038,ivory)
    rod('D_Pillar_'+side,(-2.24,s*.885,1.24),(-2.14,s*.774,1.79),.047,ivory)
    GROUP='Door_F'+side
    panel('FrontDoorHeader_'+side,[(.114,s*.799,1.80),(-.43,s*.807,1.823),(-.43,s*.818,1.745),(.066,s*.799,1.745)],ivory,.021,.008)
    panel('FrontDoorBelt_'+side,[(.595,s*.90,1.25),(-.43,s*.90,1.25),(-.43,s*.883,1.306),(.539,s*.884,1.306)],ivory,.025,.006)
    pts=[(.532,s*.879,1.293),(-.396,s*.881,1.293),(-.396,s*.810,1.755),(.071,s*.791,1.755)]
    window('FrontSideGlass_'+side,pts)
    box('B_PillarFront_'+side,(-.416,s*.845,1.514),(.055,.040,.488),trim,.006)
    GROUP='Door_R'+side
    panel('RearDoorHeader_'+side,[(-.44,s*.807,1.823),(-1.33,s*.807,1.823),(-1.33,s*.818,1.745),(-.44,s*.818,1.745)],ivory,.021,.008)
    panel('RearDoorBelt_'+side,[(-.44,s*.90,1.25),(-1.33,s*.90,1.25),(-1.33,s*.883,1.306),(-.44,s*.883,1.306)],ivory,.025,.006)
    window('RearSideGlass_'+side,[(-.466,s*.881,1.293),(-1.272,s*.881,1.293),(-1.272,s*.813,1.755),(-.466,s*.813,1.755)])
    box('C_Pillar_'+side,(-1.305,s*.844,1.52),(.050,.055,.52),ivory,.007)
    GROUP='Body'
    panel('QuarterHeader_'+side,[(-1.33,s*.807,1.823),(-2.15,s*.786,1.797),(-2.12,s*.803,1.740),(-1.33,s*.818,1.745)],ivory,.021,.008)
    panel('QuarterBelt_'+side,[(-1.33,s*.90,1.25),(-2.235,s*.875,1.25),(-2.19,s*.879,1.306),(-1.33,s*.883,1.306)],ivory,.025,.006)
    window('QuarterGlass_'+side,[(-1.363,s*.881,1.293),(-2.187,s*.872,1.293),(-2.107,s*.795,1.751),(-1.363,s*.813,1.755)])
    for i in range(4):line('RearVent_'+side+str(i),[(-2.217,s*.89,1.31+i*.027),(-2.149,s*.89,1.31+i*.027)],.007,trim)
    GROUP='Door_F'+side
    rod('MirrorStalk_'+side,(.46,s*.89,1.286),(.39,s*1.022,1.316),.019,trim)
    box('MirrorHousing_'+side,(.35,s*1.059,1.383),(.14,.095,.16),trim,.028,2)
    box('MirrorFace_'+side,(.271,s*1.058,1.386),(.006,.070,.122),silver,.011)
GROUP='Body'
window('Windscreen',[(.559,-.831,1.291),(.559,.831,1.291),(.118,.747,1.742),(.118,-.747,1.742)])
for s in [-1,1]:
    line('WiperArm'+str(s),[(.58,s*.40,1.307),(.48,s*.25,1.386)],.009,trim)
    line('WiperBlade'+str(s),[(.49,s*.025,1.377),(.49,s*.43,1.377)],.010,rubber)
GROUP='TailgateUpper'
panel('RearHeader',[(-2.172,-.755,1.788),(-2.172,.755,1.788),(-2.166,.754,1.720),(-2.166,-.754,1.720)],ivory,.025,.008)
panel('RearWindowSill',[(-2.27,-.832,1.30),(-2.27,.832,1.30),(-2.285,.832,1.261),(-2.285,-.832,1.261)],ivory,.025,.008)
window('RearWindow',[(-2.265,.821,1.30),(-2.265,-.821,1.30),(-2.153,-.742,1.731),(-2.153,.742,1.731)])
line('RearWiper',[(-2.274,-.22,1.316),(-2.25,.25,1.396)],.012,trim)
GROUP='TailgateLower'
box('LowerTailgate',(-2.272,0,1.044),(.038,1.49,.443),ivory,.028)
box('RearPlateRecess',(-2.295,0,1.048),(.009,.365,.137),trim,.015)
box('RearPlate',(-2.304,0,1.045),(.005,.311,.107),white,.007)
box('RearHandle',(-2.303,0,1.183),(.026,.415,.043),trim,.012)
GROUP='Body'
for s in [-1,1]:
    box('RearLightHousing'+str(s),(-2.284,s*.815,1.115),(.055,.166,.381),rubber,.02)
    for z,h,ma in [(1.249,.089,amber),(1.161,.064,silver),(1.077,.092,red),(.978,.085,red)]:
        box('RearLens'+str(s)+str(z),(-2.316,s*.815,z),(.020,.141,h),ma,.009)
    box('RearReflector'+str(s),(-2.417,s*.68,.622),(.009,.127,.049),red,.008)
line('FuelFlapSeam',[(-2.015,.935,1.02),(-1.805,.935,1.02),(-1.805,.921,1.193),(-2.015,.921,1.193),(-2.015,.935,1.02)],.0028,trim)

# Wheels: 32 radial segments, shaped sidewalls, discrete broad tread; one reusable mesh per corner.
def wheel(u,v,tag):
    global GROUP
    GROUP='Wheel_'+tag;s=1 if v>0 else -1
    vs=[];profile=[(-.142,.24),(-.14,.32),(-.11,.377),(-.073,.397),(.073,.397),(.11,.377),(.14,.32),(.142,.24)]
    for off,r in profile:
        for k in range(32):
            a=2*math.pi*k/32;vs.append((u+r*math.cos(a),v+off,.40+r*math.sin(a)))
    fs=[]
    for j in range(len(profile)):
        for k in range(32):a=j*32+k;b=j*32+(k+1)%32;c=((j+1)%len(profile))*32+(k+1)%32;d=((j+1)%len(profile))*32+k;fs.append((a,b,c,d))
    mesh('Tyre_'+tag,vs,fs,rubber,smooth=True)
    # Treads are a single economical mesh, 2 chevron rows x32.
    vs=[];fs=[]
    for k in range(32):
        for row in [-1,1]:
            a=2*math.pi*(k+(0.35 if row<0 else 0))/32
            start=len(vs)
            for r in [.393,.407]:
                for da,off in [(-.060,row*.015),(.060,row*.018),(.065,row*.11),(-.065,row*.10)]:
                    vs.append((u+r*math.cos(a+da),v+off,.40+r*math.sin(a+da)))
            for f in [(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]:fs.append(tuple(start+i for i in f))
    mesh('Tread_'+tag,vs,fs,rubber)
    rod('WheelBarrel_'+tag,(u,v-.13,.4),(u,v+.13,.4),.238,steel,24)
    rod('RimFace_'+tag,(u,v+s*.133,.4),(u,v+s*.151,.4),.211,steel,24)
    # Rolled outer rim lip; simple 24 x4 cross-section.
    rvs=[];rfs=[]
    for k in range(24):
        a=math.tau*k/24
        for r,off in [(.212,.15),(.218,.164),(.233,.157),(.237,.14)]:rvs.append((u+r*math.cos(a),v+s*off,.4+r*math.sin(a)))
    for k in range(24):
        for j in range(4):rfs.append((k*4+j,((k+1)%24)*4+j,((k+1)%24)*4+(j+1)%4,k*4+(j+1)%4))
    mesh('RimLip_'+tag,rvs,rfs,steel,smooth=True)
    for k in range(6):
        a=math.pi*k/3;uu=u+.151*math.cos(a);zz=.4+.151*math.sin(a)
        rod('Vent_'+tag+str(k),(uu,v+s*.153,zz),(uu,v+s*.155,zz),.037,dark,8)
        uu=u+.087*math.cos(a);zz=.4+.087*math.sin(a)
        rod('Lug_'+tag+str(k),(uu,v+s*.160,zz),(uu,v+s*.174,zz),.015,steel,6)
    rod('Hub_'+tag,(u,v+s*.152,.4),(u,v+s*.184,.4),.061,trim,12)
    # Apply modifiers and merge materials into one rigid wheel mesh.
    obs=list(col(GROUP).objects);bpy.ops.object.select_all(action='DESELECT')
    for o in obs:o.select_set(True)
    bpy.context.view_layer.objects.active=obs[0];bpy.ops.object.convert(target='MESH');bpy.ops.object.join()
    o=bpy.context.object;o.name='Wheel_'+tag
    scene.cursor.location=P((u,v,.4));bpy.ops.object.origin_set(type='ORIGIN_CURSOR');o['rig_role']='wheel';o['radius_m']=.407
for u,t in [(1.425,'F'),(-1.425,'R')]:
    for v,s in [(.80,'L'),(-.80,'R')]:wheel(u,v,t+s)

# Visible ladder frame/solid axle massing. Not a physics suspension implementation.
GROUP='Chassis'
for v in [-.55,.55]:box('FrameRail'+str(v),(-.04,v,.40),(4.0,.11,.16),trim,.018)
for u in [-1.8,-.4,.7,1.8]:box('Crossmember'+str(u),(u,0,.42),(.11,1.10,.10),trim,.012)
for u in [-1.425,1.425]:
    rod('LiveAxle'+str(u),(u,-.80,.4),(u,.80,.4),.052,trim,10)
    box('Differential'+str(u),(u,-.18,.40),(.24,.27,.20),trim,.065,2)
    for v in [-.56,.56]:rod('Damper'+str(u)+str(v),(u,v,.42),(u-.10,v,.77),.026,steel,8)
rod('Propshaft',(1.425,-.18,.40),(-1.425,-.18,.40),.031,steel,10)
rod('Exhaust',(-2.39,-.64,.40),(-.3,-.64,.40),.024,steel,10)
box('Floorpan',(-.68,0,.62),(3.06,1.62,.07),trim,.025)

# Cabin geometry and recognisable RHD driving controls.
GROUP='Interior'
box('CargoFloor',(-1.71,0,.682),(1.10,1.62,.04),dashmat,.01)
box('Headliner',(-1.02,0,1.80),(2.12,1.50,.04),cloth,.07,2)
box('DashboardMain',(.375,0,1.142),(.37,1.67,.27),dashmat,.045,2)
box('DashboardTop',(.365,0,1.277),(.43,1.69,.07),dashmat,.025,2)
box('Glovebox',(.17,.48,1.105),(.028,.66,.19),trim,.025)
box('GloveboxLatch',(.15,.48,1.17),(.021,.095,.028),rubber,.006)
for v in [-.74,.10,.31,.75]:
    box('DashVent'+str(v),(.143,v,1.25),(.012,.15,.07),dark,.008)
    for j in range(3):box('VentSlat'+str(v)+str(j),(.134,v,1.228+j*.019),(.009,.13,.005),trim,.001)
box('CentreStack',(.151,.17,1.095),(.05,.40,.26),trim,.018)
for z in [1.045,1.14]:
    box('RadioHVAC'+str(z),(.119,.17,z),(.014,.32,.063),dark,.004)
    for v in [.05,.29]:rod('RadioKnob'+str(z)+str(v),(.103,v,z),(.122,v,z),.015,trim,10)
box('TransmissionTunnel',(-.29,0,.79),(1.19,.29,.20),dashmat,.05,2)
def seat(u,v,name):
    box(name+'_Base',(u,v,.855),(.46,.48,.16),cloth,.05,2)
    back=box(name+'_Back',(u-.213,v,1.145),(.14,.49,.53),cloth,.05,2)
    back.rotation_euler.x=math.radians(-8)
    box(name+'_Insert',(u-.121,v,1.153),(.024,.31,.35),dashmat,.025)
    box(name+'_Headrest',(u-.258,v,1.52),(.11,.31,.16),cloth,.034,2)
    for vv in [v-.11,v+.11]:rod(name+'_HeadPost'+str(vv),(u-.248,vv,1.39),(u-.248,vv,1.46),.012,steel)
    for vv in [v-.18,v+.18]:box(name+'_SeatRail'+str(vv),(u,vv,.744),(.48,.028,.05),trim,.005)
seat(-.37,-.46,'DriverSeat');seat(-.37,.46,'PassengerSeat')
box('RearBenchBase',(-1.18,0,.89),(.48,1.40,.17),cloth,.045,2)
box('RearBenchBack',(-1.47,0,1.15),(.14,1.40,.53),cloth,.04,2)
for v in [-.45,.45]:box('RearHeadrest'+str(v),(-1.49,v,1.49),(.11,.30,.15),cloth,.03,2)
for s in [-1,1]:
    for u in [-.03,-.90]:
        GROUP=('Door_F' if u>-.5 else 'Door_R')+('L' if s>0 else 'R')
        box('InnerDoor'+str(u)+str(s),(u,s*.865,1.01),(.67,.028,.38),dashmat,.016)
        box('DoorArmrest'+str(u)+str(s),(u,s*.817,1.055),(.39,.105,.075),trim,.02)
        box('DoorPull'+str(u)+str(s),(u+.12,s*.801,1.166),(.10,.025,.035),dark,.006)
    GROUP='Interior';box('RearWheelHouse'+str(s),(-1.60,s*.70,.785),(.58,.26,.25),dashmat,.04)

# Gauge plane faces toward driver (-u). All needles are separate objects for later animation.
GROUP='Instruments'
box('InstrumentBinnacle',(.163,-.45,1.279),(.18,.52,.25),trim,.043,2)
box('InstrumentFace',(.064,-.45,1.282),(.010,.46,.191),dark,.012)
def gauge(v,z,r,name,maxangle=2.8):
    rod(name+'_Rim',(.054,v,z),(.061,v,z),r,steel,24)
    rod(name+'_Face',(.046,v,z),(.053,v,z),r*.93,dark,24)
    for k in range(11):
        a=-.65+k*maxangle/10
        a+=math.pi/2
        line(name+'_Tick'+str(k),[(.043,v+math.cos(a)*r*.78,z+math.sin(a)*r*.78),(.043,v+math.cos(a)*r*.89,z+math.sin(a)*r*.89)],.0019,white)
    line(name+'_Needle',[(.039,v,z),(.039,v+r*.62,z-r*.31)],.003,needle)
    rod(name+'_Pin',(.032,v,z),(.043,v,z),r*.09,trim,8)
gauge(-.54,1.28,.079,'Speedometer');gauge(-.36,1.28,.079,'Tachometer')
for v in [-.652,-.25]:
    for z in [1.235,1.325]:gauge(v,z,.031,'Aux'+str(v)+str(z))
GROUP='Steering'
rod('SteeringColumn',(.19,-.46,1.08),(-.13,-.46,1.23),.031,trim,12)
# Steering wheel tilted 20 degrees from vertical, 16-segment rim.
centre=Vector((-.14,-.46,1.252));verts=[];faces=[]
for k in range(24):
    a=math.tau*k/24
    for j in range(6):
        b=math.tau*j/6;r=.185+.017*math.cos(b)
        verts.append((centre.x+.017*math.sin(b)-r*math.sin(a)*.24,centre.y+r*math.cos(a),centre.z+r*math.sin(a)*.971))
for k in range(24):
    for j in range(6):faces.append((k*6+j,((k+1)%24)*6+j,((k+1)%24)*6+(j+1)%6,k*6+(j+1)%6))
mesh('SteeringRim',verts,faces,rubber,smooth=True)
box('SteeringHub',tuple(centre),(.055,.22,.10),trim,.025,2)
for s in [-1,1]:
    line('SteeringSpoke'+str(s),[tuple(centre),(centre.x-.024,centre.y+s*.132,centre.z-.075)],.029,trim)
GROUP='Interior'
for u,v,z,name in [(-.14,.025,1.025,'GearLever'),(-.07,-.13,.965,'TransferLever')]:
    rod(name,(-.015,v,.86),(u,v,z),.013,steel,8)
    box(name+'_Boot',(-.01,v,.873),(.12,.10,.11),rubber,.034,2)
    box(name+'_Knob',(u,v,z),(.059,.05,.046),trim,.018,2)
rod('Handbrake',(-.48,-.19,.83),(-.19,-.19,.90),.019,trim,8)
for v in [-.60,-.46,-.30]:
    box('Pedal'+str(v),(.29,v,.757),(.075,.065,.021),rubber,.006)
    rod('PedalArm'+str(v),(.34,v,.77),(.40,v,.88),.009,steel,6)
box('InteriorMirror',(.11,0,1.65),(.065,.23,.071),trim,.012)
box('InteriorMirrorGlass',(.071,0,1.65),(.008,.20,.049),silver,.006)

print('LC_MODEL_GEOMETRY_READY',flush=True)

# Articulated groups and actual Blender pivots; rigging remains a later integration step.
pivots={'Door_FL':(.62,.91,1.1),'Door_FR':(.62,-.91,1.1),'Door_RL':(-.43,.91,1.1),'Door_RR':(-.43,-.91,1.1),
        'Hood':(.62,0,1.26),'TailgateUpper':(-2.15,0,1.76),'TailgateLower':(-2.29,0,.82),'Steering':tuple(centre)}
for group,p in pivots.items():
    parent=bpy.data.objects.new(group+'_Pivot',None);col('Pivots').objects.link(parent);parent.location=P(p);parent.empty_display_size=.08
    bpy.context.view_layer.update()
    for o in list(col(group).objects):
        o.parent=parent;o.matrix_parent_inverse=parent.matrix_world.inverted()
    parent['purpose']='Articulated source part; not gameplay rig'

# Neutral studio rig, isolated from exportable collection names.
GROUP='Studio'
floor=mat('StudioFloor',(.135,.16,.175),.83)
box('StudioGround',(0,0,-.055),(200,200,.10),floor,0)
scene.world.color=(.2,.2,.2);scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.47,.57,.69,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.38
def light(name,loc,power,size,color):
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;d.color=color
    o=bpy.data.objects.new(name,d);col('Studio').objects.link(o);o.location=P(loc);o.rotation_euler=(P((0,0,.8))-o.location).to_track_quat('-Z','Y').to_euler()
light('Key',(3,4,6),1250,4,(1,.90,.76));light('Fill',(1,-4,3.5),650,4,(.68,.80,1));light('Rim',(-4,1,4),1350,3,(1,.91,.75))
light('CabinReviewFill',(-.5,0,1.68),12,1.0,(.84,.91,1));bpy.data.objects['CabinReviewFill'].hide_render=True
camdata=bpy.data.cameras.new('ReviewCamera');cam=bpy.data.objects.new('ReviewCamera',camdata);col('Studio').objects.link(cam);scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=args.samples;scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED';scene.render.threads=6
scene.render.resolution_x=1200;scene.render.resolution_y=800;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=0
views={'front':((6.3,6.1,3.4),(.10,0,.96),57),'rear':((-6.3,-5.7,3.0),(-.2,0,.99),57),
       'side':((0,8,1.1),(0,0,1.1),55),'cockpit':((-.50,-.46,1.58),(.9,-.19,1.33),18),
       'front_flat':((7,0,1.2),(0,0,1.05),55)}
def setview(name):
    pos,target,lens=views[name];cam.location=P(pos);cam.rotation_euler=(P(target)-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO' if name=='side' else 'PERSP';camdata.ortho_scale=5.7;camdata.lens=lens;camdata.clip_start=.015
setview('front')
scene['Asset']='Land Cruiser 80 low-poly study';scene['Wheelbase_m']=2.85;scene['SourceFront']='-Y';scene['Status']='Modelling iteration; no Unreal import'
scene.cursor.location=(0,0,0)
# Save the editable source before rendering. Pack references into a hidden collection.
for name in ['01_exterior_proportions_v2.png','02_exterior_form_finish.png','03_cockpit_gauges.png']:
    im=bpy.data.images.load(str(ROOT/'Art/References/Vehicles/LandCruiser80_v01'/name));im.pack()
    ob=bpy.data.objects.new('Ref_'+name,None);col('Reference').objects.link(ob);ob.empty_display_type='IMAGE';ob.data=im;ob.hide_render=True;ob.hide_viewport=True
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'LandCruiser80.blend'))
# Evaluated counts exclude the studio and reference objects.
dg=bpy.context.evaluated_depsgraph_get();counts={};bounds=[]
for group,c in COLS.items():
    if group in ['Studio','Reference','Pivots']:continue
    total=0
    for o in c.objects:
        if o.type not in {'MESH','CURVE','FONT'}:continue
        ev=o.evaluated_get(dg);me=ev.to_mesh();me.calc_loop_triangles();total+=len(me.loop_triangles)
        bounds.extend([list(ev.matrix_world@v.co) for v in me.vertices]);ev.to_mesh_clear()
    counts[group]=total
manifest={'iteration':args.version,'triangles_by_group':counts,'triangles_total':sum(counts.values()),'wheelbase_m':2.85,
          'wheel_radius_m':.407,'track_m':1.60,'units':'metres','front':'-Y','left':'+X','render':'Cycles CPU, 6 threads',
          'bounds_m':[[min(p[i] for p in bounds),max(p[i] for p in bounds)] for i in range(3)],
          'not_yet':['UV atlas','baked material textures','Chaos rig','collision meshes','LODs','Unreal import','in-game validation']}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
print('LC_COUNTS '+json.dumps(manifest),flush=True)
for view in args.views.split(','):
    setview(view);bpy.data.objects['StudioGround'].hide_render=(view=='side')
    bpy.data.objects['CabinReviewFill'].hide_render=(view!='cockpit')
    scene.render.filepath=str(OUT/(view+'.png'));bpy.ops.render.render(write_still=True);print('LC_RENDER_OK '+view,flush=True)
print('LC_MODEL_OK '+str(OUT),flush=True)
