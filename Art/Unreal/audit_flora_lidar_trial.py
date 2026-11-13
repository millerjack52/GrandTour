"""Read-only NullRHI audit of saved mud, water, detail and rock trial assets.

No PIE, GPU rendering or asset saves. This does not certify driving or visuals.
"""
import unreal as u
import json, math, hashlib, traceback, sys
from pathlib import Path

R=Path('C:/GrandTour'); O=R/'Art/Export/FloraDrive'
sys.path[:0]=[str(R/'Art/tools'),str(R/'Art/Unreal')]
from make_mud_road import centre
from flora_drive_ground import floor_z
M=u.MaterialEditingLibrary
report=dict(ok=False,mode='NullRHI / saved assets only',warnings=[],materials=[],textures={},rocks=[],meshes={})

def asset_file(asset):
    return R/'Content'/Path(asset.get_path_name().split('.')[0].removeprefix('/Game/')).with_suffix('.uasset')

def texture_row(t):
    key=t.get_path_name()
    if key not in report['textures']:
        size,fmt=u.GTMudArtLibrary.texture_all_mips_bytes(t)
        # NullRHI may not build platform texture data; zero is unknown, not free.
        report['textures'][key]=dict(all_mips_bytes=size if size>0 else None,format=fmt,srgb=t.get_editor_property('srgb'),never_stream=t.get_editor_property('never_stream'),compression=str(t.get_editor_property('compression_settings')))
        if key.startswith('/Game/'):tracked.append(asset_file(t))
    return key

def material_row(m):
    roots={p:M.get_material_property_input_node(m,getattr(u.MaterialProperty,p)) for p in ['MP_BASE_COLOR','MP_NORMAL','MP_ROUGHNESS','MP_SPECULAR','MP_AMBIENT_OCCLUSION','MP_SUBSURFACE_COLOR','MP_EMISSIVE_COLOR','MP_WORLD_POSITION_OFFSET','MP_OPACITY_MASK','MP_OPACITY','MP_MATERIAL_ATTRIBUTES'] if hasattr(u.MaterialProperty,p)}
    todo=[n for n in roots.values() if n]; reachable=set()
    while todo:
        n=todo.pop()
        if n.get_name() in reachable:continue
        reachable.add(n.get_name());todo.extend(x for x in M.get_inputs_for_material_expression(m,n) if x)
    row=dict(path=m.get_path_name(),roots={p:n.get_name() if n else None for p,n in roots.items()},tangent_space=m.get_editor_property('tangent_space_normal'),nodes=[],scalar_parameters={},vector_parameters={})
    for n in M.get_material_expressions(m):
        item=dict(name=n.get_name(),desc=str(n.get_editor_property('desc')),reachable=n.get_name() in reachable,type=n.get_class().get_name())
        if isinstance(n,(u.MaterialExpressionTextureObject,u.MaterialExpressionTextureSample)):
            t=n.get_editor_property('texture')
            item['texture']=texture_row(t) if t else None
        if isinstance(n,u.MaterialExpressionScalarParameter):row['scalar_parameters'][str(n.get_editor_property('parameter_name'))]=n.get_editor_property('default_value')
        if isinstance(n,u.MaterialExpressionVectorParameter):
            v=n.get_editor_property('default_value');row['vector_parameters'][str(n.get_editor_property('parameter_name'))]=[v.r,v.g,v.b,v.a]
        if isinstance(n,u.MaterialExpressionCustom):item['code']=str(n.get_editor_property('code'))
        row['nodes'].append(item)
    report['materials'].append(row);return row

