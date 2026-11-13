"""setup_m6_proving.py - The Proving Ground (L_Proving): a compact test map for water, mud and the car, built from
DA_Terrain_Proving (GTTerrain::ProvingSpec) through the same path as The Hide (setup_m6_hide.build_level).

Run with Art\\setup_m6_proving.bat (close the editor first; run setup_m6_textures, setup_m6_water, setup_m6_mud and
setup_m6_hide before it: this reuses M_GT_Landscape and M_GT_Water, it does not rebuild them). Add "reset" to the .bat to
overwrite DA_Terrain_Proving with the C++ default.
- L_Proving is created when missing, as setup_m5_legs.py makes a leg map (sun, sky light, atmosphere, fog, a player
  start) but with no AGTLegStart, checkpoints, zone or fronts: AGTRunGameMode finds no leg there and the run is free roam.
- The landscape and the dressing (ford rocks, track stones, rally posts) come from the builder as on The Hide; this
  script adds the water sheets (setup_m6_hide.place_ford_sheet), four winch posts per bog (both ends, 11 m either side
  of the middle line) and four per ford of 1.0 m or deeper (one on each bank 14 m from mid-channel and 8 m upstream,
  and one 20 m downstream of each), the player start on the pad, and logs the gaps between the stations' footprints.
Safe to re-run.
"""
import importlib.util
import math
import os

import unreal

os.environ["GT_M6_AS_MODULE"] = "1"
_here = os.environ.get("GT_ART_UNREAL") or os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("setup_m6_hide", os.path.join(_here, "setup_m6_hide.py"))
m6 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m6)

LEVEL_PATH = "/Game/GrandTour/Legs/L_Proving"
SPEC_NAME = "DA_Terrain_Proving"
DEEP_FORD_M = 1.0         # a ford this deep gets four winch posts (FGTProvingTestRunner counts them the same way)
BOG_POST_SIDE_M = 11.0    # as The Hide's bog posts
FORD_POST_ALONG_M = 14.0  # from mid-channel along the route: on the bank, above the water (the cable is 25 m)
FORD_POST_SIDE_M = 8.0    # upstream of the road's edge
FORD_POST_DOWN_M = 20.0

lib = m6.lib
eal = m6.eal
les = m6.les


def log(msg):
    unreal.log("SETUP_M6_PROVING " + msg)


def ensure_level():
    if eal.does_asset_exist(LEVEL_PATH):
        log("level exists: " + LEVEL_PATH)
        return
    if not les.new_level(LEVEL_PATH):
        raise SystemExit("could not create level " + LEVEL_PATH)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    # What setup_m5_legs.py gives a leg map, minus the leg: no floor (the landscape is the ground), no LegStart.
    sun = m6.spawn(world, unreal.DirectionalLight, "Sun", 0, 0, 1000)
    sun.set_actor_rotation(m6.rot(pitch=-40, yaw=20), False)
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_intensity(8.0)
    sky = m6.spawn(world, unreal.SkyLight, "SkyLight", 0, 0, 1000)
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
    m6.spawn(world, unreal.SkyAtmosphere, "SkyAtmosphere", 0, 0, 0)
    m6.spawn(world, unreal.ExponentialHeightFog, "HeightFog", 0, 0, 0)
    m6.spawn(world, unreal.PlayerStart, "PlayerStart", 0, 0, 120)
    if not les.save_current_level():
        raise SystemExit("could not save the new level " + LEVEL_PATH)
    log("created level " + LEVEL_PATH)


