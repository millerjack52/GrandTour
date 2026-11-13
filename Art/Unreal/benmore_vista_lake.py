"""Map-owned visual lake sheet, masked to the source DEM's lake coverage."""
import unreal as u
from pathlib import Path
DEST='/Game/GrandTour/Demo/BenmoreRoads/Vistas'
def build():
    root=Path(u.Paths.project_dir()).resolve();eal=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;assets=u.AssetToolsHelpers.get_asset_tools()
    t=u.AssetImportTask()
    for k,v in dict(filename=str(root/'Art/Export/BenmoreVistas/T_Benmore_LakeCoverage.png'),destination_path=DEST,destination_name='T_Benmore_LakeCoverage',automated=True,replace_existing=True,save=True).items():t.set_editor_property(k,v)
    assets.import_asset_tasks([t]);tex=u.load_asset(DEST+'/T_Benmore_LakeCoverage');assert tex
    for k,v in dict(srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP,never_stream=True).items():tex.set_editor_property(k,v)
    eal.save_loaded_asset(tex)
    path=DEST+'/M_Benmore_VistaLake';m=u.load_asset(path) if eal.does_asset_exist(path) else assets.create_asset('M_Benmore_VistaLake',DEST,u.Material,u.MaterialFactoryNew());mel.delete_all_material_expressions(m)
    for k,v in dict(blend_mode=u.BlendMode.BLEND_MASKED,opacity_mask_clip_value=.45,two_sided=False,tangent_space_normal=False).items():m.set_editor_property(k,v)
    def expr(cls,**kw):
        n=mel.create_material_expression(m,cls)
        for k,v in kw.items():n.set_editor_property(k,v)
        return n
    def custom(names,code,typ=u.CustomMaterialOutputType.CMOT_FLOAT3):
        ins=[]
        for name in names:
            i=u.CustomInput();i.set_editor_property('input_name',name);ins.append(i)
        return expr(u.MaterialExpressionCustom,inputs=ins,code=code,output_type=typ)
    def wire(a,b,name,out=''):assert mel.connect_material_expressions(a,out,b,name)
    p=expr(u.MaterialExpressionWorldPosition);tm=expr(u.MaterialExpressionTime)
    uv=custom(['P'],'return float2((P.x/100+11463)/13680,(4278-P.y/100)/12770);',u.CustomMaterialOutputType.CMOT_FLOAT2);wire(p,uv,'P')
    mask=expr(u.MaterialExpressionTextureSample,texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR);wire(uv,mask,'UVs')
    mel.connect_material_property(mask,'R',u.MaterialProperty.MP_OPACITY_MASK)
    col=custom(['P','Shore'],'float wide=.5+.5*sin(P.x*.00012+P.y*.00019);return lerp(float3(.008,.040,.068),float3(.032,.16,.16),saturate(Shore*.65)) * lerp(.96,1.04,wide);');wire(p,col,'P');wire(mask,col,'Shore','G')
    mel.connect_material_property(col,'',u.MaterialProperty.MP_BASE_COLOR)
    n=custom(['P','Time'],'float a=P.x*.022+P.y*.011+Time*.35;float b=P.x*-.009+P.y*.017-Time*.24;float c=P.x*.0028+P.y*.0011+Time*.09;return normalize(float3(.013*cos(a)-.009*sin(b)+.009*cos(c),.008*cos(a)+.013*sin(b)+.004*cos(c),1));');wire(p,n,'P');wire(tm,n,'Time');mel.connect_material_property(n,'',u.MaterialProperty.MP_NORMAL)
    for prop,val in [(u.MaterialProperty.MP_ROUGHNESS,.12),(u.MaterialProperty.MP_SPECULAR,.65)]:mel.connect_material_property(expr(u.MaterialExpressionConstant,r=val),'',prop)
    glow=expr(u.MaterialExpressionMultiply,const_b=.06);wire(col,glow,'A');mel.connect_material_property(glow,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    assert not mel.recompile_material(m);eal.save_loaded_asset(m)
    act=u.get_editor_subsystem(u.EditorActorSubsystem)
    for a in act.get_all_level_actors():
        if a.get_actor_label()=='Benmore_Vista_Lake':act.destroy_actor(a)
    a=act.spawn_actor_from_class(u.StaticMeshActor,u.Vector());a.set_actor_label('Benmore_Vista_Lake');c=a.static_mesh_component;c.set_static_mesh(u.load_asset('/Engine/BasicShapes/Plane'));c.set_material(0,m)
    c.set_collision_profile_name('NoCollision');c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION);a.set_actor_enable_collision(False)
    for k,v in dict(cast_shadow=False,affect_distance_field_lighting=False,visible_in_ray_tracing=False,receives_decals=False).items():c.set_editor_property(k,v)
    a.set_actor_location(u.Vector(-462300,-210700,60),False,True);a.set_actor_scale3d(u.Vector(13680,12770,1));a.set_actor_rotation(u.Rotator(),False)
    return {'visual_only':True,'collision':'NoCollision','surface_height_above_datum_m':.6,'source_mask':'DEM below datum + 0.48 m','shore_colour':'visual approximation, not bathymetry'}
