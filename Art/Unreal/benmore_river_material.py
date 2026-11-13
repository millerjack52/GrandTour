"""Single Layer Water driven by the numerical flow bake; procedural ripples."""
import unreal as u
DEST='/Game/GrandTour/Demo/BenmoreRoads/Rivers'

# The same pigment mixture is used on the bank mesh and its terrain skirt.
# Numeric art weights also drive the deliberately clustered vegetation.
BANK_PIGMENT='''
float tone=clamp(dot(Gravel,float3(.2126,.7152,.0722))/.24,.68,1.30);
float3 mineral=lerp(float3(.130,.147,.141),float3(.225,.207,.163),Art.b);
float3 soil=lerp(float3(.220,.164,.073),float3(.365,.268,.112),Art.b);
float3 ground=lerp(mineral*tone,soil*lerp(.96,1.04,tone),smoothstep(.15,.78,Art.r));
float damp=saturate(Art.g*.8+1-smoothstep(.1,1.65,Bank.r*16));
ground=lerp(ground,ground*float3(.47,.56,.54),damp*.78);
'''

def build(flow,banks,name='M_Benmore_BakedRiver'):
    mel=u.MaterialEditingLibrary;eal=u.EditorAssetLibrary;assets=u.AssetToolsHelpers.get_asset_tools()
    def props(o,**kw):
        for k,v in kw.items():o.set_editor_property(k,v)
        return o
    m=u.load_asset(DEST+'/'+name) or assets.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    # UE 5.8's bulk delete iterates the collection it mutates, leaving nodes.
    # Iterate a snapshot, particularly to avoid duplicate water outputs.
    for old in list(mel.get_material_expressions(m)):mel.delete_material_expression(m,old)
    assert not mel.get_material_expressions(m)
    props(m,shading_model=u.MaterialShadingModel.MSM_SINGLE_LAYER_WATER,blend_mode=u.BlendMode.BLEND_MASKED,opacity_mask_clip_value=.5,two_sided=False,tangent_space_normal=False)
    def expr(cls,**kw):return props(mel.create_material_expression(m,cls),**kw)
    def wire(a,b,pin,out=''):
        clean=lambda s:''.join(c.lower() for c in s if c.isalnum())
        names=mel.get_material_expression_input_names(b)
        actual=next((n for n in names if clean(n)==clean(pin)),pin)
        assert mel.connect_material_expressions(a,out,b,actual),(a.get_name(),pin,names)
    def custom(names,code,typ=u.CustomMaterialOutputType.CMOT_FLOAT3):return expr(u.MaterialExpressionCustom,inputs=[props(u.CustomInput(),input_name=n) for n in names],code=code,output_type=typ)
    def scalar(v):return expr(u.MaterialExpressionConstant,r=v)
    def vector(v):return expr(u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*v,1))
    p=expr(u.MaterialExpressionWorldPosition);tm=expr(u.MaterialExpressionTime);camera=expr(u.MaterialExpressionCameraPositionWS);vn=expr(u.MaterialExpressionVertexNormalWS)
    uv=custom(['P'],'return (P.xy*.01-float2(-1570,-20)+.5)/float2(1331,686);',u.CustomMaterialOutputType.CMOT_FLOAT2);wire(p,uv,'P')
    sample=expr(u.MaterialExpressionTextureSample,texture=flow,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR);wire(uv,sample,'UVs')
    coverage=expr(u.MaterialExpressionTextureSample,texture=banks,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR);wire(uv,coverage,'UVs');mel.connect_material_property(coverage,'G',u.MaterialProperty.MP_OPACITY_MASK)
    # Two staggered phases cross-fade before either reset; the baked velocity
    # advects patterns in metres/second. No cumulative UV stretching.
    normal=custom(['P','Time','Flow','Camera','N'],'''
float2 q=P.xy*.01, v=(Flow.rg-.5)*12;
v*=step(-1570,q.x)*step(q.x,-240)*step(-20,q.y)*step(q.y,665);
float t0=frac(Time/6),t1=frac(Time/6+.5),blend=abs(2*t0-1);
float2 a=q-v*(t0*6),b=q-v*(t1*6);
float2 wa=float2(sin(dot(a,float2(8.1,5.3)))+.45*sin(dot(a,float2(-13.3,11.7))), cos(dot(a,float2(5.6,-9.2)))+.45*cos(dot(a,float2(17.2,6.1))));
float2 wb=float2(sin(dot(b,float2(8.1,5.3)))+.45*sin(dot(b,float2(-13.3,11.7))), cos(dot(b,float2(5.6,-9.2)))+.45*cos(dot(b,float2(17.2,6.1))));
float fade=1-smoothstep(35,180,length(Camera-P)*.01);
float amplitude=lerp(.025,.105,saturate(length(v)/3))*fade;
float2 broad=float2(sin(dot(q-v*Time*.12,float2(.7,.4))),cos(dot(q-v*Time*.12,float2(.2,-.8))))*.009;
return normalize(N+float3(lerp(wa,wb,blend)*amplitude+broad,0));
''')
    for a,pin in [(p,'P'),(tm,'Time'),(sample,'Flow'),(camera,'Camera'),(vn,'N')]:wire(a,normal,pin)
    mel.connect_material_property(normal,'',u.MaterialProperty.MP_NORMAL)
    foam=custom(['P','Time','Flow','Potential','Camera'],'''
float2 q=P.xy*.01,v=(Flow.rg-.5)*12;
float inside=step(-1570,q.x)*step(q.x,-240)*step(-20,q.y)*step(q.y,665);
v*=inside;
float t0=frac(Time/6),t1=frac(Time/6+.5),blend=abs(2*t0-1);
float2 a=q-v*t0*6,b=q-v*t1*6;
float f0=sin(a.x*4.3+a.y*2.1)*sin(a.x*-1.6+a.y*5.7);
float f1=sin(b.x*4.3+b.y*2.1)*sin(b.x*-1.6+b.y*5.7);
float shape=smoothstep(.12,.62,lerp(f0,f1,blend)*.5+.5);
float detail=lerp(shape,.34,smoothstep(80,450,length(Camera-P)*.01));
return saturate(Potential*detail*1.5)*inside;
''',u.CustomMaterialOutputType.CMOT_FLOAT1)
    for a,pin in [(p,'P'),(tm,'Time'),(sample,'Flow'),(camera,'Camera')]:wire(a,foam,pin)
    wire(sample,foam,'Potential','A')
    col=custom(['Foam'],'return lerp(float3(.012,.027,.023),float3(.56,.61,.54),Foam);');wire(foam,col,'Foam');mel.connect_material_property(col,'',u.MaterialProperty.MP_BASE_COLOR)
    rough=custom(['Foam'],'return lerp(.14,.58,Foam);',u.CustomMaterialOutputType.CMOT_FLOAT1);wire(foam,rough,'Foam');mel.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
    opacity=custom(['Foam'],'return lerp(.09,.95,Foam);',u.CustomMaterialOutputType.CMOT_FLOAT1);wire(foam,opacity,'Foam');mel.connect_material_property(opacity,'',u.MaterialProperty.MP_OPACITY)
    mel.connect_material_property(scalar(.32),'',u.MaterialProperty.MP_SPECULAR)
    water=expr(u.MaterialExpressionSingleLayerWaterMaterialOutput)
    wire(vector((.0017,.0034,.0028)),water,'Scattering Coefficients')
    wire(vector((.014,.0055,.0035)),water,'Absorption Coefficients')
    wire(scalar(.25),water,'PhaseG');wire(vector((.88,.94,.92)),water,'Color Scale Behind Water')
    assert not mel.recompile_material(m);assert eal.save_loaded_asset(m)
    return m

