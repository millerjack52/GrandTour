import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector
P=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-cleanup-v01')
bpy.ops.wm.open_mainfile(filepath=str(P/'Porsche_Assembly.blend'))
o=bpy.data.objects['Body_and_cabin'];bm=bmesh.new();bm.from_mesh(o.data)
sc=bpy.context.scene;cam=sc.camera
m=bpy.data.materials.new('Window selection');m.diffuse_color=(1,.015,.01,1);o.data.materials.append(m)
selected=[]
for f in bm.faces:
 p=f.calc_center_median()/4.5;x,y,z=p;n=f.normal;area=f.calc_area()/4.5**2
 wind=abs(x)<.153 and -.175<y<-.044 and .242<z<.329 and abs(n.dot(Vector((0,-.6,.8))))>.82 and area>.00006
 rear=abs(x)<.135 and .19<y<.36 and .248<z<.327 and abs(n.dot(Vector((0,.6,.8))))>.85 and area>.00006
 side=abs(x)>.12 and .10<y<.25 and .242<z<.327 and abs(n.x)>.65 and area>.00009
 if wind or rear or side:f.material_index=len(o.data.materials)-1;selected.append({'i':f.index,'p':list(p),'a':area,'normal':list(n),'which':'wind' if wind else 'rear' if rear else 'quarter'})
bm.to_mesh(o.data);bm.free();(P/'glass-selection.json').write_text(json.dumps(selected,indent=2))
sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.color_type='MATERIAL'
sc.render.resolution_x=1400;sc.render.resolution_y=1000
for name,pos in [('glass-front',(5.4,-7.2,4.5)),('glass-side',(5.4,0,1)),('glass-rear',(5,7,4))]:
 cam.location=pos;cam.rotation_euler=(Vector((0,0,.85))-cam.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(P/(name+'.png'));bpy.ops.render.render(write_still=True)
print('SELECTED',len(selected))
