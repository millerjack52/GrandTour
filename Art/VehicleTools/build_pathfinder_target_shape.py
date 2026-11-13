"""Reference-led R50 form study. No prior complete vehicle generator is imported.
Editable metre-space meshes, shared body sections, real openings and fitted floor.
"""
import bpy,bmesh,math,json,sys,argparse,shutil
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
p=argparse.ArgumentParser();p.add_argument('--output',required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output)
if out.exists() and any(out.iterdir()):raise RuntimeError('Use a new empty revision to preserve edits.')
out.mkdir(parents=True,exist_ok=True)
src=Path('C:/GrandTour/Art/References/Vehicles/Pathfinder2002');S=json.loads((src/'approved-target-shape-spec.json').read_text());R=S['registration'];D=S['dimensions'];P=R['pixels_per_metre']
bpy.ops.wm.read_factory_settings(use_empty=True);sc=bpy.context.scene;sc.unit_settings.system='METRIC'
def col(name):
    c=bpy.data.collections.new(name);sc.collection.children.link(c);return c
body=col('01 | R50 body sections');cabin=col('02 | Fitted cabin and glazing');arches=col('03 | Arch interfaces');wheels=col('04 | Wheel form proxies');face=col('05 | Identity and trim studies');floor=col('06 | Fitted underside');studio=col('07 | Studio');cameras=col('08 | Fixed review views')
def mat(name,c,rough=.55,metal=0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*c,1);m.use_nodes=True;n=m.node_tree.nodes['Principled BSDF'];n.inputs['Base Color'].default_value=(*c,1);n.inputs['Roughness'].default_value=rough;n.inputs['Metallic'].default_value=metal;return m
paint=mat('R50 | restrained burgundy',(.095,.020,.029),.43,.22);trim=mat('R50 | charcoal',(.031,.039,.040),.6);glass=mat('R50 | shape-study glazing',(.033,.052,.057),.32,.10)
rubber=mat('R50 | rubber',(.027,.030,.031),.8);silver=mat('R50 | subdued alloy',(.44,.46,.44),.35,.6);lens=mat('R50 | clear lens proxy',(.63,.72,.73),.27,.25);amber=mat('R50 | amber',(.70,.245,.026),.35);red=mat('R50 | red lens',(.39,.016,.024),.35);clay=mat('R50 | review clay',(.43,.44,.42),.65)
def interp(x,rs):
    rs=sorted(rs)
    if x<=rs[0][0]:return rs[0][1]
    for (aa,av),(bb,bv) in zip(rs,rs[1:]):
        if x<=bb:return av+(bv-av)*(x-aa)/(bb-aa)
    return rs[-1][1]
def Y(u):
    return -1.35+(u-R['front_hub_px'][0])/P
def U(y):
    return R['front_hub_px'][0]+(y+1.35)*P
def Z(v):return R['axle_z']+(R['front_hub_px'][1]-v)/P
def V(z):return R['front_hub_px'][1]-(z-R['axle_z'])*P
def width(y,z):return interp(z,S['body_section_z_width'])*interp(U(y),S['longitudinal_width'])
def top(y):return Z(interp(U(y),S['side_top_uv']))
def front(z):return Y(interp(V(z),[(v,u) for u,v in S['front_profile_uv']]))
def rear(z):return Y(interp(V(z),[(v,u) for u,v in S['rear_profile_uv']]))

def wrap(z,r):return S['rear_wrap_depth' if r else 'front_wrap_depth']*max(0,min(1,(1.10-z)/.22))
def archz(y):
    u=U(y)
    for pts in S['arches_uv'].values():
        if pts[0][0]<=u<=pts[-1][0]:return Z(interp(u,pts))
    return 0
def bottom(y):return max(Z(interp(U(y),S['sill_uv'])),archz(y))
def mesh(name,vs,fs,material,collection,solid=0):
    me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update();o=bpy.data.objects.new(name,me);collection.objects.link(o)
    if material:me.materials.append(material)
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    if solid:m=o.modifiers.new('Inward sheet','SOLIDIFY');m.thickness=solid;m.offset=-1
    o['stage']='Shape study; editable';return o
def apply(o,m):
    bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=m.name)
