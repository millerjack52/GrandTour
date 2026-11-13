"""Fitted headlamp cassettes and front grille, using the workshop's mesh primitives.

Import does not change the scene. Local X is outward, Y lateral, Z up.
The RR nose adapter is separate from reusable component construction.
"""
bl_info={'name':'Grand Tour Lamp and Grille Workshop','author':'Grand Tour','version':(0,1,0),
         'blender':(5,1,0),'category':'Mesh'}
import bpy, math, json, sys
from pathlib import Path
from mathutils import Vector
try:
    from . import wheel_fender_workshop as wf
except ImportError:
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    import wheel_fender_workshop as wf

OWNER='GT_LIGHTS_01'
LAMP=dict(center=[.690,-2.031,.945],side=1,interface='rr-lamp-286-v1',
          radius=.119,lens_crown=.017,rib_pitch=.012)
GRILLE=dict(center=[0,-2.031,.937],side=1,interface='rr-front-grille-v1',slats=5)

def palette():
    mats=dict(black=wf.material('Lights | graphite housings',(.030,.041,.046),.62),
              seal=wf.material('Lights | rubber seals',(.012,.017,.019),.85),
              reflector=wf.material('Lights | satin reflector',(.63,.65,.61),.21,.88),
              bezel=wf.material('Lights | brushed bezel',(.35,.38,.36),.36,.7),
              slat=wf.material('Lights | graphite grille slats',(.075,.092,.093),.43,.22),
              bulb=wf.material('Lights | unlit tungsten bulb',(.63,.51,.29),.28,.5))
    for key,color in [('glass',(.94,.965,.94)),('amber',(.95,.31,.018)),('clear',(.75,.82,.79))]:
        name='Lights | '+key+' lens';exists=bpy.data.materials.get(name)
        mats[key]=wf.material(name,color,.026 if key=='glass' else .12,0)
        if not exists:
            bs=mats[key].node_tree.nodes.get('Principled BSDF')
            bs.inputs['Transmission Weight'].default_value=.99 if key=='glass' else .65
            bs.inputs['IOR'].default_value=1.46
    return mats

def collection(name,s,kind):
    c,r=wf.root_collection(name,s,kind);c['gt_owner']=OWNER
    r.rotation_euler.z=-math.pi/2;r.scale=(1,1,1)
    r['interface']=s['interface'];return c,r

def seal(c):
    for ob in c.objects:ob['gt_owner']=OWNER
    wf.seal(c)

def box(name,center,size,mat,c,root=None,bevel=0):
    verts=[(center[0]+x*size[0]/2,center[1]+y*size[1]/2,center[2]+z*size[2]/2)
           for x,y,z in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]]
    return wf.mesh(name,verts,[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)],mat,c,root,bevel)

def cut(ob,cutter):
    bpy.context.view_layer.update();bpy.context.view_layer.objects.active=ob
    mod=ob.modifiers.new('True component opening','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
    bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)

def validate(s,kind):
    if not all(math.isfinite(x) for x in s['center']):raise ValueError('Invalid mounting frame')
    expected={'lamp':'rr-lamp-286-v1','grille':'rr-front-grille-v1','indicator':'rr-indicator-v1'}[kind]
    if s['interface']!=expected:raise ValueError('Incompatible opening interface')
    if kind=='lamp':
        if abs(s['radius']-.119)>1e-6:raise ValueError('Fixed lens radius .119 m required by this cassette')
        if not .008<=s['lens_crown']<=.023:raise ValueError('Lens crown range .008 to .023 m')
        if not .009<=s['rib_pitch']<=.018:raise ValueError('Lens flute pitch range .009 to .018 m')
    if kind=='grille' and s['slats'] not in [4,5,6]:raise ValueError('Supported grille slat counts: 4, 5, 6')

