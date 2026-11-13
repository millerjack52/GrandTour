"""Fit static Crafted Utility details to the accepted v03 primary forms.
Preserves source files; derives side panels from actual accepted mesh faces.
"""
import bpy,bmesh,json,math,sys,argparse,hashlib,shutil
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
OUT=Path(a.output)
if OUT.exists() and any(OUT.iterdir()):raise RuntimeError('Use a new empty output revision; manual work is never replaced.')
OUT.mkdir(parents=True)
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT))
import wheel_fender_workshop as wf
import door_window_workshop as dw
import lamp_grille_workshop as lg
import cockpit_workshop as ck
SRC=Path('C:/GrandTour/Art/Export/VehicleTools/shape-character-v03')
BLEND=SRC/'Crafted_Utility_Character_Study.blend';source_hash=hashlib.sha256(BLEND.read_bytes()).hexdigest()
S=json.loads((SRC/'shape-spec.json').read_text());R=S['registration'];P=R['pixels_per_metre']
bpy.ops.wm.open_mainfile(filepath=str(BLEND));sc=bpy.context.scene

def coll(n):
    c=bpy.data.collections.new(n);sc.collection.children.link(c);c['interface']='crafted-utility-character-v03';return c
def mat(n,col,rough=.5,metal=0):return wf.material('Dressed | '+n,col,rough,metal)
M=dict(paint=mat('olive enamel',(.12,.137,.075),.5),cream=mat('ivory coachline',(.68,.54,.33),.55),
       rubber=mat('black rubber',(.011,.015,.016),.80),trim=mat('satin graphite',(.018,.023,.025),.48,.10),
       bright=mat('warm metal',(.39,.40,.34),.34,.65),amber=mat('amber lens',(.92,.25,.017),.22),
       red=mat('red lens',(.43,.019,.013),.23),clear=mat('clear marker lens',(.63,.66,.58),.21),
       dark=mat('interior shadows',(.008,.012,.012),.85),glass=mat('clear smoke glass',(.83,.88,.85),.025),
       mirror=mat('mirror silver',(.67,.73,.73),.055,1),plate=mat('registration ivory',(.68,.67,.54),.58))
bs=M['glass'].node_tree.nodes.get('Principled BSDF');bs.inputs['Transmission Weight'].default_value=1.;bs.inputs['IOR'].default_value=1.46
M['paint'].node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value=.3

def mesh(n,v,f,m,c,solid=0):
    o=wf.mesh(n,v,f,m,c)
    bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
    if solid:
        mod=o.modifiers.new('Closed sheet with inward returns','SOLIDIFY');mod.thickness=solid;mod.offset=-1
        bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=mod.name)
    return o
def box(n,loc,dim,m,c,b=0):return dw.box(n,loc,dim,m,c,None,b)
def solid(n,poly,d,m,c):return dw.solid(n,poly,d,m,c,None)
def rod(n,start,end,r,m,c):return ck.rod(n,start,end,r,m,c,None)
def lerp(x,rows):return dw.lerp(x,sorted(rows))
def Y(u):return R['axle_front_world']+(u-R['front_hub_px'][0])/P
def Z(v):return R['axle_z']+(R['front_hub_px'][1]-v)/P
def U(y):return R['front_hub_px'][0]+(y-R['axle_front_world'])*P
def V(z):return R['front_hub_px'][1]-(z-R['axle_z'])*P
def width(u,v):return lerp(v,S['side_section_v_width'])*lerp(u,S['longitudinal_width'])
def rearY(z):return Y(lerp(V(z),[(v,u) for u,v in S['rear_profile_uv']]))
def frontY(z):return Y(lerp(V(z),[(v,u) for u,v in S['front_profile_uv']]))
def cabx(z):return lerp(V(z),[(40,S['cabin_half_width_top']),(136,S['cabin_half_width_bottom'])])
def bottom(u):
    for name in ['front_arch_uv','rear_arch_uv']:
        pts=S[name]
        if pts[0][0]<=u<=pts[-1][0]:return Z(lerp(u,pts))
    return Z(278)

