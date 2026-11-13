"""Review-only river/ground materials; do not modify the production assets."""
import unreal as u
DEST='/Game/GrandTour/Demo/BenmoreRoads/Gaea'
UV='((P.xy*.01+1250)/2500*2016+.5)/2017'


def props(o,**kw):
    for k,v in kw.items():o.set_editor_property(k,v)
    return o


def water(flow,banks):
    import benmore_river_material as river
    prior=river.DEST
    try:
        river.DEST=DEST
        m=river.build(flow,banks,'M_Gaea_Creeks')
    finally:river.DEST=prior
    mel=u.MaterialEditingLibrary
    m.set_editor_property('opacity_mask_clip_value',.2)
    for n in mel.get_material_expressions(m):
        if not isinstance(n,u.MaterialExpressionCustom):continue
        code=n.get_editor_property('code')
        code=code.replace('(P.xy*.01-float2(-1570,-20)+.5)/float2(1331,686)',UV)
        code=code.replace('(Flow.rg-.5)*12','(Flow.rg-.5)*1.4')
        code=code.replace('step(-1570,q.x)*step(q.x,-240)*step(-20,q.y)*step(q.y,665)','step(-1250,q.x)*step(q.x,1250)*step(-1250,q.y)*step(q.y,1250)')
        code=code.replace('lerp(.025,.105','lerp(.010,.035')
        code=code.replace('lerp(.14,.58,Foam)','lerp(.32,.60,Foam)')
        code=code.replace('lerp(.09,.95,Foam)','lerp(.18,.95,Foam)')
        code=code.replace('normalize(N+float3(lerp(wa,wb,blend)*amplitude+broad,0))','normalize(float3(N.xy*.15+lerp(wa,wb,blend)*amplitude+broad,1))')
        n.set_editor_property('code',code)
    assert not mel.recompile_material(m);assert u.EditorAssetLibrary.save_loaded_asset(m)
    return m


def ground(source,banks,vegetation):
    eal=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary
    path=DEST+'/M_Gaea_Terrain'
    # Clone the present material, including its road POM and painterly treatment.
    m=u.load_asset(path) if eal.does_asset_exist(path) else eal.duplicate_asset(source.get_path_name().split('.')[0],path)
    nodes=list(mel.get_material_expressions(m))
    pigment=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and 'float3 straw=' in n.get_editor_property('code') and 'return P.z<48' in n.get_editor_property('code'))
    for n in nodes:
        if str(n.get_editor_property('desc')) in ['BenmoreRiverBank','GaeaBank']:
            mel.delete_material_expression(m,n);continue
        if isinstance(n,(u.MaterialExpressionTextureSample,u.MaterialExpressionTextureObject)):
            t=n.get_editor_property('texture')
            if t and t.get_name() in ['T_Benmore_VegetationMask','T_Gaea_VegetationMask']:n.set_editor_property('texture',vegetation)
    def expr(cls,**kw):return props(mel.create_material_expression(m,cls),desc='GaeaBank',**kw)
    def custom(names,code,typ=u.CustomMaterialOutputType.CMOT_FLOAT3):return expr(u.MaterialExpressionCustom,inputs=[props(u.CustomInput(),input_name=n) for n in names],code=code,output_type=typ)
    def wire(a,b,pin,out=''):assert mel.connect_material_expressions(a,out,b,pin)
    p=expr(u.MaterialExpressionWorldPosition)
    uv=custom(['P'],'return '+UV+';',u.CustomMaterialOutputType.CMOT_FLOAT2);wire(p,uv,'P')
    mask=expr(u.MaterialExpressionTextureSample,texture=banks,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR);wire(uv,mask,'UVs')
    guv=custom(['P'],'return P.xy/1250;',u.CustomMaterialOutputType.CMOT_FLOAT2);wire(p,guv,'P')
    gravel=expr(u.MaterialExpressionTextureSample,texture=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/ReferenceSurface/T_Benmore_LooseGravel'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR);wire(guv,gravel,'UVs')
    color=custom(['P','Bank','Base','Gravel'],'''
float2 q=P.xy*.01;
float inside=step(-1250,q.x)*step(q.x,1250)*step(-1250,q.y)*step(q.y,1250);
float d=Bank.r*16;
float patch=.5+.5*sin(q.x*.037+q.y*.029)*cos(q.y*.067-q.x*.009);
float tone=clamp(dot(Gravel,float3(.2126,.7152,.0722))/.24,.72,1.24);
float3 gravel=lerp(float3(.18,.182,.163),float3(.26,.227,.169),patch)*tone;
float3 damp=gravel*float3(.46,.57,.55);
float bank=(1-smoothstep(1.0,4.0+patch*3,d))*inside;
float3 dry=lerp(Base,Base*float3(.95,.97,1.04),Bank.b*inside*.18);
return lerp(dry,lerp(damp,gravel,smoothstep(.2,2.8,d)),bank*.88);
''')
    for a,pin in [(p,'P'),(mask,'Bank'),(pigment,'Base'),(gravel,'Gravel')]:wire(a,color,pin)
    mel.connect_material_property(color,'',u.MaterialProperty.MP_BASE_COLOR)
    assert not mel.recompile_material(m);assert eal.save_loaded_asset(m)
    return m


def lake(source):
    """Retain lake optics/mouth coverage but remove the retired river cutout."""
    eal=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;path=DEST+'/M_Gaea_Lake'
    m=u.load_asset(path) if eal.does_asset_exist(path) else eal.duplicate_asset(source.get_path_name().split('.')[0],path)
    changed=0
    for n in mel.get_material_expressions(m):
        if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('desc'))=='RiverLakeJunction':
            code=n.get_editor_property('code')
            if 'return lake*' in code:
                n.set_editor_property('code',code[:code.index('return lake*')]+'return lake;');changed+=1
    assert changed or any(isinstance(n,u.MaterialExpressionCustom) and 'return lake;' in n.get_editor_property('code') for n in mel.get_material_expressions(m))
    assert not mel.recompile_material(m);assert eal.save_loaded_asset(m)
    return m
