"""Purchased forest-floor textures, shared world coordinates, retained native mud normals."""
import unreal as u
from pathlib import Path
from benmore_river_life_materials import Graph,props,NOISE
DEST='/Game/GrandTour/ArtTests/FloraDrive'
SRC=Path('D:/GrandTourAssets/FlippedNormals/Lazy_Forest_Gen_Addon/Assets/Textures/Ground')
mel=u.MaterialEditingLibrary;eal=u.EditorAssetLibrary
COLLECTION=DEST+'/MPC_ForestGround'
def controls():
    c=u.load_asset(COLLECTION) or u.AssetToolsHelpers.get_asset_tools().create_asset('MPC_ForestGround',DEST,u.MaterialParameterCollection,u.MaterialParameterCollectionFactoryNew())
    c.set_editor_property('scalar_parameters',[props(u.CollectionScalarParameter(),parameter_name=k,default_value=v) for k,v in [('POMEnabled',1.),('NormalEnabled',1.),('ReliefDepthCm',2.8),('POMNearCm',700.),('POMFarCm',1800.)]])
    eal.save_loaded_asset(c)
    return c
def height_texture():
    path=DEST+'/T_ForestHeightRGB';t=u.load_asset(path)
    if not t:
        task=props(u.AssetImportTask(),filename='C:/GrandTour/Art/Export/FloraDrive/T_ForestHeightRGB.png',destination_path=DEST,destination_name='T_ForestHeightRGB',automated=True,save=True)
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);t=u.load_asset(path)
    assert t
    props(t,srgb=False,compression_settings=u.TextureCompressionSettings.TC_MASKS,max_texture_size=2048);eal.save_loaded_asset(t)
    return t
def textures():
    result=[]
    for i in (1,2,3):
        pair=[]
        for normal in (False,True):
            name='T_ForestGround_%02d%s'%(i,'N' if normal else '')
            t=u.load_asset(DEST+'/'+name)
            if not t:
                task=props(u.AssetImportTask(),filename=str(SRC/('Ground_%02d%s'%(i,'N.png' if normal else '.jpg'))),destination_path=DEST,destination_name=name,automated=True,save=True)
                u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);t=u.load_asset(DEST+'/'+name)
            assert t
            props(t,srgb=not normal,max_texture_size=2048,compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_DEFAULT)
            # Blender source maps use OpenGL +Y; world XY mapping below explicitly flips Y.
            if normal:props(t,flip_green_channel=True)
            eal.save_loaded_asset(t);pair.append(t)
        result.append(pair)
    return result

def road_mask():
    # Reimport each authoring pass: numerical channels, not colour data.
    task=props(u.AssetImportTask(),filename='C:/GrandTour/Art/Export/FloraDrive/road-relief-mask.png',destination_path=DEST,destination_name='T_RoadReliefMask',automated=True,replace_existing=True,save=True)
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    t=u.load_asset(DEST+'/T_RoadReliefMask');assert t
    props(t,srgb=False,compression_settings=u.TextureCompressionSettings.TC_MASKS,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP)
    eal.save_loaded_asset(t);return t