# ---- footprints and gaps ------------------------------------------------------------------------------------------
class Rect:
    """An oriented rectangle, m: centre, unit axis (along), half length, half width."""

    def __init__(self, cx, cy, yaw_deg, half_a, half_b):
        self.cx, self.cy = cx, cy
        self.ux, self.uy = math.cos(math.radians(yaw_deg)), math.sin(math.radians(yaw_deg))
        self.a, self.b = half_a, half_b

    def sd(self, x, y):
        dx, dy = x - self.cx, y - self.cy
        la = abs(dx * self.ux + dy * self.uy) - self.a
        lb = abs(-dx * self.uy + dy * self.ux) - self.b
        outside = math.hypot(max(la, 0.0), max(lb, 0.0))
        return outside + min(max(la, lb), 0.0)

    def edge(self):
        pts = []
        for sa, sb, n in ((1, None, self.b), (-1, None, self.b), (None, 1, self.a), (None, -1, self.a)):
            steps = max(1, int(2 * n))
            for k in range(steps + 1):
                t = -n + 2 * n * k / steps
                a = sa * self.a if sa is not None else t
                b = sb * self.b if sb is not None else t
                pts.append((self.cx + a * self.ux - b * self.uy, self.cy + a * self.uy + b * self.ux))
        return pts


class Corridor:
    """A stretch of route, m: its centre line every metre and a half width."""

    def __init__(self, spec, start_m, end_m, half):
        self.pts, self.half, self.side = [], half, []
        arc = start_m
        while arc <= end_m:
            p, yaw = lib.terrain_route_point_cm(spec, arc)
            x, y = p.x / 100.0, p.y / 100.0
            nx, ny = -math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
            self.pts.append((x, y))
            self.side += [(x + nx * half, y + ny * half), (x - nx * half, y - ny * half)]
            arc += 1.0

    def sd(self, x, y):
        return min(math.hypot(x - px, y - py) for px, py in self.pts) - self.half

    def edge(self):
        return self.side


class Group:
    def __init__(self, members):
        self.members = members

    def sd(self, x, y):
        return min(m.sd(x, y) for m in self.members)

    def edge(self):
        return [p for m in self.members for p in m.edge() if self.sd(p[0], p[1]) >= -0.01]


def gap(f, g):
    return min(min(g.sd(x, y) for x, y in f.edge()), min(f.sd(x, y) for x, y in g.edge()))


def plane_rect(plane):
    s = plane.get_editor_property("start_m")
    yaw = plane.get_editor_property("yaw_degrees")
    length = plane.get_editor_property("length_m")
    return Rect(s.x + math.cos(math.radians(yaw)) * length * 0.5, s.y + math.sin(math.radians(yaw)) * length * 0.5, yaw,
                length * 0.5, plane.get_editor_property("half_width_m"))


