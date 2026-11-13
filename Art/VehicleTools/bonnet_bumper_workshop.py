"""Fitted bonnet surfaces, stepped bumper carriers and swappable recessed inserts.

RR study interface, metres, front -Y. Imports do not mutate the scene.
"""
bl_info={'name':'Grand Tour Bonnet and Bumper Workshop','author':'Grand Tour',
         'version':(0,1,0),'blender':(5,1,0),'category':'Mesh'}
import bpy,math,json,sys
from pathlib import Path
from mathutils import Vector
try:from . import wheel_fender_workshop as wf
except ImportError:
    sys.path.insert(0,str(Path(__file__).resolve().parent));import wheel_fender_workshop as wf
OWNER='GT_BONNET_BUMPER_01'
HOOD=dict(center=[0,0,0],side=1,interface='rr-bonnet-v1',crown=.052,plateau=.64)
BUMPER=dict(center=[0,0,0],side=1,interface='rr-bumper-v1')
STATIONS=[-2.024,-1.94,-1.84,-1.10,-.84,-.776]
RISE=[0,.80,1,1,.40,0]

def width(y):return .875+.045*max(0,min(1,(y+2.03)/.19))
def shoulder(y):return 1.135+.025*max(0,min(1,(y+2.03)/1.26))
def palette():
    return dict(paint=wf.material('Muted heritage green',(.125,.265,.205),.57),
                beam=wf.material('Bumper | graphite powdercoat',(.063,.080,.083),.56,.18),
                cap=wf.material('Bumper | moulded corner caps',(.038,.052,.056),.72),
                rubber=wf.material('Bumper | rubber rubbing strip',(.019,.027,.030),.84),
                dark=wf.material('Bumper | recessed shadow',(.013,.020,.023),.80),
                metal=wf.material('Bumper | satin skid plate',(.21,.25,.25),.46,.60))

def validate(s,kind):
    expected={'bonnet':'rr-bonnet-v1','bumper':'rr-bumper-v1','insert':'rr-bumper-insert-v1'}[kind]
    if s['interface']!=expected:raise ValueError('Unsupported mating interface')
    if s['center']!=[0,0,0]:raise ValueError('This study requires the original assembly origin')
    if kind=='bonnet':
        if not .030<=s['crown']<=.070:raise ValueError('Crown range .030 to .070 m')
        if not .55<=s['plateau']<=.70:raise ValueError('Bonnet plateau range .55 to .70 of half width')
    if kind=='insert' and s['variant'] not in ['vent','blank']:raise ValueError('Insert variant must be vent or blank')

def collection(name,s,kind):
    c,r=wf.root_collection(name,s,kind);c['gt_owner']=OWNER;r.scale=(1,1,1);return c,r
def seal(c):
    for o in c.objects:o['gt_owner']=OWNER
    wf.seal(c)

def box(name,loc,dim,mat,c,root,bevel=0):
    vs=[(loc[0]+x*dim[0]/2,loc[1]+y*dim[1]/2,loc[2]+z*dim[2]/2)
        for x,y,z in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]]
    return wf.mesh(name,vs,[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)],mat,c,root,bevel)
def cut(ob,cutter):
    bpy.context.view_layer.update();bpy.context.view_layer.objects.active=ob
    mod=ob.modifiers.new('Actual recessed opening','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
    bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)

def bonnet(s,name='Bonnet'):
    validate(s,'bonnet');c,r=collection(name,s,'bonnet');m=palette()
    p=s['plateau'];fractions=[-1,-.82,-p,p,.82,1];weights=[0,.10,1,1,.10,0]
    verts=[];faces=[];n=6;rows=len(STATIONS)
    for offset in [0,-.004]:
        for y,lift in zip(STATIONS,RISE):
            w=width(y)-.039
            for u,k in zip(fractions,weights):verts.append((w*u,y,shoulder(y)+.006+s['crown']*lift*k+offset))
    count=n*rows
    for off in [0,count]:
        for j in range(rows-1):
            for i in range(n-1):faces.append((off+j*n+i,off+j*n+i+1,off+(j+1)*n+i+1,off+(j+1)*n+i))
    perimeter=list(range(n))+[j*n+n-1 for j in range(1,rows)]+list(range((rows-1)*n+n-2,(rows-1)*n-1,-1))+[j*n for j in range(rows-2,0,-1)]
    for a,b in zip(perimeter,perimeter[1:]+perimeter[:1]):faces.append((a,b,b+count,a+count))
    skin=wf.mesh('Bonnet | crowned folded skin',verts,faces,m['paint'],c,r)
    skin['edge_vertex_indices']=json.dumps([[j*n,j*n+5] for j in range(rows)])
    # Recessed underside beads/returns follow the skin's side guide, stopping clear
    # of the fixed nose cap and scuttle. They are separate editable pressings.
    for side in [-1,1]:
        rail=[]
        for y in STATIONS[1:-1]:
            x=side*(width(y)-.058);z=shoulder(y)-.008
            rail.extend([(x,y,z),(x-side*.014,y,z),(x-side*.014,y,z+.012),(x,y,z+.012)])
        ff=[(3,2,1,0),(12,13,14,15)]
        ff += [(j*4+k,j*4+(k+1)%4,(j+1)*4+(k+1)%4,(j+1)*4+k) for j in range(3) for k in range(4)]
        wf.mesh('Bonnet | underside edge return',rail,ff,m['paint'],c,r)
    # Actual latch mounting pad is underneath, without decorative exterior vents.
    pad=[]
    for down in [.004,.018]:
        for x,y in [(-.06,-1.98),(.06,-1.98),(.06,-1.94),(-.06,-1.94)]:
            lift=RISE[0]+(RISE[1]-RISE[0])*(y-STATIONS[0])/(STATIONS[1]-STATIONS[0])
            pad.append((x,y,shoulder(y)+.006+s['crown']*lift-down))
    wf.mesh('Bonnet | fitted latch mounting pad',pad,[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],m['metal'],c,r)
    seal(c);return c

