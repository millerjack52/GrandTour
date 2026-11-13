"""Study-owned coherent stone, wetness and optically shallow water materials."""
import unreal as u
from pathlib import Path
from benmore_river_life_materials import Graph,props,NOISE
DEST='/Game/GrandTour/ArtTests/MackenzieRiverStudy'
mel=u.MaterialEditingLibrary;assets=u.EditorAssetLibrary
ROOT=Path(u.Paths.project_dir()).resolve()

def fresh(name):
    m=u.load_asset(DEST+'/'+name) or u.AssetToolsHelpers.get_asset_tools().create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    for n in list(mel.get_material_expressions(m)):mel.delete_material_expression(m,n)
    return m,Graph(m,'MackenzieRiverStudy')

def save(m):
    mel.set_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
    errors=mel.recompile_material(m);assert not errors,list(errors)
    assert assets.save_loaded_asset(m);return m

def textures():
    result={}
    for key,suffix,ext,compression in [('Color','diff','jpg',u.TextureCompressionSettings.TC_DEFAULT),('Normal','nor_dx','jpg',u.TextureCompressionSettings.TC_NORMALMAP),('Height','disp','png',u.TextureCompressionSettings.TC_MASKS),('Rough','rough','jpg',u.TextureCompressionSettings.TC_MASKS),('AO','ao','jpg',u.TextureCompressionSettings.TC_MASKS)]:
        name='T_MRS_Pebble_'+key;t=u.load_asset(DEST+'/'+name)
        if not t:
            task=props(u.AssetImportTask(),filename=str(ROOT/'Art/Textures/MackenzieRiver'/('ganges_river_pebbles_'+suffix+'_2k.'+ext)),destination_path=DEST,destination_name=name,automated=True,save=True)
            u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);t=u.load_asset(DEST+'/'+name);assert t
        props(t,srgb=key=='Color',compression_settings=compression);assets.save_loaded_asset(t);result[key]=t
    return result

