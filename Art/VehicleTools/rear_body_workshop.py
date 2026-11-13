"""RR rear quarters, split tailgate, inset rear lights and step bumper.

Static fitted exterior components, metres, rear +Y. Imports do not mutate scenes.
"""
bl_info={'name':'Grand Tour Rear Body Workshop','author':'Grand Tour','version':(0,1,0),'blender':(5,1,0),'category':'Mesh'}
import bpy,bmesh,math,json,sys
from pathlib import Path
from mathutils import Vector
try:from . import door_window_workshop as dw
except ImportError:
    sys.path.insert(0,str(Path(__file__).resolve().parent));import door_window_workshop as dw
wf=dw.wf
OWNER='GT_REAR_BODY_01'
KINDS=['quarter','lower_gate','upper_gate','lamp','bumper']
def spec(side=1,**kw):return dict(center=[0,0,0],side=side,interface='rr-rear-v1',**dict(dict(crown=.017,lens='ribbed'),**kw))
def validate(s,kind):
    if kind not in KINDS or s['interface']!='rr-rear-v1' or s['center']!=[0,0,0]:raise ValueError('Requires RR rear v1 assembly interface')
    if s['side'] not in [-1,1]:raise ValueError('Side must be -1 or 1')
    if not .010<=s['crown']<=.024:raise ValueError('Tailgate crown range 10 to 24 mm')
    if s['lens'] not in ['ribbed','smooth']:raise ValueError('Lens must be ribbed or smooth')
def collection(name,s,kind):
    validate(s,kind);c,r=wf.root_collection(name,s,kind);c['gt_owner']=OWNER
    if kind not in ['quarter','lamp']:r.scale=(1,1,1)
    return c,r
def seal(c):
    for o in c.objects:o['gt_owner']=OWNER
    wf.seal(c)
def palette():
    m=dw.palette();m.update(beam=wf.material('Rear | graphite beam',(.063,.080,.083),.56,.18),
        plate=wf.material('Rear | registration enamel',(.60,.62,.57),.47),
        red=wf.material('Rear | ruby lens',(.48,.018,.014),.22),
        amber=wf.material('Rear | amber lens',(.90,.225,.008),.22),
        clear=wf.material('Rear | clear lens',(.70,.74,.68),.20))
    for k in ['red','amber','clear']:
        mat=m[k]
        if not mat.get('rear_initialized'):
            bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Transmission Weight'].default_value=.32;bs.inputs['IOR'].default_value=1.46;mat['rear_initialized']=True
    return m
def rect(x,y,z,w,h,b=.009):
    return [(x+a,y,z+c) for a,c in [(-w/2+b,-h/2),(w/2-b,-h/2),(w/2,-h/2+b),(w/2,h/2-b),(w/2-b,h/2),(-w/2+b,h/2),(-w/2,h/2-b),(-w/2,-h/2+b)]]
def thickness(ob,d):
    bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()
    bpy.context.view_layer.objects.active=ob;mod=ob.modifiers.new('Sheet thickness','SOLIDIFY');mod.thickness=d;mod.offset=-1;bpy.ops.object.modifier_apply(modifier=mod.name)
    return ob
def rod(name,a,b,radius,mat,c,root,n=12):
    av=Vector(a);delta=Vector(b)-av;normal=delta.normalized();u=normal.cross(Vector((0,0,1)))
    if u.length<.01:u=normal.cross(Vector((0,1,0)))
    u.normalize();v=normal.cross(u)
    outline=[tuple(av+radius*(math.cos(i*math.tau/n)*u+math.sin(i*math.tau/n)*v)) for i in range(n)]
    return dw.solid(name,outline,tuple(delta),mat,c,root)
def label(name,body,loc,size,mat,c,r):
    cu=bpy.data.curves.new(name,'FONT');cu.body=body;cu.align_x='CENTER';cu.align_y='CENTER';cu.size=size;cu.space_character=1.2;cu.extrude=.0002;cu.resolution_u=1
    ob=bpy.data.objects.new(name,cu);c.objects.link(ob);ob.parent=r;ob.location=loc;ob.rotation_euler=(math.pi/2,0,math.pi);cu.materials.append(mat);return ob