def box(name,loc,dim,material,collection=face,bevel=.008):
    x,y,z=loc;dx,dy,dz=[q/2 for q in dim];vs=[(x+a*dx,y+b*dy,z+c*dz) for a,b,c in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]]
    o=mesh(name,vs,[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)],material,collection)
    if bevel:m=o.modifiers.new('Rounded production edge','BEVEL');m.width=bevel;m.segments=2
    return o
def clip(poly,fn):
    result=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=fn(*a);db=fn(*b)
        if da>=-1e-8:result.append(a)
        if (da>=0)!=(db>=0):
            t=da/(da-db);result.append(tuple(x+(y-x)*t for x,y in zip(a,b)))
    return result
def curve(name,pts,r,material,collection=face):
    cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.bevel_depth=r;cu.bevel_resolution=1;s=cu.splines.new('POLY');s.points.add(len(pts)-1)
    for v,p in zip(s.points,pts):v.co=(*p,1)
    o=bpy.data.objects.new(name,cu);collection.objects.link(o);cu.materials.append(material);return o
def prism(name,poly,axis,lo,hi):
    def q(t,p):return (t,*p) if axis==0 else (p[0],t,p[1])
    n=len(poly);vs=[q(t,p) for t in [lo,hi] for p in poly];return mesh(name,vs,[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],None,face)
def cut(o,cutter):
    for m in list(o.modifiers):apply(o,m)
    m=o.modifiers.new('Real opening','BOOLEAN');m.operation='DIFFERENCE';m.solver='EXACT';m.object=cutter;apply(o,m);bpy.data.objects.remove(cutter,do_unlink=True)
def grid_side(name,ys,zs,limits,position,material,collection,solid=.014):
    vs=[];fs=[]
    for ya,yb in zip(ys,ys[1:]):
        for za,zb in zip(zs,zs[1:]):
            poly=[(ya,za),(yb,za),(yb,zb),(ya,zb)]
            for fn in limits:
                if len(poly)<3:break
                poly=clip(poly,fn)
            if len(poly)<3:continue
            i=len(vs);vs.extend(position(y,z) for y,z in poly);fs.append(tuple(range(i,len(vs))))
    return mesh(name,vs,fs,material,collection,solid)
ys=sorted(set([Y(u) for u in range(40,981,3)]+[Y(u) for u,v in S['side_top_uv']]+[Y(u) for pts in S['arches_uv'].values() for u,v in pts]))
zs=sorted(set([z for z,w in S['body_section_z_width']]+[Z(v) for pts in S['arches_uv'].values() for u,v in pts]+[Z(v) for pts in [S['front_profile_uv'],S['rear_profile_uv']] for u,v in pts]))
sideobs=[]
for side in [-1,1]:
    ob=grid_side(('Left' if side>0 else 'Right')+' | shared body skin',ys,zs,[lambda y,z:top(y)-z,lambda y,z:z-bottom(y),lambda y,z:y-front(z)-wrap(z,False),lambda y,z:rear(z)-wrap(z,True)-y],lambda y,z:(side*width(y,z),y,z),paint,body)
    sideobs.append(ob)
# Front and tail surfaces wrap from the exact side perimeter across the centre.
def cap_y(x,z,isrear):
    yy=rear(z)-wrap(z,True) if isrear else front(z)+wrap(z,False);f=min(1,abs(x)/width(yy,z))
    return yy+wrap(z,True)*(1-f**5) if isrear else yy-wrap(z,False)*(1-f**5)
caps={}
for isrear in [False,True]:
    profile=S['rear_profile_uv'] if isrear else S['front_profile_uv']
    topz=Z(734) if isrear else Z(756)
    zrows=sorted(set([Z(v) for u,v in profile if Z(v)<topz]+[topz]))
    vs=[];fs=[];fracs=[-1,-.96,-.86,-.65,-.35,0,.35,.65,.86,.96,1]
    for row,z in enumerate(zrows):
        yy=rear(z)-wrap(z,True) if isrear else front(z)+wrap(z,False)
        for f in fracs:
            zz=z
            if not isrear and row==len(zrows)-1:
                uc,vc=S['bonnet_crown_uv'][0];zc=Z(vc);ze=top(Y(uc))
                zz=zc+(ze-zc)*interp(abs(f),[(0,0),(.50,.05),(.73,.18),(.88,.52),(.97,.88),(1,1)])
            x=f*width(yy,zz);vs.append((x,cap_y(x,zz,isrear),zz))
    n=len(fracs)
    fs=[(j*n+i,j*n+i+1,(j+1)*n+i+1,(j+1)*n+i) for j in range(len(zrows)-1) for i in range(n-1)]
    caps[isrear]=mesh(('Rear' if isrear else 'Front')+' | wraparound fascia',vs,fs,paint,body,.022)
