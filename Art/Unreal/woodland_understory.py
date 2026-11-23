"""LiDAR-owned painted understory materials and folded, ground-facing litter."""

import math
import random
import unreal as u
from benmore_river_life_materials import Graph

M = u.MaterialEditingLibrary
E = u.EditorAssetLibrary

FOLIAGE = """
float value=dot(Old,float3(.26,.58,.16));
float upper=smoothstep(.07,.96,Q.z);
float4 marks=Texture2DSample(Paint,View.MaterialTextureBilinearWrapedSampler,
                            float2(Q.x*.66+Q.y*.53, Q.z+Q.y*.22)*1.65);
float brush=smoothstep(.31,.70,marks.r*.67+marks.g*.33);
float form=saturate(.43*upper+.35*smoothstep(.018,.235,value)+.22*brush);
float3 green=lerp(float3(.030,.052,.025),float3(.077,.112,.047),smoothstep(.16,.53,form));
float tips=smoothstep(.56,.85,form)*smoothstep(.29,.72,brush+.14*upper);
green=lerp(green,float3(.155,.163,.066),tips);
return green*lerp(.81,1.11,saturate(value*3+.30*brush));
"""


def plant_material(mi, dest, paint, apply):
    source = mi.get_editor_property("parent")
    path = dest + "/M_Understory_" + source.get_name()
    mat = u.load_asset(path) if E.does_asset_exist(path) else None
    if not mat:
        assert apply
        mat = E.duplicate_asset(source.get_path_name().split(".")[0], path)
        g = Graph(mat, "WoodlandPlantPigment")
        old = M.get_material_property_input_node(mat, u.MaterialProperty.MP_BASE_COLOR)
        pin = str(
            M.get_material_property_input_node_output_name(mat, u.MaterialProperty.MP_BASE_COLOR)
            or ""
        )
        from flora_world_art_direction import local_volume

        node = g.custom(["Old", "Q", "Paint"], FOLIAGE)
        g.wire(old, node, "Old", pin)
        g.wire(local_volume(g), node, "Q")
        g.wire(
            g.node(
                u.MaterialExpressionTextureObject,
                texture=paint,
                sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS,
            ),
            node,
            "Paint",
        )
        g.output(node, u.MaterialProperty.MP_BASE_COLOR)
        if M.get_material_property_input_node(mat, u.MaterialProperty.MP_SUBSURFACE_COLOR):
            trans = g.custom(["C"], "return C*float3(.48,.55,.36);")
            g.wire(node, trans, "C")
            g.output(trans, u.MaterialProperty.MP_SUBSURFACE_COLOR)
        M.set_material_usage(mat, u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
        assert not M.recompile_material(mat)
        assert E.save_loaded_asset(mat, False)
    node = M.get_material_property_input_node(mat, u.MaterialProperty.MP_BASE_COLOR)
    assert node.get_editor_property("desc") == "WoodlandPlantPigment"
    if node.get_editor_property("code") != FOLIAGE:
        assert apply
        mat.modify()
        node.modify()
        node.set_editor_property("code", FOLIAGE)
        assert not M.recompile_material(mat) and E.save_loaded_asset(mat, False)
    child_path = dest + "/MI_Understory_" + mi.get_name()
    child = u.load_asset(child_path) if E.does_asset_exist(child_path) else None
    if not child:
        assert apply
        child = E.duplicate_asset(mi.get_path_name().split(".")[0], child_path)
        M.set_material_instance_parent(child, mat)
        E.set_metadata_tag(child, "WoodlandPlantSource", mi.get_path_name())
        assert E.save_loaded_asset(child, False)
    assert child.get_editor_property("parent") == mat
    return child


def folded_litter(dest, source, apply):
    path = dest + "/SM_FoldedLeafLitter"
    mesh = u.load_asset(path) if E.does_asset_exist(path) else None
    if mesh and E.get_metadata_tag(mesh, "FoldedLitter") == "1":
        return mesh
    assert apply
    mat = (
        u.load_asset(dest + "/M_FoldedLeafLitter")
        if E.does_asset_exist(dest + "/M_FoldedLeafLitter")
        else u.AssetToolsHelpers.get_asset_tools().create_asset(
            "M_FoldedLeafLitter", dest, u.Material, u.MaterialFactoryNew()
        )
    )
    if not mat:
        mat = u.load_asset(dest + "/M_FoldedLeafLitter")
    M.delete_all_material_expressions(mat)
    g = Graph(mat, "FoldedLeaves")
    g.output(g.node(u.MaterialExpressionVertexColor), u.MaterialProperty.MP_BASE_COLOR)
    g.output(g.scalar(0.91), u.MaterialProperty.MP_ROUGHNESS)
    g.output(g.scalar(0.14), u.MaterialProperty.MP_SPECULAR)
    mat.set_editor_property("two_sided", True)
    M.set_material_usage(mat, u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
    assert not M.recompile_material(mat) and E.save_loaded_asset(mat, False)
    part = dict(origin=[0, 0, 0], v=[], t=[], c=[], uv=[])
    bounds = source.get_bounding_box()
    width = (bounds.max.x - bounds.min.x) / 100
    depth = (bounds.max.y - bounds.min.y) / 100
    rng = random.Random(8190)
    for i in range(34):
        x = rng.gauss(-0.10 if i < 22 else 0.20, 0.17) * width
        y = rng.gauss(0.09 if i < 22 else -0.18, 0.14) * depth
        a = rng.gauss(-0.45 if i < 22 else 0.68, 0.88)
        length = rng.uniform(0.055, 0.108)
        half_width = length * rng.uniform(0.15, 0.25)
        fold = length * 0.15
        tone = rng.uniform(0.73, 1.12)
        tint = (0.148, 0.085, 0.035) if i % 6 else (0.107, 0.102, 0.039)
        verts = [
            (-0.52, 0, 0.15),
            (-0.30, -0.77, 0.63),
            (0.05, -1, 0.92),
            (0.32, -0.56, 0.61),
            (0.55, 0, 0.30),
            (0.29, 0.62, 0.36),
            (-0.06, 0.90, 0.54),
            (-0.35, 0.63, 0.37),
            (0, 0, 0.05),
        ]
        start = len(part["v"])
        lift = rng.uniform(0.005, 0.016)
        for j, (l, w, h) in enumerate(verts):
            part["v"].append(
                [
                    x + math.cos(a) * l * length - math.sin(a) * w * half_width,
                    y + math.sin(a) * l * length + math.cos(a) * w * half_width,
                    lift + h * fold,
                ]
            )
            shade = (0.68 if j in (5, 6, 7) else 1.01) if j != 8 else 0.80
            part["c"].append([v * tone * shade for v in tint])
            part["uv"].append([l + 0.5, w * 0.5 + 0.5])
        for j in range(8):
            part["t"].append((start + 8, start + (j + 1) % 8, start + j))
    mesh = mesh or E.duplicate_asset(source.get_path_name().split(".")[0], path)
    for lod, stride in enumerate((1, 2, 4)):
        indices = [i for i in range(len(part["v"])) if (i // 9) % stride == 0]
        local = {old: i for i, old in enumerate(indices)}
        buf = u.GeometryScriptSimpleMeshBuffers()
        buf.vertices = [u.Vector(*(a * 100 for a in part["v"][i])) for i in indices]
        buf.triangles = [
            u.IntVector(*(local[i] for i in tri)) for tri in part["t"] if tri[0] in local
        ]
        buf.vertex_colors = [u.LinearColor(*part["c"][i], 1) for i in indices]
        buf.uv0 = [u.Vector2D(*part["uv"][i]) for i in indices]
        dynamic = u.DynamicMesh()
        dynamic.append_buffers_to_mesh(buf)
        opts = u.GeometryScriptCopyMeshToAssetOptions()
        opts.emit_transaction = False
        _, result = u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(
            dynamic, mesh, opts, u.GeometryScriptMeshWriteLOD(lod_index=lod), False
        )
        assert result == u.GeometryScriptOutcomePins.SUCCESS
    mesh.set_material(0, mat)
    E.set_metadata_tag(mesh, "FoldedLitter", "1")
    assert E.save_loaded_asset(mesh, False)
    return mesh


def bind_understory(rows, dest, apply):
    paint = u.load_asset(dest + "/T_WoodlandPaint")
    tally = {}
    for a in rows:
        label = a.get_actor_label()
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            if not c.static_mesh or not c.visible or c.hidden_in_game:
                continue
            name = c.static_mesh.get_name()
            key = label + "/" + c.get_name()
            if name in ("SM_NZ_LeafLitter_A", "SM_FoldedLeafLitter"):
                source = u.load_asset(
                    "/Game/GrandTour/Environment/NativePlants/v01/SM_NZ_LeafLitter_A"
                )
                mesh = folded_litter(dest, source, apply)
                if c.static_mesh != mesh:
                    assert apply and c.get_collision_enabled() == u.CollisionEnabled.NO_COLLISION
                    a.modify()
                    c.modify()
                    assert c.set_static_mesh(mesh)
                    c.set_material(0, mesh.get_material(0))
                assert c.get_material(0) == mesh.get_material(0)
                tally[key] = c.get_instance_count()
            if label not in ("LidarStudy_FloraWorld_FernCover", "LidarStudy_FloraWorld_Understory"):
                continue
            if not any(k in name for k in ("Ferns_", "Blooming_Shrubbery", "Small_Plants")):
                continue
            current = c.get_material(0)
            src = current
            if current.get_path_name().startswith(dest + "/"):
                src = u.load_asset(E.get_metadata_tag(current, "WoodlandPlantSource"))
            assert isinstance(src, u.MaterialInstanceConstant)
            target = plant_material(src, dest, paint, apply)
            if target != current:
                assert apply
                a.modify()
                c.modify()
                c.set_material(0, target)
            tally[key] = c.get_instance_count()
    assert tally
    return tally
