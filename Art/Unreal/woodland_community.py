"""Apply one baked habitat field to ground, both grass distances, ferns and rock."""

import hashlib
import json
import math
import os
import random
from collections import Counter, defaultdict
import unreal as u
from benmore_river_life_materials import Graph, props
from lidar_grounding import GroundSampler
from lidar_bank_material_polish import BUMP
from woodland_stone import bind_rocks
from woodland_understory import bind_understory

REVISION = int(os.environ.get("GT_HABITAT_REVISION", "1"))
DEST = f"/Game/GrandTour/ArtTests/LidarStudy/WoodlandHabitats/v{REVISION}"
TAG = f"GT_WoodlandHabitats_v{REVISION}"
E = u.EditorAssetLibrary
M = u.MaterialEditingLibrary


def import_texture(out, name, mask):
    path = DEST + "/" + name
    file = out / (name + ".png")
    signature = hashlib.sha256(file.read_bytes()).hexdigest()
    t = u.load_asset(path) if E.does_asset_exist(path) else None
    if t and E.get_metadata_tag(t, "HabitatBake") == signature:
        return t
    task = props(
        u.AssetImportTask(),
        filename=str(file),
        destination_path=DEST,
        destination_name=name,
        automated=True,
        replace_existing=True,
        save=True,
    )
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    t = u.load_asset(path)
    assert t, path
    if mask:
        props(
            t,
            srgb=False,
            compression_settings=u.TextureCompressionSettings.TC_MASKS,
            address_x=u.TextureAddress.TA_CLAMP,
            address_y=u.TextureAddress.TA_CLAMP,
            never_stream=True,
        )
    E.set_metadata_tag(t, "HabitatBake", signature)
    assert E.save_loaded_asset(t, False)
    return t


FLOOR = """
float2 uv=(P.xy-Origin.xy)/Span;
float4 field=Texture2DSample(Habitat,View.MaterialTextureBilinearClampedSampler,uv);
float worked=saturate(State.a)*smoothstep(.04,1.1,max(0,-State.r));
Weight=field.r*(1-worked)*all(uv>=0)*all(uv<=1);
Height=0;
[branch] if(Weight<.003) return Old;
float2 q=P.xy/240.;
float4 leaf=Texture2DSample(Litter,View.MaterialTextureBilinearWrapedSampler,q);
float4 paint=Texture2DSample(Paint,View.MaterialTextureBilinearWrapedSampler,P.xy/173.);
float2 tuftUV=float2(dot(P.xy,float2(.80,.60)),dot(P.xy,float2(-.60,.80)))/31.;
float4 tuft=Texture2DSample(Paint,View.MaterialTextureBilinearWrapedSampler,tuftUV+paint.rg*.30);
float2 stoneUV=float2(P.x*.78+P.y*.62,P.z*.65-P.x*.62+P.y*.78)/195.;
float4 mineral=Texture2DSample(Paint,View.MaterialTextureBilinearWrapedSampler,stoneUV);
float moss=smoothstep(.35,.66,field.g*.69+paint.b*.37);
float stone=smoothstep(.28,.70,field.b+(mineral.g-.45)*.32);
float grass=smoothstep(.38,.83,field.a)*(1-stone);
float3 peat=leaf.rgb*float3(.94,.90,.84);
float cushion=smoothstep(.27,.70,.66*paint.b+.34*paint.a);
float shoots=smoothstep(.37,.69,.57*tuft.r+.43*tuft.g);
float3 green=lerp(float3(.034,.050,.019),float3(.119,.132,.041),cushion);
float3 earth=lerp(peat,green,moss);
float soilGrain=dot(leaf.rgb,float3(.26,.58,.16));
earth=lerp(earth,lerp(float3(.070,.090,.032),float3(.154,.176,.067),saturate(soilGrain*5)),grass*.82);
float3 rock=lerp(float3(.055,.048,.037),float3(.128,.109,.077),smoothstep(.31,.68,mineral.r));
float seam=smoothstep(.405,.575,paint.b*.72+field.g*.34+paint.a*.09+(mineral.r-.5)*.09);
rock=lerp(rock,green,seam*.94);
float mossCover=lerp(moss*(1-grass*.82),seam*.94,stone);
// The same patch boundary controls colour and surface relief on rock and on peat.
// Small marks resolve within cushions while the stone between them remains exposed.
float tuftHeight=paint.b*3.1+paint.a*.84+shoots*.67;
Height=lerp(lerp(leaf.a*1.15,mineral.b*2.1,stone),tuftHeight,mossCover);
// Match the value of the source soil at this location. The habitat supplies the hue
// and the variation within it, without turning an entire shaded hillside pale.
float3 lum=float3(.26,.58,.16);
float3 pigment=lerp(earth,rock,stone);
float grain=lerp(lerp(lerp(.74,1.20,leaf.a),lerp(.84,1.14,paint.g),moss),
                 lerp(.68,1.08,mineral.b),stone);
float soilValue=max(.002,dot(Old,lum));
soilValue=lerp(soilValue,clamp(soilValue,.022,.049),moss*.82);
soilValue=lerp(soilValue,.033+.013*smoothstep(.26,.74,mineral.r),stone*.94);
grain=lerp(grain,lerp(.75,1.18,cushion),moss*.86);
grain*=lerp(1.,lerp(.82,1.27,shoots)*lerp(.91,1.15,cushion),mossCover);
pigment*=soilValue*grain/max(.003,dot(pigment,lum));
return lerp(Old,pigment,Weight*.86);
"""

