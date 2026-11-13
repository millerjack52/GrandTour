"""Package reusable grass prototypes without loading the assembled scene."""
from pathlib import Path
import bpy,json
from io_scene_fbx import parse_fbx
root=Path(__file__).resolve().parents[2]
out=root/'Art/Export/RoadFordStyle'
with bpy.data.libraries.load(str(out/'RoadFordStyle.blend'),link=False) as (src,dst):
    dst.objects=[name for name in src.objects if name.startswith('SM_RF_GrassCarpet')]
assert len(dst.objects)==20
manifest=json.loads((out/'manifest.json').read_text())
metrics=[]
for ob in dst.objects:
    ob.data.calc_loop_triangles()
    expected={'Mat':88,'Tuft':90,'Swept':100,'Seed':98}
    form=ob.name.split('_')[3]
    assert len(ob.data.loop_triangles)==expected[form]
    assert len(ob.data.materials)==1
    ca=ob.data.color_attributes['Color']
    assert max(c.color[3] for c in ca.data)<.70
    fbx,_=parse_fbx.parse(str(out/(ob.name+'.fbx')))
    def walk(node):
        yield node
        for child in node.elems: yield from walk(child)
    raw=next(n.props[0] for n in walk(fbx) if n.id==b'Colors')
    exported={tuple(round(v,5) for v in raw[i:i+4]) for i in range(0,len(raw),4)}
    authored={tuple(round(v,5) for v in c.color) for c in ca.data}
    assert exported==authored,(ob.name,'FBX vertex colours differ from linear authored values')
    metrics.append(dict(name=ob.name,triangles=len(ob.data.loop_triangles),material_slots=1,fbx_linear_colors_verified=True))
bpy.data.libraries.write(str(out/'GrassCoverage.blend'),set(dst.objects),fake_user=True)
(out/'grass-library-validation.json').write_text(json.dumps(metrics,indent=2))
print('GRASS_LIBRARY_OK '+json.dumps(metrics))
