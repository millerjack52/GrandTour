"""Audit and author height-based surface detail for the active LiDAR materials."""
import unreal as u,json,sys,os,time,traceback,hashlib,shutil
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from forest_shaders import connected_nodes
from benmore_river_life_materials import Graph,props
QA=ROOT/'Saved/LidarAuthoringQA/RoadParallax';QA.mkdir(parents=True,exist_ok=True)
BASE='/Game/GrandTour/ArtTests/LidarStudy';DEST=BASE+'/CohesiveStyle'
mel=u.MaterialEditingLibrary;assets=u.EditorAssetLibrary
SCALARS=dict(SurfaceDetailStrength=0,SurfaceParallaxStrength=1,GravelDepthCm=1.6,GroundDepthCm=2.2,GravelTileCm=140,GroundTileCm=150,SurfaceNearCm=600,SurfaceFarCm=1800,SurfaceMaxSteps=24)
PROPS=['MP_BASE_COLOR','MP_NORMAL','MP_ROUGHNESS','MP_AMBIENT_OCCLUSION','MP_WORLD_POSITION_OFFSET','MP_OPACITY_MASK']
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def protection(m):
 return dict(codes={n.get_name():hashlib.sha256(n.get_editor_property('code').encode()).hexdigest() for n in connected_nodes(m) if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('desc'))!='RoadParallax'},outputs={p:[mel.get_material_property_input_node(m,getattr(u.MaterialProperty,p)).get_name(),str(mel.get_material_property_input_node_output_name(m,getattr(u.MaterialProperty,p)))] for p in ['MP_WORLD_POSITION_OFFSET','MP_OPACITY_MASK']})
