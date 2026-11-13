"""Build a fresh editable primary-form study from an explicit per-car shape spec.

No old vehicle generator is imported. Side-profile observations supply longitudinal
shape; widths and hidden geometry are provisional. Rebuilds require a new folder.
"""
import bpy, bmesh, json, math, sys, argparse, shutil, hashlib
from pathlib import Path
from mathutils import Vector

p=argparse.ArgumentParser()
p.add_argument('--spec',required=True);p.add_argument('--output',required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
specpath=Path(a.spec);src=specpath.parent;out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
if any(out.glob('*.blend')):raise RuntimeError('Existing editable study; choose a new output folder.')
S=json.loads(specpath.read_text());R=S['registration'];P=R['pixels_per_metre']
source_vehicle=Path('C:/GrandTour/Art/Export/VehicleTools/crafted-utility-v05/Crafted_Utility.blend')
original_hash=hashlib.sha256(source_vehicle.read_bytes()).hexdigest()
bpy.ops.wm.read_factory_settings(use_empty=True);sc=bpy.context.scene
sc.unit_settings.system='METRIC';sc['status']='Bare-body character study; shape provisional, not approved. Original A is primary.'

def collection(name):
    c=bpy.data.collections.new(name);sc.collection.children.link(c);return c
body=collection('01 | Primary surfaces');cabin=collection('02 | Cabin and openings')
bumpers=collection('03 | Bumper profiles');wheels=collection('04 | Wheel proxies')
guides=collection('05 | Section evidence');studio=collection('06 | Review studio');cams=collection('07 | Fixed cameras')
guides.hide_render=True;guides.hide_viewport=True

def material(name,color,roughness=.62):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=roughness
    return m
clay=material('Body | neutral warm clay',(.37,.40,.37));dark=material('Openings | charcoal',(.043,.058,.060),.42)
rubber=material('Proxy tyres',(.038,.041,.040));metal=material('Proxy wheel centres',(.22,.23,.21))
trim=material('Bumper and pillars',(.12,.145,.14));groundmat=material('Studio',(.28,.30,.31),.8)
gold=material('Observed sections',(.88,.39,.025))

def lerp(x,rows):
    rows=sorted(rows)
    if x<=rows[0][0]:return rows[0][1]
    for (a,va),(b,vb) in zip(rows,rows[1:]):
        if x<=b:return va+(vb-va)*(x-a)/(b-a)
    return rows[-1][1]
def Y(u):return R['axle_front_world']+(u-R['front_hub_px'][0])/P
def Z(v):return R['axle_z']+(R['front_hub_px'][1]-v)/P
def U(y):return R['front_hub_px'][0]+(y-R['axle_front_world'])*P
def V(z):return R['front_hub_px'][1]-(z-R['axle_z'])*P
def width(u,v):return lerp(v,S['side_section_v_width'])*lerp(u,S['longitudinal_width'])
def rear_u(v):return lerp(v,[(v,u) for u,v in S['rear_profile_uv']])
def front_u(v):return lerp(v,[(v,u) for u,v in S['front_profile_uv']])
def arch(u):
    for name in ['front_arch_uv','rear_arch_uv']:
        pts=S[name]
        if pts[0][0]<=u<=pts[-1][0]:return lerp(u,pts)
    return 278
def pos(side,u,v):return (side*width(u,v),Y(u),Z(v))
def cabwidth(v):return lerp(v,[(S['cabin_top_v'],S['cabin_half_width_top']),(S['cabin_bottom_v'],S['cabin_half_width_bottom'])])
def cabpos(side,u,v):return (side*cabwidth(v),Y(u),Z(v))

def mesh(name,verts,faces,mat,col,solid=0):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    ob=bpy.data.objects.new(name,me);col.objects.link(ob);me.materials.append(mat)
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    if solid:
        mod=ob.modifiers.new('Thin inward return','SOLIDIFY');mod.thickness=solid;mod.offset=-1
    ob['study_part']=True;return ob

def shape_control(ob,name,alternative):
    # Full intended form at value 1. Moving toward zero exposes a flattening error.
    desired=[v.co.copy() for v in ob.data.vertices]
    if ob.data.shape_keys is None:ob.shape_key_add(name='Basis')
    basis=ob.data.shape_keys.key_blocks[0]
    key=ob.shape_key_add(name=name)
    for i,co in enumerate(desired):
        alt=Vector(alternative(co.copy()))
        basis.data[i].co=alt
        key.data[i].co=co
    key.value=1;key.slider_min=0;key.slider_max=1.5
    ob['control_note']='1 = proposed form; 0 = deliberately flattened comparison. Not measured dimensions.'
    return key

def clip(poly,fn):
    result=[]
    for q,r in zip(poly,poly[1:]+poly[:1]):
        dq=fn(*q);dr=fn(*r)
        if dq>=-1e-8:result.append(q)
        if (dq>=0)!=(dr>=0):
            t=dq/(dq-dr);result.append((q[0]+(r[0]-q[0])*t,q[1]+(r[1]-q[1])*t))
    clean=[]
    for q in result:
        if not clean or math.dist(q,clean[-1])>1e-7:clean.append(q)
    if len(clean)>2 and math.dist(clean[0],clean[-1])<1e-7:clean.pop()
    return clean

# Dense only where a contour or a section changes direction. All side faces are
# samples of one section function; no boxes are used as body panels.
us=sorted(set([32,819,280,475,634,735,765,783,800,809,813]+[u for key in ['side_top_uv','front_arch_uv','rear_arch_uv','longitudinal_width'] for u,v in S[key]]))
vs=sorted(set([136,139,151,167,170,180,200,221,223,229,235,245,247,253,263,273,278]+[v for u,v in S['rear_profile_uv']]))
verts=[];faces=[]
for side in [-1,1]:
    for ua,ub in zip(us,us[1:]):
        for va,vb in zip(vs,vs[1:]):
            poly=[(ua,va),(ub,va),(ub,vb),(ua,vb)]
            for fn in [lambda u,v:v-lerp(u,S['side_top_uv']),lambda u,v:arch(u)-v,lambda u,v:u-front_u(v),lambda u,v:rear_u(v)-u]:
                poly=clip(poly,fn)
                if len(poly)<3:break
            if len(poly)<3:continue
            j=len(verts);verts.extend(pos(side,u,v) for u,v in poly);faces.append(tuple(range(j,len(verts))))
# End surfaces share the same outer section samples, so rear tuck is in both side
# outline and actual tailgate volume. Main body remains an editable surface cage.
for isrear in [False,True]:
    rows=[v for v in vs if v>=(136 if isrear else 170)]
    for va,vb in zip(rows,rows[1:]):
        uu=rear_u if isrear else front_u
        j=len(verts)
        verts.extend([pos(-1,uu(va),va),pos(1,uu(va),va),pos(1,uu(vb),vb),pos(-1,uu(vb),vb)])
        faces.append((j,j+1,j+2,j+3))
master=mesh('Body | shared shoulder, side tuck and rear return',verts,faces,clay,body,.012)

# Multiple independent shape keys use the unchanged Basis plus deltas; this avoids
# one control cancelling another at a shared corner.
master.shape_key_add(name='Basis')
body_deltas=[
    ('Rear lower tuck',lambda co:Vector((0,(Y(819)-co.y)*max(0,min(1,(U(co.y)-735)/35)),0)) if V(co.z)>167 else Vector()),
    ('Lower side tuck',lambda co:Vector((math.copysign(max(0,.921-abs(co.x)),co.x)*max(0,min(1,(V(co.z)-235)/43)),0,0)))]
proposed=[v.co.copy() for v in master.data.vertices]
flat=[co+sum((delta(co) for name,delta in body_deltas),Vector()) for co in proposed]
for point,co in zip(master.data.shape_keys.key_blocks[0].data,flat):point.co=co
for name,delta in body_deltas:
    key=master.shape_key_add(name=name)
    for dst,co,b in zip(key.data,proposed,flat):dst.co=b-delta(co)
    key.value=1;key.slider_min=0;key.slider_max=1.5
master['control_note']='1 = proposed shape; 0 = remove the named feature. The scene FORM CONTROLS drives coordinated part keys.'

def surface(name,stations,section,halfwidth,mat,col,mode):
    fs=[-f for f,d in reversed(section[1:])]+[f for f,d in section]
    vv=[]
    for u,v in stations:
        for f in fs:
            if mode=='hood':drop=(Z(v)-Z(lerp(u,S['side_top_uv'])))*lerp(abs(f),section)/section[-1][1]
            else:drop=lerp(abs(f),section)
            vv.append((halfwidth(u,v)*f,Y(u),Z(v)-drop))
    n=len(fs);ff=[(j*n+i,j*n+i+1,(j+1)*n+i+1,(j+1)*n+i) for j in range(len(stations)-1) for i in range(n-1)]
    if mode=='roof':
        # Folded perimeter returns down to the shared gutter and cabin top.
        for i in [0,n-1]:
            rim=[]
            for j,(u,v) in enumerate(stations):
                idx=len(vv);vv.append((vv[j*n+i][0],Y(u),Z(lerp(u,S['roof_gutter_uv']))));rim.append(idx)
            ff.extend((j*n+i,(j+1)*n+i,rim[j+1],rim[j]) for j in range(len(stations)-1))
        for j in [0,len(stations)-1]:
            u,v=stations[j];lower=[]
            for i in range(n):
                lower.append(len(vv));vv.append((vv[j*n+i][0],Y(u),Z(lerp(u,S['roof_gutter_uv']))))
            ff.extend((j*n+i,j*n+i+1,lower[i+1],lower[i]) for i in range(n-1))
    return mesh(name,vv,ff,mat,col,.010)

# Bonnet shoulder relief decreases at its rolled leading tip; control moves the
# transverse relief, while the longitudinal crown follows observed points.
hood=surface('Bonnet | crown and folded shoulders',S['bonnet_crown_uv'],S['bonnet_section'],lambda u,v:width(u,lerp(u,S['side_top_uv'])),clay,body,'hood')
shape_control(hood,'Bonnet shoulder relief',lambda co:(co.x,co.y,Z(lerp(U(co.y),S['side_top_uv']))))
roof=surface('Roof | shallow compound crown',S['roof_crown_uv'],S['roof_section'],lambda u,v:S['roof_half_width'],clay,body,'roof')
shape_control(roof,'Roof crown',lambda co:(co.x,co.y,min(co.z,Z(lerp(U(co.y),S['roof_gutter_uv']))+.018)))

def poly_ring(name,outer,inner,mat,col):
    n=len(outer);return mesh(name,outer+inner,[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],mat,col,.012)
outers=[[(280,136),(475,136),(477,38),(348,38)],[(475,136),(634,136),(615,38),(477,38)],[(634,136),(809,136),(755,38),(615,38)]]
names=['front_window','rear_window','cargo_window']
for side in [-1,1]:
    for outer,name in zip(outers,names):
        inner=S['window_profiles_uv'][name][:4]
        frame=poly_ring(('Left' if side>0 else 'Right')+' | '+name+' frame',[cabpos(side,*p) for p in outer],[cabpos(side,*p) for p in inner],trim,cabin)
        pane=[(x-side*.010,y,z) for x,y,z in [cabpos(side,*p) for p in inner]]
        mesh(('Left' if side>0 else 'Right')+' | '+name+' opening',pane,[(0,1,2,3)],dark,cabin,.004)

for rear in [False,True]:
    ub=S['cabin_rear_bottom_u'] if rear else S['cabin_front_bottom_u'];ut=S['cabin_rear_top_u'] if rear else S['cabin_front_top_u']
    outer=[cabpos(-1,ub,136),cabpos(1,ub,136),cabpos(1,ut,40),cabpos(-1,ut,40)]
    centre=sum((Vector(v) for v in outer),Vector())/4
    inner=[tuple(centre+(Vector(v)-centre)*.91) for v in outer]
    poly_ring(('Rear screen' if rear else 'Windscreen')+' | structural surround',outer,inner,trim,cabin)
    # Geometric recess; move into cabin along Y, not merely darker paint.
    pane=[(x,y+(-.008 if rear else .008),z) for x,y,z in inner]
    mesh(('Rear screen' if rear else 'Windscreen')+' | opening',pane,[(0,1,2,3)],dark,cabin,.004)

for ob in list(cabin.objects):
    shape_control(ob,'Cabin inward taper',lambda co:(math.copysign(S['cabin_half_width_bottom']*abs(co.x)/cabwidth(V(co.z)),co.x),co.y,co.z))

# Narrow gutter-to-frame returns close the visible perimeter without thickening
# the main roof or hiding a gap behind overlapping boxes.
for side in [-1,1]:
    vv=[]
    for u in [350,380,434,500,610,697,738,754]:
        vv.extend([(side*S['roof_half_width'],Y(u),Z(lerp(u,S['roof_gutter_uv']))),(side*S['cabin_half_width_top'],Y(u),Z(38))])
    mesh('Roof gutter | side return '+str(side),vv,[(i,i+2,i+3,i+1) for i in range(0,len(vv)-2,2)],trim,body,.004)
for roofu,cabu in [(347,350),(754,755)]:
    mesh('Roof gutter | end return '+str(roofu),[(-S['roof_half_width'],Y(roofu),Z(lerp(roofu,S['roof_gutter_uv']))),(S['roof_half_width'],Y(roofu),Z(lerp(roofu,S['roof_gutter_uv']))),(S['cabin_half_width_top'],Y(cabu),Z(40)),(-S['cabin_half_width_top'],Y(cabu),Z(40))],[(0,1,2,3)],trim,body,.004)

# Fill the modest ledge between the body shoulder and cabin base, and scuttle
# between the bonnet and windscreen. These share the endpoint geometry.
for side in [-1,1]:
    pts=[]
    for u in [280,475,634,809]:pts.extend([pos(side,u,lerp(u,S['side_top_uv'])),cabpos(side,u,136)])
    mesh('Belt ledge '+str(side),pts,[(i,i+2,i+3,i+1) for i in range(0,6,2)],clay,body,.007)
back=[v.co.copy() for v in hood.data.shape_keys.key_blocks['Bonnet shoulder relief'].data if abs(v.co.y-Y(275))<.0001]
back.sort(key=lambda co:co.x);vv=[];maxx=max(abs(v.x) for v in back)
for co in back:vv.extend([tuple(co),(co.x/maxx*S['cabin_half_width_bottom'],Y(280),Z(136))])
mesh('Scuttle | fitted bonnet to screen',vv,[(i,i+2,i+3,i+1) for i in range(0,len(vv)-2,2)],clay,body,.01)

# Slim arch lips follow the asymmetric observed openings rather than assuming
# circles. They are a form cue, not decorative bolt-on expedition flares.
for side in [-1,1]:
    for name in ['front_arch_uv','rear_arch_uv']:
        pts=S[name];v=[]
        for i,(u,pv) in enumerate(pts):
            prev=Vector(pts[max(0,i-1)]);nxt=Vector(pts[min(len(pts)-1,i+1)]);t=(nxt-prev).normalized();n=Vector((t.y,-t.x))
            outer=Vector((u,pv))+n*(S['arch_lip_width']*P)
            x,y,z=pos(side,u,pv);v.append((x+side*.009,y,z))
            x,y,z=pos(side,*outer);v.append((x+side*.004,y,z))
        mesh(str(side)+' | '+name+' narrow lip',v,[(i,i+2,i+3,i+1) for i in range(0,len(v)-2,2)],clay,body,.007)
        # Recessed wheel-well surfaces describe depth and prevent seeing through
        # the opposite opening; they carry no suspension or accessory detail.
        vv=[]
        for u,pv in pts:vv.extend([(side*.88,Y(u),Z(pv)),(side*.61,Y(u),Z(pv))])
        mesh(str(side)+' | '+name+' inner well',vv,[(i,i+2,i+3,i+1) for i in range(0,len(vv)-2,2)],rubber,body,.006)
        back=[(side*.61,Y(u),Z(pv)) for u,pv in pts]
        mesh(str(side)+' | '+name+' recessed backing',back,[tuple(range(len(back)))],rubber,body,.006)

def bumper(name,profile,rear):
    # Shared end profile extruded across width, with separate plan-view chamfers.
    vv=[];levels=[(-.947,.047),(-.885,0),(.885,0),(.947,.047)]
    for x,inset in levels:
        for u,v in profile:vv.append((x,Y(u)+(-inset if rear else inset),Z(v)))
    n=len(profile);faces=[tuple(reversed(range(n))),tuple(range(3*n,4*n))]
    faces += [(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(3) for i in range(n)]
    ob=mesh(name,vv,faces,trim,bumpers)
    if rear:shape_control(ob,'Bumper underside return',lambda co:(co.x,max(co.y,Y(827)-(.047 if abs(co.x)>.93 else 0)) if V(co.z)>230 else co.y,co.z))
    return ob
bumper('Rear bumper | projecting ledge and inward lower return',S['rear_bumper_uv'],True)
bumper('Front bumper | thin chamfered carrier',S['front_bumper_uv'],False)

def tyre(side,cy):
    n=48;cx=side*S['wheel_half_track'];radius=S['tyre_radius'];w=S['wheel_width']/2
    profile=[(-w,.70),(-w,.89),(-w*.70,1),(-w*.35,1.007),(w*.35,1.007),(w*.70,1),(w,.89),(w,.70)]
    vv=[(cx+xx,cy+radius*k*math.cos(i*math.tau/n),R['axle_z']+radius*k*math.sin(i*math.tau/n)) for xx,k in profile for i in range(n)]
    ff=[(j*n+i,j*n+(i+1)%n,((j+1)%len(profile))*n+(i+1)%n,((j+1)%len(profile))*n+i) for j in range(len(profile)) for i in range(n)]
    ob=mesh('Wheel | smooth tyre proxy',vv,ff,rubber,wheels)
    for face in ob.data.polygons:face.use_smooth=True
    bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=radius*.69,depth=.03,location=(cx+side*w*.94,cy,R['axle_z']),rotation=(0,math.pi/2,0))
    ob=bpy.context.object;ob.name='Wheel | plain centre proxy'
    for c in list(ob.users_collection):c.objects.unlink(ob)
    wheels.objects.link(ob);ob.data.materials.append(metal);ob['study_part']=True
for side in [-1,1]:
    for cy in [R['axle_front_world'],R['axle_rear_world']]:tyre(side,cy)

def curve(name,points,col,mat=gold):
    data=bpy.data.curves.new(name,'CURVE');data.dimensions='3D';data.bevel_depth=.003
    sp=data.splines.new('POLY');sp.points.add(len(points)-1)
    for dst,co in zip(sp.points,points):dst.co=(*co,1)
    ob=bpy.data.objects.new(name,data);col.objects.link(ob);data.materials.append(mat);return ob
for u in [45,142,280,475,638,765,809]:
    vmin=lerp(u,S['side_top_uv']);vmax=arch(u)
    points=[pos(side,u,v) for side in [-1,1] for v in ([vmax]+[q for q in reversed(vs) if vmin<q<vmax]+[vmin] if side<0 else [vmin]+[q for q in vs if vmin<q<vmax]+[vmax])]
    curve('SECTION | u '+str(u),points,guides)
for feature in ['rear_profile_uv','bonnet_crown_uv','roof_crown_uv']:
    curve('OBSERVATION | '+feature,[(1.10,Y(u),Z(v)) for u,v in S[feature]],guides)

# Studio and fixed, named review cameras. Side reuses the unchanged registration;
# other views expose volume but are not claimed to be calibrated overlays.
mesh('Ground',[(-200,-200,-.003),(200,-200,-.003),(200,200,-.003),(-200,200,-.003)],[(0,1,2,3)],groundmat,studio)
world=bpy.data.worlds.new('Soft neutral world');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.45,.49,.53,1);world.node_tree.nodes['Background'].inputs[1].default_value=.5;sc.world=world
for name,loc,energy,size in [('Broad key',(4,-3,6),1100,4),('Fill',(-3,-2,3),650,3),('Surface strip',(1,4,5),950,2)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=energy;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);studio.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,.1,1))-o.location).to_track_quat('-Z','Y').to_euler()
def camera(name,loc,target,scale,w,h,perspective=False):
    d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);cams.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();d.type='PERSP' if perspective else 'ORTHO';d.ortho_scale=scale;d.lens=65
    o['resolution']=[w,h];o.lock_location=(True,)*3;o.lock_rotation=(True,)*3;return o
