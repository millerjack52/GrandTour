"""Static passenger-floor coverage, support and wheel-clearance checks."""
import bpy,math
from mathutils import Vector
import assembly_contracts as ac

def inspect(S):
    floors=[o for o in bpy.context.scene.objects if o.type=='MESH' and (o.name in ['Cabin | central floor','Cabin | cargo floor'] or o.name.startswith('Floor pan |'))]
    trees=[ac.bvh(o) for o in floors]
    R=S['registration'];P=R['pixels_per_metre']
    Y=lambda u:R['axle_front_world']+(u-R['front_hub_px'][0])/P
    Z=lambda v:R['axle_z']+(R['front_hub_px'][1]-v)/P
    U=lambda y:R['front_hub_px'][0]+(y-R['axle_front_world'])*P
    def hit(a,b):
        d=b-a;length=d.length
        return any(t.ray_cast(a,d.normalized(),length)[0] is not None for t in trees)
    # Grid follows the independent body/tub boundaries, not a list stored on the new pan.
    missing=[];count=0
    panels=[ac.bvh(o) for o in bpy.context.scene.objects if o.type=='MESH' and 'derived skin' in o.name]
    for j in range(145):
        y=-.88+j*(2.00+.88)/144;u=U(y)
        arch=any(pts[0][0]<u<pts[-1][0] and Z(ac.interp(u,pts))>.566 for pts in [S['front_arch_uv'],S['rear_arch_uv']])
        if arch:w=.595
        else:
            hits=[t.ray_cast(Vector((1.4,y,.565)),Vector((-1,0,0)),.8)[0] for t in panels]
            hits=[p for p in hits if p is not None]
            if not hits:continue # deliberate door reveals, not floor apertures
            w=max(p.x for p in hits)-.008
        for k in range(29):
            x=-w+2*w*k/28;count+=1
            if not hit(Vector((x,y,.30)),Vector((x,y,.585))):missing.append([x,y])
    exposed=[];samples=0
    seats=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith(('Seat | base frame','Seat | sculpted cushion','Seat | fixed floor','Bench | cushion','Bench | raised pedestal'))]
    for ob in seats:
        vs,_=ac.geometry(ob)
        for p in vs:
            samples+=1
            if not hit(Vector((p.x,p.y,.25)),Vector((p.x,p.y,p.z+.002))):exposed.append([ob.name,list(p)])
    tyres=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith(('Tyre | shaped carcass','Tyre | staggered tread'))]
    crossings=[]
    for ob in floors:
        tree=ac.bvh(ob)
        for tyre in tyres:
            if tree.overlap(ac.bvh(tyre)):crossings.append([ob.name,tyre.name])
    protrusions=[]
    for ob in floors:
        if ob.name!='Floor pan | continuous cabin and cargo':continue
        for q in ac.geometry(ob)[0]:
            if abs(q.x)<.65:continue
            side=1 if q.x>0 else -1
            hits=[t.ray_cast(Vector((side*1.4,q.y,q.z)),Vector((-side,0,0)),.8)[0] for t in panels]
            hits=[h for h in hits if h is not None]
            if hits and abs(q.x)>max(abs(h.x) for h in hits)+.0005:protrusions.append(list(q))
    return {'passed':bool(floors) and count>3000 and samples>100 and not missing and not exposed and not crossings and not protrusions,
        'floor_objects':[o.name for o in floors],'coverage_ray_count':count,'uncovered_floor_samples':len(missing),'uncovered_examples':missing[:20],
        'seat_projection_samples':samples,'exposed_seat_samples':len(exposed),'exposed_examples':exposed[:10],
        'floor_tyre_surface_intersections':crossings,'floor_vertices_outside_body':protrusions,'scope':'Passenger/cargo floor coverage from below, seat-base projection, pan/body envelope and static floor/tyre surface clearance; excludes engine compartment and moving suspension.'}
