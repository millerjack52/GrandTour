"""Reopen the R50 shape study and check its own measured interfaces."""
import bpy,sys,json,math,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
out=Path(sys.argv[sys.argv.index('--')+1]);bpy.ops.wm.open_mainfile(filepath=str(out/'Pathfinder_Bonnet_Wheels.blend'));bpy.context.view_layer.update()
S=json.loads((out/'approved-target-shape-spec.json').read_text());dg=bpy.context.evaluated_depsgraph_get()
P=S['registration']['pixels_per_metre']
def U(y):return 208+(y+1.35)*P
def Z(v):return .369+(891-v)/P
def geom(o):
    eo=o.evaluated_get(dg);m=eo.to_mesh();vs=[o.matrix_world@v.co for v in m.vertices];fs=[tuple(p.vertices) for p in m.polygons];eo.to_mesh_clear();return vs,fs
def bvh(o):
    v,f=geom(o);return BVHTree.FromPolygons(v,f,all_triangles=False)
def interp(x,rows):
    rows=sorted(rows)
    if x<=rows[0][0]:return rows[0][1]
    for (a,av),(b,bv) in zip(rows,rows[1:]):
        if x<=b:return av+(bv-av)*(x-a)/(b-a)
    return rows[-1][1]
skins=[o for o in bpy.context.scene.objects if o.type=='MESH' and 'shared body skin' in o.name];skinb=[bvh(o) for o in skins]
tyres=[o for o in bpy.context.scene.objects if o.type=='MESH' and 'tyre envelope' in o.name]
obstacles=[o for o in bpy.context.scene.objects if o.type=='MESH' and ('shared body skin' in o.name or 'wheelhouse wall' in o.name or 'continuous tub' in o.name or o.name.startswith('Floor |') or 'fascia' in o.name)]
obsb={o.name:bvh(o) for o in obstacles};crossings=[];wheelrows=[]
for o in tyres:
    tree=bvh(o);vs,_=geom(o);cx,cy,cz=o['centre'];tread=bpy.data.objects[o.name.replace('tyre envelope','tread blocks')];tv,_=geom(tread);r=max(math.hypot(v.y-cy,v.z-cz) for v in vs+tv)
    root=o.name.replace('tyre envelope','');rim=bpy.data.objects[root+'rim barrel'];rv,_=geom(rim)
    margin=min(min(v.x for v in rv)-min(v.x for v in vs),max(v.x for v in vs)-max(v.x for v in rv))
    wheelrows.append({'wheel':o.name,'radius_m':r,'width_m':max(v.x for v in vs)-min(v.x for v in vs),'rim_margin_m':margin})
    for n,t in obsb.items():
        if tree.overlap(t) or bvh(tread).overlap(t):crossings.append([o.name,n])
joins=[]
for o in bpy.context.scene.objects:
    if o.type!='MESH' or 'continuous tub' not in o.name:continue
    ids=json.loads(o['seat_vertex_indices']);vs=[o.matrix_world@v.co for v in o.data.vertices];ds=[]
    for a,b in zip(ids,ids[1:]):
        for t in [0,.25,.5,.75,1]:
            v=vs[a].lerp(vs[b],t);ds.append(min(tree.find_nearest(v)[3] for tree in skinb))
    joins.append({'arch':o.name,'maximum_seat_distance_m':max(ds)})
pan=bvh(bpy.data.objects['Floor | fitted passenger and cargo pan']);missing=[];samples=0
def shape_width(y,z):return interp(z,S['body_section_z_width'])*interp(U(y),S['longitudinal_width'])
floor_z=.431
rear_u=interp(891-(floor_z-.369)*P,[(v,u) for u,v in S['rear_profile_uv']])
end_y=-1.35+(rear_u-208)/P-S['rear_wrap_depth']*max(0,min(1,(1.1-floor_z)/.22))-.020
for j in range(150):
    yy=-.84+j*(end_y+.84)/149;inside=False
    for pts in S['arches_uv'].values():
        if pts[0][0]<=U(yy)<=pts[-1][0] and Z(interp(U(yy),pts))>.431:inside=True
    if inside:w=.594
    else:
        w=shape_width(yy,floor_z)-.012
    for k in range(25):
        xx=-w+k*2*w/24;samples+=1
        if pan.ray_cast(Vector((xx,yy,0)),Vector((0,0,1)),.46)[0] is None:missing.append([xx,yy])
body=[v for o in bpy.data.collections['01 | R50 body sections'].objects if o.type=='MESH' for v in geom(o)[0]]
roof_tree=bvh(bpy.data.objects['Roof | shallow transverse and longitudinal crown']);screen_joins=[]
for name,isrear in [('Windscreen | formed surround',False),('Rear screen | formed surround',True)]:
    ob=bpy.data.objects[name];pts=[ob.matrix_world@v.co for v in ob.data.vertices];edge_y=(min if isrear else max)(v.y for v in pts)
    edge=[v for v in pts if abs(v.y-edge_y)<1e-6]
    ds=[roof_tree.find_nearest(v)[3] for v in edge];screen_joins.append({'screen':name,'max_roof_distance_m':max(ds)})
axles=sorted(set(round((min(v.y for v in geom(o)[0])+max(v.y for v in geom(o)[0]))/2,6) for o in tyres))
closure_trees=skinb+[bvh(o) for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith('Floor |')]
closure_gaps=[]
for i in range(45):
    yy=-.70+i*1.40/44;body_low=Z(interp(U(yy),S['sill_uv']));zz=(.431+body_low)/2
    for side in [-1,1]:
        if not any(t.ray_cast(Vector((side*1.15,yy,zz)),Vector((-side,0,0)),.57)[0] is not None for t in closure_trees):closure_gaps.append([side,yy,zz])
