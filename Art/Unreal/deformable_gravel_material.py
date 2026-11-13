"""Gravel over the existing physical heightfield; shared sampling on both sides of the patch edge."""
import ast
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve()
DEST='/Game/GrandTour/ArtTests/DeformableGravel'
REF='/Game/GrandTour/ArtTests/GravelRoad'
mel=u.MaterialEditingLibrary; eal=u.EditorAssetLibrary

def props(o,**kw):
    for k,v in kw.items():o.set_editor_property(k,v)
    return o

def build(patch):
    path=DEST+('/M_GravelField' if patch else '/M_GravelLandscape')
    m=eal.load_asset(path)
    if m is None:
        m=(u.AssetToolsHelpers.get_asset_tools().create_asset('M_GravelField',DEST,u.Material,u.MaterialFactoryNew()) if patch
           else eal.duplicate_asset('/Game/GrandTour/Materials/M_GT_Landscape',path))
    if patch:
        for e in list(mel.get_material_expressions(m)):mel.delete_material_expression(m,e)
    else:
        # Rebuild our own nodes only; preserve the landscape's layer blends and runtime hole mask.
        for e in list(mel.get_material_expressions(m)):
            if str(e.get_editor_property('desc')).startswith('Gravel:') or isinstance(e,u.MaterialExpressionLandscapeGrassOutput):mel.delete_material_expression(m,e)
    props(m,tangent_space_normal=False)
    row=[0]
    def expr(cls,**kw):
        row[0]+=140
        return props(mel.create_material_expression(m,cls,-2200,row[0]),desc='Gravel:'+str(row[0]),**kw)
    def wire(a,b,name,out=''):assert mel.connect_material_expressions(a,out,b,name),name
    def custom(code,inputs,kind=u.CustomMaterialOutputType.CMOT_FLOAT3,outputs=()):
        n=expr(u.MaterialExpressionCustom,code=code,output_type=kind)
        n.set_editor_property('inputs',[props(u.CustomInput(),input_name=k) for k in inputs])
        n.set_editor_property('additional_outputs',[props(u.CustomOutput(),output_name=k,output_type=t) for k,t in outputs])
        return n
    p=expr(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    vn=expr(u.MaterialExpressionVertexNormalWS)
    wet=expr(u.MaterialExpressionCollectionParameter,collection=u.load_asset('/Game/GrandTour/Materials/MPC_Weather'),parameter_name='Wetness')
    zero=expr(u.MaterialExpressionConstant, r=0.)
    if patch:
        tree=ast.parse((ROOT/'Art/Unreal/setup_m6_mud.py').read_text())
        constants={n.targets[0].id:ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('WPO_HLSL','SURFACE_A')}
        rt=u.load_asset('/Game/GrandTour/Terrain/RT_TrackPaint')
        field=expr(u.MaterialExpressionTextureObjectParameter,parameter_name='MudField',texture=rt,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
        params={}
        for name,val in [('PatchMin',(0,0,0)),('PatchSize',(100,100,0)),('PatchTexels',(8,8,0))]:
            params[name]=expr(u.MaterialExpressionVectorParameter,parameter_name=name,default_value=u.LinearColor(*val,1))
        inputs=['WorldPos','PatchMin','PatchSize','PatchTexels','Tex']
        displace=custom(constants['WPO_HLSL'],inputs+['SlideScale'])
        prefix=constants['SURFACE_A'].split('// The ground this mesh')[0]
        state=custom(prefix+'Shift=s.gb*100.0; Tracks=tracks; CutCm=max(0,-s.r*100); return n;',inputs+['VertexNormal','Wetness'],outputs=[('Shift',u.CustomMaterialOutputType.CMOT_FLOAT2),('Tracks',u.CustomMaterialOutputType.CMOT_FLOAT1),('CutCm',u.CustomMaterialOutputType.CMOT_FLOAT1)])
        for target in [displace,state]:
            wire(p,target,'WorldPos');wire(field,target,'Tex')
            for name,node in params.items():wire(node,target,name)
        wire(zero,displace,'SlideScale');wire(vn,state,'VertexNormal');wire(wet,state,'Wetness')
        assert mel.connect_material_property(displace,'',u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    names=['P','N','Shift','Tracks','CutCm','Wet','FineC','CoarseC','FineN','CoarseN']
    code='''
float2 q=P.xy-Shift;
// Approved gravel-04 bakes: 6 m square, mirrored with the normal axes reflected too.
float2 tile=frac(q/1200.);
float2 uv=1-abs(tile*2-1);uv.y=1-uv.y;
float lane=max(exp(-pow((P.y-79.)/35.,2.)),exp(-pow((P.y+79.)/35.,2.)));
float looseSection=smoothstep(7000.,7900.,P.x)*(1-smoothstep(11300.,12300.,P.x));
float loose=saturate(.28+.48*smoothstep(135.,330.,abs(P.y))+.24*looseSection-.21*lane);
// Compaction exposes the finer matrix; displacement and its slope still come from the CPU field.
float worked=saturate(Tracks)*smoothstep(.05,1.5,CutCm);
loose*=1-.50*worked;
float2 coarseUv=uv;
float3 col=lerp(Texture2DSample(FineC,FineCSampler,uv).rgb,Texture2DSample(CoarseC,CoarseCSampler,coarseUv).rgb,loose);
float2 fn=UnpackNormalMap(Texture2DSample(FineN,FineNSampler,uv)).xy;
float2 cn=UnpackNormalMap(Texture2DSample(CoarseN,CoarseNSampler,coarseUv)).xy;
float2 detail=lerp(fn,cn,loose)*float2(tile.x<.5?1:-1,tile.y<.5?-1:1)*lerp(.85,.58,worked);
float grass=smoothstep(375.,590.,abs(P.y));
float variation=.5+.5*sin(P.x*.006)*sin(P.y*.008);
col=lerp(col*.82,lerp(float3(.10,.081,.046),float3(.18,.147,.077),variation),grass);
col*=(1-.16*saturate(Wet))*(1-.06*worked);
Normal=normalize(N+float3(detail*(1-grass),0));
Rough=lerp(.87,.76,saturate(Wet));
return col;
'''
    surf=custom(code,names,outputs=[('Normal',u.CustomMaterialOutputType.CMOT_FLOAT3),('Rough',u.CustomMaterialOutputType.CMOT_FLOAT1)])
    wire(p,surf,'P');wire(wet,surf,'Wet')
    for pin,out in [('N',''),('Shift','Shift'),('Tracks','Tracks'),('CutCm','CutCm')]:
        wire(state if patch else (vn if pin=='N' else zero),surf,pin,out if patch else '')
    for pin,asset in [('FineC','CompactColor'),('CoarseC','LooseColor'),('FineN','CompactNormal'),('CoarseN','LooseNormal')]:
        tex=u.load_asset(REF+'/T_GR_'+asset);assert tex,asset
        node=expr(u.MaterialExpressionTextureObject,texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if pin.endswith('N') else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        wire(node,surf,pin)
    if not patch:
        # Keep all six physical landscape layers referenced, with the same appearance for this road study.
        layer=expr(u.MaterialExpressionLandscapeLayerBlend)
        layer.set_editor_property('layers',[props(u.LayerBlendInput(),layer_name=name,blend_type=u.LandscapeLayerBlendType.LB_WEIGHT_BLEND) for name in ['Tarmac','Dirt','Mud','Snow','Scrub','Bog']])
        for name in ['Tarmac','Dirt','Mud','Snow','Scrub','Bog']:wire(surf,layer,'Layer '+name)
    for node,out,prop in [(surf if patch else layer,'',u.MaterialProperty.MP_BASE_COLOR),(surf,'Normal',u.MaterialProperty.MP_NORMAL),(surf,'Rough',u.MaterialProperty.MP_ROUGHNESS)]:
        assert mel.connect_material_property(node,out,prop)
    errors=mel.recompile_material(m);assert not errors,str(errors)
    eal.save_loaded_asset(m)
    return path
