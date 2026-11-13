"""Scoped rear-lens extraction for the source-preserving Prado assembly.

Mutates only the passed Blender scene in memory. Does not save, render, or delete
files. Existing source cap coordinates remain unchanged. Source face IDs are
resolved by coordinates so unrelated window work can reindex the body safely.
"""
import json
from pathlib import Path
from collections import Counter
import bpy,bmesh,math
from mathutils import Vector

SOURCE_ISLANDS = Path('C:/GrandTour/Art/Export/VehicleTools/prado-source-v01/islands.json')
SOURCE_FACES = {
 'L':[1088,1089,1090,1091,1092,1093,1094,1097,1098,6682,6683,6684,6685,6686,6687,6696,6697,6698,6699,6700,6701,6702,6703,6704,6705,6706,6707,6708,6709,6710,6711,6712,6713,6724,6725,6726,6727,6728,6729,6767,6771,6782,6783,6784,6785,6786,6787,6788,6789,6790,6791,6792,6793,6794,6795,6796,6797,6798,6799,6800,6801,6802,6803,6804,6805,6810,6811,6812,6813,7412,7413,7416,7417,7464,7470,7471,7474,7475,7476,7477],
 'R':[462,463,464,465,466,467,474,475,476,3056,3057,3060,3061,3062,3063,3066,3067,3070,3071,3163,3165,3171,3178,3179,3180,3181,3182,3183,3188,3189,3190,3191,3192,3193,3194,3195,3196,3197,3198,3199,3200,3201,3202,3203,3204,3205,3206,3207,3208,3209,3210,3211,3212,3213,3218,3219,3220,3221,3252,3253,3254,3255,3256,3257,3258,3259,3260,3261,3262,3263,3960,3961,3985,3992,3993,3994,3995,3998,3999,4002,4003]}

def _key(points):
 return tuple(sorted(tuple(round(float(x),6) for x in p) for p in points))

# These partner triangles complete the three outer bevel quads. A centroid-only
# aperture filter misses them and creates triangular painted slivers in a lens.
SOURCE_FACES['L'].extend([6766,6770,7465])
SOURCE_FACES['R'].extend([3162,3170,3984])

def _material(name,color):
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name)
 m.diffuse_color=(*color,1);m.use_nodes=True
 p=m.node_tree.nodes.get('Principled BSDF')
 p.inputs['Base Color'].default_value=(*color,1)
 p.inputs['Metallic'].default_value=.0;p.inputs['Roughness'].default_value=.24
 p.inputs['Transmission Weight'].default_value=.08;p.inputs['IOR'].default_value=1.49
 p.inputs['Coat Weight'].default_value=.25;p.inputs['Coat Roughness'].default_value=.18
 p.inputs['Emission Strength'].default_value=0
 return m

def _copy_faces(obj, face_ids, name, materials=None, assignments=None):
 src=obj.data;fs=[src.polygons[i] for i in face_ids]
 ids=sorted({j for f in fs for j in f.vertices});remap={j:i for i,j in enumerate(ids)}
 verts=[tuple(src.vertices[j].co) for j in ids];faces=[[remap[j] for j in f.vertices] for f in fs]
 mesh=bpy.data.meshes.new(name+' mesh');mesh.from_pydata(verts,[],faces);mesh.update()
 for m in materials if materials is not None else list(src.materials):mesh.materials.append(m)
 normals=[tuple(src.corner_normals[l].vector) for f in fs for l in f.loop_indices]
 for k,(a,b) in enumerate(zip(mesh.polygons,fs)):
  a.use_smooth=b.use_smooth;a.material_index=assignments[k] if assignments is not None else b.material_index
 sharp={tuple(sorted(e.vertices)) for e in src.edges if e.use_edge_sharp}
 for e in mesh.edges:
  e.use_edge_sharp=tuple(sorted(ids[j] for j in e.vertices)) in sharp
 mesh.normals_split_custom_set(normals)
 return mesh

