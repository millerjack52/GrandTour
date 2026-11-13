"""Approved scanned soil layers in Benmore's existing terrain graph.

This adapter is material-only: no landscape rescale, new collision, holes or simulation actors.
"""
import unreal as u
from benmore_river_life_materials import Graph,props

TAG='BenmoreScannedMud'
SOURCE='/Game/GrandTour/ArtTests/LandscapeMudVariants/PBR'
mel=u.MaterialEditingLibrary

CODE=r'''
Normal=OldN;Rough=OldR;Specular=OldS;AO=OldAO;
float2 buv=<BEDUV>;
float4 bed=Texture2DSampleLevel(Bed,View.SharedBilinearClampedSampler,saturate(buv),0);
bed*=all(buv>=0)&&all(buv<=1);
float exposed=1-smoothstep(.08,.5,bed.b);
float silt=max(Eco.g,bed.g*bed.a*exposed);
float road=saturate(Road.r);
float soil=smoothstep(.10,.55,silt)*(1-road);
float verge=Road.g*(1-road)*.52;
float coverage=max(soil,verge)*smoothstep(.68,.93,N.z)*smoothstep(48,85,P.z)*Enabled;
[branch] if(coverage<.001) return Base;
float wet=.9*smoothstep(.10,.55,silt);
float crust=1-smoothstep(.12,.58,wet);
float4 uv=float4(P.xy/260.,P.xy/180.);
float4 dx=ddx(uv),dy=ddy(uv);
float3 view=normalize(Eye);
float fade=(1-smoothstep(1000,2200,distance(Camera,P)))*smoothstep(.08,.25,abs(view.z));
float2 ray=-view.xy/max(abs(view.z),.2)*2.5*coverage*fade;
float4 stepUV=float4(ray/260.,ray/180.);
float steps=lerp(24,12,saturate(abs(view.z)));
float t=0,prevT=0,prevD=0;float4 q=uv;
[branch] if(fade*coverage>.001) {
 float h=lerp(Texture2DSampleGrad(WetHeight,View.SharedBilinearWrappedSampler,q.xy,dx.xy,dy.xy).r,
              Texture2DSampleGrad(DryHeight,View.SharedBilinearWrappedSampler,q.zw,dx.zw,dy.zw).r,crust);
 float d=1-h;
 [loop] for(int i=0;i<24;i++) {
  if(t>=d)break;
  prevT=t;prevD=d;t+=1/steps;q=uv+stepUV*t;
  h=lerp(Texture2DSampleGrad(WetHeight,View.SharedBilinearWrappedSampler,q.xy,dx.xy,dy.xy).r,
         Texture2DSampleGrad(DryHeight,View.SharedBilinearWrappedSampler,q.zw,dx.zw,dy.zw).r,crust);
  d=1-h;
 }
 float a=saturate((prevD-prevT)/max((t-d)+(prevD-prevT),.00001));
 q=uv+stepUV*lerp(prevT,t,a);
}
float3 scanned=Texture2DSampleGrad(WetColor,View.SharedBilinearWrappedSampler,q.xy,dx.xy,dy.xy).rgb;
float3 dry=Texture2DSampleGrad(DryColor,View.SharedBilinearWrappedSampler,q.zw,dx.zw,dy.zw).rgb;
dry=lerp(dot(dry,float3(.2126,.7152,.0722)).xxx,dry,.3)*float3(.9,.93,.91);
float3 colour=lerp(scanned,dry,crust);
colour=lerp(dot(colour,float3(.2126,.7152,.0722)).xxx,colour,.38);
colour*=lerp(lerp(2.2,1.8,wet),.9,crust)*float3(.95,1.,.93);
float3 wn=UnpackNormalMap(float4(Texture2DSampleGrad(WetNormal,View.SharedBilinearWrappedSampler,q.xy,dx.xy,dy.xy).xyz,1));
float3 dn=UnpackNormalMap(float4(Texture2DSampleGrad(DryNormal,View.SharedBilinearWrappedSampler,q.zw,dx.zw,dy.zw).xyz,1));
float3 sn=normalize(lerp(wn,dn,crust));
float3 X=normalize(float3(1,0,-N.x/max(N.z,.1)));
float3 Y=normalize(cross(N,X));
float3 scanN=normalize(N+(X*sn.x+Y*sn.y)/max(sn.z,.35)*.65);
Normal=normalize(lerp(OldN,scanN,coverage));
float r=lerp(Texture2DSampleGrad(WetRough,View.SharedBilinearWrappedSampler,q.xy,dx.xy,dy.xy).r,
             Texture2DSampleGrad(DryRough,View.SharedBilinearWrappedSampler,q.zw,dx.zw,dy.zw).r,crust);
float occlusion=lerp(Texture2DSampleGrad(WetAO,View.SharedBilinearWrappedSampler,q.xy,dx.xy,dy.xy).r,
                     Texture2DSampleGrad(DryAO,View.SharedBilinearWrappedSampler,q.zw,dx.zw,dy.zw).r,crust);
Rough=lerp(OldR,clamp(r*lerp(1,.7,wet),.42,.95),coverage);
Specular=lerp(OldS,.16,coverage);
AO=lerp(OldAO,lerp(1,occlusion,.65),coverage);
return lerp(Base,colour,coverage);
'''

