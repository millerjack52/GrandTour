"""Landscape-streamed cover across the entire Benmore driving terrain."""
import unreal as u,json,time,traceback,sys
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreVegetation'
sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_ground_detail import build as build_ground_detail,DENSITIES
DEST='/Game/GrandTour/Demo/BenmoreRoads/Vegetation';LEVEL='/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive'
eal=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;assets=u.AssetToolsHelpers.get_asset_tools()
act=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem)
report={'ok':False,'level':LEVEL,'types':[]};phase='load';last=time.monotonic();started=last
u.EditorPythonScripting.set_keep_python_script_alive(True)
def props(o,**kw):
    for k,v in kw.items():o.set_editor_property(k,v)
    return o
def expr(m,cls,**kw):return props(mel.create_material_expression(m,cls),**kw)
def wire(a,b,name,out=''):assert mel.connect_material_expressions(a,out,b,name)
def custom(m,names,code,typ=u.CustomMaterialOutputType.CMOT_FLOAT3):
    return expr(m,u.MaterialExpressionCustom,inputs=[props(u.CustomInput(),input_name=n) for n in names],code=code,output_type=typ)
def finish(error=None):
    global phase
    phase='finished';report['ok']=error is None
    if error:report['error']=error;u.log_error(error)
    (OUT/'setup-report.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
def tick(dt):
    global phase,last,world,land
    now=time.monotonic()
    try:
        if now-started>700:raise RuntimeError('Vegetation setup timeout')
        if phase=='load':
            phase='building';assert les.load_level(LEVEL);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
            assert world.get_path_name().startswith(LEVEL+'.')
            eal.make_directory(DEST)
            # Keep a reversible baseline before adding terrain-wide cover.
            backup='/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_BeforeFullVegetation'
            if not eal.does_asset_exist(backup):assert u.EditorLoadingAndSavingUtils.save_map(world,backup)
            land=next(a for a in act.get_all_level_actors() if isinstance(a,u.Landscape))
            task=props(u.AssetImportTask(),filename=str(OUT/'T_Benmore_VegetationMask.png'),destination_path=DEST,destination_name='T_Benmore_VegetationMask',automated=True,replace_existing=True,save=True)
            assets.import_asset_tasks([task]);tex=u.load_asset(DEST+'/T_Benmore_VegetationMask')
            props(tex,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,filter=u.TextureFilter.TF_BILINEAR,never_stream=True);eal.save_loaded_asset(tex)
            mpath=DEST+'/M_Benmore_FullCover';m=u.load_asset(mpath) if eal.does_asset_exist(mpath) else eal.duplicate_asset('/Game/GrandTour/Demo/BenmoreRoads/M_Benmore_RoadLandscape',mpath)
            # Refresh the copy so re-running creates one grass output only.
            for node in mel.get_material_expressions(m) if hasattr(mel,'get_material_expressions') else []:
                if isinstance(node,u.MaterialExpressionLandscapeGrassOutput):mel.delete_material_expression(m,node)
            p=expr(m,u.MaterialExpressionWorldPosition)
            uv=custom(m,['P'],'return ((P.xy+125000)/250000*2016+.5)/2017;',u.CustomMaterialOutputType.CMOT_FLOAT2);wire(p,uv,'P')
            mask=expr(m,u.MaterialExpressionTextureSample,texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR);wire(uv,mask,'UVs')
            # Use the approved L_TussockStyle meshes and their authored materials.
            # Empty overrides preserve the vertex-painted source appearance.
            source='/Game/GrandTour/ArtTests/TussockStyle'
            variants=['Straw','Rust','Weathered','Fine']
            report['source_level']=source+'/L_TussockStyle'
            rows=[('LowGrass',3,175,6500,11000,.85,1.5,'R',-1),('CrownTussock',0,28,18000,32000,.65,1.2,'G',-1),('ShaggyTussock',1,22,21000,38000,.7,1.25,'G',-1),('TallClumps',2,14,22000,45000,.8,1.4,'B',-1),('DistantTussock',0,3,65000,95000,.9,1.5,'G',2)]
            entries=[]
            for name,kind,density,start,end,lo,hi,channel,lod in rows:
                density=DENSITIES[name]
                path=DEST+'/LGT_Benmore_'+name
                grass=u.load_asset(path) if eal.does_asset_exist(path) else assets.create_asset('LGT_Benmore_'+name,DEST,u.LandscapeGrassType,u.LandscapeGrassTypeFactory())
                mesh=u.load_asset(source+'/SM_TS_'+variants[kind]);assert mesh
                v=props(u.GrassVariety(),grass_mesh=mesh,override_materials=[],grass_density=u.PerPlatformFloat(default=density),start_cull_distance=u.PerPlatformInt(default=start),end_cull_distance=u.PerPlatformInt(default=end),use_grid=False,random_rotation=True,align_to_surface=True,min_lod=lod,scaling=u.GrassScaling.LOCK_XY,scale_x=u.FloatInterval(min=lo,max=hi),scale_y=u.FloatInterval(min=lo,max=hi),scale_z=u.FloatInterval(min=lo*.85,max=hi),cast_dynamic_shadow=False,cast_contact_shadow=True,affect_distance_field_lighting=False,receives_decals=False)
                props(grass,grass_varieties=[v],enable_density_scaling=True);eal.save_loaded_asset(grass)
                entries.append(props(u.GrassInput(),name=name,grass_type=grass));report['types'].append({'name':name,'density_per_100m2':density,'cull_m':end/100,'mesh':mesh.get_path_name(),'mask':channel})
            gout=expr(m,u.MaterialExpressionLandscapeGrassOutput,grass_types=entries)
            for row in rows:wire(mask,gout,row[0],row[7])
            report['ground_detail']=build_ground_detail(m)
            assert not mel.recompile_material(m);eal.save_loaded_asset(m);land.set_editor_property('landscape_material',m)
            # Replace the dense roadside-only grass with the unified cover, retaining stones/posts.
            removed=0
            for a in act.get_all_level_actors():
                if a.get_actor_label()!='Benmore_Roadside_ArtSample':continue
                for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
                    mesh=c.get_editor_property('static_mesh')
                    if mesh and mesh.get_name().startswith('SM_DT_'):removed+=c.get_instance_count();c.destroy_component(a)
            report['replaced_roadside_instances']=removed
            u.SystemLibrary.execute_console_command(world,'grass.FlushCache')
            phase='warm';last=time.monotonic()
        elif phase=='warm' and now-last>60:
            phase='saving';assert les.save_current_level();finish()
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
