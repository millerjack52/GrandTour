"""Candidate-local owned Lazy Forest fern; no shared asset mutations."""
import unreal as u, json, hashlib
from pathlib import Path
from benmore_river_life_materials import props, Graph
import flora_fern_surface as previous
D='/Game/GrandTour/ArtTests/FloraTrail/LazyFern'
MAP=D+'/L_FloraTrail_LazyFern'
BASE='/Game/GrandTour/ArtTests/FloraTrail/FernSurface/L_FloraTrail_Fern'
O=Path('D:/GrandTourAssets/ReviewEvidence/FloraTrail/LazyFern')
E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary

def component(world):
    owner=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor) if a.get_actor_label()=='FloraTrail_SourceFoliage')
    return next(c for c in owner.get_components_by_class(u.InstancedStaticMeshComponent) if c.static_mesh and c.static_mesh.get_name() in ('SM_Exact_fern','SM_LazyFern02'))

def signature(world):
    rows=previous.scene_signature(world)
    for row in rows:
        if row['mesh'].split('.')[-1] in ('SM_Exact_fern','SM_LazyFern02'):
            row['mesh']='FERN_REVIEW_MESH';row['materials']=['FERN_REVIEW_SLOT']
    text=json.dumps(rows).replace(MAP+'.L_FloraTrail_LazyFern','<ReviewWorld>').replace(MAP,'<ReviewMap>')
    return json.loads(text)

def build(world):
    report=json.loads((O/'bake-report.json').read_text());assert report['ok']
    at=u.AssetToolsHelpers.get_asset_tools();textures={}
    for role in ('Colour','Coverage','Normal','Transmission'):
        name='T_LazyFern_'+role;file=O/(name+'.png')
        assert hashlib.sha256(file.read_bytes()).hexdigest()==report['files'][file.name]
        t=u.load_asset(D+'/'+name)
        if not t or E.get_metadata_tag(t,'SourceSHA256')!=report['files'][file.name]:
            job=props(u.AssetImportTask(),filename=str(file),destination_path=D,destination_name=name,automated=True,save=True,replace_existing=True)
            at.import_asset_tasks([job]);t=u.load_asset(D+'/'+name)
        assert t
        props(t,srgb=role=='Colour',compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if role=='Normal' else u.TextureCompressionSettings.TC_BC7 if role=='Colour' else u.TextureCompressionSettings.TC_MASKS,max_texture_size=4096,lod_bias=0,flip_green_channel=False)
        E.set_metadata_tag(t,'SourceSHA256',report['files'][file.name]);assert E.save_loaded_asset(t,False);textures[role]=t
    material=u.load_asset(D+'/M_LazyFern')
    if not material:
        material=at.create_asset('M_LazyFern',D,u.Material,u.MaterialFactoryNew())
        props(material,blend_mode=u.BlendMode.BLEND_MASKED,shading_model=u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE,two_sided=True,tangent_space_normal=True,opacity_mask_clip_value=.35)
        g=Graph(material,'LazyFern')
        samples={role:g.node(u.MaterialExpressionTextureSample,texture=t,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR if role=='Colour' else u.MaterialSamplerType.SAMPLERTYPE_NORMAL if role=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS) for role,t in textures.items()}
        gain=g.node(u.MaterialExpressionScalarParameter,parameter_name='PigmentGain',default_value=.45)
        colour=g.custom(['C','Gain'],'return C*Gain;');g.wire(samples['Colour'],colour,'C','RGB');g.wire(gain,colour,'Gain')
        g.output(colour,u.MaterialProperty.MP_BASE_COLOR)
        sub=g.custom(['C','T'],'return C*.15*saturate(T);');g.wire(samples['Colour'],sub,'C','RGB');g.wire(samples['Transmission'],sub,'T','R')
        g.output(sub,u.MaterialProperty.MP_SUBSURFACE_COLOR)
        g.output(samples['Coverage'],u.MaterialProperty.MP_OPACITY_MASK,'R')
        g.output(samples['Normal'],u.MaterialProperty.MP_NORMAL,'RGB')
        g.output(g.scalar(.605263),u.MaterialProperty.MP_ROUGHNESS)
        g.output(g.scalar(.08),u.MaterialProperty.MP_SPECULAR)
        M.set_material_usage(material,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
        assert not M.recompile_material(material);assert E.save_loaded_asset(material,False)
    for prop in (u.MaterialProperty.MP_BASE_COLOR,u.MaterialProperty.MP_NORMAL,u.MaterialProperty.MP_SUBSURFACE_COLOR,u.MaterialProperty.MP_OPACITY_MASK):
        assert M.get_material_property_input_node(material,prop),prop
    mesh=u.load_asset(D+'/SM_LazyFern02')
    if not mesh:
        u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
        options=props(u.FbxImportUI(),import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,import_animations=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
        props(options.static_mesh_import_data,combine_meshes=True,auto_generate_collision=False,generate_lightmap_u_vs=False,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
        job=props(u.AssetImportTask(),filename=str(O/'SM_LazyFern02.fbx'),destination_path=D,destination_name='SM_LazyFern02',options=options,automated=True,save=True)
        at.import_asset_tasks([job]);mesh=u.load_asset(D+'/SM_LazyFern02')
    assert mesh
    sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    options=u.StaticMeshReductionOptions();options.auto_compute_lod_screen_size=False
    options.reduction_settings=[u.StaticMeshReductionSettings(percent_triangles=p,screen_size=s) for p,s in [(1.,1.),(.65,.10),(.35,.035)]]
    assert sm.set_lods(mesh,options)==3
    mesh.set_material(0,material);assert E.save_loaded_asset(mesh,False)
    return mesh,material
