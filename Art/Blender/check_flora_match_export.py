import bpy,json
from pathlib import Path
OUT=Path('C:/GrandTour/Art/Export/LidarStudy/FloraMatch')

def inspect(o):
    used={i for p in o.data.polygons for i in p.vertices}
    colors={}
    ca=o.data.color_attributes.active_color
    if ca:
        for idx,m in enumerate(o.data.materials):
            vals=[ca.data[li].color[:3] for p in o.data.polygons if p.material_index==idx for li in p.loop_indices]
            if vals:colors[m.name]={'mean':[sum(c[k] for c in vals)/len(vals) for k in range(3)],'min':min(min(c) for c in vals),'max':max(max(c) for c in vals)}
    return {'name':o.name,'scale':list(o.scale),'location':list(o.location),'all':len(o.data.vertices),'used':len(used),
    'bounds_all':[[min(v.co[k] for v in o.data.vertices),max(v.co[k] for v in o.data.vertices)] for k in range(3)],
    'bounds_used':[[min(o.data.vertices[i].co[k] for i in used),max(o.data.vertices[i].co[k] for i in used)] for k in range(3)],
    'mat':[m.name for m in o.data.materials],'colors':colors}
rows=[inspect(o) for o in bpy.data.objects if o.type=='MESH']
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=str(OUT/'SM_Match_Tree_E_001.fbx'))
rows+=[inspect(o) for o in bpy.data.objects if o.type=='MESH']
(OUT/'roundtrip.json').write_text(json.dumps(rows,indent=2))
print(json.dumps(rows),flush=True)
