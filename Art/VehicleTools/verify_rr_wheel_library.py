"""Read saved components and contextual assembly; scoped fit and geometry evidence."""
import bpy,bmesh,json,math,sys,hashlib
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
OUT=Path(sys.argv[sys.argv.index('--')+1]);SPEC=json.loads((OUT/'spec.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(OUT/'GT_RangeRover_Wheel_Components.blend'))
checks=[];stats={}
def check(name,ok,detail=None):checks.append({'name':name,'pass':bool(ok),'detail':detail})
def meshdata(obs,evaluated=True,transform=None):
    vs=[];fs=[];dg=bpy.context.evaluated_depsgraph_get()
    for o in obs:
        if o.type!='MESH':continue
        ev=o.evaluated_get(dg) if evaluated else o;me=ev.to_mesh() if evaluated else o.data
        mat=transform if transform is not None else Matrix.Identity(4)
        start=len(vs);vs += [mat@v.co for v in me.vertices];fs += [tuple(start+i for i in f.vertices) for f in me.polygons]
        if evaluated:ev.to_mesh_clear()
    return vs,fs
parts=[c for c in bpy.data.collections if c.get('kind') in ['rim','tyre']]
for c in parts:
    if c.name not in bpy.context.scene.collection.children:bpy.context.scene.collection.children.link(c)
bpy.context.view_layer.update()
check('Six independently appendable components',len(parts)==6)
rimdata={};tyredata={}
for c in parts:
    meshes=[o for o in c.objects if o.type=='MESH'];bad=[]
    for o in meshes:
        bm=bmesh.new();bm.from_mesh(o.data)
        bad_edges=sum(not e.is_manifold for e in bm.edges);zero=sum(f.calc_area()<1e-12 for f in bm.faces)
        if bad_edges or zero:bad.append({'object':o.name,'nonmanifold_edges':bad_edges,'zero_faces':zero})
        bm.free()
    check(c.name+' closed component meshes',not bad,bad)
    vv,ff=meshdata(meshes);tree=BVHTree.FromPolygons(vv,ff)
    radius=max(math.hypot(v.y,v.z) for v in vv);half=max(abs(v.x) for v in vv)
    stats[c.name]={'meshes':len(meshes),'evaluated_vertices':len(vv),'evaluated_faces':len(ff),'max_radius':radius,'half_width':half}
    check(c.name+' hub pivot at origin',all(o.location.length<1e-6 for o in c.objects if o.get('mount')))
    if c['kind']=='tyre':
        tyredata[c.name]=(vv,ff,tree)
        check(c.name+' common size envelope',abs(radius-SPEC['outer_radius_m'])<.001 and half<SPEC['width_m']/2+.001,{'radius':radius,'half_width':half})
        carcass=next(o for o in meshes if 'closed carcass' in o.name)
        cv,cf=meshdata([carcass]);ct=BVHTree.FromPolygons(cv,cf)
        tread=next(o for o in meshes if 'individually shaped tread' in o.name)
        # Each distinct tread block root must be embedded in the continuous carcass.
        missing=0
        for block in json.loads(tread['block_vertex_groups']):
            p=sum((tread.data.vertices[i].co for i in block[:len(block)//2]),Vector())/(len(block)//2)
            hit,normal,idx,dist=ct.find_nearest(p)
            if hit is None or (p-hit).dot(normal)>.0001:missing+=1
        check(c.name+' tread roots attached',missing==0,{'detached_roots':missing,'blocks':tread['block_count']})
    else:
        rimdata[c.name]=(vv,ff,tree)
        web=next(o for o in meshes if 'perforated dish' in o.name);wv,wf=meshdata([web]);wt=BVHTree.FromPolygons(wv,wf)
        count=c['vent_count'];r=.15 if 'Pressed' in c.name else .15 if 'Alloy' in c.name else .158
        misses=0
        for i in range(count):
            a=i*math.tau/count;hit=wt.ray_cast(Vector((.2,r*math.sin(a),r*math.cos(a))),Vector((-1,0,0)),.4)[0]
            if hit is not None:misses+=1
        check(c.name+' ventilation really open',misses==0,{'blocked':misses,'openings':count})
        check(c.name+' five lug nuts',sum('hex nut' in o.name for o in meshes)==5)
        hit=wt.ray_cast(Vector((.20,.074*math.sin(.15),.074*math.cos(.15))),Vector((-1,0,0)),.4)[0]
        check(c.name+' vent probe detects solid web control',hit is not None)
for rn,(rv,rf,rt) in rimdata.items():
    for tn,(tv,tf,tt) in tyredata.items():
        # Signed distance at each rim flange detects a gap; small bead overlap is intentional.
        gaps=[]
        for side in [-1,1]:
            for i in range(32):
                a=i*math.tau/32;d=Vector((0,math.sin(a),math.cos(a)))
                point=Vector((side*.099,0,0))+d*.221
                hit,normal,idx,dist=tt.find_nearest(point)
                if hit is None:gaps.append(999)
                else:gaps.append(max(0,(point-hit).dot(normal)))
        check(rn+' + '+tn+' bead closure',max(gaps)<.005,{'worst_radial_gap_m':max(gaps),'samples':64})
for tn,(tv,tf,tt) in tyredata.items():
    badpoint=Vector((.20,0,.221));hit,n,idx,dist=tt.find_nearest(badpoint)
    check(tn+' bead gap negative control',hit is not None and (badpoint-hit).dot(n)>.005)
check('Original Range Rover file preserved',hashlib.sha256(Path(SPEC['source']).read_bytes()).hexdigest()==SPEC['source_sha256'])
(OUT/'verification.json').write_text(json.dumps({'ok':all(c['pass'] for c in checks),'checks':checks,'statistics':stats,'scope':'Raw topology, evaluated envelopes, tread attachment, open vents, bead seating for all nine combinations; not runtime readiness.'},indent=2))

# Fit scene: all actual authored body geometry, plus source wheel baseline at same poses.
bpy.ops.wm.open_mainfile(filepath=str(OUT/'RangeRover_Wheel_Fit.blend'))
body=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.name.lower().startswith('wheel')]
def fingerprint(o):
    return hashlib.sha256(json.dumps({'vertices':[list(v.co) for v in o.data.vertices],
        'faces':[list(f.vertices) for f in o.data.polygons],'transform':[list(row) for row in o.matrix_basis]},sort_keys=True).encode()).hexdigest()
body_before={o.name:fingerprint(o) for o in body}
vs=[];fs=[]
for o in body:
    v,f=meshdata([o]);start=len(vs);vs += [o.matrix_world@p for p in v];fs += [tuple(start+k for k in face) for face in f]
bt=BVHTree.FromPolygons(vs,fs)
poses=[(0,0),(-30,0),(30,0),(0,.12),(0,-.16),(-30,.12),(30,.12)]
records=[]
sources=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.lower().startswith('wheel')]
for centre in SPEC['measured_hub_centres_m']:
    front=centre[1]<0
    for yaw,z in poses:
        if not front and yaw:continue
        rot=Matrix.Rotation(math.radians(yaw)+(math.pi if centre[0]<0 else 0),4,'Z')
        tr=Matrix.Translation(Vector(centre)+Vector((0,0,z)))@rot
        for name,(tv,tf,tt) in tyredata.items():
            tree=BVHTree.FromPolygons([tr@v for v in tv],tf)
            hits=tree.overlap(bt)
            records.append({'tyre':name,'centre':centre,'steer_deg':yaw,'bump_m':z,'surface_intersection_pairs':len(hits)})
        old=min(sources,key=lambda o:(sum((o.matrix_world@v.co for v in o.data.vertices),Vector())/len(o.data.vertices)-Vector(centre)).length)
        ov,of=meshdata([old])
        # Baseline rotation is relative to source world geometry, no side mirror needed.
        shift=Matrix.Translation(Vector(centre)+Vector((0,0,z)))@Matrix.Rotation(math.radians(yaw),4,'Z')@Matrix.Translation(-Vector(centre))
        tree=BVHTree.FromPolygons([shift@old.matrix_world@v for v in ov],of)
        records.append({'tyre':'SOURCE BASELINE','centre':centre,'steer_deg':yaw,'bump_m':z,'surface_intersection_pairs':len(tree.overlap(bt))})
with bpy.data.libraries.load(SPEC['source'],link=False) as (src,dst):
    original_names=[n for n in src.objects if n in body_before];dst.objects=list(original_names)
preservation={name:body_before[name]==fingerprint(o) for name,o in zip(original_names,dst.objects)}
assert len(preservation)==len(body_before) and all(preservation.values()),'Source body geometry or transforms changed'
(OUT/'fit-review.json').write_text(json.dumps({'records':records,'body_geometry_and_transforms_preserved':preservation,'scope':'Surface-intersection sampling against unchanged authored body. Neutral plus illustrative +/-30 degree steering, +120/-160 mm travel. Not Chaos kinematics or continuous swept certification. Baseline comparison included; counts depend on topology.'},indent=2))
print('VERIFICATION '+str(sum(c['pass'] for c in checks))+'/'+str(len(checks)),flush=True)
if not all(c['pass'] for c in checks):raise RuntimeError('See verification.json')
