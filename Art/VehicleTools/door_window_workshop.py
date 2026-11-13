"""Fitted RR door skins, layered window cassettes and serviceable mirrors.

Metres, front -Y. Importing has no scene side effects. Static exterior study.
"""
bl_info={'name':'Grand Tour Doors and Windows','author':'Grand Tour','version':(0,1,0),'blender':(5,1,0),'category':'Mesh'}
import bpy,bmesh,math,json,sys
from pathlib import Path
from mathutils import Vector
try:from . import wheel_fender_workshop as wf
except ImportError:
    sys.path.insert(0,str(Path(__file__).resolve().parent));import wheel_fender_workshop as wf
OWNER='GT_DOORS_01'
ARCH=[(1.27+.475*math.cos(math.pi-i*math.pi/8),max(.43,.38+.475*math.sin(math.pi-i*math.pi/8))) for i in range(9)]
ZROWS=[.509,.554,.610,.773,.815,1.025,1.100,1.130,1.157]
RELIEF=[0,0,-.009,-.009,.002,.008,.008,0,0]
WINDOWS={
    'front':[(-.77,1.16),(.23,1.16),(.23,1.74),(-.43,1.74)],
    'rear':[(.23,1.16),(1.17,1.16),(1.08,1.74),(.23,1.74)],
    'cargo':[(1.17,1.16),(2.24,1.16),(1.93,1.74),(1.08,1.74)]}

def spec(kind,side=1,position='front',**kw):
    return dict(center=[0,0,0],side=side,interface='rr-side-v1',position=position,relief=1.,seal_width=.010,**kw)

def validate(s,kind):
    if s['interface']!='rr-side-v1' or s['center']!=[0,0,0]:raise ValueError('Requires the RR side v1 origin and interface')
    if s['side'] not in [-1,1]:raise ValueError('Side must be -1 or 1')
    if s['position'] not in (['front','rear'] if kind=='door' else WINDOWS):raise ValueError('Unsupported position')
    if not .5<=s['relief']<=1.5:raise ValueError('Door relief range 0.5 to 1.5')
    if not .007<=s['seal_width']<=.014:raise ValueError('Seal width range 7 to 14 mm')

def palette():
    g=wf.material('Doors | mineral tinted glass',(.23,.33,.34),.045)
    bs=g.node_tree.nodes.get('Principled BSDF')
    # Initialize only once; a hand-edited existing material must not be reset.
    if not g.get('gt_initialized'):
        bs.inputs['Transmission Weight'].default_value=.82;bs.inputs['IOR'].default_value=1.46;g['gt_initialized']=True
    return dict(paint=wf.material('Muted heritage green',(.125,.265,.205),.57),
        frame=wf.material('Doors | satin window frame',(.042,.055,.056),.48,.18),
        rubber=wf.material('Doors | dense rubber',(.019,.025,.027),.80),
        shadow=wf.material('Doors | pocket interior',(.025,.035,.036),.72),
        edge=wf.material('Doors | brushed detail metal',(.28,.32,.31),.40,.65),
        glass=g,mirror=wf.material('Doors | mirror silver',(.72,.79,.80),.045,1.0))

def collection(name,s,kind):
    validate(s,kind);c,r=wf.root_collection(name,s,kind);c['gt_owner']=OWNER;return c,r

def seal(c):
    for o in c.objects:o['gt_owner']=OWNER
    wf.seal(c)

def box(name,loc,dim,mat,c,r,bevel=0):
    vs=[(loc[0]+x*dim[0]/2,loc[1]+y*dim[1]/2,loc[2]+z*dim[2]/2) for x,y,z in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]]
    return wf.mesh(name,vs,[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)],mat,c,r,bevel)

def solid(name,outline,delta,mat,c,r):
    n=len(outline);v=[Vector(p) for p in outline];dv=Vector(delta)
    return wf.mesh(name,[tuple(p) for p in v]+[tuple(p+dv) for p in v],
        [tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],mat,c,r)

