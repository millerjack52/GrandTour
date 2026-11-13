import bpy,json
from pathlib import Path
bpy.ops.wm.open_mainfile(filepath='C:/GrandTour/Art/Export/VehicleTools/porsche-completion-v04/Porsche_Safari_Review.blend')
o=bpy.data.objects['Rear glass fitted surround'];N=238
rows=[]
for j in range(4):
 ps=[o.data.vertices[j*N+i].co for i in range(N)]
 rows.append({'row':j,'bounds':[[min(p[k] for p in ps) for k in range(3)],[max(p[k] for p in ps) for k in range(3)]],'top':[list(p) for p in ps if p.z>1.27]})
print(json.dumps(rows))
