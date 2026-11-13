"""Bake read-only authoring files into modular, centimetre/+X-front FBX packages.

Run in background Blender. Sources are never saved. The manifest retains source
object membership, material values, pivots, bounds and hashes for import checks.
"""
import bpy, json, re, math, hashlib
from pathlib import Path
from mathutils import Matrix, Vector

ROOT=Path('C:/GrandTour/Art/Export/VehicleTools')
OUT=ROOT/'new-cars-unreal-v01'
FILES={
 'CraftedUtility': ROOT/'crafted-character-detailed-v06/Crafted_Utility_Detailed.blend',
 'Pathfinder2002': ROOT/'pathfinder-articulation-v08/Pathfinder_Articulation.blend',
 'Impreza2003': ROOT/'impreza-ortho-full-v08/Impreza_Orthographic_Rebuild.blend',
}
def clean(s): return re.sub('[^A-Za-z0-9_]+','_',s).strip('_')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def unreal_point(p): return [-p[1]*100,-p[0]*100,p[2]*100]
def bounds(points): return [[min(p[i] for p in points) for i in range(3)],[max(p[i] for p in points) for i in range(3)]]
def export(car,path):
 before=sha(path)
 bpy.ops.wm.open_mainfile(filepath=str(path))
 scene=bpy.context.scene
 scene.frame_set(1)
 ctrl=bpy.data.objects.get('GT | Pathfinder controls')
 membership={}; pivots={}
 if ctrl:
  for k in ['left_front_door','right_front_door','left_rear_door','right_rear_door','steer','roll']: ctrl[k]=0.0
  for g,names in json.loads(ctrl['groups']).items():
   for n in names: membership[n]=clean(g)
   pivot=bpy.data.objects.get('Hinge | '+g) or bpy.data.objects.get('Roll | '+g)
   if pivot: pivots[clean(g)]=pivot.matrix_world.translation.copy()
 bpy.context.view_layer.update()
 sources=[]; excluded=[]
 for o in list(scene.objects):
  cols=[c.name for c in o.users_collection]
  excluded_col=any(c.hide_render or re.search('studio|fixed.*(camera|view)|reference|section evidence|wheel prox',c.name,re.I) for c in o.users_collection)
  if o.type not in {'MESH','CURVE','FONT','SURFACE'} or o.hide_render or excluded_col or o.name.startswith('TRACE'):
   excluded.append(o.name); continue
  sources.append(o)
 def group(o):
  cs=' '.join(c.name for c in o.users_collection)
  if o.name in membership:return membership[o.name]
  ag=str(o.get('assembly_group',''))
  if 'wheel' in ag:
   pivots[clean(ag)]=Vector((.805 if ag.startswith('L') else -.805,-1.2675 if 'front' in ag else 1.2675,.3575))
   return clean(ag)
  if 'Detailed wheel' in cs:
   c=next(c for c in o.users_collection if 'Detailed wheel' in c.name)
   key=clean(c.name); pivots[key]=bpy.data.objects[c.name+' | mount'].matrix_world.translation.copy();return key
  if re.search('Cabin|cockpit|seats|lining',cs,re.I):return 'Cabin'
  if re.search('floor|underside|wheelhouse',cs,re.I):return 'Underbody'
  if re.search('Front door|Rear door',cs):return clean(next(c.name for c in o.users_collection if 'door' in c.name))
  if 'door' in ag:return clean(ag)
  if re.search('lights|optics|lighting|Headlamp',cs,re.I):return 'Lighting'
  if re.search('trim|Glazing|fixtures',cs,re.I):return 'ExteriorTrim'
  if 'Rally' in cs:return 'RallyEquipment'
  return 'Body'
 groups={}; material_specs={}
 used_mats={m for o in sources for m in o.data.materials if m}
 for m in sorted(used_mats,key=lambda m:m.name):
  original=m.name; name='M_'+car+'_'+clean(original)
  p=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None) if m.node_tree else None
  def val(k,default):return p.inputs[k].default_value if p and k in p.inputs else default
  linked=[i.name for i in p.inputs if i.is_linked] if p else []
  assert not linked,(original,'Linked shader inputs require baking',linked)
  material_specs[name]=dict(source=original,base_color=list(val('Base Color',m.diffuse_color)),roughness=float(val('Roughness',.5)),metallic=float(val('Metallic',0)),specular=float(val('Specular IOR Level',.5)),transmission=float(val('Transmission Weight',0)),alpha=float(val('Alpha',1)),emission=list(val('Emission Color',[0,0,0,1])),emission_strength=float(val('Emission Strength',0)))
  m.name=name
 dg=bpy.context.evaluated_depsgraph_get()
 col=bpy.data.collections.new('EXPORT_ONLY');scene.collection.children.link(col)
 all_points=[]
 for o in sources:
  g=group(o); ev=o.evaluated_get(dg)
  mesh=bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=True,depsgraph=dg)
  if not mesh.polygons:continue
  mesh.transform(ev.matrix_world)
  all_points.extend([unreal_point(v.co) for v in mesh.vertices])
  copy=bpy.data.objects.new('EXPORT_'+o.name,mesh);col.objects.link(copy)
  groups.setdefault(g,[]).append((copy,o.name))
 # Deselect the complete source scene, including objects excluded from the view layer.
 for o in bpy.context.view_layer.objects:o.select_set(False)
 scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.01
 transform=Matrix.Scale(100,4)@Matrix.Rotation(math.pi/2,4,'Z')
 package=OUT/car;package.mkdir(parents=True,exist_ok=True)
 report=dict(car=car,source=str(path),source_sha256=before,axis='centimetres, +X forward, -Y left, +Z up',bounds_cm=bounds(all_points),materials=material_specs,parts=[],excluded=excluded,static_only=True)
 for g,entries in sorted(groups.items()):
  for o in bpy.context.selected_objects:o.select_set(False)
  for o,_ in entries:o.select_set(True)
  bpy.context.view_layer.objects.active=entries[0][0]
  bpy.ops.object.join()
  o=bpy.context.object; o.name='SM_'+car+'_'+g
  pivot=pivots.get(g,Vector((0,0,0)))
  o.data.transform(transform@Matrix.Translation(-pivot))
  # Explicit triangulation keeps the Unreal surface identical to evaluated Blender.
  mod=o.modifiers.new('Export triangulation','TRIANGULATE');mod.keep_custom_normals=True
  bpy.ops.object.modifier_apply(modifier=mod.name)
  old=list(o.data.materials);used=sorted({p.material_index for p in o.data.polygons})
  new=[]
  for idx in used:
   m=old[idx] if idx<len(old) else None
   if m is None:
    name='M_'+car+'_DefaultSurface'
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material_specs[name]=dict(source='Unassigned Blender surface',base_color=[.8,.8,.8,1],roughness=.5,metallic=0,specular=.5,transmission=0,alpha=1,emission=[0,0,0,1],emission_strength=0)
   new.append(m)
  mapping={idx:i for i,idx in enumerate(used)}
  indices=[mapping[p.material_index] for p in o.data.polygons]
  o.data.materials.clear()
  for m in new:o.data.materials.append(m)
  for p,i in zip(o.data.polygons,indices):p.material_index=i
  pts=[unreal_point(Vector((0,0,0)))] if not o.data.vertices else [[v.co.x,-v.co.y,v.co.z] for v in o.data.vertices]
  filename=package/(o.name+'.fbx')
  bpy.ops.export_scene.fbx(filepath=str(filename),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',bake_space_transform=False,use_mesh_modifiers=True,mesh_smooth_type='FACE',use_tspace=False,bake_anim=False,path_mode='AUTO',use_custom_props=False)
  report['parts'].append(dict(name=o.name,file=str(filename),group=g,source_objects=[n for _,n in entries],pivot_cm=unreal_point(pivot),bounds_local_cm=bounds(pts),triangles=len(o.data.polygons),vertices=len(o.data.vertices),materials=[m.name for m in o.data.materials],sha256=sha(filename)))
 assert sha(path)==before,'Source changed'
 report['triangles']=sum(p['triangles'] for p in report['parts'])
 (package/'manifest.json').write_text(json.dumps(report,indent=2))
 print('EXPORTED',car,len(sources),'source components;',len(groups),'parts;',report['triangles'],'triangles;',report['bounds_cm'])
 return report
if __name__=='__main__':
 assert bpy.app.background,'Background-only: never modify a working Blender session'
 OUT.mkdir(exist_ok=True)
 reports=[export(car,path) for car,path in FILES.items()]
 (OUT/'export-report.json').write_text(json.dumps([dict(car=r['car'],parts=len(r['parts']),triangles=r['triangles'],bounds_cm=r['bounds_cm'],source_sha256=r['source_sha256']) for r in reports],indent=2))
