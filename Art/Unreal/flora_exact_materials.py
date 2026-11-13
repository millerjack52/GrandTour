"""Clean source-output materials. No FloraWorld colour/normal wrappers."""
import unreal as u
import hashlib
from pathlib import Path
from benmore_river_life_materials import Graph,props
E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary;T=u.AssetToolsHelpers.get_asset_tools();S=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
D='/Game/GrandTour/ArtTests/FloraParity/AssetMatch';O=Path('C:/GrandTour/Art/Export/LidarStudy/FloraParity/AssetMatch')
REV=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:7]

def lighting_controls():
    name='MPC_SourceLighting';mpc=u.load_asset(D+'/'+name)
    if not mpc:
        mpc=T.create_asset(name,D,u.MaterialParameterCollection,u.MaterialParameterCollectionFactoryNew())
        props(mpc,vector_parameters=[props(u.CollectionVectorParameter(),parameter_name='SunDirection',default_value=u.LinearColor(0,0,1,0)),props(u.CollectionVectorParameter(),parameter_name='SkyRadiance',default_value=u.LinearColor(.743,.743,.743,0))])
        E.save_loaded_asset(mpc,False)
    return mpc

def texture(path,coverage):
    name=Path(path).stem;t=u.load_asset(D+'/'+name)
    digest=hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if not t or E.get_metadata_tag(t,'FloraSourceSHA256')!=digest:
        task=props(u.AssetImportTask(),filename=path,destination_path=D,destination_name=name,automated=True,replace_existing=True,save=True);T.import_asset_tasks([task]);t=u.load_asset(D+'/'+name)
    assert t
    props(t,srgb=not coverage,compression_settings=u.TextureCompressionSettings.TC_GRAYSCALE if coverage else u.TextureCompressionSettings.TC_BC7,max_texture_size=2048)
    E.set_metadata_tag(t,'FloraSourceSHA256',digest);E.save_loaded_asset(t,False);return t

def make_material(asset,slot,colour,mask):
    name='M_Exact_'+asset['key']+'_'+slot['name'].replace('.','_')+'_'+REV
    m=u.load_asset(D+'/'+name)
    if m:return m
    m=T.create_asset(name,D,u.Material,u.MaterialFactoryNew())
    M.delete_all_material_expressions(m);g=Graph(m,'FloraSourceOutputs')
    props(m,two_sided=True,tangent_space_normal=False,shading_model=u.MaterialShadingModel.MSM_DEFAULT_LIT,blend_mode=u.BlendMode.BLEND_MASKED if slot['foliage'] else u.BlendMode.BLEND_OPAQUE,dither_opacity_mask=False,opacity_mask_clip_value=.5,has_pixel_animation=slot['foliage'])
    M.set_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
    uv=g.node(u.MaterialExpressionTextureCoordinate,coordinate_index=1)
    c=g.node(u.MaterialExpressionTextureSampleParameter2D,parameter_name='SourcePigment',texture=colour,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR);g.wire(uv,c,'UVs');g.output(c,u.MaterialProperty.MP_BASE_COLOR,'RGB')
    g.output(g.scalar(0),u.MaterialProperty.MP_SPECULAR);g.output(g.scalar(0),u.MaterialProperty.MP_ROUGHNESS)
    normal=g.node(u.MaterialExpressionVertexNormalWS);view=g.node(u.MaterialExpressionCameraVectorWS);side=g.node(u.MaterialExpressionTwoSidedSign)
    if slot['foliage']:
        mask=texture(slot['shared_mask'],True)
        mask_uv=g.node(u.MaterialExpressionTextureCoordinate,coordinate_index=0)
        a=g.node(u.MaterialExpressionTextureSampleParameter2D,parameter_name='SourceCoverage',texture=mask,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE);g.wire(mask_uv,a,'UVs')
        coverage=g.custom(['A','N','V','Soft'],'''float b=clamp(Soft,0.,.99999);float exponent=b<.5?2*b:.5/(1-b);float c=pow(saturate(abs(dot(normalize(N),normalize(V)))),exponent);return saturate(A*(.1+.9*c));''',u.CustomMaterialOutputType.CMOT_FLOAT1)
        soft=g.node(u.MaterialExpressionScalarParameter,parameter_name='SourceFacingSoftness',default_value=slot['soft'])
        for n,pin,out in [(a,'A','R'),(normal,'N',''),(view,'V',''),(soft,'Soft','')]:g.wire(n,coverage,pin,out)
        # Native screen-space dither correlates every overlapping card at a pixel.
        # Source Eevee uses hashed transparency: independent surfaces accumulate.
        # The purchased frozen FBX already carries deterministic per-card seeds
        # in vertex alpha, assigned during its original export.
        seed=g.node(u.MaterialExpressionVertexColor)
        hashed=g.custom(['Coverage','Seed'],'''uint2 p=uint2(Parameters.SvPosition.xy);
uint h=p.x*1973u+p.y*9277u+uint(Seed*65535.)*26699u;
h^=h>>16;h*=0x7feb352du;h^=h>>15;h*=0x846ca68bu;h^=h>>16;
uint t=View.StateFrameIndex & 7u;
#if SHADOW_DEPTH_SHADER
// Stable shadow coverage permits virtual-shadow-map page caching.
t=0u;
#endif
uint rank=((t&1u)<<2)|(t&2u)|((t&4u)>>2);
float r=frac(float(h & 0x00ffffffu)/16777216.+float(rank)*.125);
return step(r,saturate(Coverage));''',u.CustomMaterialOutputType.CMOT_FLOAT1)
        g.wire(coverage,hashed,'Coverage');g.wire(seed,hashed,'Seed','A');g.output(hashed,u.MaterialProperty.MP_OPACITY_MASK)
        # Source Eevee's UNCONNECTED thickness means object bounds, not zero.
        # Thick transmission applies the weighted colour twice and isotropic
        # direct response 1/pi. Reproduce the source's sun + uniform sky case
        # analytically, with native UE directional shadows. No per-plant fit.
        # The shared downward transmission normal also gates the source's
        # reflection stack for upper-hemisphere lights (Blender 5.1.2 behavior).
        # Additional local lights / nonuniform sky require a separate extension.
        mpc=lighting_controls()
        sun=g.node(u.MaterialExpressionCollectionParameter,collection=mpc,parameter_name='SunDirection')
        sky=g.node(u.MaterialExpressionCollectionParameter,collection=mpc,parameter_name='SkyRadiance')
        lighting=g.custom(['C','N','Side','Weight','Sun','Sky'],'''float3 L=normalize(Sun);
float w=saturate(Weight);
float3 reflection=C*w;
float3 transmission=C*(1-w);transmission*=transmission;
float reflectionGate=L.z<0?1.:0.;
float3 direct=transmission/3.14159265359+reflection*saturate(dot(normalize(N)*Side,L))*reflectionGate;
Ambient=max(0.,Sky*(reflection+transmission-direct));
LightNormal=L;
return direct;''',outputs=[('Ambient',u.CustomMaterialOutputType.CMOT_FLOAT3),('LightNormal',u.CustomMaterialOutputType.CMOT_FLOAT3)])
        weight=g.node(u.MaterialExpressionScalarParameter,parameter_name='SourceDiffuseWeight',default_value=slot['diffuse_weight'])
        for n,pin in [(normal,'N'),(side,'Side'),(weight,'Weight'),(sun,'Sun'),(sky,'Sky')]:g.wire(n,lighting,pin)
        g.wire(c,lighting,'C','RGB');g.output(lighting,u.MaterialProperty.MP_BASE_COLOR)
        g.output(lighting,u.MaterialProperty.MP_EMISSIVE_COLOR,'Ambient');g.output(lighting,u.MaterialProperty.MP_NORMAL,'LightNormal')
    else:
        n=g.custom(['N','Side'],'return normalize(N)*Side;');g.wire(normal,n,'N');g.wire(side,n,'Side');g.output(n,u.MaterialProperty.MP_NORMAL)
    assert not M.recompile_material(m);E.save_loaded_asset(m,False)
    return m

