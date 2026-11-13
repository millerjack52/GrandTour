import bpy,json
from pathlib import Path
P=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-authored-v01');bpy.ops.wm.open_mainfile(filepath=str(P/'Porsche_Safari_Complete.blend'))
r=json.loads((P/'validation-report.json').read_text())
for n in ['Body_FrontWing_L','Body_RearQuarter_L','Body_Cabin_side_1']:
 o=bpy.data.objects[n];o.data.calc_loop_triangles()
 for pair in r['self_intersections'].get(n,{}).get('samples',[])[:4]:
  print(n,[[[round(c/4.5,6) for c in o.data.vertices[i].co] for i in o.data.loop_triangles[t].vertices] for t in pair],flush=True)
