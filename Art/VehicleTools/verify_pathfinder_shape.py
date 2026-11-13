"""Reopen the R50 shape study and check its own measured interfaces."""
import bpy,sys,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
out=Path(sys.argv[sys.argv.index('--')+1]);bpy.ops.wm.open_mainfile(filepath=str(out/'Pathfinder_2002_Shape.blend'));bpy.context.view_layer.update()
S=json.loads((out/'shape-spec.json').read_text());dg=bpy.context.evaluated_depsgraph_get()
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
    tree=bvh(o);vs,_=geom(o);cx,cy,cz=o['centre'];r=max(math.hypot(v.y-cy,v.z-cz) for v in vs)
    root=o.name.replace('tyre envelope','');rim=bpy.data.objects[root+'rim barrel'];rv,_=geom(rim)
    margin=min(min(v.x for v in rv)-min(v.x for v in vs),max(v.x for v in vs)-max(v.x for v in rv))
    wheelrows.append({'wheel':o.name,'radius_m':r,'width_m':max(v.x for v in vs)-min(v.x for v in vs),'rim_margin_m':margin})
    for n,t in obsb.items():
        if tree.overlap(t):crossings.append([o.name,n])
joins=[]
for o in bpy.context.scene.objects:
    if o.type!='MESH' or 'continuous tub' not in o.name:continue
    ids=json.loads(o['seat_vertex_indices']);vs=[o.matrix_world@v.co for v in o.data.vertices];ds=[]
    for a,b in zip(ids,ids[1:]):
        for t in [0,.25,.5,.75,1]:
            v=vs[a].lerp(vs[b],t);ds.append(min(tree.find_nearest(v)[3] for tree in skinb))
    joins.append({'arch':o.name,'maximum_seat_distance_m':max(ds)})
pan=bvh(bpy.data.objects['Floor | fitted passenger and cargo pan']);missing=[];samples=0
for j in range(150):
    yy=-.84+j*2.99/149;inside=False
    for cy in [-1.35,1.35]:
        dy=yy-cy
        if -.465<=dy<=.465 and interp(dy,S['arch_relative_yz'])>.431:inside=True
    if inside:w=.607
    else:
        hits=[t.ray_cast(Vector((1.3,yy,.431)),Vector((-1,0,0)),.8)[0] for t in skinb];hits=[h for h in hits if h is not None]
        if not hits:continue
        w=max(h.x for h in hits)-.012
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
report={'stage':'Primary form study, no interior/rig/export certification','wheelbase_m':axles[-1]-axles[0],
 'wheel_measurements':wheelrows,'tyre_surface_intersections':crossings,'arch_seating':joins,'screen_roof_joins':screen_joins,
 'floor_coverage':{'ray_count':samples,'missing_count':len(missing),'examples':missing[:10]},
 'body_envelope_m':{'length':max(v.y for v in body)-min(v.y for v in body),'width':max(v.x for v in body)-min(v.x for v in body),'roof_height':max(v.z for v in body)},
 'not_applicable_yet':['Seat/wheelhouse clearance: no cockpit fitted','Mudflap attachment: no mudflaps fitted','Motion clearance: no rig fitted']}
report['passed']=not crossings and not missing and abs(report['wheelbase_m']-2.7)<.001 and all(abs(r['radius_m']-.369)<.001 and r['rim_margin_m']>.01 for r in wheelrows) and all(r['maximum_seat_distance_m']<.004 for r in joins) and all(r['max_roof_distance_m']<.002 for r in screen_joins)
(out/'saved-shape-checks.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));assert report['passed']
