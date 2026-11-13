"""Ensure the local repair did not change unrelated meshes or their world poses."""
import bpy,json,sys,hashlib
from pathlib import Path
from mathutils import Vector
out=Path(sys.argv[sys.argv.index('--')+1]);manifest=json.loads((out/'repair-manifest.json').read_text());src=Path(manifest['source'])
assert hashlib.sha256(src.read_bytes()).hexdigest()==manifest['source_sha256']
bpy.ops.wm.open_mainfile(filepath=str(src));baseline={}
excluded=set(manifest['changed_objects'])|set(manifest['removed_objects'])
for ob in bpy.context.scene.objects:
    if ob.type=='MESH' and ob.name not in excluded:
        baseline[ob.name]=([tuple(v.co) for v in ob.data.vertices],[tuple(r) for r in ob.matrix_world])
bpy.ops.wm.open_mainfile(filepath=str(out/'Crafted_Utility_Detailed.blend'));bpy.context.view_layer.update();maximum=0
for name,(points,transform) in baseline.items():
    ob=bpy.data.objects[name];assert len(ob.data.vertices)==len(points),name
    delta=max((v.co-Vector(pt)).length for v,pt in zip(ob.data.vertices,points));maximum=max(maximum,delta);assert delta<1e-7,(name,delta)
    assert max(abs(ob.matrix_world[i][j]-transform[i][j]) for i in range(4) for j in range(4))<1e-7,name
report={'unchanged_source_file':True,'unchanged_meshes_and_world_transforms':len(baseline),'max_vertex_displacement_m':maximum,'intentional_changed_or_replaced_objects':sorted(excluded),'scope':'All pre-existing scene meshes outside the explicit repair list retain their local vertices and world transforms.'}
(out/'repair-preservation-checks.json').write_text(json.dumps(report,indent=2));print('TIDY_PRESERVATION_PASSED',len(baseline))
