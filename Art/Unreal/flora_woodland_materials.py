"""Isolated woodland art-direction candidate, retaining source meshes/textures."""
import unreal as u, json, hashlib
from pathlib import Path
from benmore_river_life_materials import Graph,props
from flora_trail_source34 import settings as original_light
import flora_trail_atmosphere as atmosphere
R=Path('C:/GrandTour');O=Path('D:/GrandTourAssets/ReviewEvidence/FloraTrail/Woodland')
CFG=json.loads((R/'Art/flora_woodland_settings.json').read_text())
D='/Game/GrandTour/ArtTests/FloraTrail/Woodland/'+CFG['revision']
MAP=D+'/L_FloraTrail_Woodland';BASE='/Game/GrandTour/ArtTests/FloraTrail/FernSurface/L_FloraTrail_Fern'
E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary

def slots(world):
    result=[]
    for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
        for c in a.get_components_by_class(u.StaticMeshComponent):
            if not c.static_mesh:continue
            name=c.static_mesh.get_name()
            for i,m in enumerate(c.get_materials()):
                if not isinstance(m,u.Material):continue
                role=None
                if name in ('SM_Exact_tree','SM_Exact_pine','SM_Exact_pine_f002'):
                    role='canopy' if m.blend_mode==u.BlendMode.BLEND_MASKED else 'bark'
                elif name=='SM_Exact_shrub':role='shrub'
                elif name=='SM_Exact_grass':role='grass'
                elif name=='SM_Exact_drygrass':role='litter'
                elif name.startswith(('SM_Detail_FP_Rock','SM_RM_')):role='rock'
                if role:result.append((a.get_actor_label(),c,i,m,role))
    return result

def clone(source,role):
    key=hashlib.sha1(source.get_path_name().encode()).hexdigest()[:8]
    path=D+'/Materials/M_Woodland_'+role+'_'+key
    existing=u.load_asset(path)
    if existing:return existing
    m=E.duplicate_asset(source.get_path_name().split('.')[0],path);assert m
    g=Graph(m,'Woodland');nodes=list(M.get_material_expressions(m))
    old=M.get_material_property_input_node(m,u.MaterialProperty.MP_BASE_COLOR)
    out=M.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_BASE_COLOR) or ''
    assert old,(source.get_path_name(),role)
    rand=g.node(u.MaterialExpressionPerInstanceRandom)
    code={
      'canopy':'return C*float3(.76,.86,.94)*lerp(.88,1.06,R);',
      'bark':'return C*float3(.82,.74,.83);',
      'rock':'float moss=smoothstep(.02,.12,C.g-max(C.r,C.b));float l=dot(C,float3(.2126,.7152,.0722));return lerp(C*float3(.58,.62,.59),l*float3(.56,.65,.29),moss);',
      'shrub':'float l=dot(C,float3(.2126,.7152,.0722));float a=smoothstep(.73,.79,R);return lerp(C*float3(.78,1.03,.94),l*float3(2.3,.72,.43),a*.82);',
      'grass':'return C*float3(.78,1.04,.87)*lerp(.85,1.12,R);',
      'litter':'float l=dot(C,float3(.2126,.7152,.0722));return lerp(C*float3(1.,.9,.85),l*float3(2.05,.91,.44),.68);'
    }[role]
    color=g.custom(['C','R'],code);g.wire(old,color,'C',out);g.wire(rand,color,'R');g.output(color,u.MaterialProperty.MP_BASE_COLOR)
    if role in ('grass','shrub','litter'):
        sub=g.custom(['C'],'return C*.22;');g.wire(color,sub,'C');g.output(sub,u.MaterialProperty.MP_SUBSURFACE_COLOR)
    if role=='canopy':
        props(m,tangent_space_normal=False,has_pixel_animation=False,opacity_mask_clip_value=.35,shading_model=u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
        n=g.node(u.MaterialExpressionVertexNormalWS)
        side=g.node(u.MaterialExpressionTwoSidedSign)
        normal=g.custom(['N','Side'],'return normalize(lerp(float3(0,0,1),normalize(N)*Side,'+str(CFG['normal_blend'])+'));')
        g.wire(n,normal,'N');g.wire(side,normal,'Side');g.output(normal,u.MaterialProperty.MP_NORMAL)
        sub=g.custom(['C'],'return C*.12;');g.wire(color,sub,'C');g.output(sub,u.MaterialProperty.MP_SUBSURFACE_COLOR)
        g.output(g.scalar(.82),u.MaterialProperty.MP_ROUGHNESS)
        g.output(g.scalar(.04),u.MaterialProperty.MP_SPECULAR)
        source_mask=next(n for n in nodes if isinstance(n,u.MaterialExpressionTextureSampleParameter2D) and str(n.get_editor_property('parameter_name'))=='SourceCoverage')
        oldmask=M.get_material_property_input_node(m,u.MaterialProperty.MP_OPACITY_MASK)
        oldout=M.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_OPACITY_MASK) or ''
        stable=g.node(u.MaterialExpressionScalarParameter,parameter_name='WoodlandStableCoverage',default_value=1.)
        view=g.node(u.MaterialExpressionCameraVectorWS)
        mask=g.custom(['Original','A','Stable','N','V'],'''#if SHADOW_DEPTH_SHADER
return Original;
#else
float facing=pow(saturate(abs(dot(normalize(N),normalize(V)))),.7);
return lerp(Original,A*(.15+.85*facing),saturate(Stable));
#endif''',u.CustomMaterialOutputType.CMOT_FLOAT1)
        g.wire(oldmask,mask,'Original',oldout);g.wire(source_mask,mask,'A','R');g.wire(stable,mask,'Stable');g.wire(n,mask,'N');g.wire(view,mask,'V');g.output(mask,u.MaterialProperty.MP_OPACITY_MASK)
    M.set_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
    assert not M.recompile_material(m);E.set_metadata_tag(m,'WoodlandSource',source.get_path_name());assert E.save_loaded_asset(m,False)
    return m

