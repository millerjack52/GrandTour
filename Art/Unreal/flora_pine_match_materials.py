"""Apply only a measured pine coverage correction; all colour/light nodes survive."""
import unreal as u,json
from pathlib import Path
R=Path('C:/GrandTour');P='/Game/GrandTour/ArtTests/FloraTrail/PineTrial'
E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
FACING='float b=clamp(Soft,0.,.99999);float exponent=b<.5?2*b:.5/(1-b);float c=pow(saturate(abs(dot(normalize(N),normalize(V)))),exponent);return saturate(A*(.1+.9*c));'
def source_mask():
 tex=u.load_asset(P+'/SourceMatch/T_SourceMask4K')
 if not tex:
  data=json.loads((R/'Art/Export/FloraTrail/PineMatch/mask-report.json').read_text())
  assert data['ok'] and data['source_unchanged']
  task=u.AssetImportTask()
  for key,value in dict(filename=data['masks']['Leaf_0.002'],destination_path=P+'/SourceMatch',destination_name='T_SourceMask4K',automated=True,save=True).items():task.set_editor_property(key,value)
  u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);tex=u.load_asset(P+'/SourceMatch/T_SourceMask4K');assert tex
  for key,value in dict(srgb=False,compression_settings=u.TextureCompressionSettings.TC_GRAYSCALE,max_texture_size=4096,lod_bias=0).items():tex.set_editor_property(key,value)
  assert E.save_loaded_asset(tex,False)
 return tex

def apply(material):
 cfg=json.loads((R/'Art/flora_pine_match_settings.json').read_text())
 tex=source_mask()
 assert tex.get_editor_property('max_texture_size')==4096 and not tex.get_editor_property('srgb')
 material.set_editor_property('has_pixel_animation',cfg['has_pixel_animation'])
 for n in M.get_material_expressions(material):
  if isinstance(n,u.MaterialExpressionTextureSampleParameter2D) and str(n.get_editor_property('parameter_name'))=='SourceCoverage':n.set_editor_property('texture',tex)
  if isinstance(n,u.MaterialExpressionCustom):
   code=str(n.get_editor_property('code'))
   if 'float b=clamp(Soft' in code:
    code=FACING
    if not cfg['surface_only']:code=code.replace('saturate(A*','saturate('+str(cfg['coverage_gain'])+'*A*')
    n.set_editor_property('code',code)
   if 'uint2 p=uint2(Parameters.SvPosition.xy)' in code:
    # Existing baseline has no view-only correction. Replace a previous generated
    # section explicitly so rebuilds cannot compound opacity adjustments.
    start='\n#else\nCoverage*= '
    if start in code:
     a,b=code.split(start,1);code=a+'\n#endif'+b.split('\n#endif',1)[1]
    if cfg['surface_only'] and cfg['coverage_gain']!=1:
     code=code.replace('Coverage*=ShadowCoverage;\n#endif','Coverage*=ShadowCoverage;\n#else\nCoverage*= '+str(cfg['coverage_gain'])+';\n#endif')
    n.set_editor_property('code',code)
 assert not M.recompile_material(material);assert E.save_loaded_asset(material,False)
 return cfg
