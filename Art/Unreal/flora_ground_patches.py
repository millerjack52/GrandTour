"""Isolated soil/moss/litter distribution; source samples and central mud preserved."""
from pathlib import Path
import json,unreal as u
from benmore_river_life_materials import Graph,props
import flora_crown_materials as crown
import flora_woodland_mud as brown
R=Path('C:/GrandTour');O=Path('D:/GrandTourAssets/ReviewEvidence/FloraTrail/GroundPatches')
CFG=json.loads((R/'Art/flora_ground_patches_settings.json').read_text())
D='/Game/GrandTour/ArtTests/FloraTrail/Woodland/GroundPatches/'+CFG['revision']
BASE=crown.MAP;MAP=D+'/L_FloraTrail_GroundPatches'
E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
PROFILES={'baseline':0.,'patches':.75,'strong':1.}
SELECTED=PROFILES[CFG['selected']]

def clone(source,name):
    path=D+'/'+name;m=u.load_asset(path)
    if not m:
        m=E.duplicate_asset(source.get_path_name().split('.')[0],path);assert m
        g=Graph(m,'GroundPatches')
        node=next(n for n in M.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom) and 'VergeNormal=' in str(n.get_editor_property('code')))
        code=str(node.get_editor_property('code'))
        needle='float3 colour=lerp(C2,C0,moss);'
        assert code.count(needle)==1
        # Retain the old transition weight: the wheel channels remain unchanged.
        code=code.replace(needle,'''float2 warp=float2(f.n(P.xy/240.+71.),f.n(P.xy/240.+113.))-.5;
float2 q=P.xy+warp*145.;
float broad=f.n(q/680.);
float largeMoss=smoothstep(.39,.60,broad)*.90;
float largeLitter=smoothstep(.49,.64,f.n(q/430.+31.))*.86*(1.-largeMoss*.70);
moss=lerp(moss,largeMoss,saturate(GroundPatchStrength));
litter=lerp(litter,largeLitter,saturate(GroundPatchStrength));
float3 colour=lerp(C2,C0,moss);''')
        outputs=[(p,M.get_material_property_input_node_output_name(m,p) or '') for p in (u.MaterialProperty.MP_BASE_COLOR,u.MaterialProperty.MP_NORMAL,u.MaterialProperty.MP_ROUGHNESS)]
        assert all(M.get_material_property_input_node(m,p)==node for p,out in outputs)
        # Disconnect the live outputs while extending the custom input list.
        # Otherwise editor auto-compilation observes the temporarily unwired pin.
        temporary=g.scalar(0.)
        for prop,out in outputs:g.output(temporary,prop)
        control=g.node(u.MaterialExpressionScalarParameter,parameter_name='GroundPatchStrength',default_value=SELECTED)
        node.set_editor_property('inputs',list(node.get_editor_property('inputs'))+[props(u.CustomInput(),input_name='GroundPatchStrength')])
        g.wire(control,node,'GroundPatchStrength')
        node.set_editor_property('code',code)
        for prop,out in outputs:g.output(node,prop,out)
        M.delete_material_expression(m,temporary)
    for n in M.get_material_expressions(m):
        if isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))=='GroundPatchStrength':n.set_editor_property('default_value',SELECTED)
    audit_material(source,m)
    assert not M.recompile_material(m);assert E.save_loaded_asset(m,False)
    return m

def audit_material(source,new):
    def textures(m):return [(n.get_name(),n.get_editor_property('texture').get_path_name() if n.get_editor_property('texture') else None) for n in M.get_material_expressions(m) if isinstance(n,u.MaterialExpressionTextureSample)]
    assert textures(source)==textures(new)
    old={n.get_name():str(n.get_editor_property('code')) for n in M.get_material_expressions(source) if isinstance(n,u.MaterialExpressionCustom)}
    current={n.get_name():str(n.get_editor_property('code')) for n in M.get_material_expressions(new) if isinstance(n,u.MaterialExpressionCustom)}
    for name,code in old.items():
        if 'VergeNormal=' not in code:assert code==current[name],name
    for prop in (u.MaterialProperty.MP_WORLD_POSITION_OFFSET,u.MaterialProperty.MP_OPACITY_MASK):
        a=M.get_material_property_input_node(source,prop);b=M.get_material_property_input_node(new,prop)
        assert (a.get_name() if a else None)==(b.get_name() if b else None)
        assert M.get_material_property_input_node_output_name(source,prop)==M.get_material_property_input_node_output_name(new,prop)
    return {'texture_samples':len(textures(new)),'non_verge_shader_programs_unchanged':True,'displacement_and_mask_connections_unchanged':True}

def install(world):
    surface=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface));landscape=surface.landscape
    material=clone(landscape.landscape_material,'M_GroundPatchesLandscape')
    landscape.set_editor_property('landscape_material',material);landscape.set_editor_property('use_dynamic_material_instance',True)
    for c in landscape.get_components_by_class(u.MeshComponent):
        for i in range(c.get_num_materials()):c.set_material(i,material)
    visual=u.GameplayStatics.get_all_actors_of_class(world,u.GTMudRunnerVisual)[0]
    source=visual.material;parent=clone(source.get_editor_property('parent'),'M_GroundPatchesMud')
    mi=u.load_asset(D+'/MI_GroundPatchesMud') or E.duplicate_asset(source.get_path_name().split('.')[0],D+'/MI_GroundPatchesMud')
    M.set_material_instance_parent(mi,parent);M.update_material_instance(mi);assert E.save_loaded_asset(mi,False)
    visual.set_editor_property('material',mi)

def audit(world):
    surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0]
    visual=u.GameplayStatics.get_all_actors_of_class(world,u.GTMudRunnerVisual)[0]
    assert surface.landscape.landscape_material.get_path_name().startswith(D+'/M_GroundPatchesLandscape')
    assert visual.material.get_path_name().startswith(D+'/MI_GroundPatchesMud')
    return {'terrain':audit_material(u.load_asset('/Game/GrandTour/ArtTests/FloraTrail/MudTrial/M_VergeLandscape'),surface.landscape.landscape_material),'overlay':audit_material(u.load_asset(brown.D+'/M_WoodlandBrownMud'),visual.material.get_editor_property('parent')),'mud':brown.audit(visual.material)}

def geometry(world):
    data=json.dumps(crown.geometry(world))
    for root in (BASE,MAP):data=data.replace(root+'.'+root.rsplit('/',1)[-1],'<ReviewWorld>').replace(root,'<ReviewMap>')
    return json.loads(data)