def bumper(s,name='Bumper carrier'):
    validate(s,'bumper');c,r=collection(name,s,'bumper');m=palette()
    profile=[(-2.080,.455),(-2.197,.455),(-2.225,.482),(-2.225,.629),(-2.207,.663),(-2.160,.674),(-2.038,.665)]
    verts=[(x,y,z) for x in [-.780,.780] for y,z in profile];n=len(profile)
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    beam=wf.mesh('Bumper | stepped carrier with openings',verts,faces,m['beam'],c,r)
    for side in [-1,1]:
        cut(beam,box('Temporary insert aperture',(side*.590,-2.17,.550),(.236,.45,.084),None,c,r))
        cut(beam,box('Temporary lower inlet',(side*.205,-2.17,.498),(.138,.45,.028),None,c,r))
        box('Bumper | lower inlet backing',(side*.205,-2.128,.498),(.136,.008,.026),m['dark'],c,r)
    mod=beam.modifiers.new('Manufactured aperture edges','BEVEL');mod.width=.002;mod.segments=2
    mod=beam.modifiers.new('Carrier planar normals','WEIGHTED_NORMAL');mod.keep_sharp=True
    for side in [-1,1]:
        poly=[(.787,-2.216),(.903,-2.210),(.981,-2.127),(.958,-1.908),(.933,-1.908),(.916,-2.040),(.787,-2.038)]
        vv=[(side*x,y,z) for z in [.469,.657] for x,y in poly];nn=len(poly)
        ff=[tuple(range(nn-1,-1,-1)),tuple(range(nn,nn*2))]+[(i,(i+1)%nn,(i+1)%nn+nn,i+nn) for i in range(nn)]
        wf.mesh('Bumper | wraparound corner cap',vv,ff,m['cap'],c,r,.006)
    box('Bumper | upper rubbing strip',(0,-2.228,.626),(1.505,.014,.038),m['rubber'],c,r,.005)
    box('Bumper | recessed registration mount',(0,-2.235,.569),(.315,.010,.087),m['dark'],c,r,.004)
    for side in [-1,1]:
        box('Bumper | chassis mounting arm',(side*.38,-2.025,.55),(.065,.190,.067),m['metal'],c,r,.004)
    # A folded lower guard; real slots let its thickness read without surface decals.
    outline=[(-.525,-2.174,.438),(.525,-2.174,.438),(.460,-1.946,.354),(-.460,-1.946,.354)]
    vv=outline+[(x,y+.005,z-.008) for x,y,z in outline]
    guard=wf.mesh('Bumper | folded lower guard',vv,[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],m['metal'],c,r)
    for x in [-.30,0,.30]:cut(guard,box('Temporary guard slot',(x,-2.063,.400),(.084,.066,.20),None,c,r))
    for side in [-1,1]:
        # Short tabs join the guard's sloping upper face to the carrier underside.
        # Their ends deliberately enter the two parent pieces by about 2 mm.
        yz=[(y,.438+(y+2.174)*(-.084/.228)-.002) for y in [-2.16,-2.10]]+[(-2.10,.467),(-2.16,.467)]
        vv=[(side*.405+dx,y,z) for dx in [-.011,.011] for y,z in yz]
        wf.mesh('Bumper | lower guard mounting tab',vv,[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],m['metal'],c,r)
    seal(c);return c

