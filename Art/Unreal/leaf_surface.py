"""Map-owned close leaf treatment; preserves tree placement and distance shaders."""
import unreal as u,sys,json,os,traceback,hashlib,shutil
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_life_materials import Graph,props
from forest_shaders import connected_nodes
QA=ROOT/'Saved/LidarAuthoringQA/LeafSurface';QA.mkdir(parents=True,exist_ok=True)
BASE='/Game/GrandTour/ArtTests/LidarStudy';DEST=BASE+'/CohesiveStyle'
mel=u.MaterialEditingLibrary;assets=u.EditorAssetLibrary
PARAMS=dict(LeafStrength=1,LeafCurvature=.85,LeafTransmission=.32,LeafNearCm=1600,LeafFarCm=5000)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def protected():
 paths=[ROOT/'Content/GrandTour/ArtTests/LidarStudy'/x for x in ['L_LidarStudy.umap','CohesiveStyle/M_EvergreenTerrain.uasset','CohesiveStyle/M_EvergreenDetail.uasset','CohesiveStyle/DA_Lidar_Evergreen.uasset']]
 paths+=list((ROOT/'Content/GrandTour/ArtTests/LidarStudy/CanopyDepth').glob('*.uasset'))
 return {str(p.relative_to(ROOT)):sha(p) for p in paths}
def install():
 m=u.load_asset(DEST+'/M_EvergreenFoliage');assert m
 mi=u.load_asset(DEST+'/MI_EvergreenFoliage');assert mi.get_editor_property('parent')==m
 mpc=u.load_asset(BASE+'/FirewatchStyle/MPC_DistanceStyle')
 if not (QA/'before.json').exists():
  folder=QA/'Before';folder.mkdir(exist_ok=True)
  for a in [m,mi,mpc]:
   p=ROOT/'Content'/(a.get_path_name().split('.')[0].removeprefix('/Game/')+'.uasset');shutil.copy2(p,folder/p.name)
  report=dict(protected=protected(),material={k:str(m.get_editor_property(k)) for k in ['blend_mode','two_sided','shading_model','tangent_space_normal']},codes={n.get_name():n.get_editor_property('code') for n in connected_nodes(m) if isinstance(n,u.MaterialExpressionCustom)})
  (QA/'before.json').write_text(json.dumps(report,indent=2))
 rows=list(mpc.get_editor_property('scalar_parameters'))
 if not any(str(x.get_editor_property('parameter_name'))=='LeafReviewStrength' for x in rows):
  rows.append(props(u.CollectionScalarParameter(),parameter_name='LeafReviewStrength',default_value=1))
  mpc.set_editor_property('scalar_parameters',rows);assert assets.save_loaded_asset(mpc,False)
 nodes=connected_nodes(m);n=next((x for x in nodes if isinstance(x,u.MaterialExpressionCustom) and str(x.get_editor_property('desc'))=='LeafSurface'),None)
 g=Graph(m,'LeafSurface');code=(ROOT/'Art/Shaders/LeafSurface.ush').read_text()
 if n is None:
  pins={'Base':u.MaterialProperty.MP_BASE_COLOR,'OldN':u.MaterialProperty.MP_NORMAL,'OldSub':u.MaterialProperty.MP_SUBSURFACE_COLOR,'OldRough':u.MaterialProperty.MP_ROUGHNESS}
  originals={k:(mel.get_material_property_input_node(m,p),mel.get_material_property_input_node_output_name(m,p)) for k,p in pins.items()}
  n=g.custom(list(pins)+['UV','P','Camera','LeafStrength','Curvature','Transmission','NearCm','FarCm','Review'],code,outputs=[('Normal',u.CustomMaterialOutputType.CMOT_FLOAT3),('Subsurface',u.CustomMaterialOutputType.CMOT_FLOAT3),('Rough',u.CustomMaterialOutputType.CMOT_FLOAT1),('Mask',u.CustomMaterialOutputType.CMOT_FLOAT1)])
  for k,(a,out) in originals.items():assert a,k;g.wire(a,n,k,str(out))
  for k,cls in [('UV',u.MaterialExpressionTextureCoordinate),('P',u.MaterialExpressionWorldPosition),('Camera',u.MaterialExpressionCameraPositionWS)]:g.wire(g.node(cls),n,k)
  for key,pin in [('LeafStrength','LeafStrength'),('LeafCurvature','Curvature'),('LeafTransmission','Transmission'),('LeafNearCm','NearCm'),('LeafFarCm','FarCm')]:
   a=g.node(u.MaterialExpressionScalarParameter,parameter_name=key,default_value=PARAMS[key],group='Leaf Surface');g.wire(a,n,pin)
  g.wire(g.node(u.MaterialExpressionCollectionParameter,collection=mpc,parameter_name='LeafReviewStrength'),n,'Review')
 n.set_editor_property('code',code)
 for p,out in [(u.MaterialProperty.MP_BASE_COLOR,''),(u.MaterialProperty.MP_NORMAL,'Normal'),(u.MaterialProperty.MP_SUBSURFACE_COLOR,'Subsurface'),(u.MaterialProperty.MP_ROUGHNESS,'Rough'),(u.MaterialProperty.MP_OPACITY_MASK,'Mask')]:g.output(n,p,out)
 props(m,blend_mode=u.BlendMode.BLEND_MASKED,opacity_mask_clip_value=.333,two_sided=True,tangent_space_normal=False,shading_model=u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
 assert not mel.recompile_material(m);assert assets.save_loaded_asset(m,False)
 before=json.loads((QA/'before.json').read_text());assert protected()==before['protected']
 codes={x.get_name():x.get_editor_property('code') for x in connected_nodes(m) if isinstance(x,u.MaterialExpressionCustom) and str(x.get_editor_property('desc'))!='LeafSurface'}
 assert codes==before['codes'],'Upstream shader changed'
 assert all(mel.get_inputs_for_material_expression(m,n))
 return dict(ok=True,protected_packages_unchanged=True,upstream_programs_unchanged=True,parameters=PARAMS,material=m.get_path_name(),original=before['material'])
if __name__=='__main__':
 try:result=install()
 except Exception:result=dict(ok=False,error=traceback.format_exc());u.log_error(result['error'])
 (QA/'install.json').write_text(json.dumps(result,indent=2));u.SystemLibrary.quit_editor()
