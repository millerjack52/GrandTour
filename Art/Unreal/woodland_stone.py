"""Adapt the existing rock surfaces to the woodland floor while keeping each mesh's UVs and relief."""

import unreal as u
from benmore_river_life_materials import Graph

E = u.EditorAssetLibrary
M = u.MaterialEditingLibrary
USAGE = u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES

STONE = """
float2 uv=(P.xy-Origin.xy)/Span;
float4 f=Texture2DSample(Habitat,View.MaterialTextureBilinearClampedSampler,uv);
float w=all(uv>=0)*all(uv<=1);
if(w<.003) return Original;
// The broad mineral planes come from the mesh's own texture. Keep a lower-amplitude
// contribution from its sharper pigment for cracks and edges seen near the player.
float3 macro=Texture2DSampleBias(Stone,StoneSampler,UV,3.).rgb;
float3 lum=float3(.26,.58,.16);
float value=smoothstep(.045,.43,dot(macro,lum));
float3 n=normalize(Up);float3 axis=pow(abs(n),4);axis/=max(.001,axis.x+axis.y+axis.z);
float4 pigment=Texture2DSample(Paint,View.MaterialTextureBilinearWrapedSampler,P.yz/130.)*axis.x
              +Texture2DSample(Paint,View.MaterialTextureBilinearWrapedSampler,P.xz/130.)*axis.y
              +Texture2DSample(Paint,View.MaterialTextureBilinearWrapedSampler,P.xy/130.)*axis.z;
float planes=saturate(value*.40+pigment.r*.60);
float3 face=lerp(float3(.035,.041,.038),float3(.100,.088,.066),smoothstep(.28,.49,planes));
face=lerp(face,float3(.164,.151,.115),smoothstep(.54,.70,planes)*.85);
face*=.86+.26*pigment.g;
float moss=smoothstep(.48,.90,n.z)*smoothstep(.31,.70,.47*f.g+.53*pigment.b);
float3 patina=lerp(float3(.047,.060,.027),float3(.119,.132,.055),smoothstep(.30,.69,pigment.a));
return lerp(Original,lerp(face,patina,moss*.86),w);
"""


def rock_material(source, dest, atlas, field, ledges, apply):
    path = dest + "/M_Woodland_" + source.get_name()
    mat = u.load_asset(path) if E.does_asset_exist(path) else None
    if not mat:
        assert apply, path
        mat = E.duplicate_asset(source.get_path_name().split(".")[0], path)
        assert isinstance(mat, u.Material), path
        if not ledges:
            samples = [
                n.texture
                for n in M.get_material_expressions(mat)
                if isinstance(n, u.MaterialExpressionTextureSample)
                and n.texture
                and n.texture.get_name().lower().endswith(("_colour", "_color"))
            ]
            assert len(set(samples)) == 1, (path, samples)
            base = M.get_material_property_input_node(mat, u.MaterialProperty.MP_BASE_COLOR)
            pin = str(
                M.get_material_property_input_node_output_name(
                    mat, u.MaterialProperty.MP_BASE_COLOR
                )
                or ""
            )
            g = Graph(mat, "WoodlandStone")
            node = g.custom(
                ["Original", "Stone", "UV", "P", "Up", "Habitat", "Origin", "Span"], STONE
            )
            g.wire(base, node, "Original", pin)
            g.wire(
                g.node(
                    u.MaterialExpressionTextureObject,
                    texture=samples[0],
                    sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR,
                ),
                node,
                "Stone",
            )
            g.wire(g.node(u.MaterialExpressionTextureCoordinate), node, "UV")
            g.wire(g.node(u.MaterialExpressionWorldPosition), node, "P")
            g.wire(g.node(u.MaterialExpressionVertexNormalWS), node, "Up")
            g.wire(
                g.node(
                    u.MaterialExpressionTextureObject,
                    texture=atlas,
                    sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS,
                ),
                node,
                "Habitat",
            )
            g.wire(g.vector((*field["origin"], 0)), node, "Origin")
            g.wire(g.scalar(field["span"]), node, "Span")
            from woodland_community import wire_paint

            wire_paint(mat, node, True)
            g.output(node, u.MaterialProperty.MP_BASE_COLOR)
        M.set_material_usage(mat, USAGE)
        assert not M.recompile_material(mat)
        E.set_metadata_tag(mat, "HabitatStoneSource", source.get_path_name())
        assert E.save_loaded_asset(mat, False)
    assert E.get_metadata_tag(mat, "HabitatStoneSource") == source.get_path_name()
    assert mat.get_editor_property("used_with_instanced_static_meshes")
    if not ledges:
        from woodland_community import wire_paint

        node = M.get_material_property_input_node(mat, u.MaterialProperty.MP_BASE_COLOR)
        assert node.get_editor_property("desc") == "WoodlandStone"
        changed = wire_paint(mat, node, apply)
        normal = M.get_material_property_input_node(mat, u.MaterialProperty.MP_NORMAL)
        if normal.get_editor_property("desc") != "WoodlandRockRelief":
            assert apply
            port = str(
                M.get_material_property_input_node_output_name(mat, u.MaterialProperty.MP_NORMAL)
                or ""
            )
            g = Graph(mat, "WoodlandRockRelief")
            broad = g.custom(["N"], "return normalize(float3(N.xy*.32,max(.10,N.z)));")
            g.wire(normal, broad, "N", port)
            g.output(broad, u.MaterialProperty.MP_NORMAL)
            changed = True
        if changed or node.get_editor_property("code") != STONE:
            assert apply, path
            mat.modify()
            node.modify()
            node.set_editor_property("code", STONE)
            assert not M.recompile_material(mat)
            assert E.save_loaded_asset(mat, False)
    return mat


def bind_rocks(rows, dest, atlas, field, apply):
    tally = {}
    for actor in rows:
        label = actor.get_actor_label()
        if label not in ("LidarStudy_FloraWorld_Rocks", "LidarStudy_ForestAccessBend_v1"):
            continue
        for c in actor.get_components_by_class(u.InstancedStaticMeshComponent):
            if not c.visible or c.hidden_in_game or not c.static_mesh or not c.get_instance_count():
                continue
            ledges = label != "LidarStudy_FloraWorld_Rocks"
            if ledges and "ForestAccessRiverReveal" not in map(str, c.component_tags):
                continue
            current = c.get_material(0)
            source = current
            if current.get_path_name().startswith(dest + "/"):
                source = u.load_asset(E.get_metadata_tag(current, "HabitatStoneSource"))
            assert source and (not ledges or source.get_name() == "M_BendMossLedges")
            mat = rock_material(source, dest, atlas, field, ledges, apply)
            if current != mat:
                assert apply, c.get_name()
                actor.modify()
                c.modify()
                c.set_material(0, mat)
            tally[label + "/" + c.get_name()] = c.get_instance_count()
    assert tally, "No woodland rock families found"
    return tally
