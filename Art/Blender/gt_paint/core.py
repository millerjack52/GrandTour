"""GT Paint core: the GT_Paint node group, the per-object materials, the bake and the FBX export.

docs/LOOK_PLAN.md stage L1, docs/VEHICLE_BUILD_SYSTEM.md section 55. Pure functions over bpy data so the headless test
(Art/Blender/tests/test_gt_paint.py) and the panel's operators run the same code.

The contract (LOOK_PLAN section 2): a bake carries paint, never light. The albedo is the painted colour only - base
colour, edge wear and scuffs, grime, an optional paint highlight - posterised to the preset's tone count, then brush
strokes one tone up or down; lighting, shadows and bands belong to Unreal (the L2 post layer). Since 2026-09-24 the
brush strokes live in a third output, T_GT_<Asset>_N (painted-dab normals from the owner's OW Painterly Normal Baker,
which GT Paint calls, never re-implements), and scuffs and albedo strokes default to 0. Every number comes
from the preset JSON, and every one of
them is the owner's to name.

Blender rules kept here: nodes are found by type, never by name; every enum value is checked against RNA (pick())
before it is assigned; the render engine is read, then assigned inside try/except TypeError.
"""
import json
import math
import os
import re
import time

import bpy
from mathutils import Matrix, Vector

GROUP_NAME = "GT_Paint"
BAKE_COLLECTION = "GT Paint Bake"
BAKE_SUFFIX = "_GTBake"
MARK = "gt_paint"            # custom property on the materials this addon owns
ID_PROP = "gt_id_colour"     # the material's base (ID) colour, linear RGBA, kept across refreshes
SOURCE_PROP = "gt_source"    # "id" or "vertex"
ADDON_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ART = r"C:\GrandTour\Art"

# The proposed starting values (docs/LOOK_PLAN.md L1), all UNMEASURED; Art/Blender/gt_paint_preset.json overrides
# every key it names. Kept here so the addon still runs when installed away from the repo without its preset file.
DEFAULT_PRESET = {
    "tones": 4,
    "grain_scale_m": 0.35,
    "grain_strength": 0.0,
    "_grain_strength": "The share of the surface in brush strokes, half light and half dark, each moving the rounded tone one step (2026-09-23; it was a shade amplitude the tone rounding swallowed). 0 since 2026-09-24: the strokes live in the normal map (the normal block).",
    "grain_stretch": 5.0,
    "wear_width_m": 0.02,
    "wear_lighten": 0.25,
    "wear_colour": "#F2EDE4",
    "wear_breakup": 0.5,
    "wear_pointiness": 0.0,
    "_wear_pointiness": "0 = wear on bevelled edges only (the Bevel node's term). Raising it adds convex pointiness, which reads mid-high across whole panels of a subsurfed, creased model (the owner's gate 2026-09-23: specks everywhere).",
    "wear_tint": 0.35,
    "_wear_tint": "The colour of the top light tone - scuffs, edge wear and, at tones 4, the light strokes: 0 = the base colour, 1 = wear_colour.",
    "scuff_scale_m": 0.3,
    "_scuff_scale_m": "The size in metres of the world-aligned noise the scuff patches are cut from.",
    "scuff_cover": 0.0,
    "_scuff_cover": "The share of surface a scuff patch may cover where its weight is 1: the bevelled edges and the base of the Apply Style selection; the weight falls linearly to 0 at the selection's top. 0 since 2026-09-24 (the owner: not heaps of wear marks / scuffs); edge wear stays.",
    "grime_strength": 0.3,
    "grime_distance_m": 0.3,
    "highlight": 0.0,
    "highlight_up": 0.7,
    "roughness": 0.85,
    "roughness_wear": 0.6,
    "roughness_grime": 0.95,
    "base_source": "auto",
    "palette": {"body": "#D9772E", "trim": "#B8B2A6", "tyre": "#2C2C30", "interior": "#46423C"},
    "name_rules": [["wheel", "tyre"], ["interior", "interior"], ["bumper", "trim"], ["pillar", "trim"], ["", "body"]],
    "bake_size": 1024,
    "bake_samples": 1,
    "bake_margin_px": 8,
    "uv_angle_deg": 66.0,
    "uv_island_margin": 0.01,
    "ao_samples": 16,
    "bevel_samples": 8,
    "export_yaw_deg": 90.0,
    "normal_enable": True,
    "_normal_enable": "Bake also writes T_GT_<Asset>_N.png (DirectX tangent normal): painted brush dabs from the owner's OW Painterly Normal Baker, so the lighting paints the lights and darks (2026-09-24). false = no _N.",
    "normal_baker_path": "",
    "_normal_baker_path": "The extension's folder when this Blender has not enabled it; empty = %APPDATA%\\Blender Foundation\\Blender\\5.1\\extensions\\user_default\\ow_painterly_normal_baker.",
    "normal_strength": 0.5,
    "_normal_strength": "How strongly the painted dabs tilt the shading: the preview's Normal Map Strength, 0 = flat, 1 = as baked; Art/Unreal/setup_look_l1.py's NORMAL_STRENGTH mirrors it by hand. 0.7 proposed 2026-09-24 (the owner: 'reduce colour jitter'), unmeasured.",
    "normal": {
        "_note": "The baker's own settings (its panel), set for the Bake and put back afterwards. The numbers are the baker's own defaults, PROPOSED and UNMEASURED for this use.",
        "dab_length_cm": 55.0,
        "_dab_length_cm": "One dab's length in world cm (the main pass).",
        "length_min": 0.7,
        "_length_min": "Each dab's length is dab_length_cm x a random factor from length_min to length_max.",
        "length_max": 2.4,
        "_length_max": "See length_min.",
        "aspect": 2.0,
        "_aspect": "Dab length / width.",
        "coverage": 2.0,
        "_coverage": "How many times the dabs over-cover the surface (the baker caps a pass at 40,000 dabs, so a big asset gets fewer).",
        "normal_jitter": 8.0,
        "_normal_jitter": "The painter's hand: degrees each dab's flat normal wobbles.",
        "rot_jitter": 20.0,
        "_rot_jitter": "Degrees each dab's direction wobbles off its flow direction.",
        "detail_enable": True,
        "_detail_enable": "A second pass of small dabs weighted to the edges.",
        "detail_length_cm": 1.8,
        "_detail_length_cm": "The detail pass's dab length in cm.",
        "seed": 7,
        "_seed": "The dab placement's random seed.",
        "brush_path": "",
        "_brush_path": "The dab's alpha image; empty = the baker's bundled oil_knife.png."
    },
}

# The spread (standard deviation) of Blender 5.1's Noise Texture Fac around 0.5 at roughness 0.55, by detail,
# MEASURED 2026-09-23 on two tilted 40 m planes baked to 1024 float images (means 0.500; the 5 and 95 % quantiles
# within 0.002 of a normal's with these spreads). The spread depends on the slice: a plane on the noise's integer
# lattice (world z = 0 unscaled) reads 0.0793 / 0.0735 / 0.0706, a flat slice at z 0.123 reads 0.0867 / 0.0803 /
# 0.0770, so a single flat face's cover can read about 0.8-1.2 x the asked one. Graph.uniform() turns a Fac into a
# ~uniform 0..1 with it, so a cover (a share of surface) becomes a plain threshold.
NOISE_SIGMA = {2: 0.0843, 3: 0.0781, 4: 0.0750}
# Ragged edges: the threshold is moved by +-RAGGED x the cover by a second, finer noise (made uniform too), which
# keeps the covered share as asked. The warp noises run WARP_FREQ times finer than the noise they cut; the offsets
# only decorrelate noises sampled at the same origin. Strokes are laid on walls only: full cover where the normal's
# |z| is under WALL_FULL, none over WALL_NONE (a level drag has no direction on a roof; the first judge render showed
# round blobs there). Constants, not preset keys: proposed, unmeasured.
RAGGED = 0.5
WALL_FULL = 0.6
WALL_NONE = 0.8
WARP_FREQ = 4.0
SCUFF_OFFSET = (37.1, 11.3, 23.7)
WARP_OFFSET = (-19.4, 53.9, 7.2)

# The FBX settings of Art/Blender/export_rangerover.py (FBX_COMMON), so a painted prop comes into Unreal exactly as
# the car's panels do: centimetres, +X front, Z up.
FBX_SETTINGS = dict(axis_forward='-Z', axis_up='Y', global_scale=1.0, apply_unit_scale=True,
                    apply_scale_options='FBX_SCALE_NONE', bake_space_transform=False,
                    use_mesh_modifiers=True, mesh_smooth_type='FACE', use_tspace=False,
                    add_leaf_bones=False, use_armature_deform_only=True, bake_anim=False,
                    path_mode='AUTO', embed_textures=False, use_custom_props=False,
                    use_selection=True)


