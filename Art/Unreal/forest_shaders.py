"""Distance-canopy shader authoring and evidence for the LiDAR map."""
import unreal as u,json,sys,hashlib,shutil,time,subprocess
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_life_materials import Graph,props
import lidar_first_section as section
BASE='/Game/GrandTour/ArtTests/LidarStudy';DEST=BASE+'/ForestShaders'
OUT=ROOT/'Art/Export/LidarStudy/Place/ForestShaders';QA=ROOT/'Saved/LidarAuthoringQA/ForestShaders'
OUT.mkdir(parents=True,exist_ok=True);QA.mkdir(parents=True,exist_ok=True)
mel=u.MaterialEditingLibrary;assets=u.EditorAssetLibrary;actors=u.get_editor_subsystem(u.EditorActorSubsystem);sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def enabled():
    recipe=OUT/'recipe.json'
    return recipe.exists() and json.loads(recipe.read_text()).get('enabled',False)

def ensure_atlases():
    """A rebake of the source canopy must invalidate the derived shader maps."""
    manifest=OUT/'atlas-build.json'
    rows=json.loads(manifest.read_text()).get('trees',[]) if manifest.exists() else []
    current=len(rows)==4
    for row in rows:
        k=row['kind']
        current=current and row['source_sha256']==sha(OUT.parent/f'FirAtlas_{k}.tga') and row['normal_sha256']==sha(OUT.parent/f'FirNormal_{k}.tga')
        current=current and all((OUT/f'T_FS_{stem}_{k}.png').exists() for stem in ['Colour','NormalAO'])
    if not current:
        subprocess.run([str(ROOT/'Saved/Tools/TerrainPython/Scripts/python.exe'),str(ROOT/'Art/tools/build_forest_shader_atlases.py')],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
    return not current

def atlas_signature(kind):
    return {stem:sha(OUT/f'T_FS_{stem}_{kind}.png') for stem in ['Colour','NormalAO']}

def imported_atlas_current(kind):
    path=OUT/'imported-atlases.json'
    return path.exists() and json.loads(path.read_text()).get(str(kind))==atlas_signature(kind)

def connected_nodes(material):
    # UE can retain deleted expressions in a saved package. Inspect only the
    # graph reached from active outputs, never those orphaned subobjects.
    outputs=['MP_BASE_COLOR','MP_NORMAL','MP_OPACITY_MASK','MP_AMBIENT_OCCLUSION','MP_SUBSURFACE_COLOR','MP_ROUGHNESS','MP_SPECULAR']
    todo=[mel.get_material_property_input_node(material,getattr(u.MaterialProperty,p)) for p in outputs]
    seen=set();nodes=[]
    while todo:
        node=todo.pop()
        if not node or node.get_name() in seen:continue
        seen.add(node.get_name());nodes.append(node)
        todo.extend(n for n in mel.get_inputs_for_material_expression(material,node) if n)
    return nodes
def protect():
    manifest=QA/'backup.json'
    if manifest.exists():return json.loads(manifest.read_text())
    folder=ROOT/'Saved/LidarAuthoringBackups'/('ForestShaders-'+str(time.time_ns()));content=ROOT/'Content/GrandTour/ArtTests/LidarStudy'
    paths=[content/'L_LidarStudy.umap',content/'M_LP6_Foliage.uasset',content/'MI_NZ_Foliage_Canopy.uasset',content/'M_Terrain.uasset',content/'M_Detail.uasset',ROOT/'Config/DefaultEngine.ini',ROOT/'Art/lidar_performance.json']
    for sub in ['CanopyKit','FirstSection','ForestGround']:paths+=list((content/sub).rglob('*.uasset'))
    files={}
    for src in paths:
        if not src.exists():continue
        rel=src.relative_to(ROOT);dst=folder/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);files[str(rel)]=sha(src)
    result=dict(folder=str(folder),files=files);manifest.write_text(json.dumps(result,indent=2));return result
