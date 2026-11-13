"""Matched scanned mud relief, isolated to the six-character art review material."""
from pathlib import Path
import shutil
import time
import unreal as u
import landscape_surface_material as base

# Paint's softness/depth select the dry crust character; wetness dissolves the crust.
STYLE = r'''
float crust=(1-smoothstep(.15,.35,wet))*(1-smoothstep(.25,.45,paint.a))*smoothstep(20,28,thickness);
float4 scanUV=float4(mudUV/260.,mudUV/180.);
float reliefMask=active*mud*(1-pool)*(1-field.a*.75);
'''

POM = base.COMMON + STYLE + r'''
// GTLS_POM: shared coordinates keep albedo, normal and roughness attached to relief.
float3 view=normalize(View);
float fade=(1-smoothstep(1000,2200,distance(Camera,P)))*smoothstep(.08,.25,abs(view.z));
float strength=reliefMask*fade*POMEnabled;
float2 ray=-view.xy/max(abs(view.z),.2)*2.5*strength;
float4 stepUV=float4(ray/260.,ray/180.);
float4 gx=ddx(scanUV),gy=ddy(scanUV);
float steps=lerp(24,12,saturate(abs(view.z)));
float t=0,prevT=0,prevD=0;float4 q=scanUV;
if(strength>.001) {
    float h=lerp(Texture2DSampleGrad(WetHeight,WetHeightSampler,q.xy,gx.xy,gy.xy).r,
                 Texture2DSampleGrad(DryHeight,DryHeightSampler,q.zw,gx.zw,gy.zw).r,crust);
    float d=1-h;
    [loop] for(int i=0;i<24;i++) {
        if(t>=d) break;
        prevT=t;prevD=d;t+=1/steps;q=scanUV+stepUV*t;
        h=lerp(Texture2DSampleGrad(WetHeight,WetHeightSampler,q.xy,gx.xy,gy.xy).r,
               Texture2DSampleGrad(DryHeight,DryHeightSampler,q.zw,gx.zw,gy.zw).r,crust);
        d=1-h;
    }
    float a=saturate((prevD-prevT)/max((t-d)+(prevD-prevT),.00001));
    q=scanUV+stepUV*lerp(prevT,t,a);
}
return q;
'''