# Capture raw accepted outer skin before Solidify, then freeze the remaining
# evaluated primary surfaces without changing any coordinates.
master=bpy.data.objects['Body | shared shoulder, side tuck and rear return']
for mod in master.modifiers:mod.show_viewport=False
bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
raw=bpy.data.meshes.new_from_object(master.evaluated_get(dg),depsgraph=dg)
sourceverts=[v.co.copy() for v in raw.vertices];sourcepolys=[[sourceverts[i] for i in p.vertices] for p in raw.polygons]
surface_bvh=BVHTree.FromPolygons(sourceverts,[tuple(p.vertices) for p in raw.polygons],all_triangles=False)
for mod in master.modifiers:mod.show_viewport=True
preserve=coll('REFERENCE | Accepted outer skin');preserve.hide_render=True;preserve.hide_viewport=True
for c in list(master.users_collection):c.objects.unlink(master)
preserve.objects.link(master);master.hide_select=True
frozen={};protected_names=[]
for cname in ['01 | Primary surfaces','02 | Cabin and openings','03 | Bumper profiles']:
    for ob in list(bpy.data.collections[cname].objects):
        if ob.type!='MESH':continue
        bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();me=bpy.data.meshes.new_from_object(ob.evaluated_get(dg),depsgraph=dg)
        ob.modifiers.clear();ob.data=me;frozen[ob.name]=[tuple(v.co) for v in me.vertices];protected_names.append(ob.name)
        ob['shape_source']='Accepted shape-character-v03, frozen evaluated mesh';ob.hide_select=False
        material=M['paint']
        if 'frame' in ob.name or 'surround' in ob.name or 'gutter' in ob.name or 'bumper' in ob.name:material=M['trim']
        if 'opening' in ob.name:material=M['glass']
        if 'well' in ob.name or 'backing' in ob.name:material=M['dark']
        ob.data.materials.clear();ob.data.materials.append(material)
controls=bpy.data.objects.get('FORM CONTROLS | 1 proposed - 0 flattened')
controls.hide_viewport=True;controls.hide_render=True;controls['status']='Historical probes retained for reference only. Detail pass uses frozen accepted forms.'
for ob in list(bpy.data.collections['04 | Wheel proxies'].objects):ob.hide_render=True;ob.hide_set(True)

def clip(poly,axis,value,greater):
    result=[]
    for aa,bb in zip(poly,poly[1:]+poly[:1]):
        d=(aa[axis]-value)*(1 if greater else -1);e=(bb[axis]-value)*(1 if greater else -1)
        if d>=-1e-9:result.append(aa)
        if (d>=0)!=(e>=0):result.append(aa+(bb-aa)*(d/(d-e)))
    clean=[]
    for q in result:
        if not clean or (q-clean[-1]).length>1e-7:clean.append(q)
    if len(clean)>2 and (clean[0]-clean[-1]).length<1e-7:clean.pop()
    return clean
