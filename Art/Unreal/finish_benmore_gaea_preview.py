"""Refresh only the review creek edges/shading; terrain and placements stay fixed."""
import unreal as u
from pathlib import Path
import sys,json,time,traceback
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreGaea/integration'
sys.path.insert(0,str(ROOT/'Art/Unreal'))
import benmore_gaea_materials as mats
DEST=mats.DEST;LEVEL=DEST+'/L_Benmore_GaeaReview'
act=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem)
eal=u.EditorAssetLibrary;assets=u.AssetToolsHelpers.get_asset_tools();phase='load';last=time.monotonic();report={'ok':False}
u.EditorPythonScripting.set_keep_python_script_alive(True)
def props(o,**kw):
    for k,v in kw.items():o.set_editor_property(k,v)
    return o
def tick(dt):
    global phase,last
    try:
        if phase=='load':
            phase='working';assert les.load_level(LEVEL)
            world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
            for name in ['T_Gaea_Flow','T_Gaea_Banks','T_Gaea_VegetationMask']:
                task=props(u.AssetImportTask(),filename=str(OUT/(name+'.png')),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
                assets.import_asset_tasks([task]);t=u.load_asset(DEST+'/'+name)
                props(t,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP,filter=u.TextureFilter.TF_BILINEAR,never_stream=True)
                assert eal.save_loaded_asset(t)
            material=mats.water(u.load_asset(DEST+'/T_Gaea_Flow'),u.load_asset(DEST+'/T_Gaea_Banks'))
            name='SM_Benmore_GaeaCreeks';u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
            task=props(u.AssetImportTask(),filename=str(OUT/(name+'.fbx')),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
            opt=props(u.FbxImportUI(),import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,import_animations=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
            props(opt.static_mesh_import_data,combine_meshes=True,convert_scene=True,convert_scene_unit=True,auto_generate_collision=False,generate_lightmap_u_vs=False,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
            task.options=opt;assets.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/'+name);mesh.set_material(0,material);assert eal.save_loaded_asset(mesh)
            a=next(a for a in act.get_all_level_actors() if a.get_actor_label()=='Benmore_Gaea_CreekSurface');a.static_mesh_component.set_static_mesh(mesh);a.static_mesh_component.set_material(0,material);a.static_mesh_component.set_collision_profile_name('NoCollision')
            phase='save';last=time.monotonic()
        elif phase=='save' and time.monotonic()-last>12:
            phase='saving'
            world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
            assert u.EditorLoadingAndSavingUtils.save_map(world,LEVEL)
            report.update(ok=True,scope='Creek material, mask filtering and water mesh only',terrain_changed=False,placements_changed=False)
            (OUT/'water-refinement-report.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);phase='done'
            review=ROOT/'Art/Unreal/check_benmore_gaea_review.py'
            exec(compile(review.read_text(),str(review),'exec'),{'__file__':str(review)})
    except Exception:
        phase='done';report['ok']=False;report['error']=traceback.format_exc();u.log_error(report['error']);(OUT/'water-refinement-report.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
handle=u.register_slate_post_tick_callback(tick)