def quarter(s,name='Rear quarter'):
    c,r=collection(name,s,'quarter');m=palette();ys=sorted(set([1.174,1.234,1.82,2.14,2.236]+[y for y,z in dw.ARCH if 1.174<y<2.236]))
    # Deliberate transverse planes; the door and upper window boundaries stay fixed.
    zs=[.434,.505,.60,.87,.91,1.10,1.13,1.157];rel=[0,0,0,0,.006,.006,0,0]
    vv=[];ff=[]
    for ya,yb in zip(ys,ys[1:]):
        for za,zb in zip(zs,zs[1:]):
            poly=[(ya,za),(yb,za),(yb,zb),(ya,zb)];pp=[]
            for p,q in zip(poly,poly[1:]+poly[:1]):
                def low(y):return dw.lerp(y,dw.ARCH)+.004 if y<=dw.ARCH[-1][0] else .434
                da=p[1]-low(p[0]);db=q[1]-low(q[0])
                if da>=-1e-8:pp.append(p)
                if (da>=0)!=(db>=0):
                    t=da/(da-db);pp.append((p[0]+t*(q[0]-p[0]),p[1]+t*(q[1]-p[1])))
            clean=[]
            for p in pp:
                if not clean or math.dist(clean[-1],p)>1e-7:clean.append(p)
            if len(clean)>2 and math.dist(clean[0],clean[-1])<1e-7:clean.pop()
            if len(clean)<3:continue
            start=len(vv)
            for y,z in clean:
                fade=min(1.,max(0,(y-1.174)/.06),max(0,(2.236-y)/.06))
                vv.append((dw.edge_x(z)+dw.lerp(z,list(zip(zs,rel)))*fade,y,z))
            ff.append(tuple(range(start,len(vv))))
    skin=wf.mesh('Quarter | pressed side skin',vv,ff,m['paint'],c,r)
    skin['front_boundary'] = json.dumps([list(v.co) for v in skin.data.vertices if abs(v.co.y-1.174)<1e-6])
    thickness(skin,.006)
    # The complete arch lip uses the existing door interface, including its floor clamp.
    vv=[]
    for x,radius in [(.920,.475),(.936,.435),(.835,.435),(.835,.475)]:
        for i in range(9):
            a=math.pi-i*math.pi/8;vv.append((x,1.27+radius*math.cos(a),max(.43,.38+radius*math.sin(a))))
    ff=[(j*9+i,j*9+i+1,((j+1)%4)*9+i+1,((j+1)%4)*9+i) for j in range(4) for i in range(8)]
    ff += [(0,9,18,27),(8,35,26,17)]
    wf.mesh('Quarter | returned rear wheel arch',vv,ff,m['paint'],c,r)
    dw.box('Quarter | rubbing moulding',(.932,1.955,.811),(.025,.365,.031),m['rubber'],c,r,.004)
    # Rear lamp column: a real opening receives a separate cassette with clearance.
    col=dw.box('Quarter | lamp aperture column',(.823,2.234,.901),(.186,.024,.512),m['paint'],c,r)
    dw.cut(col,dw.solid('Temporary lamp opening',rect(.817,2.30,.918,.134,.350), (0,-.18,0),None,c,r))
    bevel=col.modifiers.new('Rear corner edge','BEVEL');bevel.width=.002;bevel.segments=2
    dw.box('Quarter | rear lower valance',(.824,2.226,.549),(.184,.040,.178),m['paint'],c,r,.003)
    # Formed pillar closes the rear corner without intruding into the existing
    # cargo frame. Its section follows both window planes throughout its height.
    z0,z1=1.179,1.724;x0=dw.cp(0,z0)[0];y0=2.24-.31*(z0-1.16)/.58
    outline=[(x0-.0005,y0+.0025,z0),(x0-.005,y0+.015,z0),(x0-.021,y0+.015,z0),(x0-.021,y0+.0025,z0)]
    delta=(-.125*(z1-z0)/.58,-.31*(z1-z0)/.58,z1-z0)
    dw.solid('Quarter | formed rear corner post',outline,delta,m['frame'],c,r)
    if s['side']==-1:
        aperture=dw.rect_yz(1.,1.952,1.030,.174,.136)
        dw.cut(skin,dw.solid('Temporary fuel filler opening',aperture,(-.18,0,0),None,c,r))
        outer=dw.rect_yz(.930,1.952,1.030,.177,.139);inner=dw.inset(outer,.003)
        dw.ring('Quarter | fuel flap seal',outer,inner,(-.017,0,0),m['rubber'],c,r)
        flap=dw.rect_yz(.931,1.952,1.030,.166,.128)
        dw.solid('Quarter | separate fuel flap',flap,(-.006,0,0),m['paint'],c,r)
        dw.box('Quarter | fuel flap finger recess',(.932,2.018,1.030),(.003,.014,.035),m['shadow'],c,r,.003)
    seal(c);return c