class GTPaintError(Exception):
    pass


# ---- small helpers ---------------------------------------------------------------------------------------------

def enum_ids(owner, prop):
    """The identifiers RNA lists for an enum property of a struct instance, a type or an operator's rna type."""
    rna = owner.bl_rna if hasattr(owner, "bl_rna") else owner
    return [i.identifier for i in rna.properties[prop].enum_items]


def pick(owner, prop, *wanted):
    ids = enum_ids(owner, prop)
    for w in wanted:
        if w in ids:
            return w
    raise GTPaintError("%s.%s: none of %s in RNA's %s" % (getattr(owner, "bl_idname", owner), prop, wanted, ids))


def set_enum(owner, prop, *wanted):
    setattr(owner, prop, pick(owner, prop, *wanted))


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_linear(value):
    """'#RRGGBB' (sRGB, what a colour picker shows) -> linear RGBA for a Blender colour socket."""
    if isinstance(value, (list, tuple)):
        rgb = [float(v) for v in value[:3]]
        return (rgb[0], rgb[1], rgb[2], 1.0)
    h = str(value).strip().lstrip("#")
    if len(h) != 6:
        raise GTPaintError("colour %r is not #RRGGBB" % (value,))
    rgb = [srgb_to_linear(int(h[i:i + 2], 16) / 255.0) for i in (0, 2, 4)]
    return (rgb[0], rgb[1], rgb[2], 1.0)


def clean_name(name):
    """An asset name Unreal and file systems take: 'rear bumper.001' -> 'RearBumper001'."""
    parts = [p for p in re.split(r"[^A-Za-z0-9]+", name) if p]
    return "".join(p[0].upper() + p[1:] for p in parts) or "Asset"


def default_preset_path():
    for path in (os.path.join(os.path.dirname(ADDON_DIR), "gt_paint_preset.json"),
                 os.path.join(REPO_ART, "Blender", "gt_paint_preset.json")):
        if os.path.isfile(path):
            return path
    return ""


def default_export_dir():
    for path in (os.path.join(os.path.dirname(os.path.dirname(ADDON_DIR)), "Export"),
                 os.path.join(REPO_ART, "Export")):
        if os.path.isdir(path):
            return path
    return bpy.path.abspath("//GT_Export")


def load_preset(path=""):
    """(preset dict, where it came from). Unknown keys are kept (the owner's notes), missing keys take the defaults."""
    preset = json.loads(json.dumps(DEFAULT_PRESET))
    path = bpy.path.abspath(path) if path else default_preset_path()
    if not path or not os.path.isfile(path):
        return preset, "built-in defaults (no preset file)"
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    for key, value in data.items():
        if key.startswith("_"):
            continue
        if key == "normal" and isinstance(value, dict):
            preset[key].update(value)    # a partial normal block keeps the other defaults
        else:
            preset[key] = value
    return preset, path


def mesh_objects(objects):
    """The selection as paintable meshes: the addon's own bake copies are never a source."""
    return [o for o in objects if o.type == 'MESH' and not o.name.endswith(BAKE_SUFFIX)
            and BAKE_COLLECTION not in {c.name for c in o.users_collection}]


def sock(sockets, key):
    for s in sockets:
        if s.identifier == key:
            return s
    for s in sockets:
        if s.name == key and getattr(s, "enabled", True):
            return s
    raise GTPaintError("no socket %r in %s" % (key, [s.identifier for s in sockets]))


# ---- the node group --------------------------------------------------------------------------------------------

GROUP_INPUTS = [
    # name, socket type, default, preset key (None = per material)
    ("Base Colour", "NodeSocketColor", (0.8, 0.8, 0.8, 1.0), None),
    ("Vertex Colour", "NodeSocketColor", (0.8, 0.8, 0.8, 1.0), None),
    ("Use Vertex Colour", "NodeSocketFloat", 0.0, None),
    ("Tones", "NodeSocketFloat", 4.0, "tones"),
    ("Grain Scale", "NodeSocketFloat", 0.35, "grain_scale_m"),
    ("Grain Strength", "NodeSocketFloat", 0.15, "grain_strength"),
    ("Grain Stretch", "NodeSocketFloat", 5.0, "grain_stretch"),
    ("Wear Width", "NodeSocketFloat", 0.02, "wear_width_m"),
    ("Wear Lighten", "NodeSocketFloat", 0.25, "wear_lighten"),
    ("Wear Colour", "NodeSocketColor", (0.89, 0.85, 0.78, 1.0), "wear_colour"),
    ("Wear Breakup", "NodeSocketFloat", 0.5, "wear_breakup"),
    ("Wear Pointiness", "NodeSocketFloat", 0.0, "wear_pointiness"),
    ("Wear Tint", "NodeSocketFloat", 0.35, "wear_tint"),
    ("Scuff Scale", "NodeSocketFloat", 0.3, "scuff_scale_m"),
    ("Scuff Cover", "NodeSocketFloat", 0.05, "scuff_cover"),
    ("Scuff Low", "NodeSocketFloat", 0.0, None),     # world Z (m) of the Apply Style selection's base
    ("Scuff High", "NodeSocketFloat", 1.0, None),    # and of its top: set per material by apply_style
    ("Grime Strength", "NodeSocketFloat", 0.3, "grime_strength"),
    ("Grime Distance", "NodeSocketFloat", 0.3, "grime_distance_m"),
    ("Highlight", "NodeSocketFloat", 0.0, "highlight"),
    ("Highlight Up", "NodeSocketFloat", 0.7, "highlight_up"),
    ("Roughness", "NodeSocketFloat", 0.85, "roughness"),
    ("Roughness Wear", "NodeSocketFloat", 0.6, "roughness_wear"),
    ("Roughness Grime", "NodeSocketFloat", 0.95, "roughness_grime"),
]
GROUP_OUTPUTS = [("Albedo", "NodeSocketColor"), ("Wear", "NodeSocketFloat"), ("Grime", "NodeSocketFloat"),
                 ("Roughness", "NodeSocketFloat"), ("Mask", "NodeSocketColor")]


