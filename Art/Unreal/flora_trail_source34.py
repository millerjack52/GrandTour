"""Install the approved source-version response locally; shared sources stay read-only."""
import unreal as u,json,math
from pathlib import Path
from benmore_river_life_materials import props
R=Path('C:/GrandTour');D='/Game/GrandTour/ArtTests/FloraTrail';E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
BENCH='/Game/GrandTour/ArtTests/FloraTreeLighting/M_Source34Tree'
def settings():return json.loads((R/'Art/flora_trail_source34_settings.json').read_text())
def candidate(key):
 assert key in ['tree','pine']
 # Both tested tree meshes use the same audited Leaf_0 shader family.
 recipes=[json.loads((R/'Art/Export/LidarStudy/FloraParity/AssetMatch/recipe.json').read_text()),json.loads((R/'Art/Export/LidarStudy/FloraGroup/extra-assets.json').read_text())]
 asset=next(a for recipe in recipes for a in recipe['assets'] if a['key']==key)
 slot=next(s for s in asset['exact_slots'] if s['foliage']);assert slot['name']=='Leaf_0' and slot['diffuse_weight']==0 and abs(slot['soft']-.8534567356)<1e-6
 source=u.load_asset('/Game/GrandTour/ArtTests/FloraGroup/Assets/M_Exact_'+key+'_Leaf_0_26834fc');assert source
 template=u.load_asset(BENCH);assert template
 path=D+'/Materials/Source34/M_Source34_'+key
 m=u.load_asset(path) or E.duplicate_asset(BENCH,path);assert m
 textures={str(n.get_editor_property('parameter_name')):n.get_editor_property('texture') for n in M.get_material_expressions(source) if isinstance(n,u.MaterialExpressionTextureSampleParameter2D)}
 for n in M.get_material_expressions(m):
  if isinstance(n,u.MaterialExpressionTextureSampleParameter2D):
   name=str(n.get_editor_property('parameter_name'));assert name in textures;n.set_editor_property('texture',textures[name])
  if isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))=='SourceShadowCoverage':n.set_editor_property('default_value',1.)
 E.set_metadata_tag(m,'Source34OriginalMaterial',source.get_path_name());E.set_metadata_tag(m,'Source34Version','1')
 M.set_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
 assert not M.recompile_material(m);assert E.save_loaded_asset(m,False);return m
def install_component(c):
 if not c.static_mesh or c.static_mesh.get_name() not in ['SM_Exact_tree','SM_Exact_pine']:return []
 key=c.static_mesh.get_name().removeprefix('SM_Exact_');result=candidate(key);changed=[]
 for i,m in enumerate(c.get_materials()):
  if m.blend_mode==u.BlendMode.BLEND_MASKED:c.set_material(i,result);changed.append(result.get_path_name())
 return changed
def configure(world,cfg,save_collection=False):
 actors=u.GameplayStatics.get_all_actors_of_class(world,u.Actor)
 sun=next(a for a in actors if isinstance(a,u.DirectionalLight) and a.get_actor_label()=='FloraTrail_Sun')
 sky=next(a for a in actors if isinstance(a,u.SkyLight) and a.get_actor_label()=='FloraTrail_Sky')
 sun.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(),u.Vector(*cfg['sun_ray'])),False)
 sun.light_component.set_intensity(cfg['sun_energy']*cfg['sun_unit_gain']);sun.light_component.set_light_color(u.LinearColor(*cfg['sun_colour'],1))
 props(sun.light_component,use_temperature=False,light_source_angle=cfg['sun_source_angle'],contact_shadow_length=cfg['contact_shadow_length'])
 sky.light_component.set_intensity(cfg['sky_strength']*cfg['sky_unit_gain']);sky.light_component.set_light_color(u.LinearColor(*cfg['sky_colour'],1));sky.light_component.recapture_sky()
 for a in actors:
  if isinstance(a,u.PostProcessVolume) and a.get_actor_label()=='FloraTrail_Display':
   s=a.settings
   for k,v in dict(auto_exposure_bias=cfg['exposure_bias'],bloom_intensity=0.,local_exposure_highlight_contrast_scale=1.,local_exposure_shadow_contrast_scale=1.).items():props(s,**{'override_'+k:True,k:v})
   a.settings=s
 ray=sun.get_actor_forward_vector();direction=u.LinearColor(-ray.x,-ray.y,-ray.z,0)
 # Existing undergrowth keeps its conversion; synchronize its light inputs.
 collection=u.load_asset(D+'/Controls/MPC_SourceLighting');assert collection
 radiance=u.LinearColor(*(v*cfg['sky_strength']*.92909 for v in cfg['sky_colour']),0)
 if save_collection:
  parameters=[]
  for p in collection.get_editor_property('vector_parameters'):
   name=str(p.get_editor_property('parameter_name'))
   if name=='SunDirection':p.set_editor_property('default_value',direction)
   if name=='SkyRadiance':p.set_editor_property('default_value',radiance)
   parameters.append(p)
  collection.set_editor_property('vector_parameters',parameters);assert E.save_loaded_asset(collection,False)
 u.MaterialLibrary.set_vector_parameter_value(world,collection,'SunDirection',direction);u.MaterialLibrary.set_vector_parameter_value(world,collection,'SkyRadiance',radiance)
 return {'sun':sun.light_component.intensity,'sky':sky.light_component.intensity,'sun_direction':[direction.r,direction.g,direction.b],'sky_radiance':[radiance.r,radiance.g,radiance.b],'exposure_bias':cfg['exposure_bias']}