def lens(s,c,root,mat):
    """Closed curved lens with geometric vertical fluting, independent of reflector."""
    verts=[];faces=[];r=s['radius'];crown=s['lens_crown'];pitch=s['rib_pitch']
    # Sample along the flute direction instead of radial rings: the earlier polar
    # mesh undersampled narrow ribs at the perimeter and blurred their normals.
    cols=math.ceil(2*r/pitch)*6;rows=20;layers=[]
    for back in [False,True]:
        columns=[]
        for i in range(cols+1):
            y=-r+2*r*i/cols;half=math.sqrt(max(0,r*r-y*y));indices=[]
            zs=[0] if i in [0,cols] else [-half+2*half*j/rows for j in range(rows+1)]
            for z in zs:
                rr=math.hypot(y,z)
                flute=0 if back else .0012*math.cos(y/pitch*math.tau)*(1-(rr/r)**8)
                xx=.045+crown*(1-(rr/r)**2)+flute-(.003 if back else 0)
                indices.append(len(verts));verts.append((xx,y,z))
            columns.append(indices)
        for a,b in zip(columns,columns[1:]):
            if len(a)==1:faces += [(a[0],b[j],b[j+1]) for j in range(rows)]
            elif len(b)==1:faces += [(a[j],b[0],a[j+1]) for j in range(rows)]
            else:faces += [(a[j],b[j],b[j+1],a[j+1]) for j in range(rows)]
        boundary=[column[0] for column in columns]+[column[-1] for column in columns[-2:0:-1]]
        layers.append(boundary)
    for i in range(len(layers[0])):
        j=(i+1)%len(layers[0]);faces.append((layers[0][i],layers[0][j],layers[1][j],layers[1][i]))
    ob=wf.mesh('Lamp | curved fluted glass',verts,faces,mat,c,root)
    for p in ob.data.polygons:p.use_smooth=True
    return ob

def lamp(s,name='Headlamp cassette'):
    validate(s,'lamp');c,r=collection(name,s,'lamp');m=palette()
    wf.revolve('Lamp | closed rear shell',[(-.090,.003),(-.090,.081),(-.074,.108),
               (-.020,.137),(.023,.140),(.027,.132),(-.017,.129),(-.065,.097),(-.080,.003)],m['black'],c,r,48)
    wf.revolve('Lamp | parabolic reflector',[(.024,.117),(.010,.112),(-.014,.094),
               (-.035,.067),(-.049,.033),(-.052,.013),(-.056,.013),(-.053,.035),
               (-.039,.070),(-.018,.097),(.007,.116),(.023,.121)],m['reflector'],c,r,64,True)
    wf.revolve('Lamp | outer rubber seat',[(.012,.139),(.031,.141),(.045,.138),(.045,.130),(.016,.130)],m['seal'],c,r,64)
    wf.revolve('Lamp | rolled retaining bezel',[(.027,.134),(.058,.136),(.070,.131),(.072,.122),
               (.064,.119),(.056,.122),(.052,.129),(.026,.130)],m['bezel'],c,r,64,True)
    wf.revolve('Lamp | lens edge gasket',[(.041,.117),(.055,.117),(.058,.121),(.044,.122)],m['seal'],c,r,64)
    wf.cylinder('Lamp | bulb socket',-.042,0,0,.016,.022,m['black'],c,r,16)
    wf.cylinder('Lamp | bulb capsule',-.020,0,0,.010,.029,m['bulb'],c,r,16)
    lens(s,c,r,m['glass'])
    for i in range(3):
        a=(i/3+.125)*math.tau;y=.128*math.sin(a);z=.128*math.cos(a)
        wf.cylinder('Lamp | retaining screw',.073,y,z,.004,.003,m['reflector'],c,r,8)
        box('Lamp | screw slot',(.075,y,z),(.001,.005,.0008),m['black'],c,r)
        y=.151*math.sin(a);z=.151*math.cos(a)
        tab=box('Lamp | rear mounting tab',(.001,y,z),(.010,.026,.023),m['black'],c,r,.002)
    seal(c);return c

def grille(s,name='Grille and cassette carrier'):
    validate(s,'grille');c,r=collection(name,s,'grille');m=palette()
    plate=box('Grille | perforated carrier',(.019,0,0),(.032,1.716,.326),m['black'],c,r)
    for side in [-1,1]:
        cutter=wf.cylinder('Temporary lamp aperture',.01,side*.690,.008,.143,.30,None,c,r,64)
        cut(plate,cutter)
    cut(plate,box('Temporary grille aperture',(.01,0,0),(.30,1.036,.272),None,c,r))
    bevel=plate.modifiers.new('Carrier edge radius','BEVEL');bevel.width=.0025;bevel.segments=2
    # Deep side walls and a top/bottom return. All visible openings are actual voids.
    for y in [-.520,.520]:box('Grille | side return',(-.011,y,0),(.092,.009,.270),m['black'],c,r,.001)
    for z in [-.137,.137]:box('Grille | horizontal return',(-.011,0,z),(.092,1.045,.008),m['black'],c,r,.001)
    for i in range(s['slats']):
        z=-.109+i*.218/(s['slats']-1)
        profile=[(-.047,z-.008),(.039,z-.008),(.061,z-.001),(.061,z+.006),(.043,z+.013),(-.047,z+.010)]
        verts=[(x,y,zz) for y in [-.514,.514] for x,zz in profile];n=len(profile)
        faces=[tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]
        faces += [(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)]
        wf.mesh('Grille | shaped horizontal slat',verts,faces,m['slat'],c,r,.001)
    for y in [-.34,0,.34]:box('Grille | rear brace',(-.037,y,0),(.012,.009,.268),m['black'],c,r)
    box('Grille | radiator shadow',(-.125,0,0),(.012,1.028,.263),m['seal'],c,r)
    # Fin spacing visible through the open slats, kept quieter than the main grille.
    for i in range(35):box('Grille | radiator fin',(-.113,-.493+i*.029,0),(.006,.003,.250),m['black'],c,r)
    seal(c);return c

