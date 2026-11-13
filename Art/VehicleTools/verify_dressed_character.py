"""Saved-file checks: protected shapes, real apertures and selected static fit."""
import bpy,json,sys,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
out=Path(sys.argv[sys.argv.index('--')+1]);source=Path('C:/GrandTour/Art/Export/VehicleTools/shape-character-v03/Crafted_Utility_Character_Study.blend')
bpy.ops.wm.open_mainfile(filepath=str(source));bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();baseline={}
for cname in ['01 | Primary surfaces','02 | Cabin and openings','03 | Bumper profiles']:
    for ob in bpy.data.collections[cname].objects:
        if ob.type!='MESH' or ob.name.startswith('Body | shared'):continue
        eo=ob.evaluated_get(dg);me=eo.to_mesh();baseline[ob.name]=[v.co.copy() for v in me.vertices];eo.to_mesh_clear()
bpy.ops.wm.open_mainfile(filepath=str(out/'Crafted_Utility_Detailed.blend'));bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
checks={};displacement={}
repair_path=out/'repair-manifest.json'
repair=json.loads(repair_path.read_text()) if repair_path.exists() else {}
allowed=set(repair.get('protected_shape_exceptions',[]))|set(repair.get('removed_objects',[]))
for name,points in baseline.items():
    if name in allowed:continue
    ob=bpy.data.objects[name];assert len(points)==len(ob.data.vertices),name
    delta=max((v.co-pt).length for v,pt in zip(ob.data.vertices,points));assert delta<1e-7,(name,delta);displacement[name]=delta
checks['protected_shapes']={'object_count':len(displacement),'max_displacement_m':max(displacement.values())}
checks['authorized_local_repair_exceptions']=sorted(set(baseline)&allowed)
pres=json.loads((out/'preservation-checks.json').read_text());assert hashlib.sha256(source.read_bytes()).hexdigest()==pres['accepted_source_sha256'];checks['accepted_source_unchanged']=True

def rayclear(ob,origin,direction,distance):
    result=ob.ray_cast(Vector(origin),Vector(direction),distance=distance,depsgraph=dg)
    return not result[0]
apertures={}
for side,label in [(1,'L'),(-1,'R')]:
    for title in ['Front door','Rear door']:
        ob=bpy.data.objects[label+' | '+title+' derived skin']
        c=next(c for c in ob.users_collection if c.name==label+' | '+title)
        handle=next(o for o in c.objects if 'metal door release' in o.name)
        # Boxes use baked vertex positions and zero object transforms.
        centre=sum((v.co for v in handle.data.vertices),Vector())/len(handle.data.vertices)
        apertures[label+' '+title+' handle']=rayclear(ob,(side*1.2,centre.y,centre.z-.007),(-side,0,0),.5)
nose=bpy.data.objects['Front nose | derived closure skin'];carrier=bpy.data.objects['Fascia | dark inset carrier']
for x,label in [(0,'grille'),(.641,'left headlamp'),(-.641,'right headlamp')]:
    apertures['nose '+label]=rayclear(nose,(x,-2.4,.888),(0,1,0),.6)
    apertures['carrier '+label]=rayclear(carrier,(x,-2.4,.888),(0,1,0),.6)
tail=bpy.data.objects['Rear tailgate | derived closure skin']
for x,z,label in [(0,.905,'plate'),(.81,.892,'left lamp'),(-.81,.892,'right lamp')]:apertures['rear '+label]=rayclear(tail,(x,2.55,z),(0,-1,0),.65)
checks['real_apertures']=apertures
assert all(apertures.values()),apertures

def geom(ob):
    eo=ob.evaluated_get(dg);me=eo.to_mesh();verts=[ob.matrix_world@v.co for v in me.vertices];polys=[tuple(p.vertices) for p in me.polygons];eo.to_mesh_clear();return verts,polys
def bvh(ob):
    vs,ps=geom(ob);return BVHTree.FromPolygons(vs,ps,all_triangles=False)
skins=[o for o in bpy.context.scene.objects if o.type=='MESH' and ('derived skin' in o.name or 'narrow lip' in o.name or 'inner well' in o.name or 'recessed backing' in o.name)]
tyres=[o for o in bpy.context.scene.objects if o.type=='MESH' and (o.name.startswith('Tyre | shaped carcass') or o.name.startswith('Tyre | staggered tread'))]
skinbvhs={o.name:bvh(o) for o in skins};collisions=[];envelopes=[]
for ob in tyres:
    bv=bvh(ob);vs,ps=geom(ob);cy=ob.parent.location.y;cz=ob.parent.location.z
    radial=max(((v.y-cy)**2+(v.z-cz)**2)**.5 for v in vs);envelopes.append({'object':ob.name,'outer_radius_m':radial})
    assert radial<=.392*1.007+.003,(ob.name,radial)
    for skin in skins:
        if bv.overlap(skinbvhs[skin.name]):collisions.append([ob.name,skin.name])
checks['tyre_body_surface_intersections']=collisions;checks['tyre_envelopes']=envelopes
assert not collisions,collisions

# Interior/exterior surface intersection evidence catches intrusion through glass.
glass=[o for o in bpy.data.collections['02 | Cabin and openings'].objects if 'opening' in o.name]
glass_bvhs={o.name:bvh(o) for o in glass};intrusions=[]
for c in bpy.data.collections:
    if not c.name.startswith('Cabin |'):continue
    for ob in c.objects:
        if ob.type!='MESH':continue
        bv=bvh(ob)
        for gl in glass:
            if bv.overlap(glass_bvhs[gl.name]):intrusions.append([ob.name,gl.name])
checks['cockpit_glass_surface_intersections']=intrusions
assert not intrusions,intrusions
checks['scope']='Static tyre/body and cockpit/glass surface intersections plus selected apertures. Not exhaustive collision, motion, ergonomics or game-ready validation.'
(out/'saved-assembly-checks.json').write_text(json.dumps(checks,indent=2));print('DRESSED_SAVED_CHECKS_PASSED',flush=True)
