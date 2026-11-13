"""Fitted exterior components on the user-endorsed Pathfinder target shape.
Keeps the source blend and primary mesh positions untouched. New output required.
"""
import bpy,bmesh,math,json,hashlib,sys,argparse,shutil
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
out=Path(a.output)
if out.exists() and any(out.iterdir()):raise RuntimeError('Choose a new empty revision.')
out.mkdir(parents=True,exist_ok=True)
source=Path('C:/GrandTour/Art/Export/VehicleTools/pathfinder-approved-target-v03/Pathfinder_2002_Shape.blend')
source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source));sc=bpy.context.scene
S=json.loads((source.parent/'approved-target-shape-spec.json').read_text());P=S['registration']['pixels_per_metre']
def interp(x,rows):
    rows=sorted(rows)
    if x<=rows[0][0]:return rows[0][1]
    for (a,av),(b,bv) in zip(rows,rows[1:]):
        if x<=b:return av+(bv-av)*(x-a)/(b-a)
    return rows[-1][1]
def Y(u):return -1.35+(u-208)/P
def U(y):return 208+(y+1.35)*P
def Z(v):return .369+(891-v)/P
def V(z):return 891-(z-.369)*P
def width(y,z):return interp(z,S['body_section_z_width'])*interp(U(y),S['longitudinal_width'])
def top(y):return Z(interp(U(y),S['side_top_uv']))
def gutter(y):return Z(interp(U(y),S['roof_gutter_uv']))
def cabwidth(y,z):
    t=max(0,min(1,(z-top(y))/(gutter(y)-top(y))));return width(y,top(y))*(1-t)+S['roof_half_width']*t
def cap_y(x,z,rear=False):
    yy=Y(interp(V(z),[(v,u) for u,v in S['rear_profile_uv' if rear else 'front_profile_uv']]))
    dep=S['rear_wrap_depth' if rear else 'front_wrap_depth']*max(0,min(1,(1.10-z)/.22))
    yy+=-dep if rear else dep;f=min(1,abs(x)/width(yy,z))
    return yy+(dep if rear else -dep)*(1-f**5)
def primary_hashes():
    ans={}
    for cname in ['01 | R50 body sections','02 | Fitted cabin and glazing','03 | Arch interfaces','06 | Fitted underside']:
        for o in bpy.data.collections[cname].objects:
            if o.type!='MESH':continue
            h=hashlib.sha256()
            for v in o.data.vertices:h.update(str(tuple(v.co)).encode())
            for f in o.data.polygons:h.update(str(tuple(f.vertices)).encode())
            h.update(str(tuple(tuple(r) for r in o.matrix_world)).encode());ans[o.name]=h.hexdigest()
    return ans
baseline=primary_hashes()
def col(n):
    c=bpy.data.collections.new(n);sc.collection.children.link(c);return c
frontcol=col('10 | Fitted front optics and grille');rearcol=col('11 | Fitted rear optics');trimcol=col('12 | Surface fitted exterior trim')
def mat(n,c,rough=.5,metal=0,trans=0):
    m=bpy.data.materials.new(n);m.use_nodes=True;m.diffuse_color=(*c,1);b=m.node_tree.nodes['Principled BSDF'];b.inputs['Base Color'].default_value=(*c,1);b.inputs['Roughness'].default_value=rough;b.inputs['Metallic'].default_value=metal;b.inputs['Transmission Weight'].default_value=trans;b.inputs['IOR'].default_value=1.46;return m
