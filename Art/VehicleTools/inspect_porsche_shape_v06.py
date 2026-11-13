import bpy,sys,json,numpy as np
from pathlib import Path
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools/vendor_geometry')
from shapely.geometry import MultiPoint
bpy.ops.wm.open_mainfile(filepath='C:/GrandTour/Art/Export/VehicleTools/porsche-preserved-repair-v02/Porsche_Preserved_Repair.blend')
out={}
for n in ['Windscreen','Rear glass','Door glass L','Quarter glass L','Vent glass L']:
 o=bpy.data.objects[n];ps=[o.matrix_world@v.co for v in o.data.vertices];ax=(0,2) if n in ['Windscreen','Rear glass'] else (1,2);p=MultiPoint([(v[ax[0]],v[ax[1]]) for v in ps]).convex_hull.simplify(.004)
 out[n]={'outline':list(p.exterior.coords),'bounds':[[min(v[k] for v in ps),max(v[k] for v in ps)] for k in range(3)]}
 if n=='Windscreen':
  a=np.array([[1,p.z,p.x*p.x,p.x*p.x*p.z] for p in ps]);c=np.linalg.lstsq(a,[p.y for p in ps],rcond=None)[0];out[n]['ruled_fit']=c.tolist()
print(json.dumps(out,indent=2),flush=True)
Path('C:/GrandTour/Art/VehicleTools/porsche-v02-window-measurements.json').write_text(json.dumps(out,indent=2))
