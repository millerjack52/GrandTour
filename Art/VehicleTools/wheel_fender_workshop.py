"""Grand Tour wheel/fender authoring primitives and optional Blender sidebar.

Import is non-destructive. Run as a Blender Text to register the GT Parts panel.
Units: metres; axle along X; front -Y. This first fender interface is RR-study specific.
"""
bl_info = {'name': 'Grand Tour Wheel and Fender Workshop', 'author': 'Grand Tour',
           'version': (0, 1, 0), 'blender': (5, 1, 0), 'category': 'Mesh'}
import bpy, bmesh, math, json, hashlib
from mathutils import Vector
from mathutils.bvhtree import BVHTree

OWNER = 'GT_WHEEL_FENDER_01'
DEFAULT = dict(radius=.38, width=.272, rim_radius=.225, clearance=.064,
               center=[.78, -1.36, .38], side=1, interface='rr-front-v1')
# [fraction of half width, fraction of carcass radius]; explicit closed section.
PROFILE = [(-.86,.61),(-1,.78),(-.99,.89),(-.81,.963),(-.54,.991),
           (0,1),(.54,.991),(.81,.963),(.99,.89),(1,.78),(.92,.64),(.84,.61)]

def material(name, color, rough=.6, metallic=0):
    m=bpy.data.materials.get(name)
    if m: return m
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Roughness'].default_value=rough; bs.inputs['Metallic'].default_value=metallic
    return m

def palette():
    return dict(rubber=material('Workshop | charcoal rubber',(.024,.030,.032),.84),
                tread=material('Workshop | tread faces',(.032,.039,.041),.86),
                steel=material('Workshop | warm satin alloy',(.32,.305,.255),.38,.65),
                edge=material('Workshop | machined edge',(.53,.54,.50),.32,.75),
                black=material('Workshop | inner liner',(.016,.022,.025),.78),
                hub=material('Workshop | hub enamel',(.06,.075,.072),.43,.35),
                paint=material('Muted heritage green',(.125,.265,.205),.57))

def mesh(name, verts, faces, mat, coll, parent=None, bevel=0):
    me=bpy.data.meshes.new(name); me.from_pydata(verts,[],faces); me.update()
    bm=bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(me); bm.free()
    ob=bpy.data.objects.new(name,me); coll.objects.link(ob)
    if mat: me.materials.append(mat)
    ob.parent=parent; ob['gt_owner']=OWNER
    if bevel:
        mod=ob.modifiers.new('Small manufactured edge', 'BEVEL'); mod.width=bevel; mod.segments=2
        mod=ob.modifiers.new('Weighted corner normals', 'WEIGHTED_NORMAL'); mod.keep_sharp=True
    return ob

def revolve(name, profile, mat, coll, root, segments=64, smooth=False):
    """Closed editable cross-section revolved about X; no caps hidden behind a disc."""
    verts=[(x,r*math.sin(i*math.tau/segments),r*math.cos(i*math.tau/segments))
           for x,r in profile for i in range(segments)]
    faces=[(j*segments+i,j*segments+(i+1)%segments,
            ((j+1)%len(profile))*segments+(i+1)%segments,((j+1)%len(profile))*segments+i)
           for j in range(len(profile)) for i in range(segments)]
    ob=mesh(name,verts,faces,mat,coll,root)
    if smooth:
        for p in ob.data.polygons:p.use_smooth=True
    return ob

def cylinder(name, x, y, z, radius, depth, mat, coll, root, segments=12, radial_scale=1):
    verts=[(xx,y+radius*math.sin(i*math.tau/segments),z+radius*radial_scale*math.cos(i*math.tau/segments))
           for xx in [x-depth/2,x+depth/2] for i in range(segments)]
    faces=[tuple(range(segments-1,-1,-1)),tuple(range(segments,segments*2))]
    faces += [(i,(i+1)%segments,(i+1)%segments+segments,i+segments) for i in range(segments)]
    return mesh(name,verts,faces,mat,coll,root)

