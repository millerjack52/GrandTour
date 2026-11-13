"""Lossless indexed shader audit of the purchased Eevee source, without saving it."""
import bpy,json,hashlib,traceback
from pathlib import Path
R=Path('C:/GrandTour');O=R/'Art/Export/LidarStudy/FloraParity';O.mkdir(parents=True,exist_ok=True)
S=Path('D:/GrandTourAssets/FlippedNormals/Flora_Paint_Bonus_Project_Files/Bonus_Project_Files/001/001.blend')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def val(v):
 if isinstance(v,(str,bool,int,float)) or v is None:return v
 try:return [val(x) for x in v]
 except:return str(v)
def props(x,keys):return {k:val(getattr(x,k)) for k in keys if hasattr(x,k)}
def sockets(xs):return [dict(index=i,name=s.name,identifier=s.identifier,type=s.type,enabled=s.enabled,linked=s.is_linked,default=val(s.default_value) if hasattr(s,'default_value') else None) for i,s in enumerate(xs)]
groups={}
def graph(t,key=None):
 key=key or 'Group:'+t.name
 if key in groups:return key
 out={'nodes':[],'links':[]};groups[key]=out
 for n in t.nodes:
  row=dict(name=n.name,type=n.bl_idname,inputs=sockets(n.inputs),outputs=sockets(n.outputs),properties=props(n,['operation','blend_type','data_type','factor_mode','clamp_factor','clamp_result','use_clamp','mute','is_active_output','target','vector_type','space','convert_from','convert_to','uv_map','attribute_name','layer_name','interpolation','extension','projection','projection_blend','noise_dimensions','noise_type','normalize','distribution','invert','gradient_type']))
  if hasattr(n,'node_tree') and n.node_tree:row['group']=graph(n.node_tree)
  if hasattr(n,'image') and n.image:row['image']=n.image.name
  if hasattr(n,'color_ramp'):
   cr=n.color_ramp;row['ramp']=dict(props(cr,['interpolation','color_mode','hue_interpolation']),elements=[dict(position=e.position,colour=list(e.color)) for e in cr.elements])
  if hasattr(n,'mapping') and hasattr(n.mapping,'curves'):
   cm=n.mapping;cm.initialize();row['curves']=dict(props(cm,['use_clip','clip_min_x','clip_min_y','clip_max_x','clip_max_y','extend','tone']),curves=[dict(points=[dict(location=list(p.location),handle=p.handle_type) for p in c.points],samples=[cm.evaluate(c,i/256) for i in range(257)]) for c in cm.curves])
  if hasattr(n,'internal_links'):row['internal_links']=[dict(from_index=list(n.inputs).index(l.from_socket),to_index=list(n.outputs).index(l.to_socket)) for l in n.internal_links]
  out['nodes'].append(row)
 for l in t.links:out['links'].append(dict(from_node=l.from_node.name,from_index=list(l.from_node.outputs).index(l.from_socket),from_identifier=l.from_socket.identifier,to_node=l.to_node.name,to_index=list(l.to_node.inputs).index(l.to_socket),to_identifier=l.to_socket.identifier,valid=l.is_valid))
 return key
report={'ok':False}
try:
 before=sha(S);bpy.ops.wm.open_mainfile(filepath=str(S),load_ui=False,use_scripts=False);s=bpy.context.scene
 materials={}
 for m in bpy.data.materials:
  if not m.use_nodes:continue
  materials[m.name]=dict(graph=graph(m.node_tree,'Material:'+m.name),settings=props(m,['surface_render_method','use_transparent_shadow','use_transparency_overlap','use_backface_culling','use_backface_culling_shadow','displacement_method','max_vertex_displacement','pass_index']))
 if s.world and s.world.use_nodes:graph(s.world.node_tree,'World:'+s.world.name)
 images=[]
 for im in bpy.data.images:
  if not im.users:continue
  raw=Path(bpy.path.abspath(im.filepath));fallback=S.parent/'textures'/Path(im.filepath.replace('\\','/')).name
  p=raw if raw.is_file() else fallback
  images.append(dict(name=im.name,path=im.filepath,resolved=str(p),exists=p.is_file(),sha256=sha(p) if p.is_file() else None,colour_space=im.colorspace_settings.name,alpha_mode=im.alpha_mode,size=list(im.size),source=im.source,packed=bool(im.packed_file)))
 report.update(ok=True,schema=1,source=str(S),source_sha256=before,blender=dict(version=bpy.app.version_string,build_hash=str(bpy.app.build_hash)),scene=dict(name=s.name,frame=s.frame_current,engine=s.render.engine,view=props(s.view_settings,['view_transform','look','exposure','gamma']),display_device=s.display_settings.display_device,world=s.world.name if s.world else None),materials=materials,groups=groups,images=images)
 assert sha(S)==before
 report['source_unchanged']=True
 (O/'source-contract.json').write_text(json.dumps(report,indent=2))
 print('PARITY_AUDIT_OK',len(materials),'materials',len(groups),'graphs',len(images),'images',flush=True)
except Exception:
 report['error']=traceback.format_exc();(O/'audit-error.json').write_text(json.dumps(report,indent=2));raise