# Bonnet sections reproduce the rolled nose and rounded shoulder, not a wedge.
fracs=[-1,-.97,-.88,-.73,-.50,0,.50,.73,.88,.97,1]
vs=[];fs=[]
for j,(u,v) in enumerate(S['bonnet_crown_uv']):
    yy=Y(u);zc=Z(v);ze=top(yy)
    for f in fracs:
        drop=interp(abs(f),[(0,0),(.50,.05),(.73,.18),(.88,.52),(.97,.88),(1,1)])
        z=zc+(ze-zc)*drop;x=f*width(yy,ze)
        y=cap_y(x,z,False) if j==0 else yy
        vs.append((x,y,z))
n=len(fracs);fs=[(j*n+i,j*n+i+1,(j+1)*n+i+1,(j+1)*n+i) for j in range(len(S['bonnet_crown_uv'])-1) for i in range(n-1)]
hood=mesh('Bonnet | rolled nose and broad shoulders',vs,fs,paint,body,.014)
# Cabin shares its bottom width with the actual body and its top with roof gutter.
def gutter(y):return Z(interp(U(y),S['roof_gutter_uv']))
def crown(y):return Z(interp(U(y),S['roof_crown_uv']))
def cabwidth(y,z):
    t=max(0,min(1,(z-top(y))/(gutter(y)-top(y))));return width(y,top(y))*(1-t)+S['roof_half_width']*t
def cabfront(z):return Y(interp(V(z),[(v,u) for u,v in S['cabin_front_profile_uv']]))
def cabrear(z):return Y(interp(V(z),[(v,u) for u,v in S['cabin_rear_profile_uv']]))
cyrows=sorted(set([Y(u) for u in range(310,949,3)]+[Y(u) for u,v in S['roof_gutter_uv']]))
czrows=[Z(v) for v in range(741,620,-3)];czrows.sort()
for side in [-1,1]:
    ob=grid_side(('Left' if side>0 else 'Right')+' | continuous cabin frame',cyrows,czrows,[lambda y,z:z-top(y),lambda y,z:gutter(y)-z,lambda y,z:y-cabfront(z),lambda y,z:cabrear(z)-y],lambda y,z:(side*cabwidth(y,z),y,z),paint,cabin,.027)
    for key,uv in S['windows'].items():
        poly=[(Y(u),Z(v)) for u,v in uv];cut(ob,prism('Temporary window opening',poly,0,side*.58,side*1.03))
        centre=sum((Vector(p) for p in poly),Vector((0,0)))/len(poly);inner=[tuple(centre+(Vector(p)-centre)*.965) for p in poly]
        outer3=[(side*(cabwidth(y,z)+.001),y,z) for y,z in poly];inner3=[(side*(cabwidth(y,z)+.001),y,z) for y,z in inner];n=len(poly)
        mesh(str(side)+' | '+key+' window seal',outer3+inner3,[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],trim,cabin,.01)
        mesh(str(side)+' | '+key+' recessed glass',[(side*(cabwidth(y,z)-.010),y,z) for y,z in inner],[tuple(range(n))],glass,cabin,.008)
# Crown and gutter are sampled from exactly the same shared roof sections.
vs=[];fs=[]
for u,v in S['roof_crown_uv']:
    yy=Y(u)
    for f in fracs:
        z=crown(yy)+(gutter(yy)-crown(yy))*interp(abs(f),[(0,0),(.5,.10),(.73,.28),(.88,.58),(.97,.91),(1,1)])
        vs.append((S['roof_half_width']*f,yy,z))
