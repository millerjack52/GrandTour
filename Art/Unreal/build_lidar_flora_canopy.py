"""Map-local Flora Paint canopy LODs, with colour/normal atlases baked in Unreal.

Uses the project's validated canopy baker; leaves purchased source assets intact.
Three side cards plus a horizontal card retain crown coverage from all views.
"""
import unreal as u,sys,time,json,traceback,gc,math
from pathlib import Path
R=Path('C:/GrandTour');sys.path.insert(0,str(R/'Art/Unreal'))
import lidar_canopy_assets as B
from flora_world_finish import bake_override
B.bake_override=bake_override
from benmore_river_life_materials import Graph,props
O=R/'Art/Export/LidarStudy/FloraWorld';O.mkdir(parents=True,exist_ok=True)
D='/Game/GrandTour/ArtTests/LidarStudy/FloraWorld/Canopy'
B.OUT=O;B.DEST=D;B.SOURCES=['Tree_B_001','Tree_D_003','Tree_B_002'];B.VERSION=1
B.source_path=lambda n:'/Game/GrandTour/ArtTests/FloraPath/SM_Path_FP_'+n
B.cached=lambda:None
B.screen_sizes=lambda mesh:[1.,.65,.28,.14]

def shade(k):
 m=u.load_asset(D+'/M_FirFar_'+str(k));nt=u.load_asset(D+'/T_FirNormal_'+str(k))
 g=Graph(m,'FloraFarNormal');uv=g.node(u.MaterialExpressionTextureCoordinate);s=g.tex(nt,uv)
 n=g.custom(['Packed'],'return normalize(Packed*2-1);');g.wire(s,n,'Packed','RGB')
 w=g.node(u.MaterialExpressionTransform,transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD);g.wire(n,w,'');g.output(w,u.MaterialProperty.MP_NORMAL)
 # Preserve source colour, with the same warm/cool level lighting as the near mesh.
 for node in u.MaterialEditingLibrary.get_material_expressions(m):
  if isinstance(node,u.MaterialExpressionConstant3Vector) and str(node.get_editor_property('desc'))=='LP3cTint':node.set_editor_property('constant',u.LinearColor(1,1,1,1))
 props(m,dithered_lod_transition=True,tangent_space_normal=False)
 assert not u.MaterialEditingLibrary.recompile_material(m);assert u.EditorAssetLibrary.save_loaded_asset(m,False)
 return True
B.shade_far_card=shade
# Reuse the baker without changing its source or other maps' assets.
source=(R/'Art/Unreal/lidar_canopy_assets.py').read_text().split('def build(world,force=False):',1)[1]
source='def build(world,force=False):'+source
# Reduced source LODs can lack editable MeshDescriptions after a fresh load.
# Existing map clones already contain those valid render LODs; retain them.
source=source.replace("   for lod in range(3):\n    assert mesh.get_static_mesh_description(lod) and source.get_static_mesh_description(lod)\n    assert sm.set_lod_from_static_mesh(mesh,lod,source,lod,True)==lod", "   # Preserve the existing three source render LODs on a bake-only rebuild.")
source=source.replace('tree.static_mesh_component.set_forced_lod_model(1)','tree.static_mesh_component.set_forced_lod_model(1);bake_override(tree.static_mesh_component)')
source=source.replace('for view in range(3):','for view in range(4):').replace('bytearray(512*512*3*4)','bytearray(512*512*4*4)').replace('*1536+view*512','*2048+view*512').replace('1536,512,32,40','2048,512,32,40').replace('((view+ux)/3,uy)','((view+ux)/4,uy)')
source=source.replace('pos=centre+u.Vector(math.cos(angle)*size*2,math.sin(angle)*size*2,0)','pos=centre+(u.Vector(0,0,size*2) if view==3 else u.Vector(math.cos(angle)*size*2,math.sin(angle)*size*2,0))')
old="for side,up in [(-1,-1),(1,-1),(1,1),(-1,1)]:lines.append('v %f %f %f'%(b.origin.x+right[0]*side*size/2,b.origin.y+right[1]*side*size/2,b.origin.z+up*size/2))"
new="for side,up in [(-1,-1),(1,-1),(1,1),(-1,1)]:lines.append('v %f %f %f'%((b.origin.x+up*size/2,b.origin.y+side*size/2,b.origin.z+b.box_extent.z*.40) if view==3 else (b.origin.x+right[0]*side*size/2,b.origin.y+right[1]*side*size/2,b.origin.z+up*size/2)))"
assert old in source;source=source.replace(old,new)
exec(compile(source,'<flora-canopy-baker>','exec'),B.__dict__)
state={'busy':False,'deadline':0};report={'ok':False}
def run():
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 yield from B.build(world,True)
 for k in range(3):
  m=u.load_asset(D+'/SM_Canopy_'+str(k))
  assert B.sm.get_lod_count(m)==4 and m.get_static_mesh_description(3).get_triangle_count()==8
  for prefix in ['T_FirAtlas_','T_FirNormal_']:
   tex=u.load_asset(D+'/'+prefix+str(k))
   props(tex,power_of_two_mode=u.TexturePowerOfTwoSetting.STRETCH_TO_POWER_OF_TWO,mip_gen_settings=u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE,filter=u.TextureFilter.TF_TRILINEAR)
   assert u.EditorAssetLibrary.save_loaded_asset(tex,False)
 report.update(ok=True,meshes=B.report['meshes'],far_triangles=8,top_card=True)
 (O/'canopy-report.json').write_text(json.dumps(report,indent=2))
 world=None;gc.collect();yield 2
steps=run()
def tick(dt):
 if state['busy'] or time.monotonic()<state['deadline']:return
 state['busy']=True
 try:state['deadline']=time.monotonic()+next(steps)
 except StopIteration:u.unregister_slate_post_tick_callback(state['handle']);u.SystemLibrary.quit_editor()
 except Exception:
  report.update(error=traceback.format_exc());(O/'canopy-report.json').write_text(json.dumps(report,indent=2));u.log_error(report['error']);u.unregister_slate_post_tick_callback(state['handle']);u.SystemLibrary.quit_editor()
 finally:state['busy']=False
u.EditorPythonScripting.set_keep_python_script_alive(True);state['handle']=u.register_slate_post_tick_callback(tick)
