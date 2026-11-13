"""Read the saved Benmore material graphs without saving any asset or map."""
import unreal as u
import os,json,hashlib,traceback
from pathlib import Path

ROOT=Path(u.Paths.project_dir()).resolve()
OUT=Path(os.environ['GT_BENMORE_MATERIAL_AUDIT']).resolve()
assert OUT.parent==ROOT/'Art/Export/BenmoreGaea' and not OUT.exists()
OUT.mkdir()
report=dict(ok=False,assets=[],read_only=True)
mel=u.MaterialEditingLibrary
try:
    assert not u.EditorLevelLibrary.get_game_world()
    world=u.EditorLoadingAndSavingUtils.load_map('/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview')
    assert world
    report['landscapes']=[]
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.LandscapeProxy):
        settings={key:actor.get_editor_property(key) for key in (
            'bEnableNanite','MaxLODLevel','LOD0ScreenSize','LOD0DistributionSetting','LODDistributionSetting')}
        material=actor.get_editor_property('LandscapeMaterial')
        components=[dict(name=c.get_name(),forced_lod=c.get_editor_property('ForcedLOD'),
                         lod_bias=c.get_editor_property('LODBias'))
                    for c in actor.get_components_by_class(u.LandscapeComponent)]
        report['landscapes'].append(dict(actor=actor.get_path_name(),settings=settings,
            material=material.get_path_name() if material else None,components=components))
    sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    report['willows']=[]
    report['static_meshes']={}
    report['static_components']=[]
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
        for c in actor.get_components_by_class(u.StaticMeshComponent):
            mesh=c.static_mesh
            if not mesh:continue
            key=mesh.get_path_name()
            if key not in report['static_meshes']:
                report['static_meshes'][key]=dict(
                    nanite=mesh.get_editor_property('nanite_settings').enabled,
                    vertices_by_lod=[sm.get_number_verts(mesh,i) for i in range(sm.get_lod_count(mesh))],
                    lod_screen_sizes=list(sm.get_lod_screen_sizes(mesh)))
            report['static_components'].append(dict(component=c.get_path_name(),actor=actor.get_actor_label(),
                mesh=key,visible=c.is_visible(),actor_hidden=actor.get_editor_property('hidden'),
                instances=c.get_instance_count() if isinstance(c,u.InstancedStaticMeshComponent) else 1,
                generated_grass=isinstance(c,u.GrassInstancedStaticMeshComponent)))
            if '/Scenery/SM_Willow_' not in key:continue
            materials=[]
            for material in c.get_materials():
                while isinstance(material,u.MaterialInstance):material=material.get_editor_property('parent')
                assert isinstance(material,u.Material)
                materials.append(dict(asset=material.get_path_name(),
                    nanite_usage=material.get_editor_property('used_with_nanite'),
                    wpo_connected=bool(mel.get_material_property_input_node(material,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)),
                    blend=str(material.get_editor_property('blend_mode'))))
            report['willows'].append(dict(component=c.get_path_name(),mesh=mesh.get_path_name(),
                visible=c.is_visible(),actor_hidden=actor.get_editor_property('hidden'),
                instances=c.get_instance_count() if isinstance(c,u.InstancedStaticMeshComponent) else 1,
                nanite=mesh.get_editor_property('nanite_settings').enabled,
                vertices_by_lod=[sm.get_number_verts(mesh,i) for i in range(sm.get_lod_count(mesh))],
                lod_screen_sizes=list(sm.get_lod_screen_sizes(mesh)),
                raytracing=c.get_editor_property('visible_in_ray_tracing'),materials=materials))
    for name in ('M_GC_Terrain','M_GC_Hills','M_GC_DomainRiver','M_GC_DomainLake'):
        path='/Game/GrandTour/Demo/BenmoreRoads/Gaea/ShoreRefinement/'+name
        file=ROOT/'Content'/Path(path.removeprefix('/Game/')).with_suffix('.uasset')
        before=hashlib.sha256(file.read_bytes()).hexdigest()
        material=u.load_asset(path)
        assert isinstance(material,u.Material),path
        roots={key:mel.get_material_property_input_node(material,getattr(u.MaterialProperty,key))
               for key in ('MP_BASE_COLOR','MP_NORMAL','MP_ROUGHNESS','MP_EMISSIVE_COLOR',
                           'MP_WORLD_POSITION_OFFSET','MP_OPACITY_MASK','MP_MATERIAL_ATTRIBUTES')}
        reachable=set()
        pending=[node for node in roots.values() if node]
        while pending:
            node=pending.pop()
            if node.get_name() in reachable:continue
            reachable.add(node.get_name())
            pending.extend(n for n in mel.get_inputs_for_material_expression(material,node) if n)
        nodes=[]
        for node in mel.get_material_expressions(material):
            row=dict(name=node.get_name(),kind=node.get_class().get_name(),
                     description=str(node.get_editor_property('desc')),
                     reachable=node.get_name() in reachable,
                     inputs=[n.get_name() if n else None for n in mel.get_inputs_for_material_expression(material,node)])
            if isinstance(node,u.MaterialExpressionCustom):
                row.update(code=node.get_editor_property('code'),
                           input_names=[str(i.get_editor_property('input_name')) for i in node.get_editor_property('inputs')])
            if isinstance(node,u.MaterialExpressionCollectionParameter):
                collection=node.get_editor_property('collection')
                row.update(collection=collection.get_path_name() if collection else None,
                           parameter=str(node.get_editor_property('parameter_name')))
            if isinstance(node,(u.MaterialExpressionTextureSample,u.MaterialExpressionTextureObject)):
                texture=node.get_editor_property('texture')
                row['texture']=texture.get_path_name() if texture else None
            nodes.append(row)
        after=hashlib.sha256(file.read_bytes()).hexdigest()
        assert before==after,'Read-only audit changed a package'
        report['assets'].append(dict(asset=path,sha256=before,unchanged=True,
            roots={key:node.get_name() if node else None for key,node in roots.items()},nodes=nodes))
    report['ok']=True
except Exception:
    report['error']=traceback.format_exc();u.log_error(report['error'])
finally:
    (OUT/'audit-report.json').write_text(json.dumps(report,indent=2))
    u.SystemLibrary.quit_editor()
