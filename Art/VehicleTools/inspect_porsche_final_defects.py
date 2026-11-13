import bpy,bmesh,json
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath='C:/GrandTour/Art/Export/VehicleTools/porsche-preserved-repair-v02/Porsche_Preserved_Repair.blend')
o=bpy.data.objects['Porsche original body - locally repaired'];bm=bmesh.new();bm.from_mesh(o.data)
print('BAD_EDGES',json.dumps([{'co':[list(v.co) for v in e.verts],'faces':[{'area':f.calc_area(),'n':list(f.normal)} for f in e.link_faces]} for e in bm.edges if len(e.link_faces)>2]))
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));print('AFTER_RECALC',sum(e.is_manifold and not e.is_contiguous for e in bm.edges))
for name in ['Headlamp_L','Headlamp_R']:
 o=bpy.data.objects[name];print(name,json.dumps({'v':[list(o.matrix_world@v.co) for v in o.data.vertices],'f':[list(f.vertices) for f in o.data.polygons]}))
for o in bpy.data.collections['Porsche - repaired original components'].objects:
 if o.type!='MESH':continue
 ps=[o.matrix_world@v.co for v in o.data.vertices];c=sum(ps,Vector())/len(ps)
 if min((c-Vector((s*.71,-1.81,.82))).length for s in [-1,1])<.2:print('RIGHT_LAMP',o.name,o.get('source_island'),list(c))