def lower_gate(s,name='Lower tailgate'):
    c,r=collection(name,s,'lower_gate');m=palette()
    # Parallel rectangular loops make planar folded shoulders around a calm
    # central face. Multiplying X/Z crown weights made large twisted quads.
    perimeter=[(-.724,2.244,.652),(.724,2.244,.652),(.724,2.244,1.152),(-.724,2.244,1.152)]
    inner=[(-.662,2.244+s['crown'],.686),(.662,2.244+s['crown'],.686),(.662,2.244+s['crown'],1.136),(-.662,2.244+s['crown'],1.136)]
    vv=perimeter+inner;ff=[(i,4+i,4+(i+1)%4,(i+1)%4) for i in range(4)]+[(7,6,5,4)]
    skin=wf.mesh('Lower gate | crowned sheet',vv,ff,m['paint'],c,r);thickness(skin,.006)
    skin['fixed_perimeter']=json.dumps(perimeter)
    dw.cut(skin,dw.solid('Temporary registration recess',rect(0,2.31,.879,.470,.154),(0,-.20,0),None,c,r))
    outer=rect(0,2.244+s['crown']+.002,.879,.484,.168);inner=dw.inset(outer,.010)
    dw.ring('Lower gate | registration aperture rim',outer,inner,(0,-.010,0),m['rubber'],c,r)
    back=[(x,2.215,z) for x,y,z in inner]
    wf.mesh('Lower gate | deep registration cup',inner+back,[(i,(i+1)%8,(i+1)%8+8,i+8) for i in range(8)]+[tuple(range(8,16))],m['shadow'],c,r)
    dw.box('Lower gate | registration plate',(0,2.233,.879),(.398,.006,.110),m['plate'],c,r,.004)
    label('Lower gate | registration text','GRAND TOUR',(0,2.237,.879),.037,m['shadow'],c,r)
    for x in [-.180,.180]:rod('Lower gate | plate screw',(x,2.234,.879),(x,2.239,.879),.004,m['edge'],c,r,10)
    # Recessed upper release uses an actual aperture and mounted grip.
    dw.cut(skin,dw.solid('Temporary release opening',rect(0,2.31,1.105,.200,.043,.006),(0,-.16,0),None,c,r))
    yy=2.244+s['crown']+.002;outer=rect(0,yy,1.105,.211,.054,.006);inner=dw.inset(outer,.006)
    dw.ring('Lower gate | release bezel',outer,inner,(0,-.010,0),m['rubber'],c,r)
    back=[(x,2.222,z) for x,y,z in inner]
    wf.mesh('Lower gate | release pocket',inner+back,[(i,(i+1)%8,(i+1)%8+8,i+8) for i in range(8)]+[tuple(range(8,16))],m['shadow'],c,r)
    dw.box('Lower gate | release grip',(0,yy+.001,1.115),(.163,.018,.012),m['frame'],c,r,.003)
    for x in [-.073,.073]:dw.box('Lower gate | release end return',(x,(yy+2.222)/2,1.115),(.017,yy-2.220,.012),m['frame'],c,r,.002)
    label('Lower gate | raised lettering','RANGE ROVER',(0,2.244+s['crown']+.0007,1.032),.035,m['frame'],c,r)
    dw.box('Lower gate | split weather seal',(0,2.247,1.158),(1.447,.034,.008),m['rubber'],c,r,.002)
    for x in [-.54,.54]:
        vv=[(x+dx,2.248+s['crown']*min(1,(z-.652)/.034),z) for z in [.660,.686,.697] for dx in [-.0595,.0595]]
        leaf=wf.mesh('Lower gate | fitted hinge leaf',vv,[(0,2,3,1),(2,4,5,3)],m['frame'],c,r);thickness(leaf,.007)
        rod('Lower gate | hinge barrel',(x-.061,2.257,.655),(x+.061,2.257,.655),.011,m['frame'],c,r)
    seal(c);return c