panel_points=[];panels={};seam=.003
sections=[('Front wing',-10,Y(280)),('Front door',Y(280),Y(475)),('Rear door',Y(475),Y(634)),('Rear quarter',Y(634),10)]
for side,label in [(1,'L'),(-1,'R')]:
    polys=[p for p in sourcepolys if all(v.x*side>.5 for v in p)]
    for title,lo,hi in sections:
        c=coll(label+' | '+title);vv=[];ff=[]
        for poly in polys:
            q=clip(poly,1,lo+seam/2,True);q=clip(q,1,hi-seam/2,False) if q else []
            if len(q)<3:continue
            j=len(vv);vv.extend(q);panel_points.extend(q);ff.append(tuple(range(j,len(vv))))
        ob=mesh(label+' | '+title+' derived skin',vv,ff,M['paint'],c,.012);panels[(side,title)]=ob
        ob['derivation']='Clipped accepted outer polygons; 3 mm reveals, no reshaping.'
        # Coachline follows the actual shared section, split at each door reveal.
        ulo=max(39,U(lo+.003));uhi=min(809,U(hi-.003))
        if uhi>ulo:
            stations=sorted(set([ulo,uhi]+[u for u,w in S['longitudinal_width'] if ulo<u<uhi]))
            verts=[(side*(width(u,v)+.0018),Y(u),Z(v)) for u in stations for v in [174,185]]
            mesh(label+' | ivory belt stripe',verts,[(i,i+2,i+3,i+1) for i in range(0,len(verts)-2,2)],M['cream'],c,.001)
        # Low moulding clears arches and follows the change of body plane.
        samples=sorted(set([max(40,ulo),min(806,uhi)]+[u for name in ['front_arch_uv','rear_arch_uv'] for u,v in S[name] if ulo<u<uhi]))
        for u1,u2 in zip(samples,samples[1:]):
            if max(bottom(u1),bottom(u2))>Z(233):continue
            for v,h,m in [(236,3.0,M['rubber']),(234.8,.7,M['bright'])]:
                pts=[(side*(width(u,vv)+.003),Y(u),Z(vv)) for u,vv in [(u1,v-h/2),(u2,v-h/2),(u2,v+h/2),(u1,v+h/2)]]
                mesh(label+' | lower moulding',pts,[(0,1,2,3)],m,c,.002)
        if 'door' in title.lower():
            y=hi-.14;z=Z(156);x=side*width(U(y),V(z))
            dw.cut(ob,box('Temporary handle aperture',(x,y,z),(.12,.134,.060),None,c,.006))
            outer=dw.rect_yz(x+side*.002,y,z,.143,.070,.007);inner=dw.inset(outer,.008)
            dw.ring(label+' | handle rubber bezel',outer,inner,(-side*.012,0,0),M['rubber'],c,None)
            solid(label+' | recessed handle cup',[(xx-side*.017,yy,zz) for xx,yy,zz in inner],(-side*.005,0,0),M['dark'],c)
            box(label+' | metal door release',(x+side*.006,y,z+.007),(.012,.088,.025),M['bright'],c,.003)
            rod(label+' | lock cylinder',(x+side*.005,y+.052,z),(x+side*.010,y+.052,z),.005,M['bright'],c)
    # Narrow dark reveal backing follows section; it never replaces a body panel.
    c=coll(label+' | reveal backing')
    for u in [280,475,634]:
        vs=sorted(set([V(bottom(u)),139,151,170,235,253,278]));vs=[v for v in vs if 139<=v<=V(bottom(u))]
        vv=[(side*(width(u,v)-.014),Y(u)+d,Z(v)) for v in vs for d in [-.007,.007]]
        mesh(label+' | inset jamb',vv,[(i,i+1,i+3,i+2) for i in range(0,len(vv)-2,2)],M['dark'],c,.004)

# Front and rear closure surfaces come from the same accepted master mesh.
endpolys=[p for p in sourcepolys if min(v.x for v in p)<0<max(v.x for v in p)]
for rear,title in [(False,'Front nose'),(True,'Rear tailgate')]:
    c=coll(title+' | closure');vv=[];ff=[]
    for poly in endpolys:
        if (sum(v.y for v in poly)/len(poly)>0)!=rear:continue
        j=len(vv);vv.extend(poly);ff.append(tuple(range(j,len(vv))))
    ob=mesh(title+' | derived closure skin',vv,ff,M['paint'],c,.012)
    if not rear:
        nose=ob
        dw.cut(nose,box('Temporary fascia opening',(0,-1.97,.888),(1.735,.32,.300),None,c,.003))
    else:tail=ob;tailcoll=c

