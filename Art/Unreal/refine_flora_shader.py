"""Port Flora Paint's coverage and lighting behaviour into the isolated trial."""
import unreal as u
import json,traceback,hashlib
from pathlib import Path

ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/LidarStudy/FloraShader';OUT.mkdir(parents=True,exist_ok=True)
DEST='/Game/GrandTour/ArtTests/FloraPilot'
eal=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary
report={'ok':False,'woodland_modified':False,'performance_verified':False,'materials':[]}
def props(o,**kw):
    for k,v in kw.items():o.set_editor_property(k,v)
    return o
def node(m,cls,**kw):return props(mel.create_material_expression(m,cls),**kw)
def wire(a,b,p,out=''):assert mel.connect_material_expressions(a,out,b,p),(p,out)
def output(n,p,out=''):assert mel.connect_material_property(n,out,p)
def scalar(m,name,v):return node(m,u.MaterialExpressionScalarParameter,parameter_name=name,default_value=v)
def vector(m,name,v):return node(m,u.MaterialExpressionVectorParameter,parameter_name=name,default_value=u.LinearColor(*v,1))
def custom(m,names,code,kind=u.CustomMaterialOutputType.CMOT_FLOAT3):
    return node(m,u.MaterialExpressionCustom,code=code,output_type=kind,inputs=[props(u.CustomInput(),input_name=n) for n in names])