def audit():
    protect();report=dict(local=section.snapshot(),outside=section.outside_snapshot(),components=[],materials={},textures={})
    paths=set()
    for a in actors.get_all_level_actors():
        if not any(s in a.get_actor_label() for s in ['Forest','PD_Stand','RS7_Tree']):continue
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            m=c.static_mesh
            if not m:continue
            mats=[c.get_material(i) for i in range(c.get_num_materials())]
            report['components'].append(dict(actor=a.get_actor_label(),component=c.get_name(),mesh=m.get_path_name(),count=c.get_instance_count(),screens=list(sm.get_lod_screen_sizes(m)),materials=[x.get_path_name() if x else None for x in mats],nanite=str(m.get_editor_property('nanite_settings')),lod_scale=c.get_editor_property('instance_lod_distance_scale')))
            paths.update(x.get_path_name().split('.')[0] for x in mats if x)
    paths.update(BASE+'/CanopyKit/M_FirFar_'+str(k) for k in range(4));paths.add(BASE+'/M_LP6_Foliage')
    for path in list(paths):
        m=u.load_asset(path)
        if isinstance(m,u.MaterialInstance):paths.add(m.get_editor_property('parent').get_path_name().split('.')[0])
    for path in sorted(paths):
        m=u.load_asset(path)
        if not isinstance(m,u.Material):continue
        nodes=[]
        for n in mel.get_material_expressions(m):
            row=dict(type=n.get_class().get_name(),desc=str(n.get_editor_property('desc')))
            if isinstance(n,u.MaterialExpressionCustom):row.update(code=n.get_editor_property('code'),inputs=[str(i.get_editor_property('input_name')) for i in n.get_editor_property('inputs')])
            if isinstance(n,(u.MaterialExpressionTextureSample,u.MaterialExpressionTextureObject)):
                t=n.get_editor_property('texture')
                if t:
                    row['texture']=t.get_path_name();report['textures'][t.get_path_name()]={k:str(t.get_editor_property(k)) for k in ['srgb','compression_settings','mip_gen_settings','never_stream','do_scale_mips_for_alpha_coverage','alpha_coverage_thresholds']}
            nodes.append(row)
        report['materials'][path]=dict(nodes=nodes,properties={k:str(m.get_editor_property(k)) for k in ['shading_model','blend_mode','two_sided','tangent_space_normal','opacity_mask_clip_value']},outputs={str(p):str(mel.get_material_property_input_node(m,p)) for p in [u.MaterialProperty.MP_BASE_COLOR,u.MaterialProperty.MP_NORMAL,u.MaterialProperty.MP_AMBIENT_OCCLUSION,u.MaterialProperty.MP_SUBSURFACE_COLOR]})
    (QA/'audit.json').write_text(json.dumps(report,indent=2))
    views=json.loads((ROOT/'Saved/LidarAuthoringQA/PerceivedDetail/cameras-proof.json').read_text())
    views=[v for v in views if v['view'] in ['T01','F01','F02','B04','G01']]
    views+= [v for v in json.loads((ROOT/'Saved/LidarAuthoringQA/ForestGround/cameras.json').read_text()) if v['view']=='W02']
    (QA/'cameras.json').write_text(json.dumps(views,indent=2))
    print('FOREST_SHADER_AUDIT',len(report['components']),len(report['materials']))

