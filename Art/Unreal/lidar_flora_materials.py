"""Map-local detail wrapper. Native soil/WPO/water and approved palette are preserved."""
import unreal as u,re
from benmore_river_life_materials import Graph,props,NOISE
import lidar_logging_trial as T
DEST='/Game/GrandTour/ArtTests/LidarStudy/FloraIntegration'
M=u.MaterialEditingLibrary;E=u.EditorAssetLibrary

def clone_material(source,cache):
    key=source.get_path_name()
    if key in cache:return cache[key]
    # Use the already-reviewed demo coverage/wind fix when one exists.
    demo=u.load_asset('/Game/GrandTour/ArtTests/FloraDrive/Foliage/'+source.get_name()) or source
    path=DEST+'/Foliage/'+source.get_name()
    local=u.load_asset(path) or E.duplicate_asset(demo.get_path_name().split('.')[0],path)
    assert local;cache[key]=local
    if isinstance(local,u.MaterialInstanceConstant):M.set_material_instance_parent(local,clone_material(demo.get_editor_property('parent'),cache))
    E.save_loaded_asset(local);return local

def ground(source,role,route,cfg):
    path=DEST+'/M_Flora'+role;m=u.load_asset(path)
    if not m:
        m=E.duplicate_asset(source.get_path_name().split('.')[0],path);assert m
        g=Graph(m,'LidarFloraDetail')
        original={pin:(M.get_material_property_input_node(m,prop),str(M.get_material_property_input_node_output_name(m,prop))) for pin,prop in [('Base',u.MaterialProperty.MP_BASE_COLOR),('N',u.MaterialProperty.MP_NORMAL),('Rough',u.MaterialProperty.MP_ROUGHNESS)]}
        assert all(n for n,p in original.values())
        wp=g.node(u.MaterialExpressionWorldPosition);cam=g.node(u.MaterialExpressionCameraPositionWS);view=g.node(u.MaterialExpressionCameraVectorWS)
        inputs=[('P',wp,''),('Camera',cam,''),('V',view,'')]+[(k,n,p) for k,(n,p) in original.items()]
        for key,value in cfg['ground'].items():
            inputs.append((key,g.node(u.MaterialExpressionScalarParameter,parameter_name=key,default_value=value),''))
        for i in [1,2,3]:
            for prefix,suffix,typ in [('C','',u.MaterialSamplerType.SAMPLERTYPE_COLOR),('T','N',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)]:
                t=u.load_asset('/Game/GrandTour/ArtTests/FloraDrive/T_ForestGround_%02d%s'%(i,suffix));assert t
                inputs.append((prefix+str(i),g.node(u.MaterialExpressionTextureObject,texture=t,sampler_type=typ),''))
        ht=u.load_asset('/Game/GrandTour/ArtTests/FloraDrive/T_ForestHeightRGB');assert ht
        inputs.append(('HeightTex',g.node(u.MaterialExpressionTextureObject,texture=ht,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR),''))
        stations=list(range(int(cfg['start_m']),int(cfg['end_m'])+1,10));pts=[T.at(route,s) for s in stations]
        segments='float distanceRoad=1e12;\n'
        for a,b in zip(pts,pts[1:]):
            segments+='{{float2 a=float2({:.5f},{:.5f}),b=float2({:.5f},{:.5f});float2 ab=b-a;float t=saturate(dot(P.xy-a,ab)/dot(ab,ab));distanceRoad=min(distanceRoad,length(P.xy-(a+ab*t)));}}\n'.format(a[0],a[1],b[0],b[1])
        code=NOISE+'''
DetailNormal=N;DetailRoughness=Rough;
float range=length(Camera-P);
float2 uv=float2(P.x,-P.y)/max(GroundTileCm,20.);
float2 dx=ddx(uv),dy=ddy(uv);
'''+segments+'''
float cover=1-smoothstep(DetailWidthCm-350,DetailWidthCm,distanceRoad);
[branch] if(cover<.001 || range>6500.)return Base;
float shoulder=smoothstep(280,560,distanceRoad);
float moss=smoothstep(.47,.68,f.n(P.xy/410)+.14*f.n(P.xy/95))*shoulder;
float litter=smoothstep(.44,.64,f.n(P.xy/290+31))*shoulder*(1-moss*.85);
float3 weights=float3(moss*(1-litter),litter,(1-moss)*(1-litter));
float facing=dot(normalize(N),normalize(V));
float strength=POMEnabled*cover*(1-smoothstep(POMNearCm,POMFarCm,range))*smoothstep(.07,.2,facing);
[branch] if(strength>.001){
 float depth=ReliefDepthCm*dot(weights,float3(1.,.6,.55));
 float2 ray=float2(-V.x,V.y)*depth*strength*max(N.z,.1)/max(facing,.09)/max(GroundTileCm,20.);
 int steps=(int)lerp(24.,10.,saturate(facing));float t=0,prev=0,prevDiff=0;
 [loop] for(int i=0;i<=24;i++){
  float2 at=uv+ray*t;float h=dot(Texture2DSampleGrad(HeightTex,HeightTexSampler,at,dx,dy).rgb,weights);float diff=t-(1-h);
  if(diff>=0 || i==steps){uv+=ray*lerp(prev,t,saturate(-prevDiff/max(diff-prevDiff,.00001)));break;}
  prev=t;prevDiff=diff;t+=1./steps;
 }
}
float3 c=Texture2DSampleGrad(C1,C1Sampler,uv,dx,dy).rgb*weights.x+Texture2DSampleGrad(C2,C2Sampler,uv,dx,dy).rgb*weights.y+Texture2DSampleGrad(C3,C3Sampler,uv,dx,dy).rgb*weights.z;
// Normal texture objects return packed BC5 XY; rebuild Z explicitly.
float2 xy=(Texture2DSampleGrad(T1,T1Sampler,uv,dx,dy).rg*weights.x+Texture2DSampleGrad(T2,T2Sampler,uv,dx,dy).rg*weights.y+Texture2DSampleGrad(T3,T3Sampler,uv,dx,dy).rg*weights.z)*2-1;
float fade=cover*(1-smoothstep(1800.,6500.,range));
float3 n=normalize(N);float3 tx=normalize(float3(n.z,0,-n.x));float3 ty=normalize(cross(n,tx));
DetailNormal=normalize(n+(tx*xy.x-ty*xy.y)*GroundNormalStrength*fade);
float grain=clamp(dot(c,float3(.2126,.7152,.0722))/.18,.55,1.45);
// Retain the real mud's wetness and map pigment; only modulate local grain.
return Base*lerp(1.,grain,GrainStrength*fade);
'''
        detail=g.custom([k for k,n,p in inputs],code,outputs=[('DetailNormal',u.CustomMaterialOutputType.CMOT_FLOAT3),('DetailRoughness',u.CustomMaterialOutputType.CMOT_FLOAT1)])
        for k,n,p in inputs:g.wire(n,detail,k,p)
        g.output(detail,u.MaterialProperty.MP_BASE_COLOR);g.output(detail,u.MaterialProperty.MP_NORMAL,'DetailNormal');g.output(detail,u.MaterialProperty.MP_ROUGHNESS,'DetailRoughness')
    for n in M.get_material_expressions(m):
        if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('desc'))=='LidarFloraDetail':
            code=str(n.get_editor_property('code'))
            # LiDAR's native mud graph is already sampler-heavy. Seven new
            # textures share the engine wrap sampler instead of adding seven.
            for name in ['C1','C2','C3','T1','T2','T3','HeightTex']:
                code=code.replace('Texture2DSampleGrad('+name+','+name+'Sampler,','Texture2DSampleGrad('+name+',GetMaterialSharedSampler('+name+'Sampler,Material.Wrap_WorldGroupSettings),')
            # Regenerate the bounded road mask when the profile's extent changes.
            pts=[T.at(route,s) for s in range(int(cfg['start_m']),int(cfg['end_m'])+1,10)]
            segments='float distanceRoad=1e12;\n'
            for a,b in zip(pts,pts[1:]):
                segments+='{{float2 a=float2({:.5f},{:.5f}),b=float2({:.5f},{:.5f});float2 ab=b-a;float t=saturate(dot(P.xy-a,ab)/dot(ab,ab));distanceRoad=min(distanceRoad,length(P.xy-(a+ab*t)));}}\n'.format(a[0],a[1],b[0],b[1])
            code=re.sub(r'float distanceRoad=1e12;.*?(?=float cover=)',segments,code,flags=re.S)
            n.set_editor_property('code',code)
        if isinstance(n,u.MaterialExpressionScalarParameter):
            key=str(n.get_editor_property('parameter_name'))
            if key in cfg['ground']:n.set_editor_property('default_value',cfg['ground'][key])
    # Exact native displacement / coverage graph is never replaced by the detail wrapper.
    for prop in [u.MaterialProperty.MP_WORLD_POSITION_OFFSET,u.MaterialProperty.MP_OPACITY_MASK]:
        a=M.get_material_property_input_node(source,prop);b=M.get_material_property_input_node(m,prop)
        assert (a.get_name() if a else None)==(b.get_name() if b else None)
    M.recompile_material(m);E.save_loaded_asset(m);return m

