"""Repair the audited vehicle material's missing skeletal shader permutation.

Run only in the sole editor, outside Play. No graph, palette or mesh changes.
The package backup and hashes make this flag-only change independently reversible.
"""
import unreal as u
import os,json,hashlib,shutil,traceback
from pathlib import Path

ROOT=Path(u.Paths.project_dir()).resolve()
OUT=Path(os.environ['GT_BENMORE_USAGE_OUT']).resolve()
assert OUT.parent==ROOT/'Art/Export/BenmoreGaea' and not OUT.exists()
OUT.mkdir()
report=dict(ok=False,scope='Skeletal usage on M_GT_Vehicle',assets=[])


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def graph(m):
    return [(n.get_name(),n.get_class().get_name(),n.get_editor_property('code')
             if isinstance(n,u.MaterialExpressionCustom) else None)
            for n in u.MaterialEditingLibrary.get_material_expressions(m)]


try:
    assert not u.EditorLevelLibrary.get_game_world()
    path='/Game/GrandTour/Materials/M_GT_Vehicle'
    material=u.load_asset(path)
    assert isinstance(material,u.Material)
    file=ROOT/'Content/GrandTour/Materials/M_GT_Vehicle.uasset'
    backup=OUT/file.name
    shutil.copy2(file,backup)
    before=graph(material)
    row=dict(asset=path,file=str(file),backup=str(backup),before_sha256=sha(file),
        used_with_skeletal_mesh_before=material.get_editor_property('used_with_skeletal_mesh'))
    report['assets'].append(row)
    (OUT/'install-report.json').write_text(json.dumps(report,indent=2))
    u.MaterialEditingLibrary.set_material_usage(material,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    assert material.get_editor_property('used_with_skeletal_mesh')
    assert graph(material)==before
    if not row['used_with_skeletal_mesh_before']:
        assert u.EditorAssetLibrary.save_loaded_asset(material)
    row.update(saved=not row['used_with_skeletal_mesh_before'],after_sha256=sha(file))
    # Read-only audit of the level's actual bindings. Imported LOD count alone
    # does not prove that a cheaper LOD is selected during a driving frame.
    world=u.EditorLoadingAndSavingUtils.load_map('/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview')
    assert world
    editor=u.get_editor_subsystem(u.EditorActorSubsystem)
    meshes=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
    report['vehicle_lod_audit']=[]
    report['grass_varieties']=[]
    seen_grass=set()
    materials={}
    for actor in editor.get_all_level_actors():
        for c in actor.get_components_by_class(u.SkeletalMeshComponent):
            mesh=c.get_skeletal_mesh_asset()
            if not mesh:continue
            count=meshes.get_lod_count(mesh)
            report['vehicle_lod_audit'].append(dict(actor=actor.get_actor_label(),mesh=mesh.get_path_name(),
                lod_vertices=[meshes.get_num_verts(mesh,i) for i in range(count)],
                lod_sections=[meshes.get_num_sections(mesh,i) for i in range(count)],
                forced_lod=c.get_editor_property('forced_lod_model'),min_lod=c.get_editor_property('min_lod_model')))
        for c in actor.get_components_by_class(u.PrimitiveComponent):
            for i in range(c.get_num_materials()):
                m=c.get_material(i)
                while isinstance(m,u.MaterialInstance):m=m.get_editor_property('parent')
                if isinstance(m,u.Material):materials[m.get_path_name()]=m
    report['material_statistics']={}
    report['material_graphs']={}
    for name,m in materials.items():
        for node in u.MaterialEditingLibrary.get_material_expressions(m):
            if not isinstance(node,u.MaterialExpressionLandscapeGrassOutput):continue
            for entry in node.get_editor_property('grass_types'):
                grass=entry.get_editor_property('grass_type')
                if not grass or grass.get_path_name() in seen_grass:continue
                seen_grass.add(grass.get_path_name())
                for v in grass.get_editor_property('grass_varieties'):
                    mesh=v.get_editor_property('grass_mesh')
                    report['grass_varieties'].append(dict(type=grass.get_path_name(),
                        density_scaling=grass.get_editor_property('enable_density_scaling'),
                        density=v.get_editor_property('grass_density').get_editor_property('default'),
                        cull_start=v.get_editor_property('start_cull_distance').get_editor_property('default'),
                        cull_end=v.get_editor_property('end_cull_distance').get_editor_property('default'),
                        min_lod=v.get_editor_property('min_lod'),
                        mesh=mesh.get_path_name() if mesh else None,
                        nanite=mesh.get_editor_property('nanite_settings').enabled if mesh else None))
        if not any(s in name for s in ('Terrain','Hills','Tussock','DomainRiver','DomainLake','M_GT_Vehicle')):continue
        if m.get_name() in ('M_Gaea_Terrain','M_GC_Terrain','M_GC_Hills'):
            mel=u.MaterialEditingLibrary
            roots={key:mel.get_material_property_input_node(m,getattr(u.MaterialProperty,key))
                   for key in ('MP_BASE_COLOR','MP_NORMAL','MP_ROUGHNESS','MP_EMISSIVE_COLOR','MP_WORLD_POSITION_OFFSET','MP_MATERIAL_ATTRIBUTES')}
            reachable=set()
            pending=[node for node in roots.values() if node]
            while pending:
                node=pending.pop()
                if node.get_name() in reachable:continue
                reachable.add(node.get_name())
                pending.extend(n for n in mel.get_inputs_for_material_expression(m,node) if n)
            nodes=[]
            for node in mel.get_material_expressions(m):
                data=dict(name=node.get_name(),kind=node.get_class().get_name(),reachable=node.get_name() in reachable,
                          inputs=[n.get_name() if n else None for n in mel.get_inputs_for_material_expression(m,node)])
                if isinstance(node,u.MaterialExpressionCustom):data['code']=node.get_editor_property('code')
                if isinstance(node,u.MaterialExpressionCollectionParameter):
                    data.update(collection=str(node.get_editor_property('collection')),
                                parameter=str(node.get_editor_property('parameter_name')))
                nodes.append(data)
            report['material_graphs'][name]=dict(roots={k:n.get_name() if n else None for k,n in roots.items()},nodes=nodes)
        stats=u.MaterialEditingLibrary.get_statistics(m)
        report['material_statistics'][name]={k:stats.get_editor_property(k) for k in (
            'num_vertex_shader_instructions','num_pixel_shader_instructions','num_samplers',
            'num_vertex_texture_samples','num_pixel_texture_samples','num_interpolator_scalars')}
    report['audit_note']='Shader statistics are compiler estimates, not GPU timings. LOD asset/binding audit is not rendered-LOD telemetry.'
    report['ok']=True
except Exception:
    report['error']=traceback.format_exc()
    u.log_error(report['error'])
finally:
    (OUT/'install-report.json').write_text(json.dumps(report,indent=2))
    u.SystemLibrary.quit_editor()