c=coll('Front | fitted lights and grille')
carrier=box('Fascia | dark inset carrier',(0,-1.957,.888),(1.72,.036,.295),M['trim'],c,.004)
dw.cut(carrier,box('Temporary grille opening',(0,-1.97,.888),(.985,.16,.266),None,c))
for side in [-1,1]:
    cutter=rod('Temporary lamp opening',(side*.641,-2.10,.887),(side*.641,-1.75,.887),.131,None,c);dw.cut(carrier,cutter)
    cc=lg.lamp(dict(lg.LAMP,center=[side*.641,-1.940,.887]),('L' if side>0 else 'R')+' | Headlamp cassette')
    root=next(o for o in cc.objects if o.get('mount'));root.scale=(.925,)*3
    cc['adaptation']='0.925 uniform cassette scale, new body opening radius 0.131 m; previous fit claims do not apply.'
box('Grille | radiator shadow',(0,-1.870,.888),(.981,.025,.264),M['dark'],c,.002)
for i in range(6):
    z=.777+i*.044
    solid('Grille | folded horizontal slat',[(-.488,-1.991,z-.005),(-.488,-1.985,z+.008),(-.488,-1.949,z+.006),(-.488,-1.949,z-.008)],(.976,0,0),M['trim'],c)
for x in [-.34,0,.34]:box('Grille | vertical rear support',(x,-1.929,.89),(.009,.014,.263),M['rubber'],c)
for side in [-1,1]:
    box('Marker | recessed surround',(side*.812,-1.967,.886),(.090,.06,.288),M['rubber'],c,.004)
    for z,h,m in [(.982,.081,M['amber']),(.891,.078,M['amber']),(.802,.073,M['clear'])]:
        box('Marker | moulded lens',(side*.812,-2.001,z),(.073,.010,h),m,c,.003)
        for i in range(6):box('Marker | lens flute',(side*.812+(i-2.5)*.010,-2.007,z),(.002,.0018,h-.01),m,c,.0005)
    x=side*width(74,194)
    box('Wing | small amber repeater',(x+side*.004,Y(74),Z(194)),(.010,.046,.024),M['amber'],c,.004)

# Keep accepted bumpers intact, dress the faces, and perforate only the lower
# valance; it is not allowed to become a new expedition bumper silhouette.
c=coll('Front | bumper inserts and lower valance')
for side in [-1,1]:box('Bumper | modest rubber overrider',(side*.56,-2.093,Z(247)),(.071,.026,.115),M['rubber'],c,.007)
dw.cut(nose,box('Temporary lower vent',(0,-1.94,.608),(1.04,.32,.092),None,c,.003))
box('Valance | recessed shadow',(0,-1.80,.608),(1.05,.03,.10),M['dark'],c)
for x in [-.40,0,.40]:box('Valance | opening rib',(x,-1.928,.608),(.035,.040,.105),M['trim'],c,.003)
for side in [-1,1]:
    fogz=.487
    box('Fog lamp | seated bezel',(side*.675,frontY(fogz)-.022,fogz),(.168,.080,.072),M['rubber'],c,.006)
    box('Fog lamp | metal rim',(side*.675,frontY(fogz)-.066,fogz),(.139,.009,.057),M['bright'],c,.004)
    box('Fog lamp | ribbed amber lens',(side*.675,frontY(fogz)-.073,fogz),(.119,.006,.042),M['clear'],c,.003)
    for i in range(9):box('Fog lamp | flute',(side*.675+(i-4)*.012,frontY(fogz)-.077,fogz),(.0014,.0014,.036),M['clear'],c)