def ground(tex):
    m,g=fresh('M_MRS_Shingle');props(m,tangent_space_normal=False)
    n=g.custom(['P','N','View','Camera','Color','Normal','Height','Rough','AO'],NOISE+r'''
float2 base=P.xy/135.;float2 dx=ddx(base),dy=ddy(base);
float pocket=exp(-pow((P.x-640)/340,2)-pow((P.y+425)/150,2));
float high=smoothstep(62,105,P.z);
float fines=saturate(pocket*.94+high*.65);
float fade=(1-smoothstep(900,2000,distance(Camera,P)))*smoothstep(.10,.30,abs(View.z));
float2 ray=-View.xy/max(abs(View.z),.25)*3.0/135.*fade*(1-fines);
float2 uv=base;float t=0,prev=0,prevD=0;float steps=lerp(22,12,saturate(abs(View.z)));
float d=1-Texture2DSampleGrad(Height,HeightSampler,uv,dx,dy).r;
[loop]for(int i=0;i<24;i++){if(t>=d)break;prev=t;prevD=d;t+=1/steps;uv=base+ray*t;d=1-Texture2DSampleGrad(Height,HeightSampler,uv,dx,dy).r;}
float a=saturate((prevD-prev)/max((t-d)+(prevD-prev),.00001));uv=base+ray*lerp(prev,t,a);
float3 c=Texture2DSampleGrad(Color,ColorSampler,uv,dx,dy).rgb;
float3 sn=UnpackNormalMap(float4(Texture2DSampleGrad(Normal,NormalSampler,uv,dx,dy).xyz,1));
float r=Texture2DSampleGrad(Rough,RoughSampler,uv,dx,dy).r;
float ao=Texture2DSampleGrad(AO,AOSampler,uv,dx,dy).r;
// Once scan relief/POM is leaving view, blend offset scan samples on an
// warped triangular lattice. Each sample has its own rotation and offset;
// rotate normals back to world XY and preserve contrast through the blend.
struct TileRotation {
 float2 turn(float2 p,float2 cs){return float2(p.x*cs.x-p.y*cs.y,p.x*cs.y+p.y*cs.x);}
};TileRotation tiles;
float farBlend=smoothstep(1200,2800,distance(Camera,P));
[branch] if(farBlend>0){
    float2 q=float2(P.x/235.+P.y/407.,P.y/203.5);
    q+=float2(f.n(P.xy/510.+17),f.n(P.xy/510.+43))*.85;
    float2 cell=floor(q),b=frac(q);float3 w;float2 c0,c1,c2;
    if(b.x+b.y<1){w=float3(1-b.x-b.y,b.x,b.y);c0=cell;c1=cell+float2(1,0);c2=cell+float2(0,1);}
    else{w=float3(b.x+b.y-1,1-b.x,1-b.y);c0=cell+1;c1=cell+float2(0,1);c2=cell+float2(1,0);}
    w=w*w*w;w/=max(w.x+w.y+w.z,.00001);
    float3 angles=float3(f.hash(c0+71),f.hash(c1+71),f.hash(c2+71))*6.2831853;
    float2 r0=float2(cos(angles.x),sin(angles.x)),r1=float2(cos(angles.y),sin(angles.y)),r2=float2(cos(angles.z),sin(angles.z));
    float2 u0=tiles.turn(base,r0)+float2(f.hash(c0),f.hash(c0+37.2));
    float2 u1=tiles.turn(base,r1)+float2(f.hash(c1),f.hash(c1+37.2));
    float2 u2=tiles.turn(base,r2)+float2(f.hash(c2),f.hash(c2+37.2));
    float2 dx0=tiles.turn(dx,r0),dy0=tiles.turn(dy,r0),dx1=tiles.turn(dx,r1),dy1=tiles.turn(dy,r1),dx2=tiles.turn(dx,r2),dy2=tiles.turn(dy,r2);
    float3 tc=Texture2DSampleGrad(Color,ColorSampler,u0,dx0,dy0).rgb*w.x+Texture2DSampleGrad(Color,ColorSampler,u1,dx1,dy1).rgb*w.y+Texture2DSampleGrad(Color,ColorSampler,u2,dx2,dy2).rgb*w.z;
    float3 n0=UnpackNormalMap(float4(Texture2DSampleGrad(Normal,NormalSampler,u0,dx0,dy0).xyz,1));
    float3 n1=UnpackNormalMap(float4(Texture2DSampleGrad(Normal,NormalSampler,u1,dx1,dy1).xyz,1));
    float3 n2=UnpackNormalMap(float4(Texture2DSampleGrad(Normal,NormalSampler,u2,dx2,dy2).xyz,1));
    n0.xy=tiles.turn(n0.xy,r0*float2(1,-1));n1.xy=tiles.turn(n1.xy,r1*float2(1,-1));n2.xy=tiles.turn(n2.xy,r2*float2(1,-1));
    float3 tn=n0*w.x+n1*w.y+n2*w.z;
    float contrast=rsqrt(max(dot(w,w),.001));
    float3 mean=Texture2DSampleLevel(Color,ColorSampler,float2(.5,.5),12).rgb;
    tc=max(0,mean+(tc-mean)*contrast);tn.xy*=contrast;
    float tr=Texture2DSampleGrad(Rough,RoughSampler,u0,dx0,dy0).r*w.x+Texture2DSampleGrad(Rough,RoughSampler,u1,dx1,dy1).r*w.y+Texture2DSampleGrad(Rough,RoughSampler,u2,dx2,dy2).r*w.z;
    float ta=Texture2DSampleGrad(AO,AOSampler,u0,dx0,dy0).r*w.x+Texture2DSampleGrad(AO,AOSampler,u1,dx1,dy1).r*w.y+Texture2DSampleGrad(AO,AOSampler,u2,dx2,dy2).r*w.z;
    c=lerp(c,tc,farBlend);sn=normalize(lerp(sn,tn,farBlend));r=lerp(r,tr,farBlend);ao=lerp(ao,ta,farBlend);
}
float l=dot(c,float3(.2126,.7152,.0722));
c=lerp(l.xxx,c,.23)*float3(1.01,1.055,1.075);
// Broad sediment variation continues beyond the dressed close-up area.
c*=lerp(.89,1.10,f.n(P.xy/780.)*.65+f.n(P.xy/193.)*.35);
float noise=f.n(P.xy/31)+.4*f.n(P.xy/8);
float wet=1-smoothstep(1.5,17.,P.z+(noise-.7)*4.);
float3 silt=float3(.23,.209,.171)*(.80+.28*f.n(P.xy/5));
c=lerp(c,silt,fines)*lerp(1.06,.55,wet);
OutN=normalize(float3(N.xy+sn.xy*.90*(1-fines),N.z));
OutR=lerp(clamp(r*.65+.28,.68,.96),clamp(r*.40+.15,.26,.54),wet);
OutAO=lerp(.23,1.,ao);
return c;
''',outputs=[('OutN',u.CustomMaterialOutputType.CMOT_FLOAT3),('OutR',u.CustomMaterialOutputType.CMOT_FLOAT1),('OutAO',u.CustomMaterialOutputType.CMOT_FLOAT1)])
    for pin,cls in [('P',u.MaterialExpressionWorldPosition),('N',u.MaterialExpressionVertexNormalWS),('View',u.MaterialExpressionCameraVectorWS),('Camera',u.MaterialExpressionCameraPositionWS)]:g.wire(g.node(cls),n,pin)
    for key,t in tex.items():g.wire(g.node(u.MaterialExpressionTextureObject,texture=t,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR if key=='Color' else u.MaterialSamplerType.SAMPLERTYPE_NORMAL if key=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS),n,key)
    for prop,out in [(u.MaterialProperty.MP_BASE_COLOR,''),(u.MaterialProperty.MP_NORMAL,'OutN'),(u.MaterialProperty.MP_ROUGHNESS,'OutR'),(u.MaterialProperty.MP_AMBIENT_OCCLUSION,'OutAO')]:g.output(n,prop,out)
    g.output(g.scalar(.30),u.MaterialProperty.MP_SPECULAR)
    return save(m)