def rect_lens(name,width,height,ycenter,mat,c,r):
    n=40;verts=[]
    for rear in [False,True]:
        for i in range(n+1):
            y=-width/2+width*i/n
            x=.041 if rear else .049+.0008*math.cos(y/.009*math.tau)
            for z in [-height/2,height/2]:verts.append((x,y+ycenter,z))
    count=(n+1)*2;faces=[]
    for layer in [0,1]:
        off=layer*count
        faces += [(off+2*i,off+2*i+2,off+2*i+3,off+2*i+1) for i in range(n)]
    for i in range(n):
        for j in [0,1]:faces.append((i*2+j,(i+1)*2+j,count+(i+1)*2+j,count+i*2+j))
    faces += [(0,1,count+1,count),(count-2,count-1,count*2-1,count*2-2)]
    return wf.mesh(name,verts,faces,mat,c,r)

def indicator(s,name='Indicator cluster'):
    validate(s,'indicator');c,r=collection(name,s,'indicator');m=palette()
    box('Indicator | recessed housing',(-.012,0,0),(.086,.252,.082),m['black'],c,r,.004)
    for yc,width,key in [(s['side']*.066,.106,'amber'),(-s['side']*.059,.119,'clear')]:
        box('Indicator | reflector bed',(.033,yc,0),(.006,width,.060),m['reflector'],c,r,.003)
        rect_lens('Indicator | '+key+' fluted lens',width,.058,yc,m[key],c,r)
    box('Indicator | centre separator',(.043,s['side']*.004,0),(.013,.006,.065),m['black'],c,r)
    for yy in [-.120,.120]:wf.cylinder('Indicator | housing screw',.034,yy,0,.0025,.002,m['bezel'],c,r,8)
    seal(c);return c

def adapt_nose(car):
    """Replace only the old flat nose cap with a matching cap containing real openings."""
    old=bpy.data.objects.get('Nose fascia')
    if not old:raise RuntimeError('Expected original RR nose cap')
    paint=old.data.materials[0]
    outline=[(-.875,.43),(.875,.43),(.875,1.105),(.840,1.135),(-.840,1.135),(-.875,1.105)]
    verts=[(x,y,z) for y in [-2.03,-2.011] for x,z in outline];n=len(outline)
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    cap=wf.mesh('Nose fascia | fitted apertures',verts,faces,paint,car)
    cut(cap,box('Temporary fascia opening',(0,-2.02,.937),(1.722,.4,.340),None,car))
    for side in [-1,1]:cut(cap,box('Temporary indicator opening',(side*.735,-2.02,.724),(.258,.4,.088),None,car))
    bpy.data.objects.remove(old,do_unlink=True)
    return cap

def fit_report(lamps,gc):
    """Measure actual evaluated lamp placement in the carrier's local aperture frame."""
    bpy.context.view_layer.update();carrier=next(o for o in gc.objects if 'perforated carrier' in o.name)
    gr=next(o for o in gc.objects if o.get('mount'));inverse=gr.matrix_world.inverted()
    ct=wf.tree(carrier);reports=[]
    for lc in lamps:
        lr=next(o for o in lc.objects if o.get('mount'));pos=inverse@lr.matrix_world.translation
        target=Vector((0,.690 if pos.y>0 else -.690,.008));delta=pos-target
        contact=[]
        for ob in lc.objects:
            if ob.type=='MESH' and not any(t in ob.name for t in ['mounting tab','screw slot','retaining screw']):
                if ct.overlap(wf.tree(ob)):contact.append(ob.name)
        lensob=next(o for o in lc.objects if 'curved fluted glass' in o.name)
        radial=max(math.hypot(v.co.y,v.co.z) for v in lensob.data.vertices)
        reports.append(dict(part=lc.name,mount_error_m=delta.length,carrier_intersections=contact,
                            lens_radius_m=radial,lens_inside_retaining_seat=radial<=.119001))
    return dict(lamps=reports,scope='Actual lamp mount positions, glass radial containment and static lamp-to-carrier surface intersections. Rear mounting tabs/fasteners are intentional contacts. Not optical, watertightness, moving-part or game-ready certification.')