def far_material(kind):
    ensure_atlases()
    textures={}
    for stem,colour in [('Colour',True),('NormalAO',False)]:
        name=f'T_FS_{stem}_{kind}'
        task=props(u.AssetImportTask(),filename=str(OUT/(name+'.png')),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);t=u.load_asset(DEST+'/'+name)
        props(t,srgb=colour,compression_settings=u.TextureCompressionSettings.TC_BC7,mip_gen_settings=u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE,never_stream=False,max_texture_size=2048,lod_bias=0,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP,
              do_scale_mips_for_alpha_coverage=colour,alpha_coverage_thresholds=u.Vector4(0,0,0,.35 if colour else 0))
        assert assets.save_loaded_asset(t,False);textures[stem]=t
    m=u.load_asset(BASE+'/CanopyKit/M_FirFar_'+str(kind));assert m
    for n in mel.get_material_expressions(m):
        if isinstance(n,u.MaterialExpressionCustom):n.set_editor_property('code','return 0;');n.set_editor_property('inputs',[])
    mel.delete_all_material_expressions(m);g=Graph(m,'ForestShaders')
    uv=g.custom(['UV'],'return UV*float2(.75,1);',u.CustomMaterialOutputType.CMOT_FLOAT2);g.wire(g.node(u.MaterialExpressionTextureCoordinate),uv,'UV')
    c=g.node(u.MaterialExpressionTextureSample,texture=textures['Colour'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR);g.wire(uv,c,'UVs')
    n=g.node(u.MaterialExpressionTextureSample,texture=textures['NormalAO'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR);g.wire(uv,n,'UVs')
    tint=g.vector((.42,.40,.38) if kind==3 else (.74,.94,.84));tint.set_editor_property('desc','ForestShaderTint')
    shade=g.custom(['C','AO','Tint','P','Rand','IsLeaf'],r'''
float patch=.5+.5*sin(P.x*.00043+P.y*.00031);
float3 palette=lerp(float3(.84,1.04,1.17),float3(1.08,1.04,.85),smoothstep(.35,.8,patch));
float leaf=IsLeaf*smoothstep(1.06,1.30,C.g/max(C.r,.001));
float cavity=lerp(1,lerp(.88,1.08,saturate((AO-.64)/.36)),leaf);
float3 colour=C*Tint*lerp(float3(1,1,1),palette*lerp(.94,1.08,Rand),IsLeaf)*cavity;
Transmission=colour*(.10+.06*AO)*leaf;
Occlusion=lerp(1,AO,leaf*.75);
return colour;
''',outputs=[('Transmission',u.CustomMaterialOutputType.CMOT_FLOAT3),('Occlusion',u.CustomMaterialOutputType.CMOT_FLOAT1)])
    for node,pin,out in [(c,'C','RGB'),(n,'AO','A'),(tint,'Tint',''),(g.node(u.MaterialExpressionWorldPosition),'P',''),(g.node(u.MaterialExpressionPerInstanceRandom),'Rand',''),(g.scalar(float(kind<3)),'IsLeaf','')]:g.wire(node,shade,pin,out)
    g.output(shade,u.MaterialProperty.MP_BASE_COLOR);g.output(shade,u.MaterialProperty.MP_AMBIENT_OCCLUSION,'Occlusion');g.output(shade,u.MaterialProperty.MP_SUBSURFACE_COLOR,'Transmission')
    decode=g.custom(['Packed'],'return normalize(lerp(Packed*2-1,float3(0,0,1),.12));');g.wire(n,decode,'Packed','RGB')
    # Pixel LOCAL space belongs to the forest component. INSTANCE space rotates
    # the baked normal with each tree, including independently rotated cards.
    world=g.node(u.MaterialExpressionTransform,transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_INSTANCE,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD);g.wire(decode,world,'');g.output(world,u.MaterialProperty.MP_NORMAL)
    g.output(c,u.MaterialProperty.MP_OPACITY_MASK,'A');g.output(g.scalar(.88),u.MaterialProperty.MP_ROUGHNESS);g.output(g.scalar(.05),u.MaterialProperty.MP_SPECULAR)
    props(m,blend_mode=u.BlendMode.BLEND_MASKED,shading_model=u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE if kind<3 else u.MaterialShadingModel.MSM_DEFAULT_LIT,two_sided=True,tangent_space_normal=False,opacity_mask_clip_value=.35,dithered_lod_transition=True)
    mel.set_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
    assert not mel.recompile_material(m);assert assets.save_loaded_asset(m,False)
    manifest=OUT/'imported-atlases.json'
    imported=json.loads(manifest.read_text()) if manifest.exists() else {}
    imported[str(kind)]=atlas_signature(kind);manifest.write_text(json.dumps(imported,indent=2))
    s=mel.get_statistics(m)
    return dict(material=m.get_path_name(),statistics={k:s.get_editor_property(k) for k in ['num_pixel_shader_instructions','num_vertex_shader_instructions','num_samplers','num_pixel_texture_samples']},normal_space='instance to world',texture_size=[2048,512],mips=True)

def install(asset_only=False):
    backup=protect();saved=json.loads((QA/'audit.json').read_text())
    protected_before={rel:sha(ROOT/rel) for rel in backup['files']}
    before=saved['local'] if asset_only else section.snapshot();outside=saved['outside'] if asset_only else section.outside_snapshot();assets.make_directory(DEST)
    materials=[far_material(k) for k in range(4)]
    if not asset_only:assert section.snapshot()==before and section.outside_snapshot()==outside
    allowed={str(Path('Content/GrandTour/ArtTests/LidarStudy/CanopyKit')/f'M_FirFar_{k}.uasset') for k in range(4)}
    protected=[]
    for rel,digest in protected_before.items():
        if rel in allowed:continue
        assert sha(ROOT/rel)==digest,rel;protected.append(rel)
    result=dict(ok=True,materials=materials,protected_packages=len(protected),map_geometry_unchanged=True,local=before,outside=outside,backup=backup['folder'],atlas=json.loads((OUT/'atlas-build.json').read_text()))
    (QA/'installed.json').write_text(json.dumps(result,indent=2));print('FOREST_SHADERS_INSTALLED',json.dumps(result))

def verify():
    """Inspect saved shader settings and exercise the idempotent Polish hook."""
    import lidar_canopy_assets as canopy
    assert enabled()
    ensure_atlases()
    rows=[]
    for k in range(4):
        assert imported_atlas_current(k)
        m=u.load_asset(BASE+'/CanopyKit/M_FirFar_'+str(k));assert m
        nodes=connected_nodes(m)
        assert sum(str(n.get_editor_property('desc'))=='ForestShaderTint' for n in nodes)==1,[(n.get_class().get_name(),str(n.get_editor_property('desc'))) for n in nodes]
        assert not any(str(n.get_editor_property('desc'))=='RS1LeafColour' for n in nodes)
        transform=mel.get_material_property_input_node(m,u.MaterialProperty.MP_NORMAL)
        assert isinstance(transform,u.MaterialExpressionTransform)
        assert transform.get_editor_property('transform_source_type')==u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_INSTANCE
        assert m.get_editor_property('shading_model')==(u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE if k<3 else u.MaterialShadingModel.MSM_DEFAULT_LIT)
        samples=[n for n in nodes if isinstance(n,u.MaterialExpressionTextureSample)]
        assert len(samples)==2
        for sample in samples:
            t=sample.get_editor_property('texture')
            assert t.get_editor_property('mip_gen_settings')==u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE
            assert t.get_editor_property('compression_settings')==u.TextureCompressionSettings.TC_BC7
            assert not t.get_editor_property('never_stream')
        package=ROOT/'Content/GrandTour/ArtTests/LidarStudy/CanopyKit'/f'M_FirFar_{k}.uasset'
        digest=sha(package)
        canopy.tint_far_card(k,(.42,.40,.38) if k==3 else (.74,.94,.84))
        assert canopy.shade_far_card(k)
        assert len(connected_nodes(m))==len(nodes)
        assert sha(package)==digest,'Repeated Polish changed the shader'
        rows.append(dict(kind=k,nodes=len(nodes),sha256=digest))
    result=dict(ok=True,materials=rows,source_atlases_current=True,polish_idempotent=True)
    (QA/'verified.json').write_text(json.dumps(result,indent=2))
    return result