NORMAL_BLEND = "return normalize(lerp(Base,New,Weight*.56));"

GRASS = """
float2 uv=(P.xy-Origin.xy)/Span;
float4 field=Texture2DSample(Habitat,View.MaterialTextureBilinearClampedSampler,uv);
float root=saturate(Parameters.VertexColor.a);
float light=saturate(dot(Old,float3(.25,.60,.15))*3.7);
float3 body=lerp(float3(.048,.073,.028),float3(.160,.191,.070),light);
float shelter=smoothstep(.30,.75,field.g)*(1-smoothstep(.32,.82,field.a));
body*=lerp(float3(1.08,1.03,.98),float3(.77,.85,.85),shelter);
float3 tip=lerp(Old,body,.48);
return lerp(Old,lerp(body*.68,tip,root),field.r*all(uv>=0)*all(uv<=1)*.94);
"""


def material(src, role, atlas, litter, field):
    path = DEST + "/M_Woodland_" + role
    if E.does_asset_exist(path):
        mat = u.load_asset(path)
        assert E.get_metadata_tag(mat, "HabitatSource") == src.get_path_name(), path
        update_surface_code(mat, apply=True)
        return mat
    mat = E.duplicate_asset(src.get_path_name().split(".")[0], path)
    assert mat and isinstance(mat, u.Material), role
    g = Graph(mat, "WoodlandHabitat")
    pos = g.node(
        u.MaterialExpressionWorldPosition,
        world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS,
    )
    prop = u.MaterialProperty.MP_BASE_COLOR

    def old_output(prop):
        node = M.get_material_property_input_node(mat, prop)
        return node, str(
            M.get_material_property_input_node_output_name(mat, prop) or ""
        ) if node else ""

    base, base_pin = old_output(prop)
    assert base, (role, "base")
    is_ground = role in ("Terrain", "Detail", "Relief")
    names = ["P", "Origin", "Span", "Habitat", "Old"]
    if is_ground:
        names += ["Litter", "State"]
    outputs = (
        [(k, u.CustomMaterialOutputType.CMOT_FLOAT1) for k in ("Weight", "Height")]
        if is_ground
        else []
    )
    surface = g.custom(names, FLOOR if is_ground else GRASS, outputs=outputs)
    g.wire(pos, surface, "P")
    g.wire(base, surface, "Old", base_pin)
    g.wire(g.vector((*field["origin"], 0)), surface, "Origin")
    g.wire(g.scalar(field["span"]), surface, "Span")

    def texture(pin, t, sampler):
        assert t, pin
        g.wire(
            g.node(u.MaterialExpressionTextureObject, texture=t, sampler_type=sampler), surface, pin
        )

    texture("Habitat", atlas, u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    if is_ground:
        texture("Litter", litter, u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        wire_paint(mat, surface, apply=True)
        states = [
            n
            for n in M.get_material_expressions(mat)
            if isinstance(n, u.MaterialExpressionCustom)
            and "RR1State"
            in [
                str(o.get_editor_property("output_name"))
                for o in n.get_editor_property("additional_outputs")
            ]
        ]
        assert len(states) == 1, (role, "native contact state", len(states))
        g.wire(states[0], surface, "State", "RR1State")
        prev, normal_pin = old_output(u.MaterialProperty.MP_NORMAL)
        assert not mat.get_editor_property("tangent_space_normal")
        normal = g.node(u.MaterialExpressionVertexNormalWS)
        bump = g.custom(["H", "P", "N", "Camera"], BUMP)
        g.wire(surface, bump, "H", "Height")
        g.wire(pos, bump, "P")
        g.wire(normal, bump, "N")
        g.wire(g.node(u.MaterialExpressionCameraPositionWS), bump, "Camera")
        blend = g.custom(["Base", "New", "Weight"], NORMAL_BLEND)
        g.wire(prev or normal, blend, "Base", normal_pin)
        g.wire(bump, blend, "New")
        g.wire(surface, blend, "Weight", "Weight")
        g.output(blend, u.MaterialProperty.MP_NORMAL)
    g.output(surface, prop)
    update_surface_code(mat, apply=True)
    assert not M.recompile_material(mat), role
    E.set_metadata_tag(mat, "HabitatSource", src.get_path_name())
    assert E.save_loaded_asset(mat, False)
    return mat


def wire_paint(mat, node, apply):
    pins = node.get_editor_property("inputs")
    if any(str(p.get_editor_property("input_name")) == "Paint" for p in pins):
        return False
    assert apply, mat.get_path_name()
    tex = u.load_asset(DEST + "/T_WoodlandPaint")
    assert tex
    mat.modify()
    node.modify()
    node.set_editor_property("inputs", [*pins, props(u.CustomInput(), input_name="Paint")])
    g = Graph(mat, "WoodlandPaint")
    g.wire(
        g.node(
            u.MaterialExpressionTextureObject,
            texture=tex,
            sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS,
        ),
        node,
        "Paint",
    )
    return True


def update_surface_code(mat, apply):
    assert mat.get_path_name().startswith(DEST + "/M_Woodland_")
    base = M.get_material_property_input_node(mat, u.MaterialProperty.MP_BASE_COLOR)
    assert (
        isinstance(base, u.MaterialExpressionCustom)
        and base.get_editor_property("desc") == "WoodlandHabitat"
    )
    is_ground = any(
        str(pin.get_editor_property("input_name")) == "State"
        for pin in base.get_editor_property("inputs")
    )
    nodes = [(base, FLOOR if is_ground else GRASS)]
    if is_ground:
        normal = M.get_material_property_input_node(mat, u.MaterialProperty.MP_NORMAL)
        assert normal.get_editor_property("desc") == "WoodlandHabitat"
        nodes.append((normal, NORMAL_BLEND))
    changed = wire_paint(mat, base, apply) if is_ground else False
    if is_ground:
        # The inherited 25.6 m moss spots also drive AO and height. Blending a
        # new albedo above them leaves pale grain in shadow on exposed slopes.
        old_stamp = "moss=lerp(moss,.230587,smoothstep(2200,6000,dist));"
        far_average = "moss=.230587*smoothstep(2200,6000,dist);"
        (moss_node,) = [
            n
            for n in M.get_material_expressions(mat)
            if isinstance(n, u.MaterialExpressionCustom)
            and "moss=macro.r" in n.get_editor_property("code")
        ]
        inherited = moss_node.get_editor_property("code")
        if old_stamp in inherited:
            assert apply
            mat.modify()
            moss_node.modify()
            moss_node.set_editor_property("code", inherited.replace(old_stamp, far_average))
            changed = True
        else:
            assert far_average in inherited
        pins = base.get_editor_property("inputs")
        kept = [
            p for p in pins if str(p.get_editor_property("input_name")) not in ("Shoots", "Stone")
        ]
        if len(kept) != len(pins):
            assert apply
            mat.modify()
            base.modify()
            base.set_editor_property("inputs", kept)
            changed = True
    for node, text in nodes:
        if node.get_editor_property("code") == text:
            continue
        if not apply:
            raise ValueError(f"Saved surface code differs on {mat.get_path_name()}")
        mat.modify()
        node.modify()
        node.set_editor_property("code", text)
        changed = True
    if changed:
        assert not M.recompile_material(mat)
        assert E.save_loaded_asset(mat, False)


def regroup(rows, field, pixels, ground, river, bend):
    n = field["size"]
    origin = field["origin"]
    factor = n / field["span"]
    protected = defaultdict(set)
    for a, c, i, _ in bend["moved"] + bend["river_reveal"]["moved"]:
        protected[a, c].add(i)

    def sample(x, y):
        i = math.floor((x - origin[0]) * factor)
        j = math.floor((y - origin[1]) * factor)
        if not (0 <= i < n and 0 <= j < n):
            return (0, 0, 0, 0)
        k = (j * n + i) * 4
        return pixels[k : k + 4]

    def suitability(f, kind):
        if kind == "stone":
            return f[2]
        if kind == "grass":
            return f[3]
        return 0.79 * f[1] + 0.21 * (255 - f[3]) - 0.30 * f[2]

    anchors = {}

    def anchor(ix, iy, step, kind):
        key = (ix, iy, kind)
        if key not in anchors:
            r = random.Random(f"{kind}/{ix}/{iy}")
            x = (ix + r.uniform(0.15, 0.85)) * step
            y = (iy + r.uniform(0.15, 0.85)) * step
            anchors[key] = (x, y, suitability(sample(x, y), kind), r.uniform(-math.pi, math.pi))
        return anchors[key]

    inventory = Counter()
    moved = Counter()
    checks = []
    for a in rows:
        label = a.get_actor_label()
        if label not in (
            "LidarStudy_FloraWorld_FernCover",
            "LidarStudy_FloraWorld_Understory",
            "LidarStudy_FloraWorld_Rocks",
        ):
            continue
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            if (
                not c.static_mesh
                or not c.visible
                or c.hidden_in_game
                or c.get_collision_enabled() != u.CollisionEnabled.NO_COLLISION
            ):
                continue
            mesh = c.static_mesh
            name = mesh.get_name()
            bounds = mesh.get_bounding_box()
            kind = (
                "stone"
                if label.endswith("Rocks")
                else "fern"
                if label.endswith("FernCover")
                else "grass"
                if "Grass" in name
                else "shrub"
            )
            step = {"stone": 2150, "shrub": 1750, "fern": 1170, "grass": 1250}[kind]
            rng = random.Random(label + "/" + name)
            count = c.get_instance_count()
            inventory[kind] += count
            edits = 0
            last = None
            for i in range(count):
                if i in protected[label, c.get_name()]:
                    continue
                tf = c.get_instance_transform(i, True)
                p = tf.translation
                f = sample(p.x, p.y)
                if f[0] < 142:
                    continue
                ix, iy = math.floor(p.x / step), math.floor(p.y / step)
                sites = [
                    anchor(ix + dx, iy + dy, step, kind) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                ]
                x, y, score, ang = max(
                    sites, key=lambda v: v[2] - math.hypot(v[0] - p.x, v[1] - p.y) * 0.039
                )
                if score < (73 if kind == "stone" else 85):
                    continue
                # Shelves follow contours, with ferns and grass spreading in looser colonies.
                if kind == "stone":
                    dx = ground.height(x + 90, y) - ground.height(x - 90, y)
                    dy = ground.height(x, y + 90) - ground.height(x, y - 90)
                    if math.hypot(dx, dy) > 8:
                        ang = math.atan2(dx, -dy)
                along = rng.uniform(-0.40, 0.40) * step
                across = rng.gauss(0, 0.09) * step
                x += along * math.cos(ang) - across * math.sin(ang)
                y += along * math.sin(ang) + across * math.cos(ang)
                feet = sample(x, y)
                if feet[0] < 240 or suitability(feet, kind) < 60:
                    continue
                if (
                    river.covers(u.Vector2D(x, y))
                    and ground.height(x, y) < river.surface_cm_at(u.Vector2D(x, y)) + 12
                ):
                    continue
                sc = tf.scale3d
                growth = rng.uniform(0.86, 1.45)
                if kind == "stone":
                    growth = min(growth * 1.32, 620 / max(1, (bounds.max.x - bounds.min.x) * sc.x))
                    sc = u.Vector(
                        sc.x * growth,
                        sc.y * growth * rng.uniform(0.64, 0.9),
                        sc.z * growth * rng.uniform(0.43, 0.74),
                    )
                else:
                    sc = sc * growth
                radius = min(
                    650,
                    max((bounds.max.x - bounds.min.x) * sc.x, (bounds.max.y - bounds.min.y) * sc.y)
                    * 0.55,
                )
                if any(
                    sample(x + ax * radius, y + ay * radius)[0] < 178
                    for ax, ay in ((1, 0), (-1, 0), (0, 1), (0, -1))
                ):
                    continue
                if math.hypot(x - bend["hero"][0], y - bend["hero"][1]) < radius + 180:
                    continue
                yaw = (
                    math.degrees(ang) + rng.uniform(-17, 17)
                    if kind == "stone"
                    else rng.uniform(-180, 180)
                )
                nt = ground.seat(
                    mesh,
                    u.Transform(location=u.Vector(x, y, 0), rotation=u.Rotator(yaw=yaw), scale=sc),
                    kind != "stone",
                )
                if kind == "stone":
                    nt.translation -= u.Vector(0, 0, (bounds.max.z - bounds.min.z) * sc.z * 0.19)
                if not edits:
                    a.modify()
                    c.modify()
                assert c.update_instance_transform(i, nt, True, False, True)
                if edits == 0:
                    checks.append([label, c.get_name(), i, list(nt.translation.to_tuple()), count])
                edits += 1
                last = (i, nt)
            if last:
                assert c.update_instance_transform(last[0], last[1], True, True, True)
            moved[kind] += edits
    assert all(moved[k] > 10 for k in ("fern", "grass", "shrub", "stone")), moved
    return dict(inventory=inventory, moved=moved, samples=checks)


def run(root, out, rows, levels, stage):
    (grass,) = [
        a for a in rows if isinstance(a, u.GTMixedGroundDetails) and a.generate_around_player
    ]
    (stamps,) = [a for a in rows if isinstance(a, u.GTForestGroundDetails)]
    land = next(a for a in rows if isinstance(a, u.Landscape))
    author = next(a for a in rows if isinstance(a, u.GTProceduralGround))
    mud = next(a for a in rows if isinstance(a, u.GTMudRunnerVisual))
    field = json.loads((out / "field.json").read_text())
    marker = out / ("placement.json" if REVISION == 1 else f"placement-v{REVISION}.json")
    installed = [str(tag) for tag in grass.tags if str(tag).startswith("GT_WoodlandHabitats_v")]
    if installed and installed != [TAG]:
        raise RuntimeError(
            f"{installed} is already installed on this map. Start a new revision on its pre-habitat backup to preserve the original distribution."
        )
    if stage in ("Verify", "Surface", "GroundPaint") or grass.actor_has_tag(TAG):
        rec = json.loads(marker.read_text())
        assert grass.actor_has_tag(TAG) and str(author.output_digest) == rec["ground_digest"]
        atlas = u.load_asset(DEST + "/T_WoodlandHabitat")
        baked_field = hashlib.sha256((out / "T_WoodlandHabitat.png").read_bytes()).hexdigest()
        if E.get_metadata_tag(atlas, "HabitatBake") != baked_field:
            raise ValueError(
                "Habitat geography has changed. Install a new revision from the pre-habitat map so the plant groups and the floor move together."
            )
        if stage == "Surface":
            import_texture(out, "T_WoodlandLitter", False)
            import_texture(out, "T_WoodlandPaint", True)
        assert land.landscape_material.get_path_name() == rec["terrain"]
        assert (
            mud.material.get_path_name() == rec["detail"]
            and author.relief_material.get_path_name() == rec["relief"]
        )
        assert all(
            grass.get_editor_property(k).get_path_name().startswith(DEST + "/")
            for k in ("grass_material", "rank_material", "distant_pasture_material")
        )
        named = {a.get_actor_label(): a for a in rows}
        for label, name, i, pos, count in rec["plants"]["samples"]:
            c = next(
                c
                for c in named[label].get_components_by_class(u.InstancedStaticMeshComponent)
                if c.get_name() == name
            )
            assert (
                c.get_instance_count() == count
                and math.dist(c.get_instance_transform(i, True).translation.to_tuple(), pos) < 0.25
            )
        if stage == "Surface":
            # Allow rapid changes to floor pigments and grass without clustering the same plants twice.
            assert grass.import_visual_grass_density(
                str(out / "grass-density.bin"), u.Vector2D(*field["origin"]), field["span"]
            )
            rec["grass_probes"] = [
                [x, y, grass.visual_grass_density_at(u.Vector2D(x, y))]
                for x, y, _ in rec["grass_probes"]
            ]
        materials = [land.landscape_material, author.relief_material, mud.material]
        materials.extend(
            grass.get_editor_property(k)
            for k in ("grass_material", "rank_material", "distant_pasture_material")
        )
        for mat in set(materials):
            update_surface_code(mat, apply=stage in ("Surface", "GroundPaint"))
        stones = bind_rocks(rows, DEST, atlas, field, apply=stage == "Surface")
        understory = bind_understory(rows, DEST, apply=stage == "Surface")
        if stage == "Surface":
            rec["stone_material_instances"] = stones
            rec["understory"] = understory
        else:
            assert stones == rec["stone_material_instances"]
            assert understory == rec["understory"]
        for x, y, expected in rec["grass_probes"]:
            assert abs(grass.visual_grass_density_at(u.Vector2D(x, y)) - expected) < 0.002
        if stage == "Surface":
            assert levels.save_current_level()
            temp = marker.with_suffix(".tmp")
            temp.write_text(json.dumps(rec, indent=2))
            temp.replace(marker)
        return dict(saved=True, field=field, moved=rec["plants"]["moved"], backup=rec["backup"])
    assert stage == "Install"
    E.make_directory(DEST)
    atlas = import_texture(out, "T_WoodlandHabitat", True)
    litter = import_texture(out, "T_WoodlandLitter", False)
    import_texture(out, "T_WoodlandPaint", True)
    mapping = {}

    def bind(obj, prop, role):
        old = obj.get_editor_property(prop)
        if old not in mapping:
            mapping[old] = material(old, role, atlas, litter, field)
        obj.modify()
        obj.set_editor_property(prop, mapping[old])
        return mapping[old].get_path_name()

    digest = str(author.output_digest)
    terrain = bind(land, "landscape_material", "Terrain")
    detail = bind(mud, "material", "Detail")
    relief = bind(author, "relief_material", "Relief")
    for k, role in [
        ("grass_material", "Grass"),
        ("rank_material", "Verge"),
        ("distant_pasture_material", "FarGrass"),
    ]:
        bind(grass, k, role)
    for a in rows:
        if isinstance(a, u.LandscapeProxy) and a.landscape_material in mapping:
            a.modify()
            a.set_editor_property("landscape_material", mapping[a.landscape_material])
        if not isinstance(a, (u.GTRoadReliefTile, u.GTMudRunnerVisual, u.GTMixedGroundDetails)):
            continue
        for c in a.get_components_by_class(u.PrimitiveComponent):
            for j, m in enumerate(c.get_materials()):
                if m and m in mapping:
                    c.modify()
                    c.set_material(j, mapping[m])
    assert grass.import_visual_grass_density(
        str(out / "grass-density.bin"), u.Vector2D(*field["origin"]), field["span"]
    )
    assert stamps.import_coverage(str(out / "moss-density.bin"))
    bend = json.loads((root / "Saved/ForestAccessBend/build.json").read_text())
    river = next(
        a
        for a in rows
        if isinstance(a, u.GTWaterSheet) and not a.get_editor_property("mud_initial_domain")
    )
    plants = regroup(
        rows, field, (out / "habitat.rgba").read_bytes(), GroundSampler(author), river, bend
    )
    stones = bind_rocks(rows, DEST, atlas, field, apply=True)
    understory = bind_understory(rows, DEST, apply=True)
    probes = [
        [x, y, grass.visual_grass_density_at(u.Vector2D(x, y))]
        for x, y in [
            (-31222, -10774),
            (-53420, -31020),
            (-52800, -32000),
            (-64589, 6835),
            (90061, 60070),
        ]
    ]
    assert probes[0][2] > 0.98 and min(p[2] for p in probes[1:]) < 0.5
    assert str(author.output_digest) == digest
    grass.tags = [*grass.tags, u.Name(TAG)]
    rec = dict(
        terrain=terrain,
        detail=detail,
        relief=relief,
        ground_digest=digest,
        plants=plants,
        stone_material_instances=stones,
        understory=understory,
        grass_probes=probes,
        backup=os.environ["GT_HABITAT_BACKUP"],
    )
    temp = marker.with_suffix(".tmp")
    temp.write_text(json.dumps(rec, indent=2))
    temp.replace(marker)
    assert levels.save_current_level()
    return dict(saved=True, moved=plants["moved"], field=field, backup=rec["backup"])