def install(destination, presets, report):
    root=Path(u.Paths.project_dir()).resolve()
    mel=u.MaterialEditingLibrary; assets=u.EditorAssetLibrary
    material=assets.load_asset(destination+'/M_LandscapeSurface');assert material
    expressions=list(mel.get_material_expressions(material))
    def expr(cls, **props):
        e=mel.create_material_expression(material,cls)
        for k,v in props.items():e.set_editor_property(k,v)
        return e
    def param(name,cls,**props):
        e=next((e for e in expressions if isinstance(e,cls) and str(e.get_editor_property('parameter_name'))==name),None)
        return e or expr(cls,parameter_name=name,**props)
    def texture(asset,kind,name):
        path=destination+'/PBR/T_'+asset+'_'+kind
        t=assets.load_asset(path) if assets.does_asset_exist(path) else None
        if t is None:
            task=u.AssetImportTask()
            ext='jpg' if kind=='Diffuse' else 'png'
            for k,v in dict(filename=str(root/'Art/Textures/LandscapeMudPBR'/asset/(kind+'.'+ext)),destination_path=destination+'/PBR',destination_name=path.rsplit('/',1)[1],automated=True,save=True,replace_existing=False).items():task.set_editor_property(k,v)
            u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            t=assets.load_asset(path);assert t,path
        t.set_editor_property('srgb',kind=='Diffuse')
        t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if kind=='nor_dx' else u.TextureCompressionSettings.TC_DEFAULT if kind=='Diffuse' else u.TextureCompressionSettings.TC_MASKS)
        assets.save_loaded_asset(t)
        sampler=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind=='nor_dx' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if kind=='Diffuse' else u.MaterialSamplerType.SAMPLERTYPE_MASKS
        return param(name,u.MaterialExpressionTextureObjectParameter,texture=t,sampler_type=sampler)
    maps={}
    for prefix,asset in [('Wet','brown_mud_02'),('Dry','mud_cracked_dry_03')]:
        for kind,suffix in [('Diffuse','Color'),('Displacement','Height'),('nor_dx','Normal'),('Rough','Rough'),('AO','AO')]:
            maps[prefix+suffix]=texture(asset,kind,prefix+suffix)
    shared={}
    for name,pname in [('Paint','GTLS_Paint'),('Field','GTLS_Field'),('Water','GTLS_Water'),('Window','GTLS_Window'),('PaintWindow','GTLS_PaintWindow'),('Ready','GTLS_Ready'),('Enabled','GTLS_DisplacementEnabled')]:
        shared[name]=next(e for e in expressions if isinstance(e,(u.MaterialExpressionTextureObjectParameter,u.MaterialExpressionScalarParameter,u.MaterialExpressionVectorParameter)) and str(e.get_editor_property('parameter_name'))==pname)
    shared['P']=next(e for e in expressions if isinstance(e,u.MaterialExpressionWorldPosition))
    def connect(node,inputs):
        entries=list(node.get_editor_property('inputs'))
        for name,value in inputs.items():
            if not any(str(e.get_editor_property('input_name'))==name for e in entries):
                e=u.CustomInput();e.set_editor_property('input_name',name);entries.append(e)
        node.set_editor_property('inputs',entries)
        for name,value in inputs.items():assert mel.connect_material_expressions(value,'',node,name),name
    pom=next((e for e in expressions if isinstance(e,u.MaterialExpressionCustom) and 'GTLS_POM:' in e.get_editor_property('code')),None)
    if pom is None:pom=expr(u.MaterialExpressionCustom,output_type=u.CustomMaterialOutputType.CMOT_FLOAT4)
    pom.set_editor_property('code',POM)
    def singleton(cls):
        return next((e for e in expressions if isinstance(e,cls)),None) or expr(cls)
    connect(pom,dict(shared,WetHeight=maps['WetHeight'],DryHeight=maps['DryHeight'],View=singleton(u.MaterialExpressionCameraVectorWS),Camera=singleton(u.MaterialExpressionCameraPositionWS),POMEnabled=param('GTLS_POMEnabled',u.MaterialExpressionScalarParameter,default_value=1.)))
    color=base.COLOR
    a=color.index('float broad=');b=color.index('float3 slurry=')
    color=color[:a]+STYLE+r'''
float3 scanned=Texture2DSample(WetColor,WetColorSampler,ReliefUV.xy).rgb;
float3 dry=Texture2DSample(DryColor,DryColorSampler,ReliefUV.zw).rgb;
dry=lerp(dot(dry,float3(.2126,.7152,.0722)).xxx,dry,.3)*float3(.9,.93,.91);
float3 soil=lerp(scanned,dry,crust);
soil=lerp(dot(soil,float3(.2126,.7152,.0722)).xxx,soil,.38);
soil*=lerp(lerp(2.2,1.8,wet),.9,crust)*float3(.95,1.,.93)*(1-field.a*.08);
float3 colour=lerp(soil,gravel,paint.b*(1-mud));
'''+color[b:]
    normal=base.NORMAL
    a=normal.index('float2 microSlope=')
    normal=normal[:a]+STYLE+r'''
float3 wn=UnpackNormalMap(float4(Texture2DSample(WetNormal,WetNormalSampler,ReliefUV.xy).xyz,1));
float3 dn=UnpackNormalMap(float4(Texture2DSample(DryNormal,DryNormalSampler,ReliefUV.zw).xyz,1));
float3 sn=normalize(lerp(wn,dn,crust));
float2 tilt=slope-sn.xy/max(sn.z,.35)*reliefMask*.65+detail.xy*.22*(1-mud)+waveN*pool*3;
return normalize(float3(BaseN.xy-lerp(tilt,slope,ClayReview),BaseN.z));
'''
    rough=base.COMMON+STYLE+r'''// GTLS_ROUGHNESS
float r=lerp(Texture2DSample(WetRough,WetRoughSampler,ReliefUV.xy).r,Texture2DSample(DryRough,DryRoughSampler,ReliefUV.zw).r,crust);
return lerp(lerp(.91,clamp(r*lerp(1,.7,wet),.42,.95),mud),.38,pool);
'''
    displacement=base.DISPLACEMENT.replace('float h=clamp(',STYLE+r'''
float scannedHeight=lerp(Texture2DSampleLevel(WetHeight,WetHeightSampler,scanUV.xy,0).r,Texture2DSampleLevel(DryHeight,DryHeightSampler,scanUV.zw,0).r,crust);
micro=(scannedHeight-.62)*2.*reliefMask;
float h=clamp(''')
    for e in expressions:
        if not isinstance(e,u.MaterialExpressionCustom):continue
        code=e.get_editor_property('code')
        if 'float3 fine=' in code:e.set_editor_property('code','if(ClayReview>.5) return float3(.32,.32,.32);\n'+color);connect(e,dict(maps,ReliefUV=pom))
        elif 'float2 slope=' in code:e.set_editor_property('code',normal);connect(e,dict(maps,ReliefUV=pom))
        elif 'GTLS_ROUGHNESS' in code:e.set_editor_property('code','if(ClayReview>.5) return .9;\n'+rough);connect(e,dict(maps,ReliefUV=pom))
        elif 'GTLS_SPECULAR' in code:e.set_editor_property('code','if(ClayReview>.5) return .08;\n'+base.COMMON+'// GTLS_SPECULAR\nreturn lerp(.16,.09,pool);')
        elif 'return saturate((h*Enabled+50)/65)' in code:e.set_editor_property('code',displacement);connect(e,dict(WetHeight=maps['WetHeight'],DryHeight=maps['DryHeight']))
    ao=next((e for e in expressions if isinstance(e,u.MaterialExpressionCustom) and 'GTLS_SCAN_AO' in e.get_editor_property('code')),None)
    if ao is None:ao=expr(u.MaterialExpressionCustom,output_type=u.CustomMaterialOutputType.CMOT_FLOAT1)
    ao.set_editor_property('code','if(ClayReview>.5) return 1.;\n'+base.COMMON+STYLE+r'''// GTLS_SCAN_AO
float occlusion=lerp(Texture2DSample(WetAO,WetAOSampler,ReliefUV.xy).r,Texture2DSample(DryAO,DryAOSampler,ReliefUV.zw).r,crust);
return lerp(1,occlusion,mud*(1-pool)*.65);
''')
    connect(ao,dict(shared,WetAO=maps['WetAO'],DryAO=maps['DryAO'],ReliefUV=pom,ClayReview=param('GTLS_ClayReview',u.MaterialExpressionScalarParameter,default_value=0.)))
    assert mel.connect_material_property(ao,'',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
    mel.recompile_material(material);assets.save_loaded_asset(material)
    # Explicitly update only this study's regions, including already-existing review maps.
    actor=next(a for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors() if isinstance(a,u.GTLandscapeSurface))
    level=root/'Content/GrandTour/ArtTests/LandscapeMudVariants/L_LandscapeMudVariants.umap'
    backup=root/'Saved/LandscapeMudVariants'/str(time.time_ns());backup.mkdir(parents=True)
    shutil.copy2(level,backup/level.name)
    regions=list(actor.get_editor_property('mud_regions'))
    for region,preset in zip(regions,presets):
        assert str(region.get_editor_property('name'))==preset['key']
        region.set_editor_property('relief',preset['relief'])
    actor.set_editor_property('mud_regions',regions)
    assert u.GTLandscapeSurfaceSetupLibrary.import_rest_heights(actor,maps['WetHeight'].get_editor_property('texture'),maps['DryHeight'].get_editor_property('texture'))
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
    report['pbr']={'sources':['https://polyhaven.com/a/brown_mud_02','https://polyhaven.com/a/mud_cracked_dry_03'],'pom_depth_cm':2.5,'scanned_micro_range_cm':2,'cpu_scan_resolution':32,'cpu_scan_tile_cm':[260,180],'level_backup':str(backup/level.name)}
