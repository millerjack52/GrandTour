import unreal as u,json
from pathlib import Path
out=Path(u.Paths.project_dir()).resolve()/'Art/Export/BenmoreVegetation'
src='/Game/ANGRY_MESH/StylizedPack_MeadowEnvironment/Textures/Landscape/'
report={}
for name in ['T_Landscape_DryGrass_01_A','T_Landscape_Grass_01_N','T_Landscape_Grass_01_R']:
    tex=u.load_asset(src+name);assert tex
    task=u.AssetExportTask();task.object=tex;task.filename=str(out/(name+'.tga'));task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.TextureExporterTGA()
    report[name]=u.Exporter.run_asset_export_task(task)
(out/'ground-inspection.json').write_text(json.dumps(report,indent=2))
u.SystemLibrary.quit_editor()