def insert(s,name='Bumper insert'):
    validate(s,'insert');c,r=collection(name,s,'insert');m=palette();x=s['side']*.590
    frame=box('Insert | recessed frame',(x,-2.177,.55),(.230,.084,.078),m['cap'],c,r)
    cut(frame,box('Temporary insert mouth',(x,-2.177,.55),(.207,.20,.057),None,c,r))
    mod=frame.modifiers.new('Moulded opening edge','BEVEL');mod.width=.0015;mod.segments=2
    box('Insert | rear cavity',(x,-2.136,.55),(.224,.008,.073),m['dark'],c,r)
    if s['variant']=='vent':
        for z in [.531,.550,.569]:box('Insert | recessed louvre',(x,-2.200,z),(.204,.025,.006),m['beam'],c,r,.001)
    else:box('Insert | blank cover',(x,-2.211,.55),(.205,.008,.055),m['cap'],c,r,.002)
    c['slot_center']=json.dumps([x,-2.177,.55]);seal(c);return c

def fit_report(hc,bc,inserts):
    bpy.context.view_layer.update();skin=next(o for o in hc.objects if 'crowned folded skin' in o.name)
    errors=[]
    for j,y in enumerate(STATIONS):
        for k,side in [(0,-1),(5,1)]:
            actual=skin.matrix_world@skin.data.vertices[j*6+k].co
            expected=Vector((side*(width(y)-.039),y,shoulder(y)+.006))
            errors.append((actual-expected).length)
    beam=next(o for o in bc.objects if 'stepped carrier' in o.name);bt=wf.tree(beam);contacts=[]
    for c in inserts:
        for ob in c.objects:
            if ob.type=='MESH' and bt.overlap(wf.tree(ob)):contacts.append([c.name,ob.name])
    return dict(bonnet_boundary_error_m=max(errors),bonnet_side_gap_m=.004,bonnet_rear_gap_m=.006,
                insert_carrier_intersections=contacts,
                scope='Bonnet boundary vertices against the fixed interface and static insert/carrier surfaces. Chassis arms are intentional mounting overlaps. No articulation, crash, UV/LOD or game validation.')

def rebuild(c,s):
    if wf.fingerprint(c)!=c.get('fingerprint'):raise RuntimeError('Manual edits detected; preserve this part as a variant')
    kind=c['kind'];old=json.loads(c['spec']);s=dict(s,center=old['center'],side=old['side']);validate(s,kind)
    before=set(bpy.data.collections);name=c.name
    try:
        new={'bonnet':bonnet,'bumper':bumper,'insert':insert}[kind](s,name+' STAGED')
        if not wf.component_report(new)['finite']:raise RuntimeError('Invalid staged geometry')
    except Exception:
        for cc in set(bpy.data.collections)-before:wf.remove_collection(cc)
        raise
    wf.remove_collection(c);new.name=name;seal(new);return new

class GTBB_Settings(bpy.types.PropertyGroup):
    crown:bpy.props.FloatProperty(name='Bonnet crown',default=.052,min=.030,max=.070,unit='LENGTH')
    plateau:bpy.props.FloatProperty(name='Centre plateau',default=.64,min=.55,max=.70)
    variant:bpy.props.EnumProperty(name='Insert',items=[('vent','Vent','Recessed louvres'),('blank','Blank','Solid insert')],default='vent')
class GTBB_OT_Rebuild(bpy.types.Operator):
    bl_idname='gtbb.rebuild';bl_label='Rebuild selected bonnet / bumper part';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        c=next((c for c in context.active_object.users_collection if c.get('gt_owner')==OWNER),None) if context.active_object else None
        if not c:self.report({'ERROR'},'Select a bonnet, bumper or insert mesh');return {'CANCELLED'}
        s=json.loads(c['spec']);p=context.scene.gtbb
        if c['kind']=='bonnet':s.update(crown=p.crown,plateau=p.plateau)
        if c['kind']=='insert':s['variant']=p.variant
        try:rebuild(c,s)
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
        return {'FINISHED'}
class GTBB_PT_Panel(bpy.types.Panel):
    bl_label='Bonnet and Bumper Workshop';bl_idname='GTBB_PT_panel';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='GT Parts'
    def draw(self,context):
        l=self.layout
        for k in ['crown','plateau','variant']:l.prop(context.scene.gtbb,k)
        l.operator('gtbb.rebuild');l.label(text='Fixed RR interfaces. Manual edits protected.')
CLASSES=[GTBB_Settings,GTBB_OT_Rebuild,GTBB_PT_Panel]
def register():
    for cls in CLASSES:bpy.utils.register_class(cls)
    bpy.types.Scene.gtbb=bpy.props.PointerProperty(type=GTBB_Settings)
def unregister():
    if hasattr(bpy.types.Scene,'gtbb'):del bpy.types.Scene.gtbb
    for cls in reversed(CLASSES):bpy.utils.unregister_class(cls)
if __name__=='__main__':register()