def log_gaps(spec):
    road_half = spec.get_editor_property("road_half_width_m")
    features = []   # (name, shape, is water or mud)
    climbs = []
    for plane in spec.get_editor_property("planes"):
        if abs(plane.get_editor_property("cross_slope_degrees")) > 0.01:
            features.append(("slope", plane_rect(plane), False))
        elif plane.get_editor_property("layer") == 0:
            features.append(("pad", plane_rect(plane), False))
        else:
            climbs.append(plane_rect(plane))
    if climbs:
        features.append(("climbs", Group(climbs), False))
    fords = 0
    for index, section in enumerate(spec.get_editor_property("sections")):
        kind = section.get_editor_property("kind")
        start_m, end_m = section.get_editor_property("start_m"), section.get_editor_property("end_m")
        if kind == unreal.GTRouteSectionKind.FORD:
            p, yaw = lib.terrain_route_point_cm(spec, (start_m + end_m) * 0.5)
            fords += 1
            # The sheet: (length + 24) x 30 m about the section's middle, turned to the route there (place_ford_sheet).
            features.append(("ford%s sheet" % "abcdefgh"[fords - 1], Rect(p.x / 100.0, p.y / 100.0, yaw, (end_m - start_m + 24.0) * 0.5, 15.0), True))
        elif kind == unreal.GTRouteSectionKind.MUD:
            # The patch: UGTMudSubsystem::BuildPatches' box, every 2 m of the section +- (half width + MarginCm 2 m).
            half = road_half * spec.get_editor_property("mud_width_scale") + 2.0
            xs, ys = [], []
            steps = max(1, int(math.ceil((end_m - start_m) / 2.0)))
            for k in range(steps + 1):
                p, _yaw = lib.terrain_route_point_cm(spec, start_m + (end_m - start_m) * k / steps)
                xs += [p.x / 100.0 - half, p.x / 100.0 + half]
                ys += [p.y / 100.0 - half, p.y / 100.0 + half]
            features.append(("bog patch", Rect((min(xs) + max(xs)) * 0.5, (min(ys) + max(ys)) * 0.5, 0.0,
                                               (max(xs) - min(xs)) * 0.5, (max(ys) - min(ys)) * 0.5), True))
        elif kind == unreal.GTRouteSectionKind.RALLY:
            half = road_half * spec.get_editor_property("rally_width_scale") + spec.get_editor_property("verge_width_m")
            features.append(("rally", Corridor(spec, start_m, end_m, half), False))
        elif kind == unreal.GTRouteSectionKind.TRACK:
            features.append(("track", Corridor(spec, start_m, end_m, road_half * spec.get_editor_property("track_width_scale")), False))
    lines = []
    worst_wet = (1e9, "")
    worst_all = (1e9, "")
    for i in range(len(features)):
        for j in range(i + 1, len(features)):
            ni, fi, wi = features[i]
            nj, fj, wj = features[j]
            g = gap(fi, fj)
            lines.append("%s-%s %.1f" % (ni, nj, g))
            if isinstance(fi, Corridor) and isinstance(fj, Corridor):
                continue   # two stretches of the same road, one after the other: they meet, and that is the loop
            if g < worst_all[0]:
                worst_all = (g, "%s / %s" % (ni, nj))
            if (wi or wj) and g < worst_wet[0]:
                worst_wet = (g, "%s / %s" % (ni, nj))
    log("gaps between footprints, m (negative overlaps): " + ", ".join(lines))
    log("minimum gap to a water sheet or mud patch %.1f m (%s); minimum gap of all %.1f m (%s)" % (worst_wet[0], worst_wet[1], worst_all[0], worst_all[1]))
    return worst_wet[0], worst_all[0]