def rear_y(z):return 2.258-.31*(z-1.16)/.58
def upper_gate(s,name='Upper tailgate'):
    c,r=collection(name,s,'upper_gate');m=palette()
    outline=[(-.885,2.258,1.16),(.885,2.258,1.16),(.76,1.948,1.74),(-.76,1.948,1.74)]
    outer=dw.inset(outline,.004);inside=dw.inset(outer,.035)
    # Back of outer frame is inset to form a mitred return at cargo-window joints.
    backouter=[(x,y-.011,z) for x,y,z in dw.inset(outer,.016)]
    backinner=[(x,y-.011,z) for x,y,z in inside]
    vv=outer+inside+backouter+backinner;ff=[]
    for i in range(4):
        j=(i+1)%4;ff += [(i,j,4+j,4+i),(8+i,12+i,12+j,8+j),(i,8+i,8+j,j),(4+i,4+j,12+j,12+i)]
    wf.mesh('Upper gate | mitred glazed frame',vv,ff,m['frame'],c,r)
    header=dw.box('Upper gate | roof header weather seal',(0,1.940,1.7355),(1.478,.026,.015),m['rubber'],c,r,.002)
    header['intentional_roof_mount']=True
    trimouter=[(x,y+.001,z) for x,y,z in inside];triminner=dw.inset(trimouter,.0035)
    dw.ring('Upper gate | metal glazing reveal',trimouter,triminner,(0,-.004,0),m['edge'],c,r)
    gasket=[(x,y-.003,z) for x,y,z in triminner];seat=dw.inset(gasket,.010)
    dw.ring('Upper gate | glazing gasket',gasket,seat,(0,-.010,0),m['rubber'],c,r)
    pane=[(x,y-.006,z) for x,y,z in dw.inset(seat,.0005)]
    dw.solid('Upper gate | solid rear glass',pane,(0,-.003,0),m['glass'],c,r)
    for x in [-.55,.55]:
        yz=[(1.905,1.796),(1.936,1.796),(1.982,1.743),(1.982,1.719),(1.951,1.719),(1.951,1.741),(1.925,1.786),(1.905,1.786)]
        h=dw.solid('Upper gate | roof hinge bracket',[(x-.045,y,z) for y,z in yz],(.090,0,0),m['frame'],c,r);h['intentional_roof_mount']=True
        rod('Upper gate | hinge pin',(x-.060,1.968,1.732),(x+.060,1.968,1.732),.008,m['edge'],c,r)
    # Blade seats near the glazing plane; arm stands off it.
    z=1.229;rod('Upper gate | wiper spindle',(.27,rear_y(z)-.004,z),(.27,rear_y(z)+.021,z),.019,m['frame'],c,r)
    rod('Upper gate | wiper arm',(.27,rear_y(z)+.019,z),(.04,rear_y(1.317)+.014,1.317),.007,m['frame'],c,r,8)
    rod('Upper gate | wiper blade',(-.145,rear_y(1.321)-.002,1.321),(.250,rear_y(1.321)-.002,1.321),.006,m['rubber'],c,r,8)
    seal(c);return c

