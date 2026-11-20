"""Build map-local test copies with an equivalent threshold for the filtered painted leaf mask."""

import hashlib
import json
import sys
from pathlib import Path

import unreal as u


root = Path(u.Paths.project_dir()).resolve()
sys.path.insert(0, str(root / "Art/Unreal"))
from benmore_river_life_materials import Graph

assets = u.EditorAssetLibrary
materials = u.MaterialEditingLibrary
base = "/Game/GrandTour/ArtTests/LidarStudy"
folder = base + "/PerformanceStudy"
assets.make_directory(folder)
manifest = json.loads((root / "Art/Export/LidarStudy/FloraPath/scene-manifest.json").read_text())
ramp = manifest["materials"]["Leaf_0"]["ramp"]
assert ramp[0] == [0.0, 0.0] and ramp[-1][1] == 1.0 and len(ramp) == 3


def inverse_smoothstep(value):
    low, high = 0.0, 1.0
    for _ in range(45):
        t = (low + high) / 2
        if t * t * (3 - 2 * t) < value:
            low = t
        else:
            high = t
    return (low + high) / 2


def mask_threshold(coverage, gain):
    if coverage > 1.0 or gain <= 0 or coverage > gain:
        return 2.0
    value = coverage / gain
    for (x0, y0), (x1, y1) in zip(ramp, ramp[1:]):
        assert x1 > x0 and y1 > y0
        if value <= y1:
            x = x0 + (x1 - x0) * (value - y0) / (y1 - y0)
            return 12.92 * x if x <= 0.04045 / 12.92 else 1.055 * x ** (1 / 2.4) - 0.055
    raise AssertionError(value)


def connected(mat, expression):
    return [node for node in materials.get_inputs_for_material_expression(mat, expression) if node]


def scratch_copy(source, name):
    dest = folder + "/" + name
    result = (
        u.load_asset(dest)
        if assets.does_asset_exist(dest)
        else assets.duplicate_asset(source.get_path_name().split(".")[0], dest)
    )
    assert result and result != source
    return result


leaves = (
    "MI_Path_Leaf_0_T_Colour_6_4c813bf5",
    "MI_Path_Leaf_0_T_Colour_5_ca124a94",
    "MI_Path_Leaf_0_T_Colour_4_4cbf099c",
)
for kind, leaf in enumerate(leaves):
    paths = [
        p
        for p in assets.list_assets(base + "/FloraTrailStyle/v1", False)
        if p.split("/")[-1].split(".")[0].startswith(leaf)
    ]
    assert len(paths) == 1, paths
    original = u.load_asset(paths[0])
    gain = materials.get_material_instance_scalar_parameter_value(original, "Coverage")
    softness = materials.get_material_instance_scalar_parameter_value(
        original, "PaintedEdgeSoftness"
    )
    chain, parent = [], original
    while isinstance(parent, u.MaterialInstance):
        overrides = parent.get_editor_property("base_property_overrides")
        assert not overrides.get_editor_property("override_opacity_mask_clip_value")
        chain.append(parent)
        parent = parent.get_editor_property("parent")
    clip = parent.get_editor_property("opacity_mask_clip_value")
    assert not parent.get_editor_property("dither_opacity_mask")
    assert gain > 0 and 0 < clip < 1
    package = (
        root / "Content" / parent.get_path_name().split(".")[0].removeprefix("/Game/")
    ).with_suffix(".uasset")
    signature = hashlib.sha256(
        package.read_bytes() + json.dumps([ramp, gain, softness, clip]).encode()
    ).hexdigest()
    mat = scratch_copy(parent, f"M_FilteredLeafMask_{kind}_{signature[:12]}")
    if assets.get_metadata_tag(mat, "FilteredMaskSignature") != signature:
        switch = materials.get_material_property_input_node(mat, u.MaterialProperty.MP_OPACITY_MASK)
        assert isinstance(switch, u.MaterialExpressionShadowReplace), switch
        inputs = connected(mat, switch)
        view = next(n for n in inputs if isinstance(n, u.MaterialExpressionCustom))
        shadow = next(n for n in inputs if isinstance(n, u.MaterialExpressionMultiply))
        assert "saturate((c-.22)/max(fwidth(c),.035)+.5)" in view.get_editor_property("code")
        assert abs(shadow.get_editor_property("const_b") - 1.7) < 1e-6
        (alpha,) = connected(mat, shadow)
        assert isinstance(alpha, u.MaterialExpressionCustom) and alpha in connected(mat, view)
        assert "Mask<.04045?Mask/12.92:pow((Mask+.055)/1.055,2.4)" in alpha.get_editor_property(
            "code"
        )
        assert "return saturate(a*Gain)" in alpha.get_editor_property("code")
        for x, y in ramp[1:]:
            assert str(x) in alpha.get_editor_property("code") and str(
                y
            ) in alpha.get_editor_property("code")
        mask = next(
            n
            for n in connected(mat, alpha)
            if isinstance(n, u.MaterialExpressionTextureSampleParameter2D)
        )
        assert str(mask.get_editor_property("parameter_name")) == "PaintedMask"
        graph = Graph(mat, "FilteredLeafMask")
        # For a clip value of 0.5, the positive derivative denominator cannot
        # change which side of the painted edge a pixel lies on.
        values = {"Shadow": mask_threshold(clip / shadow.get_editor_property("const_b"), gain)}
        if clip == 0.5:
            required = 0.015 + (max(0.05, softness) - 0.015) * inverse_smoothstep(0.22)
            values["Default"] = mask_threshold(required, gain)
        for pin, threshold in values.items():
            shifted = graph.node(u.MaterialExpressionAdd, const_b=clip - threshold)
            graph.wire(mask, shifted, "A", "R")
            graph.wire(shifted, switch, pin)
        assert not materials.recompile_material(mat)
        assets.set_metadata_tag(mat, "FilteredMaskSignature", signature)
        assert assets.save_loaded_asset(mat, False)
    for index, instance in enumerate(reversed(chain)):
        name = (
            f"MI_FilteredLeafMask_{kind}"
            if instance == original
            else f"MI_FilteredLeafMask_{kind}_parent{index}"
        )
        copied = scratch_copy(instance, name)
        materials.set_material_instance_parent(copied, mat)
        assert assets.save_loaded_asset(copied, False)
        mat = copied
    u.log(
        f"GT_MASK_VERIFIED kind={kind} clip={clip} gain={gain} softness={softness} camera_simplified={clip == 0.5}"
    )
u.log("GT_MASK_STUDY_READY")