def lighting(world,changed=False,depth=False,reverse=False):
    cfg=original_light()
    if changed:
        cfg.update({k:CFG[k] for k in ('sun_energy','sun_colour','sky_strength','sky_colour','sun_ray','sun_source_angle')})
    ray=list(cfg['sun_ray'])
    if reverse:ray=[-ray[0],-ray[1],ray[2]]
    actors=u.GameplayStatics.get_all_actors_of_class(world,u.Actor)
    sun=next(a for a in actors if isinstance(a,u.DirectionalLight) and a.get_actor_label()=='FloraTrail_Sun')
    sky=next(a for a in actors if isinstance(a,u.SkyLight) and a.get_actor_label()=='FloraTrail_Sky')
    sun.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(),u.Vector(*ray)),False)
    sun.light_component.set_intensity(cfg['sun_energy']*.98);sun.light_component.set_light_color(u.LinearColor(*cfg['sun_colour'],1))
    props(sun.light_component,light_source_angle=cfg['sun_source_angle'])
    sky.light_component.set_intensity(cfg['sky_strength']*.98);sky.light_component.set_light_color(u.LinearColor(*cfg['sky_colour'],1));sky.light_component.recapture_sky()
    fog=next(a.component for a in actors if isinstance(a,u.ExponentialHeightFog))
    atmosphere.apply(fog,sun.light_component,CFG if depth else json.loads((R/'Art/flora_trail_atmosphere_settings.json').read_text()))
    return {'sun_energy':cfg['sun_energy'],'sun_ray':ray,'sun_colour':cfg['sun_colour'],'sky_strength':cfg['sky_strength'],'depth':depth}

def geometry(world):
    result=[];S=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
        for c in a.get_components_by_class(u.StaticMeshComponent):
            if not c.static_mesh:continue
            tr=c.get_world_transform()
            row={'actor':a.get_actor_label(),'component':c.get_name(),'mesh':c.static_mesh.get_path_name(),'lods':S.get_lod_count(c.static_mesh),'transform':[*tr.translation.to_tuple(),*tr.rotation.to_tuple(),*tr.scale3d.to_tuple()]}
            if isinstance(c,u.InstancedStaticMeshComponent):
                row['instances']=c.get_instance_count()
                row['instances_hash']=hashlib.sha256(json.dumps([[*t.translation.to_tuple(),*t.rotation.to_tuple(),*t.scale3d.to_tuple()] for t in (c.get_instance_transform(i,True) for i in range(c.get_instance_count()))]).encode()).hexdigest()
            result.append(row)
    data=json.dumps(sorted(result,key=lambda r:(r['actor'],r['component'])))
    for root in (BASE,MAP):
        data=data.replace(root+'.'+root.rsplit('/',1)[-1],'<ReviewWorld>').replace(root,'<ReviewMap>')
    return json.loads(data)

def audit_saved_lighting(world):
    """Read the reloaded map before any runtime light adjustment."""
    actors=u.GameplayStatics.get_all_actors_of_class(world,u.Actor)
    sun=next(a for a in actors if isinstance(a,u.DirectionalLight) and a.get_actor_label()=='FloraTrail_Sun')
    sky=next(a for a in actors if isinstance(a,u.SkyLight) and a.get_actor_label()=='FloraTrail_Sky')
    fog=next(a.component for a in actors if isinstance(a,u.ExponentialHeightFog))
    ray=list(sun.get_actor_forward_vector().to_tuple())
    length=sum(x*x for x in CFG['sun_ray'])**.5
    assert max(abs(a-b/length) for a,b in zip(ray,CFG['sun_ray']))<1e-5
    assert abs(sun.light_component.intensity-CFG['sun_energy']*.98)<1e-5
    assert abs(sky.light_component.intensity-CFG['sky_strength']*.98)<1e-5
    depth=atmosphere.snapshot(fog,sun.light_component)
    for key,value in depth.items():
        actual=value if isinstance(value,list) else [value]
        expected=CFG[key] if isinstance(CFG[key],list) else [CFG[key]]
        assert max(abs(a-b) for a,b in zip(actual,expected))<1e-5,(key,value,CFG[key])
    exposure=[{'actor':a.get_actor_label(),'bias':a.settings.auto_exposure_bias,
               'override':a.settings.override_auto_exposure_bias} for a in actors if isinstance(a,u.PostProcessVolume)]
    overrides=[v['bias'] for v in exposure if v['override']]
    assert overrides and all(abs(v)<1e-6 for v in overrides),exposure
    colours={}
    for name,component in [('sun',sun.light_component),('sky',sky.light_component)]:
        c=component.get_editor_property('light_color')
        colours[name]=[c.r,c.g,c.b,c.a]
    return {'sun_intensity':sun.light_component.intensity,'sky_intensity':sky.light_component.intensity,
            'sun_ray':ray,'stored_light_colours':colours,'fog':depth,'exposure_bias':exposure}
