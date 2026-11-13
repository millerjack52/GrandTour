"""Low-cost shoulder forms; purchased ground colour/normal textures assigned in Unreal."""
import bpy,sys,math,json
from pathlib import Path
sys.path.insert(0,'C:/GrandTour/Art/tools')
from flora_drive_ground import MOUNDS,ground_height,surround_height
O=Path('C:/GrandTour/Art/Export/FloraDrive')
bpy.ops.wm.read_factory_settings(use_empty=True)
verts=[];faces=[]
for x,y,rx,ry,h in MOUNDS:
    start=len(verts);verts.append((x/100,-y/100,h/100))
    for ring in range(1,9):
        for j in range(24):
            a=j*math.tau/24;r=ring/8
            xx=x+rx*r*math.cos(a);yy=y+ry*r*math.sin(a)
            verts.append((xx/100,-yy/100,(ground_height(xx,yy)-.8)/100))
    for j in range(24):faces.append((start,start+1+(j+1)%24,start+1+j))
    for ring in range(7):
        for j in range(24):
            a=start+1+ring*24+j;b=start+1+ring*24+(j+1)%24
            faces.extend([(a,b,b+24),(a,b+24,a+24)])
mesh=bpy.data.meshes.new('ForestFloorForms');mesh.from_pydata(verts,[],faces);mesh.update()
obj=bpy.data.objects.new('SM_FloraFloorForms',mesh);bpy.context.collection.objects.link(obj)
for p in mesh.polygons:p.use_smooth=True
bpy.context.view_layer.objects.active=obj;obj.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(O/'SM_FloraFloorForms.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,bake_anim=False)
(O/'ground-geometry.json').write_text(json.dumps({'mounds':len(MOUNDS),'triangles':len(faces),'max_height_cm':max(m[4] for m in MOUNDS),'collision':'none; shoulders only'},indent=2))
# A low-poly, uneven forest backdrop starts outside the 63 m simulated square.
obj.select_set(False);verts=[];faces=[];segments=128;rings=24
for ring in range(rings+1):
    for j in range(segments):
        a=math.tau*j/segments;c=math.cos(a);s=math.sin(a)
        inner=3150/max(abs(c),abs(s));radius=inner+(12500-inner)*ring/rings
        x=radius*c;y=radius*s;verts.append((x/100,-y/100,(surround_height(x,y)-35)/100))
for ring in range(rings):
    for j in range(segments):
        a=ring*segments+j;b=ring*segments+(j+1)%segments
        faces.extend([(a,b,b+segments),(a,b+segments,a+segments)])
mesh=bpy.data.meshes.new('ForestSurround');mesh.from_pydata(verts,[],faces);mesh.update()
obj=bpy.data.objects.new('SM_ForestSurround',mesh);bpy.context.collection.objects.link(obj)
for p in mesh.polygons:p.use_smooth=True
bpy.context.view_layer.objects.active=obj;obj.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(O/'SM_ForestSurround.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,bake_anim=False)
(O/'surround-geometry.json').write_text(json.dumps({'triangles':len(faces),'outer_radius_m':125,'inner_square_m':63,'collision':'complex as simple; static background'},indent=2))