# Rear light faces, plate, split seal and hinges follow y(z) at the tapered tail.
def rearpatch(n,x,z,w,h,offset,mat,c):
    rows=sorted(set([z-h/2,z+h/2]+[Z(v) for u,v in S['rear_profile_uv'] if z-h/2<Z(v)<z+h/2]))
    pts=[(xx,rearY(zz)+offset,zz) for zz in rows for xx in [x-w/2,x+w/2]]
    depth=.045 if 'cassette' in n else .012 if 'lens' in n else .006 if 'flute' in n else .005
    count=len(pts);pts += [(xx,yy-depth,zz) for xx,yy,zz in pts]
    ff=[]
    for i in range(0,count-2,2):
        ff.extend([(i,i+2,i+3,i+1),(i+count,i+1+count,i+3+count,i+2+count),
                   (i,i+count,i+2+count,i+2),(i+1,i+3,i+3+count,i+1+count)])
    ff.extend([(0,1,count+1,count),(count-2,2*count-2,2*count-1,count-1)])
    return mesh(n,pts,ff,mat,c)
c=coll('Rear | fitted lamps and tailgate fixtures')
for side in [-1,1]:
    x=side*.810
    dw.cut(tail,box('Temporary rear lamp aperture',(x,2.18,.892),(.119,.30,.291),None,c,.003))
    rearpatch('Tail lamp | recessed black cassette',x,.892,.126,.304,.004,M['rubber'],c)
    for z,h,m in [(.990,.086,M['amber']),(.895,.098,M['red']),(.798,.072,M['clear'])]:
        rearpatch('Tail lamp | lens',x,z,.102,h,.014,m,c)
        for i in range(7):rearpatch('Tail lamp | optical flute',x+(i-3)*.012,z,.0018,h-.010,.019,m,c)
    for z in [.695,1.135]:rod('Tailgate | hinge barrel',(side*.58-.041,rearY(z)+.010,z),(side*.58+.041,rearY(z)+.010,z),.010,M['trim'],c)
    rearpatch('Tailgate | hinge leaf',side*.58,.716,.078,.036,.004,M['trim'],c)
rearpatch('Tailgate | split weatherstrip',0,Z(167),1.58,.009,.002,M['rubber'],c)
# Plate opening is cut through the tapered panel and has a real recessed backing.
plate_z=.905;dw.cut(tail,box('Temporary plate recess',(0,rearY(plate_z),plate_z),(.512,.15,.177),None,c,.006))
rearpatch('Plate | pocket backing',0,plate_z,.506,.171,-.031,M['dark'],c)
rearpatch('Plate | ivory registration',0,plate_z,.438,.123,-.022,M['plate'],c)
rearpatch('Plate | upper pocket return',0,plate_z+.083,.505,.012,-.005,M['paint'],c)
rearpatch('Tailgate | release bezel',0,1.016,.119,.043,.009,M['rubber'],c)
rearpatch('Tailgate | release grip',0,1.019,.084,.019,.020,M['bright'],c)
for side in [-1,1]:rearpatch('Plate | fastening',side*.19,plate_z+.046,.006,.006,-.018,M['bright'],c)
cu=bpy.data.curves.new('Registration lettering','FONT');cu.body='GT  /  01';cu.align_x='CENTER';cu.align_y='CENTER';cu.size=.055;cu.extrude=.0001;cu.resolution_u=1
o=bpy.data.objects.new('Registration | GT 01',cu);c.objects.link(o);o.location=(0,rearY(plate_z)-.018,plate_z);o.rotation_euler=(math.pi/2,0,math.pi);cu.materials.append(M['trim'])
for side in [-1,1]:
    for z1,z2 in [(.740,1.050)]:
        rod('Tailgate | narrow side reveal',(side*.73,rearY(z1)+.001,z1),(side*.73,rearY(z2)+.001,z2),.0017,M['rubber'],c)
for side in [-1,1]:box('Rear bumper | rubber pad',(side*.58,Y(826)+.002,Z(243)),(.072,.02,.113),M['rubber'],c,.007)
# Small fuel flap on the right rear quarter, fitted to the side plane.
fuelu=757;fuelv=194;fx=-width(fuelu,fuelv)
box('Fuel flap | fine dark reveal',(fx-.001,Y(fuelu),Z(fuelv)),(.004,.129,.109),M['rubber'],c,.008)
box('Fuel flap | painted cover',(fx-.003,Y(fuelu),Z(fuelv)),(.004,.121,.101),M['paint'],c,.007)

