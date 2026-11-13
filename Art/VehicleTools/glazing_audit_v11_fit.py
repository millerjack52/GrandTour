import bpy,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path('C:/GrandTour/Art/Export/VehicleTools/prado-glazing-v11');O=P.parent/'prado-glazing-audit';bpy.ops.wm.open_mainfile(filepath=str(P/'Prado_Corrected.blend'))
def tree(obs):
 v=[];f=[]
 for ob in obs:
  k=len(v);v.extend(ob.matrix_world@x.co for x in ob.data.vertices);f.extend([k+i for i in p.vertices] for p in ob.data.polygons)
 return BVHTree.FromPolygons(v,f)
bodytree=tree([ob for ob in bpy.context.scene.objects if ob.type=='MESH' and (ob.name.startswith('Door |') or ob.name=='Prado | fixed shell and underbody')])
rep={}
for mode,file,key,patchname in [('front','windscreen-corner-repair-contract.json','outer_ring','Windscreen | fitted painted surround'),('rear','repair-contract.json','rear_outer_ring',None)]:
 data=json.loads((O/file).read_text());ring=[Vector(p['co'])*5 for p in data[key]]
 candidates=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name==patchname] if patchname else [o for o in bpy.context.scene.objects if o.type=='MESH' and 'rear' in o.name.lower() and any(k in o.name.lower() for k in ['seal','surround','reveal'])]
 print(mode,'PATCH', [o.name for o in candidates]);ptree=tree(candidates)
 samples=[a.lerp(b,j/10) for a,b in zip(ring,ring[1:]+ring[:1]) for j in range(10)]
 bd=[bodytree.find_nearest(p)[3]*1000 for p in samples];pd=[ptree.find_nearest(p)[3]*1000 for p in samples]
 rep[mode]={'samples':len(samples),'original_shared_boundary_max_body_distance_mm':max(bd),'replacement_edge_max_distance_mm':max(pd),'body_worst_sample_m':list(samples[bd.index(max(bd))])}
(O/'v11-boundary-fit.json').write_text(json.dumps(rep,indent=2));print(json.dumps(rep,indent=2))