def lamp(s,name='Rear lamp cassette'):
    c,r=collection(name,s,'lamp');m=palette();x=.817
    outer=rect(x,2.263,.918,.128,.343);inside=dw.inset(outer,.009)
    dw.ring('Rear lamp | cassette bezel',outer,inside,(0,-.051,0),m['rubber'],c,r)
    dw.solid('Rear lamp | back shell',[(x,2.211,z) for x,y,z in outer],(0,-.005,0),m['frame'],c,r)
    for z,h,key in [(1.033,.085,'amber'),(.938,.075,'clear'),(.824,.128,'red')]:
        dw.box('Rear lamp | reflector '+key,(x,2.229,z),(.106,.024,h),m['edge'],c,r,.003)
        # A closed lens with shallow vertical optical ribs in its actual surface.
        n=24 if s['lens']=='ribbed' else 2;vv=[]
        for zz in [z-h/2,z+h/2]:
            for j in range(n+1):
                xx=x-.051+j*.102/n;yy=2.258+(.0024*(j%2) if s['lens']=='ribbed' else 0)
                vv.append((xx,yy,zz))
        count=len(vv);vv += [(xx,2.248,zz) for xx,yy,zz in vv]
        ff=[(j,j+1,n+2+j,n+1+j) for j in range(n)]+[(count+j,count+n+1+j,count+n+2+j,count+j+1) for j in range(n)]
        per=list(range(n+1))+list(range(2*n+1,n,-1))
        ff += [(a,b,b+count,a+count) for a,b in zip(per,per[1:]+per[:1])]
        wf.mesh('Rear lamp | '+key+' lens',vv,ff,m[key],c,r)
    for z in [.929-.045,1.033-.050]:dw.box('Rear lamp | cell divider',(x,2.249,z),(.109,.024,.008),m['rubber'],c,r,.001)
    for z in [.754,1.082]:rod('Rear lamp | mounting screw',(x,2.260,z),(x,2.266,z),.0037,m['edge'],c,r,10)
    seal(c);return c

def bumper(s,name='Rear step bumper'):
    c,r=collection(name,s,'bumper');m=palette()
    yz=[(2.200,.445),(2.333,.445),(2.363,.472),(2.363,.589),(2.340,.630),(2.270,.632),(2.198,.615)]
    vv=[(x,y,z) for x in [-.780,.780] for y,z in yz];n=len(yz)
    beam=wf.mesh('Rear bumper | stepped carrier',vv,[tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],m['beam'],c,r)
    # Real recessed tread deck, with clipped corners and visible edge thickness.
    for side in [-1,1]:
        poly=[(.787,2.349),(.903,2.347),(.979,2.271),(.958,2.044),(.934,2.044),(.916,2.200),(.787,2.198)]
        vv=[(side*x,y,z) for z in [.457,.614] for x,y in poly];n=len(poly)
        wf.mesh('Rear bumper | wraparound corner',vv,[tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],m['frame'],c,r,.005)
        dw.box('Rear bumper | chassis arm',(side*.38,2.155,.535),(.066,.170,.067),m['edge'],c,r,.003)
        dw.box('Rear bumper | recessed reflector pocket',(side*.599,2.365,.536),(.189,.012,.049),m['rubber'],c,r,.006)
        dw.box('Rear bumper | red reflector',(side*.599,2.373,.536),(.161,.007,.027),m['red'],c,r,.004)
    dw.box('Rear bumper | upper tread bed',(0,2.294,.632),(1.39,.070,.012),m['rubber'],c,r,.006)
    for x in [-.62+i*.062 for i in range(21)]:dw.box('Rear bumper | raised tread rib',(x,2.295,.640),(.018,.055,.005),m['frame'],c,r,.0015)
    dw.box('Rear bumper | face rubbing strip',(0,2.365,.591),(1.509,.012,.026),m['rubber'],c,r,.004)
    # Under-bumper finisher is a closed folded panel, not a floating flat plane.
    dw.box('Rear bumper | lower centre finisher',(0,2.241,.435),(.86,.070,.026),m['frame'],c,r,.005)
    seal(c);return c

