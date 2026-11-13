"""Review-owned flow, bed and timber materials. Shared production assets untouched."""
import unreal as u
import ast
from pathlib import Path
DEST='/Game/GrandTour/Demo/BenmoreRoads/Gaea/RiverLife'
mel=u.MaterialEditingLibrary;eal=u.EditorAssetLibrary

def props(o,**kw):
    for k,v in kw.items():o.set_editor_property(k,v)
    return o

class Graph:
    def __init__(self,m,tag='RiverLife'):self.m=m;self.tag=tag
    def node(self,cls,**kw):return props(mel.create_material_expression(self.m,cls),desc=self.tag,**kw)
    def custom(self,names,code,kind=u.CustomMaterialOutputType.CMOT_FLOAT3,outputs=()):
        return self.node(u.MaterialExpressionCustom,code=code,output_type=kind,inputs=[props(u.CustomInput(),input_name=n) for n in names],additional_outputs=[props(u.CustomOutput(),output_name=n,output_type=k) for n,k in outputs])
    def scalar(self,v):return self.node(u.MaterialExpressionConstant,r=v)
    def vector(self,v):return self.node(u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*v,1))
    def wire(self,a,b,name,out=''):assert mel.connect_material_expressions(a,out,b,name),(name,out)
    def output(self,a,prop,out=''):assert mel.connect_material_property(a,out,prop)
    def tex(self,t,uv,normal=False):
        n=self.node(u.MaterialExpressionTextureSample,texture=t,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
        self.wire(uv,n,'UVs');return n

def fresh(name):
    path=DEST+'/'+name;m=u.load_asset(path) or u.AssetToolsHelpers.get_asset_tools().create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    for n in list(mel.get_material_expressions(m)):mel.delete_material_expression(m,n)
    return m

NOISE='''
struct Field {
 float hash(float2 p){return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);}
 float n(float2 p){float2 i=floor(p),f=frac(p);f=f*f*(3-2*f);return lerp(lerp(hash(i),hash(i+float2(1,0)),f.x),lerp(hash(i+float2(0,1)),hash(i+1),f.x),f.y);}
 float h(float2 p){return n(p*2.8)+.48*n(float2(p.x*.83-p.y*.56,p.x*.56+p.y*.83)*7.1)+.16*n(p*17.3);}
};Field f;
'''

def water(flow,mask):
    m=fresh('M_RL_Stream')
    g=Graph(m)
    water=g.node(u.MaterialExpressionSingleLayerWaterMaterialOutput)
    props(m,shading_model=u.MaterialShadingModel.MSM_SINGLE_LAYER_WATER,blend_mode=u.BlendMode.BLEND_MASKED,opacity_mask_clip_value=.12,tangent_space_normal=False,two_sided=False)
    # Add the required water output before requesting any graph compilation.
    for pin,v in [('Scattering Coefficients',(.00025,.00060,.00045)),('Absorption Coefficients',(.003,.0015,.001)),('Color Scale Behind Water',(.95,.98,.96))]:
        names=mel.get_material_expression_input_names(water);clean=lambda s:''.join(c.lower() for c in s if c.isalnum());actual=next(n for n in names if clean(n)==clean(pin));g.wire(g.vector(v),water,actual)
    actual=next(n for n in mel.get_material_expression_input_names(water) if ''.join(c.lower() for c in n if c.isalnum())=='phaseg');g.wire(g.scalar(.08),water,actual)
    p=g.node(u.MaterialExpressionWorldPosition);cam=g.node(u.MaterialExpressionCameraPositionWS);tm=g.node(u.MaterialExpressionTime);vn=g.node(u.MaterialExpressionVertexNormalWS)
    uv=g.custom(['P'],'return (P.xy*.01-float2(-1480,-300)+.625)/float2(1261.25,1076.25);',u.CustomMaterialOutputType.CMOT_FLOAT2);g.wire(p,uv,'P')
    flowtex=g.tex(flow,uv);cover=g.tex(mask,uv)
    normal=g.custom(['P','Flow','Time','Camera','N'],NOISE+'''
float2 q=P.xy*.01,v=(Flow.rg-.5)*4;
float speed=length(v),depth=Flow.b*2;
float t0=frac(Time/5),t1=frac(Time/5+.5),blend=abs(t0*2-1);
float2 a=q-v*t0*5,b=q-v*t1*5;
float e=.032;
float2 ga=float2(f.h(a+float2(e,0))-f.h(a-float2(e,0)),f.h(a+float2(0,e))-f.h(a-float2(0,e)));
float2 gb=float2(f.h(b+float2(e,0))-f.h(b-float2(e,0)),f.h(b+float2(0,e))-f.h(b-float2(0,e)));
float riffle=saturate(speed*.7)*(1-smoothstep(.35,.9,depth));
float fade=1-smoothstep(25,150,length(Camera-P)*.01);
float2 broad=float2(f.n(q*.4+Time*float2(.014,.006))-.5,f.n(q*.36+8-Time*float2(.006,.013))-.5)*.013;
return normalize(float3(N.xy*.30+lerp(ga,gb,blend)*lerp(.07,.34,riffle)*fade+broad,1));
''')
    for a,pin in [(p,'P'),(flowtex,'Flow'),(tm,'Time'),(cam,'Camera'),(vn,'N')]:g.wire(a,normal,pin,'RGBA' if pin=='Flow' else '')
    g.output(normal,u.MaterialProperty.MP_NORMAL)
    foam=g.custom(['P','Flow','Time','Camera'],NOISE+'''
float2 q=P.xy*.01,v=(Flow.rg-.5)*4;
float t0=frac(Time/5),t1=frac(Time/5+.5),blend=abs(t0*2-1);
float2 a=q-v*t0*5,b=q-v*t1*5;
float streak=lerp(f.n(a*float2(3.7,1.2)),f.n(b*float2(3.7,1.2)),blend);
float detail=smoothstep(.55,.78,streak);
return Flow.a*detail*1.65*(1-smoothstep(120,400,length(Camera-P)*.01));
''',u.CustomMaterialOutputType.CMOT_FLOAT1)
    for a,pin in [(p,'P'),(flowtex,'Flow'),(tm,'Time'),(cam,'Camera')]:g.wire(a,foam,pin,'RGBA' if pin=='Flow' else '')
    surf=g.custom(['P','Flow','Foam','Camera'],'''
float speed=length((Flow.rg-.5)*4),depth=Flow.b*2;
float riffle=saturate(speed*.65)*(1-smoothstep(.45,1.1,depth));
float far=smoothstep(12,70,length(Camera-P)*.01);
Rough=lerp(lerp(.34,.48,riffle),.55,far*.7)+Foam*.10;
Opacity=lerp(.045,.16,saturate(depth*.7))+Foam*.65;
float3 clear=lerp(float3(.026,.037,.024),float3(.009,.028,.027),smoothstep(.12,.7,depth));
return lerp(clear,float3(.40,.43,.35),Foam);
''',outputs=[('Rough',u.CustomMaterialOutputType.CMOT_FLOAT1),('Opacity',u.CustomMaterialOutputType.CMOT_FLOAT1)])
    for a,pin in [(p,'P'),(flowtex,'Flow'),(foam,'Foam'),(cam,'Camera')]:g.wire(a,surf,pin,'RGBA' if pin=='Flow' else '')
    for prop,out in [(u.MaterialProperty.MP_BASE_COLOR,''),(u.MaterialProperty.MP_ROUGHNESS,'Rough'),(u.MaterialProperty.MP_OPACITY,'Opacity')]:g.output(surf,prop,out)
    spec=g.custom(['P','Camera'],'return lerp(.055,.018,smoothstep(35,160,length(Camera-P)*.01));',u.CustomMaterialOutputType.CMOT_FLOAT1);g.wire(p,spec,'P');g.wire(cam,spec,'Camera');g.output(spec,u.MaterialProperty.MP_SPECULAR);g.output(cover,u.MaterialProperty.MP_OPACITY_MASK,'G')
    assert not mel.recompile_material(m);assert eal.save_loaded_asset(m);return m

def ground(source,ecology,vegetation):
    path=DEST+'/M_RL_Terrain';m=u.load_asset(path) or eal.duplicate_asset(source.get_path_name().split('.')[0],path)
    # Rebuild only our colour/normal wrapper from the intact upstream pigment.
    for n in list(mel.get_material_expressions(m)):
        if str(n.get_editor_property('desc')) in ['GaeaBank','RiverLife','RiverLifeHole']:mel.delete_material_expression(m,n)
    nodes=list(mel.get_material_expressions(m));pigment=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and 'float3 straw=' in n.get_editor_property('code') and 'return P.z<48' in n.get_editor_property('code'))
    marked=next((n for n in nodes if str(n.get_editor_property('desc')).startswith('RL_SourceNormal|')),None)
    oldnormal=marked or mel.get_material_property_input_node(m,u.MaterialProperty.MP_NORMAL)
    oldout=str(marked.get_editor_property('desc')).split('|',1)[1] if marked else mel.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_NORMAL)
    if oldnormal:oldnormal.set_editor_property('desc','RL_SourceNormal|'+oldout)
    for n in nodes:
        if isinstance(n,(u.MaterialExpressionTextureSample,u.MaterialExpressionTextureObject)):
            t=n.get_editor_property('texture')
            if t and t.get_name() in ['T_Gaea_VegetationMask','T_RL_Vegetation']:n.set_editor_property('texture',vegetation)
    g=Graph(m);p=g.node(u.MaterialExpressionWorldPosition)
    uv=g.custom(['P'],'return ((P.xy*.01+1250)/2500*2016+.5)/2017;',u.CustomMaterialOutputType.CMOT_FLOAT2);g.wire(p,uv,'P');eco=g.tex(ecology,uv)
    detail=g.custom(['P'],'return P.xy/620;',u.CustomMaterialOutputType.CMOT_FLOAT2);g.wire(p,detail,'P')
    gc=g.node(u.MaterialExpressionTextureSample,texture=u.load_asset('/Game/GrandTour/ArtTests/GravelRoad/T_GR_LooseColor'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR);g.wire(detail,gc,'UVs')
    gn=g.tex(u.load_asset('/Game/GrandTour/ArtTests/GravelRoad/T_GR_LooseNormal'),detail,True)
    mc=g.node(u.MaterialExpressionTextureSample,texture=u.load_asset('/Game/GrandTour/ArtTests/MudStyle/T_MS_ClayColor'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR);g.wire(detail,mc,'UVs')
    mn=g.tex(u.load_asset('/Game/GrandTour/ArtTests/MudStyle/T_MS_ClayNormal'),detail,True)
    vn=g.node(u.MaterialExpressionVertexNormalWS)
    surface=g.custom(['P','Base','N','GN','MN','Gravel','Mud','Eco'],'''
float gt=clamp(dot(Gravel,float3(.2126,.7152,.0722))/.30,.65,1.38);
float mt=clamp(dot(Mud,float3(.2126,.7152,.0722))/.18,.65,1.30);
float3 mineral=float3(.205,.194,.156)*gt;
float3 silt=float3(.086,.069,.046)*mt;
float influence=max(Eco.r,Eco.g);
float3 col=lerp(Base,mineral,Eco.r*.93);col=lerp(col,silt,Eco.g*.80);
float2 detail=lerp(GN.xy*.65,MN.xy*.44,Eco.g);
Normal=normalize(N+float3(detail*influence,0));
Rough=lerp(.88,.69,Eco.g);
return col;
''',outputs=[('Normal',u.CustomMaterialOutputType.CMOT_FLOAT3),('Rough',u.CustomMaterialOutputType.CMOT_FLOAT1)])
    for a,pin in [(p,'P'),(pigment,'Base'),(gn,'GN'),(mn,'MN'),(gc,'Gravel'),(mc,'Mud'),(eco,'Eco')]:g.wire(a,surface,pin)
    g.wire(oldnormal or vn,surface,'N',oldout if oldnormal else '')
    g.output(surface,u.MaterialProperty.MP_BASE_COLOR);g.output(surface,u.MaterialProperty.MP_NORMAL,'Normal');g.output(surface,u.MaterialProperty.MP_ROUGHNESS,'Rough')
    assert not mel.recompile_material(m);assert eal.save_loaded_asset(m);return m

def timber():
    m=fresh('M_RL_WeatheredTimber');g=Graph(m);props(m,tangent_space_normal=False)
    p=g.node(u.MaterialExpressionTextureCoordinate);col=g.custom(['UV'],NOISE+'''
float grain=f.n(UV*float2(4,85));float broad=f.n(UV*float2(1.2,12));
float3 grey=lerp(float3(.11,.085,.061),float3(.235,.210,.168),broad);
return grey*lerp(.83,1.13,grain);
''');g.wire(p,col,'UV');g.output(col,u.MaterialProperty.MP_BASE_COLOR);g.output(g.scalar(.87),u.MaterialProperty.MP_ROUGHNESS);g.output(g.scalar(.12),u.MaterialProperty.MP_SPECULAR)
    assert not mel.recompile_material(m);assert eal.save_loaded_asset(m);return m

def lake(source,mask):
    path=DEST+'/M_RL_Lake';m=u.load_asset(path) or eal.duplicate_asset(source.get_path_name().split('.')[0],path)
    for node in mel.get_material_expressions(m):
        if not isinstance(node,u.MaterialExpressionCustom):continue
        code=node.get_editor_property('code')
        if 'float2 wa=' in code:
            node.set_editor_property('code',NOISE+'''float2 q=P.xy*.01-Time*float2(.08,.035);float e=.07;float2 grad=float2(f.h(q+float2(e,0))-f.h(q-float2(e,0)),f.h(q+float2(0,e))-f.h(q-float2(0,e)));return normalize(float3(grad*.045*(1-smoothstep(40,250,length(Camera-P)*.01)),1));''')
        if 'lerp(.14,.58,Foam)' in code:node.set_editor_property('code','return .38;')
    g=Graph(m);p=g.node(u.MaterialExpressionWorldPosition)
    original=next(n for n in mel.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('desc'))=='RiverLakeJunction')
    uv=g.custom(['P'],'return (P.xy*.01-float2(-1480,-300)+.625)/float2(1261.25,1076.25);',u.CustomMaterialOutputType.CMOT_FLOAT2);g.wire(p,uv,'P');sample=g.tex(mask,uv)
    cut=g.custom(['Old','Mask','UV'],'float inside=step(0,UV.x)*step(UV.x,1)*step(0,UV.y)*step(UV.y,1);return Old*(1-Mask.g*inside);',u.CustomMaterialOutputType.CMOT_FLOAT1)
    g.wire(original,cut,'Old');g.wire(sample,cut,'Mask');g.wire(uv,cut,'UV');g.output(cut,u.MaterialProperty.MP_OPACITY_MASK);g.output(g.scalar(.10),u.MaterialProperty.MP_SPECULAR)
    assert not mel.recompile_material(m);assert eal.save_loaded_asset(m);return m

def deformation(terrain):
    """The existing CPU mud field displaces the same bank material at crossings."""
    path=DEST+'/M_RL_DeformField';m=u.load_asset(path) or eal.duplicate_asset(terrain.get_path_name().split('.')[0],path)
    for n in list(mel.get_material_expressions(m)):
        if isinstance(n,u.MaterialExpressionLandscapeGrassOutput) or str(n.get_editor_property('desc'))=='RiverLifeField':mel.delete_material_expression(m,n)
    g=Graph(m,'RiverLifeField');p=g.node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS);vn=g.node(u.MaterialExpressionVertexNormalWS)
    root=Path(u.Paths.project_dir()).resolve();tree=ast.parse((root/'Art/Unreal/setup_m6_mud.py').read_text())
    constants={n.targets[0].id:ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ['WPO_HLSL','SURFACE_A']}
    tex=g.node(u.MaterialExpressionTextureObjectParameter,parameter_name='MudField',texture=u.load_asset('/Game/GrandTour/Terrain/RT_TrackPaint'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    args={name:g.node(u.MaterialExpressionVectorParameter,parameter_name=name,default_value=u.LinearColor(*value,1)) for name,value in [('PatchMin',(0,0,0)),('PatchSize',(100,100,0)),('PatchTexels',(8,8,0))]}
    names=['WorldPos','PatchMin','PatchSize','PatchTexels','Tex']
    displace=g.custom(names+['SlideScale'],constants['WPO_HLSL'])
    state=g.custom(names+['VertexNormal','Wetness'],constants['SURFACE_A'].split('// The ground this mesh')[0]+'return n;')
    for node in [displace,state]:
        g.wire(p,node,'WorldPos');g.wire(tex,node,'Tex')
        for name,src in args.items():g.wire(src,node,name)
    g.wire(g.scalar(0),displace,'SlideScale');g.wire(vn,state,'VertexNormal');g.wire(g.scalar(0),state,'Wetness');g.output(displace,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    marked=next((n for n in mel.get_material_expressions(m) if str(n.get_editor_property('desc')).startswith('RL_FieldOriginalNormal|')),None)
    old=marked or mel.get_material_property_input_node(m,u.MaterialProperty.MP_NORMAL);out=str(marked.get_editor_property('desc')).split('|',1)[1] if marked else mel.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_NORMAL)
    old.set_editor_property('desc','RL_FieldOriginalNormal|'+out)
    normal=g.custom(['Base','Field','Vertex'],'return normalize(Base+Field-Vertex);');g.wire(old,normal,'Base',out);g.wire(state,normal,'Field');g.wire(vn,normal,'Vertex');g.output(normal,u.MaterialProperty.MP_NORMAL)
    g.output(g.scalar(1),u.MaterialProperty.MP_OPACITY_MASK)
    assert not mel.recompile_material(m);assert eal.save_loaded_asset(m)
    # Preserve physical Landscape collision; this masks only its rendering below
    # the two live patch meshes, using the existing subsystem's four boxes.
    g=Graph(terrain,'RiverLifeHole');p=g.node(u.MaterialExpressionWorldPosition)
    hole=g.custom(['P','P0','P1','P2','P3'],'''float4 boxes[4]={P0,P1,P2,P3};float mask=1;[unroll]for(int i=0;i<4;i++){float4 b=boxes[i];if(b.z>b.x+25&&b.w>b.y+25&&P.x>=b.x+12.5&&P.x<=b.z-12.5&&P.y>=b.y+12.5&&P.y<=b.w-12.5)mask=0;}return mask;''',u.CustomMaterialOutputType.CMOT_FLOAT1)
    g.wire(p,hole,'P')
    for i in range(4):g.wire(g.node(u.MaterialExpressionCollectionParameter,collection=u.load_asset('/Game/GrandTour/Terrain/MPC_TrackPaint'),parameter_name='Patch'+str(i)),hole,'P'+str(i))
    props(terrain,blend_mode=u.BlendMode.BLEND_MASKED,opacity_mask_clip_value=.5);g.output(hole,u.MaterialProperty.MP_OPACITY_MASK)
    assert not mel.recompile_material(terrain);assert eal.save_loaded_asset(terrain)
    return m