paint=bpy.data.materials['R50 | restrained burgundy'];bs=paint.node_tree.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=(.075,.013,.022,1);bs.inputs['Roughness'].default_value=.34;bs.inputs['Metallic'].default_value=.30;bs.inputs['Coat Weight'].default_value=.22;bs.inputs['Coat Roughness'].default_value=.27
black=mat('Detail | satin black polymer',(.012,.016,.017),.5)
rubber=mat('Detail | soft rubber seal',(.015,.018,.020),.74)
reflector=mat('Detail | reflector aluminium',(.67,.71,.72),.22,.87)
bright=mat('Detail | satin metal trim',(.39,.43,.45),.26,.83)
glass=mat('Detail | clear moulded lens',(.94,.97,.98),.09,0,.97)
redglass=mat('Detail | red moulded lens',(.49,.008,.016),.23,0,.30)
amberglass=mat('Detail | amber moulded lens',(.88,.28,.015),.22,0,.32)
white=mat('Detail | white ceramic bulb',(.68,.67,.60),.3,.15)
darkmetal=mat('Detail | radiator metal',(.022,.028,.030),.6,.35)

def mesh(n,vs,fs,m,c,solid=0,smooth=False):
    me=bpy.data.meshes.new(n);me.from_pydata(vs,[],fs);me.update();o=bpy.data.objects.new(n,me);c.objects.link(o);me.materials.append(m)
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    for f in me.polygons:f.use_smooth=smooth
    if solid:mod=o.modifiers.new('Component wall thickness','SOLIDIFY');mod.thickness=solid;mod.offset=-1
    o['construction']='Independent fitted component';return o
def curve(n,pts,r,m,c=trimcol):
    cu=bpy.data.curves.new(n,'CURVE');cu.dimensions='3D';cu.bevel_depth=r;cu.bevel_resolution=2;sp=cu.splines.new('POLY');sp.points.add(len(pts)-1)
    for p,v in zip(sp.points,pts):p.co=(*v,1)
    o=bpy.data.objects.new(n,cu);c.objects.link(o);cu.materials.append(m);return o
def box(n,loc,dim,m,c,bevel=.004):
    x,y,z=loc;dx,dy,dz=[v/2 for v in dim];vs=[(x+a*dx,y+b*dy,z+c*dz) for a,b,c in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]]
    o=mesh(n,vs,[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)],m,c)
    if bevel:mod=o.modifiers.new('Moulded edge radius','BEVEL');mod.width=bevel;mod.segments=3
    return o
def rr(x,z,w,h,r,steps=8):
    pts=[]
    for cx,cz,start in [(x+w/2-r,z+h/2-r,0),(x-w/2+r,z+h/2-r,90),(x-w/2+r,z-h/2+r,180),(x+w/2-r,z-h/2+r,270)]:
        for j in range(steps+1):
            t=math.radians(start+90*j/steps);pts.append((cx+r*math.cos(t),cz+r*math.sin(t)))
    return pts
def polar_rectangle(x,z,w,h,r):
    # Uniform angular samples preserve visible flute spacing around the perimeter.
    poly=rr(x,z,w,h,r,16);return poly
def facing_pos(x,z,depth,rear):return (x,cap_y(x,z,rear)+(-depth if rear else depth),z)
def prism(n,poly,axis,lo,hi,c):
    def q(t,p):return (t,*p) if axis==0 else (p[0],t,p[1])
    N=len(poly);vs=[q(t,p) for t in [lo,hi] for p in poly]
    return mesh(n,vs,[tuple(range(N-1,-1,-1)),tuple(range(N,2*N))]+[(i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N)],black,c)
