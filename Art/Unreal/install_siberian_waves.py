"""Patch saved wave optics and bindings without rebuilding any terrain."""
import unreal as u
from pathlib import Path
import sys,json,traceback,shutil,time
sys.path.insert(0,str(Path(__file__).parent))
import siberian_wave_materials as waves
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/SiberianShowcase'
BASE='/Game/GrandTour/ArtTests/SiberianShowcase';LEVEL=BASE+'/L_SiberianShowcase'
report={'ok':False,'materials':[]}
try:
 backup=ROOT/'Saved/SiberianWaveBackups'/str(time.time_ns());backup.mkdir(parents=True)
 for relative in ['L_SiberianShowcase.umap','M_River.uasset','SW/M_Water.uasset','SE/M_Water.uasset','NE/M_Water.uasset']:
  src=ROOT/'Content/GrandTour/ArtTests/SiberianShowcase'/relative;dst=backup/relative;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
 report['backup']=str(backup)
 pre=waves.precombine()
 for path in [BASE+'/M_River']+[BASE+'/'+t+'/M_Water' for t in ['SW','SE','NE']]:
  m=u.load_asset(path);assert m;waves.patch(m);report['materials'].append(path)
 les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(LEVEL)
 for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
  if isinstance(a,u.GTWaterSheet):a.set_editor_property('ambient_wave_material',pre)
 assert les.save_current_level();les.load_level('/Engine/Maps/Entry')
 # GPU arithmetic fixture uses the actual recovered wave texture as known input.
 from benmore_river_life_materials import Graph,props
 path=waves.BASE+'/M_SamplingOracle';m=u.load_asset(path) or u.AssetToolsHelpers.get_asset_tools().create_asset('M_SamplingOracle',waves.BASE,u.Material,u.MaterialFactoryNew())
 for e in list(waves.mel.get_material_expressions(m)):waves.mel.delete_material_expression(m,e)
 props(m,shading_model=u.MaterialShadingModel.MSM_UNLIT);g=Graph(m,'WaveOracle')
 inputs={'UV':g.node(u.MaterialExpressionTextureCoordinate)}
 textures={'Waves':u.load_asset('/Game/GrandTour/ArtTests/MudLab/NativeReference/T_env_water_waves__d_a_uncmp'),'Directions':waves.lookup('direction'),'Speeds':waves.lookup('speed')}
 for k,t in textures.items():inputs[k]=g.node(u.MaterialExpressionTextureObject,texture=t,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
 body=waves.SAMPLING+'''
MRWaveSampling recovered;
float theta=(UV.x*2-1)*3.141592653589793;
float2 flow=float2(cos(theta),sin(theta))*floor(UV.y*8)*.12;
float2 worldM=UV*float2(13.7,15)-float2(6,3);
float4 wave=recovered.optical(Waves,WavesSampler,Directions,DirectionsSampler,Speeds,SpeedsSampler,worldM,flow,1.25,0);
return recovered.normal(wave.xy,flow,.2+UV.y*50)*.5+.5;
'''
 e=g.custom(list(inputs),body)
 for k,v in inputs.items():g.wire(v,e,k)
 g.output(e,u.MaterialProperty.MP_EMISSIVE_COLOR);assert not waves.mel.recompile_material(m);assert waves.assets.save_loaded_asset(m)
 import audit_siberian_materials
 assert audit_siberian_materials.report['ok']
 report['ok']=True
except Exception:
 report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'waves-report.json').write_text(json.dumps(report,indent=2))