n=len(fracs);fs=[(j*n+i,j*n+i+1,(j+1)*n+i+1,(j+1)*n+i) for j in range(len(S['roof_crown_uv'])-1) for i in range(n-1)]
mesh('Roof | shallow transverse and longitudinal crown',vs,fs,paint,body,.018)
def screenpos(s,t,rearward):
    lowy=Y(944 if rearward else 313);highy=Y(881 if rearward else 411)
    ly=cap_y(s*width(lowy,Z(734)),Z(734),True) if rearward else lowy
    lz=Z(734) if rearward else Z(711)+(Z(722)-Z(711))*interp(abs(s),[(0,0),(.50,.05),(.73,.18),(.88,.52),(.97,.88),(1,1)])
    hz=crown(highy)+(gutter(highy)-crown(highy))*interp(abs(s),[(0,0),(.5,.10),(.73,.28),(.88,.58),(.97,.91),(1,1)])
    yy=ly+(highy-ly)*t;z=lz+(hz-lz)*t;x=s*(width(lowy,top(lowy))*(1-t)+S['roof_half_width']*t)
    return (x,yy,z)
border=[(f,0) for f in fracs]+[(f,1) for f in reversed(fracs)]
for r in [False,True]:
    outer=[screenpos(s,t,r) for s,t in border];inner=[screenpos(s*.94,.07+t*.87,r) for s,t in border];n=len(border)
    mesh(('Rear screen' if r else 'Windscreen')+' | formed surround',outer+inner,[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],paint,cabin,.02)
    inside=[screenpos(s*.915,.09+t*.83,r) for s,t in border]
    mesh(('Rear screen' if r else 'Windscreen')+' | rubber',inner+inside,[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],trim,cabin,.008)
    gv=[];gf=[];nu=16;nv=7
    for j in range(nv+1):
        for i in range(nu+1):
            x,y,z=screenpos(-.915+1.83*i/nu,.09+.83*j/nv,r);gv.append((x,y+(-.006 if r else .006),z))
    for j in range(nv):
        for i in range(nu):k=j*(nu+1)+i;gf.append((k,k+1,k+nu+2,k+nu+1))
    glassob=mesh(('Rear screen' if r else 'Windscreen')+' | glass',gv,gf,glass,cabin,.004)
    for p in glassob.data.polygons:p.use_smooth=True
# One fitted band from side seating edge through rounded flare into the inner tub.
for side in [-1,1]:
    for cy,label in [(-1.35,'Front'),(1.35,'Rear')]:
        path=[(Y(u),Z(v)) for u,v in S['arches_uv'][label]];vs=[];fs=[]
        for y,z in path:
            radial=Vector((y-cy,z-.369)).normalized();oy=y+radial.x*S['arch_band_width'];oz=z+radial.y*S['arch_band_width']
            oz=max(Z(interp(U(oy),S['sill_uv']))+.002,oz)
            vs.extend([(side*width(oy,oz),oy,oz),(side*.921,y+radial.x*.035,max(bottom(y) if abs(y-cy)>.47 else 0,z+radial.y*.035)),(side*.924,y,z),(side*.600,y,z)])
        for j in range(len(path)-1):
            for k in range(3):i=j*4+k;fs.append((i,i+4,i+5,i+1))
        o=mesh(label+' '+str(side)+' | seated flare and continuous tub',vs,fs,paint,arches,.01);o.data.materials.append(trim)
        for p in o.data.polygons:
            if p.index%3==2:p.material_index=1
        o['seat_vertex_indices']=json.dumps(list(range(0,len(vs),4)))
        mesh(label+' '+str(side)+' | inner wheelhouse wall',[(side*.600,y,z) for y,z in path],[tuple(range(len(path)))],trim,arches,.012)
# Tyre/rim prototypes establish stance and proper axial fit; tread/lugs deferred.
def revolve(name,profile,cx,cy,cz,side,material):
    vs=[];fs=[];N=48
    for xx,r in profile:
        for j in range(N):a=j*math.tau/N;vs.append((cx+side*xx,cy+r*math.sin(a),cz+r*math.cos(a)))
    for i in range(len(profile)):
        for j in range(N):fs.append((i*N+j,i*N+(j+1)%N,((i+1)%len(profile))*N+(j+1)%N,((i+1)%len(profile))*N+j))
    o=mesh(name,vs,fs,material,wheels)
    for p in o.data.polygons:p.use_smooth=True
    return o
