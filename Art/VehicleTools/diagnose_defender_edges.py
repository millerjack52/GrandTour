import bpy,bmesh
bpy.ops.wm.open_mainfile(filepath='C:/GrandTour/Art/Export/VehicleTools/defender-separated-v05/Defender_Separated.blend')
for o in bpy.data.objects:
 if o.type!='MESH' or o.name.startswith('SOURCE'):continue
 bm=bmesh.new();bm.from_mesh(o.data);bad=[e for e in bm.edges if len(e.link_faces)!=2]
 if bad:
  print(o.name,'bad',len(bad),'boundary',sum(e.is_boundary for e in bad),'nonmanifold',sum(len(e.link_faces)>2 for e in bad))
  if o.name.startswith('Door'):
   for e in bad[:20]:print('edge',e.index,'len',e.calc_length(),'faces',len(e.link_faces),'coords',[list(v.co) for v in e.verts])
 bm.free()
