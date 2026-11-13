"""Tree-only native light response trials: source hue, normals and coverage retained."""
import unreal as u

CASES={'colour_medium':(.40,.24),'colour_strong':(.60,.32)}

def make(source,mode):
    E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
    path='/Game/GrandTour/ArtTests/FloraTreeColourReview/'+source.get_name()+'_'+mode
    m=u.load_asset(path) or E.duplicate_asset(source.get_path_name().split('.')[0],path)
    assert m
    reflectance,transmission=CASES[mode];found=set()
    for n in M.get_material_expressions(m):
        if isinstance(n,u.MaterialExpressionScalarParameter):
            k=str(n.get_editor_property('parameter_name'))
            if k=='CanopyReflectance':n.set_editor_property('default_value',reflectance);found.add(k)
            if k=='CanopyTransmission':n.set_editor_property('default_value',transmission);found.add(k)
    assert len(found)==2
    assert not M.recompile_material(m)
    E.save_loaded_asset(m,False)
    return m