def grass_exclusion(source,route,cfg,cache):
    """Hide legacy streamed blades only where the new, authored ground cover lives.
    Keep all native contact/WPO bindings and the rest of the map's grass intact.
    """
    if not source:return None
    key=source.get_path_name()
    if key in cache:return cache[key]
    path=DEST+'/Grass/'+source.get_name();local=u.load_asset(path) or E.duplicate_asset(key.split('.')[0],path);assert local;cache[key]=local
    if isinstance(source,u.MaterialInstanceConstant):
        M.set_material_instance_parent(local,grass_exclusion(source.get_editor_property('parent'),route,cfg,cache))
    else:
        assert isinstance(local,u.Material) and local.blend_mode==u.BlendMode.BLEND_MASKED,'Native grass must retain a masked parent'
        nodes=[n for n in M.get_material_expressions(local) if str(n.get_editor_property('desc'))=='LidarFloraGrassExclusion']
        code='float d=1e12;\n';pts=[T.at(route,s) for s in range(cfg['start_m'],cfg['end_m']+1,10)]
        for a,b in zip(pts,pts[1:]):
            code+='{{float2 a=float2({:.5f},{:.5f}),b=float2({:.5f},{:.5f});float2 ab=b-a;float t=saturate(dot(P.xy-a,ab)/dot(ab,ab));d=min(d,length(P.xy-a-ab*t));}}\n'.format(a[0],a[1],b[0],b[1])
        code+='return Mask*smoothstep({:.1f},{:.1f},d);'.format(cfg['half_width_m']*100-180,cfg['half_width_m']*100+100)
        if cfg.get('retain_native_grass',False):
            code='float cover=1.;\n'
            for rock in cfg['outcrops']:
                x,y,_=T.at(route,rock['station'],rock['across']);radius=rock['width_cm']*.42
                code+='cover*=smoothstep({:.3f},{:.3f},distance(P.xy,float2({:.5f},{:.5f})));\n'.format(radius-35,radius,x,y)
            code+='return Mask*cover;'
        if not nodes:
            old=M.get_material_property_input_node(local,u.MaterialProperty.MP_OPACITY_MASK);port=str(M.get_material_property_input_node_output_name(local,u.MaterialProperty.MP_OPACITY_MASK));assert old
            g=Graph(local,'LidarFloraGrassExclusion');p=g.node(u.MaterialExpressionWorldPosition)
            node=g.custom(['P','Mask'],code,u.CustomMaterialOutputType.CMOT_FLOAT1);g.wire(p,node,'P');g.wire(old,node,'Mask',port);g.output(node,u.MaterialProperty.MP_OPACITY_MASK)
        else:
            next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom)).set_editor_property('code',code)
        M.recompile_material(local)
    E.save_loaded_asset(local);return local
