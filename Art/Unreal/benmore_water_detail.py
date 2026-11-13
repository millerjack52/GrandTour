"""Perforated advected froth, shallow optics and batched ballistic riffle spray."""
import unreal as u
from pathlib import Path
from benmore_river_life_materials import Graph,props
mel=u.MaterialEditingLibrary;eal=u.EditorAssetLibrary
DEST='/Game/GrandTour/Demo/BenmoreRoads/Gaea/WaterDetail'
SRC='/Game/GrandTour/Demo/BenmoreRoads/Gaea/WaterRapids'

FROTH=r'''
struct BrokenFroth {
 float h(float2 p){return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);}
 float n(float2 p){float2 i=floor(p),f=frac(p);f=f*f*(3-2*f);return lerp(lerp(h(i),h(i+float2(1,0)),f.x),lerp(h(i+float2(0,1)),h(i+1),f.x),f.y);}
 float3 sampleFoam(float2 p){
  float2 warp=float2(n(p*2.1),n(p*2.1+19))-.5;
  p+=warp*.14;
  float strand=smoothstep(.47,.69,n(p*float2(2.2,12)));
  float gaps=smoothstep(.32,.62,n(p*7.8+31));
  float2 b=p*25,cell=floor(b),f=frac(b),delta=0;float best=10,bubbleSeed=0;
  [unroll]for(int y=-1;y<=1;y++)[unroll]for(int x=-1;x<=1;x++){
   float2 ij=float2(x,y),c=cell+ij;
   float2 d=ij+.5+float2(h(c),h(c+71))*.64-.32-f;
   float ds=dot(d,d);if(ds<best){best=ds;delta=d;bubbleSeed=h(c+39);}
  }
  float r=sqrt(best);
  float radius=lerp(.13,.37,bubbleSeed),width=lerp(.035,.11,h(cell+87));
  float rim=(1-smoothstep(width,width+.08,abs(r-radius)))*smoothstep(.32,.66,n(p*43+12));
  float beads=(1-smoothstep(radius*.3,radius*.85,r))*.6;
  float lace=smoothstep(.51,.76,n(p*float2(13,37)+warp*3));
  float coverage=strand*gaps*saturate(rim*.55+beads+lace*.65);
  return float3(coverage,delta*coverage);
 }
 float3 advect(float2 q,float2 v,float clock){
  float turn=atan2(v.y,v.x)/6.2831853*16;
  float lo=floor(turn),blendDir=smoothstep(0,1,frac(turn));
  float phase=clock/2.8+n(q*.075)*.7;
  float a=frac(phase),b=frac(phase+.5),blend=abs(a*2-1);float3 outF=0;
  [unroll]for(int j=0;j<2;j++){
   float sn,cs;sincos((lo+j)*6.2831853/16,sn,cs);
   float2 x=float2(cs,sn),y=float2(-sn,cs);
   float2 p=float2(dot(q,x),dot(q,y)),adv=float2(dot(v,x),dot(v,y))*2.8;
   float3 f=lerp(sampleFoam(p-adv*(a-.5)),sampleFoam(p-adv*(b-.5)+float2(17.3,9.1)),blend);
   outF+=float3(f.x,x*f.y+y*f.z)*(j==0?1-blendDir:blendDir);
  }
  return outF;
 }
};BrokenFroth broken;
float detailResolve=1-smoothstep(.015,.075,max(length(ddx(q)),length(ddy(q))));
float3 frothDetail=0;
[branch]if(rapidStrength>.001 && detailResolve>.001 && nearFade>.001)frothDetail=broken.advect(q,ambientVelocity,Clock);
float rapidResolve=1-smoothstep(.06,.22,max(length(ddx(q)),length(ddy(q))));
// Preserve the dark water between bubbles. Never threshold a broad patch into white.
float frothCoverage=lerp(surfaceThreads*.18,frothDetail.x,detailResolve);
float whitewater=frothCoverage*lerp(.32,1,rapidWave.a)*smoothstep(.08,.55,rapidStrength)*shore*nearFade*rapidResolve;
foam=saturate(foam*.32+whitewater*1.8);
Normal=normalize(Normal+float3(frothDetail.yz*.75*rapidStrength*detailResolve,0));
'''

def precombine():
    m=u.load_asset(DEST+'/M_FW_Precombine') or eal.duplicate_asset(SRC+'/M_FW_Precombine',DEST+'/M_FW_Precombine')
    assert eal.save_loaded_asset(m);return m

