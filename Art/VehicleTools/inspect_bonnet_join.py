import bpy,json,bmesh
from mathutils.bvhtree import BVHTree
bpy.ops.wm.open_mainfile(filepath='C:/GrandTour/Art/Export/VehicleTools/pathfinder-bonnet-wheels-v01/Pathfinder_Bonnet_Wheels.blend')
skin=next(o for o in bpy.context.scene.objects if 'shared body skin' in o.name and max(v.co.x for v in o.data.vertices)>0)
tree=BVHTree.FromPolygons([v.co for v in skin.data.vertices],[tuple(p.vertices) for p in skin.data.polygons])
o=bpy.data.objects['Left | fitted front wing top'];rows=[]
for i in range(8,len(o.data.vertices),9):
 v=o.data.vertices[i].co;p,n,idx,d=tree.find_nearest(v);rows.append({'v':list(v),'near':list(p),'d':d})
print('SKIN',skin.name,[(m.name,m.type) for m in skin.modifiers]);print('WING',[(m.name,m.type,getattr(m,'offset',None)) for m in o.modifiers]);print(json.dumps(sorted(rows,key=lambda r:-r['d'])[:12]))
print('TOP SKIN',sorted(set(tuple(v.co) for v in skin.data.vertices if v.co.z>.95 and v.co.y<-.7),key=lambda v:v[1])[:100])
bm=bmesh.new();bm.from_mesh(skin.data);edges=[e for e in bm.edges if e.is_boundary and all(v.co.z>.98 and -1.96<v.co.y<-.9 for v in e.verts)]
print('BOUNDARIES',[[list(v.co) for v in e.verts] for e in edges][:60])