BUILDERS=dict(quarter=quarter,lower_gate=lower_gate,upper_gate=upper_gate,lamp=lamp,bumper=bumper)
def rebuild(c,s):
    if wf.fingerprint(c)!=c.get('fingerprint'):raise RuntimeError('Manual edits detected; preserve this component as a variant')
    old=json.loads(c['spec']);s=dict(s,center=old['center'],side=old['side']);kind=c['kind'];validate(s,kind);before=set(bpy.data.collections);name=c.name
    try:
        new=BUILDERS[kind](s,name+' STAGED')
        if not wf.component_report(new)['finite']:raise RuntimeError('Invalid staged component')
    except Exception:
        for cc in set(bpy.data.collections)-before:wf.remove_collection(cc)
        raise
    wf.remove_collection(c);new.name=name;seal(new);return new
def fit_report(parts):
    bpy.context.view_layer.update();bounds={};closed={};contacts=[]
    for c in parts:
        for o in c.objects:
            if o.type!='MESH':continue
            for prop in ['fixed_perimeter','front_boundary']:
                if prop in o:
                    s=json.loads(c['spec']);points=[o.matrix_world@v.co for v in o.data.vertices];err=[]
                    for p in json.loads(o[prop]):
                        if prop=='front_boundary':p=[s['side']*dw.edge_x(p[2]),1.174,p[2]]
                        err.append(min((q-Vector(p)).length for q in points))
                    bounds[c.name]=max(err)
            if any(t in o.name for t in ['pressed side skin','returned rear wheel arch','crowned sheet','mitred glazed frame','solid rear glass','cassette bezel',' lens','stepped carrier']):
                bm=bmesh.new();bm.from_mesh(o.data);closed[o.name]=all(e.is_manifold for e in bm.edges);bm.free()
    for q in [c for c in parts if c['kind']=='quarter']:
        side=json.loads(q['spec'])['side'];col=next(o for o in q.objects if 'lamp aperture column' in o.name);tree=wf.tree(col)
        for c in [c for c in parts if c['kind']=='lamp' and json.loads(c['spec'])['side']==side]:
            for o in c.objects:
                if o.type=='MESH' and tree.overlap(wf.tree(o)):contacts.append([col.name,o.name])
    return dict(boundary_error_m=bounds,closed_selected_meshes=closed,lamp_column_intersections=contacts,
        scope='Static shared panel boundaries, selected closed meshes and lamp/column fit. No tailgate opening sweep, rear collision structure or game export validation.')
class GTRB_Settings(bpy.types.PropertyGroup):
    crown:bpy.props.FloatProperty(name='Tailgate crown',default=.017,min=.010,max=.024,unit='LENGTH')
    lens:bpy.props.EnumProperty(name='Rear lens',items=[('ribbed','Ribbed','Faceted optical ribs'),('smooth','Smooth','Plain lens face')],default='ribbed')
class GTRB_OT_Rebuild(bpy.types.Operator):
    bl_idname='gtrb.rebuild';bl_label='Rebuild selected rear component';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        c=next((c for c in context.active_object.users_collection if c.get('gt_owner')==OWNER),None) if context.active_object else None
        if not c:self.report({'ERROR'},'Select a rear workshop component');return {'CANCELLED'}
        s=json.loads(c['spec'])
        if c['kind']=='lower_gate':s['crown']=context.scene.gtrb.crown
        if c['kind']=='lamp':s['lens']=context.scene.gtrb.lens
        try:rebuild(c,s)
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
        return {'FINISHED'}
class GTRB_PT_Panel(bpy.types.Panel):
    bl_label='Rear Body Workshop';bl_idname='GTRB_PT_panel';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='GT Parts'
    def draw(self,context):
        l=self.layout;l.prop(context.scene.gtrb,'crown');l.prop(context.scene.gtrb,'lens');l.operator('gtrb.rebuild');l.label(text='Fixed boundaries; direct edits protected.')
CLASSES=[GTRB_Settings,GTRB_OT_Rebuild,GTRB_PT_Panel]
def register():
    if hasattr(bpy.types.Scene,'gtrb'):return
    for cls in CLASSES:bpy.utils.register_class(cls)
    bpy.types.Scene.gtrb=bpy.props.PointerProperty(type=GTRB_Settings)
def unregister():
    if hasattr(bpy.types.Scene,'gtrb'):del bpy.types.Scene.gtrb
    for cls in reversed(CLASSES):bpy.utils.unregister_class(cls)
if __name__=='__main__':register()