def surface(kind):
    name='M_GC_Domain'+kind;source=u.load_asset(SRC+'/'+name);assert source
    m=u.load_asset(DEST+'/'+name) or eal.duplicate_asset(SRC+'/'+name,DEST+'/'+name)
    for n in list(mel.get_material_expressions(m)):
        if str(n.get_editor_property('desc'))=='WaterDetail':mel.delete_material_expression(m,n)
    g=Graph(m,'WaterDetail')
    src=mel.get_material_property_input_node(source,u.MaterialProperty.MP_BASE_COLOR)
    node=mel.get_material_property_input_node(m,u.MaterialProperty.MP_BASE_COLOR)
    code=str(src.get_editor_property('code'))
    start=code.index('// A broken white crest feeds');end=code.index('float2 trail=0;',start)
    code=code[:start]+FROTH+'\n'+code[end:]
    marker='float3 foamColour='
    start=code.index(marker)
    code=code[:start]+'''
// Optical coverage fades over the actual signed bank distance, independent of
// the live simulation window. This also suppresses the sharp sun at the rim.
float wetEdge=lerp(1,smoothstep(0,.45,bankDistance)*smoothstep(.005,.12,ambientDepth),inBake);
Opacity*=wetEdge;Scatter*=wetEdge;Absorb*=wetEdge;
Rough=lerp(.48,Rough,wetEdge);
Spec=lerp(.002,lerp(.32,.20,smoothstep(35,160,dist)),wetEdge)*(1-foam*.6);
// Bounded screen refraction from moving normal deviations; no constant
// whole-plane offset. Engine SLW adds scene-depth/disocclusion rejection.
float3 baseView=TransformWorldVectorToView(baseNormal);
float3 waterView=TransformWorldVectorToView(Normal);
Refract=clamp((baseView.xy-waterView.xy)*.10,-.035,.035)*wetEdge*(1-foam)*RefractionGain;
float3 foamColour=lerp(float3(.43,.51,.47),float3(.78,.84,.79),saturate(whitewater*3));
return lerp(colour*wetEdge,foamColour,foam);
'''
    inputs=list(node.get_editor_property('inputs'))
    if 'RefractionGain' not in {str(i.get_editor_property('input_name')) for i in inputs}:
        node.set_editor_property('inputs',inputs+[props(u.CustomInput(),input_name='RefractionGain')])
    g.wire(g.node(u.MaterialExpressionScalarParameter,parameter_name='RefractionStrength',default_value=1),node,'RefractionGain')
    outputs=list(node.get_editor_property('additional_outputs'))
    for name,kind in [('Spec',u.CustomMaterialOutputType.CMOT_FLOAT1),('Refract',u.CustomMaterialOutputType.CMOT_FLOAT2)]:
        if name not in {str(o.get_editor_property('output_name')) for o in outputs}:outputs.append(props(u.CustomOutput(),output_name=name,output_type=kind))
    node.set_editor_property('additional_outputs',outputs);node.set_editor_property('code',code)
    props(m,refraction_method=u.RefractionMode.RM_2D_OFFSET,refraction_depth_bias=2.0)
    g.output(node,u.MaterialProperty.MP_SPECULAR,'Spec');g.output(node,u.MaterialProperty.MP_REFRACTION,'Refract')
    errors=mel.recompile_material(m);assert not errors,list(errors)
    assert eal.save_loaded_asset(m);return m

