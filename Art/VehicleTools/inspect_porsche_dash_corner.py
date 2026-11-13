import bpy,json
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath='C:/GrandTour/Art/Export/VehicleTools/porsche-completion-v04/Porsche_Safari_Review.blend')
out={}
for n in ['Porsche original body - locally repaired','Windscreen','Dashboard | continuous padded shell','Dashboard | windscreen-fitted scuttle pad']:
 ob=bpy.data.objects[n];inv=ob.matrix_world.inverted();origin=Vector((-.6,-.643,1.8 if n=='Windscreen' else 1.159));hit,p,no,i=ob.ray_cast(inv@origin,Vector((0,0,-1)))
 out[n]={'hit':hit,'point':list(ob.matrix_world@p),'verts':[list(ob.matrix_world@ob.data.vertices[j].co) for j in ob.data.polygons[i].vertices] if hit else []}
print(json.dumps(out))
