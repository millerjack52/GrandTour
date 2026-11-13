"""Map-owned bank geology and macro shading shared with the DEM backdrop."""
import unreal as u
DEST='/Game/GrandTour/Demo/BenmoreRoads/Environment'
def import_landform():
    from pathlib import Path
    root=Path(u.Paths.project_dir()).resolve();task=u.AssetImportTask()
    for k,v in dict(filename=str(root/'Art/Export/BenmoreEnvironment/T_Benmore_Landform.png'),destination_path=DEST,destination_name='T_Benmore_Landform',automated=True,replace_existing=True,save=True).items():task.set_editor_property(k,v)
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);t=u.load_asset(DEST+'/T_Benmore_Landform');assert t
    for k,v in dict(srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP).items():t.set_editor_property(k,v)
    u.EditorAssetLibrary.save_loaded_asset(t)
NOISE='''struct TerrainNoise { float n(float2 p) { float2 i=floor(p),f=frac(p);f=f*f*(3-2*f);
float4 h=frac(sin(float4(dot(i,float2(127.1,311.7)),dot(i+float2(1,0),float2(127.1,311.7)),dot(i+float2(0,1),float2(127.1,311.7)),dot(i+1,float2(127.1,311.7))))*43758.5453);
return lerp(lerp(h.x,h.y,f.x),lerp(h.z,h.w,f.x),f.y); }};TerrainNoise f;
float dist=length(Camera-P);float detail=1-smoothstep(8000,35000,dist);
float macro=.65*f.n(P.xy/19000)+.35*f.n(P.xy/5700);
float broken=f.n(P.xy/520+P.z/1900);
float bank=smoothstep(.07,.28,1-N.z+(.5-broken)*.045);
float rock=smoothstep(.20,.43,1-N.z+(.5-broken)*.075);
float strataCoord=(P.z+P.x*.17+P.y*.09)/34+f.n(P.xy/180)*1.7;
float strata=f.n(float2((P.x*.62+P.y*.39)/130,strataCoord*.7));
float layer=smoothstep(.23,.75,strata);
float fade=smoothstep(3500,22000,dist);
'''
COLOR=NOISE+'''
float3 w=pow(abs(N),4);w/=max(w.x+w.y+w.z,.001);
float rockL=.42;
[branch] if(detail>.01 && bank>.02) {
float3 a=Texture2DSample(RockA,RockASampler,P.yz/340).rgb*w.x+Texture2DSample(RockA,RockASampler,P.xz/340).rgb*w.y+Texture2DSample(RockA,RockASampler,P.xy/340).rgb*w.z;
rockL=dot(a,float3(.2126,.7152,.0722)); }
float2 landUV=float2((P.x/100+11463)/13680,(4278-P.y/100)/12770);
float3 land=Texture2DSample(Landform,LandformSampler,landUV).rgb;
float gully=smoothstep(.48,.82,land.r);float ridge=1-smoothstep(.22,.48,land.r);
float exposure=saturate(.55*macro+.45*ridge);
float3 dirt=lerp(float3(.145,.132,.112),float3(.31,.277,.227),exposure);
dirt*=lerp(1,clamp(.75+rockL,.7,1.25),detail*.65);
float3 schist=lerp(float3(.16,.17,.168),float3(.24,.237,.211),.6*macro+.4*layer*detail);
schist*=lerp(1,clamp(.64+rockL,.7,1.24),detail);
float3 earth=lerp(dirt,schist,rock);
// Meso-scale cover survives past the mesh-grass cull distance.
float2 warp=float2(f.n(P.xy/4100),f.n(P.yx/3700+17))*1450;
float patchCover=.58*f.n((P.xy+warp)/8000)+.42*f.n((P.xy-warp*.3)/19000);
float cover=smoothstep(.34,.64,patchCover+gully*.12-ridge*.055);
float footprint=max(length(ddx(P.xy)),length(ddy(P.xy)));
float clumps=.5*lerp(.5,f.n(P.xy/145),1-smoothstep(55,160,footprint))
            +.3*lerp(.5,f.n(P.xy/430),1-smoothstep(160,500,footprint))
            +.2*lerp(.5,f.n(P.xy/1100),1-smoothstep(450,1300,footprint));
float tuft=smoothstep(.33,.68,clumps);
float3 dryCover=lerp(float3(.19,.145,.075),float3(.255,.195,.105),tuft);
float3 mineral=lerp(float3(.19,.17,.14),float3(.25,.232,.19),smoothstep(.25,.72,macro));
mineral*=lerp(.92,1.07,clumps);
float3 grassMacro=lerp(mineral,dryCover,cover);
float sheltered=smoothstep(.50,.80,land.r)*smoothstep(.33,.65,f.n(P.xy/9000));
grassMacro=lerp(grassMacro,float3(.13,.135,.078)*lerp(.90,1.10,tuft),sheltered*.45);
grassMacro*=lerp(.84,1.14,land.g);
// Aspect affects broad plant/soil colour, not baked directional lighting.
grassMacro*=.94+.10*saturate(N.y*.5+.5);
float3 meadow=lerp(Base,grassMacro,fade*.92);
float3 terrain=lerp(meadow,earth,bank);
terrain*=lerp(.90,1.09,macro);
// Geographic cover and fractured relief remain legible past the grass cull distance.
float4 hills=Texture2DSample(Hills,HillsSampler,landUV);
float4 ecology=Texture2DSample(CoverDetail,CoverDetailSampler,landUV);
float grain=.55*f.n(P.xy/4700)+.30*f.n(P.xy/13000)+.15*f.n(P.xy/1700);
float pixelFoot=max(length(ddx(P.xy)),length(ddy(P.xy)));
// Explicit footprint fades stop fine clump patterns sparkling in long views.
float small=lerp(.5,f.n(P.xy/230),1-smoothstep(100,330,pixelFoot));
float mid=lerp(.5,f.n(P.xy/850),1-smoothstep(400,1200,pixelFoot));
float coarse=f.n(P.xy/2700);
float coverGrain=smoothstep(.24,.76,small*.50+mid*.38+coarse*.12);
float3 dryGrass=lerp(float3(.22,.160,.069),float3(.295,.218,.091),coverGrain);
float3 drySoil=lerp(float3(.16,.139,.105),float3(.30,.263,.191),grain);
float3 upland=lerp(drySoil,dryGrass,.40+ecology.r*.60);
float3 scree=lerp(float3(.16,.166,.157),float3(.345,.326,.273),smoothstep(.24,.75,grain));
float fractured=smoothstep(.28,.66,ecology.g+(ecology.b-.5)*.18);
upland=lerp(upland,scree,fractured*.94);
// Concave, sheltered patches match the physical scrub islands in the basin.
float shrubPatch=ecology.a*(1-fractured)*smoothstep(.20,.66,mid*.5+coarse*.5);
upland=lerp(upland,float3(.061,.072,.036)*lerp(.85,1.2,coarse),shrubPatch*.75);
// Actual 5 m curvature gives small erosion ribs across the large terrain folds.
upland*=lerp(lerp(.86,1.12,ecology.b),lerp(.70,1.22,ecology.b),fractured)*lerp(.88,1.12,coverGrain);
terrain=lerp(terrain,upland,smoothstep(7000,26000,dist)*.94);
return P.z<48 ? float3(.035,.15,.19) : lerp(terrain,Base,saturate(Mask.r+Mask.g*.18));
'''
NORMAL=NOISE+'''
float3 w=pow(abs(N),4);w/=max(w.x+w.y+w.z,.001);
float3 perturb=0;
[branch] if(detail>.01 && bank>.02) {
float2 x=Texture2DSample(RockN,RockNSampler,P.yz/340).rg*2-1;
float2 y=Texture2DSample(RockN,RockNSampler,P.xz/340).rg*2-1;
float2 z=Texture2DSample(RockN,RockNSampler,P.xy/340).rg*2-1;
perturb=float3(0,x.x,x.y)*w.x+float3(y.x,0,y.y)*w.y+float3(z.x,z.y,0)*w.z;
perturb-=N*dot(perturb,N);
}
// Fine, broken ledges remain shading detail; terrain supplies the bank silhouette.
float ledge=(strata-.5)*.06*rock*detail;
float3 ledgeDir=float3(.17,.09,1);ledgeDir-=N*dot(ledgeDir,N);
float3 bankN=normalize(N+perturb*.65*detail+ledgeDir*ledge);
float3 nearNormal=normalize(lerp(BaseN,bankN,bank*(1-saturate(Mask.r+Mask.g*.3))));
// Add only the missing fine relief, keeping the playable landscape's own slope.
float2 uv=float2((P.x/100+11463)/13680,(4278-P.y/100)/12770);
float3 coarseN=normalize(Texture2DSample(HillNormal,HillNormalSampler,uv).rgb*2-1);
float3 fineN=normalize(Texture2DSample(FineNormal,FineNormalSampler,uv).rgb*2-1);
float amount=smoothstep(9000,30000,dist)*(1-saturate(Mask.r+Mask.g));
return normalize(nearNormal+(fineN-coarseN)*amount);
'''