cy=Y(420);cz=Z(200)
views={
 'side':camera('Side | fixed reference registration',(8,cy,cz),(0,cy,cz),840/P,1260,600),
 'quarter':camera('Front quarter | volume review',(5.6,-8.2,3.15),(0,.17,.92),5.4,1200,900,True),
 'rear-quarter':camera('Rear quarter | return review',(5.8,8.4,3.0),(0,.17,.93),5.4,1200,900,True),
 'front':camera('Front | section review',(0,-8,1),(0,0,1),2.65,900,900),
 'rear':camera('Rear | section review',(0,8,1),(0,0,1),2.65,900,900),
 'top':camera('Top | width review',(0,.25,8),(0,.25,0),4.85,900,1100),
 'rear-detail':camera('Rear detail | fixed profile',(8,Y(742),Z(192)),(0,Y(742),Z(192)),1.45,850,850)}
cam=views['side'];cam.data.show_background_images=True;bg=cam.data.background_images.new();bg.image=bpy.data.images.load(str(src/'side-reference.png'));bg.image.pack();bg.alpha=.45;bg.display_depth='FRONT';bg.frame_method='STRETCH'
for name in ['source-board.png','original-a-reference.png','front-reference.png']:
    im=bpy.data.images.load(str(src/name));im.use_fake_user=True;im.pack()
