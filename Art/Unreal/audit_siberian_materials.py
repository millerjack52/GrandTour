"""Read saved custom shaders and assert the showcase bridge fixes are present."""
import unreal as u
from pathlib import Path
import json,traceback
root=Path(u.Paths.project_dir())/'Art/Export/SiberianShowcase'
base='/Game/GrandTour/ArtTests/SiberianShowcase'
report={'ok':False,'materials':[]}
try:
 for path in u.EditorAssetLibrary.list_assets(base,True,False):
  m=u.EditorAssetLibrary.load_asset(path)
  if not isinstance(m,u.Material):continue
  name=m.get_name()
  if name not in ['M_Soil','M_Tread','M_Water','M_River','M_WaterSim','M_Sediment','M_Grass']:continue
  code='\n\n'.join(e.get_editor_property('code') for e in u.MaterialEditingLibrary.get_material_expressions(m) if isinstance(e,u.MaterialExpressionCustom))
  record={'path':path,'kind':name,'code_chars':len(code)};report['materials'].append(record)
  relative=path.split('SiberianShowcase/')[1].split('.')[0].replace('/','_')
  (root/(relative+'.hlsl.txt')).write_text(code)
  if name in ['M_Soil','M_Tread']:
   assert 'paint.r=clamp(paint.r*DepthScale,0,2.48);' in code,path
  if name=='M_Tread':
   assert 'float treadLight=' in code and 'float3 turfTrack=' in code,path
   assert 'dot(Texture2DSampleLevel(Style,StyleSampler,saturate(q),0).rg' in code,path
  if name=='M_Soil':assert 'float coverage=saturate(.45+field.a*.25);' in code and 'sandy*float3(.72,.60,.44)' in code,path
  if name in ['M_Water','M_River']:
   assert 'shoreDepth' in code and 'smoothstep(.05,1.25,shoreDepth)' in code,path
   assert 'MRWaveSampling recovered;' in code and 'float2 phase=float2(-5.12*clock,19.723);' in code,path
   assert 'speed*(.2+.8*fade)' in code and 'float2 fine=' in code,path
   assert 'float nativeRippleCm=max' not in code,path
   assert not m.get_editor_property('tangent_space_normal'),path
  if name in ['M_WaterSim','M_Sediment']:
   assert 'float4 c0=0,c1=0;' in code and 'float2 disturbance=old;' in code,path
  if name=='M_Grass':assert 'float3(.62,.78,.46)' in code,path
 assert len(report['materials'])==19,len(report['materials'])
 report['ok']=True
except Exception:
 report['error']=traceback.format_exc();u.log_error(report['error'])
(root/'audit-report.json').write_text(json.dumps(report,indent=2))
