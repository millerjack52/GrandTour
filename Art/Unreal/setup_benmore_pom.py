"""Import linear height maps and save close gravel POM on the Benmore material."""
import unreal as u,json,sys,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_reference_surface import DEST,build
from benmore_gravel_pom import COLLECTION
OUT=ROOT/'Art/Export/BenmorePOM';OUT.mkdir(parents=True,exist_ok=True)
eal=u.EditorAssetLibrary;assets=u.AssetToolsHelpers.get_asset_tools();report={'ok':False}
def props(o,**kw):
    for k,v in kw.items():o.set_editor_property(k,v)
    return o
try:
    les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level('/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive')
    m=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Vegetation/M_Benmore_FullCover');assert m
    if not eal.does_asset_exist(DEST+'/M_Benmore_BeforePOM'):assert eal.duplicate_asset(m.get_path_name(),DEST+'/M_Benmore_BeforePOM')
    collection=u.load_asset(COLLECTION) if eal.does_asset_exist(COLLECTION) else assets.create_asset('MPC_Benmore_GravelPOM',DEST,u.MaterialParameterCollection,u.MaterialParameterCollectionFactoryNew())
    assert collection
    parameter=props(u.CollectionScalarParameter(),parameter_name='Enabled',default_value=1.0)
    collection.set_editor_property('scalar_parameters',[parameter]);assert eal.save_loaded_asset(collection)
    for name,file in [('T_Benmore_FineGravelH','gravel_floor_04_disp_2k.png'),('T_Benmore_LooseGravelH','gravel_floor_02_disp_2k.png')]:
        task=props(u.AssetImportTask(),filename=str(ROOT/'Art/Textures/RoadBenchmark'/file),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
        assets.import_asset_tasks([task]);t=u.load_asset(DEST+'/'+name);assert t
        props(t,srgb=False,compression_settings=u.TextureCompressionSettings.TC_GRAYSCALE,never_stream=True)
        assert eal.save_loaded_asset(t)
    report.update(build(m));errors=u.MaterialEditingLibrary.recompile_material(m);assert not errors,str(errors)
    assert eal.save_loaded_asset(m);assert les.save_current_level();report['ok']=True
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'setup-report.json').write_text(json.dumps(report,indent=2));u.SystemLibrary.quit_editor()