def ring(name,outer,inner,delta,mat,c,r):
    n=len(outer);dv=Vector(delta);a=[Vector(p) for p in outer+inner]
    vs=[tuple(p) for p in a]+[tuple(p+dv) for p in a];ff=[]
    for i in range(n):
        j=(i+1)%n
        ff.extend([(i,j,n+j,n+i),(2*n+i,3*n+i,3*n+j,2*n+j),
            (i,2*n+i,2*n+j,j),(n+i,n+j,3*n+j,3*n+i)])
    return wf.mesh(name,vs,ff,mat,c,r)

def inset(poly,d):
    vs=[Vector(p) for p in poly];n=(vs[1]-vs[0]).cross(vs[2]-vs[0]).normalized();center=sum(vs,Vector())/len(vs);out=[]
    for i,v in enumerate(vs):
        a=n.cross((v-vs[i-1]).normalized());b=n.cross((vs[(i+1)%len(vs)]-v).normalized())
        if a.dot(center-v)<0:a=-a
        if b.dot(center-v)<0:b=-b
        bis=(a+b).normalized();out.append(tuple(v+bis*d/bis.dot(a)))
    return out

def rect_yz(x,y,z,w,h,b=.008):
    return [(x,y+a,z+c) for a,c in [(-w/2+b,-h/2),(w/2-b,-h/2),(w/2,-h/2+b),(w/2,h/2-b),(w/2-b,h/2),(-w/2+b,h/2),(-w/2,h/2-b),(-w/2,-h/2+b)]]

def cut(ob,cutter):
    bpy.context.view_layer.update();bpy.context.view_layer.objects.active=ob
    mod=ob.modifiers.new('Actual handle aperture','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
    bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)

def lerp(y,rows):
    if y<=rows[0][0]:return rows[0][1]
    for (a,x),(b,z) in zip(rows,rows[1:]):
        if y<=b:return x+(z-x)*(y-a)/(b-a)
    return rows[-1][1]

def edge_x(z):return .92 if z<=1.13 else .92-(z-1.13)*(.035/.030)

def bottom(y,position):return max(.509,lerp(y,ARCH)+.004) if position=='rear' else .509

def limits(position):return (-.766,.226) if position=='front' else (.234,1.166)

def door_x(y,z,s):
    lo,hi=limits(s['position']);fade=min(1.,max(0,(y-lo)/.060),max(0,(hi-y)/.060))
    # Both exterior ends and the lower arch boundary remain on the shared surface.
    fade*=min(1.,max(0,(z-bottom(y,s['position']))/.035))
    return edge_x(z)+s['relief']*lerp(z,list(zip(ZROWS,RELIEF)))*fade