def cobble():
    m,g=fresh('M_MRS_Cobble');props(m,tangent_space_normal=False)
    n=g.custom(['P','N','Random'],NOISE+r'''
float3 grey=float3(.29,.309,.315),warm=float3(.32,.277,.209),dark=float3(.10,.117,.12);
float3 c=Random<.55?lerp(grey,warm,Random/.55):lerp(grey,dark,(Random-.55)/.45);
float mineral=f.n(P.xy*.32+P.z*.18);float fleck=pow(f.n(P.xy*2.7+P.z*.83),7);
c*=.69+.53*mineral;c+=fleck*.12;
float vein=1-smoothstep(.025,.09,abs(sin(P.x*.22+P.y*.36+P.z*.18+f.n(P.xy/6)*2)));
c=lerp(c,c*1.65,vein*.40*step(.72,Random));
float wet=1-smoothstep(1.8,14.,P.z+(f.n(P.xy/15)-.5)*4);
OutR=lerp(.83,.30+.15*mineral,wet);
float e=.18;float2 slope=float2(f.n(P.xy*.65+e)-f.n(P.xy*.65-e),f.n(P.yx*.65+e)-f.n(P.yx*.65-e));
OutN=normalize(N+float3(slope*.14,0));
return c*lerp(1.,.47,wet);
''',outputs=[('OutN',u.CustomMaterialOutputType.CMOT_FLOAT3),('OutR',u.CustomMaterialOutputType.CMOT_FLOAT1)])
    for pin,cls in [('P',u.MaterialExpressionWorldPosition),('N',u.MaterialExpressionVertexNormalWS),('Random',u.MaterialExpressionPerInstanceRandom)]:g.wire(g.node(cls),n,pin)
    for prop,out in [(u.MaterialProperty.MP_BASE_COLOR,''),(u.MaterialProperty.MP_NORMAL,'OutN'),(u.MaterialProperty.MP_ROUGHNESS,'OutR')]:g.output(n,prop,out)
    g.output(g.scalar(.3),u.MaterialProperty.MP_SPECULAR);return save(m)

