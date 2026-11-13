import bpy,json
from pathlib import Path
P=Path('C:/GrandTour/Art/Export/VehicleTools/ferrari288-good-game-v01');bpy.ops.wm.open_mainfile(filepath=str(P/'Ferrari288_GameRig.blend'));out={}
for o in bpy.data.collections['EXPORT | Unreal rig'].objects:
 if o.type!='MESH':continue
 m=o.data;bad=[p.index for p in m.polygons if p.area<1e-8];badn=sum(n.vector.length<.5 for n in m.corner_normals);uv=m.uv_layers[0]
 baduv=0
 for p in m.polygons:
  a,b,c=[uv.data[i].uv for i in list(p.loop_indices)[:3]];area=abs((b-a).cross(c-a));baduv+=area<1e-12
 out[o.name]={'triangles':len(m.polygons),'zero_area_faces':bad,'zero_normals':badn,'zero_area_uv':baduv}
(P/'mesh-health.json').write_text(json.dumps(out,indent=2));print(out)