def spray_material(rebuild=False):
    path=DEST+'/M_RiffleSpray'
    existing=u.load_asset(path)
    if not rebuild and existing and existing.get_editor_property('shading_model')==u.MaterialShadingModel.MSM_UNLIT:
        # Support a small exposure correction without rebuilding the animation.
        spray_exposure(existing)
        assert not mel.recompile_material(existing);assert eal.save_loaded_asset(existing)
        return existing
    m=existing or u.AssetToolsHelpers.get_asset_tools().create_asset('M_RiffleSpray',DEST,u.Material,u.MaterialFactoryNew())
    for n in list(mel.get_material_expressions(m)):mel.delete_material_expression(m,n)
    props(m,blend_mode=u.BlendMode.BLEND_MASKED,shading_model=u.MaterialShadingModel.MSM_UNLIT,two_sided=True,tangent_space_normal=False,opacity_mask_clip_value=.45)
    g=Graph(m,'RiffleSpray')
    inputs={'P':g.node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS),
        'UV':g.node(u.MaterialExpressionTextureCoordinate,coordinate_index=0),'SeedUV':g.node(u.MaterialExpressionTextureCoordinate,coordinate_index=1),
        'Camera':g.node(u.MaterialExpressionCameraPositionWS),'Time':g.node(u.MaterialExpressionTime),
        'Override':g.node(u.MaterialExpressionScalarParameter,parameter_name='WaterTimeOverride',default_value=-1),
        'Baked':g.node(u.MaterialExpressionTextureObject,texture=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Gaea/Morphology/T_RS_DomainFlow'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)}
    common='''
float seed=SeedUV.x,clock=Override>=0?Override:Time;
float period=.85+seed*.9,duration=.29+frac(seed*7.13)*.16;
float age=frac(clock/period+seed*13.7)*period/duration;
float t=saturate(age);
float3 root=P-float3((UV-.5)*4,0);
float2 buv=(root.xy*.01-float2(-1480,-300)+.625)/float2(1261.25,1076.25);
float4 flow=Texture2DSampleLevel(Baked,BakedSampler,saturate(buv),0);
float2 v=(flow.rg-.5)*4;
float fade=(1-smoothstep(2200,6000,length(Camera-root)))*step(age,1);
'''
    wpo=g.custom(list(inputs),common+'''
float3 view=normalize(Camera-root),right=normalize(cross(float3(0,0,1),view)),up=cross(view,right);
float size=lerp(1.0,2.7,frac(seed*29.1))*fade;
float3 billboard=(right*(UV.x-.5)+up*(UV.y-.5)*1.6)*size;
float height=lerp(5,17,frac(seed*17.7))*4*t*(1-t);
return root-P+float3(v*duration*t*100,height)+billboard;
''')
    mask=g.custom(list(inputs),common+'''
float2 p=(UV-.5)*2;
return (1-smoothstep(.48,.92,dot(p,p)))*fade*smoothstep(0,.08,t)*(1-smoothstep(.82,1,t));
''',u.CustomMaterialOutputType.CMOT_FLOAT1)
    for key,n in inputs.items():g.wire(n,wpo,key);g.wire(n,mask,key)
    normal=g.custom(['P','Camera'],'return normalize(Camera-P);');g.wire(inputs['P'],normal,'P');g.wire(inputs['Camera'],normal,'Camera')
    g.output(wpo,u.MaterialProperty.MP_WORLD_POSITION_OFFSET);g.output(mask,u.MaterialProperty.MP_OPACITY_MASK)
    g.output(normal,u.MaterialProperty.MP_NORMAL);g.output(g.vector((.50,.62,.58)),u.MaterialProperty.MP_BASE_COLOR)
    # Tiny aerated droplets need a stable soft luminance on either side of a
    # card. A camera-facing lit normal otherwise turns the backlit spray black.
    spray_exposure(m)
    g.output(g.scalar(.24),u.MaterialProperty.MP_ROUGHNESS);g.output(g.scalar(.6),u.MaterialProperty.MP_SPECULAR)
    assert not mel.recompile_material(m);assert eal.save_loaded_asset(m);return m

def spray_exposure(m):
    # Daylight uses physical light intensities and correspondingly low exposure.
    # Unit-valued unlit colour becomes black without inverse eye adaptation.
    for n in list(mel.get_material_expressions(m)):
        if str(n.get_editor_property('desc'))=='RiffleSprayExposure':mel.delete_material_expression(m,n)
    g=Graph(m,'RiffleSprayExposure')
    colour=g.custom(['Exposure'],'return float3(.55,.64,.60)/max(Exposure,.00001);')
    g.wire(g.node(u.MaterialExpressionEyeAdaptation),colour,'Exposure')
    g.output(colour,u.MaterialProperty.MP_EMISSIVE_COLOR)

def install_spray():
    import install_benmore_gaea_creek as shared
    material=spray_material();out=Path(u.Paths.project_dir())/'Art/Export/BenmoreGaea/WaterDetail_20261011'
    task=props(u.AssetImportTask(),filename=str(out/'SM_RiffleSpray.fbx'),destination_path=DEST,destination_name='SM_RiffleSpray',automated=True,replace_existing=True,save=True)
    opt=props(u.FbxImportUI(),import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,import_animations=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
    props(opt.static_mesh_import_data,combine_meshes=True,convert_scene=True,convert_scene_unit=True,transform_vertex_to_absolute=True,auto_generate_collision=False,generate_lightmap_u_vs=False)
    task.options=opt;u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh=u.load_asset(DEST+'/SM_RiffleSpray');assert mesh;mesh.set_material(0,material);assert eal.save_loaded_asset(mesh)
    actor=shared.refs().get('Benmore_RiffleSpray') or shared.act.spawn_actor_from_class(u.StaticMeshActor,u.Vector(0,0,0))
    actor.set_actor_label('Benmore_RiffleSpray');component=actor.static_mesh_component
    component.set_static_mesh(mesh);component.set_material(0,material);component.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
    props(component,cast_shadow=False,bounds_scale=1.1)
    return actor
