import bpy,json
from pathlib import Path
bpy.ops.wm.open_mainfile(filepath='C:/GrandTour/Art/Export/VehicleTools/pathfinder-exterior-v01/Pathfinder_Exterior.blend')
hood=bpy.data.objects['Bonnet | rolled nose and broad shoulders']
print('HOOD_FIRST',json.dumps([list(v.co) for v in list(hood.data.vertices)[:11]]))
cap=bpy.data.objects['Front | wraparound fascia']
print('CAP_TOP',json.dumps(sorted([list(v.co) for v in cap.data.vertices if v.co.z>.985],key=lambda p:p[0])))
