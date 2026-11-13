"""Local bonnet/wing repair and wheel construction on the latest exterior file."""
import bpy,bmesh,math,json,hashlib,sys,argparse,ast,shutil
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output)
if out.exists() and any(out.iterdir()):raise RuntimeError('Preserve existing work; choose an empty output.')
out.mkdir(parents=True,exist_ok=True)
src=Path('C:/GrandTour/Art/Export/VehicleTools/pathfinder-exterior-v04');source=src/'Pathfinder_Exterior.blend';sha=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source));sc=bpy.context.scene
S=json.loads((src/'approved-target-shape-spec.json').read_text());P=S['registration']['pixels_per_metre']
def collection(n):
    c=bpy.data.collections.new(n);sc.collection.children.link(c);return c
hoodcol=collection('13 | Bonnet and fitted wing tops');wheelcol=collection('14 | Detailed wheels and tyres');trimcol=hoodcol
paint=bpy.data.materials['R50 | restrained burgundy'];black=bpy.data.materials['Detail | satin black polymer'];rubber=bpy.data.materials['R50 | rubber'];silver=bpy.data.materials['R50 | subdued alloy'];darkmetal=bpy.data.materials['Detail | radiator metal'];bright=bpy.data.materials['Detail | satin metal trim']
# Reuse only pure construction helpers, never execute the earlier whole-car builder.
helpers=ast.parse((src/'dress_pathfinder_exterior.py').read_text())
names={'interp','mesh','curve','box','rr','prism','cut'}
exec(compile(ast.Module(body=[n for n in helpers.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'<shared fitted geometry helpers>','exec'))
def Y(u):return -1.35+(u-208)/P
def U(y):return 208+(y+1.35)*P
def Z(v):return .369+(891-v)/P
def V(z):return 891-(z-.369)*P
def width(y,z):return interp(z,S['body_section_z_width'])*interp(U(y),S['longitudinal_width'])
def top(y):return Z(interp(U(y),S['side_top_uv']))
def cap_y(x,z):
    yy=Y(interp(V(z),[(v,u) for u,v in S['front_profile_uv']]))
    dep=S['front_wrap_depth']*max(0,min(1,(1.1-z)/.22));yy+=dep;f=min(1,abs(x)/width(yy,z));return yy-dep*(1-f**5)
def geometry_hash(o):
    h=hashlib.sha256()
    for v in o.data.vertices:h.update(str(tuple(v.co)).encode())
    for f in o.data.polygons:h.update(str(tuple(f.vertices)).encode())
    h.update(str(tuple(tuple(r) for r in o.matrix_world)).encode());return h.hexdigest()
protected={o.name:geometry_hash(o) for o in sc.objects if o.type=='MESH' and not ('Bonnet | rolled nose' in o.name or o.name=='Front | wraparound fascia' or o.name in bpy.data.collections['04 | Wheel form proxies'].objects)}
oldhood=bpy.data.objects['Bonnet | rolled nose and broad shoulders'];oldv=[v.co.copy() for v in oldhood.data.vertices];leading=sorted(oldv[:11],key=lambda v:v.x);trailing=sorted(oldv[-11:],key=lambda v:v.x);half=max(v.x for v in leading);end_y=trailing[0].y
def ease(t):t=max(0,min(1,t));return t*t*(3-2*t)
def pchip(x,rows):
    # Monotone Hermite interpolation: controlled curvature without overshoot.
    rows=sorted(rows);xs=[p[0] for p in rows];ys=[p[1] for p in rows];n=len(xs)
    if x<=xs[0]:return ys[0]
    if x>=xs[-1]:return ys[-1]
    hs=[xs[i+1]-xs[i] for i in range(n-1)];ds=[(ys[i+1]-ys[i])/hs[i] for i in range(n-1)];ms=[ds[0]]
    for i in range(1,n-1):
        if ds[i-1]*ds[i]<=0:ms.append(0)
        else:
            w1=2*hs[i]+hs[i-1];w2=hs[i]+2*hs[i-1];ms.append((w1+w2)/(w1/ds[i-1]+w2/ds[i]))
    ms.append(ds[-1]);i=next(i for i in range(n-1) if xs[i]<=x<=xs[i+1]);t=(x-xs[i])/hs[i]
    return (2*t**3-3*t*t+1)*ys[i]+(t**3-2*t*t+t)*hs[i]*ms[i]+(-2*t**3+3*t*t)*ys[i+1]+(t**3-t*t)*hs[i]*ms[i+1]
def lead(f):
    xx=f*half;yy=interp(xx,[(v.x,v.y) for v in leading]);zz=interp(xx,[(v.x,v.z) for v in leading]);q=ease((abs(f)-.82)/.18)
    zz=zz*(1-q)+top(yy)*q;xx=xx*(1-q)+f*width(yy,top(yy))*q
    return Vector((xx,yy,zz))
cross=[(0,0),(.45,.02),(.60,.035),(.65,.075),(.705,.25),(.77,.43),(.84,.57),(.92,.77),(1,1)]
crown_rows=[(Y(u),Z(v)) for u,v in S['bonnet_crown_uv']]
def surface(f,t):
    l=lead(f);yy=l.y+(end_y-l.y)*t;zz=top(yy);cc=pchip(yy,crown_rows);z=cc+(zz-cc)*pchip(abs(f),cross);x=f*width(yy,zz)
    nose=1-ease(t/.13);z=z*(1-nose)+l.z*nose;x=x*(1-nose)+l.x*nose
    rear=ease((t-.87)/.13);rearx=f*max(v.x for v in trailing);rearz=interp(rearx,[(v.x,v.z) for v in trailing]);z=z*(1-rear)+rearz*rear;x=x*(1-rear)+rearx*rear
    if abs(f)>.999999:z=top(yy);x=f*width(yy,z)
    return Vector((x,yy,z))
ts=sorted(set([j/64 for j in range(65)]+[(Y(u)-lead(1).y)/(end_y-lead(1).y) for u,v in S['side_top_uv'] if lead(1).y<Y(u)<end_y]+[(Y(u)-lead(1).y)/(end_y-lead(1).y) for u,v in S['bonnet_crown_uv'] if lead(1).y<Y(u)<end_y]))
bpy.data.objects.remove(oldhood,do_unlink=True)
def panel(n,fsamples,side_seam=False):
    vs=[];faces=[]
    for t in ts:
        for f in fsamples:
            v=surface(f,t)
            if abs(abs(f)-.82)<1e-6:
                # 3 mm real panel reveal, with a returned dark channel below it.
                v.x+=(1 if f>0 else -1)*(.0015 if side_seam else -.0015)
            vs.append(tuple(v))
    N=len(fsamples)
    for j in range(len(ts)-1):
        for i in range(N-1):a=j*N+i;faces.append((a,a+1,a+1+N,a+N))
    o=mesh(n,vs,faces,paint,hoodcol,.004,True)
    bm=bmesh.new();bm.from_mesh(o.data)
    if sum(f.normal.z for f in bm.faces)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
    bm.to_mesh(o.data);bm.free()
    if side_seam:
        for mod in o.modifiers:
            if mod.type=='SOLIDIFY':mod.use_rim=False
        normals=[]
        for j,t in enumerate(ts):
            for f in fsamples:
                lo=max(-1,f-.0001);hi=min(1,f+.0001)
                tangent=surface(hi,t)-surface(lo,t)
                along=surface(f,min(1,t+.0001))-surface(f,max(0,t-.0001))
                normal=tangent.cross(along).normalized()
                v=surface(f,t);eps=.0001;side=1 if f>0 else -1
                dy=(width(v.y+eps,v.z)-width(v.y-eps,v.z))/(2*eps)
                dz=(width(v.y,v.z+eps)-width(v.y,v.z-eps))/(2*eps)
                side_normal=Vector((side,-dy,-dz)).normalized()
                normal=normal.lerp(side_normal,ease((abs(f)-.94)/.06)).normalized()
                normals.append(tuple(normal))
        o.data.normals_split_custom_set_from_vertices(normals)
    return o
fbase=sorted(set([j*.82/24 for j in range(25)]+[.45,.60,.65,.675,.705,.735,.77,.80,.82]));fhood=sorted(set(fbase+[-f for f in fbase]))
hood=panel('Bonnet | defined crown and shoulder folds',fhood)
for side in [-1,1]:
    panel(('Left' if side>0 else 'Right')+' | fitted front wing top',sorted([side*f for f in [.82,.84,.87,.90,.92,.94,.96,.98,1]]),True)
    vs=[];faces=[]
    for t in ts:
        p=surface(side*.82,t);vs.extend([(p.x-side*.003,p.y,p.z-.003),(p.x+side*.003,p.y,p.z-.003)])
    for j in range(len(ts)-1):k=2*j;faces.append((k,k+2,k+3,k+1))
    mesh('Bonnet | returned seam channel '+str(side),vs,faces,black,hoodcol,.003)

# Boolean-cut side panels have uneven triangles at their upper boundary. Use
# the actual section derivative for side-surface normals, preserving vertices.
for ob in [o for o in sc.objects if o.type=='MESH' and 'shared body skin' in o.name]:
    for mod in ob.modifiers:
        if mod.type=='SOLIDIFY':mod.use_rim=False
    side=1 if sum(v.co.x for v in ob.data.vertices)>0 else -1
    normals=[]
    for v in ob.data.vertices:
        x,y,z=v.co;eps=.0001
        dy=(width(y+eps,z)-width(y-eps,z))/(2*eps)
        dz=(width(y,z+eps)-width(y,z-eps))/(2*eps)
        normals.append(tuple(Vector((side,-dy,-dz)).normalized()))
    ob.data.normals_split_custom_set_from_vertices(normals)

# The front fascia follows the revised leading row; lamp openings remain fixed.
oldcap=bpy.data.objects['Front | wraparound fascia'];bodycol=bpy.data.collections['01 | R50 body sections'];bpy.data.objects.remove(oldcap,do_unlink=True)
ff=sorted(set([j/32 for j in range(-32,33)]+fhood+[-.98,-.94,-.90,-.84,.84,.90,.94,.98]));zrows=sorted(set([Z(v) for u,v in S['front_profile_uv'] if Z(v)<min(lead(f).z for f in ff)-.006]));vs=[];fs=[]
for z in zrows:
    yy=Y(interp(V(z),[(v,u) for u,v in S['front_profile_uv']]))+S['front_wrap_depth']*max(0,min(1,(1.1-z)/.22))
    for f in ff:x=f*width(yy,z);vs.append((x,cap_y(x,z),z))
vs.extend(tuple(surface(f,0)) for f in ff);N=len(ff)
for j in range(len(zrows)):
    for i in range(N-1):k=j*N+i;fs.append((k,k+1,k+1+N,k+N))
cap=mesh('Front | wraparound fascia',vs,fs,paint,bodycol,.018)
if sum(p.normal.y for p in cap.data.polygons)>0:
    bm=bmesh.new();bm.from_mesh(cap.data);bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.to_mesh(cap.data);bm.free()
apertures=[(0,.902,.88,.198,.025),(0,.625,.86,.14,.016)]
for side in [-1,1]:apertures.extend([(side*.621,.889,.347,.174,.025),(side*.759,.889,.065,.170,.012),(side*.640,.601,.23,.186,.028),(side*.685,.599,.105,.13,.013)])
for x,z,w,h,r in apertures:cut(cap,prism('Temporary fascia opening',rr(x,z,w,h,r),1,-2.7,-1.4,hoodcol))
path=[(Y(u),Z(v)) for u,v in S['arches_uv']['Front']];poly=[(path[0][0],-.1)]+path+[(path[-1][0],-.1)]
for side in [-1,1]:lo,hi=sorted([side*.596,side*1.1]);cut(cap,prism('Temporary arch clearance',poly,0,lo,hi,hoodcol))

# New wheels use the accepted centres and a .369 m total tyre envelope.
for o in list(bpy.data.collections['04 | Wheel form proxies'].objects):bpy.data.objects.remove(o,do_unlink=True)
def wheelmesh(n,vs,fs,m,smooth=False,bevel=0):
    o=mesh(n,vs,fs,m,wheelcol,0,smooth)
    if bevel:mod=o.modifiers.new('Manufactured edge radius','BEVEL');mod.width=bevel;mod.segments=2
    return o
def rev(n,profile,cx,cy,side,m,N=72,smooth=True):
    vs=[];fs=[]
    for ax,r in profile:
        for j in range(N):t=j*math.tau/N;vs.append((cx+side*ax,cy+r*math.sin(t),.369+r*math.cos(t)))
    for i in range(len(profile)):
        for j in range(N):a=i*N+j;b=i*N+(j+1)%N;c=((i+1)%len(profile))*N+(j+1)%N;d=((i+1)%len(profile))*N+j;fs.append((a,b,c,d))
    return wheelmesh(n,vs,fs,m,smooth)
profile=[(-.091,.210),(-.110,.220),(-.121,.247),(-.1275,.291),(-.125,.319),(-.111,.342),(-.090,.353),(-.055,.359),(0,.361),(.055,.359),(.090,.353),(.111,.342),(.125,.319),(.1275,.291),(.121,.247),(.110,.220),(.091,.210)]
wheel_specs=[]
for side in [-1,1]:
    for label,cy,track in [('Front',-1.35,1.54),('Rear',1.35,1.545)]:
        cx=side*track/2;root=label+' '+str(side)+' | '
        tyre=rev(root+'tyre envelope',profile,cx,cy,side,rubber);tyre['centre']=[cx,cy,.369];tyre['expected_radius']=.361;tyre['total_radius_with_tread']=.369
        rev(root+'rim barrel',[(-.094,.205),(-.094,.223),(-.084,.226),(.094,.226),(.106,.223),(.108,.215),(.101,.204),(.091,.200),(-.078,.200)],cx,cy,side,silver)
        # Circumferential blocks follow the carcass crown, staggered across lanes.
        tv=[];tf=[]
        for lane,ax in enumerate([-.079,-.026,.026,.079]):
            for j in range(64):
                theta=(j+.5*(lane%2))*math.tau/64;aw=.022 if abs(ax)<.05 else .024;dt=.035
                start=len(tv)
                for depth in [-.0015,.008]:
                    for aa,tt in [(-aw,-dt),(aw,-dt+.008), (aw,dt),(-aw,dt-.008)]:
                        r=interp(abs(ax+aa),[(0,.361),(.055,.359),(.09,.353),(.111,.342),(.125,.319),(.1275,.291)])+depth
                        ang=theta+tt;tv.append((cx+side*(ax+aa),cy+r*math.sin(ang),.369+r*math.cos(ang)))
                tf.extend([tuple(start+k for k in face) for face in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]])
        tread=wheelmesh(root+'tread blocks',tv,tf,rubber,False,.0007);tread['wheel_root']=root
        for rad,ax in [(.244,.120),(.321,.124)]:rev(root+'sidewall moulding '+str(rad),[(ax-.0005,rad-.001),(ax+.0005,rad-.001),(ax+.0008,rad+.001),(ax-.0005,rad+.001)],cx,cy,side,rubber)
        rev(root+'brake rotor',[(-.033,0),(-.033,.171),(-.025,.171),(-.025,0)],cx,cy,side,darkmetal)
        box(root+'brake caliper',(cx-side*.020,cy+.133,.387),(.048,.056,.102),darkmetal,wheelcol,.008)
        stations=[(.060,.39,.090),(.082,.36,.080),(.110,.29,.078),(.15,.225,.087),(.182,.20,.100),(.211,.19,.099)]
        for j in range(5):
            theta=j*math.tau/5;sv=[];sf=[]
            for rr,hw,ax in stations:
                for depth,ang in [(-.024,-hw),(-.024,hw),(0,-hw),(0,hw)]:sv.append((cx+side*(ax+depth),cy+rr*math.sin(theta+ang),.369+rr*math.cos(theta+ang)))
            for k in range(len(stations)-1):
                a=4*k;b=a+4;sf.extend([(a,b,b+1,a+1),(a+2,a+3,b+3,b+2),(a,a+2,b+2,b),(a+1,b+1,b+3,a+3)])
            sf.extend([(0,1,3,2),(20,22,23,21)])
            wheelmesh(root+'sculpted spoke '+str(j),sv,sf,silver,True,.002)
        rev(root+'hub web',[(.056,.043),(.055,.083),(.082,.084),(.094,.070),(.100,.043)],cx,cy,side,silver)
        rev(root+'centre cap',[(.090,0),(.090,.044),(.105,.045),(.110,.039),(.111,0)],cx,cy,side,bright)
        for j in range(6):
            theta=j*math.tau/6;y=cy+.061*math.sin(theta);z=.369+.061*math.cos(theta);vv=[];faces=[]
            for ax in [.094,.108]:
                for k in range(6):ang=k*math.tau/6;vv.append((cx+side*ax,y+.008*math.sin(ang),z+.008*math.cos(ang)))
            faces=[tuple(range(5,-1,-1)),tuple(range(6,12))]+[(k,(k+1)%6,(k+1)%6+6,k+6) for k in range(6)]
            wheelmesh(root+'lug '+str(j),vv,faces,bright,False,.0007)
        theta=.66;yp=cy+.192*math.sin(theta);zp=.369+.192*math.cos(theta)
        curve(root+'valve stem',[(cx+side*.093,yp,zp),(cx+side*.124,yp,zp)],.004,black,wheelcol)
        wheel_specs.append({'root':root,'centre':[cx,cy,.369],'nominal_radius_with_tread':.369,'carcass_radius':.361,'width':.255})

assert hashlib.sha256(source.read_bytes()).hexdigest()==sha
for name,h in protected.items():assert geometry_hash(bpy.data.objects[name])==h,'Unexpected neighbour edit '+name
report={'source':str(source),'source_sha256':sha,'protected_mesh_count':len(protected),'protected_hashes':protected,'bonnet_authority':'Approved 02-form-and-detail.png upper-left: broad centre, shoulder fold and distinct hood/fender seam. User specifically rejected the soft bonnet in exterior v04.','wheel_authority':'Approved sheets: dished alloy, six fasteners, all-terrain tread; original stance/envelope retained.','bonnet_side_boundary_rows':len(ts),'intentional_hood_wing_gap_m':.003,'wheels':wheel_specs,'scope':'Bonnet/wing repair and static wheels. No steering/suspension, cockpit, rig or game export certification.'}
(out/'refinement-manifest.json').write_text(json.dumps(report,indent=2));shutil.copy2(src/'approved-target-shape-spec.json',out/'approved-target-shape-spec.json');shutil.copy2(src/'component-manifest.json',out/'parent-component-manifest.json');shutil.copy2(Path(__file__),out/Path(__file__).name)
sc['stage']='Bonnet/wing correction and detailed wheels; body/cabin retained. Static review.'
for name in ['side','front quarter','rear quarter','front','top']:
    cam=bpy.data.objects['Review | '+name];sc.camera=cam;sc.render.resolution_x,sc.render.resolution_y=cam['resolution'];sc.render.filepath=str(out/(name.replace(' ','-')+'.png'));bpy.ops.render.render(write_still=True)
for name in ['front-module','rear-module']:
    cam=bpy.data.objects['Detail review | '+name];sc.camera=cam;sc.render.resolution_x,sc.render.resolution_y=cam['resolution'];sc.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
sc.camera=bpy.data.objects['Review | front quarter'];sc.render.resolution_x,sc.render.resolution_y=sc.camera['resolution'];bpy.ops.wm.save_as_mainfile(filepath=str(out/'Pathfinder_Bonnet_Wheels.blend'))
print('BONNET_WHEELS_READY '+str(out),flush=True)
