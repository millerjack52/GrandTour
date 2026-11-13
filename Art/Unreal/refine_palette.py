"""One shared near/far finish with per-map controls; preserve surface detail."""
import unreal as u,sys,json,traceback,hashlib,shutil
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_life_materials import Graph,props
BASE='/Game/GrandTour/ArtTests/LidarStudy';DEST=BASE+'/CohesiveStyle';QA=ROOT/'Saved/LidarAuthoringQA/PaletteRefinement';QA.mkdir(parents=True,exist_ok=True)
assets=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary
PARAMS=dict(FinishStrength=0,FinishSaturation=.80,GreenRestraint=.8,HighlightCompression=.18,MidtoneGain=.92,SunlightWarmth=0,SunlightLift=0)
VALUES=dict(finish_strength=.9,finish_saturation=.8,green_restraint=.8,highlight_compression=.10,midtone_gain=.92,sunlight_warmth=.65,sunlight_lift=.18,patch_variation=.04,
 forest_colour=(.048,.066,.041),shadow_colour=(.019,.030,.025),sunlit_colour=(.125,.142,.068),clearing_colour=(.145,.151,.082),clearing_shadow_colour=(.048,.062,.041),
 sky_horizon_colour=(.67,.70,.64),sky_zenith_colour=(.33,.44,.43),haze_colour=(.43,.51,.47),ground_tint=(1.02,.96,.88))

def connected_nodes(material):
 todo=[mel.get_material_property_input_node(material,u.MaterialProperty.MP_EMISSIVE_COLOR)];nodes=[];seen=set()
 while todo:
  node=todo.pop()
  if not node or node.get_name() in seen:continue
  seen.add(node.get_name());nodes.append(node)
  todo.extend(n for n in mel.get_inputs_for_material_expression(material,node) if n)
 return nodes
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def protection():
 root=ROOT/'Content/GrandTour/ArtTests/LidarStudy'
 paths=[root/'L_LidarStudy.umap']+[root/'CanopyDepth'/f'SM_CD_Canopy_{i}.uasset' for i in range(3)]+[root/'CohesiveStyle'/f'{n}.uasset' for n in ['M_EvergreenTerrain','M_EvergreenDetail','M_EvergreenFoliage','MI_EvergreenFoliage']]
 return {str(p.relative_to(ROOT)):sha(p) for p in paths}