class Graph:
    """A few lines per node: math(), vmath(), map_range() return output sockets; feed() takes a socket or a number."""

    def __init__(self, tree):
        self.tree = tree
        self.count = 0

    def new(self, idname, **enums):
        node = self.tree.nodes.new(idname)
        node.location = (200 * (self.count // 6), -170 * (self.count % 6))
        self.count += 1
        for prop, wanted in enums.items():
            set_enum(node, prop, *(wanted if isinstance(wanted, tuple) else (wanted,)))
        return node

    def feed(self, socket, value):
        if isinstance(value, bpy.types.NodeSocket):
            self.tree.links.new(value, socket)
        elif isinstance(value, (tuple, list)):
            socket.default_value = value
        else:
            socket.default_value = float(value)

    def math(self, op, a, b=None, clamp=False):
        node = self.new("ShaderNodeMath", operation=op)
        node.use_clamp = clamp
        self.feed(sock(node.inputs, "Value"), a)
        if b is not None:
            self.feed(sock(node.inputs, "Value_001"), b)
        return sock(node.outputs, "Value")

    def vmath(self, op, a, b=None, scale=None, out="Vector"):
        node = self.new("ShaderNodeVectorMath", operation=op)
        self.feed(sock(node.inputs, "Vector"), a)
        if b is not None:
            self.feed(sock(node.inputs, "Vector_001"), b)
        if scale is not None:
            self.feed(sock(node.inputs, "Scale"), scale)
        return sock(node.outputs, out)

    def map_range(self, value, from_min, from_max, to_min=0.0, to_max=1.0):
        node = self.new("ShaderNodeMapRange", data_type="FLOAT", interpolation_type="LINEAR")
        node.clamp = True
        self.feed(sock(node.inputs, "Value"), value)
        self.feed(sock(node.inputs, "From Min"), from_min)
        self.feed(sock(node.inputs, "From Max"), from_max)
        self.feed(sock(node.inputs, "To Min"), to_min)
        self.feed(sock(node.inputs, "To Max"), to_max)
        return sock(node.outputs, "Result")

    def noise(self, vector, detail):
        node = self.new("ShaderNodeTexNoise", noise_dimensions="3D")
        self.feed(sock(node.inputs, "Vector"), vector)
        self.feed(sock(node.inputs, "Scale"), 1.0)
        self.feed(sock(node.inputs, "Detail"), detail)
        self.feed(sock(node.inputs, "Roughness"), 0.55)
        return sock(node.outputs, "Fac")

    def uniform(self, fac, detail):
        """A noise Fac made ~uniform over 0..1: z = (Fac - 0.5) / NOISE_SIGMA[detail], then the normal CDF by
        Bowling et al.'s logistic fit 1 / (1 + exp(-(1.5976 z + 0.070566 z^3))) (error under 0.0002)."""
        z = self.math("DIVIDE", self.math("SUBTRACT", fac, 0.5), NOISE_SIGMA[int(detail)])
        poly = self.math("MULTIPLY", z, self.math("ADD", 1.5976, self.math("MULTIPLY", 0.070566, self.math("MULTIPLY", z, z))))
        return self.math("DIVIDE", 1.0, self.math("ADD", 1.0, self.math("EXPONENT", self.math("MULTIPLY", poly, -1.0))))

    def cut(self, u, warp, cover, high=True):
        """1 where the uniform u, its threshold moved by warp (-1..1) x RAGGED x cover, lies in the top (high) or
        bottom share `cover` of 0..1, else 0: a patch covering that share with ragged edges."""
        ut = self.math("ADD", u, self.math("MULTIPLY", warp, self.math("MULTIPLY", cover, RAGGED)))
        if high:
            return self.math("GREATER_THAN", ut, self.math("SUBTRACT", 1.0, cover))
        return self.math("LESS_THAN", ut, cover)

    def warp(self, vector, offset):
        """-1..1, ~uniform: a noise WARP_FREQ times finer than `vector`'s, for ragged edges."""
        n = self.noise(self.vmath("ADD", self.vmath("SCALE", vector, scale=WARP_FREQ), offset), 2.0)
        return self.math("SUBTRACT", self.math("MULTIPLY", self.uniform(n, 2), 2.0), 1.0)

    def mix_colour(self, factor, a, b):
        node = self.new("ShaderNodeMix", data_type="RGBA", blend_type="MIX")
        node.clamp_factor = True
        self.feed(sock(node.inputs, "Factor_Float"), factor)
        self.feed(sock(node.inputs, "A_Color"), a)
        self.feed(sock(node.inputs, "B_Color"), b)
        return sock(node.outputs, "Result_Color")


def build_group(preset):
    """Creates or rebuilds the shared GT_Paint node group: its inside always, its interface only when the socket list
    changed, so the group nodes in every other material keep their values and links (measured: recreating the
    interface on every Apply Style turned the already-styled ochre cube black)."""
    ng = bpy.data.node_groups.get(GROUP_NAME)
    if ng is None or ng.bl_idname != "ShaderNodeTree":
        ng = bpy.data.node_groups.new(GROUP_NAME, "ShaderNodeTree")
    ng.nodes.clear()
    socket_rna = bpy.types.NodeTreeInterfaceSocket
    in_id = pick(socket_rna, "in_out", "INPUT")
    out_id = pick(socket_rna, "in_out", "OUTPUT")
    wanted = [(n, in_id, t) for n, t, _d, _k in GROUP_INPUTS] + [(n, out_id, t) for n, t in GROUP_OUTPUTS]
    have = [(i.name, i.in_out, i.socket_type) for i in ng.interface.items_tree if i.item_type == 'SOCKET']
    if have != wanted:
        # Only when the interface itself changed (a new addon version): recreating it resets every group node's
        # inputs in every material, so their values are kept by name and put back. Links into the group (a colour
        # attribute) go with the old sockets: Apply Style on those objects again rebuilds them.
        saved = {}
        for m in bpy.data.materials:
            if is_gt(m) and m.node_tree is not None:
                for n in m.node_tree.nodes:
                    if n.type == "GROUP" and n.node_tree is ng:
                        saved[(m.name, n.name)] = {x.name: x.default_value[:] if hasattr(x.default_value, "__len__")
                                                   else x.default_value for x in n.inputs if hasattr(x, "default_value")}
        ng.interface.clear()
        for name, stype, default, key in GROUP_INPUTS:
            ng.interface.new_socket(name=name, in_out=in_id, socket_type=stype)
        for name, stype in GROUP_OUTPUTS:
            ng.interface.new_socket(name=name, in_out=out_id, socket_type=stype)
        for (mat_name, node_name), values in saved.items():
            node = bpy.data.materials[mat_name].node_tree.nodes.get(node_name)
            for x in (node.inputs if node is not None else []):
                if x.name in values and hasattr(x, "default_value"):
                    try:
                        x.default_value = values[x.name]
                    except (TypeError, ValueError):
                        pass
    items = {i.name: i for i in ng.interface.items_tree if i.item_type == 'SOCKET' and i.in_out == in_id}
    for name, stype, default, key in GROUP_INPUTS:
        if key is not None:
            value = preset.get(key, default)
            default = hex_linear(value) if stype == "NodeSocketColor" else float(value)
        items[name].default_value = default

    g = Graph(ng)
    gin = g.new("NodeGroupInput")
    gout = g.new("NodeGroupOutput")
    I = lambda name: sock(gin.outputs, name)
    geo = g.new("ShaderNodeNewGeometry")
    pos, normal = sock(geo.outputs, "Position"), sock(geo.outputs, "Normal")

    # Brush strokes: world-aligned noise stretched along Z, so its features run level (ref_01's horizontal drags).
    # Section 55's follow-up: it no longer shades v before the rounding (its 0.15 never crossed a tone step of about
    # 0.28 and rounded away); it is cut into light strokes (its top Grain Strength / 2 of the walls) and dark strokes
    # (its bottom Grain Strength / 2), which move the ROUNDED tone one step up or down, below.
    inv_scale = g.math("DIVIDE", 1.0, I("Grain Scale"))
    p1 = g.vmath("SCALE", pos, scale=inv_scale)
    stretch = g.new("ShaderNodeCombineXYZ")
    g.feed(sock(stretch.inputs, "X"), 1.0)
    g.feed(sock(stretch.inputs, "Y"), 1.0)
    g.feed(sock(stretch.inputs, "Z"), I("Grain Stretch"))
    n1 = g.noise(g.vmath("MULTIPLY", p1, sock(stretch.outputs, "Vector")), 3.0)
    u1 = g.uniform(n1, 3)
    sep_n = g.new("ShaderNodeSeparateXYZ")
    g.feed(sock(sep_n.inputs, "Vector"), normal)
    wall = g.map_range(g.math("ABSOLUTE", sock(sep_n.outputs, "Z")), WALL_FULL, WALL_NONE, 1.0, 0.0)
    half = g.math("MULTIPLY", g.math("MULTIPLY", I("Grain Strength"), 0.5), wall)
    stroke_warp = g.warp(p1, WARP_OFFSET)
    stroke = g.math("SUBTRACT", g.cut(u1, stroke_warp, half, True), g.cut(u1, stroke_warp, half, False))

    # Edge wear: the Bevel node's rounded normal against the shading normal (and convex pointiness x Wear Pointiness,
    # 0 by default: on a subsurfed model it reads across whole panels); broken into chips by a second noise.
    bevel = g.new("ShaderNodeBevel")
    bevel.samples = int(preset.get("bevel_samples", 8))
    g.feed(sock(bevel.inputs, "Radius"), I("Wear Width"))
    dot = g.vmath("DOT_PRODUCT", sock(bevel.outputs, "Normal"), normal, out="Value")
    edge_bevel = g.map_range(g.math("SUBTRACT", 1.0, dot), 0.01, 0.12)
    edge_point = g.math("MULTIPLY", g.map_range(sock(geo.outputs, "Pointiness"), 0.55, 0.75), I("Wear Pointiness"))
    edge = g.math("MAXIMUM", edge_bevel, edge_point)
    n2 = g.noise(g.vmath("SCALE", p1, scale=2.0), 4.0)
    chip = g.math("MULTIPLY", edge, g.math("ADD", n2, 0.5))
    wear_edge = g.map_range(chip, I("Wear Breakup"), g.math("ADD", I("Wear Breakup"), 0.2))

    # Scuffs: sparse ragged patches cut from a low-frequency world noise (Scuff Scale). Where they may fall is a
    # weight, max(edge, 1 - the height fraction within the Apply Style selection's Z bounds): the cover is Scuff
    # Cover x weight, so patches gather at the base and along bevelled edges and thin out to none at the top.
    ps = g.vmath("SCALE", pos, scale=g.math("DIVIDE", 1.0, g.math("MAXIMUM", I("Scuff Scale"), 0.001)))
    us = g.uniform(g.noise(g.vmath("ADD", ps, SCUFF_OFFSET), 2.0), 2)
    sep_pos = g.new("ShaderNodeSeparateXYZ")
    g.feed(sock(sep_pos.inputs, "Vector"), pos)
    top = g.math("MAXIMUM", I("Scuff High"), g.math("ADD", I("Scuff Low"), 0.01))
    height = g.map_range(sock(sep_pos.outputs, "Z"), I("Scuff Low"), top)
    weight = g.math("MAXIMUM", edge, g.math("SUBTRACT", 1.0, height))
    cover = g.math("MULTIPLY", I("Scuff Cover"), weight)
    scuff = g.cut(us, g.warp(ps, WARP_OFFSET), cover, True)
    wear = g.math("MAXIMUM", wear_edge, scuff)

    # Grime: the object's own ambient occlusion (only_local: the scene around a prop never paints it).
    ao = g.new("ShaderNodeAmbientOcclusion")
    ao.only_local = True
    ao.samples = int(preset.get("ao_samples", 16))
    g.feed(sock(ao.inputs, "Distance"), I("Grime Distance"))
    occl = g.map_range(g.math("SUBTRACT", 1.0, sock(ao.outputs, "AO")), 0.05, 0.45)
    grime = g.math("MULTIPLY", occl, g.math("ADD", n1, 0.5), clamp=True)

    # The optional single paint highlight: faces turned up past Highlight Up take one lighter tone.
    sep = g.new("ShaderNodeSeparateXYZ")
    g.feed(sock(sep.inputs, "Vector"), normal)
    up = g.map_range(sock(sep.outputs, "Z"), I("Highlight Up"), g.math("ADD", I("Highlight Up"), 0.05))
    high = g.math("MULTIPLY", up, I("Highlight"))

    # The shade v around 1 (the base colour), then posterised: levels 1 + k*s, k an integer, Tones levels in all,
    # spanning the darkest (grime) to the lightest (wear + highlight) the preset allows. Section 55's follow-up: the
    # dark side leaves the top two levels free (k_min >= -(Tones - 3)); the TOP level is the wear tone (wear > 0.5
    # takes it, Wear Tint of the way to Wear Colour) and the levels between the base and it are the light strokes'
    # and the highlight's. Then the strokes move k one step (never on wear, never into the wear tone), so each base
    # colour still paints at most Tones colours.
    v = g.math("ADD", 1.0, g.math("MULTIPLY", I("Wear Lighten"), wear))
    v = g.math("ADD", g.math("SUBTRACT", v, g.math("MULTIPLY", I("Grime Strength"), grime)), high)
    lo = g.math("SUBTRACT", 1.0, I("Grime Strength"))
    hi = g.math("ADD", g.math("ADD", 1.0, I("Wear Lighten")), I("Highlight"))
    steps = g.math("MAXIMUM", g.math("SUBTRACT", g.math("ROUND", I("Tones")), 1.0), 0.0)
    s = g.math("DIVIDE", g.math("SUBTRACT", hi, lo), g.math("MAXIMUM", steps, 1.0))
    dark_room = g.math("MAXIMUM", g.math("SUBTRACT", steps, 2.0), 0.0)
    k_min = g.math("MULTIPLY", g.math("MINIMUM", g.math("ROUND", g.math("DIVIDE", g.math("SUBTRACT", 1.0, lo), s)), dark_room), -1.0)
    k_max = g.math("ADD", k_min, steps)
    k_top = g.math("MAXIMUM", g.math("SUBTRACT", k_max, 1.0), k_min)   # the highest level that is not the wear tone
    dry = g.math("LESS_THAN", wear, 0.5)
    k = g.math("ROUND", g.math("DIVIDE", g.math("SUBTRACT", v, 1.0), s))
    k = g.math("ADD", k, g.math("MULTIPLY", stroke, dry))
    k = g.math("MINIMUM", g.math("MAXIMUM", k, k_min), k_top)
    k = g.math("ADD", k, g.math("MULTIPLY", g.math("SUBTRACT", 1.0, dry), g.math("SUBTRACT", k_max, k)))
    vq = g.math("ADD", 1.0, g.math("MULTIPLY", k, s))
    dark = g.math("MINIMUM", vq, 1.0)
    # The light levels step toward Wear Colour in equal parts; the top one (the wear tone) is Wear Tint of the way.
    light = g.math("MULTIPLY", I("Wear Tint"), g.math("DIVIDE", g.math("MAXIMUM", k, 0.0), g.math("MAXIMUM", k_max, 1.0)), clamp=True)

    base = g.mix_colour(I("Use Vertex Colour"), I("Base Colour"), I("Vertex Colour"))
    albedo = g.mix_colour(light, g.vmath("SCALE", base, scale=dark), I("Wear Colour"))

    rough = g.math("ADD", I("Roughness"), g.math("MULTIPLY", g.math("SUBTRACT", I("Roughness Wear"), I("Roughness")), wear))
    rough = g.math("ADD", rough, g.math("MULTIPLY", g.math("SUBTRACT", I("Roughness Grime"), I("Roughness")), grime), clamp=True)

    mask = g.new("ShaderNodeCombineColor", mode="RGB")
    g.feed(sock(mask.inputs, "Red"), wear)
    g.feed(sock(mask.inputs, "Green"), grime)
    g.feed(sock(mask.inputs, "Blue"), rough)

    g.feed(sock(gout.inputs, "Albedo"), albedo)
    g.feed(sock(gout.inputs, "Wear"), wear)
    g.feed(sock(gout.inputs, "Grime"), grime)
    g.feed(sock(gout.inputs, "Roughness"), rough)
    g.feed(sock(gout.inputs, "Mask"), sock(mask.outputs, "Color"))
    gin.location = (-400, 0)
    gout.location = (200 * (g.count // 6 + 1), 0)
    return ng


# ---- materials -------------------------------------------------------------------------------------------------

def is_gt(material):
    return material is not None and bool(material.get(MARK, False))


def id_colour_of(material):
    """The owner's flat colour on a material that is not ours: its Principled BSDF's base colour, else its viewport
    colour. None when there is no material."""
    if material is None:
        return None
    tree = getattr(material, "node_tree", None)
    if tree is not None:
        bsdf = next((n for n in tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf is not None:
            base = sock(bsdf.inputs, "Base Color")
            if not base.is_linked:
                return tuple(base.default_value)
    return tuple(material.diffuse_color)


def colour_by_rules(name, preset):
    palette = preset.get("palette", {})
    lower = name.lower()
    for needle, key in preset.get("name_rules", []):
        if needle.lower() in lower and key in palette:
            return hex_linear(palette[key]), key
    first = next(iter(palette.values()), "#CCCCCC")
    return hex_linear(first), "first palette entry"


def group_node_of(material):
    tree = material.node_tree
    return next((n for n in tree.nodes if n.type == "GROUP" and n.node_tree is not None and n.node_tree.name == GROUP_NAME), None)


def build_material(material, ob, id_colour, preset, heights=None):
    """(Re)builds one GT material's nodes: GT_Paint -> Principled BSDF (the preview) -> output, and an unlinked
    Emission the bake links in. The ID colour, the vertex-colour choice and the scuff height bounds (heights = world
    Z of the Apply Style selection's base and top) ride on the group node's inputs."""
    if getattr(material, "node_tree", None) is None and hasattr(material, "use_nodes"):
        material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    g = Graph(tree)
    group = g.new("ShaderNodeGroup")
    group.node_tree = bpy.data.node_groups[GROUP_NAME]
    for name, stype, default, key in GROUP_INPUTS:
        if key is None:
            continue
        value = preset.get(key, default)
        g.feed(sock(group.inputs, name), hex_linear(value) if stype == "NodeSocketColor" else float(value))
    g.feed(sock(group.inputs, "Base Colour"), tuple(id_colour))
    if heights is not None:
        g.feed(sock(group.inputs, "Scuff Low"), heights[0])
        g.feed(sock(group.inputs, "Scuff High"), heights[1])
    source = "id"
    mode = str(preset.get("base_source", "auto")).lower()
    attrs = ob.data.color_attributes if ob is not None and ob.type == 'MESH' else None
    if attrs is not None and len(attrs) > 0 and mode in ("auto", "vertex"):
        vc = g.new("ShaderNodeVertexColor")
        vc.layer_name = attrs.active_color_name or attrs[0].name
        g.feed(sock(group.inputs, "Vertex Colour"), sock(vc.outputs, "Color"))
        g.feed(sock(group.inputs, "Use Vertex Colour"), 1.0)
        source = "vertex"
    bsdf = g.new("ShaderNodeBsdfPrincipled")
    g.feed(sock(bsdf.inputs, "Base Color"), sock(group.outputs, "Albedo"))
    g.feed(sock(bsdf.inputs, "Roughness"), sock(group.outputs, "Roughness"))
    emit = g.new("ShaderNodeEmission")
    g.feed(sock(emit.inputs, "Color"), sock(group.outputs, "Albedo"))
    g.feed(sock(emit.inputs, "Strength"), 1.0)
    out = g.new("ShaderNodeOutputMaterial")
    out.is_active_output = True
    g.feed(sock(out.inputs, "Surface"), sock(bsdf.outputs, "BSDF"))
    group.location = (0, 0)
    bsdf.location, emit.location, out.location = (300, 100), (300, -250), (600, 100)
    material[MARK] = True
    material[ID_PROP] = list(id_colour)
    material[SOURCE_PROP] = source
    material.diffuse_color = tuple(id_colour)   # the solid-mode viewport shows the ID colour
    return source


def apply_style(objects, preset, normal=None):
    """Apply Style: the shared group, then per object one GT material per slot (one slot added to an object with
    none). A material that is already ours keeps its base colour (as edited on its group node) and is rebuilt from
    the preset. normal = (the asset's _N path, the UV it was baked on) plugs the _N into every material's preview
    (normal_preview_of). Returns [(object, material, source, where the colour came from)]."""
    obs = mesh_objects(objects)
    # The colours on our own materials are read before the group is rebuilt: rebuilding its interface resets every
    # group node's inputs (measured by the test's refresh step: the ochre cube came back black).
    kept = {}
    for ob in obs:
        for slot in ob.material_slots:
            m = slot.material
            if is_gt(m) and m.name not in kept:
                node = group_node_of(m)
                kept[m.name] = tuple(sock(node.inputs, "Base Colour").default_value) if node                     else tuple(m.get(ID_PROP, (0.8, 0.8, 0.8, 1.0)))
    build_group(preset)
    # The scuffs' height bounds: the whole selection's world Z, so a model styled in one go (every part of a car) has
    # its scuffs at the car's base, in the preview and in the bake (a world-space copy) alike.
    zs = [(ob.matrix_world @ Vector(corner)).z for ob in obs for corner in ob.bound_box]
    heights = (min(zs), max(zs)) if zs else None
    done = []
    for ob in obs:
        if len(ob.material_slots) == 0:
            ob.data.materials.append(None)
        many = len(ob.material_slots) > 1
        for index, slot in enumerate(ob.material_slots):
            old = slot.material
            if is_gt(old):
                material = old
                colour = kept.get(old.name, tuple(old.get(ID_PROP, (0.8, 0.8, 0.8, 1.0))))
                where = "kept from the last Apply Style"
            else:
                colour = id_colour_of(old)
                where = "material %s" % old.name if colour is not None else ""
                if colour is None:
                    colour, key = colour_by_rules(ob.name, preset)
                    where = "palette '%s' by name" % key
                name = "GT_%s" % clean_name(ob.name) + ("_%d" % index if many else "")
                material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
                slot.material = material
            source = build_material(material, ob, colour, preset, heights)
            if normal is not None:
                attach_normal(material, normal[0], normal[1], float(preset.get("normal_strength", 1.0)))
            done.append((ob, material, source, where))
    return done


# ---- bake ------------------------------------------------------------------------------------------------------

def bake_collection(scene):
    col = bpy.data.collections.get(BAKE_COLLECTION)
    if col is None:
        col = bpy.data.collections.new(BAKE_COLLECTION)
    if col.name not in {c.name for c in scene.collection.children}:
        scene.collection.children.link(col)
    return col


def remove_object(name):
    ob = bpy.data.objects.get(name)
    if ob is None:
        return
    data = ob.data
    bpy.data.objects.remove(ob, do_unlink=True)
    if data is not None and data.users == 0:
        bpy.data.meshes.remove(data)


def select_only(context, obs):
    for o in context.view_layer.objects:
        if o.select_get():
            o.select_set(False)
    for o in obs:
        o.hide_set(False)
        o.select_set(True)
    context.view_layer.objects.active = obs[0]


def smart_project(preset):
    """GT Paint's one smart projection, over the edit-mode selection: the preset's uv_angle_deg and uv_island_margin,
    area weight 0, aspect corrected, not scaled to bounds. The bake copy of several sources and Unwrap for Paint (a
    single source with no UV, on Bake or from the panel) both call it, so both get the same projection."""
    bpy.ops.uv.smart_project(angle_limit=math.radians(float(preset.get("uv_angle_deg", 66.0))),
                             island_margin=float(preset.get("uv_island_margin", 0.01)),
                             area_weight=0.0, correct_aspect=True, scale_to_bounds=False)


def uv_area(me, name=None):
    """A UV map's summed face area in 0-1 UV space (islands two halves share count twice); the render-active map when
    no name is given; 0.0 without one."""
    import numpy as np
    layer = me.uv_layers.get(name) if name else next((u for u in me.uv_layers if u.active_render), None)
    if layer is None or len(me.polygons) == 0:
        return 0.0
    nl, nf = len(me.loops), len(me.polygons)
    uv = np.empty(nl * 2, dtype=np.float32)
    layer.data.foreach_get("uv", uv)
    uv = uv.reshape(nl, 2).astype(np.float64)
    starts = np.empty(nf, dtype=np.int64)
    counts = np.empty(nf, dtype=np.int64)
    me.polygons.foreach_get("loop_start", starts)
    me.polygons.foreach_get("loop_total", counts)
    face = np.repeat(np.arange(nf), counts)        # a face's loops are contiguous, faces in loop order
    nxt = np.arange(nl) + 1
    nxt[starts + counts - 1] = starts
    cross = uv[:, 0] * uv[nxt, 1] - uv[nxt, 0] * uv[:, 1]
    return float(np.abs(np.bincount(face, weights=cross, minlength=nf)).sum() * 0.5)


def unwrap_object(context, ob, preset, replace=False):
    """Unwrap for Paint on one mesh object. Its own mesh, modifiers NOT applied (a Mirror's two halves then share the
    islands, as the car exporter and the game see them), gets smart_project's UV in a new map GT_UV. An object that
    has a UV map is left alone unless replace, which re-projects its render-active map in place (name kept, no map
    added). Only the UV changes: the view layer's selection, active object and the object's hiding, the mesh's element
    selection and hiding, and object mode are put back. Prints and returns the log line; None when left alone."""
    import numpy as np
    me = ob.data
    if (len(me.uv_layers) and not replace) or len(me.polygons) == 0:
        return None
    if ob.library is not None or me.library is not None:
        raise GTPaintError("%s is linked from a library: it cannot take a UV map here" % ob.name)
    view_layer = context.view_layer
    active_before = view_layer.objects.active
    selected_before = [o for o in view_layer.objects if o.select_get()]
    hidden_before = ob.hide_get()
    elements = {}
    for key, seq in (("v", me.vertices), ("e", me.edges), ("f", me.polygons)):
        for attr in ("select", "hide"):
            arr = np.zeros(len(seq), dtype=bool)
            seq.foreach_get(attr, arr)
            elements[key, attr] = arr
    replaced = bool(len(me.uv_layers))
    try:
        for key, seq in (("v", me.vertices), ("e", me.edges), ("f", me.polygons)):
            if elements[key, "hide"].any():      # a hidden face would be left out of the projection
                seq.foreach_set("hide", np.zeros(len(seq), dtype=bool))
        if replaced:
            name = next((u for u in me.uv_layers if u.active_render), me.uv_layers[0]).name
        else:
            name = me.uv_layers.new(name=BAKE_UV).name
        me.uv_layers.active = me.uv_layers[name]
        me.uv_layers[name].active_render = True
        select_only(context, [ob])
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        smart_project(preset)
    finally:
        if ob.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        for key, seq in (("v", me.vertices), ("e", me.edges), ("f", me.polygons)):
            seq.foreach_set("select", elements[key, "select"])
            if elements[key, "hide"].any():
                seq.foreach_set("hide", elements[key, "hide"])
        me.update()
        for o in view_layer.objects:
            if o.select_get() != (o in selected_before):
                o.select_set(o in selected_before)
        view_layer.objects.active = active_before
        ob.hide_set(hidden_before)
    line = ("GT Paint: unwrapped %s -> UV map '%s'%s: smart project (angle %.1f deg, island margin %.3f, area weight 0, "
            "aspect corrected, not scaled to bounds) over its own %d faces, modifiers not applied; UV area %.4f"
            % (ob.name, name, " (replaced)" if replaced else " (new)", float(preset.get("uv_angle_deg", 66.0)),
               float(preset.get("uv_island_margin", 0.01)), len(me.polygons), uv_area(me, name)))
    print(line)
    return line


def uv_plan(objects):
    """The panel's UV line: what Bake does with the selection's UV."""
    if not objects:
        return "UV: select the asset's objects"
    if len(objects) > 1:
        return "UV: %d objects: Bake joins them on one fresh smart-project atlas" % len(objects)
    uvs = objects[0].data.uv_layers
    if len(uvs) == 0:
        return "UV: no UV: Bake unwraps it (smart project -> %s)" % BAKE_UV
    return "UV: Bake keeps its UV map '%s'" % next((u for u in uvs if u.active_render), uvs[0]).name


def build_bake_mesh(context, objects, asset, preset):
    """One object holding every source's evaluated mesh (modifiers applied) in world space, with the sources'
    materials. A single source with a UV map keeps it (the render-active one only); a single source with none is
    unwrapped first (unwrap_object: the SOURCE gets GT_UV, so the bake lands on a UV the object, its export and the
    game carry, and a second Bake keeps it); several sources get one fresh smart-project UV over the whole asset, so
    they share one atlas. Returns (object, how the UV was made)."""
    scene = context.scene
    col = bake_collection(scene)
    remove_object(asset + BAKE_SUFFIX)
    unwrapped = None
    if len(objects) == 1 and len(objects[0].data.uv_layers) == 0:
        unwrapped = unwrap_object(context, objects[0], preset)
    dg = context.evaluated_depsgraph_get()
    parts = []
    for ob in objects:
        ev = ob.evaluated_get(dg)
        me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
        me.transform(ob.matrix_world)
        me.materials.clear()
        for slot in ob.material_slots:
            me.materials.append(slot.material)
        part = bpy.data.objects.new(asset + "_part", me)
        col.objects.link(part)
        parts.append(part)
    keep_uv = len(parts) == 1 and len(parts[0].data.uv_layers) > 0
    if len(parts) > 1:
        joined_meshes = [p.data.name for p in parts[1:]]
        select_only(context, parts)
        with context.temp_override(active_object=parts[0], object=parts[0], selected_objects=parts,
                                   selected_editable_objects=parts):
            bpy.ops.object.join()
        for name in joined_meshes:
            me = bpy.data.meshes.get(name)
            if me is not None and me.users == 0:
                bpy.data.meshes.remove(me)
    bake_ob = parts[0]
    bake_ob.name = asset + BAKE_SUFFIX
    bake_ob.data.name = asset + BAKE_SUFFIX
    uvs = bake_ob.data.uv_layers
    if keep_uv:
        keep = next((u for u in uvs if u.active_render), uvs[0]).name
        for u in [u for u in uvs if u.name != keep]:
            uvs.remove(u)
        how = "the object's own UV map '%s'%s" % (keep, ", unwrapped by this Bake (it had none)" if unwrapped else "")
    else:
        for u in list(uvs):
            uvs.remove(u)
        uvs.new(name=BAKE_UV)
        select_only(context, [bake_ob])
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        smart_project(preset)
        bpy.ops.object.mode_set(mode='OBJECT')
        how = "smart project over %d part(s)" % len(objects)
    return bake_ob, how


def new_image(name, size, alpha, colourspace):
    old = bpy.data.images.get(name)
    if old is not None:
        bpy.data.images.remove(old)
    img = bpy.data.images.new(name, size, size, alpha=alpha, float_buffer=False)
    img.generated_color = (0.0, 0.0, 0.0, 0.0 if alpha else 1.0)
    set_enum(img.colorspace_settings, "name", colourspace)
    return img


def fill_margin(d_img, m_img, steps):
    """Grows both images' baked texels outwards by `steps` pixels, each new texel a copy of a baked (or already grown)
    neighbour - no averaging, so the margin holds only the paint's own tones. The albedo's alpha marks baked + grown
    texels. Returns the share of texels the bake itself wrote."""
    import numpy as np
    w, h = d_img.size
    d = np.empty(w * h * 4, dtype=np.float32)
    m = np.empty(w * h * 4, dtype=np.float32)
    d_img.pixels.foreach_get(d)
    m_img.pixels.foreach_get(m)
    d = d.reshape(h, w, 4)
    m = m.reshape(h, w, 4)
    covered = d[..., 3] > 0.5
    share = float(covered.mean())
    for _ in range(max(0, int(steps))):
        grown = covered.copy()
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            py = slice(max(0, -dy), h - max(0, dy))
            qy = slice(max(0, dy), h - max(0, -dy))
            px = slice(max(0, -dx), w - max(0, dx))
            qx = slice(max(0, dx), w - max(0, -dx))
            take = (~grown[py, px]) & covered[qy, qx]
            if not take.any():
                continue
            for a in (d, m):
                target = a[py, px]
                target[take] = a[qy, qx][take]
            grown[py, px] |= take
        covered = grown
    d_img.pixels.foreach_set(d.ravel())
    m_img.pixels.foreach_set(m.ravel())
    d_img.update()
    m_img.update()
    return share


def bake(context, objects, asset, out_dir, size=None, preset=None):
    """Bake: the unlit albedo to T_GT_<asset>_D (sRGB, alpha = covered texels) and the packed mask to
    T_GT_<asset>_M (Non-Color, R wear, G grime, B roughness), PNG, into out_dir/<asset>/. Cycles, EMIT, the preset's
    samples; the scene's engine and samples are put back afterwards. Returns a dict of what was done."""
    preset = preset or load_preset()[0]
    objects = mesh_objects(objects)
    if not objects:
        raise GTPaintError("select the mesh object(s) of one asset")
    for ob in objects:
        bad = [s.material.name if s.material else "(empty slot)" for s in ob.material_slots if not is_gt(s.material)]
        if bad or len(ob.material_slots) == 0:
            raise GTPaintError("%s has materials that are not GT Paint's (%s): press Apply Style first"
                               % (ob.name, ", ".join(bad) or "none"))
    size = int(size or preset.get("bake_size", 1024))
    folder = os.path.join(out_dir, asset)
    os.makedirs(folder, exist_ok=True)
    scene = context.scene
    t_start = time.perf_counter()
    bake_ob, uv_how = build_bake_mesh(context, objects, asset, preset)
    d_img = new_image("T_GT_%s_D" % asset, size, True, "sRGB")
    m_img = new_image("T_GT_%s_M" % asset, size, False, "Non-Color")

    materials = []
    for slot in bake_ob.material_slots:
        if slot.material is not None and slot.material not in materials:
            materials.append(slot.material)
    saved = []
    for mat in materials:
        tree = mat.node_tree
        group = group_node_of(mat)
        emit = next((n for n in tree.nodes if n.type == "EMISSION"), None)
        out = next((n for n in tree.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output), None) \
            or next((n for n in tree.nodes if n.type == "OUTPUT_MATERIAL"), None)
        if group is None or emit is None or out is None:
            raise GTPaintError("%s is missing its GT_Paint/Emission/Output nodes: press Apply Style again" % mat.name)
        surface = sock(out.inputs, "Surface")
        before = surface.links[0].from_socket if surface.is_linked else None
        tree.links.new(sock(emit.outputs, "Emission"), surface)
        img_node = tree.nodes.new("ShaderNodeTexImage")
        img_node.location = (600, -300)
        tree.nodes.active = img_node
        saved.append((mat, tree, group, emit, surface, before, img_node))

    render = scene.render
    engine_before = render.engine
    try:
        render.engine = "CYCLES"
    except TypeError as error:
        raise GTPaintError("Cycles is not available: %s" % error)
    samples_before = scene.cycles.samples
    scene.cycles.samples = int(preset.get("bake_samples", 1))
    dither_before = render.dither_intensity
    render.dither_intensity = 0.0   # a byte image takes the float bake through the dither: noise, not paint
    margin = int(preset.get("bake_margin_px", 8))
    bake_rna = bpy.ops.object.bake.get_rna_type()
    bake_type = pick(bake_rna, "type", "EMIT")
    # Cycles bakes with no margin and no clear: the new images start transparent black, so the albedo's alpha is 1
    # exactly on the texels the bake wrote. The margin is then grown here by copying the nearest baked texel
    # (fill_margin): Blender's own EXTEND margin averages its neighbours, which put in-between colours - tones the
    # paint never had - into every seam (measured: 2922 distinct colours on the car's 1K albedo against 14 tones).
    margin_type = pick(bake_rna, "margin_type", "EXTEND")
    times = {}
    try:
        select_only(context, [bake_ob])
        bake_ob.hide_render = False
        for label, img, output in (("D", d_img, "Albedo"), ("M", m_img, "Mask")):
            for mat, tree, group, emit, surface, before, img_node in saved:
                img_node.image = img
                tree.nodes.active = img_node
                tree.links.new(sock(group.outputs, output), sock(emit.inputs, "Color"))
            t0 = time.perf_counter()
            bpy.ops.object.bake(type=bake_type, margin=0, margin_type=margin_type, use_clear=False,
                                use_selected_to_active=False)
            times[label] = time.perf_counter() - t0
    finally:
        for mat, tree, group, emit, surface, before, img_node in saved:
            tree.links.new(sock(group.outputs, "Albedo"), sock(emit.inputs, "Color"))
            if before is not None:
                tree.links.new(before, surface)
            tree.nodes.remove(img_node)
        scene.cycles.samples = samples_before
        render.dither_intensity = dither_before
        try:
            render.engine = engine_before
        except TypeError:
            pass

    baked_share = fill_margin(d_img, m_img, margin)
    files = {}
    for label, img in (("D", d_img), ("M", m_img)):
        path = os.path.join(folder, "%s.png" % img.name)
        img.filepath_raw = path
        set_enum(img, "file_format", "PNG")
        img.save()
        files[label] = path
    uv_name = bake_ob.data.uv_layers[0].name if len(bake_ob.data.uv_layers) else BAKE_UV
    bake_ob["gt_uv"] = uv_name
    bake_ob["gt_sources"] = [ob.name for ob in objects]
    normal = None
    try:
        if preset.get("normal_enable", True):
            # The third output (follow-up 2): the owner's baker on the same copy, same UV, same size. An error here
            # fails the Bake loudly (D and M are already written).
            normal = bake_normal(context, bake_ob, asset, folder, size, preset)
            files["N"] = normal["file"]
            for mat in materials:
                attach_normal(mat, normal["file"], uv_name, float(preset.get("normal_strength", 1.0)))
    finally:
        bake_ob.hide_render = True
        bake_ob.hide_set(True)
        select_only(context, objects)
    return dict(asset=asset, bake_object=bake_ob.name, uv=uv_how, uv_name=uv_name, size=size,
                samples=int(preset.get("bake_samples", 1)),
                seconds_d=times.get("D", 0.0), seconds_m=times.get("M", 0.0),
                seconds_total=time.perf_counter() - t_start, files=files, baked_share=baked_share,
                materials=[m.name for m in materials], faces=len(bake_ob.data.polygons), normal=normal)


# ---- painted normals: the owner's OW Painterly Normal Baker ----------------------------------------------------
# Follow-up 2 (2026-09-24, VEHICLE_BUILD_SYSTEM 55): the lights and darks are painted by the lighting through a normal
# map of flat, tilted brush dabs, not by the albedo. GT Paint does NOT paint dab normals itself: it calls the owner's
# extension (id ow_painterly_normal_baker, operator pnb.generate, settings scene.pnb_settings) on the bake copy, then
# moves the extension's DirectX file T_<object>_Painterly_Normal_DX.png to <Export>/<Asset>/T_GT_<Asset>_N.png.

NORMAL_BAKER_ID = "ow_painterly_normal_baker"
NORMAL_KEYS = ("dab_length_cm", "length_min", "length_max", "aspect", "coverage", "normal_jitter", "rot_jitter",
               "detail_enable", "detail_length_cm", "seed", "brush_path")
NORMAL_TAG = "GT_N_"      # the name prefix of the preview's normal nodes (our own names, never localised)
BAKE_UV = "GT_UV"


def normal_baker_dir(preset=None):
    """The extension's folder: the preset's normal_baker_path, else the owner's Blender 5.1 user_default repo."""
    path = str((preset or {}).get("normal_baker_path", "") or "").strip()
    if path:
        return os.path.normpath(bpy.path.abspath(path))
    return os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Blender Foundation", "Blender", "5.1",
                        "extensions", "user_default", NORMAL_BAKER_ID)


def normal_baker_registered():
    return hasattr(bpy.types, "PNB_OT_generate") and hasattr(bpy.types.Scene, "pnb_settings")


def ensure_normal_baker(preset=None):
    """Makes the baker's operator available. Enabled in this Blender (the owner's install): used as it is. Not
    registered (a --factory-startup run, or the extension disabled): imported from its folder under its own id and
    registered, writing no bytecode into that folder. Missing: a GTPaintError naming the path."""
    if normal_baker_registered():
        return "registered in this Blender"
    import importlib.util
    import sys
    path = normal_baker_dir(preset)
    init = os.path.join(path, "__init__.py")
    if not os.path.isfile(init):
        raise GTPaintError("the OW Painterly Normal Baker is not enabled and not found at %s (set the preset's "
                           "normal_baker_path, or normal_enable false): no T_GT_<Asset>_N.png" % path)
    keep = sys.dont_write_bytecode
    sys.dont_write_bytecode = True    # the owner's installed extension folder is read, never written
    try:
        mod = sys.modules.get(NORMAL_BAKER_ID)
        if mod is None or os.path.normcase(os.path.abspath(getattr(mod, "__file__", "") or "")) != os.path.normcase(init):
            spec = importlib.util.spec_from_file_location(NORMAL_BAKER_ID, init, submodule_search_locations=[path])
            mod = importlib.util.module_from_spec(spec)
            sys.modules[NORMAL_BAKER_ID] = mod
            try:
                spec.loader.exec_module(mod)
            except Exception:
                sys.modules.pop(NORMAL_BAKER_ID, None)
                raise
        mod.register()
    except Exception as error:
        raise GTPaintError("the OW Painterly Normal Baker at %s did not import/register: %s" % (path, error))
    finally:
        sys.dont_write_bytecode = keep
    if not normal_baker_registered():
        raise GTPaintError("the OW Painterly Normal Baker at %s registered no pnb.generate / scene.pnb_settings" % path)
    return "imported from %s" % path


def _settings_snapshot(s):
    snap = {}
    for p in s.bl_rna.properties:
        if p.identifier in ("rna_type", "name") or p.is_readonly or p.type in ('POINTER', 'COLLECTION'):
            continue
        v = getattr(s, p.identifier)
        snap[p.identifier] = tuple(v) if (hasattr(v, "__len__") and not isinstance(v, str)) else v
    return snap


def normal_path_of(out_dir, asset):
    return os.path.join(out_dir, asset, "T_GT_%s_N.png" % asset)


def bake_normal(context, bake_ob, asset, folder, size, preset):
    """The _N step of Bake: the baker's settings from the preset's "normal" block (the scene's own values are put back
    afterwards), pnb.generate on the bake copy (its one UV), the DirectX PNG moved to folder/T_GT_<Asset>_N.png, the
    extension's other outputs (the OpenGL twin, its report) dropped with their temp folder. The extension swaps the
    object's materials during its bakes and puts them back; the faces' material indices are kept here too."""
    import shutil
    import tempfile
    import numpy as np
    how = ensure_normal_baker(preset)
    s = context.scene.pnb_settings
    snap = _settings_snapshot(s)
    block = preset.get("normal", {}) or {}
    staging = tempfile.mkdtemp(prefix="gt_paint_pnb_")
    me = bake_ob.data
    index = np.empty(len(me.polygons), dtype=np.int32)
    me.polygons.foreach_get("material_index", index)
    target = os.path.join(folder, "T_GT_%s_N.png" % asset)
    t0 = time.perf_counter()
    try:
        s.resolution = pick(s, "resolution", str(int(size)))
        for key in NORMAL_KEYS:
            if key in block:
                value = block[key]
                current = getattr(s, key)
                setattr(s, key, type(current)(value) if not isinstance(current, str) else str(value or ""))
        s.output_dir = staging
        used = {key: getattr(s, key) for key in NORMAL_KEYS}
        select_only(context, [bake_ob])
        bake_ob.hide_render = False
        try:
            with context.temp_override(active_object=bake_ob, object=bake_ob, selected_objects=[bake_ob],
                                       selected_editable_objects=[bake_ob]):
                result = bpy.ops.pnb.generate()
        except RuntimeError as error:
            raise GTPaintError("the OW Painterly Normal Baker failed on %s: %s" % (bake_ob.name, str(error).strip()))
        if result != {'FINISHED'}:
            raise GTPaintError("the OW Painterly Normal Baker returned %s on %s" % (sorted(result), bake_ob.name))
        gl = s.last_gl
        dx = gl[:-len("_GL.png")] + "_DX.png" if gl.endswith("_GL.png") else ""
        if not dx or not os.path.isfile(dx):
            raise GTPaintError("the OW Painterly Normal Baker wrote no DirectX PNG beside %r in %s" % (gl, staging))
        report = {}
        for name in os.listdir(staging):
            if name.endswith("_PainterlyReport.json"):
                with open(os.path.join(staging, name), "r", encoding="utf-8") as handle:
                    report = json.load(handle)
        os.replace(dx, target)
        source_name = os.path.basename(dx)
    finally:
        after = np.empty(len(me.polygons), dtype=np.int32)
        me.polygons.foreach_get("material_index", after)
        indices_kept = bool((after == index).all())
        if not indices_kept:
            me.polygons.foreach_set("material_index", index)
            me.update()
        for key, value in snap.items():
            try:
                setattr(s, key, value)
            except Exception:
                pass
        shutil.rmtree(staging, ignore_errors=True)
    for img in bpy.data.images:     # a preview already showing the old _N shows the new one
        if img.filepath and os.path.normcase(bpy.path.abspath(img.filepath)) == os.path.normcase(target):
            img.reload()
    return dict(file=target, bytes=os.path.getsize(target), seconds=time.perf_counter() - t0, how=how,
                source=source_name, dabs=report.get("dabs_per_pass", []), settings=used,
                material_indices="kept" if indices_kept else "put back (the extension's material swap reset them)")


def detach_normal(material):
    tree = getattr(material, "node_tree", None)
    if tree is None:
        return
    for node in [n for n in tree.nodes if n.name.startswith(NORMAL_TAG)]:
        tree.nodes.remove(node)


def attach_normal(material, path, uv_name, strength=1.0):
    """The preview's normal: UV Map (the bake's UV) -> the _N image (Non-Color) -> green flipped back (the file is
    DirectX, Blender's Normal Map node reads OpenGL) -> Normal Map, tangent space, on that UV -> the Principled BSDF's
    Normal. Replaces an earlier one. False when the material has no Principled BSDF."""
    detach_normal(material)
    tree = material.node_tree
    bsdf = next((n for n in tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        return False
    img = next((i for i in bpy.data.images if i.filepath and
                os.path.normcase(bpy.path.abspath(i.filepath)) == os.path.normcase(path)), None)
    if img is None:
        img = bpy.data.images.load(path, check_existing=False)
    set_enum(img.colorspace_settings, "name", "Non-Color")
    g = Graph(tree)
    uv = g.new("ShaderNodeUVMap")
    uv.uv_map = uv_name
    tex = g.new("ShaderNodeTexImage")
    tex.image = img
    g.feed(sock(tex.inputs, "Vector"), sock(uv.outputs, "UV"))
    sep = g.new("ShaderNodeSeparateColor", mode="RGB")
    g.feed(sock(sep.inputs, "Color"), sock(tex.outputs, "Color"))
    flip = g.new("ShaderNodeMath", operation="SUBTRACT")
    g.feed(sock(flip.inputs, "Value"), 1.0)
    g.feed(sock(flip.inputs, "Value_001"), sock(sep.outputs, "Green"))
    comb = g.new("ShaderNodeCombineColor", mode="RGB")
    g.feed(sock(comb.inputs, "Red"), sock(sep.outputs, "Red"))
    g.feed(sock(comb.inputs, "Green"), sock(flip.outputs, "Value"))
    g.feed(sock(comb.inputs, "Blue"), sock(sep.outputs, "Blue"))
    nmap = g.new("ShaderNodeNormalMap", space="TANGENT")
    nmap.uv_map = uv_name
    g.feed(sock(nmap.inputs, "Strength"), float(strength))
    g.feed(sock(nmap.inputs, "Color"), sock(comb.outputs, "Color"))
    g.feed(sock(bsdf.inputs, "Normal"), sock(nmap.outputs, "Normal"))
    for i, node in enumerate((uv, tex, sep, flip, comb, nmap)):
        node.name = NORMAL_TAG + ("UV", "Image", "Separate", "FlipGreen", "Combine", "NormalMap")[i]
        node.label = node.name
        node.location = (-900 + 150 * i, -500)
    return True


def normal_node_of(material):
    tree = getattr(material, "node_tree", None) if material is not None else None
    if tree is None:
        return None
    return next((n for n in tree.nodes if n.type == "NORMAL_MAP" and n.name.startswith(NORMAL_TAG)), None)


def normal_preview_of(asset, out_dir, preset):
    """(the asset's _N path, the UV it was baked on) when the preset has normals on and the file exists, else None.
    The UV: the bake copy's, else GT_UV (the smart-projected atlas's name)."""
    if not preset.get("normal_enable", True):
        return None
    path = normal_path_of(out_dir, asset)
    if not os.path.isfile(path):
        return None
    bake_ob = bpy.data.objects.get(asset + BAKE_SUFFIX)
    uv = str(bake_ob.get("gt_uv", "")) if bake_ob is not None else ""
    if not uv and bake_ob is not None and len(bake_ob.data.uv_layers):
        uv = bake_ob.data.uv_layers[0].name
    return path, (uv or BAKE_UV)


def normal_status(objects, asset, out_dir, preset):
    """The panel's normal line: whether an _N is loaded in the selection's GT materials and where it shows."""
    if not preset.get("normal_enable", True):
        return "Normal: off in the preset (normal_enable false)"
    path = normal_path_of(out_dir, asset)
    if not os.path.isfile(path):
        return "Normal: no %s yet (Bake writes it)" % os.path.basename(path)
    mats = {s.material for ob in objects for s in ob.material_slots if is_gt(s.material)}
    if not mats:
        return "Normal: %s on disk (select the asset's objects to see whether it is loaded)" % os.path.basename(path)
    loaded = [m for m in mats if normal_node_of(m) is not None]
    if not loaded:
        return "Normal: %s on disk, NOT loaded (Apply Style or Bake loads it)" % os.path.basename(path)
    uv = normal_node_of(loaded[0]).uv_map
    carry = [ob for ob in objects if uv in ob.data.uv_layers]
    where = "shows on the selection" if len(carry) == len(objects) else \
        "shows on %d of %d objects; the rest need Show Bake (the bake's UV %s is on its copy)" % (len(carry), len(objects), uv)
    return "Normal: %s loaded in %d of %d GT material(s), %s" % (os.path.basename(path), len(loaded), len(mats), where)


def toggle_bake_view(context, asset):
    """Show Bake: swaps the viewport between the sources and the bake copy (which carries the bake's UV, so the _N
    preview shows on it). Viewport hiding only; nothing is deleted or changed. Returns 'bake' or 'sources'."""
    bake_ob = bpy.data.objects.get(asset + BAKE_SUFFIX)
    if bake_ob is None:
        raise GTPaintError("no bake copy %s%s in this file: press Bake first" % (asset, BAKE_SUFFIX))
    srcs = [bpy.data.objects.get(n) for n in list(bake_ob.get("gt_sources", []))]
    srcs = [o for o in srcs if o is not None]
    show_bake = bake_ob.hide_get()
    bake_ob.hide_set(not show_bake)
    for o in srcs:
        o.hide_set(show_bake)
    if not show_bake and srcs:
        select_only(context, srcs)
    return "bake" if show_bake else "sources"


# ---- export ----------------------------------------------------------------------------------------------------

def fbx_settings():
    """FBX_SETTINGS, each enum value checked against the exporter's RNA."""
    rna = bpy.ops.export_scene.fbx.get_rna_type()
    out = {}
    for key, value in FBX_SETTINGS.items():
        prop = rna.properties.get(key)
        if prop is None:
            continue   # an option this exporter version does not have
        if prop.type == 'ENUM' and not getattr(prop, "is_enum_flag", False):
            value = pick(rna, key, value)
        out[key] = value
    out["object_types"] = {pick(rna, "object_types", "MESH")}
    return out


def export_fbx(context, asset, out_dir, pivot=None, preset=None):
    """Export: the last bake's mesh (the UVs the textures were baked on) as out_dir/<asset>/SM_<asset>.fbx, one
    material slot, pivot at the given object's origin, turned by the preset's export yaw (90: a model built front -Y,
    like the car, faces +X in Unreal) and written in centimetres the way export_rangerover.py writes the car."""
    preset = preset or load_preset()[0]
    bake_ob = bpy.data.objects.get(asset + BAKE_SUFFIX)
    if bake_ob is None:
        raise GTPaintError("no bake of %s in this file: press Bake first (the FBX carries the bake's UVs)" % asset)
    folder = os.path.join(out_dir, asset)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "SM_%s.fbx" % asset)
    origin = pivot.matrix_world.translation.copy() if pivot is not None else Vector((0.0, 0.0, 0.0))
    yaw = Matrix.Rotation(math.radians(float(preset.get("export_yaw_deg", 90.0))), 4, 'Z')
    me = bake_ob.data.copy()
    me.transform(Matrix.Scale(100.0, 4) @ yaw @ Matrix.Translation(-origin))
    me.materials.clear()
    slot_name = "M_%s" % asset
    slot_mat = bpy.data.materials.get(slot_name) or bpy.data.materials.new(slot_name)
    me.materials.append(slot_mat)
    for poly in me.polygons:
        poly.material_index = 0
    tmp = bpy.data.objects.new("SM_%s" % asset, me)
    bake_collection(context.scene).objects.link(tmp)
    units = context.scene.unit_settings
    before = (units.system, units.scale_length)
    try:
        # As export_rangerover.py: the copy is in cm, so scale_length 0.01 makes the exporter's unit factor 1. (The
        # display length unit is left alone: it is a dynamic enum RNA under-reports, and the FBX never reads it.)
        units.system = pick(units, "system", "METRIC")
        units.scale_length = 0.01
        select_only(context, [tmp])
        bpy.ops.export_scene.fbx(filepath=path, **fbx_settings())
    finally:
        units.system, units.scale_length = before[0], before[1]
        bpy.data.objects.remove(tmp, do_unlink=True)
        bpy.data.meshes.remove(me)
        if slot_mat.users == 0:
            bpy.data.materials.remove(slot_mat)
    xs = [v.co.x for v in bake_ob.data.vertices]
    ys = [v.co.y for v in bake_ob.data.vertices]
    zs = [v.co.z for v in bake_ob.data.vertices]
    size_m = (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)) if xs else (0, 0, 0)
    return dict(asset=asset, file=path, bytes=os.path.getsize(path), pivot=tuple(origin), size_m=size_m,
                faces=len(bake_ob.data.polygons))