def validate_spec(s):
    if s['interface']!='rr-front-v1': raise ValueError('Unsupported fender interface')
    if not .36<=s['radius']<=.39: raise ValueError('Supported tyre radius: .36 to .39 m')
    if not .24<=s['width']<=.29: raise ValueError('Supported tyre width: .24 to .29 m')
    if not .05<=s['clearance']<=.075: raise ValueError('Supported arch clearance: .05 to .075 m')
    if abs(s['rim_radius']-.225)>1e-6: raise ValueError('This rim template requires radius .225 m')
    if s['side'] not in [-1,1]:raise ValueError('side must be -1 or +1')
    if len(s['center'])!=3 or not all(math.isfinite(v) for v in s['center']):raise ValueError('Invalid center')

def root_collection(name,s,kind):
    coll=bpy.data.collections.new(name); bpy.context.scene.collection.children.link(coll)
    coll['gt_owner']=OWNER;coll['kind']=kind;coll['spec']=json.dumps(s)
    root=bpy.data.objects.new(name+' | mount',None); coll.objects.link(root)
    root.location=s['center']; root.scale.x=s['side']; root.empty_display_type='ARROWS';root.empty_display_size=.1
    root['gt_owner']=OWNER; root['mount']=True
    return coll,root

def profile_guide(coll,root,s):
    cu=bpy.data.curves.new('Tyre cross-section — edit points then rebuild wheel','CURVE')
    cu.dimensions='3D';sp=cu.splines.new('POLY');profile=s.get('profile',PROFILE)
    sp.points.add(len(profile)-1)
    for p,(x,r) in zip(sp.points,profile): p.co=(x*s['width']/2,0,r*(s['radius']-.014),1)
    sp.use_cyclic_u=True
    ob=bpy.data.objects.new('Tyre profile | editable guide',cu);coll.objects.link(ob);ob.parent=root
    ob.hide_render=True;ob.hide_set(True);ob['profile_guide']=True;ob['gt_owner']=OWNER
    return ob