def door(s,name='Door assembly'):
    c,r=collection(name,s,'door');m=palette();pos=s['position'];lo,hi=limits(pos)
    ys=sorted(set([lo,lo+.060,hi-.060,hi]+[y for y,z in ARCH if lo<y<hi]))
    # Include the exact sill/arch crossover to keep the clipped surface watertight.
    if pos=='rear':
        for (y0,z0),(y1,z1) in zip(ARCH,ARCH[1:]):
            if z0<.505<z1:
                yy=y0+(y1-y0)*(.505-z0)/(z1-z0)
                if lo<yy<hi:ys.append(yy)
        ys=sorted(set(ys))
    verts=[];faces=[]
    for a,b in zip(ys,ys[1:]):
        for z0,z1 in zip(ZROWS,ZROWS[1:]):
            poly=[(a,z0),(b,z0),(b,z1),(a,z1)];clipped=[]
            for p,q in zip(poly,poly[1:]+poly[:1]):
                dp=p[1]-bottom(p[0],pos);dq=q[1]-bottom(q[0],pos)
                if dp>=-1e-8:clipped.append(p)
                if (dp>=0)!=(dq>=0):
                    t=dp/(dp-dq);clipped.append((p[0]+t*(q[0]-p[0]),p[1]+t*(q[1]-p[1])))
            clean=[]
            for p in clipped:
                if not clean or math.dist(clean[-1],p)>1e-7:clean.append(p)
            if len(clean)>2 and math.dist(clean[0],clean[-1])<1e-7:clean.pop()
            if len(clean)<3:continue
            idx=len(verts);verts += [(door_x(y,z,s),y,z) for y,z in clean];faces.append(tuple(range(idx,len(verts))))
    skin=wf.mesh('Door | pressed outer skin',verts,faces,m['paint'],c,r)
    bm=bmesh.new();bm.from_mesh(skin.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    # Orient skin outwards before adding its inward thickness.
    if sum(f.normal.x*f.calc_area() for f in bm.faces)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
    boundary=[list(v.co) for v in bm.verts if v.is_boundary];bm.to_mesh(skin.data);bm.free()
    skin['interface_boundary']=json.dumps(boundary)
    bpy.context.view_layer.objects.active=skin
    mod=skin.modifiers.new('Folded sheet thickness','SOLIDIFY');mod.thickness=.006;mod.offset=-1
    bpy.ops.object.modifier_apply(modifier=mod.name)
    # Real hole, a deep cup and a bridge grip; the dark pocket is not a decal.
    hy=.080 if pos=='front' else .990;hz=1.058
    aperture=rect_yz(1.,hy,hz,.174,.074)
    cut(skin,solid('Temporary handle cutter',aperture,(-.17,0,0),None,c,r))
    outer=rect_yz(.935,hy,hz,.182,.082);inner=rect_yz(.935,hy,hz,.157,.057)
    ring('Handle | aperture lip',outer,inner,(-.012,0,0),m['rubber'],c,r)
    deep=[(.883,y,z) for x,y,z in inner]
    # Continuous pocket wall and back follow the same eight-point opening.
    wf.mesh('Handle | recessed cup',inner+deep,[(i,(i+1)%8,(i+1)%8+8,i+8) for i in range(8)]+[tuple(range(8,16))],m['shadow'],c,r)
    box('Handle | bridge grip',(.940,hy,hz+.012),(.024,.138,.016),m['frame'],c,r,.004)
    for yy in [hy-.061,hy+.061]:box('Handle | grip return',(.914,yy,hz+.012),(.057,.015,.017),m['frame'],c,r,.003)
    if pos=='front':
        wf.cylinder('Handle | lock barrel',.934,hy+.105,hz,.008,.009,m['edge'],c,r,12)
        box('Handle | key slot',(.939,hy+.105,hz),(.001,.0015,.008),m['shadow'],c,r)
    # Belt weather strip follows the upper shared ledge, with a real return.
    box('Door | belt weather strip',(.886,(lo+hi)/2,1.159),(.018,hi-lo,.015),m['rubber'],c,r,.002)
    # Separate rubbing moulding stops at the door gap and rear arch.
    trim_end=min(hi-.025,.925 if pos=='rear' else hi-.025)
    box('Door | protective rubbing moulding',(.932,(lo+.025+trim_end)/2,.811),(.025,trim_end-lo-.025,.031),m['rubber'],c,r,.004)
    # Inner perimeter return makes the thickness visible when inspected separately.
    # Static jamb structure stays under the skin; no hinge/operating-door claims.
    for yy in [lo+.013,hi-.013]:
        z0=bottom(yy,pos)+.019
        box('Door | inner edge return',(.892,yy,(z0+1.135)/2),(.044,.018,1.135-z0),m['paint'],c,r,.002)
    seal(c);return c

def cp(y,z):return (.885-.125*(z-1.16)/.58,y,z)

def window(s,name='Side window cassette'):
    c,r=collection(name,s,'window');m=palette()
    q=WINDOWS[s['position']];t=(1.729-1.16)/.58
    # The inherited gutter extends below the roof edge. Seat the frame beneath
    # its bottom (1.7305), rather than intersecting it at the old glass datum.
    outline=[cp(*q[0]),cp(*q[1]),cp(q[1][0]+(q[2][0]-q[1][0])*t,1.729),cp(q[0][0]+(q[3][0]-q[0][0])*t,1.729)]
    outer=inset(outline,.0015)
    opening=inset(outer,.027 if s['position']!='cargo' else .038)
    ring('Window | folded surround',outer,opening,(-.016,0,0),m['frame'],c,r)
    # Outer trim, flexible gasket and glass seats use one nested profile.
    trim_outer=[(x+.002,y,z) for x,y,z in opening]
    trim_inner=inset(trim_outer,.0035)
    ring('Window | fine metal reveal',trim_outer,trim_inner,(-.004,0,0),m['edge'],c,r)
    seal_outer=[(x-.002,y,z) for x,y,z in trim_inner];seal_inner=inset(seal_outer,s['seal_width'])
    ring('Window | extruded glazing seal',seal_outer,seal_inner,(-.011,0,0),m['rubber'],c,r)
    glass_edge=[(x-.007,y,z) for x,y,z in inset(seal_inner,.0005)]
    pane=solid('Window | inset solid pane',glass_edge,(-.003,0,0),m['glass'],c,r)
    pane['seat_outline']=json.dumps(glass_edge)
    # Separate lower water-shedding lip is deliberately seated against the frame.
    lo,hi=WINDOWS[s['position']][0][0],WINDOWS[s['position']][1][0]
    box('Window | lower drip lip',(.888,(lo+hi)/2,1.172),(.020,hi-lo-.009,.009),m['rubber'],c,r,.0015)
    seal(c);return c

def mirror(s,name='Door mirror'):
    c,r=collection(name,s,'mirror');m=palette()
    # Triangular sail base follows the sloping front window plane.
    base=[cp(-.727,1.185),cp(-.584,1.185),cp(-.606,1.357)]
    solid('Mirror | triangular sail mount',[(x+.013,y,z) for x,y,z in base],(-.026,0,0),m['rubber'],c,r)
    box('Mirror | pivot foot',(.906,-.642,1.245),(.097,.055,.051),m['frame'],c,r,.007)
    box('Mirror | angled support',(.969,-.629,1.261),(.085,.049,.036),m['frame'],c,r,.006)
    # Housing is an open-backed eight-sided shell. Glass faces rear (+Y).
    xz=[(-.098,-.051),(-.079,-.074),(.077,-.074),(.103,-.050),(.103,.054),(.080,.075),(-.078,.075),(-.098,.053)]
    rim=[(1.071+x,-.565,1.304+z) for x,z in xz]
    rear=[(1.068+x*.88,-.670,1.304+z*.85) for x,z in xz]
    aperture=inset(rim,.010)
    wf.mesh('Mirror | chamfered open housing',rim+rear+aperture,
        [(i,(i+1)%8,(i+1)%8+8,i+8) for i in range(8)]+[tuple(range(8,16))]+[(i,16+i,16+(i+1)%8,(i+1)%8) for i in range(8)],m['frame'],c,r)
    gasket=[(x,y+.001,z) for x,y,z in aperture];inside=inset(gasket,.005)
    ring('Mirror | glass perimeter gasket',gasket,inside,(0,-.014,0),m['rubber'],c,r)
    face=[(x,y-.004,z) for x,y,z in inset(inside,.0005)]
    solid('Mirror | recessed silver glass',face,(0,-.003,0),m['mirror'],c,r)
    # Cap seam follows the housing cross-section instead of a floating flat strip.
    t=.61;center=Vector((1.071*(1-t)+1.068*t,-.565-.105*t,1.304));band=[]
    for a,b in zip(rim,rear):
        p=Vector(a).lerp(Vector(b),t);radial=(p-center).normalized();band.append(tuple(p+radial*.0007))
    ring('Mirror | fitted casing seam',band,inset(band,.0018),(0,-.002,0),m['rubber'],c,r)
    seal(c);return c

BUILDERS={'door':door,'window':window,'mirror':mirror}
def rebuild(c,s):
    if wf.fingerprint(c)!=c.get('fingerprint'):raise RuntimeError('Manual edits detected; preserve this part as a variant')
    old=json.loads(c['spec']);s=dict(s,center=old['center'],side=old['side'],position=old['position']);kind=c['kind'];validate(s,kind)
    before=set(bpy.data.collections);name=c.name
    try:
        new=BUILDERS[kind](s,name+' STAGED')
        if not wf.component_report(new)['finite']:raise RuntimeError('Invalid staged geometry')
    except Exception:
        for cc in set(bpy.data.collections)-before:wf.remove_collection(cc)
        raise
    wf.remove_collection(c);new.name=name;seal(new);return new

def fit_report(parts):
    bpy.context.view_layer.update();boundaries={};glass={};closed={}
    for c in parts:
        for ob in c.objects:
            if ob.type!='MESH':continue
            if 'pressed outer skin' in ob.name:
                coords=[ob.matrix_world@v.co for v in ob.data.vertices];s=json.loads(c['spec']);errors=[]
                for p in json.loads(ob['interface_boundary']):
                    expected=Vector((s['side']*edge_x(p[2]),p[1],p[2]));errors.append(min((v-expected).length for v in coords))
                boundaries[c.name]=max(errors)
            if 'inset solid pane' in ob.name:
                glass[c.name]=len(ob.data.vertices)==8 and max(abs(v.co.x-cp(v.co.y,v.co.z)[0]+.007) for v in list(ob.data.vertices)[:4])<1e-6
            if any(t in ob.name for t in ['pressed outer skin','inset solid pane','folded surround','extruded glazing seal','recessed silver glass']):
                bm=bmesh.new();bm.from_mesh(ob.data);closed[ob.name]=all(e.is_manifold for e in bm.edges);bm.free()
    return dict(boundary_error_m=boundaries,closed_meshes=closed,pane_seats=glass,
        front_rear_door_gap_m=.008,scope='Static exterior fit, shared skin boundaries and closed selected meshes. Door motion, weatherproofing, UVs, LODs and game export are not validated.')

class GTDW_Settings(bpy.types.PropertyGroup):
    relief:bpy.props.FloatProperty(name='Door pressing relief',default=1.,min=.5,max=1.5)
    seal_width:bpy.props.FloatProperty(name='Window seal width',default=.010,min=.007,max=.014,unit='LENGTH')
class GTDW_OT_Rebuild(bpy.types.Operator):
    bl_idname='gtdw.rebuild';bl_label='Rebuild selected side component';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        c=next((c for c in context.active_object.users_collection if c.get('gt_owner')==OWNER),None) if context.active_object else None
        if not c:self.report({'ERROR'},'Select a door, window or mirror component');return {'CANCELLED'}
        s=json.loads(c['spec'])
        if c['kind']=='door':s['relief']=context.scene.gtdw.relief
        if c['kind']=='window':s['seal_width']=context.scene.gtdw.seal_width
        try:rebuild(c,s)
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
        return {'FINISHED'}
class GTDW_PT_Panel(bpy.types.Panel):
    bl_label='Doors and Windows Workshop';bl_idname='GTDW_PT_panel';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='GT Parts'
    def draw(self,context):
        l=self.layout;l.prop(context.scene.gtdw,'relief');l.prop(context.scene.gtdw,'seal_width');l.operator('gtdw.rebuild')
        l.label(text='Fixed boundaries; direct edits protected.')
CLASSES=[GTDW_Settings,GTDW_OT_Rebuild,GTDW_PT_Panel]
def register():
    if hasattr(bpy.types.Scene,'gtdw'):return
    for cls in CLASSES:bpy.utils.register_class(cls)
    bpy.types.Scene.gtdw=bpy.props.PointerProperty(type=GTDW_Settings)
def unregister():
    if hasattr(bpy.types.Scene,'gtdw'):del bpy.types.Scene.gtdw
    for cls in reversed(CLASSES):bpy.utils.unregister_class(cls)
if __name__=='__main__':register()
