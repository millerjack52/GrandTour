"""Skip river-bank texture work outside its geographic mask, preserving colour."""
import unreal as u
from benmore_river_life_materials import Graph

def make_terrain():
    eal=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary
    path='/Game/GrandTour/Demo/BenmoreRoads/Gaea/RiverScale/M_RS_Terrain'
    m=u.load_asset(path) or eal.duplicate_asset('/Game/GrandTour/Demo/BenmoreRoads/Gaea/RiverLife/M_RL_Terrain',path)
    nodes=list(mel.get_material_expressions(m))
    n=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and 'float3 mineral=' in n.get_editor_property('code') and 'Eco' in [str(i.get_editor_property('input_name')) for i in n.get_editor_property('inputs')])
    if 'BANK_BUDGET_BRANCH' in n.get_editor_property('code'):return m
    g=Graph(m,'RiverBankBudget')
    for pin,asset,normal in [('Gravel','/Game/GrandTour/ArtTests/GravelRoad/T_GR_LooseColor',False),('GN','/Game/GrandTour/ArtTests/GravelRoad/T_GR_LooseNormal',True),('Mud','/Game/GrandTour/ArtTests/MudStyle/T_MS_ClayColor',False),('MN','/Game/GrandTour/ArtTests/MudStyle/T_MS_ClayNormal',True)]:
        texture=u.load_asset(asset);assert texture
        obj=g.node(u.MaterialExpressionTextureObject,texture=texture,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else u.MaterialSamplerType.SAMPLERTYPE_COLOR);g.wire(obj,n,pin)
    n.set_editor_property('code','''
// BANK_BUDGET_BRANCH: samples live inside the branch, not graph inputs.
float influence=max(Eco.r,Eco.g);
Normal=N;Rough=lerp(.88,.69,Eco.g);
float2 uv=P.xy/620;float2 ux=ddx(uv),uy=ddy(uv);
[branch] if(influence<.001) return Base;
float3 gravel=Texture2DSampleGrad(Gravel,GravelSampler,uv,ux,uy).rgb;
float3 mud=Texture2DSampleGrad(Mud,MudSampler,uv,ux,uy).rgb;
float2 gn=Texture2DSampleGrad(GN,GNSampler,uv,ux,uy).rg*2-1;
float2 mn=Texture2DSampleGrad(MN,MNSampler,uv,ux,uy).rg*2-1;
float gt=clamp(dot(gravel,float3(.2126,.7152,.0722))/.30,.65,1.38);
float mt=clamp(dot(mud,float3(.2126,.7152,.0722))/.18,.65,1.30);
float3 mineral=float3(.205,.194,.156)*gt;
float3 silt=float3(.086,.069,.046)*mt;
float3 col=lerp(Base,mineral,Eco.r*.93);col=lerp(col,silt,Eco.g*.80);
float2 detail=lerp(gn*.65,mn*.44,Eco.g);
Normal=normalize(N+float3(detail*influence,0));
return col;
''')
    assert not mel.recompile_material(m);assert eal.save_loaded_asset(m);return m