for name in ['shape-map.json','shape-spec.json']:
    text=bpy.data.texts.new(name);text.write((src/name).read_text())
txt=bpy.data.texts.new('START HERE | Character study')
txt.write('This is a fresh bare-body study, not an accepted model.\nThe original A board is primary; generated side/front geometry is provisional.\nAll surfaces are editable meshes. Read shape-map.json for evidence and uncertainty.\nSelect FORM CONTROLS and use Object custom properties: 1 is proposed, 0 removes the feature for comparison.\nCoordinated drivers expose rear tuck, bumper underside, bonnet shoulders, roof crown, cabin taper and lower side tuck.\nControls are comparison probes, not a finished constrained car editor; inspect dependent interfaces before keeping an adjustment.\n05 | Section evidence is hidden in viewport/render; enable to inspect construction sections.\nSide camera retains the previous wheel-anchor registration. Other cameras are volume reviews, not calibrated source matches.\nSave manual edits to a new revision. Builder refuses an existing blend.\nNo panel seams, accessories, interior, rig or game export have been added.\n')
sc.render.engine='CYCLES';sc.cycles.samples=20;sc.cycles.use_denoising=True;sc.render.threads_mode='FIXED';sc.render.threads=12
sc.view_settings.view_transform='AgX';sc.render.image_settings.file_format='PNG';sc.render.resolution_percentage=100

