import unreal as u,json
from pathlib import Path
root=Path(u.Paths.project_dir()).resolve();out=root/'Saved/LidarAuthoringQA/RS7Ground';out.mkdir(exist_ok=True)
textures=[]
for folder in ['/Game/GrandTour/ArtTests/GroundDetail/Bakes','/Game/GrandTour/ArtTests/BenmoreWoodland','/Game/GrandTour/Demo/BenmoreRoads/ReferenceSurface']:
 for path in u.EditorAssetLibrary.list_assets(folder,recursive=False):
  if '/T_' not in path:continue
  t=u.load_asset(path)
  if not isinstance(t,u.Texture2D):continue
  props={}
  for k in ['lod_bias','max_texture_size','srgb','compression_settings','filter','mip_gen_settings','never_stream','lod_group']:
   props[k]=str(t.get_editor_property(k))
  data=t.get_editor_property('asset_import_data')
  textures.append(dict(path=path,size=[t.blueprint_get_size_x(),t.blueprint_get_size_y()],settings=props,source=list(data.extract_filenames()) if data else []))
(out/'texture-inventory.json').write_text(json.dumps(textures,indent=2))
print('BANK_GROUND_TEXTURE_INVENTORY',len(textures))