# Gaskets trace the existing pane boundary, and glass retains the approved outline.
c=coll('Glazing | seals, wipers and mirrors')
for ob in list(bpy.data.collections['02 | Cabin and openings'].objects):
    if 'opening' not in ob.name:continue
    # Original planar surface was solidified. Select the outer face by area and
    # derive its perimeter from the true mesh, keeping the actual opening shape.
    face=max(ob.data.polygons,key=lambda p:p.area);pts=[ob.data.vertices[i].co.copy() for i in face.vertices]
    for aa,bb in zip(pts,pts[1:]+pts[:1]):rod('Glass | fine rubber perimeter',aa,bb,.0035,M['rubber'],c)
for side in [-1,1]:
    y=Y(315);z=Z(120);x=side*cabx(z)
    rod('Mirror | angled stalk',(x,y,z),(side*.963,y-.01,z+.023),.015,M['trim'],c)
    box('Mirror | chamfered shell',(side*1.013,y,z+.056),(.162,.095,.106),M['trim'],c,.013)
    box('Mirror | inset reflective glass',(side*1.013,y+.050,z+.056),(.133,.006,.081),M['mirror'],c,.008)
for x in [-.43,.34]:
    rod('Wiper | spindle',(x,Y(278)-.010,Z(135)),(x,Y(278)-.018,Z(135)+.01),.011,M['trim'],c)
    rod('Wiper | arm',(x,Y(278)-.018,Z(135)+.01),(x-.15,Y(285)-.020,Z(128)),.0045,M['trim'],c)
    rod('Wiper | blade',(x-.33,Y(288)-.020,Z(125)),(x+.03,Y(288)-.020,Z(125)),.006,M['rubber'],c)
for side in [-1,1]:
    # Rear sail-pillar vents stay on the sloped window plane.
    for i in range(5):
        v=112+i*3;u=775+(v-112)*.35;z=Z(v);x=side*(cabx(z)+.004)
        rod('Rear pillar | vent rib',(x,Y(u-10),z),(x,Y(u+13),z),.003,M['rubber'],c)
for i in range(8):
    z=1.28+i*.045;t=(z-Z(136))/(Z(40)-Z(136));yy=Y(809)+(Y(755)-Y(809))*t+.005
    rod('Rear glass | demister',(-.665,yy,z),(.665,yy,z),.00035,mat('demister copper',(.12,.065,.023),.8),c)

# Reuse wheel construction at supported radius, adapt only the mounting scale.
# New outer radius equals the approved proxy envelope, not the rejected car.
wheelroots=[]
for cy,title in [(R['axle_front_world'],'Front'),(R['axle_rear_world'],'Rear')]:
    for side,label in [(1,'L'),(-1,'R')]:
        ss=dict(wf.DEFAULT,radius=.39,width=.24,center=[side*S['wheel_half_track'],cy,R['axle_z']],side=side)
        c=wf.wheel(ss,title+' '+label+' | Detailed wheel');r=next(o for o in c.objects if o.get('mount'));wheelroots.append(r)
        k=(S['tyre_radius']*1.007)/.39;r.scale=(side,k,k)
        old=next(o for o in c.objects if o.name.startswith('Rim | dished web'));bpy.data.objects.remove(old,do_unlink=True)
        off=.24/2-.136;pm=wf.palette()
        disk=wf.revolve('Rim | pressed steel twelve vent web',[(x+off,rr) for x,rr in [(.100,.050),(.094,.095),(.120,.17),(.139,.201),(.126,.205),(.106,.173),(.080,.096),(.086,.050)]],pm['steel'],c,r,64,True)
        for i in range(12):
            ang=i*math.tau/12;dw.cut(disk,wf.cylinder('Temporary round wheel vent',off+.11,.158*math.sin(ang),.158*math.cos(ang),.018,.24,None,c,r,20))
        mod=disk.modifiers.new('Vent rolled edge','BEVEL');mod.width=.0017;mod.segments=2
        mod=disk.modifiers.new('Pressed steel normals','WEIGHTED_NORMAL');mod.keep_sharp=True
        c['adaptation']='Fits v03 proxy centres/width and outer-radius envelope. No inherited clearance certification.'