# ---- the map's actors ------------------------------------------------------------------------------------------------
def place_proving(world, spec, builder):
    def ground(x, y):
        return lib.sample_terrain_height_cm(spec, x, y)

    mi_dirt = m6.load_or_none(m6.MAT_PATH + "/MI_Env_Dirt")
    m6.box(world, "Floor_Skirt", 0.0, 0.0, -2200.0, 20000.0, 20000.0, 1.0, material=mi_dirt)

    # The car starts on the pad, on the route's first metre, facing along it.
    starts = [a for a in unreal.EditorLevelLibrary.get_all_level_actors() if isinstance(a, unreal.PlayerStart)]
    if not starts:
        starts = [m6.spawn(world, unreal.PlayerStart, "PlayerStart", 0.0, 0.0, 120.0)]
    start, start_yaw = lib.terrain_route_point_cm(spec, 0.0)
    for actor in starts:
        actor.set_actor_location(unreal.Vector(start.x, start.y, start.z + 150.0), False, False)
        actor.set_actor_rotation(m6.rot(yaw=start_yaw), False)

    def post(label, x, y):
        anchor = m6.spawn(world, unreal.GTWinchAnchor, label, x, y, ground(x, y))
        anchor.get_anchor().set_editor_property("strength_n", 200000.0)
        anchor.get_anchor().set_editor_property("display_name", "steel post")
        return anchor

    water_material = m6.build_water_material()
    posts = []
    sheets = 0
    for index, section in enumerate(spec.get_editor_property("sections")):
        kind = section.get_editor_property("kind")
        start_m, end_m = section.get_editor_property("start_m"), section.get_editor_property("end_m")
        if kind == unreal.GTRouteSectionKind.MUD:
            for end_name, arc in (("in", start_m), ("out", end_m)):
                p, yaw = lib.terrain_route_point_cm(spec, arc)
                nx, ny = -math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
                for side in (-1, 1):
                    posts.append(post("Post_Bog_%d_%s_%d" % (index, end_name, side), p.x + nx * side * BOG_POST_SIDE_M * 100.0, p.y + ny * side * BOG_POST_SIDE_M * 100.0))
            log("bog %d over %.0f-%.0f m: posts at both ends, %.0f m either side of the middle line" % (index, start_m, end_m, BOG_POST_SIDE_M))
        elif kind == unreal.GTRouteSectionKind.FORD:
            sheet = m6.place_ford_sheet(world, spec, index, section, water_material)
            sheets += 1
            # RIVERBED S3 (VEHICLE_BUILD_SYSTEM 53), the owner's decision 2026-09-22 ("let the ponds stand still"): the
            # Proving Ground's fords are closed basins with no current. No head across the field and no nominal speed;
            # the flow direction stays as the field's axis (and the posts' upstream side). The Hide keeps its current.
            sheet.set_editor_property("head_drop_cm", 0.0)
            sheet.set_editor_property("flow_speed_cm_per_s", 0.0)
            log("  Water_%d: still water (head drop 0, flow 0; the owner's closed basin)" % index)
            depth = section.get_editor_property("depth_m")
            if depth < DEEP_FORD_M:
                continue
            mid = (start_m + end_m) * 0.5
            p, yaw = lib.terrain_route_point_cm(spec, mid)
            flow = sheet.get_editor_property("flow_direction")
            fx, fy = flow.x, flow.y
            for bank, arc in (("near", mid - FORD_POST_ALONG_M), ("far", mid + FORD_POST_ALONG_M)):
                b, _yaw = lib.terrain_route_point_cm(spec, arc)
                bx, by = b.x - fx * FORD_POST_SIDE_M * 100.0, b.y - fy * FORD_POST_SIDE_M * 100.0
                posts.append(post("Post_Ford_%d_%s" % (index, bank), bx, by))
                posts.append(post("Post_Ford_%d_%s_down" % (index, bank), bx + fx * FORD_POST_DOWN_M * 100.0, by + fy * FORD_POST_DOWN_M * 100.0))
            level = lib.terrain_ford_water_level_cm(spec, index)
            for anchor in posts[-4:]:
                loc = anchor.get_actor_location()
                log("  %s at (%.1f, %.1f) m, %.1f m from mid-channel, ground %.2f m over the water" % (
                    anchor.get_actor_label(), loc.x / 100.0, loc.y / 100.0, math.hypot(loc.x - p.x, loc.y - p.y) / 100.0, (loc.z - level) / 100.0))
    wet_gap, all_gap = log_gaps(spec)
    stations = ", ".join("%s (%.0f, %.0f) yaw %.0f arc %.0f" % (s.get_editor_property("name"), s.get_editor_property("point_m").x, s.get_editor_property("point_m").y,
                                                             s.get_editor_property("yaw_degrees"), s.get_editor_property("arc_m"))
                         for s in spec.get_editor_property("stations"))
    log("stations: " + stations)
    return {"witness": posts[0], "witness_name": posts[0].get_actor_label(), "min_regrounded": 0,
            "summary": "the Proving Ground: %d water sheets, %d winch posts, start at (%.0f, %.0f, %.0f) yaw %.0f; min gap to water/mud %.1f m, of all %.1f m"
                       % (sheets, len(posts), start.x, start.y, start.z, start_yaw, wet_gap, all_gap)}


ensure_level()
material = m6.load_or_none(m6.MAT_PATH + "/" + m6.LANDSCAPE_MATERIAL) or m6.build_landscape_material()
m6.build_level(material, level_path=LEVEL_PATH, spec_name=SPEC_NAME,
               write_spec=lambda reset: lib.create_proving_terrain_spec_asset(m6.TERRAIN_PATH, reset),
               place=place_proving, builder_xyz=(0.0, -15000.0, 3000.0))
log("DONE")