def wheel(s,name='Wheel'):
    validate_spec(s);c,root=root_collection(name,s,'wheel');m=palette()
    r=s['radius'];w=s['width'];h=w/2;cr=r-.014
    prof=s.get('profile',PROFILE)
    if len(prof)<6 or any(not(-1.15<=x<=1.15 and .58<=rr<=1.015) for x,rr in prof):
        remove_collection(c);raise ValueError('Profile exceeds supported tyre section envelope')
    revolve('Tyre | shaped carcass',[(x*h,rr*cr) for x,rr in prof],m['rubber'],c,root,64,True)
    profile_guide(c,root,s)
    # Four staggered rows of low, chamfered chevron blocks; one editable mesh.
    verts=[];faces=[];count=40
    for row,(xa,xb) in enumerate([(-.96,-.54),(-.50,-.05),(.05,.50),(.54,.96)]):
        for i in range(count):
            phase=i*math.tau/count+(row%2)*math.tau/count*.45
            # Slanted outline in the axial/angular plane, with small clipped corners.
            points=[(xa+.055,-.34),(xb-.04,-.34),(xb,-.24),(xb,.27),
                    (xb-.05,.35),(xa+.04,.35),(xa,.25),(xa,-.24)]
            base=len(verts)
            for layer in [0,1]:
                for xx,aa in points:
                    angle=phase+(aa+xx*.19*(1 if row<2 else -1))*math.tau/count
                    rad=cr*(1-.053*(abs(xx)**2))-.002+layer*.015
                    verts.append((xx*h,rad*math.sin(angle),rad*math.cos(angle)))
            faces += [tuple(base+i for i in range(7,-1,-1)),tuple(base+8+i for i in range(8))]
            faces += [(base+j,base+(j+1)%8,base+(j+1)%8+8,base+j+8) for j in range(8)]
    mesh('Tyre | staggered tread blocks',verts,faces,m['tread'],c,root,.0015)
    for rr,xx in [(.266,h*.99),(.236,h*.94)]:
        revolve('Tyre | moulded sidewall rib',[(xx-.001,rr-.002),(xx+.002,rr-.001),
                (xx+.002,rr+.001),(xx-.001,rr+.002)],m['rubber'],c,root,64,True)
    # Rim barrel is open. The dished web has eight real through-holes.
    offset=h-.136
    rp=[(.142,.225),(.155,.220),(.156,.211),(.141,.204),(-.095,.204),
        (-.112,.21),(-.118,.225),(-.128,.225),(-.132,.216),(-.113,.195),(.125,.195),(.144,.205)]
    revolve('Rim | barrel and rolled flange',[(x+offset,rr) for x,rr in rp],m['steel'],c,root,64,True)
    revolve('Rim | bright outer lip',[(.153+offset,.214),(.158+offset,.216),(.158+offset,.219),
            (.152+offset,.222)],m['edge'],c,root,64,True)
    disk=revolve('Rim | dished web with eight openings',[(x+offset,rr) for x,rr in
                 [(.100,.050),(.094,.095),(.120,.17),(.139,.201),(.126,.205),(.106,.173),(.080,.096),(.086,.050)]],m['steel'],c,root,64,True)
    for i in range(8):
        a=i*math.tau/8
        cutter=cylinder('Temporary vent',offset+.11,0,.153,.025,.24,None,c,root,20,1.42)
        for v in cutter.data.vertices:
            yy,zz=v.co.y,v.co.z;v.co.y=yy*math.cos(a)+zz*math.sin(a);v.co.z=-yy*math.sin(a)+zz*math.cos(a)
        bpy.context.view_layer.objects.active=disk
        mod=disk.modifiers.new('Punched vent','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
        bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
    mod=disk.modifiers.new('Rolled vent edges','BEVEL');mod.width=.0025;mod.segments=2
    mod=disk.modifiers.new('Web normals','WEIGHTED_NORMAL');mod.keep_sharp=True
    revolve('Wheel | centre hub',[(offset+.089,.053),(offset+.115,.053),(offset+.135,.045),
            (offset+.135,.004),(offset+.083,.004)],m['hub'],c,root,32)
    for i in range(5):
        a=i*math.tau/5
        cylinder('Wheel | lug seat',offset+.101,.076*math.sin(a),.076*math.cos(a),.013,.008,m['hub'],c,root,16)
        cylinder('Wheel | hex lug',offset+.111,.076*math.sin(a),.076*math.cos(a),.009,.017,m['edge'],c,root,6)
    # Visible behind the holes, without filling the rim face with a flat black disc.
    revolve('Brake | rotor',[(.043,.08),(.043,.175),(.054,.175),(.054,.08)],m['hub'],c,root,48)
    valve=cylinder('Wheel | valve stem',offset+.156,.181,0,.006,.025,m['black'],c,root,8)
    seal(c);return c

def arch_interface(s):
    """Shared faceted aperture and mating skin edge, in wheel-mount space."""
    r=s['radius'];cz=s['center'][2];gap=s['clearance']
    # Polygon chords have room around the tyre; clearance is a design parameter,
    # not a claim that every point is exactly that distance from the wheel.
    top=r+gap+.020;half=r+gap+.013
    inner=[(-half,.43-cz),(-half+.012,.20),(-half+.085,top*.84),
           (-.235,top),(.235,top),(half-.085,top*.84),(half-.012,.20),(half,.43-cz)]
    # Homothetic aperture rings keep each chamfer face planar. Independently
    # offsetting Y and Z twists quads and causes unintended diagonal highlights.
    base=.43-cz
    outer=[(y*1.12,base+(z-base)*1.12) for y,z in inner]
    return inner,outer

def fender(s,name='Fender'):
    validate_spec(s);c,root=root_collection(name,s,'fender');m=palette()
    inner,outer=arch_interface(s);cx=abs(s['center'][0]);cy=s['center'][1];cz=s['center'][2]
    # Fixed neighbour interface is the original study's bonnet/nose/door boundary.
    # Local wheel centres are allowed for isolated workshop modules. Assembly only
    # supports the documented RR front centre and a 6 mm rear reveal.
    front=-2.03-cy;back=-.776-cy
    if outer[0][0]<=front or outer[-1][0]>=back:
        remove_collection(c);raise ValueError('Arch no longer fits the fixed front-panel boundary')
    def bw(y):return .875+(.92-.875)*max(0,min(1,(y+cy+2.03)/.19))
    def sh(y):return 1.135+.025*max(0,min(1,(y+cy+2.03)/1.26))
    lower=[(front,.43-cz)]+outer+[(back,.43-cz)]
    verts=[];faces=[]
    for j,(y,z) in enumerate(lower):
        side=.875 if j==0 else .92
        # Calm planar side face, broad upper shoulder and a separately authored
        # arch chamfer. Avoid sinusoidal width offsets across variable-height quads.
        verts.extend([(side-cx,y,z),(side-cx,y,sh(y)-.108-cz),
                      (side-.009-cx,y,sh(y)-.035-cz),(bw(y)-.035-cx,y,sh(y)-cz)])
    primary=[];corner=-1.84-cy
    for j in range(len(lower)-1):
        for k in range(3):
            if k==0:primary.append(len(faces))
            # The bonnet changes plan taper at -1.84. Include that exact station,
            # even when it falls inside an arch segment, to avoid a hairline slit.
            if k==2 and lower[j][0]<corner<lower[j+1][0]:
                t=(corner-lower[j][0])/(lower[j+1][0]-lower[j][0])
                a=Vector(verts[j*4+2]);b=Vector(verts[(j+1)*4+2])
                n=len(verts);verts.extend([tuple(a.lerp(b,t)),(bw(corner)-.035-cx,corner,sh(corner)-cz)])
                faces.extend([(j*4+2,n,n+1,j*4+3),(n,(j+1)*4+2,(j+1)*4+3,n+1)])
            else:faces.append((j*4+k,(j+1)*4+k,(j+1)*4+k+1,j*4+k+1))
    skin=mesh('Fender | shoulder and lower skin',verts,faces,m['paint'],c,root)
    skin['primary_panels']=primary
    # Shared ring boundaries are used literally by both skin and separate lip.
    outer3=[tuple(verts[(i+1)*4]) for i in range(8)]
    inner3=[(.995-cx,y,z) for y,z in inner]
    lip=mesh('Fender | arch chamfer',outer3+inner3,
             [(i,i+1,i+9,i+8) for i in range(7)],m['paint'],c,root)
    returns=[(.878-cx,y,z) for y,z in inner]
    mesh('Fender | deep inner return',inner3+returns,
         [(i,i+1,i+9,i+8) for i in range(7)],m['black'],c,root)
    # Turned edges give the skin physical thickness at bonnet and door joins.
    edge=[]
    for i in range(len(lower)):
        if i and lower[i-1][0]<corner<lower[i][0]:edge.append((bw(corner)-.035-cx,corner,sh(corner)-cz))
        edge.append(tuple(verts[i*4+3]))
    mesh('Fender | bonnet edge return',edge+[(x,y,z-.023) for x,y,z in edge],
         [(i,i+1,len(edge)+i+1,len(edge)+i) for i in range(len(edge)-1)],m['paint'],c,root)
    edge=[tuple(verts[(len(lower)-1)*4+i]) for i in range(4)]
    mesh('Fender | door edge return',edge+[(x-.020,y,z) for x,y,z in edge],
         [(i,i+1,i+5,i+4) for i in range(3)],m['paint'],c,root)
    # Rear cavity liner sits behind the aperture, following the same definition.
    mesh('Fender | wheelhouse liner',returns+[(.57-cx,y,z) for y,z in inner],
         [(i,i+1,i+9,i+8) for i in range(7)],m['black'],c,root)
    mesh('Fender | wheelhouse back panel',[(.57-cx,y,z) for y,z in inner],
         [tuple(range(len(inner)))],m['black'],c,root)
    root['interface_version']='rr-front-v1';root['rear_reveal_m']=.006
    c['aperture']=json.dumps(inner);seal(c);return c

def fingerprint(coll):
    """Protect component meshes, transforms, modifiers, shader values and deletions."""
    data=[]
    for ob in sorted(coll.objects,key=lambda o:o.name):
        if ob.get('profile_guide'):continue  # designated editable input
        entry=[ob.name,ob.type,list(sum((list(row) for row in ob.matrix_basis),[]))]
        if ob.type=='MESH':
            entry += [[list(v.co) for v in ob.data.vertices],[list(p.vertices) for p in ob.data.polygons],
                      [p.material_index for p in ob.data.polygons],[p.use_smooth for p in ob.data.polygons]]
            for mod in ob.modifiers:
                vals={}
                for prop in mod.bl_rna.properties:
                    if prop.identifier in ['rna_type','name']:continue
                    val=getattr(mod,prop.identifier,None)
                    if isinstance(val,(str,int,float,bool)):vals[prop.identifier]=val
                entry.append([mod.type,vals])
            for mat in ob.data.materials:
                nodes=[]
                if mat and mat.use_nodes:
                    for n in mat.node_tree.nodes:
                        inputs=[]
                        for v in n.inputs:
                            if hasattr(v,'default_value'):
                                val=v.default_value
                                try:val=list(val)
                                except TypeError:pass
                                if isinstance(val,(float,int,str,list,bool)):inputs.append([v.name,val])
                        nodes.append([n.name,n.type,inputs])
                    entry.append([mat.name,nodes,[(l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name) for l in mat.node_tree.links]])
        data.append(entry)
    return hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()

def seal(coll):
    bpy.context.view_layer.update();coll['fingerprint']=fingerprint(coll)
    coll['manifest']=json.dumps(sorted(o.name for o in coll.objects))

def remove_collection(coll):
    for ob in list(coll.objects):bpy.data.objects.remove(ob,do_unlink=True)
    bpy.data.collections.remove(coll)

def rebuild(coll,s):
    if coll.get('fingerprint')!=fingerprint(coll):
        raise RuntimeError('This part has manual mesh, transform, material or modifier edits. Save a variant; rebuild refused.')
    old=json.loads(coll['spec']);s=dict(s);s['center']=old['center'];s['side']=old['side']
    for ob in coll.objects:
        if ob.get('profile_guide'):
            pts=ob.data.splines[0].points
            s['profile']=[(p.co.x/(old['width']/2),p.co.z/(old['radius']-.014)) for p in pts]
    validate_spec(s);kind=coll['kind'];name=coll.name
    before=set(bpy.data.collections)
    try:
        staged=(wheel if kind=='wheel' else fender)(s,name+' STAGED')
        check=component_report(staged)
        if not check['finite']:raise RuntimeError('Invalid staged coordinates')
    except Exception:
        for c in set(bpy.data.collections)-before:remove_collection(c)
        raise
    # Old collection and manual neighbours survive any build/validation failure.
    remove_collection(coll);staged.name=name;seal(staged);return staged

def component_report(coll):
    meshes=[o for o in coll.objects if o.type=='MESH']
    return dict(kind=coll['kind'],objects=len(meshes),
                finite=all(math.isfinite(v) for o in meshes for p in o.data.vertices for v in p.co),
                vertices=sum(len(o.data.vertices) for o in meshes),
                faces=sum(len(o.data.polygons) for o in meshes))

def tree(ob):
    dg=bpy.context.evaluated_depsgraph_get();eo=ob.evaluated_get(dg);me=eo.to_mesh();me.calc_loop_triangles()
    tr=BVHTree.FromPolygons([eo.matrix_world@v.co for v in me.vertices],
                           [tuple(t.vertices) for t in me.loop_triangles],all_triangles=True)
    eo.to_mesh_clear();return tr

def fit_report(wc,fc):
    bpy.context.view_layer.update()
    tyres=[o for o in wc.objects if o.type=='MESH' and ('carcass' in o.name or 'tread blocks' in o.name)]
    fixed=[o for o in fc.objects if o.type=='MESH']
    contacts=[];minimum=100
    for a in tyres:
        at=tree(a)
        for b in fixed:
            bt=tree(b)
            if at.overlap(bt):contacts.append([a.name,b.name])
            for v in a.data.vertices:
                hit=bt.find_nearest(a.matrix_world@v.co)
                if hit and hit[0] is not None:minimum=min(minimum,hit[3])
    skin=next(o for o in fixed if 'shoulder and lower' in o.name)
    lip=next(o for o in fixed if 'arch chamfer' in o.name)
    seam=max((skin.matrix_world@skin.data.vertices[(i+1)*4].co-lip.matrix_world@lip.data.vertices[i].co).length for i in range(8))
    return dict(intersections=contacts,skin_to_lip_boundary_error_m=seam,
                sampled_tyre_vertex_to_fender_min_m=minimum,
                scope='Static evaluated tyre/tread surface intersections and shared skin/lip vertices. Nearest distance samples tyre base vertices; not an exact clearance or steering/suspension certification.')

def selected_part(context):
    ob=context.active_object
    if ob:
        for c in ob.users_collection:
            if c.get('gt_owner')==OWNER:return c
    return None

class GTWF_Settings(bpy.types.PropertyGroup):
    radius:bpy.props.FloatProperty(name='Tyre radius',default=.38,min=.36,max=.39,unit='LENGTH')
    width:bpy.props.FloatProperty(name='Tyre width',default=.272,min=.24,max=.29,unit='LENGTH')
    clearance:bpy.props.FloatProperty(name='Arch allowance',default=.064,min=.05,max=.075,unit='LENGTH')

class GTWF_OT_Create(bpy.types.Operator):
    bl_idname='gtwf.create';bl_label='Create workshop corner';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        p=context.scene.gtwf;s=dict(DEFAULT,radius=p.radius,width=p.width,clearance=p.clearance)
        if any(c.get('gt_owner')==OWNER and json.loads(c['spec'])['center']==s['center']
               for c in context.scene.collection.children):
            self.report({'ERROR'},'This mount already has parts. Use a new scene or rebuild the selected part.');return {'CANCELLED'}
        before=set(bpy.data.collections)
        try:
            wc=wheel(s,'Workshop | front wheel');fc=fender(s,'Workshop | front fender')
        except Exception as e:
            for c in set(bpy.data.collections)-before:remove_collection(c)
            self.report({'ERROR'},str(e));return {'CANCELLED'}
        context.scene['gtwf_last_fit']=json.dumps(fit_report(wc,fc));return {'FINISHED'}

class GTWF_OT_Rebuild(bpy.types.Operator):
    bl_idname='gtwf.rebuild';bl_label='Rebuild selected part';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        c=selected_part(context)
        if not c:self.report({'ERROR'},'Select a workshop component');return {'CANCELLED'}
        p=context.scene.gtwf;s=dict(json.loads(c['spec']),radius=p.radius,width=p.width,clearance=p.clearance)
        try:rebuild(c,s)
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
        self.report({'INFO'},'Part rebuilt; run Check Fit after interface changes');return {'FINISHED'}

class GTWF_OT_Guides(bpy.types.Operator):
    bl_idname='gtwf.guides';bl_label='Toggle tyre profile guide';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        c=selected_part(context)
        if not c:return {'CANCELLED'}
        for ob in c.objects:
            if ob.get('profile_guide'):ob.hide_set(not ob.hide_get());ob.show_in_front=True
        return {'FINISHED'}

class GTWF_OT_Check(bpy.types.Operator):
    bl_idname='gtwf.check';bl_label='Check selected corner fit'
    def execute(self,context):
        c=selected_part(context)
        if not c:self.report({'ERROR'},'Select a workshop component');return {'CANCELLED'}
        s=json.loads(c['spec']);candidates=[v for v in bpy.data.collections if v.get('gt_owner')==OWNER and
                json.loads(v['spec'])['center']==s['center'] and json.loads(v['spec'])['side']==s['side']]
        wheels=[v for v in candidates if v['kind']=='wheel'];fenders=[v for v in candidates if v['kind']=='fender']
        if len(wheels)!=1 or len(fenders)!=1:self.report({'ERROR'},'Expected exactly one wheel and fender at this mount');return {'CANCELLED'}
        report=fit_report(wheels[0],fenders[0]);context.scene['gtwf_last_fit']=json.dumps(report)
        text=bpy.data.texts.get('Workshop fit report') or bpy.data.texts.new('Workshop fit report')
        text.clear();text.write(json.dumps(report,indent=2))
        self.report({'WARNING'} if report['intersections'] else {'INFO'},
                    f"{len(report['intersections'])} intersections; report saved in Text Editor")
        return {'FINISHED'}

class GTWF_PT_Panel(bpy.types.Panel):
    bl_label='Wheel and Fender Workshop';bl_idname='GTWF_PT_panel'
    bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='GT Parts'
    def draw(self,context):
        l=self.layout;p=context.scene.gtwf
        l.label(text='RR front interface v1 | metres')
        for key in ['radius','width','clearance']:l.prop(p,key)
        l.operator('gtwf.create');l.operator('gtwf.guides');l.operator('gtwf.rebuild');l.operator('gtwf.check')
        l.label(text='Manual mesh edits block rebuilding.')

CLASSES=[GTWF_Settings,GTWF_OT_Create,GTWF_OT_Rebuild,GTWF_OT_Guides,GTWF_OT_Check,GTWF_PT_Panel]
def register():
    for cls in CLASSES:bpy.utils.register_class(cls)
    bpy.types.Scene.gtwf=bpy.props.PointerProperty(type=GTWF_Settings)
def unregister():
    if hasattr(bpy.types.Scene,'gtwf'):del bpy.types.Scene.gtwf
    for cls in reversed(CLASSES):bpy.utils.unregister_class(cls)
if __name__=='__main__':register()