# Cockpit modules are local construction methods; mounts are new and fixed.
for func,title in [(ck.dash,'Dashboard'),(ck.instruments,'Instruments'),(ck.steering,'Steering'),(ck.console,'Console'),(ck.rear_bench,'Rear bench')]:
    c=func(ck.spec(),'Cabin | '+title);r=next(o for o in c.objects if o.get('mount'));r.location.y=.11;r.location.z=.035;c['adaptation']='Static fit to v03 cabin; old mounting validation superseded.'
for side,label in [(1,'L'),(-1,'R')]:
    c=ck.front_seat(ck.spec(side=side),'Cabin | '+label+' front seat');r=next(o for o in c.objects if o.get('mount'));r.location.y=.11;r.location.z=.035
for name,color in [('Cockpit | saddle grey vinyl',(.26,.18,.108)),('Cockpit | warm oatmeal weave',(.34,.27,.18)),('Workshop | warm satin alloy',(.32,.29,.22))]:
    m=bpy.data.materials.get(name);m.diffuse_color=(*color,1);m.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(*color,1)
c=coll('Cabin | fitted floor and lining')
box('Cabin | central floor',(0,.50,.565),(1.20,2.80,.022),M['dark'],c)
for side in [-1,1]:
    for ua,ub in [(283,472),(478,631)]:
        us=sorted(set([ua,ub]+[u for n in ['front_arch_uv','rear_arch_uv'] for u,v in S[n] if ua<u<ub]))
        pts=[(side*.837,Y(u),max(.62,bottom(u)+.015)) for u in us]+[(side*.837,Y(ub),1.20),(side*.837,Y(ua),1.20)]
        solid('Cabin | door lining',pts,(-side*.015,0,0),M['trim'],c)
        box('Cabin | padded armrest',(side*.804,Y((ua+ub)/2),.943),(.060,.38,.048),M['rubber'],c,.010)
box('Cabin | cargo floor',(0,1.83,.565),(1.18,.56,.022),M['dark'],c)
box('Cabin | roof liner',(0,.63,1.742),(1.45,1.76,.010),mat('headlining',(.36,.35,.29),.9),c,.004)

c=coll('Underside | frame, axles and mudflaps')
for side in [-1,1]:box('Chassis | frame rail',(side*.48,.12,.39),(.075,3.56,.084),M['trim'],c,.008)
for cy in [R['axle_front_world'],R['axle_rear_world']]:
    rod('Axle | tube',(-.78,cy,.395),(.78,cy,.395),.035,M['trim'],c)
    box('Axle | differential',(0,cy,.39),(.205,.215,.16),M['trim'],c,.048)
    for side in [-1,1]:
        rod('Damper | body',(side*.60,cy,.43),(side*.55,cy+.14,.72),.019,M['trim'],c)
        box('Mudflap | flexible rubber',(side*.797,cy+.475,.36),(.23,.012,.23),M['rubber'],c,.005)
pipe=rod('Exhaust | tailpipe',(-.58,1.75,.365),(-.58,2.08,.365),.026,M['bright'],c)
dw.cut(pipe,rod('Temporary exhaust bore',(-.58,1.82,.365),(-.58,2.09,.365),.019,None,c))