def rebuild(c,s):
    if wf.fingerprint(c)!=c.get('fingerprint'):raise RuntimeError('Manual edits detected; preserve this part as a variant')
    old=json.loads(c['spec']);s=dict(s,center=old['center'],side=old['side']);kind=c['kind'];validate(s,kind)
    before=set(bpy.data.collections);name=c.name
    try:
        new={'lamp':lamp,'grille':grille,'indicator':indicator}[kind](s,name+' STAGED')
        if not wf.component_report(new)['finite']:raise RuntimeError('Nonfinite staged geometry')
    except Exception:
        for cc in set(bpy.data.collections)-before:wf.remove_collection(cc)
        raise
    wf.remove_collection(c);new.name=name;seal(new);return new

def selected(context):
    if context.active_object:
        return next((c for c in context.active_object.users_collection if c.get('gt_owner')==OWNER),None)

class GTLG_Settings(bpy.types.PropertyGroup):
    crown:bpy.props.FloatProperty(name='Lens crown',default=.017,min=.008,max=.023,unit='LENGTH')
    pitch:bpy.props.FloatProperty(name='Glass flute pitch',default=.012,min=.009,max=.018,unit='LENGTH')
    slats:bpy.props.IntProperty(name='Grille slats',default=5,min=4,max=6)

class GTLG_OT_Rebuild(bpy.types.Operator):
    bl_idname='gtlg.rebuild';bl_label='Rebuild selected light / grille';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        c=selected(context)
        if not c:self.report({'ERROR'},'Select a lamp, grille or indicator mesh');return {'CANCELLED'}
        s=json.loads(c['spec']);p=context.scene.gtlg
        if c['kind']=='lamp':s.update(lens_crown=p.crown,rib_pitch=p.pitch)
        if c['kind']=='grille':s['slats']=p.slats
        try:rebuild(c,s)
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
        return {'FINISHED'}

class GTLG_OT_Check(bpy.types.Operator):
    bl_idname='gtlg.check';bl_label='Check nose cassette fit'
    def execute(self,context):
        cs=[c for c in context.scene.collection.children if c.get('gt_owner')==OWNER]
        gs=[c for c in cs if c['kind']=='grille'];ls=[c for c in cs if c['kind']=='lamp']
        if len(gs)!=1 or len(ls)!=2:self.report({'ERROR'},'Expected one grille and two lamps');return {'CANCELLED'}
        report=fit_report(ls,gs[0]);t=bpy.data.texts.get('Lights fit report') or bpy.data.texts.new('Lights fit report')
        t.clear();t.write(json.dumps(report,indent=2))
        errors=any(r['mount_error_m']>.001 or r['carrier_intersections'] or not r['lens_inside_retaining_seat'] for r in report['lamps'])
        self.report({'WARNING'} if errors else {'INFO'},'Fit issue — inspect Lights fit report' if errors else 'Static cassette fit passed')
        return {'FINISHED'}

class GTLG_PT_Panel(bpy.types.Panel):
    bl_label='Lamp and Grille Workshop';bl_idname='GTLG_PT_panel';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='GT Parts'
    def draw(self,context):
        l=self.layout;p=context.scene.gtlg
        for key in ['crown','pitch','slats']:l.prop(p,key)
        l.operator('gtlg.rebuild');l.operator('gtlg.check');l.label(text='Manual edits block rebuilding.')

CLASSES=[GTLG_Settings,GTLG_OT_Rebuild,GTLG_OT_Check,GTLG_PT_Panel]
def register():
    for cls in CLASSES:bpy.utils.register_class(cls)
    bpy.types.Scene.gtlg=bpy.props.PointerProperty(type=GTLG_Settings)
def unregister():
    if hasattr(bpy.types.Scene,'gtlg'):del bpy.types.Scene.gtlg
    for cls in reversed(CLASSES):bpy.utils.unregister_class(cls)
if __name__=='__main__':register()