try:
    protected=json.loads((O/'protected-before.json').read_text())
    tracked=[R/'Content/GrandTour/ArtTests/FloraDrive/L_FloraDrive.umap']
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GrandTour/ArtTests/FloraDrive/L_FloraDrive')
    actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    s=next(a for a in actors if isinstance(a,u.GTLandscapeSurface))
    v=next(a for a in actors if isinstance(a,u.GTMudRunnerVisual))
    reference=json.loads((O/'LidarMud/reference.json').read_text())
    report['settings']={k:s.get_editor_property(k) for k in reference['settings']}
    assert report['settings']==reference['settings'],'Saved mud response differs from LiDAR'
    assert s.tyre_coating_material is None
    assert len(s.mud_regions)==0,'Unexpected local mud-region overrides'
    report['soil_samples']=[]
    for x in range(-2400,2401,200):
        for across in [0,85,160,250,400]:
            p=s.sample_surface(u.Vector2D(x,centre(x)+across))
            report['soil_samples'].append(dict(x=x,across=across,**{k:p.get_editor_property(k) for k in ['sinkage_cap_cm','softness','wetness','grass_cover','clay_weight','cohesion','native_friction','native_linear_resistance','native_push_resistance']}))
    materials=[v.material,v.track_material,v.water_simulation_material,v.sediment_simulation_material,u.load_asset(s.simulated_water.get_editor_property('surface_material_path'))]
    for m in materials:tracked.append(asset_file(m));material_row(m)
    for name in ['M_ForestFloorForms','M_FloraLandscape']:
        m=u.load_asset('/Game/GrandTour/ArtTests/FloraDrive/'+name)
        if m:tracked.append(asset_file(m));material_row(m)
    ground=report['materials'][0]
    if not v.follow_player_grid:
        position=v.get_actor_location()
        for material in report['materials'][:2]:
            window=material['vector_parameters']['MR_VisualWindow']
            assert max(abs(position.x-window[0]),abs(position.y-window[1]))+v.half_size_cm<=window[2]-window[3]+.01,'Fixed grid lies outside its visible deformation window'
        report['fixed_visual_window_covers_grid']=True
    assert ground['path'].endswith('M_LidarDemoMud.M_LidarDemoMud')
    assert not ground['tangent_space'],'Mud detail expects world-space normals'
    normal=M.get_material_property_input_node(v.material,u.MaterialProperty.MP_NORMAL)
    assert str(normal.get_editor_property('desc'))=='ForestFloorDetail'
    assert M.get_material_property_input_node(v.material,u.MaterialProperty.MP_WORLD_POSITION_OFFSET),'Native deformation disconnected'
    local='/Game/GrandTour/ArtTests/FloraDrive/T_LidarDemo_'
    for row in report['materials'][:5]:
        textures={n.get('texture') for n in row['nodes'] if n['reachable'] and n.get('texture')}
        assert local+'paint.T_LidarDemo_paint' in textures,'Local paint missing: '+row['path']
        stale=[t for t in textures if '/LidarStudy/' in t and t.split('.')[-1] in ['T_paint','T_style','T_clay','T_rest','T_relief','T_Composition','T_RouteUV']]
        assert not stale,('Unremapped source lookup',row['path'],stale)
    for row in report['materials'][2:5]:
        assert abs(row['scalar_parameters']['GTLS_DepthScale']-reference['settings']['layer_depth_scale'])<1e-6
    sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    for a in actors:
        if not a.get_actor_label().startswith('FloraDrive_RockMaster_'):continue
        c=a.static_mesh_component;mesh=c.static_mesh;key=mesh.get_path_name()
        if key not in report['meshes']:
            tracked.append(asset_file(mesh));n=sm.get_lod_count(mesh)
            report['meshes'][key]=dict(triangles=[mesh.get_num_triangles(i) for i in range(n)],screen_sizes=list(sm.get_lod_screen_sizes(mesh)),collision_hulls=sm.get_convex_collision_count(mesh),material_slots=c.get_num_materials())
            assert n==3 and report['meshes'][key]['collision_hulls']>0
            for m in c.get_materials():tracked.append(asset_file(m));material_row(m)
        origin,extent=a.get_actor_bounds(False)
        # Conservative AABB clearance to the driven centreline, sampled every 25 cm.
        clearance=min(math.hypot(max(abs(x-origin.x)-extent.x,0),max(abs(centre(x)-origin.y)-extent.y,0)) for x in range(-2450,2451,25))
        p=a.get_actor_location();base=origin.z-extent.z;top=origin.z+extent.z;ground_z=floor_z(p.x,p.y)
        row=dict(actor=a.get_actor_label(),mesh=key,position=p.to_tuple(),bounds_origin=origin.to_tuple(),bounds_extent=extent.to_tuple(),road_centre_clearance_cm=clearance,base_z=base,top_z=top,authored_ground_z=ground_z,collision=str(c.get_collision_enabled()),collision_profile=str(c.get_collision_profile_name()))
        report['rocks'].append(row)
        assert base<ground_z<top,'Rock not embedded: '+row['actor']
        assert clearance>300,'Rock bounding box intrudes into 6 m driving corridor: '+row['actor']
    assert len(report['rocks'])==20
    if (O/'ground-shadow-settings.json').exists():
        settings=json.loads((O/'ground-shadow-settings.json').read_text())
        report['ground_shadows']=dict(broadleaf_instances=0,contact_instances=0,settings=settings)
        for a in actors:
            for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
                if not c.static_mesh:continue
                name=c.static_mesh.get_name()
                if name.startswith('SM_Path_FP_') and any(k in name for k in ['Small_Plants','Grass','Flower','Ferns','Shrubbery']):
                    assert c.get_editor_property('cast_contact_shadow'),name
                    report['ground_shadows']['contact_instances']+=c.get_instance_count()
                    if 'Small_Plants' in name and settings['broadleaf_dynamic_shadows']:
                        assert c.get_editor_property('cast_shadow') and c.get_editor_property('cast_dynamic_shadow'),name
                        report['ground_shadows']['broadleaf_instances']+=c.get_instance_count()
        light=next(a.light_component for a in actors if a.get_actor_label()=='FloraDrive_Sun')
        assert light.get_editor_property('ContactShadowLengthInWS')
        assert abs(light.get_editor_property('ContactShadowLength')-settings['contact_length_cm'])<.001
    rock_textures=[t for k,t in report['textures'].items() if '/RockMaster/' in k]
    report['rock_texture_bytes']=sum(t['all_mips_bytes'] for t in rock_textures) if all(t['all_mips_bytes'] is not None for t in rock_textures) else None
    report['referenced_texture_bytes']=sum(t['all_mips_bytes'] for t in report['textures'].values()) if all(t['all_mips_bytes'] is not None for t in report['textures'].values()) else None
    report['texture_memory_note']='NullRHI cannot establish resident GPU memory. Missing platform data is reported as null, never as zero cost.'
    report['rock_texture_estimate_bytes']=len(rock_textures)*sum(max(1,(1024//2**i+3)//4)**2*16 for i in range(11))
    report['rock_texture_estimate_assumption']='15 1024-square textures, full mip chains, 16 bytes per 4x4 block (BC3/BC5); conservative format estimate, not measured residency.'
    report['minimum_road_clearance_cm']=min(r['road_centre_clearance_cm'] for r in report['rocks'])
    report['rock_lod0_triangle_upper_bound']=sum(report['meshes'][r['mesh']]['triangles'][0] for r in report['rocks'])
    report['source_maps_unchanged']=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in protected.items())
    assert report['source_maps_unchanged']
    assert (O/'world-rest.png').read_bytes()==(O/'BeforeLidarMudRocks/world-rest.png').read_bytes()
    report['package_hashes']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in set(tracked)}
    report['ok']=True
except Exception:
    report['error']=traceback.format_exc();u.log_error(report['error'])
(O/'audit-report.json').write_text(json.dumps(report,indent=2))
u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Engine/Maps/Entry')
u.SystemLibrary.quit_editor()