for side in [-1,1]:
    for cy,track,label in [(-1.35,1.54,'Front'),(1.35,1.545,'Rear')]:
        cx=side*track/2;z=.369
        tyre=revolve(label+' '+str(side)+' | tyre envelope',[(-.09,.209),(-.12,.24),(-.1275,.29),(-.119,.345),(-.085,.367),(0,.369),(.085,.367),(.119,.345),(.1275,.29),(.12,.24),(.09,.209)],cx,cy,z,side,rubber)
        tyre['centre']=[cx,cy,z];tyre['expected_radius']=.369
        rim=revolve(label+' '+str(side)+' | rim barrel',[(-.092,.207),(-.092,.225),(.102,.225),(.108,.215),(.102,.205),(-.085,.205)],cx,cy,z,side,silver)
        # Five broad tapered spokes, not disks painted to resemble a wheel.
        for j in range(5):
            aa=j*math.tau/5
            poly=[]
            for rr,ang in [(.054,aa-.44),(.198,aa-.20),(.215,aa+.13),(.188,aa+.23),(.054,aa+.44)]:poly.append((cy+rr*math.sin(ang),z+rr*math.cos(ang)))
            o=prism(label+' '+str(side)+' | wheel spoke '+str(j),poly,0,cx+side*.064,cx+side*.096);o.data.materials.append(silver)
            for c in list(o.users_collection):c.objects.unlink(o)
            wheels.objects.link(o)
        revolve(label+' '+str(side)+' | wheel hub',[(.064,0),(.064,.064),(.105,.061),(.11,0)],cx,cy,z,side,silver)
# Medium-scale identity only: actual recessed fascia apertures, simple lens blocks.
def rectpoly(xc,zc,w,h,r=.018):
    return [(xc-w/2+r,zc-h/2),(xc+w/2-r,zc-h/2),(xc+w/2,zc-h/2+r),(xc+w/2,zc+h/2-r),(xc+w/2-r,zc+h/2),(xc-w/2+r,zc+h/2),(xc-w/2,zc+h/2-r),(xc-w/2,zc-h/2+r)]
def inset(name,poly,r,material,depth=.022,seal=.018):
    o=caps[r];cut(o,prism('Temporary fascia hole',poly,1,-2.7 if not r else 1.8,-1.8 if not r else 2.7))
    cen=sum((Vector(p) for p in poly),Vector((0,0)))/len(poly);inner=[tuple(cen+(Vector(p)-cen)*(1-seal)) for p in poly];n=len(poly)
    outer3=[(x,cap_y(x,z,r),z) for x,z in poly];inner3=[(x,cap_y(x,z,r)+( -depth if r else depth),z) for x,z in inner]
    mesh(name+' | aperture return',outer3+inner3,[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],trim,face)
    return mesh(name+' | inset',inner3,[tuple(range(n))],material,face,.006)
inset('Grille',rectpoly(0,.902,.88,.198,.025),False,trim,.04)
for x in [-.439,.439]:curve('Grille | side surround',[(x,cap_y(x,z,False)-.002,z) for z in [.810,.85,.95,.996]],.008,silver)
for z in [.800,1.004]:curve('Grille | horizontal surround',[(x,cap_y(x,z,False)-.002,z) for x in [-.414,-.25,0,.25,.414]],.010,silver)
curve('Grille | single crossbar',[(x,cap_y(x,.902,False)+.009,.902) for x in [-.417,0,.417]],.022,silver)
# A simple ring marks badge placement without fine lettering.
curve('Grille | emblem placeholder',[(.047*math.sin(a),cap_y(0,.902,False)-.023,.902+.047*math.cos(a)) for a in [j*math.tau/32 for j in range(33)]],.006,silver)
for side in [-1,1]:
    inset('Headlamp '+str(side),rectpoly(side*.621,.889,.347,.174,.025),False,lens,.014)
    inset('Corner indicator '+str(side),rectpoly(side*.759,.889,.065,.170,.012),False,amber,.010)
    inset('Fog recess '+str(side),rectpoly(side*.64,.601,.23,.186,.028),False,trim,.020)
    inset('Fog lens '+str(side),rectpoly(side*.685,.599,.105,.13,.013),False,lens,.009)
inset('Lower intake',rectpoly(0,.625,.86,.14,.016),False,trim,.035)
for side in [-1,1]:
    inset('Rear lamp '+str(side),rectpoly(side*.742,.940,.162,.348,.035),True,red,.015)
    for z in [.822,1.05]:
        poly=rectpoly(side*.742,z,.145,.065,.013)
        mesh('Rear lamp | clear band',[(x,cap_y(x,zz,True)-.010,zz) for x,zz in poly],[tuple(range(8))],lens,face,.005)
