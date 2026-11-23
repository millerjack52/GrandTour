"""Build a local stone material from the installed Rock Master texture set."""
import unreal as u
from benmore_river_life_materials import Graph


def painted_rock(folder):
    """Use the landmark's own UV islands, colour, roughness and baked tangent normals."""
    name='M_BendMossLedges'
    path=folder+'/'+name
    assets=u.EditorAssetLibrary
    if assets.does_asset_exist(path):
        mat=u.load_asset(path)
        if assets.get_metadata_tag(mat,'BendRockSurface')=='3':return mat
        u.MaterialEditingLibrary.delete_all_material_expressions(mat)
    else:mat=u.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,u.Material,u.MaterialFactoryNew())
    g=Graph(mat,'BeddedStone')
    src='/Game/GrandTour/ArtTests/FloraDrive/RockMaster/T_SM_RM_Asset_Large_Rock_005_'
    def sample(suffix,sampler):
        tex=u.load_asset(src+suffix)
        assert tex,src+suffix
        return g.node(u.MaterialExpressionTextureSample,texture=tex,sampler_type=sampler)
    colour=sample('Colour',u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    norm=sample('Normal',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    rough=sample('Roughness',u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    from forest_floor import moss_texture
    shoots=g.node(u.MaterialExpressionTextureObject,texture=moss_texture(folder),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    surface=g.custom(['Source','P','Centre','R','Up','Shoots'],'''
float l=dot(Source,float3(.28,.56,.16));
float grain=smoothstep(.012,.25,l);
float3 stone=lerp(float3(.067,.060,.047),float3(.178,.157,.123),grain)+Source*.24;
float3 q=(P-Centre)*.01;
float3 f=Texture2DSample(Shoots,View.MaterialTextureBilinearWrapedSampler,P.xy/72.).rgb;
float growth=.64*saturate(Up.z)+.46*f.r+.13*f.b-.12*grain;
float cover=smoothstep(.72,.93,growth)*(.60+.40*smoothstep(-.66,.34,-q.z));
float3 olive=lerp(float3(.045,.065,.021),float3(.126,.150,.053),saturate(f.r*.58+f.g*.90));
Rough=lerp(clamp(R.r,.72,.94),.93,cover);
return lerp(stone,olive,cover);
''',outputs=[('Rough',u.CustomMaterialOutputType.CMOT_FLOAT1)])
    for pin,node in [('Source',colour),('P',g.node(u.MaterialExpressionWorldPosition)),
                     ('Centre',g.node(u.MaterialExpressionObjectPositionWS)),('R',rough),
                     ('Up',g.node(u.MaterialExpressionVertexNormalWS)),('Shoots',shoots)]:
        g.wire(node,surface,pin)
    g.output(surface,u.MaterialProperty.MP_BASE_COLOR)
    g.output(surface,u.MaterialProperty.MP_ROUGHNESS,'Rough')
    g.output(norm,u.MaterialProperty.MP_NORMAL)
    g.output(g.scalar(.16),u.MaterialProperty.MP_SPECULAR)
    assert not u.MaterialEditingLibrary.recompile_material(mat)
    assets.set_metadata_tag(mat,'BendRockSurface','3')
    assert assets.save_loaded_asset(mat,False)
    return mat