manifest=json.loads((out/'parent-component-manifest.json').read_text());occluders={o.name:bvh(o) for o in bpy.context.scene.objects if o.type=='MESH' and ('wraparound fascia' in o.name or 'carrier' in o.name.lower() or (o.name.startswith('Fog recess ') and o.name.endswith('| inset')))}
blocked=[];optical_rays=0
def face_y(x,z,rear):
    uv=interp(891-(z-.369)*P,[(v,u) for u,v in S['rear_profile_uv' if rear else 'front_profile_uv']]);yy=-1.35+(uv-208)/P;dep=S['rear_wrap_depth' if rear else 'front_wrap_depth']*max(0,min(1,(1.10-z)/.22));yy+=-dep if rear else dep;f=min(1,abs(x)/shape_width(yy,z));return yy+(dep if rear else -dep)*(1-f**5)
for lamp in manifest['optics']:
    xc,zc=lamp['centre'];rear=lamp['rear'];direction=Vector((0,-1 if rear else 1,0))
    for i in [-.4,-.2,0,.2,.4]:
        for j in [-.4,-.2,0,.2,.4]:
            xx=xc+i*lamp['active_width'];zz=zc+j*lamp['active_height'];yy=face_y(xx,zz,rear);start=Vector((xx,yy,zz))-direction*.03;optical_rays+=1
            for name,tree in occluders.items():
                if tree.ray_cast(start,direction,.063)[0] is not None:blocked.append([lamp['name'],name,xx,zz])
refinement=json.loads((out/'refinement-manifest.json').read_text());expected=refinement['protected_hashes'];hash_mismatch=[]
for name,wanted in expected.items():
    o=bpy.data.objects.get(name)
    if not o:hash_mismatch.append(name);continue
    h=hashlib.sha256()
    for v in o.data.vertices:h.update(str(tuple(v.co)).encode())
    for f in o.data.polygons:h.update(str(tuple(f.vertices)).encode())
    h.update(str(tuple(tuple(r) for r in o.matrix_world)).encode())
    if h.hexdigest()!=wanted:hash_mismatch.append(name)
# Test whole interpolated wing boundary against the original side skin.
wing_joins=[]
for side,label in [(-1,'Right'),(1,'Left')]:
    ob=bpy.data.objects[label+' | fitted front wing top']
    skin=next(o for o in skins if o.name.startswith(label))
    raw=BVHTree.FromPolygons([v.co for v in skin.data.vertices],[tuple(p.vertices) for p in skin.data.polygons])
    ids=list(range(8 if side>0 else 0,len(ob.data.vertices),9));dist=[]
    for a,b in zip(ids,ids[1:]):
        for t in [0,.25,.5,.75,1]:dist.append(raw.find_nearest(ob.data.vertices[a].co.lerp(ob.data.vertices[b].co,t))[3])
    wing_joins.append({'side':label,'samples':len(dist),'maximum_distance_m':max(dist)})
hood=bpy.data.objects['Bonnet | defined crown and shoulder folds'];rows=refinement['bonnet_side_boundary_rows'];cols=len(hood.data.vertices)//rows;gap=[]
for side,label in [(-1,'Right'),(1,'Left')]:
    wing=bpy.data.objects[label+' | fitted front wing top']
    for j in range(rows):
        h=hood.data.vertices[j*cols+(cols-1 if side>0 else 0)].co
        w=wing.data.vertices[j*9+(0 if side>0 else 8)].co;gap.append((h-w).length)
source_unchanged=hashlib.sha256(Path(refinement['source']).read_bytes()).hexdigest()==refinement['source_sha256']
report={'wing_to_body_joins':wing_joins,'hood_wing_reveal_m':{'min':min(gap),'max':max(gap)},'source_unchanged':source_unchanged,'stage' :'Bonnet and wheel revision, no interior/rig/export certification','wheelbase_m':axles[-1]-axles[0],
 'wheel_measurements':wheelrows,'tyre_surface_intersections':crossings,'arch_seating':joins,'screen_roof_joins':screen_joins,
 'floor_coverage':{'ray_count':samples,'missing_count':len(missing),'examples':missing[:10]},
 'floor_sill_closure':{'rays':90,'open_count':len(closure_gaps),'examples':closure_gaps[:4]},
 'optical_openings':{'ray_count':optical_rays,'blocked_count':len(blocked),'examples':blocked[:12]},
 'saved_primary_hash_mismatches':hash_mismatch,
 'body_envelope_m':{'length':max(v.y for v in body)-min(v.y for v in body),'width':max(v.x for v in body)-min(v.x for v in body),'roof_height':max(v.z for v in body)},
 'not_applicable_yet':['Seat/wheelhouse clearance: no cockpit fitted','Mudflap attachment: no mudflaps fitted','Motion clearance: no rig fitted']}
report['passed']=source_unchanged and all(r['maximum_distance_m']<.001 for r in wing_joins) and min(gap)>.0029 and max(gap)<.0031 and not crossings and not missing and not closure_gaps and not blocked and not hash_mismatch and abs(report['wheelbase_m']-2.7)<.001 and all(abs(r['radius_m']-.369)<.001 and r['rim_margin_m']>.01 for r in wheelrows) and all(r['maximum_seat_distance_m']<.004 for r in joins) and all(r['max_roof_distance_m']<.002 for r in screen_joins)
(out/'saved-assembly-checks.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));assert report['passed']
