"""Install dedicated copies of the approved meshes for the LiDAR play preset."""
import unreal as u


assets = u.EditorAssetLibrary
root = "/Game/GrandTour/ArtTests/LidarStudy"
folder = root + "/FloraWorld/CrownShadows"
assets.make_directory(folder)
for species in range(3):
    source = f"{root}/PerformanceStudy/SM_NaniteRenderLod1_{species}"
    canopy = u.load_asset(f"{root}/FloraWorld/Canopy/SM_Canopy_{species}")
    study = u.load_asset(source)
    target = f"{folder}/SM_FastCrownShadow_{species}"
    mesh = u.load_asset(target) if assets.does_asset_exist(target) else assets.duplicate_asset(source, target)
    assert mesh and canopy and mesh != study
    settings = mesh.get_editor_property("nanite_settings")
    assert settings.enabled and settings.shape_preservation == u.NaniteShapePreservation.PRESERVE_AREA
    assert [m.material_interface for m in mesh.static_materials] == [m.material_interface for m in study.static_materials]
    assert mesh.get_static_mesh_description(0).get_triangle_count() == study.get_static_mesh_description(0).get_triangle_count()
    assert assets.save_loaded_asset(mesh, False)
    u.log(f"Installed shadow caster {target}")
u.log("GT_FAST_CROWN_ASSETS_READY")
