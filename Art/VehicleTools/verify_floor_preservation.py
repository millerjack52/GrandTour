import bpy,sys,json,hashlib
from pathlib import Path
from mathutils import Vector
out=Path(sys.argv[sys.argv.index('--')+1]);M=json.loads((out/'floor-repair-manifest.json').read_text());source=Path(M['source'])
assert hashlib.sha256(source.read_bytes()).hexdigest()==M['source_sha256']
bpy.ops.wm.open_mainfile(filepath=str(source));bpy.context.view_layer.update()
baseline={o.name:([tuple(v.co) for v in o.data.vertices],[list(r) for r in o.matrix_world]) for o in bpy.context.scene.objects if o.type=='MESH' and o.name not in M['removed_objects']}
bpy.ops.wm.open_mainfile(filepath=str(out/'Crafted_Utility_Detailed.blend'));bpy.context.view_layer.update()
for name,(points,matrix) in baseline.items():
    o=bpy.data.objects[name];assert len(points)==len(o.data.vertices),name
    assert max((Vector(p)-v.co).length for p,v in zip(points,o.data.vertices))<1e-7,name
    assert max(abs(o.matrix_world[i][j]-matrix[i][j]) for i in range(4) for j in range(4))<1e-7,name
result={'passed':True,'source_file_unchanged':True,'unaffected_meshes_and_transforms_unchanged':len(baseline),'scope':'Every original mesh except the two replaced floor panels.'}
(out/'saved-floor-preservation.json').write_text(json.dumps(result,indent=2));print(result)