# These copies are independent components; old workshop rebuild operators must
# not be applied using obsolete mount/interface fingerprints.
for c in bpy.data.collections:
    if c.get('gt_owner'):
        c['source_owner']=c['gt_owner'];c['gt_owner']='GT_DRESSED_CHARACTER_01'
        for ob in c.objects:ob['gt_owner']='GT_DRESSED_CHARACTER_01'

# Preservation evidence compares actual evaluated vertex positions, not settings.
checks={'accepted_source_sha256':source_hash,'accepted_source_unchanged':hashlib.sha256(BLEND.read_bytes()).hexdigest()==source_hash}
unchanged={}
for name,points in frozen.items():
    ob=bpy.data.objects[name];delta=max((Vector(pt)-v.co).length for pt,v in zip(points,ob.data.vertices));unchanged[name]=delta;assert delta<1e-8
checks['protected_primary_max_displacement_m']=max(unchanged.values());checks['protected_primary_objects']=len(unchanged)
checks['derived_panel_vertex_max_distance_to_accepted_surface_m']=max(surface_bvh.find_nearest(v)[3] for v in panel_points)
assert checks['derived_panel_vertex_max_distance_to_accepted_surface_m']<.0005
checks['scope']='Frozen primary form and derived-panel checks. Static detail assembly; no rig, UV, LOD or engine-export claim.'
checks['intentional_contacts']=['panel sheet returns and reveal backing','lamp housing within cut fascia','window perimeter seals','body-following coachline and moulding','mirror stalk to window base','tyre bead / wheel rim','seat rails / cabin floor']
(OUT/'preservation-checks.json').write_text(json.dumps(checks,indent=2))
sc['status']='Side form accepted by user 2026-10-01; detailed static assembly for review. Reproducibility on a second car not yet tested.'
t=bpy.data.texts.new('START HERE | Dressed Crafted Utility')
t.write('Detailed static assembly derived from user-accepted shape-character-v03.\nPrimary form frozen; original study file unchanged.\nSeparate door/wing/quarter skins are clipped from the actual accepted surface, with real reveals and handle apertures.\nExisting lamp, wheel and cockpit construction is refitted to the new envelope.\nOriginal FORM CONTROLS are historical probes, not linked to the fitted details. Edit this assembly as a new revision.\nNo roof rack, winch or expedition flares added: Crafted Utility base trim.\nNo operational rig, UV/LOD, collision or game export certification.\nSee preservation-checks.json and renders. Test reproducibility on a different car only after this review.\n')
for key in ['shape-map.json','shape-spec.json']:
    shutil.copy2(SRC/key,OUT/key)
for n in ['side-reference.png','original-a-reference.png']:shutil.copy2(SRC/n,OUT/n)
for n in ['dress_shape_character.py','wheel_fender_workshop.py','door_window_workshop.py','lamp_grille_workshop.py','cockpit_workshop.py']:shutil.copy2(ROOT/n,OUT/n)
sc.cycles.samples=32;sc.cycles.use_denoising=True;sc.cycles.max_bounces=8;sc.cycles.transmission_bounces=6
views={'quarter':'Front quarter | volume review','side':'Side | fixed reference registration','rear-quarter':'Rear quarter | return review','front':'Front | section review','rear':'Rear | section review','top':'Top | width review','rear-detail':'Rear detail | fixed profile'}
def render(key):
    cam=bpy.data.objects[views[key]];sc.camera=cam;sc.render.resolution_x,sc.render.resolution_y=cam['resolution'];sc.render.filepath=str(OUT/(key+'.png'));bpy.ops.render.render(write_still=True)
render('quarter')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Crafted_Utility_Detailed.blend'))
for key in ['side','rear-quarter','front','rear','top','rear-detail']:render(key)
sc.camera=bpy.data.objects[views['quarter']];sc.render.resolution_x,sc.render.resolution_y=sc.camera['resolution']
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Crafted_Utility_Detailed.blend'))
print('DRESSED_CHARACTER_READY '+str(OUT),flush=True)