def selectview(key):
    cam=views[key];sc.camera=cam;sc.render.resolution_x,sc.render.resolution_y=cam['resolution'];bpy.context.view_layer.update()
def render(key):
    selectview(key);sc.render.filepath=str(out/(key+'.png'));bpy.ops.render.render(write_still=True)

# Actual evaluated-geometry sensitivity audit, not a check of configuration text.
checks={}
def evaluated_positions(ob):
    dg=bpy.context.evaluated_depsgraph_get();eo=ob.evaluated_get(dg);me=eo.to_mesh();coords=[v.co.copy() for v in me.vertices];eo.to_mesh_clear();return coords
for ob in [master,hood,roof]+[o for o in bumpers.objects if o.data.shape_keys]+[next(iter(cabin.objects))]:
    for key in list(ob.data.shape_keys.key_blocks)[1:]:
        old=key.value;bpy.context.view_layer.update();base=evaluated_positions(ob);key.value=1 if old==0 else 0;bpy.context.view_layer.update();changed=evaluated_positions(ob)
        delta=max((x-y).length for x,y in zip(base,changed));key.value=old;bpy.context.view_layer.update()
        checks[ob.name+' / '+key.name]={'max_vertex_displacement_m':delta,'restored_value':old};assert delta>.002
checks['source_vehicle_unchanged']=hashlib.sha256(source_vehicle.read_bytes()).hexdigest()==original_hash
assert checks['source_vehicle_unchanged']
checks['scope']='Control sensitivity only. Not visual approval, manifold/export certification or complete shape fit.'
(out/'control-checks.json').write_text(json.dumps(checks,indent=2))

