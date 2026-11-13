"""Independent saved-file checks for the exterior study, not a game-ready stamp."""
import bpy,bmesh,json,sys
from pathlib import Path
from mathutils.bvhtree import BVHTree
path=Path(sys.argv[sys.argv.index('--')+1])
bpy.ops.wm.open_mainfile(filepath=str(path))
names=['Bonnet','Door_FL','Door_FR','Door_RL','Door_RR','Tailgate']
dg=bpy.context.evaluated_depsgraph_get();report={'source':str(path),'evaluated_panels':{},'panel_pair_intersections':{}}
trees={}
for name in names:
 ob=bpy.data.objects[name];evaluated=ob.evaluated_get(dg);me=evaluated.to_mesh()
 bm=bmesh.new();bm.from_mesh(me)
 data={'vertices':len(bm.verts),'faces':len(bm.faces),'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'loose_vertices':sum(not v.link_faces for v in bm.verts),'volume_m3':bm.calc_volume(signed=False)}
 report['evaluated_panels'][name]=data
 trees[name]=BVHTree.FromPolygons([ob.matrix_world@v.co for v in me.vertices],[list(p.vertices) for p in me.polygons],epsilon=0)
 bm.free();evaluated.to_mesh_clear()
for i,a in enumerate(names):
 for b in names[i+1:]:
  n=len(trees[a].overlap(trees[b]));report['panel_pair_intersections'][a+' / '+b]=n
report['ok']=all(d['boundary_edges']==0 and d['nonmanifold_edges']==0 and d['loose_vertices']==0 and d['volume_m3']>0 for d in report['evaluated_panels'].values()) and not any(report['panel_pair_intersections'].values())
report['limits']='Only the six closed panel skins and their mutual intersections are checked. Does not validate complete assembly, hinge travel, cockpit, UVs, rig or Unreal.'
(path.parent/'saved_file_fit_check.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
