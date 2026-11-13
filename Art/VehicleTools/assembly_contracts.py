"""Static assembly checks for mating surfaces, attachment and occupied volumes.
These are image-study modelling contracts, not vehicle engineering certification.
"""
import bpy,math,json
from mathutils import Vector
from mathutils.bvhtree import BVHTree

def geometry(ob):
    dg=bpy.context.evaluated_depsgraph_get();eo=ob.evaluated_get(dg);me=eo.to_mesh()
    vs=[ob.matrix_world@v.co for v in me.vertices];fs=[tuple(p.vertices) for p in me.polygons];eo.to_mesh_clear();return vs,fs
def bvh(ob):
    vs,fs=geometry(ob);return BVHTree.FromPolygons(vs,fs,all_triangles=False)
def bounds(ob):
    vs,fs=geometry(ob);return [min(v[i] for v in vs) for i in range(3)],[max(v[i] for v in vs) for i in range(3)]
def interp(x,rows):
    rows=sorted(rows)
    if x<=rows[0][0]:return rows[0][1]
    for (a,v),(b,w) in zip(rows,rows[1:]):
        if x<=b:return v+(w-v)*(x-a)/(b-a)
    return rows[-1][1]

def inspect(S):
    bpy.context.view_layer.update();R=S['registration'];P=R['pixels_per_metre']
    Y=lambda u:R['axle_front_world']+(u-R['front_hub_px'][0])/P
    Z=lambda v:R['axle_z']+(R['front_hub_px'][1]-v)/P
    U=lambda y:R['front_hub_px'][0]+(y-R['axle_front_world'])*P
    panels=[o for o in bpy.context.scene.objects if o.type=='MESH' and 'derived skin' in o.name]
    trees={o.name:bvh(o) for o in panels}
    def skin_nearest(v,side):
        candidates=[trees[o.name].find_nearest(v) for o in panels if o.name.startswith('L' if side>0 else 'R')]
        candidates=[r for r in candidates if r[0] is not None];return min(candidates,key=lambda r:r[3])
    result={}
    # Lower cargo-pillar boundary: nearest real side skin, not a nominal width.
    samples=[]
    for side,label in [(1,'Left'),(-1,'Right')]:
        ob=bpy.data.objects[label+' | cargo_window frame'];vs,fs=geometry(ob)
        for v in vs:
            if v.y>Y(780) and abs(v.z-Z(136))<.004:
                hit=skin_nearest(v,side);samples.append({'side':label,'point':list(v),'gap_m':hit[3]})
    result['rear_pillar_join']={'passed':bool(samples) and max(p['gap_m'] for p in samples)<=.004,'samples':samples}
    # Cross-arch intervals expose a lip-to-liner air gap. Also measure the outer
    # seating edge against the actual adjacent panels, including intermediate points.
    arches=[]
    for side in [-1,1]:
        for key in ['front_arch_uv','rear_arch_uv']:
            obs=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith(str(side)+' | '+key) and ('lip' in o.name or 'well' in o.name)]
            stationgaps=[]
            for u,v in S[key][2:-2]:
                intervals=[]
                for ob in obs:
                    vs,fs=geometry(ob);xs=[side*p.x for p in vs if math.hypot(p.y-Y(u),p.z-Z(v))<.0045]
                    if xs:intervals.append([min(xs),max(xs)])
                intervals.sort();gap=0
                if intervals:
                    end=intervals[0][1]
                    for lo,hi in intervals[1:]:gap=max(gap,lo-end);end=max(end,hi)
                else:gap=999
                stationgaps.append(gap)
            lip=next(o for o in obs if 'lip' in o.name)
            seating=[]
            # Contact edges are obtained from actual mesh vertices by index.
            ids=json.loads(lip.get('contact_edge_indices','[]'))
            if ids:
                verts=[lip.matrix_world@v.co for v in lip.data.vertices]
                for aa,bb in zip(ids,ids[1:]):
                    for t in [0,.25,.5,.75,1]:
                        q=verts[aa].lerp(verts[bb],t);seating.append(skin_nearest(q,side)[3])
            arches.append({'side':side,'arch':key,'max_lip_liner_gap_m':max(stationgaps),'max_seat_gap_m':max(seating) if seating else None})
    result['arch_joins']={'passed':all(a['max_lip_liner_gap_m']<.002 and (a['max_seat_gap_m'] is None or a['max_seat_gap_m']<.0025) for a in arches),'arches':arches}
    # Require a physical chain: flap -> clamp -> hanger -> body. Parenting alone
    # cannot satisfy this test. Deliberate mounting intersections are expected.
    mounts=[]
    for flap in [o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith('Mudflap | flexible rubber')]:
        clamp=bpy.data.objects.get(flap.get('mount_clamp',''));hanger=bpy.data.objects.get(flap.get('mount_hanger',''));panel=bpy.data.objects.get(flap.get('mount_panel',''))
        edges={}
        if clamp and hanger and panel:
            for label,a,b in [('flap_clamp',flap,clamp),('clamp_hanger',clamp,hanger),('hanger_body',hanger,panel)]:edges[label]=bool(bvh(a).overlap(bvh(b)))
        mounts.append({'flap':flap.name,'contacts':edges,'attached':len(edges)==3 and all(edges.values())})
    result['mudflap_attachment']={'passed':len(mounts)==4 and all(r['attached'] for r in mounts),'mounts':mounts}
    # Test surfaces AND a wheelhouse keep-out volume; containment can be missed
    # by surface-intersection-only tests. The extra 10 mm is a modelling margin.
    benches=[o for o in bpy.data.collections['Cabin | Rear bench'].objects if o.type=='MESH']
    wells=[o for o in bpy.context.scene.objects if o.type=='MESH' and 'rear_arch_uv' in o.name]
    wellb={o.name:bvh(o) for o in wells};crossings=[];inside=[];clearances=[]
    pts=S['rear_arch_uv']
    for ob in benches:
        bv=bvh(ob)
        for well in wells:
            if bv.overlap(wellb[well.name]):crossings.append([ob.name,well.name])
        vs,fs=geometry(ob)
        for v in vs:
            u=U(v.y)
            if pts[0][0]<=u<=pts[-1][0] and .2<v.z<Z(interp(u,pts))+.010:
                clearance=.600-abs(v.x);clearances.append(clearance)
                if clearance<.020:inside.append({'object':ob.name,'point':list(v),'clearance_m':clearance})
    result['rear_seat_wheelhouse']={'passed':not crossings and not inside,'surface_intersections':crossings,'keepout_violations':inside[:20],'violation_count':len(inside),'minimum_lateral_clearance_m':min(clearances) if clearances else None}
    # Compare actual axial envelopes and positive bead/barrel contact, both of
    # which the earlier outer-radius-only wheel test omitted.
    wheels=[]
    for c in [c for c in bpy.data.collections if c.name.endswith('| Detailed wheel')]:
        root=next(o for o in c.objects if o.get('mount'));carcass=next(o for o in c.objects if o.name.startswith('Tyre | shaped carcass'));barrel=next(o for o in c.objects if o.name.startswith('Rim | barrel'))
        tv,tf=geometry(carcass);rv=[]
        for ob in c.objects:
            if ob.type=='MESH' and (ob.name.startswith('Rim |') or ob.name.startswith('Wheel |')):rv.extend(geometry(ob)[0])
        tlo=min(v.x for v in tv);thi=max(v.x for v in tv);rlo=min(v.x for v in rv);rhi=max(v.x for v in rv)
        margin=min(rlo-tlo,thi-rhi);contact=bool(bvh(carcass).overlap(bvh(barrel)))
        wheels.append({'wheel':c.name,'tyre_width_m':thi-tlo,'rim_hardware_width_m':rhi-rlo,'minimum_sidewall_margin_m':margin,'bead_barrel_contact':contact})
    result['tyre_rim_fit']={'passed':len(wheels)==4 and all(r['minimum_sidewall_margin_m']>=.008 and r['bead_barrel_contact'] for r in wheels),'wheels':wheels}
    from floor_contracts import inspect as inspect_floor
    result['floor_coverage']=inspect_floor(S)
    result['passed']=all(v['passed'] for v in result.values())
    result['scope']='Six specific static assembly contracts, including passenger floor coverage. Not a global solid-intersection or vehicle-engineering certification.'
    return result