def backup():
 if (QA/'before.json').exists():return
 paths=[ROOT/'Content/GrandTour/ArtTests/LidarStudy'/p for p in ['CohesiveStyle/M_EvergreenTerrain.uasset','CohesiveStyle/M_EvergreenDetail.uasset','CohesiveStyle/DA_Lidar_Evergreen.uasset','FirewatchStyle/MPC_DistanceStyle.uasset']]
 folder=QA/'Before';folder.mkdir(exist_ok=True)
 for p in paths:shutil.copy2(p,folder/p.name)
 report=dict(files={str(p.relative_to(ROOT)):sha(p) for p in paths},map_sha256=sha(ROOT/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap'),materials={n:protection(u.load_asset(DEST+'/'+n)) for n in ['M_EvergreenTerrain','M_EvergreenDetail']})
 (QA/'before.json').write_text(json.dumps(report,indent=2))
def install():
 backup();mpc=u.load_asset(BASE+'/FirewatchStyle/MPC_DistanceStyle')
 rows=list(mpc.get_editor_property('scalar_parameters'));names={str(x.get_editor_property('parameter_name')) for x in rows}
 for k,v in SCALARS.items():
  if k not in names:rows.append(props(u.CollectionScalarParameter(),parameter_name=k,default_value=v))
 mpc.set_editor_property('scalar_parameters',rows);assert assets.save_loaded_asset(mpc,False)
 profile=u.load_asset(DEST+'/DA_Lidar_Evergreen');profile.surface_detail_strength=1
 assert assets.save_loaded_asset(profile,False)
 code=(ROOT/'Art/Shaders/RoadParallax.ush').read_text()
 spec=json.loads((ROOT/'Art/Export/LidarStudy/Place/river-repair.json').read_text())
 for name in ['M_EvergreenTerrain','M_EvergreenDetail']:
  m=u.load_asset(DEST+'/'+name);nodes=connected_nodes(m);g=Graph(m,'RoadParallax')
  n=next((x for x in nodes if isinstance(x,u.MaterialExpressionCustom) and str(x.get_editor_property('desc'))=='RoadParallax'),None)
  if not n:
   original={p:(mel.get_material_property_input_node(m,getattr(u.MaterialProperty,p)),str(mel.get_material_property_input_node_output_name(m,getattr(u.MaterialProperty,p)))) for p in PROPS[:4]}
   inputs=['Base','OldNormal','OldRough','OldAO','P','VertexN','Camera','Style','Clay','RiverMask','RiverDomain','State','Route','GC','GO','SoilColour','SoilData']+list(SCALARS)
   n=g.custom(inputs,code,outputs=[('Normal',u.CustomMaterialOutputType.CMOT_FLOAT3),('Rough',u.CustomMaterialOutputType.CMOT_FLOAT1),('AO',u.CustomMaterialOutputType.CMOT_FLOAT1)])
   for pin,p in zip(['Base','OldNormal','OldRough','OldAO'],PROPS):
    node,out=original[p];g.wire(node or g.scalar(1),n,pin,out if node else '')
   for pin,cls in [('P',u.MaterialExpressionWorldPosition),('VertexN',u.MaterialExpressionVertexNormalWS),('Camera',u.MaterialExpressionCameraPositionWS)]:g.wire(g.node(cls),n,pin)
   textures=dict(Style=(BASE+'/T_style',False),Clay=(BASE+'/T_clay',False),RiverMask=(BASE+'/RiverDetail/T_RiverDetail',False),GC=('/Game/GrandTour/ArtTests/DeformableGravel/TA_GV_Color',True),GO=('/Game/GrandTour/ArtTests/DeformableGravel/TA_GV_ORH',False),SoilColour=(BASE+'/FirstSection/PeatMoss/T_PM_PeatColour',True),SoilData=(BASE+'/FirstSection/PeatMoss/T_PM_PeatData',False))
   # Reuse the audited distance atlas, whose asset name may differ from the mask key.
   rd=next(x for x in nodes if isinstance(x,u.MaterialExpressionCustom) and str(x.get_editor_property('desc'))=='RD1Gravel')
   rdlinks=mel.get_inputs_for_material_expression(m,rd);rdnames=[str(x.get_editor_property('input_name')) for x in rd.get_editor_property('inputs')]
   for pin,(path,colour) in textures.items():
    tex=rdlinks[rdnames.index('LidarClay')].get_editor_property('texture') if pin=='Clay' else u.load_asset(path)
    assert tex,(name,pin,path)
    g.wire(g.node(u.MaterialExpressionTextureObject,texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR if colour else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR),n,pin)
   ox,oy=spec['mask_origin_cm'];g.wire(g.node(u.MaterialExpressionConstant4Vector,constant=u.LinearColor(ox,oy,spec['mask_span_cm'],0)),n,'RiverDomain')
   main=next(x for x in nodes if isinstance(x,u.MaterialExpressionCustom) and str(x.get_editor_property('desc'))=='MudRunnerStage4')
   g.wire(main,n,'State','RR1State');g.wire(main,n,'Route','LT4Coverage')
   for k in SCALARS:g.wire(g.node(u.MaterialExpressionCollectionParameter,collection=mpc,parameter_name=k),n,k)
  n.set_editor_property('code',code)
  for p,out in zip(PROPS[:4],['','Normal','Rough','AO']):g.output(n,getattr(u.MaterialProperty,p),out)
  assert not mel.recompile_material(m);assert assets.save_loaded_asset(m,False)
 return verify()
def verify():
 before=json.loads((QA/'before.json').read_text())
 assert sha(ROOT/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap')==before['map_sha256']
 for name,p in before['materials'].items():
  m=u.load_asset(DEST+'/'+name);assert protection(m)==p,(name,'Existing shading/displacement changed')
  node=mel.get_material_property_input_node(m,u.MaterialProperty.MP_BASE_COLOR)
  assert node.get_editor_property('code')==(ROOT/'Art/Shaders/RoadParallax.ush').read_text()
  assert all(mel.get_inputs_for_material_expression(m,node))
 assert u.load_asset(DEST+'/DA_Lidar_Evergreen').surface_detail_strength==1
 assert u.load_asset(BASE+'/FirewatchStyle/DA_Lidar_Medium').surface_detail_strength==0
 return dict(map_unchanged=True,existing_shader_programs_unchanged=True,displacement_and_opacity_unchanged=True,materials=2,profile_enabled=True,previous_medium_unchanged=True)
def audit():
 report={}
 for name in ['M_EvergreenTerrain','M_EvergreenDetail']:
  m=u.load_asset(DEST+'/'+name);assert m
  nodes=[]
  for n in connected_nodes(m):
   r=dict(name=n.get_name(),type=n.get_class().get_name(),desc=str(n.get_editor_property('desc')),links=[x.get_name() if x else None for x in mel.get_inputs_for_material_expression(m,n)])
   if isinstance(n,u.MaterialExpressionCustom):r.update(code=n.get_editor_property('code'),inputs=[str(i.get_editor_property('input_name')) for i in n.get_editor_property('inputs')])
   for prop in ['texture','parameter_name','default_value']:
    try:r[prop]=str(n.get_editor_property(prop))
    except Exception:pass
   nodes.append(r)
  report[name]=dict(tangent_space_normal=m.get_editor_property('tangent_space_normal'),nodes=nodes,outputs={p:[mel.get_material_property_input_node(m,getattr(u.MaterialProperty,p)).get_name() if mel.get_material_property_input_node(m,getattr(u.MaterialProperty,p)) else None,str(mel.get_material_property_input_node_output_name(m,getattr(u.MaterialProperty,p)))] for p in ['MP_BASE_COLOR','MP_NORMAL','MP_ROUGHNESS','MP_AMBIENT_OCCLUSION','MP_WORLD_POSITION_OFFSET','MP_OPACITY_MASK']})
 (QA/'audit.json').write_text(json.dumps(report,indent=2))
 return dict(materials=len(report))
if __name__=='__main__':
 result=dict(ok=False,stage=os.environ.get('GT_ROAD_POM_STAGE','audit'))
 try:
  result.update({'audit':audit,'install':install,'verify':verify}[result['stage']]());result['ok']=True
 except Exception:result['error']=traceback.format_exc();u.log_error(result['error'])
 (QA/(result['stage']+'.result.json')).write_text(json.dumps(result,indent=2));u.SystemLibrary.quit_editor()
