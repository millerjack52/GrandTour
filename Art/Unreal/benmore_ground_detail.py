"""Dry meadow detail for Benmore; preserves road masks and grass outputs."""
import unreal as u

DENSITIES={'LowGrass':350,'CrownTussock':70,'ShaggyTussock':55,'TallClumps':35,'DistantTussock':6}

def build(m):
    mel=u.MaterialEditingLibrary
    def props(o,**kw):
        for k,v in kw.items():o.set_editor_property(k,v)
        return o
    def expr(cls,**kw):
        return props(mel.create_material_expression(m,cls),desc='BenmoreGroundDetail',**kw)
    def wire(a,b,name,out=''):assert mel.connect_material_expressions(a,out,b,name)
    def custom(names,code,typ=u.CustomMaterialOutputType.CMOT_FLOAT3):
        return expr(u.MaterialExpressionCustom,inputs=[props(u.CustomInput(),input_name=n) for n in names],code=code,output_type=typ)
    nodes=list(mel.get_material_expressions(m))
    # These are the original road shader nodes, kept for their connected inputs.
    color=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and 'float3 gravel=' in n.get_editor_property('code'))
    normal=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and [str(x.get_editor_property('input_name')) for x in n.get_editor_property('inputs')][:2]==['Detail','Mask'])
    for n in nodes:
        if str(n.get_editor_property('desc'))=='BenmoreGroundDetail':mel.delete_material_expression(m,n)
    p=expr(u.MaterialExpressionWorldPosition)
    uv=custom(['P'],'return P.xy/480.0;',u.CustomMaterialOutputType.CMOT_FLOAT2);wire(p,uv,'P')
    fineuv=custom(['P'],'return float2(P.x*.8-P.y*.6,P.x*.6+P.y*.8)/160.0;',u.CustomMaterialOutputType.CMOT_FLOAT2);wire(p,fineuv,'P')
    src='/Game/ANGRY_MESH/StylizedPack_MeadowEnvironment/Textures/Landscape/'
    def sample(path,coords,normal=False):
        tex=u.load_asset(path);assert tex,path
        t=expr(u.MaterialExpressionTextureSample,texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        wire(coords,t,'UVs');return t
    dry=sample(src+'T_Landscape_DryGrass_01_A',uv)
    drynormal=sample(src+'T_Landscape_Grass_01_N',uv,True)
    blades=sample('/Game/GrandTour/Textures/Stylised/T_GT_Grass_D',fineuv)
    bladeNormal=sample('/Game/GrandTour/Textures/Stylised/T_GT_Grass_N',fineuv,True)
    slots=list(color.get_editor_property('inputs'))[:5]
    for name in ['Dry','Blades']:slots.append(props(u.CustomInput(),input_name=name))
    color.set_editor_property('inputs',slots)
    color.set_editor_property('code','''
struct FieldNoise { float noise(float2 v) { float2 i=floor(v),f=frac(v); f=f*f*(3-2*f);
float4 h=frac(sin(float4(dot(i,float2(127.1,311.7)),dot(i+float2(1,0),float2(127.1,311.7)),dot(i+float2(0,1),float2(127.1,311.7)),dot(i+1,float2(127.1,311.7))))*43758.5453);
return lerp(lerp(h.x,h.y,f.x),lerp(h.z,h.w,f.x),f.y); } }; FieldNoise field;
float broad=.65*field.noise(P.xy/3400)+.35*field.noise(P.xy/900);
float patch=field.noise(P.xy/360);
float steep=1-smoothstep(.66,.96,N.z);
float dryL=dot(Dry,float3(.2126,.7152,.0722));
float bladeL=dot(Blades,float3(.2126,.7152,.0722));
float dryDetail=clamp(1+(dryL-.255)*5.0,.55,1.65);
float bladeDetail=clamp(1+(bladeL-.13)*3.0,.65,1.4);
float3 grass=lerp(float3(.155,.132,.076),float3(.285,.243,.135),smoothstep(.2,.8,broad));
grass*=dryDetail*lerp(1,bladeDetail,.55)*lerp(.82,1.12,patch);
float3 soil=Loose*float3(.64,.58,.49);
grass=lerp(grass,soil,smoothstep(.65,.9,patch)*.32);
grass=lerp(grass,Loose*.78,steep*.78);
float3 gravel=lerp(Loose,Compact,.64)*.88;
float3 shoulder=lerp(grass,Loose*.83,Mask.g*.65);
float3 result=lerp(shoulder,gravel*(1-Mask.b*.10),Mask.r);
return P.z<48 ? float3(.035,.15,.19) : result;
''')
    wire(dry,color,'Dry','RGB');wire(blades,color,'Blades','RGB')
    # Replacing CustomInput arrays can discard Unreal's expression references.
    # Reconnect every input explicitly rather than relying on struct copies.
    samples={n.get_editor_property('texture').get_name():n for n in nodes if isinstance(n,u.MaterialExpressionTextureSample) and n.get_editor_property('texture')}
    n=expr(u.MaterialExpressionVertexNormalWS)
    roadmask=samples['T_Benmore_RoadMask']
    for source_node,name,out in [(p,'P',''),(n,'N',''),(roadmask,'Mask','RGB'),(samples['T_GR_CompactColor'],'Compact','RGB'),(samples['T_GR_LooseColor'],'Loose','RGB')]:wire(source_node,color,name,out)
    # Rotate the fine normal back from its rotated world-planar UV basis.
    slots=list(normal.get_editor_property('inputs'))[:2]
    for name in ['DryN','BladeN']:slots.append(props(u.CustomInput(),input_name=name))
    normal.set_editor_property('inputs',slots)
    normal.set_editor_property('code','''
float2 fine=float2(BladeN.x*.8+BladeN.y*.6,-BladeN.x*.6+BladeN.y*.8);
float3 meadow=normalize(float3(DryN.xy*.48+fine*.22,1));
float3 road=normalize(lerp(float3(0,0,1),Detail,.5));
return normalize(lerp(meadow,road,Mask));
''')
    wire(drynormal,normal,'DryN','RGB');wire(bladeNormal,normal,'BladeN','RGB')
    wire(samples['T_GR_CompactNormal'],normal,'Detail','RGB');wire(roadmask,normal,'Mask','R')
    assert mel.connect_material_property(color,'',u.MaterialProperty.MP_BASE_COLOR)
    assert mel.connect_material_property(normal,'',u.MaterialProperty.MP_NORMAL)
    report={'ground_texture':src+'T_Landscape_DryGrass_01_A','dry_tile_m':4.8,'fine_tile_m':1.6,'densities_per_100m2':DENSITIES}
    if u.EditorAssetLibrary.does_asset_exist('/Game/GrandTour/Demo/BenmoreRoads/ReferenceSurface/T_Benmore_RoadCoordinates'):
        from benmore_reference_surface import build as reference_surface
        report.update(reference_surface(m))
    return report


