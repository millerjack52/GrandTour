"""Add map-owned, non-colliding verge dressing and rebuild shoulder shading."""
import unreal as u,json,sys,traceback,time
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_reference_surface import build,DEST
OUT=ROOT/'Art/Export/BenmoreVerges';report={'ok':False};phase='load';last=time.monotonic()
les=u.get_editor_subsystem(u.LevelEditorSubsystem);act=u.get_editor_subsystem(u.EditorActorSubsystem);eal=u.EditorAssetLibrary
u.EditorPythonScripting.set_keep_python_script_alive(True)
def finish(error=None):
    global phase
    phase='done';report['ok']=error is None
    if error:report['error']=error;u.log_error(error)
    (OUT/'setup-report.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
def tick(dt):
    global phase,last
    try:
        if phase=='load':
            phase='building';assert les.load_level('/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive')
            m=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Vegetation/M_Benmore_FullCover')
            if not eal.does_asset_exist(DEST+'/M_Benmore_BeforeVergeDetail'):assert eal.duplicate_asset(m.get_path_name(),DEST+'/M_Benmore_BeforeVergeDetail')
            report.update(build(m));assert not u.MaterialEditingLibrary.recompile_material(m);assert eal.save_loaded_asset(m)
            mel=u.MaterialEditingLibrary;assets=u.AssetToolsHelpers.get_asset_tools()
            path=DEST+'/M_Benmore_VergeStone'
            stone_mat=u.load_asset(path) if eal.does_asset_exist(path) else assets.create_asset('M_Benmore_VergeStone',DEST,u.Material,u.MaterialFactoryNew())
            mel.delete_all_material_expressions(stone_mat)
            vc=mel.create_material_expression(stone_mat,u.MaterialExpressionVertexColor)
            random=mel.create_material_expression(stone_mat,u.MaterialExpressionPerInstanceRandom)
            color=mel.create_material_expression(stone_mat,u.MaterialExpressionCustom)
            inputs=[]
            for name in ['Face','Variation']:
                ci=u.CustomInput();ci.set_editor_property('input_name',name);inputs.append(ci)
            color.set_editor_property('inputs',inputs);color.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
            color.set_editor_property('code','return lerp(float3(.14,.145,.13),float3(.29,.28,.245),Variation)*(.82+Face.r*.8);')
            assert mel.connect_material_expressions(vc,'',color,'Face');assert mel.connect_material_expressions(random,'',color,'Variation')
            assert mel.connect_material_property(color,'',u.MaterialProperty.MP_BASE_COLOR)
            for prop,val in [(u.MaterialProperty.MP_ROUGHNESS,.94),(u.MaterialProperty.MP_SPECULAR,.12)]:
                node=mel.create_material_expression(stone_mat,u.MaterialExpressionConstant);node.set_editor_property('r',val);mel.connect_material_property(node,'',prop)
            assert not mel.recompile_material(stone_mat);assert eal.save_loaded_asset(stone_mat)
            for a in act.get_all_level_actors():
                if a.get_actor_label()=='Benmore_RoadVergeDetail':act.destroy_actor(a)
            group=act.spawn_actor_from_class(u.Actor,u.Vector());group.set_actor_label('Benmore_RoadVergeDetail')
            data=json.loads((OUT/'placements.json').read_text());report['counts']=data['counts'];report['meshes']={}
            for name in sorted(set(r['mesh'] for r in data['instances'])):
                stone=name.startswith('Stone')
                path='/Game/GrandTour/ArtTests/GravelRoad/SM_GR_'+name if stone else '/Game/GrandTour/ArtTests/TussockStyle/SM_TS_'+name
                mesh=u.load_asset(path);assert mesh,path
                rows=[r for r in data['instances'] if r['mesh']==name]
                transforms=[u.Transform(u.Vector(*[v*100 for v in r['xyz']]),u.Rotator(yaw=r['yaw']),u.Vector(*r['scale'])) for r in rows]
                c=u.GTVegetationSubsystem.add_tagged_instances(group,mesh,transforms,'BenmoreVergeDetail','NoCollision',False)
                if stone:c.set_material(0,stone_mat)
                c.set_cull_distances(6500 if stone else 10000,11000 if stone else 18000)
                for key,value in dict(affect_distance_field_lighting=False,visible_in_ray_tracing=False,receives_decals=False).items():c.set_editor_property(key,value)
                assert c.get_instance_count()==len(rows);report['meshes'][name]=len(rows)
            report['instance_total']=sum(report['meshes'].values());phase='warm';last=time.monotonic()
        elif phase=='warm' and time.monotonic()-last>20:
            phase='saving';assert les.save_current_level();finish()
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