controls=bpy.data.objects.new('FORM CONTROLS | 1 proposed - 0 flattened',None);sc.collection.objects.link(controls)
controlnames={'Rear lower tuck':'rear_tuck','Lower side tuck':'side_tuck','Bumper underside return':'bumper_return','Bonnet shoulder relief':'bonnet_shoulders','Roof crown':'roof_crown','Cabin inward taper':'cabin_taper'}
for prop in controlnames.values():
    controls[prop]=1.0;controls.id_properties_ui(prop).update(min=0,max=1.5,soft_min=0,soft_max=1,description='1 proposed form, 0 flattened comparison. Check neighbouring surfaces after editing.')
for ob in list(sc.objects):
    if ob.type!='MESH' or ob.data.shape_keys is None:continue
    for key in list(ob.data.shape_keys.key_blocks)[1:]:
        driver=key.driver_add('value').driver;driver.type='AVERAGE';v=driver.variables.new();v.name='form';v.type='SINGLE_PROP';v.targets[0].id=controls;v.targets[0].data_path='["'+controlnames[key.name]+'"]'
bpy.context.view_layer.update()

for key in views:render(key)
# Native side silhouette for transparent diagnostic overlay, same camera, no
# background or studio. All body outline comparisons use this actual geometry.
selectview('side');studio.hide_render=True;sc.render.film_transparent=True
em=bpy.data.materials.new('Diagnostic mask');em.use_nodes=True;n=em.node_tree.nodes;n.clear();e=n.new('ShaderNodeEmission');e.inputs[0].default_value=(1,1,1,1);o=n.new('ShaderNodeOutputMaterial');em.node_tree.links.new(e.outputs[0],o.inputs[0]);sc.view_layers[0].material_override=em
sc.cycles.samples=1;sc.render.filepath=str(out/'side-mask.png');bpy.ops.render.render(write_still=True)
studio.hide_render=False;sc.render.film_transparent=False;sc.view_layers[0].material_override=None;sc.cycles.samples=20
selectview('quarter')
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            space=area.spaces.active;space.region_3d.view_perspective='CAMERA';space.shading.color_type='MATERIAL'
shutil.copy2(__file__,out/Path(__file__).name)
if src.resolve()!=out.resolve():
    for name in ['shape-map.json','shape-spec.json','side-reference.png','original-a-reference.png','front-reference.png','source-board.png']:shutil.copy2(src/name,out/name)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Crafted_Utility_Character_Study.blend'))
print('CHARACTER_STUDY_READY '+str(out),flush=True)