def repair_rear_lamps(scene=None, body_name='Prado | fixed shell and underbody', scale=5.0):
 scene=scene or bpy.context.scene
 assert not bpy.data.objects.get('LAMP | rear cluster L'),'Rear lamp repair already applied'
 body=bpy.data.objects[body_name]
 A=json.loads(SOURCE_ISLANDS.read_text());src=A[0]
 source_map={side:{_key([src['verts'][i] for i in src['polys'][f]]) for f in ids} for side,ids in SOURCE_FACES.items()}
 current={_key([(body.matrix_world@body.data.vertices[i].co)/scale for i in p.vertices]):p.index for p in body.data.polygons}
 missing={side:len(keys-set(current)) for side,keys in source_map.items()}
 assert not any(missing.values()),f'Rear cap source coordinates changed; re-audit before applying: {missing}'
 selected={side:sorted(current[k] for k in keys) for side,keys in source_map.items()}
 allids=set(i for ids in selected.values() for i in ids)
 col=bpy.data.collections.get('17 Rear lighting') or bpy.data.collections.new('17 Rear lighting')
 if col.name not in scene.collection.children:scene.collection.children.link(col)
 materials=[_material('Prado | rear red lens',(.53,.022,.012)),_material('Prado | rear amber lens',(.9,.265,.018)),_material('Prado | reverse lens',(.72,.78,.77))]
 manifest={'scope':'Source cap faces only; retained shape and perimeter; unlit colored plastic optics', 'source_component':0,'source_face_ids':SOURCE_FACES,'body_object':body.name,'source_vertices_moved':0,'new_objects':[],'limitations':['No lamp wiring, reflector optics, UVs, or active emission authored.','Rear color order is a stylized amber/red/clear interpretation; no exact model-year lighting reference supplied.']}
 for side,ids in selected.items():
  assignments=[]
  for i in ids:
   z=sum((body.matrix_world@body.data.vertices[j].co).z/scale for j in body.data.polygons[i].vertices)/len(body.data.polygons[i].vertices)
   assignments.append(2 if z<.2338867 else (0 if z<.258301 else 1))
  name='LAMP | rear cluster '+side
  mesh=_copy_faces(body,ids,name,materials,assignments)
  o=bpy.data.objects.new(name,mesh);col.objects.link(o);o.parent=body.parent;o.matrix_world=body.matrix_world.copy();o.color=materials[0].diffuse_color
  o['source_component']=0;o['source_face_ids']=json.dumps(SOURCE_FACES[side]);o['position_policy']='Exact source cap coordinates; old cap faces removed from body'
  # Body-weighted custom normals include adjacent quarter-panel faces; carrying
  # them to an extracted lens makes the small reverse band appear dented.
  mesh.normals_split_custom_set([(0,0,0)]*len(mesh.loops))
  bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
  for f in bm.faces:f.smooth=True
  for e in bm.edges:e.smooth=len(e.link_faces)==2 and e.calc_face_angle()<math.radians(30)
  bm.to_mesh(mesh);bm.free();mesh.update()
  normal=o.modifiers.new('Lens local surface normals','WEIGHTED_NORMAL');normal.keep_sharp=True;normal.weight=35
  sol=o.modifiers.new('Lens inward wall 1 mm','SOLIDIFY');sol.thickness=.001;sol.offset=-1;sol.use_even_offset=True
  counts=Counter(assignments)
  manifest['new_objects'].append({'name':name,'faces':len(ids),'bands':{'red':counts[0],'amber':counts[1],'reverse':counts[2]},'inward_thickness_m':.001})
 body.data=_copy_faces(body,[p.index for p in body.data.polygons if p.index not in allids],body.data.name+' without rear caps')
 # The broad formed bar directly above the rear glazing is source component 61.
 high=next((o for o in scene.objects if o.type=='MESH' and o.get('source_component')==61),None)
 if high is not None:
  ids=[]
  for p in high.data.polygons:
   c=sum((high.matrix_world@high.data.vertices[i].co for i in p.vertices),Vector())/len(p.vertices)/scale
   n=(high.matrix_world.to_3x3()@p.normal).normalized()
   if c.y>.387 and n.y>.60:ids.append(p.index)
  if ids:
   name='LAMP | high brake lens';mesh=_copy_faces(high,ids,name,[materials[0]],[0]*len(ids))
   o=bpy.data.objects.new(name,mesh);col.objects.link(o);o.parent=high.parent;o.matrix_world=high.matrix_world.copy();o.color=materials[0].diffuse_color
   sol=o.modifiers.new('Lens inward wall 1 mm','SOLIDIFY');sol.thickness=.001;sol.offset=-1
   old=set(ids);high.data=_copy_faces(high,[p.index for p in high.data.polygons if p.index not in old],high.data.name+' housing')
   manifest['new_objects'].append({'name':name,'source_component':61,'faces':len(ids),'inward_thickness_m':.001})
  else:manifest['limitations'].append('Source high brake bar found but no outward face matched; left unchanged.')
 return manifest