def cut(ob,cutter):
    bpy.context.view_layer.objects.active=ob
    for m in list(ob.modifiers):bpy.ops.object.modifier_apply(modifier=m.name)
    mod=ob.modifiers.new('Fitted component opening','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
def carrier(n,xc,zc,w,h,holes,c,rear=False,depth=.003):
    poly=rr(xc,zc,w,h,min(.022,h*.15))
    o=mesh(n,[facing_pos(x,z,depth,rear) for x,z in poly],[tuple(range(len(poly)))],black,c,.006)
    for hx,hz,hw,hh in holes:
        cut(o,prism('Temporary carrier aperture',rr(hx,hz,hw,hh,min(.016,hh*.15)),1,-3 if not rear else 1, -1 if not rear else 3,c))
    return o
def face_ring(n,outer,inner,depth1,depth2,m,c,rear=False,solid=.001):
    vs=[facing_pos(x,z,depth1,rear) for x,z in outer]+[facing_pos(x,z,depth2,rear) for x,z in inner];N=len(outer)
    return mesh(n,vs,[(i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N)],m,c,solid)
def lens(n,xc,zc,w,h,r,dep,m,c,rear=False,flute=.00030):
    poly=polar_rectangle(xc,zc,w,h,r);N=len(poly);vs=[facing_pos(xc,zc,dep-.002,rear)];fs=[]
    for k in range(1,9):
        t=k/8
        for x,z in poly:
            xx=xc+(x-xc)*t;zz=zc+(z-zc)*t;wave=flute*(1+math.cos((xx-xc)*math.tau/.009))/2
            vs.append(facing_pos(xx,zz,dep-.002*(1-t*t)-wave,rear))
    for i in range(N):fs.append((0,1+i,1+(i+1)%N))
    for k in range(7):
        a=1+k*N;b=a+N
        for i in range(N):fs.append((a+i,b+i,b+(i+1)%N,a+(i+1)%N))
    return mesh(n,vs,fs,m,c,.002,True)
def lamp(n,xc,zc,w,h,c,rear=False,tint=None):
    outer=rr(xc,zc,w,h,min(.019,h*.17));inner=rr(xc,zc,w-.012,h-.012,min(.013,h*.12))
    face_ring(n+' | black perimeter seal',outer,inner,-.0015,.001,rubber,c,rear,.003)
    back=rr(xc,zc,w-.014,h-.014,min(.013,h*.12))
    face_ring(n+' | recessed housing wall',inner,back,.001,.060,black,c,rear,.002)
    if not rear:
        # Separate faceted reflector rings: flared opening to deep bulb pocket.
        rings=[rr(xc,zc,(w-.023)*t,(h-.023)*t,min(.012,h*.11)*t) for t in [1,.83,.48,.20]]
        for j,(a,b) in enumerate(zip(rings,rings[1:])):face_ring(n+' | reflector facet ring '+str(j),a,b,[.009,.025,.047][j],[.025,.047,.058][j],reflector,c,rear,0)
        lens(n+' | bulb pocket',xc,zc,w*.19,h*.19,min(.006,h*.035),.057,black,c,rear,0)
        loc=facing_pos(xc,zc,.041,rear);box(n+' | bulb capsule',loc,(min(.019,w*.14),.012,min(.012,h*.16)),white,c,.004)
    else:
        mesh(n+' | reflector backing',[facing_pos(x,z,.025,rear) for x,z in back],[tuple(range(len(back)))],reflector,c,.002)
    lens(n+' | closed front lens',xc,zc,w-.014,h-.014,min(.013,h*.12),.0015,tint or glass,c,rear)
    return {'name':n,'centre':[xc,zc],'active_width':w-.029,'active_height':h-.029,'rear':rear}

# Repair inherited interfaces without rebuilding the accepted bonnet/cabin/window shapes.
repairs=[]
hood=bpy.data.objects['Bonnet | rolled nose and broad shoulders']
leading=sorted([v.co.copy() for v in list(hood.data.vertices)[:11]],key=lambda v:v.x)
hood_half=max(v.x for v in leading)
def hood_edge(f):
    xx=f*hood_half
    return Vector((xx,interp(xx,[(v.x,v.y) for v in leading]),interp(xx,[(v.x,v.z) for v in leading])))
oldcap=bpy.data.objects['Front | wraparound fascia'];bodycol=bpy.data.collections['01 | R50 body sections']
fracs=sorted(set([j/20 for j in range(-20,21)]+[v.x/hood_half for v in leading]))
zrows=sorted(set([Z(v) for u,v in S['front_profile_uv'] if Z(v)<min(v.z for v in leading)-.006]))
vs=[];fs=[]
for zz in zrows:
    yy=Y(interp(V(zz),[(v,u) for u,v in S['front_profile_uv']]))+S['front_wrap_depth']*max(0,min(1,(1.1-zz)/.22))
    for f in fracs:
        xx=f*width(yy,zz);vs.append((xx,cap_y(xx,zz,False),zz))
vs.extend(tuple(hood_edge(f)) for f in fracs);N=len(fracs)
for j in range(len(zrows)):
    for i in range(N-1):fs.append((j*N+i,j*N+i+1,(j+1)*N+i+1,(j+1)*N+i))
bpy.data.objects.remove(oldcap,do_unlink=True)
frontcap=mesh('Front | wraparound fascia',vs,fs,paint,bodycol,.018)
if sum(p.normal.y for p in frontcap.data.polygons)>0:
    bm=bmesh.new();bm.from_mesh(frontcap.data);bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.to_mesh(frontcap.data);bm.free()
# Recreate through-openings on the repaired front carrier.
apertures=[(0,.902,.88,.198,.025),(0,.625,.86,.14,.016)]
for side in [-1,1]:apertures.extend([(side*.621,.889,.347,.174,.025),(side*.759,.889,.065,.170,.012),(side*.640,.601,.23,.186,.028),(side*.685,.599,.105,.13,.013)])
for x,z,w,h,r in apertures:cut(frontcap,prism('Temporary fascia aperture',rr(x,z,w,h,r),1,-2.7,-1.4,frontcol))
repairs.append({'interface':'Bonnet/front fascia','change':'Removed folded upper fascia rows; last row is sampled from unchanged bonnet leading edge. Solid wall points inward.'})
# The original bumper returns intruded into the tyre envelope: use the same arch
# opening as the side body to trim only the hidden returns at each wheelhouse.
for capname in ['Front | wraparound fascia','Rear | wraparound fascia']:
    ob=bpy.data.objects[capname]
    for label in ['Front','Rear']:
        path=[(Y(u),Z(v)) for u,v in S['arches_uv'][label]]
        poly=[(path[0][0],-.10)]+path+[(path[-1][0],-.10)]
        for side in [-1,1]:
            lo,hi=sorted([side*.596,side*1.1]);cut(ob,prism('Temporary wheelhouse clearance',poly,0,lo,hi,frontcol))
repairs.append({'interface':'Tyre/bumper returns','change':'Trimmed bumper corners through the shared wheelhouse openings; wheel centres, tyres and visible arch openings unchanged.'})
# Resample outer flare seating against evaluated skin triangles; curved body
# sections cannot be approximated reliably by a long straight seating chord.
dg0=bpy.context.evaluated_depsgraph_get();skin_trees={}
for side,nam in [(1,'Left | shared body skin'),(-1,'Right | shared body skin')]:
    ob=bpy.data.objects[nam];eo=ob.evaluated_get(dg0);me=eo.to_mesh();skin_trees[side]=BVHTree.FromPolygons([ob.matrix_world@v.co for v in me.vertices],[tuple(f.vertices) for f in me.polygons]);eo.to_mesh_clear()
for o in list(bpy.data.collections['03 | Arch interfaces'].objects):
    if 'continuous tub' not in o.name:continue
    old=[v.co.copy() for v in o.data.vertices];ids=json.loads(o['seat_vertex_indices']);side=1 if old[ids[0]].x>0 else -1
    rows=[];max_move=0
    for ri in range(len(ids)-1):
        for k in range(8):
            t=k/8;row=[old[ids[ri]+j].lerp(old[ids[ri+1]+j],t) for j in range(4)]
            v=row[0];hit=skin_trees[side].ray_cast(Vector((side*1.2,v.y,v.z)),Vector((-side,0,0)),.65)[0]
            if hit is None:hit=skin_trees[side].find_nearest(v)[0]
            max_move=max(max_move,(hit-v).length);row[0]=hit;rows.append(row)
    row=[old[ids[-1]+j].copy() for j in range(4)];v=row[0];hit=skin_trees[side].ray_cast(Vector((side*1.2,v.y,v.z)),Vector((-side,0,0)),.65)[0]
    if hit is None:hit=skin_trees[side].find_nearest(v)[0]
    max_move=max(max_move,(hit-v).length);row[0]=hit;rows.append(row)
    mv=[tuple(v) for row in rows for v in row];mf=[]
    for i in range(len(rows)-1):
        for j in range(3):a=4*i+j;mf.append((a,a+4,a+5,a+1))
    me=bpy.data.meshes.new(o.name+' | fitted seat');me.from_pydata(mv,[],mf);me.update()
    for m in o.data.materials:me.materials.append(m)
    for p in me.polygons:p.material_index=1 if p.index%3==2 else 0
    o.data=me;o['seat_vertex_indices']=json.dumps(list(range(0,len(mv),4)))
    repairs.append({'interface':o.name,'maximum_seat_vertex_adjustment_m':max_move,'change':'Seating strip projected onto actual body triangles; inner arch and wheelhouse positions preserved.'})

# The floor covers the cabin in plan, but the accepted body sill sits above it.
# Close this vertical slit with real upstands fitted into the side sheet thickness.
floorcol=bpy.data.collections['06 | Fitted underside'];floorz=.431
rearpath=[(Y(u),Z(v)) for u,v in S['arches_uv']['Rear']];cross=[]
for (ya,za),(yb,zb) in zip(rearpath,rearpath[1:]):
    if min(za,zb)<=floorz<=max(za,zb) and za!=zb:cross.append(ya+(yb-ya)*(floorz-za)/(zb-za))
end_y=cap_y(width(Y(940),floorz),floorz,True)-.013
for side in [-1,1]:
    for seg,(lo,hi) in enumerate([(-.86,min(cross)),(max(cross),end_y)]):
        count=max(3,int((hi-lo)/.007));vs=[];fs=[]
        for i in range(count+1):
            yy=lo+(hi-lo)*i/count;lowx=side*(width(yy,floorz)-.010);base=Z(interp(U(yy),S['sill_uv']));ztop=max(floorz+.008,base+.014)
            hit=skin_trees[side].ray_cast(Vector((side*1.2,yy,ztop)),Vector((-side,0,0)),.65)[0]
            highx=hit.x-side*.003 if hit is not None else side*width(yy,ztop)
            vs.extend([(lowx,yy,floorz-.002),(highx,yy,ztop)])
        for i in range(count):k=2*i;fs.append((k,k+2,k+3,k+1))
        mesh('Floor | fitted sill upstand '+str(side)+' '+str(seg),vs,fs,black,floorcol,.008)
repairs.append({'interface':'Floor to body sill','change':'Added fitted upstands to close the vertical floor/body slit; original pan and body coordinates retained.'})

# Smooth normals only on the broad surfaces. Split paint/liner normals at their
# shared boundary so a dark inner tub does not pull the flare highlight inward.
for cname in ['01 | R50 body sections','03 | Arch interfaces']:
    for o in bpy.data.collections[cname].objects:
        if o.type!='MESH':continue
        # The fascia stays deliberately planar between rounded outline vertices.
        if 'fascia' in o.name:continue
        for f in o.data.polygons:f.use_smooth=True
        o.data.update()
        if 'continuous tub' in o.name:
            edge_mats={}
            for p in o.data.polygons:
                for e in p.edge_keys:edge_mats.setdefault(tuple(sorted(e)),set()).add(p.material_index)
            for e in o.data.edges:e.use_edge_sharp=len(edge_mats.get(tuple(sorted(e.vertices)),set()))>1
            mod=o.modifiers.new('Separate liner normals','EDGE_SPLIT');mod.use_edge_angle=False;mod.use_edge_sharp=True
# Replace only owned, named optical proxies and grille trim.
removed=[]
for o in list(bpy.data.objects):
    if o.name.startswith(('Headlamp ','Corner indicator ','Fog lens ','Rear lamp ')) or o.name.startswith('Grille |') or (o.name.startswith('Fog recess ') and o.name.endswith('| inset')):
        removed.append(o.name);bpy.data.objects.remove(o,do_unlink=True)
optics=[]
for side in [-1,1]:
    carrier('Headlamp carrier '+str(side),side*.621,.889,.346,.173,[(side*.588,.889,.239,.157),(side*.753,.889,.061,.153)],frontcol)
    carrier('Fog insert carrier '+str(side),side*.640,.601,.228,.184,[(side*.685,.599,.090,.115)],frontcol,depth=.016)
    carrier('Tail lamp carrier '+str(side),side*.742,.940,.161,.347,[(side*.742,1.065,.139,.070),(side*.742,.939,.139,.161),(side*.742,.812,.139,.067)],rearcol,True)
    optics.append(lamp('Headlamp '+str(side),side*.588,.889,.244,.162,frontcol))
    optics.append(lamp('Amber corner '+str(side),side*.753,.889,.066,.158,frontcol,tint=amberglass))
    optics.append(lamp('Fog lamp '+str(side),side*.685,.599,.095,.120,frontcol))
    # Fitted louvres occupy the other half of the existing fog aperture.
    for k in range(7):
        zz=.540+k*.018;xs=[side*x for x in [.542,.561,.585,.610,.621]]
        pts=[facing_pos(x,zz,.012,False) for x in xs]
        curve('Fog insert '+str(side)+' | louvre '+str(k),pts,.0033,black,frontcol)
    # Three independently fitted lens chambers, clear/red/clear, within the existing tail aperture.
    for label,zc,h,tint in [('upper clear',1.065,.075,glass),('red stop and tail',.939,.166,redglass),('lower clear',.812,.072,glass)]:
        optics.append(lamp('Tail '+str(side)+' '+label,side*.742,zc,.144,h,rearcol,True,tint))

# Actual grille perimeter, crossbar and recessed vertical vanes.
outer=rr(0,.902,.885,.202,.023);inner=rr(0,.902,.850,.170,.015)
face_ring('Grille | satin surround',outer,inner,-.004,.002,bright,frontcol,False,.003)
poly=rr(0,.902,.85,.17,.015)
mesh('Grille | recessed radiator backing',[facing_pos(x,z,.064,False) for x,z in poly],[tuple(range(len(poly)))],darkmetal,frontcol,.002)
for i in range(9):
    xx=-.365+i*.09125;pts=[facing_pos(xx,z,.018,False) for z in [.824,.85,.9,.95,.98]]
    curve('Grille | recessed vane '+str(i),pts,.0065,black,frontcol)
for k in range(10):
    zz=.828+k*.016;curve('Grille | radiator fin '+str(k),[facing_pos(x,zz,.033,False) for x in [-.403,0,.403]],.0015,darkmetal,frontcol)
curve('Grille | shaped crossbar',[facing_pos(x,.902,-.007,False) for x in [-.421,-.3,-.15,0,.15,.3,.421]],.016,bright,frontcol)
curve('Grille | badge ring',[facing_pos(.049*math.sin(i*math.tau/64),.902+.049*math.cos(i*math.tau/64),-.025,False) for i in range(65)],.006,bright,frontcol)
box('Grille | badge bar',(0,cap_y(0,.902)-.027,.902),(.111,.007,.022),bright,frontcol,.005)
# Lower intake ribs follow the recessed carrier, with a real dark back face.
for i in range(5):
    zz=.571+i*.025;curve('Intake | horizontal rib '+str(i),[facing_pos(x,zz,.010,False) for x in [-.397,-.2,0,.2,.397]],.0035,black,frontcol)

def side_ring(n,side,y,z,w,h,m=black):
    outer=rr(y,z,w,h,.017);inner=rr(y,z,w-.006,h-.006,.014);N=len(outer)
    vs=[(side*(width(yy,zz)+.002),yy,zz) for yy,zz in outer]+[(side*(width(yy,zz)+.002),yy,zz) for yy,zz in inner]
    return mesh(n,vs,[(i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N)],m,trimcol,.001)
for side in [-1,1]:
    # Door mouldings track the actual skin, rather than a straight floating bar.
    for lo,hi in [(322,541),(556,667)]:
        y0,y1=Y(lo),Y(hi);zz=Z(818);rows=32;vs=[];fs=[]
        for i in range(rows):
            y=y0+(y1-y0)*i/(rows-1)
            for dz in [-.008,.008]:vs.append((side*(width(y,zz+dz)+.004),y,zz+dz))
        for i in range(rows-1):j=2*i;fs.append((j,j+2,j+3,j+1))
        mesh('Door moulding '+str(side)+' '+str(lo),vs,fs,paint,trimcol,.003,True)
    side_ring('Fuel door | reveal '+str(side),side,Y(817),Z(762),.162,.137)
    y=Y(521);z=Z(757);side_ring('Front handle | fitted recess '+str(side),side,y,z,.176,.070)
    # Rear window divider and cargo vent are fitted to the existing glass/frame surface.
    yy=Y(668);pts=[(side*(cabwidth(yy,Z(v))+.001),yy,Z(v)) for v in range(651,730,4)]
    curve('Rear door glass | divider '+str(side),pts,.006,rubber)
    vent_uv=[(858,651),(866,651),(911,719),(904,722)]
    mesh('Cargo vent | fitted dark backing '+str(side),[(side*(cabwidth(Y(u),Z(v))+.002),Y(u),Z(v)) for u,v in vent_uv],[(0,1,2,3)],black,trimcol,.001)
    for j in range(13):
        vv=660+j*4.6;uu=868+(vv-651)*(911-868)/(719-651);zz=Z(vv);yy=Y(uu)-.016
        curve('Cargo pillar vent '+str(side)+' '+str(j),[(side*(cabwidth(yy+t,zz)+.003),yy+t,zz) for t in [-.016,0,.016]],.0025,black)

# Fit the pad to evaluated bumper triangles, not a planar ngon spanning a curved
# surface. The first version's centre disappeared beneath the actual bumper.
dgpad=bpy.context.evaluated_depsgraph_get();capob=bpy.data.objects['Rear | wraparound fascia'];ce=capob.evaluated_get(dgpad);cm=ce.to_mesh();captree=BVHTree.FromPolygons([capob.matrix_world@v.co for v in cm.vertices],[tuple(p.vertices) for p in cm.polygons]);ce.to_mesh_clear()
def rear_surface_point(x,z,outset):
    hit=captree.ray_cast(Vector((x,3.2,z)),Vector((0,-1,0)),2)[0]
    if hit is None:raise RuntimeError('Bumper trim lacks backing at '+str((x,z)))
    return (x,hit.y+outset,z)
pad=rr(0,.665,1.23,.060,.019,24);N=len(pad);pv=[rear_surface_point(0,.665,.003)];pf=[]
for k in range(1,17):
    t=k/16
    for x,z in pad:pv.append(rear_surface_point(x*t,.665+(z-.665)*t,.003))
for i in range(N):pf.append((0,1+i,1+(i+1)%N))
for k in range(15):
    a=1+k*N;b=a+N
    for i in range(N):pf.append((a+i,b+i,b+(i+1)%N,a+(i+1)%N))
mesh('Rear bumper | fitted protective pad',pv,pf,rubber,trimcol,.003)
for j in range(3):
    zz=.646+j*.016;curve('Rear bumper | pad rib '+str(j),[rear_surface_point(-.575+1.15*i/48,zz,.005) for i in range(49)],.0015,black)
for side in [-1,1]:
    refl=lens('Rear bumper | reflector '+str(side),side*.655,.510,.11,.039,.008,-.002,redglass,rearcol,True,.0002)
    for v in refl.data.vertices:v.co=rear_surface_point(v.co.x,v.co.z,.0025)
box('Tailgate | release handle',(0,cap_y(0,.767,True)+.006,.767),(.124,.018,.035),black,trimcol,.008)

# Windshield wipers use the existing screen surface instead of a horizontal shelf.
screen=bpy.data.objects['Windscreen | glass'];dg=bpy.context.evaluated_depsgraph_get()
def evaluated(o):
    eo=o.evaluated_get(dg);me=eo.to_mesh();vs=[o.matrix_world@v.co for v in me.vertices];fs=[tuple(f.vertices) for f in me.polygons];eo.to_mesh_clear();return vs,fs
sv,sf=evaluated(screen);stree=BVHTree.FromPolygons(sv,sf)
for side in [-1,1]:
    pts=[]
    for j in range(16):
        xx=side*(.11+.48*j/15);zz=1.285+.01*math.sin(j*math.pi/15)
        hit=stree.ray_cast(Vector((xx,-3,zz)),Vector((0,1,0)),5)[0]
        if hit:pts.append(tuple(hit+Vector((0,-.006,0))))
    if len(pts)>2:
        curve('Front wiper | rubber blade '+str(side),pts,.0045,black)
        a=Vector(pts[2]);b=Vector(pts[-4]);pivot=Vector((side*.24,Y(319),Z(710)))
        curve('Front wiper | arm '+str(side),[tuple(pivot),tuple(a.lerp(b,.5)+Vector((0,-.006,.007)))],.004,black)

# Review settings, preserving fixed cameras. Unlit optics; no glow or emissive cheat.
sc.cycles.samples=32;sc.cycles.transmission_bounces=8;sc.cycles.max_bounces=12
sc['stage']='Exterior component pass on user-endorsed target form; wheels and cockpit remain future work.'
sc['source_shape_sha256']=source_hash
sc['visual_authority']='Approved Pathfinder Crafted Utility reference sheets; user endorsed corrected form as Much better.'
after=primary_hashes();changed=[n for n,h in baseline.items() if after.get(n)!=h]
allowed={'Front | wraparound fascia','Rear | wraparound fascia'}|{n for n in baseline if 'continuous tub' in n}
assert set(changed)<=allowed,'Unexpected primary mesh changes: '+str(set(changed)-allowed)
assert hashlib.sha256(source.read_bytes()).hexdigest()==source_hash,'Source blend changed'
report={'source':str(source),'source_sha256':source_hash,'unchanged_primary_mesh_count':len(baseline)-len(changed),'primary_mesh_count':len(baseline),'source_primary_hashes':baseline,'saved_primary_hashes':after,'interface_repairs':repairs,'changed_primary_meshes':changed,'removed_optical_proxies':removed,'optics':optics,'stage':'Exterior components; no cockpit, rig, export or full-car certification'}
(out/'component-manifest.json').write_text(json.dumps(report,indent=2))
shutil.copy2(source.parent/'approved-target-shape-spec.json',out/'approved-target-shape-spec.json');shutil.copy2(Path(__file__),out/Path(__file__).name)
shutil.copy2(Path(__file__).with_name('verify_pathfinder_exterior.py'),out/'verify_pathfinder_exterior.py')
for name in ['side','front quarter','rear quarter','front','rear']:
    cam=bpy.data.objects['Review | '+name];sc.camera=cam;sc.render.resolution_x,sc.render.resolution_y=cam['resolution'];sc.render.filepath=str(out/(name.replace(' ','-')+'.png'));bpy.ops.render.render(write_still=True)
def camera(n,loc,target,scale,res):
    d=bpy.data.cameras.new(n);o=bpy.data.objects.new(n,d);sc.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();d.type='ORTHO';d.ortho_scale=scale;o['resolution']=res;return o
for n,loc,target,scale in [('front-module',(3.4,-6.3,2.20),(0,-1.77,.84),2.7),('rear-module',(3.5,6.8,2.05),(0,1.90,.87),2.85)]:
    cam=camera('Detail review | '+n,loc,target,scale,(1400,1000));sc.camera=cam;sc.render.resolution_x,sc.render.resolution_y=cam['resolution'];sc.render.filepath=str(out/(n+'.png'));bpy.ops.render.render(write_still=True)
sc.camera=bpy.data.objects['Review | front quarter'];sc.render.resolution_x,sc.render.resolution_y=sc.camera['resolution']
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Pathfinder_Exterior.blend'))
print('PATHFINDER_EXTERIOR_READY '+str(out),flush=True)