inset('Tailgate plate well',rectpoly(0,.9,.55,.235,.028),True,trim,.026)
# Door split locations and high rear handle follow the particular R50 body.
for side in [-1,1]:
    for u in [313,549,756]:
        yy=Y(u);pts=[]
        for j in range(25):
            z=bottom(yy)+.015+(top(yy)-bottom(yy)-.019)*j/24
            if U(yy)<340 and z<.60:continue
            pts.append((side*(width(yy,z)+.0015),yy,z))
        curve('Door boundary '+str(side)+' '+str(u),pts,.0016,trim)
    yy=Y(521);zz=Z(757);box('Front door | handle '+str(side),(side*(width(yy,zz)+.013),yy,zz),(.025,.136,.034),trim,bevel=.008)
    yy=Y(753);zz=Z(713);box('Rear door | high handle '+str(side),(side*(cabwidth(yy,zz)+.009),yy,zz),(.023,.071,.100),trim,bevel=.012)
    # Mirror mounts are rooted at the front window corner.
    yy=Y(352);zz=Z(731);box('Mirror | stalk '+str(side),(side*.868,yy,zz),(.115,.053,.043),trim)
    box('Mirror | housing '+str(side),(side*.944,yy-.014,zz+.052),(.15,.21,.13),trim,bevel=.038)
    box('Mirror | glass '+str(side),(side*.944,yy+.092,zz+.052),(.118,.006,.101),silver,bevel=.014)
    # Restrained standard rails, supported at three roof locations.
    pts=[]
    for u in [443,465,560,680,800,855]:
        yy=Y(u);pts.append((side*.650,yy,crown(yy)+.06))
    curve('Roof rail '+str(side),pts,.025,trim)
    for u in [461,675,844]:
        yy=Y(u);box('Roof rail | foot',(side*.650,yy,crown(yy)+.025),(.060,.115,.075),trim,bevel=.013)
    # Step tube anchored with two support brackets.
    curve('Side step '+str(side),[(side*.865,y,.345) for y in [-.85,-.77,.25,.76]],.033,silver)
    for yy in [-.68,.65]:box('Side step | support',(side*.758,yy,.359),(.22,.065,.028),trim)
# Medium-scale bumper boundaries are structural character, not ornamental detail.
for isrear,v in [(False,804),(True,822)]:
    zz=Z(v);yy=rear(zz)-wrap(zz,True) if isrear else front(zz)+wrap(zz,False)
    ww=width(yy,zz)
    curve(('Rear' if isrear else 'Front')+' bumper | reveal',[(f*ww,cap_y(f*ww,zz,isrear)+(.002 if isrear else -.002),zz) for f in [-1,-.98,-.95,-.9,-.8,-.6,-.3,0,.3,.6,.8,.9,.95,.98,1]],.0028,trim)
    for side in [-1,1]:
        end=Y(859 if isrear else 144)
        lo,hi=sorted([yy,end]);pts=[]
        for j in range(32):
            y=lo+(hi-lo)*j/31
            if zz>=bottom(y):pts.append((side*(width(y,zz)+.002),y,zz))
        if len(pts)>1:curve(('Rear' if isrear else 'Front')+' bumper | side reveal '+str(side),pts,.0028,trim)
# Continuous shaped floor: wide between arches, narrow to inner tubs at wheels.
fv=[];ff=[];zz=.431;cross=[]
rear_path=[(Y(u),Z(v)) for u,v in S['arches_uv']['Rear']]
for (ya,za),(yb,zb) in zip(rear_path,rear_path[1:]):
    if min(za,zb)<=zz<=max(za,zb) and za!=zb:cross.append(ya+(yb-ya)*(zz-za)/(zb-za))
for lo,hi,narrow in [(-.86,min(cross),False),(min(cross),max(cross),True),(max(cross),rear(zz)-wrap(zz,True)-.012,False)]:
    count=max(2,int((hi-lo)/.012)+1)
    for i in range(count+1):
        yy=lo+(hi-lo)*i/count;wide=.599 if narrow else width(yy,zz)-.008
        fv.extend([(-wide,yy,zz),(wide,yy,zz)])