def attach(m,base,normal,p,n,mask,expr,wire,custom):
    if not u.EditorAssetLibrary.does_asset_exist(DEST+'/T_Benmore_Landform'):import_landform()
    camera=expr(u.MaterialExpressionCameraPositionWS)
    rocka=expr(u.MaterialExpressionTextureObject,texture=u.load_asset('/Game/ANGRY_MESH/StylizedPack_MeadowEnvironment/Textures/Landscape/T_Landscape_Cliffs_01_A'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    rockn=expr(u.MaterialExpressionTextureObject,texture=u.load_asset('/Game/ANGRY_MESH/StylizedPack_MeadowEnvironment/Textures/Rocks/T_RockDetail_01_N'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    landform=expr(u.MaterialExpressionTextureObject,texture=u.load_asset(DEST+'/T_Benmore_Landform'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    hills=expr(u.MaterialExpressionTextureObject,texture=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Hills/T_Benmore_HillStructure'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    hillnormal=expr(u.MaterialExpressionTextureObject,texture=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Hills/T_Benmore_HillNormal'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    coverdetail=expr(u.MaterialExpressionTextureObject,texture=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/ReferenceVistas/T_Benmore_CoverStructure'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    finenormal=expr(u.MaterialExpressionTextureObject,texture=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/ReferenceVistas/T_Benmore_FineHillNormal'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    color=custom(['P','N','Camera','Base','Mask','RockA','Landform','Hills','CoverDetail'],COLOR)
    for name,node,out in [('P',p,''),('N',n,''),('Camera',camera,''),('Base',base,''),('Mask',mask,'RGB'),('RockA',rocka,''),('Landform',landform,''),('Hills',hills,''),('CoverDetail',coverdetail,'')]:wire(node,color,name,out)
    worldnormal=expr(u.MaterialExpressionTransform,transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_TANGENT,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD);wire(normal,worldnormal,'')
    mapped=custom(['P','N','Camera','BaseN','Mask','RockN','HillNormal','FineNormal'],NORMAL)
    for name,node,out in [('P',p,''),('N',n,''),('Camera',camera,''),('BaseN',worldnormal,''),('Mask',mask,'RGB'),('RockN',rockn,''),('HillNormal',hillnormal,''),('FineNormal',finenormal,'')]:wire(node,mapped,name,out)
    tangent=expr(u.MaterialExpressionTransform,transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_TANGENT);wire(mapped,tangent,'')
    return color,tangent

def backdrop_material():
    mel=u.MaterialEditingLibrary;eal=u.EditorAssetLibrary;path=DEST+'/M_Benmore_Backdrop'
    eal.make_directory(DEST);m=u.load_asset(path) if eal.does_asset_exist(path) else u.AssetToolsHelpers.get_asset_tools().create_asset('M_Benmore_Backdrop',DEST,u.Material,u.MaterialFactoryNew())
    mel.delete_all_material_expressions(m)
    def expr(cls,**kw):
        o=mel.create_material_expression(m,cls)
        for k,v in kw.items():o.set_editor_property(k,v)
        return o
    def custom(names,code):
        inputs=[]
        for name in names:
            item=u.CustomInput();item.set_editor_property('input_name',name);inputs.append(item)
        return expr(u.MaterialExpressionCustom,inputs=inputs,code=code,output_type=u.CustomMaterialOutputType.CMOT_FLOAT3)
    def wire(a,b,name,out=''):assert mel.connect_material_expressions(a,out,b,name)
    p=expr(u.MaterialExpressionWorldPosition);n=expr(u.MaterialExpressionVertexNormalWS);camera=expr(u.MaterialExpressionCameraPositionWS)
    rocka=expr(u.MaterialExpressionTextureObject,texture=u.load_asset('/Game/ANGRY_MESH/StylizedPack_MeadowEnvironment/Textures/Landscape/T_Landscape_Cliffs_01_A'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    base=expr(u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.225,.181,.11,1));mask=expr(u.MaterialExpressionConstant3Vector,constant=u.LinearColor(0,0,0,1));color=custom(['P','N','Camera','Base','Mask','RockA','Landform','Hills','CoverDetail'],COLOR)
    landform=expr(u.MaterialExpressionTextureObject,texture=u.load_asset(DEST+'/T_Benmore_Landform'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    hills=expr(u.MaterialExpressionTextureObject,texture=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Hills/T_Benmore_HillStructure'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    coverdetail=expr(u.MaterialExpressionTextureObject,texture=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/ReferenceVistas/T_Benmore_CoverStructure'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    for name,node in [('P',p),('N',n),('Camera',camera),('Base',base),('Mask',mask),('RockA',rocka),('Landform',landform),('Hills',hills),('CoverDetail',coverdetail)]:wire(node,color,name)
    mel.connect_material_property(color,'',u.MaterialProperty.MP_BASE_COLOR)
    # Unsmoothed 5 m DEM normals retain erosion detail on the scenery's 20 m mesh.
    m.set_editor_property('tangent_space_normal',False)
    normaltex=expr(u.MaterialExpressionTextureObject,texture=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/ReferenceVistas/T_Benmore_FineHillNormal'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    dn=custom(['P','HillNormal'],'float2 uv=float2((P.x/100+11463)/13680,(4278-P.y/100)/12770);return normalize(Texture2DSample(HillNormal,HillNormalSampler,uv).rgb*2-1);')
    wire(p,dn,'P');wire(normaltex,dn,'HillNormal');mel.connect_material_property(dn,'',u.MaterialProperty.MP_NORMAL)
    for prop,val in [(u.MaterialProperty.MP_ROUGHNESS,.94),(u.MaterialProperty.MP_SPECULAR,.1)]:mel.connect_material_property(expr(u.MaterialExpressionConstant,r=val),'',prop)
    mel.set_material_usage(m,u.MaterialUsage.MATUSAGE_NANITE)
    assert not mel.recompile_material(m);eal.save_loaded_asset(m);return m