def attach(m):
    nodes=list(mel.get_material_expressions(m))
    # Pass-throughs retain each original output, including the multi-output ChannelPilot node.
    keep=Graph(m,TAG+'Source')
    sources={}
    slots=[('Color',u.MaterialProperty.MP_BASE_COLOR,3,0),('Normal',u.MaterialProperty.MP_NORMAL,3,0),
           ('Rough',u.MaterialProperty.MP_ROUGHNESS,1,.9),('Specular',u.MaterialProperty.MP_SPECULAR,1,.1),
           ('AO',u.MaterialProperty.MP_AMBIENT_OCCLUSION,1,1)]
    for key,prop,size,default in slots:
        marker=TAG+'Source:'+key
        source=next((n for n in nodes if str(n.get_editor_property('desc'))==marker),None)
        if source is None:
            old=mel.get_material_property_input_node(m,prop);out=mel.get_material_property_input_node_output_name(m,prop)
            if old is None:old=keep.scalar(default);out=''
            source=keep.custom(['Value'],'return Value;',u.CustomMaterialOutputType.CMOT_FLOAT3 if size==3 else u.CustomMaterialOutputType.CMOT_FLOAT1)
            source.set_editor_property('desc',marker);keep.wire(old,source,'Value',out)
        sources[key]=source
    for n in nodes:
        if str(n.get_editor_property('desc'))==TAG:mel.delete_material_expression(m,n)
    nodes=list(mel.get_material_expressions(m));g=Graph(m,TAG)
    def texsource(name):
        return next(n for n in nodes if isinstance(n,(u.MaterialExpressionTextureSample,u.MaterialExpressionTextureObject))
                    and n.get_editor_property('texture') and n.get_editor_property('texture').get_name()==name)
    bed=texsource('T_GC_ExtendedBedZones');eco=texsource('T_RL_Ecology');road=texsource('T_Benmore_RoadMask')
    cp=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('desc'))=='ChannelPilot' and 'float2 maskUV=' in n.get_editor_property('code'))
    beduv=next(l.split('=',1)[1].strip().rstrip(';') for l in cp.get_editor_property('code').splitlines() if l.strip().startswith('float2 maskUV='))
    p=g.node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    inputs={'P':p,'Camera':g.node(u.MaterialExpressionCameraPositionWS),'Eye':g.node(u.MaterialExpressionCameraVectorWS),
            'N':g.node(u.MaterialExpressionVertexNormalWS),'Base':sources['Color'],'OldN':sources['Normal'],
            'OldR':sources['Rough'],'OldS':sources['Specular'],'OldAO':sources['AO'],'Bed':bed,'Eco':eco,'Road':road,
            'Enabled':g.node(u.MaterialExpressionScalarParameter,parameter_name='BM_ScannedMudEnabled',default_value=1.)}
    tangent=m.get_editor_property('tangent_space_normal')
    if tangent:
        n=g.node(u.MaterialExpressionTransform,transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_TANGENT,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
        g.wire(sources['Normal'],n,'');inputs['OldN']=n
    for prefix,asset in [('Wet','brown_mud_02'),('Dry','mud_cracked_dry_03')]:
        for suffix,kind in [('Color','Diffuse'),('Height','Displacement'),('Normal','nor_dx'),('Rough','Rough'),('AO','AO')]:
            t=u.load_asset(SOURCE+'/T_'+asset+'_'+kind);assert t
            sampler=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if suffix=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if suffix=='Color' else u.MaterialSamplerType.SAMPLERTYPE_MASKS
            inputs[prefix+suffix]=g.node(u.MaterialExpressionTextureObject,texture=t,sampler_type=sampler)
    f1=u.CustomMaterialOutputType.CMOT_FLOAT1
    node=g.custom(list(inputs),CODE.replace('<BEDUV>',beduv),outputs=[('Normal',u.CustomMaterialOutputType.CMOT_FLOAT3),('Rough',f1),('Specular',f1),('AO',f1)])
    for name,n in inputs.items():g.wire(n,node,name,'RGB' if name in ('Eco','Road') else '')
    for key,prop,_,_ in slots:
        if key=='Normal' and tangent:
            n=g.node(u.MaterialExpressionTransform,transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_TANGENT)
            g.wire(node,n,'','Normal');g.output(n,prop)
        else:g.output(node,prop,'' if key=='Color' else key)
    errors=mel.recompile_material(m);assert not errors,list(errors)
    return {'material':m.get_path_name(),'wet_repeat_cm':260,'dry_repeat_cm':180,'pom_depth_cm':2.5,
            'pom_steps':[12,24],'geometric_displacement':False,'layers':'existing exposed silt and dry road verges; gravel running surface protected'}