def lake_junction(banks):
    """Use common optical shading and complementary coverage at the lake join."""
    mel=u.MaterialEditingLibrary;eal=u.EditorAssetLibrary;name=DEST+'/M_Benmore_RiverLake'
    m=build(u.load_asset(DEST+'/T_Benmore_RiverFlow'),banks,'M_Benmore_RiverLake')
    node=mel.create_material_expression(m,u.MaterialExpressionCustom);node.set_editor_property('desc','RiverLakeJunction')
    inputs=[]
    mouth=u.load_asset(DEST+'/T_Benmore_RiverMouth')
    for pin_name in ['P','Old','Bank']+(['Mouth'] if mouth else []):
        pin=u.CustomInput();pin.set_editor_property('input_name',pin_name);inputs.append(pin)
    node.set_editor_property('inputs',inputs);node.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
    code='''float2 uv=(P.xy*.01-float2(-1570,-20)+.5)/float2(1331,686);
float inside=step(0,uv.x)*step(0,uv.y)*step(uv.x,1)*step(uv.y,1);
float river=Texture2DSample(Bank,BankSampler,uv).g;
float2 luv=float2((P.x*.01+11463)/13680,(4278-P.y*.01)/12770);
float lake=Texture2DSample(Old,OldSampler,luv).r;
'''
    if mouth:code+='float4 detail=Texture2DSample(Mouth,MouthSampler,uv);lake=lerp(lake,detail.g,step(.99,detail.r)*inside);'
    node.set_editor_property('code',code+'return lake*(1-step(.5,river)*inside);')
    p=mel.create_material_expression(m,u.MaterialExpressionWorldPosition);p.set_editor_property('desc','RiverLakeJunction')
    assert mel.connect_material_expressions(p,'',node,'P')
    textures=[('Bank',banks),('Old',u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Vistas/T_Benmore_LakeCoverage'))]
    if mouth:textures.append(('Mouth',mouth))
    for pin_name,t in textures:
        tex=mel.create_material_expression(m,u.MaterialExpressionTextureObject);tex.set_editor_property('texture',t);tex.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
        assert mel.connect_material_expressions(tex,'',node,pin_name)
    mel.connect_material_property(node,'',u.MaterialProperty.MP_OPACITY_MASK)
    assert not mel.recompile_material(m);assert eal.save_loaded_asset(m);return m

def terrain_material(banks,vegetation):
    """Clone the approved terrain, changing only the river's wet bed and banks."""
    mel=u.MaterialEditingLibrary;eal=u.EditorAssetLibrary
    src='/Game/GrandTour/Demo/BenmoreRoads/Composition/M_Composition_Terrain';dest=DEST+'/M_Benmore_RiverTerrain'
    # Idempotence: bank wrapper is rebuilt from the unchanged composition copy.
    m=u.load_asset(dest) if eal.does_asset_exist(dest) else eal.duplicate_asset(src,dest)
    nodes=mel.get_material_expressions(m)
    for n in nodes:
        if isinstance(n,u.MaterialExpressionTextureSample) and n.get_editor_property('texture') and n.get_editor_property('texture').get_name()=='T_Benmore_VegetationMask':n.set_editor_property('texture',vegetation)
    def props(o,**kw):
        for k,v in kw.items():o.set_editor_property(k,v)
        return o
    def expr(cls,**kw):return props(mel.create_material_expression(m,cls),desc='BenmoreRiverBank',**kw)
    def custom(names,code,typ=u.CustomMaterialOutputType.CMOT_FLOAT3):return expr(u.MaterialExpressionCustom,inputs=[props(u.CustomInput(),input_name=n) for n in names],code=code,output_type=typ)
    def wire(a,b,pin,out=''):assert mel.connect_material_expressions(a,out,b,pin)
    # Locate the existing complete pigment expression, preserving the road POM.
    pigment=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and 'float3 straw=' in n.get_editor_property('code') and 'return P.z<48' in n.get_editor_property('code'))
    for n in nodes:
        if str(n.get_editor_property('desc'))=='BenmoreRiverBank':mel.delete_material_expression(m,n)
    p=expr(u.MaterialExpressionWorldPosition)
    uv=custom(['P'],'return (P.xy*.01-float2(-1570,-20)+.5)/float2(1331,686);',u.CustomMaterialOutputType.CMOT_FLOAT2);wire(p,uv,'P')
    mask=expr(u.MaterialExpressionTextureSample,texture=banks,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR);wire(uv,mask,'UVs')
    graveluv=custom(['P'],'return P.xy/1250;',u.CustomMaterialOutputType.CMOT_FLOAT2);wire(p,graveluv,'P')
    gravel=expr(u.MaterialExpressionTextureSample,texture=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/ReferenceSurface/T_Benmore_LooseGravel'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR);wire(graveluv,gravel,'UVs')
    art_texture=u.load_asset(DEST+'/T_Benmore_RiverBankArt')
    if art_texture:
        art=expr(u.MaterialExpressionTextureSample,texture=art_texture,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR);wire(uv,art,'UVs')
        bank=custom(['UV','Bank','Base','Gravel','Art','Influence'],BANK_PIGMENT+'''
float inside=step(0,UV.x)*step(0,UV.y)*step(UV.x,1)*step(UV.y,1);
return lerp(Base,ground,Influence*inside*.96);
''')
        for a,pin in [(uv,'UV'),(mask,'Bank'),(pigment,'Base'),(gravel,'Gravel'),(art,'Art')]:wire(a,bank,pin)
        wire(art,bank,'Influence','A');mel.connect_material_property(bank,'',u.MaterialProperty.MP_BASE_COLOR)
        assert not mel.recompile_material(m);assert eal.save_loaded_asset(m);return m
    bank=custom(['P','UV','Bank','Base','Gravel'],'''
float inside=step(0,UV.x)*step(0,UV.y)*step(UV.x,1)*step(UV.y,1);
float distance=Bank.r*16;
float noise=.5+.5*sin(P.x*.0037+P.y*.0049)*cos(P.y*.0091);
float blend=(1-smoothstep(2.2,8.0+noise*4,distance))*inside;
float tone=clamp(dot(Gravel,float3(.2126,.7152,.0722))/.24,.64,1.34);
float3 dry=float3(.25,.244,.211)*tone;
float3 damp=float3(.105,.119,.101)*tone;
return lerp(Base,lerp(dry,damp,1-smoothstep(.1,2.1,distance)),blend*.96);
''')
    for a,pin in [(p,'P'),(uv,'UV'),(mask,'Bank'),(pigment,'Base'),(gravel,'Gravel')]:wire(a,bank,pin)
    mel.connect_material_property(bank,'',u.MaterialProperty.MP_BASE_COLOR)
    assert not mel.recompile_material(m);assert eal.save_loaded_asset(m);return m

def bank_material(banks):
    mel=u.MaterialEditingLibrary;eal=u.EditorAssetLibrary;assets=u.AssetToolsHelpers.get_asset_tools();name='M_Benmore_RiverBank'
    m=u.load_asset(DEST+'/'+name) or assets.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    for old in list(mel.get_material_expressions(m)):mel.delete_material_expression(m,old)
    assert not mel.get_material_expressions(m)
    m.set_editor_property('tangent_space_normal',False)
    def node(cls,**kw):
        n=mel.create_material_expression(m,cls)
        for k,v in kw.items():n.set_editor_property(k,v)
        return n
    def custom(names,code,typ=u.CustomMaterialOutputType.CMOT_FLOAT3):
        inputs=[]
        for name in names:
            pin=u.CustomInput();pin.set_editor_property('input_name',name);inputs.append(pin)
        return node(u.MaterialExpressionCustom,inputs=inputs,code=code,output_type=typ)
    def wire(a,b,pin,out=''):assert mel.connect_material_expressions(a,out,b,pin)
    p=node(u.MaterialExpressionWorldPosition);vn=node(u.MaterialExpressionVertexNormalWS)
    uv=custom(['P'],'return P.xy/1250;',u.CustomMaterialOutputType.CMOT_FLOAT2);wire(p,uv,'P')
    gravel=node(u.MaterialExpressionTextureSample,texture=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/ReferenceSurface/T_Benmore_LooseGravel'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR);wire(uv,gravel,'UVs')
    normal=node(u.MaterialExpressionTextureSample,texture=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/ReferenceSurface/T_Benmore_LooseGravelN'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL);wire(uv,normal,'UVs')
    buv=custom(['P'],'return (P.xy*.01-float2(-1570,-20)+.5)/float2(1331,686);',u.CustomMaterialOutputType.CMOT_FLOAT2);wire(p,buv,'P')
    mask=node(u.MaterialExpressionTextureSample,texture=banks,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR);wire(buv,mask,'UVs')
    art_texture=u.load_asset(DEST+'/T_Benmore_RiverBankArt')
    if art_texture:
        art=node(u.MaterialExpressionTextureSample,texture=art_texture,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR);wire(buv,art,'UVs')
        col=custom(['Gravel','Bank','Art'],BANK_PIGMENT+'return ground;');wire(art,col,'Art')
        n=custom(['N','Detail','Cover'],'return normalize(N+float3(Detail.xy*lerp(.52,.18,Cover),0));');wire(art,n,'Cover','R')
    else:
        col=custom(['Gravel','Bank'],'float t=clamp(dot(Gravel,float3(.2126,.7152,.0722))/.24,.64,1.34);return lerp(float3(.25,.244,.211),float3(.105,.119,.101),1-smoothstep(.1,2.1,Bank.r*16))*t;')
        n=custom(['N','Detail'],'return normalize(N+float3(Detail.xy*.52,0));')
    wire(gravel,col,'Gravel');wire(mask,col,'Bank');mel.connect_material_property(col,'',u.MaterialProperty.MP_BASE_COLOR)
    wire(vn,n,'N');wire(normal,n,'Detail');mel.connect_material_property(n,'',u.MaterialProperty.MP_NORMAL)
    for prop,value in [(u.MaterialProperty.MP_ROUGHNESS,.89),(u.MaterialProperty.MP_SPECULAR,.15)]:mel.connect_material_property(node(u.MaterialExpressionConstant,r=value),'',prop)
    assert not mel.recompile_material(m);assert eal.save_loaded_asset(m);return m