def apply(m,tex,source_colour=None,source_normal=None,preserve_mud=False,source_roughness=None):
    nodes=list(mel.get_material_expressions(m))
    base=source_colour or next((n for n in nodes if str(n.get_editor_property('desc'))=='FloorSourceColour'),None)
    normal=source_normal or next((n for n in nodes if str(n.get_editor_property('desc'))=='FloorSourceNormal'),None)
    if not base:
        base=mel.get_material_property_input_node(m,u.MaterialProperty.MP_BASE_COLOR);base.set_editor_property('desc','FloorSourceColour')
        normal=mel.get_material_property_input_node(m,u.MaterialProperty.MP_NORMAL);normal.set_editor_property('desc','FloorSourceNormal')
    assert base and normal,m.get_name()
    base.set_editor_property('desc','FloorSourceColour');normal.set_editor_property('desc','FloorSourceNormal')
    for n in nodes:
        if str(n.get_editor_property('desc'))=='ForestFloorDetail':mel.delete_material_expression(m,n)
    g=Graph(m,'ForestFloorDetail');p=g.node(u.MaterialExpressionWorldPosition);cam=g.node(u.MaterialExpressionCameraPositionWS)
    scale=g.node(u.MaterialExpressionScalarParameter,parameter_name='GroundTileCm',default_value=280.)
    uv=g.custom(['P','Scale'],'return float2(P.x,-P.y)/max(Scale,20.);',u.CustomMaterialOutputType.CMOT_FLOAT2);g.wire(p,uv,'P');g.wire(scale,uv,'Scale')
    collection=u.load_asset(COLLECTION);assert collection
    params={k:g.node(u.MaterialExpressionCollectionParameter,collection=collection,parameter_name=k) for k in ['POMEnabled','NormalEnabled','ReliefDepthCm','POMNearCm','POMFarCm']}
    view=g.node(u.MaterialExpressionCameraVectorWS)
    ht=g.node(u.MaterialExpressionTextureObject,texture=height_texture(),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    pom=g.custom(['UV','P','Camera','N','V','Scale','HeightTex']+list(params),NOISE+'''
float2 dx=ddx(UV),dy=ddy(UV);
float facing=dot(normalize(N),normalize(V));
float strength=POMEnabled*(1-smoothstep(POMNearCm,POMFarCm,length(Camera-P)))*smoothstep(.06,.17,facing);
ReliefHeight=.5;
[branch] if(strength<.001)return UV;
float centre=530*sin((P.x+2200)/1050)-150;
float shoulder=smoothstep(280,540,abs(P.y-centre));
float moss=smoothstep(.46,.65,f.n(P.xy/410)+.18*f.n(P.xy/95))*shoulder;
float litter=smoothstep(.43,.58,f.n(P.xy/290+31))*shoulder*(1-moss*.85);
float3 weights=float3(moss*(1-litter),litter,(1-moss)*(1-litter));
float depthCm=ReliefDepthCm*dot(weights,float3(1.,.60,.55));
float2 ray=float2(-V.x,V.y)*(depthCm*strength*max(N.z,.1)/max(facing,.08))/max(Scale,20.);
int steps=(int)lerp(24.,10.,saturate(facing));
float t=0,previousT=0,previousDiff=0;
float2 result=UV;
[loop] for(int i=0;i<=24;i++){
    float2 at=UV+ray*t;
    float h=dot(Texture2DSampleGrad(HeightTex,HeightTexSampler,at,dx,dy).rgb,weights);
    float diff=t-(1-h);
    if(diff>=0 || i==steps){
        float blend=saturate(-previousDiff/max(diff-previousDiff,.00001));
        result=UV+ray*lerp(previousT,t,blend);ReliefHeight=h;break;
    }
    previousT=t;previousDiff=diff;t+=1./steps;
}
return result;
''',u.CustomMaterialOutputType.CMOT_FLOAT2,outputs=[('ReliefHeight',u.CustomMaterialOutputType.CMOT_FLOAT1)])
    for k,n in [('UV',uv),('P',p),('Camera',cam),('N',normal),('V',view),('Scale',scale),('HeightTex',ht)]+list(params.items()):g.wire(n,pom,k)
    du=g.custom(['UV'],'return ddx(UV);',u.CustomMaterialOutputType.CMOT_FLOAT2);dv=g.custom(['UV'],'return ddy(UV);',u.CustomMaterialOutputType.CMOT_FLOAT2);g.wire(uv,du,'UV');g.wire(uv,dv,'UV')
    inputs=[('P',p),('Camera',cam),('Base',base),('N',normal)]
    inputs.append(('PreserveMud',g.scalar(1. if preserve_mud else 0.)))
    inputs.append(('SourceRough',source_roughness or g.scalar(.85)))
    road_uv=g.custom(['P'],'return (P.xy+3150.)/6300.;',u.CustomMaterialOutputType.CMOT_FLOAT2);g.wire(p,road_uv,'P')
    mask=g.node(u.MaterialExpressionTextureSample,texture=road_mask(),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS);g.wire(road_uv,mask,'UVs');inputs.append(('Road',mask))
    for i,(colour,norm) in enumerate(tex):
        c=g.node(u.MaterialExpressionTextureSample,texture=colour,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR);g.wire(pom,c,'UVs')
        n=g.tex(norm,pom,True)
        for sample in [c,n]:
            props(sample,mip_value_mode=u.TextureMipValueMode.TMVM_DERIVATIVE,sampler_source=u.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS);g.wire(du,sample,'DDX(UVs)');g.wire(dv,sample,'DDY(UVs)')
        inputs.extend([('C'+str(i),c),('N'+str(i),n)])
    strength=g.node(u.MaterialExpressionScalarParameter,parameter_name='GroundNormalStrength',default_value=1.15);inputs.append(('Strength',strength));inputs.append(('NormalEnabled',params['NormalEnabled']))
    detail=g.custom([k for k,n in inputs],NOISE+'''
float2 q=P.xy;
float centre=530*sin((q.x+2200)/1050)-150;
float shoulder=smoothstep(280,540,abs(q.y-centre));
float patch=f.n(q/410)+.18*f.n(q/95);
float moss=smoothstep(.46,.65,patch)*shoulder;
float litter=smoothstep(.43,.58,f.n(q/290+31))*shoulder*(1-moss*.85);
float3 c=lerp(C2,C0,moss);c=lerp(c,C1,litter);
float3 n=lerp(N2,N0,moss);n=normalize(lerp(n,N1,litter));
float fade=1-smoothstep(1800,6500,length(P-Camera));
// World-aligned normal detail laid over the live tyre/rut normal.
DetailNormal=normalize(float3(N.xy+float2(n.x,-n.y)*Strength*NormalEnabled*fade,N.z));
float macro=lerp(.58,1.06,f.n(q/700));
float3 palette=c*float3(.64,.67,.54)*macro;
// Compacted wheel channels and drier raised aggregates share the geometric masks.
// This is material variation, not a painted directional shadow.
float3 colour=lerp(Base*.72,palette,lerp(.76,1.,shoulder));
colour*=lerp(1.,.72,Road.r)*lerp(1.,1.10,Road.b);
DetailRoughness=clamp(.85-.19*Road.r+.07*Road.b,.6,.94);
if(PreserveMud>.5){
 float grain=clamp(dot(c,float3(.2126,.7152,.0722))/.18,.75,1.25);
 colour=lerp(Base*lerp(1.,grain,.25),palette,shoulder);
 DetailRoughness=lerp(SourceRough,.88,shoulder);
}
return colour;
''',outputs=[('DetailNormal',u.CustomMaterialOutputType.CMOT_FLOAT3),('DetailRoughness',u.CustomMaterialOutputType.CMOT_FLOAT1)])
    for k,n in inputs:g.wire(n,detail,k)
    g.output(detail,u.MaterialProperty.MP_BASE_COLOR);g.output(detail,u.MaterialProperty.MP_NORMAL,'DetailNormal')
    g.output(detail,u.MaterialProperty.MP_ROUGHNESS,'DetailRoughness')
    mel.recompile_material(m);eal.save_loaded_asset(m)
