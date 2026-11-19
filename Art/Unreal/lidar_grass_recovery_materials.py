"""Restore existing fine-blade art with one muted near/far/pasture palette."""
import unreal as u,json
from pathlib import Path
R=Path('C:/GrandTour');CFG=json.loads((R/'Art/lidar_grass_recovery_settings.json').read_text())
B='/Game/GrandTour/ArtTests/LidarStudy';D=B+'/GrassRecovery/'+CFG['revision']
E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
SOURCES={**{k:B+'/GrassGS3/M_GS3_'+k for k in ('Near','Far','Verge')},**{k:B+'/FloraWorld/M_Flora'+k for k in ('Terrain','Detail')}}

def path(m):return m.get_path_name()
def inputs(m,p):
 n=M.get_material_property_input_node(m,p);return (n.get_name() if n else None,str(M.get_material_property_input_node_output_name(m,p) or ''))
def textures(m):return sorted(path(n.texture) for n in M.get_material_expressions(m) if isinstance(n,(u.MaterialExpressionTextureSample,u.MaterialExpressionTextureObject)) and n.texture)

def prepare():
 checks=[]
 for role,source in SOURCES.items():
  src=u.load_asset(source);assert src,source
  dst=D+'/M_Fine_'+role;m=u.load_asset(dst)
  if m:assert E.get_metadata_tag(m,'GrassRecoverySource')==path(src)
  else:
   m=E.duplicate_asset(source,dst);assert m
   E.set_metadata_tag(m,'GrassRecoverySource',path(src));E.set_metadata_tag(m,'LidarTransferSource',path(src))
   changes=0
   replacements={'float3(.105,.255,.060)':'green','float3(.060,.190,.115)':'cool','float3(.285,.295,.105)':'straw','float3(.32,.30,.13)':'verge','float3(.285,.275,.15)':'straw'}
   for n in M.get_material_expressions(m):
    if not isinstance(n,u.MaterialExpressionCustom):continue
    code=str(n.get_editor_property('code'))
    if 'rsColour' not in code:continue
    for old,key in replacements.items():code=code.replace(old,'float3('+','.join(str(v) for v in CFG[key])+')')
    n.set_editor_property('code',code);changes+=1
   assert changes==1,(role,changes)
   assert not M.recompile_material(m);assert E.save_loaded_asset(m,False)
  assert textures(src)==textures(m)
  for pin in (u.MaterialProperty.MP_WORLD_POSITION_OFFSET,u.MaterialProperty.MP_OPACITY_MASK):assert inputs(src,pin)==inputs(m,pin),(role,pin)
  for n in M.get_material_expressions(m):
   if isinstance(n,u.MaterialExpressionCustom) and 'rsColour' in str(n.get_editor_property('code')):assert 'float3(.105,.255,.060)' not in str(n.get_editor_property('code'))
  checks.append({'role':role,'source':path(src),'copy':path(m),'textures_wind_coverage_preserved':True})
 return checks

def apply(world,muted):
 art={**{k:B+'/GrassGS3/SM_GS3_'+v for k,v in [('pasture_clump_mesh','Near_A'),('pasture_clump_mesh_b','Near_B'),('pasture_clump_mesh_c','Near_C'),('rank_clump_mesh','Verge')]},**{k:(D+'/M_Fine_'+v if muted else SOURCES[v]) for k,v in [('grass_material','Near'),('rank_material','Verge'),('distant_pasture_material','Far')]}}
 rows=u.GameplayStatics.get_all_actors_of_class(world,u.Actor);changes=[]
 for a in rows:
  if isinstance(a,u.GTMixedGroundDetails) and a.generate_around_player:
   for k,v in art.items():
    old=a.get_editor_property(k);new=u.load_asset(v);assert new
    a.set_editor_property(k,new);changes.append({'actor':a.get_actor_label(),'property':k,'source':path(old),'copy':path(new)})
 if muted:
  mapping={u.load_asset(SOURCES[k]):u.load_asset(D+'/M_Fine_'+k) for k in ('Terrain','Detail')};assert all(mapping) and all(mapping.values())
  for a in rows:
   if isinstance(a,u.GTProceduralGround) and a.relief_material in mapping:a.relief_material=mapping[a.relief_material]
   if isinstance(a,u.GTMudRunnerVisual) and a.material in mapping:a.material=mapping[a.material]
   if isinstance(a,u.LandscapeProxy) and a.landscape_material in mapping:a.landscape_material=mapping[a.landscape_material]
   for c in a.get_components_by_class(u.PrimitiveComponent):
    try:ms=list(c.get_materials())
    except Exception:continue
    for i,m in enumerate(ms):
     if m in mapping:c.set_material(i,mapping[m])
  changes.extend({'role':k,'source':path(u.load_asset(SOURCES[k])),'copy':path(u.load_asset(D+'/M_Fine_'+k))} for k in ('Terrain','Detail'))
 return changes
