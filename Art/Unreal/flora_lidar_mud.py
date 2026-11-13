"""Localize LiDAR's actual mud/tread programs, retaining demo rest relief and POM."""
import unreal as u,json,re
from pathlib import Path
from benmore_river_life_materials import props,Graph
import flora_drive_ground_materials as detail
O=Path('C:/GrandTour/Art/Export/FloraDrive/LidarMud');D='/Game/GrandTour/ArtTests/FloraDrive/LidarMud'
E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary

def local_visual_window(material,visual):
    # Fixed study grids never call BindGridWindow. The copied LiDAR/Benmore
    # coverage gate must cover this grid, not its distant source-map location.
    p=visual.get_actor_location();window=u.LinearColor(p.x,p.y,visual.half_size_cm+600.,600.)
    count=0
    for e in M.get_material_expressions(material):
        if isinstance(e,u.MaterialExpressionVectorParameter) and str(e.get_editor_property('parameter_name'))=='MR_VisualWindow':
            e.set_editor_property('default_value',window);count+=1
    assert count==1,material.get_path_name()
    return [window.r,window.g,window.b,window.a]
def install(surface,visual,import_texture):
    ref=json.loads((O/'reference.json').read_text());assert ref['ok']
    for key,value in ref['settings'].items():surface.set_editor_property(key,value)
    surface.tyre_coating_material=None;surface.mud_regions=[]
    maps={}
    for key in ['paint','style','clay','composition','route','neutral-rest']:
        t=import_texture(O/(key+'.png'),'T_LidarDemo_'+key.replace('-','_'))
        props(t,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,never_stream=True,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP);E.save_loaded_asset(t);maps[key]=t
    assert u.GTLandscapeSurfaceSetupLibrary.import_paint(surface,maps['paint'])
    assert u.GTLandscapeSurfaceSetupLibrary.import_material_atlas(surface,maps['style'])
    assert u.GTLandscapeSurfaceSetupLibrary.import_clay_atlas(surface,maps['clay'])
    rest=u.load_asset('/Game/GrandTour/ArtTests/FloraDrive/T_FloraDriveRest');assert rest
    replacements={'T_paint':maps['paint'],'T_style':maps['style'],'T_clay':maps['clay'],'T_rest':rest,'T_relief':maps['neutral-rest'],'T_Composition':maps['composition'],'T_RouteUV':maps['route']}
    result={'settings':ref['settings'],'materials':[],'retained_road_rest':rest.get_path_name(),'source_segment_m':[170,260]}
    for role,name in [('ground','M_LidarDemoMud'),('tread','M_LidarDemoTread')]:
        path=D+'/'+name;m=u.load_asset(path) or E.duplicate_asset(ref['materials'][role]['path'].split('.')[0],path);assert m
        for e in M.get_material_expressions(m):
            if isinstance(e,(u.MaterialExpressionTextureObject,u.MaterialExpressionTextureSample)):
                t=e.get_editor_property('texture')
                if t and t.get_name() in replacements:e.set_editor_property('texture',replacements[t.get_name()])
            if isinstance(e,u.MaterialExpressionVectorParameter) and str(e.get_editor_property('parameter_name'))=='GTLS_PaintWindow':e.set_editor_property('default_value',u.LinearColor(-3150,-3150,6300,0))
            if isinstance(e,u.MaterialExpressionCustom):
                code=str(e.get_editor_property('code')).replace('185000','3150').replace('370000','6300')
                code=re.sub(r'float2 lt4xy=\(materialXY-float2\([^;]+;', 'float2 lt4xy=(materialXY+3150.)/6300.;',code)
                e.set_editor_property('code',code)
        nodes=list(M.get_material_expressions(m))
        if role=='ground':
            def tagged(*tags):return next(n for n in nodes if str(n.get_editor_property('desc')) in tags)
            base=tagged('LT4Final','FloorSourceColour');normal=tagged('WoodlandSoilDetailSource:Normal','FloorSourceNormal');rough=tagged('WoodlandSoilDetailSource:Rough')
            M.connect_material_property(base,'',u.MaterialProperty.MP_BASE_COLOR)
            props(m,blend_mode=u.BlendMode.BLEND_OPAQUE)
            detail.apply(m,detail.textures(),base,normal,preserve_mud=True,source_roughness=rough)
            visual.material=m
        else:visual.track_material=m
        result['visual_window']=local_visual_window(m,visual)
        M.recompile_material(m);E.save_loaded_asset(m);result['materials'].append(m.get_path_name())
    # Water keeps the existing pond/route topology, using the same updated soil bed.
    for m in [visual.water_simulation_material,visual.sediment_simulation_material,u.load_asset(surface.simulated_water.get_editor_property('surface_material_path'))]:
        for e in M.get_material_expressions(m):
            if isinstance(e,u.MaterialExpressionTextureObjectParameter) and str(e.get_editor_property('parameter_name'))=='GTLS_Paint':e.set_editor_property('texture',maps['paint'])
            if isinstance(e,u.MaterialExpressionScalarParameter) and str(e.get_editor_property('parameter_name'))=='GTLS_DepthScale':e.set_editor_property('default_value',ref['settings']['layer_depth_scale'])
        M.recompile_material(m);E.save_loaded_asset(m)
    return result