def water():
    m,g=fresh('M_MRS_ClearWater')
    w=g.node(u.MaterialExpressionSingleLayerWaterMaterialOutput)
    props(m,shading_model=u.MaterialShadingModel.MSM_SINGLE_LAYER_WATER,blend_mode=u.BlendMode.BLEND_OPAQUE,tangent_space_normal=False)
    names=mel.get_material_expression_input_names(w);clean=lambda s:''.join(c.lower() for c in s if c.isalnum())
    for pin,v in [('Scattering Coefficients',(.00012,.00025,.00022)),('Absorption Coefficients',(.0018,.00075,.00048)),('Color Scale Behind Water',(1.,1.,1.))]:g.wire(g.vector(v),w,next(n for n in names if clean(n)==clean(pin)))
    g.wire(g.scalar(.12),w,next(n for n in names if clean(n)=='phaseg'))
    n=g.custom(['P','Time'],NOISE+r'''
float2 q=P.xy*.011-float2(Time*.10,Time*.012);
float e=.10;float2 grad=float2(f.h(q+float2(e,0))-f.h(q-float2(e,0)),f.h(q+float2(0,e))-f.h(q-float2(0,e)));
float phase=f.n(P.xy/170)*2.4;
float a=cos(P.x*.046+P.y*.012-Time*1.65+phase);
float b=cos(P.x*.012-P.y*.075-Time*1.2+phase*.4);
float2 broad=float2(a*.055+b*.010,a*.014-b*.040);
return normalize(float3(grad*float2(.045,.065)+broad,1));
''')
    g.wire(g.node(u.MaterialExpressionWorldPosition),n,'P');g.wire(g.node(u.MaterialExpressionTime),n,'Time');g.output(n,u.MaterialProperty.MP_NORMAL)
    for prop,v in [(u.MaterialProperty.MP_BASE_COLOR,(.006,.011,.013))]:g.output(g.vector(v),prop)
    for prop,v in [(u.MaterialProperty.MP_ROUGHNESS,.13),(u.MaterialProperty.MP_SPECULAR,.32),(u.MaterialProperty.MP_OPACITY,.018)]:g.output(g.scalar(v),prop)
    return save(m)

def simple(name,grass=False):
    m,g=fresh(name)
    if grass:props(m,two_sided=True,shading_model=u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
    n=g.custom(['P','V'],NOISE+('''
float n=f.n(P.xy/90);float blade=lerp(.65,1.1,V.r);
return lerp(float3(.10,.102,.049),float3(.32,.269,.143),n)*blade;
''' if grass else '''
float n=f.n(P.xy/370)+.35*f.n(P.xy/73);
return lerp(float3(.17,.159,.125),float3(.33,.288,.199),saturate(n));
'''))
    g.wire(g.node(u.MaterialExpressionWorldPosition),n,'P');g.wire(g.node(u.MaterialExpressionVertexColor),n,'V');g.output(n,u.MaterialProperty.MP_BASE_COLOR)
    if grass:g.output(n,u.MaterialProperty.MP_SUBSURFACE_COLOR)
    g.output(g.scalar(.9),u.MaterialProperty.MP_ROUGHNESS);g.output(g.scalar(.1),u.MaterialProperty.MP_SPECULAR)
    return save(m)

def build():return dict(bed=ground(textures()),stone=cobble(),water=water(),grass=simple('M_MRS_Tussock',True),hills=simple('M_MRS_Hills'))
