"""Coverage-only pine experiment. Approved pigment, normals and shadows stay fixed."""
import unreal as u
import json, hashlib
from pathlib import Path
from benmore_river_life_materials import Graph
import flora_crown_materials as crown
import flora_woodland_materials as wood

R=Path('C:/GrandTour');O=Path('D:/GrandTourAssets/ReviewEvidence/FloraTrail/PineBrush')
CFG=json.loads((R/'Art/flora_pine_brush_settings.json').read_text())
D='/Game/GrandTour/ArtTests/FloraTrail/Woodland/PineBrush/'+CFG['revision']
BASE=crown.MAP;MAP=D+'/L_FloraTrail_PineBrush'
E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
KEYS=('BrushEnabled','BrushThreshold','BrushFacing')
PROFILES={
    'baseline':dict(zip(KEYS,(0.,.35,1.))),
    'threshold45':dict(zip(KEYS,(1.,.45,1.))),
    'threshold55':dict(zip(KEYS,(1.,.55,1.))),
    'fixed45':dict(zip(KEYS,(1.,.45,0.))),
}
SELECTED=PROFILES[CFG['selected']]

def eligible(component,role):
    return role=='canopy' and component.static_mesh.get_name()=='SM_Exact_pine_f002'

def protected_outputs(m):
    result={}
    for name in ('MP_BASE_COLOR','MP_NORMAL','MP_SUBSURFACE_COLOR','MP_ROUGHNESS','MP_SPECULAR','MP_AMBIENT_OCCLUSION','MP_WORLD_POSITION_OFFSET','MP_EMISSIVE_COLOR'):
        prop=getattr(u.MaterialProperty,name);node=M.get_material_property_input_node(m,prop)
        result[name]=[node.get_name() if node else None,str(M.get_material_property_input_node_output_name(m,prop))]
    return result

def clone(source):
    path=D+'/M_Brush_'+hashlib.sha1(source.get_path_name().encode()).hexdigest()[:8]
    m=u.load_asset(path)
    if not m:
        m=E.duplicate_asset(source.get_path_name().split('.')[0],path);assert m
        g=Graph(m,'PineBrush');nodes=list(M.get_material_expressions(m))
        params={k:g.node(u.MaterialExpressionScalarParameter,parameter_name=k,default_value=v) for k,v in SELECTED.items()}
        coverage=next(n for n in nodes if isinstance(n,u.MaterialExpressionTextureSampleParameter2D) and str(n.get_editor_property('parameter_name'))=='SourceCoverage')
        old=M.get_material_property_input_node(m,u.MaterialProperty.MP_OPACITY_MASK)
        port=M.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_OPACITY_MASK) or ''
        assert abs(m.opacity_mask_clip_value-.35)<1e-5
        mask=g.custom(['Original','A','N','V','Enabled','Threshold','Facing'],'''#if SHADOW_DEPTH_SHADER
return Original;
#else
float facing=pow(saturate(abs(dot(normalize(N),normalize(V)))),.7);
float coverage=A*lerp(1.,.15+.85*facing,saturate(Facing));
// Keep the material clip at .35; adjust only the tested coverage threshold.
return lerp(Original,.35+coverage-Threshold,saturate(Enabled));
#endif''',u.CustomMaterialOutputType.CMOT_FLOAT1)
        for node,pin,out in [(old,'Original',port),(coverage,'A','R'),(g.node(u.MaterialExpressionVertexNormalWS),'N',''),(g.node(u.MaterialExpressionCameraVectorWS),'V','')]:g.wire(node,mask,pin,out)
        for key,pin in [('BrushEnabled','Enabled'),('BrushThreshold','Threshold'),('BrushFacing','Facing')]:g.wire(params[key],mask,pin)
        g.output(mask,u.MaterialProperty.MP_OPACITY_MASK)
    for n in M.get_material_expressions(m):
        if isinstance(n,u.MaterialExpressionScalarParameter):
            key=str(n.get_editor_property('parameter_name'))
            if key in SELECTED:n.set_editor_property('default_value',SELECTED[key])
    assert protected_outputs(m)==protected_outputs(source)
    assert not M.recompile_material(m);assert E.save_loaded_asset(m,False)
    return m

def geometry(world):
    data=json.dumps(crown.geometry(world))
    for root in (BASE,MAP):data=data.replace(root+'.'+root.rsplit('/',1)[-1],'<ReviewWorld>').replace(root,'<ReviewMap>')
    return json.loads(data)

def configure(mid,profile):
    for key,value in profile.items():mid.set_scalar_parameter_value(key,value)

def focus_views(world):
    choices=[]
    components=[(a.get_actor_label(),c) for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor) for c in a.get_components_by_class(u.InstancedStaticMeshComponent) if c.static_mesh and c.static_mesh.get_name()=='SM_Exact_pine_f002']
    for actor,c in components:
        bounds=c.static_mesh.get_bounds()
        for i in range(c.get_instance_count()):
            t=c.get_instance_transform(i,True)
            local=bounds.origin+u.Vector(0,0,bounds.box_extent.z*.25)
            target=u.MathLibrary.transform_location(t,local)
            radius=max(bounds.box_extent.x*abs(t.scale3d.x),bounds.box_extent.y*abs(t.scale3d.y))
            score=(t.translation.x+1200)**2+(t.translation.y+900)**2
            choices.append((score,actor,c.get_name(),i,target,radius))
    assert choices
    _,_,_,_,target,radius=min(choices,key=lambda row:row[:4])
    views=[]
    for name,distance in [('pine_close',max(500.,radius*1.6)),('pine_middle',max(1500.,radius*3.)),('pine_far',max(3500.,radius*5.))]:
        views.append((name,[target.x-distance*.6,target.y-distance*.8,target.z],list(target.to_tuple())))
    return views

def audit(mid):
    crown.audit(mid)
    values={k:mid.get_scalar_parameter_value(k) for k in SELECTED}
    assert all(abs(values[k]-SELECTED[k])<1e-5 for k in SELECTED),values
    return values
