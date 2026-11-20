"""Measure a drivable line around the logged obstruction before timing the pickup."""

import bisect
import itertools
import json
import math
import sys
from pathlib import Path

import unreal as u


def lane_offset(station_m, offset_cm):
    # Start turning before the obstacle and merge back over the same distance.
    t = max(0.0, min(1.0, (station_m - 356) / 17, (408 - station_m) / 19))
    return offset_cm * t * t * (3 - 2 * t)


def survey(output):
    root = Path(u.Paths.project_dir()).resolve()
    roads = json.loads((root / "Art/Export/LidarStudy/Place/roads.json").read_text())
    road = next(r for r in roads if r["name"] == "Logging mud track fce5")
    points = road["points"]
    heights = road["elevations_cm"]
    stations = [0, *itertools.accumulate(math.dist(a, b) / 100 for a, b in zip(points, points[1:]))]
    world = u.find_object(None, "/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy.L_LidarStudy")
    car = u.GameplayStatics.get_player_controller(world, 0).get_car()

    def road_point(station, offset):
        i = bisect.bisect_right(stations, station) - 1
        a, b = points[i:i + 2]
        t = (station - stations[i]) / (stations[i + 1] - stations[i])
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        xy = a[0] + t * dx - dy / length * offset, a[1] + t * dy + dx / length * offset
        z = heights[i] + t * (heights[i + 1] - heights[i])
        return u.Vector(*xy, z)

    def obstruction(values):
        actor = next((v for v in values if isinstance(v, u.Actor)), None)
        if isinstance(actor, (u.GTRoadReliefTile, u.LandscapeProxy)):
            return ""
        mesh = next((v.static_mesh for v in values if isinstance(v, u.StaticMeshComponent) and v.static_mesh), None)
        return mesh.get_name() if mesh else actor.get_name() if actor else "unknown obstacle"

    def ground(station, offset):
        p = road_point(station, offset)
        hit = u.SystemLibrary.line_trace_single(
            world, p + u.Vector(0, 0, 200), p - u.Vector(0, 0, 350),
            u.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [car], u.DrawDebugTrace.NONE, True,
        )
        values = hit.to_tuple() if hit else ()
        if not values or not values[0]:
            return None, "no support"
        return next(v.z for v in values if isinstance(v, u.Vector)), obstruction(values)

    def body_obstacle(before, after):
        # Forward sweeps also catch tall trunk blockers whose top is above the ground probe.
        for a, b in zip(before, after):
            for height in (90, 165):
                rise = u.Vector(0, 0, height)
                hit = u.SystemLibrary.sphere_trace_single(
                    world, a + rise, b + rise, 60, u.TraceTypeQuery.TRACE_TYPE_QUERY1,
                    False, [car], u.DrawDebugTrace.NONE, True,
                )
                values = hit.to_tuple() if hit else ()
                if values and values[0]:
                    reason = obstruction(values)
                    if reason:
                        return reason
        return ""

    results = []
    offsets = [0, *(side * distance for distance in range(50, 501, 50) for side in (1, -1))]
    for offset in offsets:
        previous = None
        previous_body = None
        result = dict(offset_cm=offset, clear=True)
        for station in range(356, 409):
            centre = lane_offset(station, offset)
            samples = [ground(station, centre + side) for side in (-105, -50, 0, 50, 105)]
            obstacle = next((reason for _, reason in samples if reason), "")
            if not obstacle:
                levels = [z for z, _ in samples]
                if max(levels) - min(levels) > 65:
                    obstacle = "cross slope"
                elif previous and max(abs(a - b) for a, b in zip(levels, previous)) > 55:
                    obstacle = "longitudinal step"
                previous = levels
                body = []
                for side, z in ((-50, levels[1]), (50, levels[3])):
                    p = road_point(station, centre + side)
                    body.append(u.Vector(p.x, p.y, z))
                if not obstacle and previous_body:
                    obstacle = body_obstacle(previous_body, body)
                previous_body = body
            if obstacle:
                result.update(clear=False, first_blocked_station_m=station, reason=obstacle)
                break
        results.append(result)
        if result["clear"]:
            break
    chosen = next((r["offset_cm"] for r in results if r["clear"]), None)
    (output / "log-clearance.json").write_text(json.dumps(dict(chosen_cm=chosen, body_swept=True, probes=results), indent=2))
    u.log(f"GT_LOG_CLEARANCE offset_cm={chosen} measured_before_drive=1")


if __name__ == "__main__":
    survey(Path(sys.argv[1]))
