"""Reopen and check only the stated static construction properties."""
import bpy,bmesh,json,sys,math,argparse
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
p=argparse.ArgumentParser();p.add_argument('--folder',required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);folder=Path(a.folder)
bpy.ops.wm.open_mainfile(filepath=str(folder/'Crafted_Utility.blend'))
dg=bpy.context.evaluated_depsgraph_get();cache={}
def tree(ob):
    if ob.name not in cache:
        eo=ob.evaluated_get(dg);me=eo.to_mesh()
        cache[ob.name]=BVHTree.FromPolygons([ob.matrix_world@v.co for v in me.vertices],[tuple(p.vertices) for p in me.polygons])
        eo.to_mesh_clear()
    return cache[ob.name]
tires=[o for o in bpy.context.scene.objects if o.type=='MESH' and (o.name.startswith('Tyre | shaped carcass') or o.name.startswith('Tyre | staggered tread blocks'))]
obstacles=[o for o in bpy.context.scene.objects if o.type=='MESH' and any(x in o.name for x in ['formed closed skin','Narrow rolled arch lip','Wheelhouse |','rear mudflap','Floor |','Door | interior card'])]
intersections=[]
for tire in tires:
    for body in obstacles:
        hit=tree(tire).overlap(tree(body))
        if hit:intersections.append(dict(tyre=tire.name,body=body.name,overlapping_triangle_pairs=len(hit)))
wheel_collections=[c for c in bpy.data.collections if c.name.startswith('CU ') and '| Wheel' in c.name]
mounts=[]
for c in wheel_collections:
    root=next(o for o in c.objects if o.get('mount'));mounts.append(dict(collection=c.name,center=list(root.location),scale=list(root.scale)))
imgs=[i for i in bpy.data.images if i.packed_file]
report=dict(reopened_file=str(folder/'Crafted_Utility.blend'),wheel_mounts=mounts,
    tyre_obstacle_surface_intersections=intersections,packed_reference_images=[i.name for i in imgs],
    checks=dict(four_wheel_mounts=len(mounts)==4,tyre_skin_arch_liner_mudflap_surface_clear=not intersections,reference_packed=bool(imgs)),
    limitation='Checks static tyre surfaces against skins, arch lips, liners, mudflaps, floor and door cards. Not a full vehicle collision, containment, moving clearance or runtime validation.')
(folder/'saved-assembly-check.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2),flush=True)
