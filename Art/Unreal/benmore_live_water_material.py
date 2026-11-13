"""Existing stream geometry, displaced by the bounded GTWaterField texture.
Outside the field this is exactly the existing baked material, with no second sheet.
"""
import unreal as u
from benmore_river_life_materials import Graph
mel=u.MaterialEditingLibrary;eal=u.EditorAssetLibrary
DEST='/Game/GrandTour/Demo/BenmoreRoads/Gaea/RiverScale'

REGION='''
float2 d=P.xy-FieldMin.xy;
float2 local=float2(dot(d,FieldAxisX.xy),dot(d,FieldAxisY.xy));
float2 edge=min(local-.5*FieldSize.xy/FieldTexels.xy,FieldSize.xy-.5*FieldSize.xy/FieldTexels.xy-local);
float weight=Active*smoothstep(0,350,min(edge.x,edge.y));
float2 uv=saturate(local/max(FieldSize.xy,1));
'''

def surface_response(m):
    # Water's grazing reflection must reveal the moving surface. The earlier budget material
    # used such low specular/high roughness that the bed overwhelmed the water at the ford.
    for n in mel.get_material_expressions(m):
        if not isinstance(n,u.MaterialExpressionCustom):continue
        names=[str(i.get_editor_property('input_name')) for i in n.get_editor_property('inputs')]
        code=n.get_editor_property('code')
        if names==['P','Camera'] and 'return lerp(.055,.018' in code:
            n.set_editor_property('code','return lerp(.255,.12,smoothstep(35,160,length(Camera-P)*.01));')
        if names==['P','Flow','Foam','Camera'] and 'Rough=lerp' in code:
            code=code.replace('lerp(.34,.48,riffle),.55','lerp(.14,.23,riffle),.34')
            code=code.replace('lerp(.045,.16,saturate(depth*.7))','lerp(.075,.20,saturate(depth*.7))')
            n.set_editor_property('code',code)
    assert not mel.recompile_material(m);assert eal.save_loaded_asset(m)
    return m

def make():
    path=DEST+'/M_RS_LiveStream'
    # Rebuild only this owned clone; originals and rollback map retain their assets.
    m=u.load_asset(path) or eal.duplicate_asset(DEST+'/M_RS_Stream',path)
    if any(str(n.get_editor_property('desc'))=='RiverLive' for n in mel.get_material_expressions(m)):return surface_response(m)
    g=Graph(m,'RiverLive');nodes=list(mel.get_material_expressions(m))
    p=g.node(u.MaterialExpressionWorldPosition)
    args=['P','FieldMin','FieldSize','FieldAxisX','FieldAxisY','FieldTexels','Active','Tex','Level']
    inputs={'P':p}
    for name,val in [('FieldMin',(0,0,0,0)),('FieldSize',(4800,2400,0,0)),('FieldAxisX',(1,0,0,0)),('FieldAxisY',(0,1,0,0)),('FieldTexels',(128,64,0,0))]:
        inputs[name]=g.node(u.MaterialExpressionVectorParameter,parameter_name=name,default_value=u.LinearColor(*val))
    inputs['Active']=g.node(u.MaterialExpressionScalarParameter,parameter_name='FieldActive',default_value=0)
    inputs['Level']=g.node(u.MaterialExpressionScalarParameter,parameter_name='FieldLevelCm',default_value=1585.3853)
    inputs['Tex']=g.node(u.MaterialExpressionTextureObjectParameter,parameter_name='FieldTex',texture=u.load_asset('/Engine/EngineResources/WhiteSquareTexture'))
    wpo=g.custom(args,REGION+'''
    [branch] if(weight<=0) return float3(0,0,0);
    float4 f=Texture2DSampleLevel(Tex,TexSampler,uv,0);
    return float3(0,0,(f.r+Level-P.z)*weight);
    ''')
    for name,n in inputs.items():g.wire(n,wpo,name)
    g.output(wpo,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    # The original normal/tint/foam expressions receive live depth and world current inside this window.
    flow=next(n for n in nodes if isinstance(n,u.MaterialExpressionTextureSample) and n.get_editor_property('texture') and n.get_editor_property('texture').get_name()=='T_RL_Flow')
    live=g.custom(args+['Baked'],REGION+'''
    [branch] if(weight<=0) return Baked;
    float4 f=Texture2DSampleLevel(Tex,TexSampler,uv,0);
    float2 v=(FieldAxisX.xy*f.b+FieldAxisY.xy*f.a)*.01;
    return lerp(Baked,float4(.5+v/4,f.g*.005,Baked.a),weight);
    ''',u.CustomMaterialOutputType.CMOT_FLOAT4)
    for name,n in inputs.items():g.wire(n,live,name)
    g.wire(flow,live,'Baked','RGBA')
    for n in nodes:
        if isinstance(n,u.MaterialExpressionCustom) and any(str(i.get_editor_property('input_name'))=='Flow' for i in n.get_editor_property('inputs')):g.wire(live,n,'Flow')
    old=mel.get_material_property_input_node(m,u.MaterialProperty.MP_NORMAL)
    normal=g.custom(args+['Detail','BaseNormal'],REGION+'''
    [branch] if(weight<=0) return Detail;
    float2 du=float2(1/FieldTexels.x,0),dv=float2(0,1/FieldTexels.y);
    float sx=(Texture2DSampleLevel(Tex,TexSampler,uv+du,0).r-Texture2DSampleLevel(Tex,TexSampler,uv-du,0).r)/(2*FieldSize.x/FieldTexels.x);
    float sy=(Texture2DSampleLevel(Tex,TexSampler,uv+dv,0).r-Texture2DSampleLevel(Tex,TexSampler,uv-dv,0).r)/(2*FieldSize.y/FieldTexels.y);
    float2 slope=FieldAxisX.xy*sx+FieldAxisY.xy*sy;
    return normalize(lerp(Detail,normalize(float3(-slope,1))+Detail-normalize(BaseNormal),weight));
    ''')
    for name,n in inputs.items():g.wire(n,normal,name)
    g.wire(old,normal,'Detail');g.wire(g.node(u.MaterialExpressionVertexNormalWS),normal,'BaseNormal');g.output(normal,u.MaterialProperty.MP_NORMAL)
    assert not mel.recompile_material(m);assert eal.save_loaded_asset(m)
    return surface_response(m)
