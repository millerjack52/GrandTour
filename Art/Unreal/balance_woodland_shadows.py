"""Map-owned forest shadow continuity and daylight fill; preserve terrain/water."""
import unreal as u
from pathlib import Path
import json,sys,time,shutil,hashlib,traceback
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from woodland_lighting_audit import snapshot
from benmore_river_life_materials import props
BASE='/Game/GrandTour/ArtTests/BenmoreWoodland';OUT=ROOT/'Art/Export/BenmoreWoodland'
report={'ok':False,'driving_tested':False}
try:
    folder=ROOT/'Content/GrandTour/ArtTests/BenmoreWoodland'
    backup=ROOT/'Saved/BenmoreWoodlandBackups'/('shadows-'+str(time.time_ns()));backup.mkdir(parents=True)
    changed=[folder/'L_Benmore_Woodland.umap']+[folder/'Forest'/(prefix+str(k)+'.uasset') for prefix in ['SM_Fir_','M_FirFar_'] for k in range(3)]
    for p in changed:
        dest=backup/p.relative_to(folder);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
    report['backup']=str(backup)
    protected=[ROOT/'Content/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview.umap',ROOT/'Content/GrandTour/Demo/BenmoreRoads/Gaea/Morphology/DA_GC_WaterDomain.uasset']
    protected+=list((ROOT/'Content/GrandTour/Demo/BenmoreRoads/Gaea/NativeSurfaces').glob('M_NativeDomain*.uasset'))
    protected+=list(folder.glob('T_*.uasset'))+list(folder.glob('M_*.uasset'))
    hashes=lambda:{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    before=hashes()
    les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(BASE+'/L_Benmore_Woodland')
    actors=u.get_editor_subsystem(u.EditorActorSubsystem);allactors=actors.get_all_level_actors()
    report['before']=snapshot(allactors)
    # Section flags apply to the same reduced tree LODs already used for drawing.
    # Do not stop casting at the first LOD transition (formerly ~near-canopy range).
    sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);report['trees']=[]
    for k in range(3):
        far=u.load_asset(BASE+'/Forest/M_FirFar_'+str(k))
        u.MaterialEditingLibrary.set_material_usage(far,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
        u.MaterialEditingLibrary.recompile_material(far);assert u.EditorAssetLibrary.save_loaded_asset(far)
        mesh=u.load_asset(BASE+'/Forest/SM_Fir_'+str(k));assert sm.get_lod_count(mesh)==4
        for lod in range(4):
            for sec in range(mesh.get_num_sections(lod)):sm.enable_section_cast_shadow(mesh,True,lod,sec)
        assert u.EditorAssetLibrary.save_loaded_asset(mesh)
        report['trees'].append({'mesh':mesh.get_path_name(),'shadow_lods':[0,1,2,3],'vertices':[sm.get_number_verts(mesh,i) for i in range(4)]})
    sky=next(a for a in allactors if isinstance(a,u.SkyLight) and a.get_actor_label()=='Sky')
    sky.get_component_by_class(u.SkyLightComponent).set_intensity(8.0)
    sun=next(a for a in allactors if isinstance(a,u.DirectionalLight) and a.get_actor_label()=='Sun')
    props(sun.light_component,light_source_angle=1.25)
    pp=next((a for a in allactors if a.get_actor_label()=='Woodland_ShadowBalance'),None)
    if pp is None:pp=actors.spawn_actor_from_class(u.PostProcessVolume,u.Vector());pp.set_actor_label('Woodland_ShadowBalance')
    props(pp,unbound=True,priority=450.,blend_weight=1.,enabled=True)
    settings=pp.get_editor_property('settings')
    # Lift dark regions through local exposure, leaving the fixed daylight EV,
    # sun intensity, pigment and highlight grading to the existing map volume.
    props(settings,override_local_exposure_shadow_contrast_scale=True,local_exposure_shadow_contrast_scale=.70)
    pp.set_editor_property('settings',settings)
    assert les.save_current_level();assert les.load_level('/Engine/Maps/Entry');assert les.load_level(BASE+'/L_Benmore_Woodland')
    report['after']=snapshot(actors.get_all_level_actors())
    for k in range(3):
        mesh=u.load_asset(BASE+'/Forest/SM_Fir_'+str(k))
        assert all(sm.is_section_cast_shadow_enabled(mesh,lod,sec) for lod in range(4) for sec in range(mesh.get_num_sections(lod)))
    assert hashes()==before
    report.update(ok=True,protected_hashes=before,scope='Benmore Woodland lighting and owned fir shadow LODs only')
except Exception:
    report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'shadowbalance.json').write_text(json.dumps(report,indent=2));u.SystemLibrary.quit_editor()