def import_asset(asset):
    E.make_directory(D)
    colour=texture(asset['textures']['Colour'],False);mask=texture(asset['textures']['Coverage'],True)
    name=asset['exact_mesh'];mesh=u.load_asset(D+'/'+name)
    if not mesh:
        task=props(u.AssetImportTask(),filename=str(O/'meshes'/(name+'.fbx')),destination_path=D,destination_name=name,automated=True,save=True)
        opt=props(u.FbxImportUI(),import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,import_animations=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
        props(opt.static_mesh_import_data,combine_meshes=True,auto_generate_collision=False,generate_lightmap_u_vs=False,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,vertex_color_import_option=u.VertexColorImportOption.REPLACE);task.options=opt;T.import_asset_tasks([task]);mesh=u.load_asset(D+'/'+name)
    assert mesh
    materials={s['name']:make_material(asset,s,colour,mask) for s in asset['exact_slots']}
    # Name-based slot binding avoids treating importer slot order as authoritative.
    for i,sm in enumerate(mesh.get_editor_property('static_materials')):
        slot=str(sm.get_editor_property('imported_material_slot_name'))
        match=next((s for s in materials if slot==s or slot.startswith(s+'.')),None)
        assert match,(slot,list(materials));mesh.set_material(i,materials[match])
    build=S.get_lod_build_settings(mesh,0);props(build,recompute_normals=False,recompute_tangents=True,use_full_precision_u_vs=True);S.set_lod_build_settings(mesh,0,build)
    settings=mesh.get_editor_property('nanite_settings');settings.enabled=False;S.set_nanite_settings(mesh,settings,True)
    assert S.get_num_uv_channels(mesh,0)==2;E.save_loaded_asset(mesh,False)
    return mesh

def pigment_material(source,white=False):
    path=D+('/Opacity/' if white else '/Pigment/')+source.get_name();m=u.load_asset(path) or E.duplicate_asset(source.get_path_name().split('.')[0],path)
    props(m,shading_model=u.MaterialShadingModel.MSM_UNLIT)
    colour=next(n for n in M.get_material_expressions(m) if isinstance(n,u.MaterialExpressionTextureSampleParameter2D) and str(n.get_editor_property('parameter_name'))=='SourcePigment')
    if white:Graph(m).output(Graph(m).scalar(1),u.MaterialProperty.MP_EMISSIVE_COLOR)
    else:assert M.connect_material_property(colour,'RGB',u.MaterialProperty.MP_EMISSIVE_COLOR)
    assert not M.recompile_material(m);E.save_loaded_asset(m,False);return m
