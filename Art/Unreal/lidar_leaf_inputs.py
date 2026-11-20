"""Trace the UV channels used by each D003 material output and measure index locality."""

from collections import OrderedDict
import json
import os
from pathlib import Path

import unreal as u


root = "/Game/GrandTour/ArtTests/LidarStudy"
leaf = u.load_asset(root + "/FloraTrailStyle/v1/MI_Path_Leaf_0_T_Colour_5_ca124a94")
mesh = u.load_asset(root + "/FloraWorld/Canopy/SM_Canopy_1")
material = leaf
while isinstance(material, u.MaterialInstance):
    material = material.get_editor_property("parent")
edit = u.MaterialEditingLibrary
outputs = {}
for name in (
    "BASE_COLOR",
    "NORMAL",
    "OPACITY_MASK",
    "SUBSURFACE_COLOR",
    "WORLD_POSITION_OFFSET",
    "ROUGHNESS",
    "SPECULAR",
    "AMBIENT_OCCLUSION",
    "EMISSIVE_COLOR",
):
    prop = getattr(u.MaterialProperty, "MP_" + name)
    first = edit.get_material_property_input_node(material, prop)
    if not first:
        continue
    todo = [(first, ())]
    seen = set()
    uses = []
    while todo:
        node, path = todo.pop()
        if not node or node in seen:
            continue
        seen.add(node)
        chain = (*path, node.get_name())
        if isinstance(node, u.MaterialExpressionTextureSample):
            if isinstance(node, u.MaterialExpressionTextureSampleParameter2D):
                chain = (*path, str(node.get_editor_property("ParameterName")))
            uses.append(
                dict(
                    type="sample_default",
                    uv=node.get_editor_property("ConstCoordinate"),
                    path=chain,
                )
            )
        if isinstance(node, u.MaterialExpressionTextureCoordinate):
            uses.append(
                dict(
                    type="connected_uv", uv=node.get_editor_property("CoordinateIndex"), path=chain
                )
            )
        if isinstance(node, u.MaterialExpressionMaterialFunctionCall):
            raise ValueError(f"Inspect material function on {name}: {node.get_path_name()}")
        todo.extend(
            (src, chain) for src in edit.get_inputs_for_material_expression(material, node) if src
        )
    outputs[name] = dict(nodes=len(seen), uses=uses)

sections = []
for lod in (1, 2):
    # The source asset's section 1 is the painted leaves at both playable near LODs.
    pos, indices, _, _, _ = u.ProceduralMeshLibrary.get_section_from_static_mesh(mesh, lod, 1)
    indices = list(indices)
    cache = OrderedDict()
    misses = 0
    for index in indices:
        if index in cache:
            cache.move_to_end(index)
        else:
            misses += 1
            cache[index] = None
            if len(cache) > 32:
                cache.popitem(last=False)
    sections.append(
        dict(
            lod=lod,
            triangles=len(indices) // 3,
            referenced=len(set(indices)),
            lru32_misses=misses,
            vertices=len(pos),
            vertices_in_32_triangle_batches=sum(
                len(set(indices[i : i + 96])) for i in range(0, len(indices), 96)
            ),
        )
    )
report = dict(
    material=leaf.get_path_name(),
    master=material.get_path_name(),
    outputs=outputs,
    mesh=mesh.get_path_name(),
    leaf_sections=sections,
)
assert any(
    use["uv"] == 1 and use["type"] == "connected_uv" for use in outputs["BASE_COLOR"]["uses"]
)
Path(os.environ["GT_LIDAR_LEAF_INPUT_REPORT"]).write_text(json.dumps(report, indent=2) + "\n")
u.log("GT_LEAF_INPUTS_READY traced_pigment_uv1=1")