# Alpha ramps and softness read from the purchased source's material graph.
SETTINGS=[
 ('Leaves','plant_0',(.0793,.1488,.0237),.31075698,[(0,0),(.1681818,.4196344),(.5545454,1)]),
 ('Shrub','shrubbery_0',(.0609,.1201,.0129),.82898891,[(0,0),(.9227271,1)]),
 ('Grass','grass_0',(.0759,.1512,.0155),.87250996,[(0,0),(.3954544,.5),(.5409092,1)]),
 ('GrassClump','grass_0',(.0644,.1264,.0135),.73306769,[(0,0),(.3954544,.5),(.5409092,1)]),
 ('Groundleaf','plant_0',(.0759,.1512,.0155),.41723648,[(0,0),(1,1)])
]
def configure(kind,texture,tint,softness,ramp):
    m=u.load_asset(DEST+'/M_Flora_'+kind);assert m
    mel.delete_all_material_expressions(m)
    props(m,two_sided=True,tangent_space_normal=False,dither_opacity_mask=True,has_pixel_animation=False,blend_mode=u.BlendMode.BLEND_MASKED,
          shading_model=u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE,opacity_mask_clip_value=.5)
    mel.set_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
    vc=node(m,u.MaterialExpressionVertexColor);normal=node(m,u.MaterialExpressionVertexNormalWS)
    view=node(m,u.MaterialExpressionCameraVectorWS)
    sample=node(m,u.MaterialExpressionTextureSampleParameter2D,parameter_name='LeafMask',texture=u.load_asset(DEST+'/T_Flora_'+texture),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    # Preserve the source's fractional coverage. Its Blender graph also fades
    # grazing cards with Layer Weight rather than displaying each as a solid plane.
    segments=[]
    for (x0,y0),(x1,y1) in zip(ramp,ramp[1:]):
        segments.append(f'if(Mask<{x1}) a=lerp({y0},{y1},saturate((Mask-{x0})/{x1-x0}));')
    rampcode='float a=1; '+ ' else '.join(segments)
    code=rampcode+'''
float b=clamp(EdgeSoftness,.001,.98);
float exponent=b<.5?2*b:.5/(1-b);
float facing=pow(saturate(abs(dot(normalize(N),normalize(V)))),exponent);
float coverage=a*lerp(GrazingCoverage,1,facing)*.9333333;
return saturate(coverage*Density);
'''
    alpha=custom(m,['Mask','N','V','EdgeSoftness','GrazingCoverage','Density'],code,u.CustomMaterialOutputType.CMOT_FLOAT1)
    wire(sample,alpha,'Mask','R');wire(normal,alpha,'N');wire(view,alpha,'V')
    density=1.5 if kind=='Leaves' else (2.0 if kind=='Groundleaf' else 1.65)
    grazing=.75 if kind=='Groundleaf' else .3
    wire(scalar(m,'EdgeSoftness',softness),alpha,'EdgeSoftness');wire(scalar(m,'GrazingCoverage',grazing),alpha,'GrazingCoverage');wire(scalar(m,'LeafDensity',density),alpha,'Density')
    # The source's partially transparent cards transmit more sunlight than a
    # hard shadow mask. Keep opaque centres while opening fine shadow gaps.
    shadow_alpha=node(m,u.MaterialExpressionMultiply);wire(alpha,shadow_alpha,'A');wire(scalar(m,'ShadowDensity',.78),shadow_alpha,'B')
    shadow_switch=node(m,u.MaterialExpressionShadowReplace);wire(alpha,shadow_switch,'Default');wire(shadow_alpha,shadow_switch,'Shadow');output(shadow_switch,u.MaterialProperty.MP_OPACITY_MASK)
    # The shipped Eevee patch uses world-up normals. Keep a small amount of
    # source normal shape. UE world-space normals are not automatically flipped
    # for foliage backfaces (MaterialTemplate.ush); both sides should face up.
    lighting=custom(m,['N','UpBlend'],'return normalize(lerp(normalize(N),float3(0,0,1),UpBlend));')
    wire(normal,lighting,'N');wire(scalar(m,'NormalSoftness',.96),lighting,'UpBlend');output(lighting,u.MaterialProperty.MP_NORMAL)
    pos=node(m,u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    colour=custom(m,['Tint','Variation','Mask','Detail','P','ClusterSize','ClusterVariation','PaletteSoftness'],'''
float detail=lerp(1.,lerp(.42,1.12,saturate(Mask)),Detail);
float3 q=P/max(ClusterSize,1.);
float mass=.5+.5*sin(q.x+sin(q.z*1.37))*sin(q.y*.97+q.z*.51);
float value=lerp(1.,lerp(.52,1.05,mass),ClusterVariation);
float luma=dot(Tint,float3(.2126,.7152,.0722));
float3 palette=lerp(Tint,luma.xxx,PaletteSoftness);
return palette*Variation*detail*value;''')
    wire(vector(m,'FoliageTint',tint),colour,'Tint');wire(vc,colour,'Variation');wire(sample,colour,'Mask','R');wire(scalar(m,'LeafDetail',.8),colour,'Detail')
    wire(pos,colour,'P');wire(scalar(m,'ClusterSizeCm',85 if kind=='Leaves' else 26),colour,'ClusterSize');wire(scalar(m,'ClusterVariation',.5),colour,'ClusterVariation');wire(scalar(m,'PaletteSoftness',.18),colour,'PaletteSoftness');output(colour,u.MaterialProperty.MP_BASE_COLOR)
    # A bounded portion of actual sky irradiance softens leaf interiors. This
    # follows the map's skylight (including night), rather than adding a fixed glow.
    fill=custom(m,['Colour','Strength','SunFill'],'''
float3 sky=float3(View.SkyIrradianceEnvironmentMap[0].z+View.SkyIrradianceEnvironmentMap[0].w+View.SkyIrradianceEnvironmentMap[3].z,
 View.SkyIrradianceEnvironmentMap[1].z+View.SkyIrradianceEnvironmentMap[1].w+View.SkyIrradianceEnvironmentMap[4].z,
 View.SkyIrradianceEnvironmentMap[2].z+View.SkyIrradianceEnvironmentMap[2].w+View.SkyIrradianceEnvironmentMap[5].z);
// Small art-directed bounce from the actual scene sun. The renderer supplies
// linear sun irradiance / PI, so this scales with time-of-day light intensity.
// It deliberately ignores local occlusion; keep the strength bounded and low.
float3 sun=max(View.DirectionalLightColor.rgb,0)*saturate(View.DirectionalLightDirection.z);
return Colour*(max(sky,0)*View.SkyLightColor.rgb*Strength+sun*clamp(SunFill,0,.25));''')
    wire(colour,fill,'Colour');wire(scalar(m,'SkySoftFill',.45),fill,'Strength');wire(scalar(m,'SunBounce',.14),fill,'SunFill');output(fill,u.MaterialProperty.MP_EMISSIVE_COLOR)
    back=node(m,u.MaterialExpressionMultiply);wire(colour,back,'A');wire(scalar(m,'Backlight',.42),back,'B');output(back,u.MaterialProperty.MP_SUBSURFACE_COLOR)
    output(scalar(m,'TransmissionThickness',.6),u.MaterialProperty.MP_OPACITY)
    output(scalar(m,'Roughness',.95),u.MaterialProperty.MP_ROUGHNESS);output(scalar(m,'Specular',.08),u.MaterialProperty.MP_SPECULAR)
    wind=custom(m,['T','Speed','P','Strength','Weight'],'float a=sin(T*Speed+P.x*.003+P.y*.002); return float3(a,a*.37,0)*Strength*Weight;')
    wire(node(m,u.MaterialExpressionTime),wind,'T');wire(scalar(m,'WindSpeed',1.4),wind,'Speed');wire(node(m,u.MaterialExpressionWorldPosition),wind,'P');wire(scalar(m,'WindStrengthCm',0),wind,'Strength');wire(vc,wind,'Weight','A');output(wind,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    mel.recompile_material(m);assert eal.save_loaded_asset(m)
    report['materials'].append({'material':m.get_path_name(),'alpha_ramp':ramp,'edge_softness':softness,'texture_samples':1,'normal_softness':.96,'density':density,'grazing_coverage':grazing,'native_dither_opacity':True,'shadow_density':.78,'leaf_detail':.8,'cluster_size_cm':85 if kind=='Leaves' else 26,'cluster_variation':.5,'palette_softness':.18,'sky_soft_fill':.45,'sun_bounce':.14,'backlight':.42,'transmission_thickness':.6,'roughness':.95,'specular':.08,'wind_strength_cm':0})

try:
    for args in SETTINGS:configure(*args)
    # Compile the actual desktop shader permutations before reporting success.
    for row in report['materials']:
        stats=mel.get_statistics(u.load_asset(row['material']))
        row['compiled_statistics']={key:getattr(stats,key) for key in ['num_vertex_shader_instructions','num_pixel_shader_instructions','num_samplers','num_vertex_texture_samples','num_pixel_texture_samples','num_virtual_texture_samples','num_uv_scalars','num_interpolator_scalars']}
    protected=json.loads((OUT/'protected-before.json').read_text())
    for row in protected:
        row['unchanged']=hashlib.file_digest(Path(row['file']).open('rb'),'sha256').hexdigest()==row['sha256']
        assert row['unchanged'],row['file']
    report['protected_assets']=protected;report['ok']=True
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'shader-report.json').write_text(json.dumps(report,indent=2))
def finish(dt):
    u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(finish)