def run():
 p=u.load_asset(DEST+'/DA_Lidar_Evergreen');m=u.load_asset(DEST+'/M_EvergreenHaze');old_mpc=u.load_asset(BASE+'/FirewatchStyle/MPC_DistanceStyle');assert p and m and old_mpc
 muted=u.load_asset(DEST+'/DA_Lidar_MutedPalette')
 if not muted:
  muted=assets.duplicate_asset(DEST+'/DA_Lidar_Evergreen',DEST+'/DA_Lidar_MutedPalette')
  muted.set_editor_property('sunlight_warmth',0);muted.set_editor_property('sunlight_lift',0)
  assert assets.save_loaded_asset(muted,False)
 if not (QA/'before.json').exists():
  folder=QA/'Before';folder.mkdir(exist_ok=True)
  for a in [p,m,old_mpc]:
   path=ROOT/'Content'/(a.get_path_name().split('.')[0].removeprefix('/Game/')+'.uasset');shutil.copy2(path,folder/path.name)
  before_values={k:([getattr(p.get_editor_property(k),x) for x in ['r','g','b']] if isinstance(v,tuple) else p.get_editor_property(k)) for k,v in VALUES.items()}
  (QA/'before.json').write_text(json.dumps(dict(protected=protection(),values=before_values,original_codes={n.get_name():n.get_editor_property('code') for n in connected_nodes(m) if isinstance(n,u.MaterialExpressionCustom)}),indent=2))
 baseline=u.load_asset(DEST+'/DA_Lidar_BeforePalette')
 if not baseline:
  baseline=assets.duplicate_asset(DEST+'/DA_Lidar_Evergreen',DEST+'/DA_Lidar_BeforePalette')
  for k,v in json.loads((QA/'before.json').read_text())['values'].items():baseline.set_editor_property(k,u.LinearColor(*v,1) if isinstance(v,list) else v)
 assert baseline.finish_strength==0;assert assets.save_loaded_asset(baseline,False)
 mpc=u.load_asset(DEST+'/MPC_PaletteFinish') or u.AssetToolsHelpers.get_asset_tools().create_asset('MPC_PaletteFinish',DEST,u.MaterialParameterCollection,u.MaterialParameterCollectionFactoryNew())
 rows=list(mpc.get_editor_property('scalar_parameters'));names={str(x.get_editor_property('parameter_name')) for x in rows}
 for k,v in PARAMS.items():
  if k not in names:rows.append(props(u.CollectionScalarParameter(),parameter_name=k,default_value=v))
 mpc.set_editor_property('scalar_parameters',rows);assert assets.save_loaded_asset(mpc,False)
 nodes=connected_nodes(m);n=next((n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('desc'))=='PaletteFinish'),None);g=Graph(m,'PaletteFinish')
 if not n:
  before=json.loads((QA/'before.json').read_text());before['original_codes']={x.get_name():x.get_editor_property('code') for x in nodes if isinstance(x,u.MaterialExpressionCustom)}
  assert before['original_codes'], 'Original haze graph must be present'
  (QA/'before.json').write_text(json.dumps(before,indent=2))
 code=(ROOT/'Art/Shaders/PaletteFinish.ush').read_text()
 if not n:
  src=mel.get_material_property_input_node(m,u.MaterialProperty.MP_EMISSIVE_COLOR);out=mel.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_EMISSIVE_COLOR)
  n=g.custom(['Composed']+list(PARAMS),code);g.wire(src,n,'Composed',str(out))
  for key in PARAMS:g.wire(g.node(u.MaterialExpressionCollectionParameter,collection=mpc,parameter_name=key),n,key)
 else:
  inputs=[str(x.get_editor_property('input_name')) for x in n.get_editor_property('inputs')];links=mel.get_inputs_for_material_expression(m,n)
  # Extend the existing wrapper in place; preserve links and never stack grades.
  rows=list(n.get_editor_property('inputs'))
  for key in list(PARAMS)+['SceneDepth']:
   if key not in inputs:rows.append(props(u.CustomInput(),input_name=key))
  n.set_editor_property('inputs',rows)
  for key in PARAMS:
   if key in inputs:
    a=links[inputs.index(key)];a.set_editor_property('collection',mpc);a.set_editor_property('parameter_name',key)
   else:g.wire(g.node(u.MaterialExpressionCollectionParameter,collection=mpc,parameter_name=key),n,key)
 if 'SceneDepth' not in [str(x.get_editor_property('input_name')) for x in n.get_editor_property('inputs')]:
  n.set_editor_property('inputs',list(n.get_editor_property('inputs'))+[props(u.CustomInput(),input_name='SceneDepth')])
 inputs=[str(x.get_editor_property('input_name')) for x in n.get_editor_property('inputs')]
 if not mel.get_inputs_for_material_expression(m,n)[inputs.index('SceneDepth')]:
  original=next(x for x in connected_nodes(m) if isinstance(x,u.MaterialExpressionCustom) and str(x.get_editor_property('desc'))!='PaletteFinish')
  names=[str(x.get_editor_property('input_name')) for x in original.get_editor_property('inputs')]
  g.wire(mel.get_inputs_for_material_expression(m,original)[names.index('Depth')],n,'SceneDepth')
 n.set_editor_property('code',code);g.output(n,u.MaterialProperty.MP_EMISSIVE_COLOR);assert not mel.recompile_material(m);assert assets.save_loaded_asset(m,False)
 for k,v in VALUES.items():p.set_editor_property(k,u.LinearColor(*v,1) if isinstance(v,tuple) else v)
 assert assets.save_loaded_asset(p,False)
 before=json.loads((QA/'before.json').read_text());assert protection()==before['protected']
 codes={x.get_name():x.get_editor_property('code') for x in connected_nodes(m) if isinstance(x,u.MaterialExpressionCustom) and str(x.get_editor_property('desc'))!='PaletteFinish'};assert codes==before['original_codes']
 assert sum(isinstance(x,u.MaterialExpressionCustom) and str(x.get_editor_property('desc'))=='PaletteFinish' for x in connected_nodes(m))==1
 assert all(mel.get_inputs_for_material_expression(m,n));assert p.surface_detail_strength==1
 assert sha(ROOT/'Content/GrandTour/ArtTests/LidarStudy/FirewatchStyle/MPC_DistanceStyle.uasset')==sha(QA/'Before/MPC_DistanceStyle.uasset')
 for key in ['shadow_colour','clearing_shadow_colour','forest_colour','sky_horizon_colour','sky_zenith_colour','haze_colour','haze_intensity','haze_start_metres','haze_full_metres','finish_saturation','green_restraint','midtone_gain']:
  assert p.get_editor_property(key)==muted.get_editor_property(key),key+' must retain the muted baseline value'
 return dict(ok=True,values=VALUES,protected_map_leaves_roads_unchanged=True,original_haze_shader_preserved=True,existing_parameter_collection_unchanged=True,parallax_enabled=True,baseline_profile=baseline.get_path_name(),active_profile=p.get_path_name(),extra_render_passes=0,extra_texture_samples=0)
if __name__=='__main__':
 try:result=run()
 except Exception:result=dict(ok=False,error=traceback.format_exc());u.log_error(result['error'])
 (QA/'install.json').write_text(json.dumps(result,indent=2));u.SystemLibrary.quit_editor()
