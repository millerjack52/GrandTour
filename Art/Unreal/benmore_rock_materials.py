"""Map-owned dry grey stone materials, preserving the shared source pack."""
import unreal as u
DEST='/Game/GrandTour/Demo/BenmoreRoads/Scenery'
def configure(mesh,kind):
    eal=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary
    path=DEST+'/MI_Benmore_DryRock'+str(kind)
    src='/Game/ANGRY_MESH/StylizedPack_MeadowEnvironment/Materials/Instances/Rocks/MI_Rock_'+str(kind).zfill(2)+'_Summer'
    mat=u.load_asset(path) if eal.does_asset_exist(path) else eal.duplicate_asset(src,path)
    assert mat
    for name,val in [('Top Layer Intensity',0),('Top Layer VPaint Intensity',0),('Base Emissive Intensity',0)]:
        mel.set_material_instance_scalar_parameter_value(mat,name,val)
        assert abs(mel.get_material_instance_scalar_parameter_value(mat,name)-val)<.0001,name
    mel.set_material_instance_vector_parameter_value(mat,'Base Albedo Color',u.LinearColor(.45,.44,.41,1))
    assert abs(mel.get_material_instance_vector_parameter_value(mat,'Base Albedo Color').r-.45)<.0001
    mel.update_material_instance(mat);assert eal.save_loaded_asset(mat)
    mesh.set_material(0,mat);assert eal.save_loaded_asset(mesh)
    return mat.get_path_name()