for i in range(0,len(fv)-2,2):ff.append((i,i+1,i+3,i+2))
pan=mesh('Floor | fitted passenger and cargo pan',fv,ff,trim,floor,.020)
# Basic front closing face, no invented seats or exposed empty cockpit furniture.
loww=width(-.86,.431)-.015;highw=width(-.70,.90)-.015
mesh('Floor | front footwell closure',[(-loww,-.86,.431),(loww,-.86,.431),(highw,-.70,.90),(-highw,-.70,.90)],[(0,1,2,3)],trim,floor,.012)
for side in [-1,1]:box('Underbody | shallow sill member',(side*.65,.35,.38),(.09,2.5,.085),trim,floor,.012)
# Pack original sources and approved style board with a clear provenance note.
for file in ['side.jpg','front-quarter.jpg','rear-quarter.jpg','01-crafted-utility-overall.png','02-form-and-detail.png']:
    im=bpy.data.images.load(str(src/file));im.pack();im.use_fake_user=True
for name in ['approved-target-shape-spec.json','style-prompts.json']:
    shutil.copy2(src/name,out/name);t=bpy.data.texts.new(name);t.write((src/name).read_text())
t=bpy.data.texts.new('START HERE | Pathfinder shape review');t.write('2002 Nissan Pathfinder R50 SE. First independent form study following user approval of generated Crafted Utility reference sheets.\nBody, cabin, roof, flares and floor share per-car sections. The real photographs resolve identity; generated views define stylization, not measured geometry.\nWindows and fascia have actual cutouts. Wheels/lenses are simple form proxies; tyre tread, detailed optics, cockpit, rig and export are deferred until shape review.\nDo not apply Range Rover-specific repair scripts or treat their checks as transferable certification.\nSave manual changes in a new revision. Source generator refuses a non-empty output.\n')
ground=mat('Studio | warm pale grey',(.39,.405,.40),.9)
mesh('Ground',[(-200,-200,-.008),(200,-200,-.008),(200,200,-.008),(-200,200,-.008)],[(0,1,2,3)],ground,studio)
world=bpy.data.worlds.new('Neutral studio');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.60,.64,.67,1);world.node_tree.nodes['Background'].inputs[1].default_value=.55;sc.world=world
for name,loc,power,size in [('Key',(4,-4,6),1200,5),('Fill',(-4,-1,4),850,4),('Rim',(1,4,5),1000,3)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);studio.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,.8))-o.location).to_track_quat('-Z','Y').to_euler()
def cam(name,loc,target,scale,res):
    d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);cameras.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();d.type='ORTHO';d.ortho_scale=scale;o['resolution']=res;return o
views={'side':cam('Review | side',(8,.04,.94),(0,.04,.94),5.05,(1400,650)),
 'quarter':cam('Review | front quarter',(5.8,-8.3,3.55),(0,.05,.85),5.75,(1250,900)),
 'rear-quarter':cam('Review | rear quarter',(5.7,8.1,3.3),(0,.05,.86),5.7,(1250,900)),
 'front':cam('Review | front',(0,-8,.94),(0,0,.94),2.48,(950,900)),
 'rear':cam('Review | rear',(0,8,.94),(0,0,.94),2.48,(950,900)),
 'top':cam('Review | top',(0,.03,8),(0,.03,0),5.0,(850,1250)),
 'underside':cam('Review | underside',(3.7,4.7,-2.7),(0,.04,.65),5.45,(1250,900))}
sc.render.engine='CYCLES';sc.cycles.samples=24;sc.cycles.use_denoising=True;sc.render.threads_mode='FIXED';sc.render.threads=12;sc.view_settings.view_transform='AgX';sc.render.image_settings.file_format='PNG';sc.render.resolution_percentage=100
sc['vehicle']='2002 Nissan Pathfinder - approved style target refit';sc['stage']='Primary shape correction; user has not approved this mesh. Assembly must be rechecked after form acceptance.'
shutil.copy2(Path(__file__),out/Path(__file__).name)
for key,camera in views.items():
    if key not in ['side','quarter','rear-quarter','front']:continue
    sc.camera=camera;sc.render.resolution_x,sc.render.resolution_y=camera['resolution'];sc.render.filepath=str(out/(key+'.png'));bpy.data.objects['Ground'].hide_render=key=='underside';bpy.ops.render.render(write_still=True)
bpy.data.objects['Ground'].hide_render=False
sc.camera=views['quarter'];sc.render.resolution_x,sc.render.resolution_y=sc.camera['resolution']
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Pathfinder_2002_Shape.blend'))
print('PATHFINDER_SHAPE_READY '+str(out),flush=True)
