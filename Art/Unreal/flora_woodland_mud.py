"""Pigment-only brown adjustment, isolated from the saved woodland baseline."""
from pathlib import Path
import json,unreal as u
from benmore_river_life_materials import Graph
R=Path('C:/GrandTour');O=Path('D:/GrandTourAssets/ReviewEvidence/FloraTrail/WoodlandMud')
D='/Game/GrandTour/ArtTests/FloraTrail/Woodland/BrownMud'
MAP=D+'/L_FloraTrail_BrownMud'
SOURCE='/Game/GrandTour/ArtTests/FloraTrail/MudTrial'
TINT=json.loads((R/'Art/flora_woodland_mud_settings.json').read_text())['tint']
E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary

def build():
    path=D+'/M_WoodlandBrownMud'
    m=u.load_asset(path)
    if not m:
        m=E.duplicate_asset(SOURCE+'/M_VergeMud',path);assert m
        nodes=M.get_material_expressions(m)
        wrapper=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and 'TrialRoughness=lerp' in str(n.get_editor_property('code')))
        colour=next(n for n in nodes if isinstance(n,u.MaterialExpressionTextureSampleParameter2D) and str(n.get_editor_property('parameter_name'))=='MudTrialColour')
        g=Graph(m,'WoodlandBrownMud')
        tint=g.node(u.MaterialExpressionVectorParameter,parameter_name='WoodlandMudTint',default_value=u.LinearColor(*TINT,1))
        pigment=g.custom(['C','Tint'],'return C*Tint;')
        g.wire(colour,pigment,'C','RGB');g.wire(tint,pigment,'Tint','RGB');g.wire(pigment,wrapper,'Colour')
        assert not M.recompile_material(m);assert E.save_loaded_asset(m,False)
    mi=u.load_asset(D+'/MI_WoodlandBrownMud') or E.duplicate_asset(SOURCE+'/MI_VergeMud',D+'/MI_WoodlandBrownMud');assert mi
    M.set_material_instance_parent(mi,m)
    M.set_material_instance_vector_parameter_value(mi,'WoodlandMudTint',u.LinearColor(*TINT,1))
    M.update_material_instance(mi);assert E.save_loaded_asset(mi,False)
    return mi

def audit(mi):
    original=u.load_asset(SOURCE+'/MI_VergeMud')
    for kind in ('scalar','texture'):
        values=original.get_editor_property(kind+'_parameter_values')
        assert str(values)==str(mi.get_editor_property(kind+'_parameter_values')),kind
    parent=mi.get_editor_property('parent');source=u.load_asset(SOURCE+'/M_VergeMud')
    for prop in (u.MaterialProperty.MP_NORMAL,u.MaterialProperty.MP_ROUGHNESS,u.MaterialProperty.MP_WORLD_POSITION_OFFSET):
        a=M.get_material_property_input_node(source,prop);b=M.get_material_property_input_node(parent,prop)
        assert (a.get_name() if a else None)==(b.get_name() if b else None),prop
        assert M.get_material_property_input_node_output_name(source,prop)==M.get_material_property_input_node_output_name(parent,prop)
    return {'material':mi.get_path_name(),'tint':TINT,'original_scalar_and_texture_overrides_preserved':True,'normal_roughness_displacement_outputs_preserved':True}
