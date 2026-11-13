"""VQ2 focused visual install in the actual LiDAR map. No terrain regeneration."""
import unreal as u
from pathlib import Path
import sys, json, time, traceback, shutil, gc, os
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
BASE='/Game/GrandTour/ArtTests/LidarStudy'
QA=ROOT/'Saved/LidarAuthoringQA/VQ2';QA.mkdir(parents=True,exist_ok=True)
assets=u.EditorAssetLibrary;actors=u.get_editor_subsystem(u.EditorActorSubsystem)
les=u.get_editor_subsystem(u.LevelEditorSubsystem);sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
CHECK=os.environ.get('GT_VQ2_CHECK')=='1'
report={'ok':False};busy=False;deadline=0
def save(): (QA/('check.json' if CHECK else 'install.json')).write_text(json.dumps(report,indent=2))
def inventory():
    return {a.get_actor_label()+'/'+c.get_name():c.get_instance_count()
        for a in actors.get_all_level_actors() if a.get_actor_label() in ('LidarStudy_Forest','LidarStudy_Understory')
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent)}
def run():
    if CHECK:
        import lidar_canopy_assets as canopy
        mel=u.MaterialEditingLibrary;rows=[]
        assert canopy.cached()
        for k in range(4):
            assert canopy.shade_far_card(k)
            m=u.load_asset(BASE+'/CanopyKit/M_FirFar_'+str(k))
            normal=mel.get_material_property_input_node(m,u.MaterialProperty.MP_NORMAL)
            assert isinstance(normal,u.MaterialExpressionTransform)
            before=len(mel.get_material_expressions(m))
            canopy.shade_far_card(k);canopy.tint_far_card(k,(.42,.40,.38) if k==3 else (.55,.62,.50))
            assert before==len(mel.get_material_expressions(m))
            rows.append(dict(kind=k,normal=normal.get_class().get_name(),nodes=before))
        report.update(ok=True,materials=rows,cache_valid=True);save();yield 5;return
    backup=ROOT/'Saved/LidarAuthoringBackups'/('VQ2-'+str(time.time_ns()));backup.mkdir(parents=True)
    content=ROOT/'Content/GrandTour/ArtTests/LidarStudy'
    for folder in ('CanopyKit','GrassGS3'):
        if (content/folder).exists():shutil.copytree(content/folder,backup/folder)
    for name in ('L_LidarStudy.umap','M_Terrain.uasset','M_Detail.uasset','M_LP6_Foliage.uasset','MI_NZ_Foliage_Bush.uasset','MI_NZ_Foliage_Canopy.uasset'):
        if (content/name).exists():shutil.copy2(content/name,backup/name)
    report['backup']=str(backup);save()
    import lidar_canopy_assets as canopy
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    meshes=yield from canopy.build(world,force=False)
    import lidar_level_polish
    report['foliage_materials']=lidar_level_polish.foliage_materials();yield 2
    assert les.load_level(BASE+'/L_LidarStudy');yield 2
    before=inventory()
    author=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTProceduralGround))
    digest=str(author.output_digest)
    forest=next(a for a in actors.get_all_level_actors() if a.get_actor_label()=='LidarStudy_Forest')
    leaf=u.load_asset(BASE+'/MI_NZ_Foliage_Canopy');bark=u.load_asset(BASE+'/MI_NZ_Bark_Spar')
    rows=[]
    for c in forest.get_components_by_class(u.InstancedStaticMeshComponent):
        mesh=c.static_mesh
        if not mesh or not mesh.get_name().startswith('SM_Canopy_'):continue
        k=int(mesh.get_name().rsplit('_',1)[1]);mesh=meshes[k];c.set_static_mesh(mesh)
        for i,slot in enumerate(mesh.get_editor_property('static_materials')):
            mat=slot.get_editor_property('material_interface')
            if mat and mat.get_name()=='M_NZ_Foliage':mat=leaf
            elif k==3 and mat and mat.get_name()=='M_NZ_Bark':mat=bark
            c.set_material(i,mat)
        for lod in range(4):
            for sec in range(mesh.get_num_sections(lod)):sm.enable_section_cast_shadow(mesh,lod<3,lod,sec)
        assert assets.save_loaded_asset(mesh)
        rows.append(dict(kind=k,instances=c.get_instance_count(),screens=list(sm.get_lod_screen_sizes(mesh)),triangles=[mesh.get_num_triangles(i) for i in range(4)]))
    import lidar_grass_gs3
    report['grass']=lidar_grass_gs3.install(True);yield 5
    assert inventory()==before,'Foliage instance counts changed'
    assert str(author.output_digest)==digest,'Terrain changed'
    import canopy_depth
    if canopy_depth.enabled():report['canopy_depth']=canopy_depth.apply()
    assert les.save_current_level()
    report.update(forest=rows,ground_digest=digest,instances_unchanged=before,canopy_cache_valid=bool(canopy.cached()),saved=True)
    assert report['canopy_cache_valid']
    save()
    forest=author=mesh=meshes=c=world=None;gc.collect()
    les.load_level('/Engine/Maps/Entry');yield 3
    assert les.load_level(BASE+'/L_LidarStudy');yield 2
    assert inventory()==before,'Reload changed foliage counts'
    grass=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTMixedGroundDetails) and a.generate_around_player)
    assert grass.rank_clump_mesh.get_name()=='SM_GS3_Verge'
    assert grass.rank_material.get_name()=='M_GS3_Verge'
    # Reapplying materials must not grow shader graphs.
    mel=u.MaterialEditingLibrary
    mats=[u.load_asset(BASE+'/CanopyKit/M_FirFar_'+str(k)) for k in range(4)]
    counts=[len(mel.get_material_expressions(m)) for m in mats]
    for k in range(4):assert canopy.shade_far_card(k)
    assert counts==[len(mel.get_material_expressions(m)) for m in mats]
    report.update(ok=True,reloaded=True,far_shader_idempotent=True);save()
    grass=mats=None;gc.collect();les.load_level('/Engine/Maps/Entry');yield 4
steps=run()
def tick(dt):
    global busy,deadline,steps
    if busy:return
    busy=True
    try:
        if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
    except StopIteration:
        u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
    except Exception:
        report.update(ok=False,error=traceback.format_exc());save();u.log_error(report['error'])
        u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
    finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
