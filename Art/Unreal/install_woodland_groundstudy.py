"""Install the bounded sunny-ground and understory study, with recoverable backups."""
import unreal as u
from pathlib import Path
import sys,json,time,traceback,shutil,hashlib
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import benmore_woodland_materials as mat
from benmore_river_life_materials import props
BASE=mat.BASE;OUT=mat.OUT;assets=u.EditorAssetLibrary
les=u.get_editor_subsystem(u.LevelEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem)
report=dict(ok=False,driving_tested=False)
try:
    target=ROOT/'Content/GrandTour/ArtTests/BenmoreWoodland'
    backup=ROOT/'Saved/BenmoreWoodlandBackups'/('groundstudy-'+str(time.time_ns()))
    shutil.copytree(target,backup);report['backup']=str(backup)
    protected=[ROOT/'Content/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview.umap',ROOT/'Content/GrandTour/Demo/BenmoreRoads/Gaea/Morphology/DA_GC_WaterDomain.uasset']
    protected+=list((ROOT/'Content/GrandTour/Demo/BenmoreRoads/Gaea/NativeSurfaces').glob('M_NativeDomain*.uasset'))
    protected+=list((target/'Forest').glob('*.uasset'))
    protected+=[target/('T_'+s+'.uasset') for s in ['paint','rest','macro']]
    hashes=lambda:{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    before=hashes()
    assert les.load_level(BASE+'/L_Benmore_Woodland')
    from woodland_lighting_audit import snapshot
    (OUT/'lighting-before.json').write_text(json.dumps(snapshot(actors.get_all_level_actors()),indent=2))
    s=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTLandscapeSurface))
    style=mat.texture('style_groundstudy')
    assert u.GTLandscapeSurfaceSetupLibrary.import_material_atlas(s,style)
    s.set_editor_property('grass_is_visual_cover',True)
    import woodland_sunlit_ground
    report['materials']=woodland_sunlit_ground.install(style)
    grass=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTMixedGroundDetails) and a.generate_around_player)
    grass.set_editor_property('grass_spacing_cm',45.)
    # Retain the recovered wind/contact shader on the existing player-following grass.
    assert grass.grass_material.get_name()=='M_GrassRecovered'
    for a in list(actors.get_all_level_actors()):
        if a.get_actor_label() in ['Woodland_GroundStudy_Understory','Woodland_GroundStudy_Tufts']:actors.destroy_actor(a)
    owner=actors.spawn_actor_from_class(u.Actor,u.Vector());owner.set_actor_label('Woodland_GroundStudy_Understory')
    src=['/Game/OWGame/Dev/DressingLab/Trees/SM_OWBush_Birch_A',
         '/Game/GrandTour/ArtTests/MudRoad/MixedSurfaces/SM_NativeShortGrass',
         '/Game/GrandTour/ArtTests/MudRoads/SM_MRD_Branch0']
    entries=json.loads((OUT/'groundstudy-placement.json').read_text());report['understory']=[]
    sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    for kind,path in enumerate(src):
        source=u.load_asset(path);assert source,path
        mesh=source
        if kind!=1:
            dest=BASE+'/Understory/SM_'+('BirchBush' if kind==0 else 'Branch')
            mesh=u.load_asset(dest) or assets.duplicate_asset(path,dest)
            ns=sm.get_nanite_settings(mesh);ns.enabled=False;sm.set_nanite_settings(mesh,ns,True)
            opts=props(u.StaticMeshReductionOptions(),auto_compute_lod_screen_size=False,reduction_settings=[props(u.StaticMeshReductionSettings(),percent_triangles=p,screen_size=v) for p,v in [(1,1),(.45,.3),(.16,.12)]])
            assert sm.set_lods(mesh,opts)>=3
            sm.remove_collisions(mesh);assert assets.save_loaded_asset(mesh)
        b=mesh.get_bounds();ts=[]
        for item in entries:
            if item['kind']!=kind:continue
            px,py,pz=item['p'];sc=item['height_cm']/max(1,2*b.box_extent.z)
            # Native grass accent height is varied; woody debris is embedded.
            ts.append(u.Transform(location=u.Vector(px,py,pz-(b.origin.z-b.box_extent.z)*sc-3),rotation=u.Rotator(yaw=item['yaw']),scale=u.Vector(sc,sc,sc)))
        if not ts:continue
        if kind==1:
            tuft=actors.spawn_actor_from_class(u.GTMixedGroundDetails,u.Vector());tuft.set_actor_label('Woodland_GroundStudy_Tufts')
            props(tuft,surface=s,grass_material=grass.grass_material,generate_around_player=False)
            c=tuft.grass;c.set_static_mesh(mesh);c.set_material(0,grass.grass_material);c.add_instances(ts,False,True)
        else:c=u.GTVegetationSubsystem.add_tagged_instances(owner,mesh,ts,'GroundStudyUnderstory','NoCollision',False)
        c.set_cull_distances(2400 if kind==1 else 5000,3200 if kind==1 else 7000)
        c.set_editor_property('visible_in_ray_tracing',False);c.set_editor_property('affect_distance_field_lighting',False)
        # Both grass layers use recovered wind and persistent contact state.
        if kind==0:
            tintpath=BASE+'/Understory/MI_BirchBush'
            tint=u.load_asset(tintpath) or assets.duplicate_asset('/Game/GrandTour/Dressing/Materials/MI_GT_Leaf_Bush_OWBirch_Summer',tintpath)
            if tint:
                for key,rgb in [('TopColor',(.025,.055,.012)),('NoiseColor',(.035,.07,.018)),('SubsurfaceColor',(.012,.026,.006))]:
                    u.MaterialEditingLibrary.set_material_instance_vector_parameter_value(tint,key,u.LinearColor(*rgb,1))
                u.MaterialEditingLibrary.update_material_instance(tint);assert assets.save_loaded_asset(tint)
                for slot in range(c.get_num_materials()):
                    old=c.get_material(slot)
                    if old and any(k in old.get_name().lower() for k in ['leaf','leave','foliage']):c.set_material(slot,tint)
        report['understory'].append(dict(kind=kind,mesh=mesh.get_path_name(),instances=len(ts),vertices=[sm.get_number_verts(mesh,i) for i in range(sm.get_lod_count(mesh))]))
    assert les.save_current_level();assert les.load_level('/Engine/Maps/Entry');assert les.load_level(BASE+'/L_Benmore_Woodland')
    s=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTLandscapeSurface))
    assert s.grass_is_visual_cover and hashes()==before
    report.update(ok=True,protected_hashes=before,scope='Road / ford / bog study areas; original paint and water unchanged',grass_spacing_cm=45,physics='Existing mud equations; opt-in vegetation/soil separation')
except Exception:
    report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'groundstudy.json').write_text(json.dumps(report,indent=2));u.SystemLibrary.quit_editor()
