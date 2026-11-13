"""Reference-led gravel grading and restrained high-country ground palette."""
import unreal as u
DEST='/Game/GrandTour/Demo/BenmoreRoads/ReferenceSurface'
TRACKS='''float lateral=(Coords.r-.5)*32;
float halfWidth=Coords.g*8;
float wander=.14*sin(P.x*.00071+P.y*.00113)+.10*sin(P.y*.0031)+.045*sin(P.x*.014+P.y*.009);
float lane=lerp(1.05,.88,Mask.b);
float track=1-smoothstep(.18,.50,abs(abs(lateral-wander)-lane));
float centre=1-smoothstep(.12,.62,abs(lateral));
float edge=smoothstep(halfWidth-1.1,halfWidth-.15,abs(lateral));
float loose=clamp(.50+.24*centre+.38*edge-.34*track,.22,1);'''
def build(m):
    mel=u.MaterialEditingLibrary
    def props(o,**kw):
        for k,v in kw.items():o.set_editor_property(k,v)
        return o
    nodes=list(mel.get_material_expressions(m))
    for n in nodes:
        if str(n.get_editor_property('desc'))=='BenmoreReferenceSurface':mel.delete_material_expression(m,n)
    nodes=list(mel.get_material_expressions(m))
    def expr(cls,**kw):return props(mel.create_material_expression(m,cls),desc='BenmoreReferenceSurface',**kw)
    def wire(a,b,name,out=''):assert mel.connect_material_expressions(a,out,b,name)
    def custom(names,code,typ=u.CustomMaterialOutputType.CMOT_FLOAT3):return expr(u.MaterialExpressionCustom,inputs=[props(u.CustomInput(),input_name=n) for n in names],code=code,output_type=typ)
    def sample(name,uv,normal=False):
        tex=u.load_asset(DEST+'/'+name);assert tex,name
        node=expr(u.MaterialExpressionTextureSample,texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else (u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR if 'Coordinates' in name else u.MaterialSamplerType.SAMPLERTYPE_COLOR));wire(uv,node,'UVs');return node
    old={n.get_editor_property('texture').get_name():n for n in nodes if isinstance(n,u.MaterialExpressionTextureSample) and n.get_editor_property('texture')}
    color=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and 'float3 gravel=' in n.get_editor_property('code'))
    normal=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and [str(x.get_editor_property('input_name')) for x in n.get_editor_property('inputs')][:2]==['Detail','Mask'])
    p=expr(u.MaterialExpressionWorldPosition);n=expr(u.MaterialExpressionVertexNormalWS)
    uv=custom(['P'],'return P.xy/400;',u.CustomMaterialOutputType.CMOT_FLOAT2);wire(p,uv,'P')
    mapuv=custom(['P'],'return ((P.xy+125000)/250000*2016+.5)/2017;',u.CustomMaterialOutputType.CMOT_FLOAT2);wire(p,mapuv,'P')
    coords=sample('T_Benmore_RoadCoordinates',mapuv)
    from benmore_gravel_pom import attach
    base_uv=uv
    uv,pom_report=attach(m,uv,p,n,old['T_Benmore_RoadMask'],coords,expr,wire,custom,TRACKS)
    # A larger repeat enlarges only the loose stones; packed tracks stay fine.
    coarse_uv=custom(['UV'],'return UV*.32;',u.CustomMaterialOutputType.CMOT_FLOAT2);wire(uv,coarse_uv,'UV')
    compact=sample('T_Benmore_FineGravel',uv);loose=sample('T_Benmore_LooseGravel',coarse_uv)
    compactN=sample('T_Benmore_FineGravelN',uv,True);looseN=sample('T_Benmore_LooseGravelN',coarse_uv,True)
    if pom_report['gravel_pom']:
        dx=expr(u.MaterialExpressionDDX);dy=expr(u.MaterialExpressionDDY)
        wire(base_uv,dx,'Value');wire(base_uv,dy,'Value')
        coarse_dx=custom(['D'],'return D*.32;',u.CustomMaterialOutputType.CMOT_FLOAT2);wire(dx,coarse_dx,'D')
        coarse_dy=custom(['D'],'return D*.32;',u.CustomMaterialOutputType.CMOT_FLOAT2);wire(dy,coarse_dy,'D')
        for node in [compact,compactN]:
            node.set_editor_property('mip_value_mode',u.TextureMipValueMode.TMVM_DERIVATIVE)
            wire(dx,node,'DDX(UVs)');wire(dy,node,'DDY(UVs)')
        for node in [loose,looseN]:
            node.set_editor_property('mip_value_mode',u.TextureMipValueMode.TMVM_DERIVATIVE)
            wire(coarse_dx,node,'DDX(UVs)');wire(coarse_dy,node,'DDY(UVs)')
    names=['P','N','Mask','Compact','Loose','Dry','Blades','Coords']
    color.set_editor_property('inputs',[props(u.CustomInput(),input_name=name) for name in names])
    code='''struct FieldNoise { float noise(float2 v) { float2 i=floor(v),f=frac(v); f=f*f*(3-2*f);
float4 h=frac(sin(float4(dot(i,float2(127.1,311.7)),dot(i+float2(1,0),float2(127.1,311.7)),dot(i+float2(0,1),float2(127.1,311.7)),dot(i+1,float2(127.1,311.7))))*43758.5453);
return lerp(lerp(h.x,h.y,f.x),lerp(h.z,h.w,f.x),f.y); } }; FieldNoise field;
float broad=.65*field.noise(P.xy/3400)+.35*field.noise(P.xy/900);
float patch=field.noise(P.xy/360);
float steep=1-smoothstep(.68,.965,N.z);
float dryL=dot(Dry,float3(.2126,.7152,.0722));
float bladeL=dot(Blades,float3(.2126,.7152,.0722));
float fineL=dot(Compact,float3(.2126,.7152,.0722));
float coarseL=dot(Loose,float3(.2126,.7152,.0722));
float3 grass=lerp(float3(.17,.137,.082),float3(.29,.233,.139),smoothstep(.2,.8,broad));
grass*=clamp(1+(dryL-.255)*4.5,.6,1.55)*lerp(1,clamp(1+(bladeL-.13)*3,.65,1.4),.45)*lerp(.87,1.1,patch);
float hills=saturate(smoothstep(1200,10000,P.z)*.55+steep*.72);
float3 scree=lerp(float3(.115,.108,.094),float3(.205,.19,.164),broad)*( .82+.55*coarseL);
grass=lerp(grass,scree,hills);
'''+TRACKS+'''
float3 packed=float3(1,.98,.92)*clamp(.25+(fineL-.20)*.75,.13,.46);
float3 aggregate=float3(1,.985,.94)*clamp(.29+(coarseL-.4)*1.25,.075,.62);
float3 gravel=lerp(packed*.8,aggregate*.72,loose);
gravel*=1-.075*track+.035*centre;
float3 shoulder=lerp(grass,aggregate,Mask.g*.78);
// Dry exposed soil and broken gravel spill between the running surface and grass.
float beyond=abs(lateral)-halfWidth;
float vergePatch=field.noise(P.xy/210);
float spillWidth=lerp(.4,1.65,vergePatch);
float verge=smoothstep(-.65,.12,beyond)*(1-smoothstep(1.4,3.1,beyond))*saturate(Mask.g*4);
float spill=(1-smoothstep(.05,spillWidth,beyond))*lerp(.32,.82,field.noise(P.xy/64));
float3 drySoil=lerp(float3(.105,.088,.063),float3(.19,.16,.116),vergePatch)*( .78+fineL*.85);
float3 vergeSurface=lerp(drySoil,aggregate*.69,spill);
vergeSurface=lerp(vergeSurface,grass,smoothstep(.45,.82,field.noise(P.xy/115))*.62);
shoulder=lerp(shoulder,vergeSurface,verge*.88);
float ragged=saturate(Mask.r+((field.noise(P.xy/45)-.5)*.25+(vergePatch-.5)*.22)*Mask.r*(1-Mask.r)*4);
float3 result=lerp(shoulder,gravel,ragged);
return P.z<48 ? float3(.035,.15,.19) : result;'''
    color.set_editor_property('code',code)
    inputs=[(p,''),(n,''),(old['T_Benmore_RoadMask'],'RGB'),(compact,'RGB'),(loose,'RGB'),(old['T_Landscape_DryGrass_01_A'],'RGB'),(old['T_GT_Grass_D'],'RGB'),(coords,'RGB')]
    for name,(node,out) in zip(names,inputs):wire(node,color,name,out)
    names=['Detail','Mask','DryN','BladeN','CoarseN','Coords','P']
    normal.set_editor_property('inputs',[props(u.CustomInput(),input_name=name) for name in names])
    normal.set_editor_property('code',TRACKS+'''
float2 fine=float2(BladeN.x*.8+BladeN.y*.6,-BladeN.x*.6+BladeN.y*.8);
float3 meadow=normalize(float3(DryN.xy*.4+fine*.18,1));
float3 roadN=normalize(lerp(float3(Detail.xy*.55,Detail.z),float3(CoarseN.xy*.9,CoarseN.z),loose));
float beyond=abs(lateral)-halfWidth;
float shoulder=smoothstep(-.5,.1,beyond)*(1-smoothstep(.7,2.2,beyond))*saturate(Mask.g*3);
return normalize(lerp(meadow,roadN,saturate(Mask.r+shoulder*.65)));''')
    for name,(node,out) in zip(names,[(compactN,'RGB'),(old['T_Benmore_RoadMask'],'RGB'),(old['T_Landscape_Grass_01_N'],'RGB'),(old['T_GT_Grass_N'],'RGB'),(looseN,'RGB'),(coords,'RGB'),(p,'')]):wire(node,normal,name,out)
    from benmore_bank_surface import attach as banks
    color,normal=banks(m,color,normal,p,n,old['T_Benmore_RoadMask'],expr,wire,custom)
    mel.connect_material_property(color,'',u.MaterialProperty.MP_BASE_COLOR);mel.connect_material_property(normal,'',u.MaterialProperty.MP_NORMAL)
    return {'reference_surface':True,'gravel_repeat_m':{'compact':4,'loose':12.5},'wheel_paths':'road-relative, compacted','hill_palette':'muted grey-brown scree','terrain_heights_changed':False,**pom_report}
