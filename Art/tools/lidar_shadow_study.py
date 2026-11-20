"""Schedule and analyze standalone LiDAR shadow and base-pass comparisons."""

import csv
import hashlib
import json
import re
import statistics
import shutil
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]


def schedule(stage, candidate, out, base_family="control"):
    events = []
    route_names = ("paddock_mid", "access", "river", "bog_entry", "bog552")
    poses = {
        p["name"]: p
        for p in json.loads((ROOT / "Art/lidar_driving_baseline_poses.json").read_text())
    }
    prefix = hashlib.sha256(out.name.encode()).hexdigest()[:8] + "_"
    windows = []

    def cmd(frame, command):
        events.append((frame, command))

    def probe(frame, mode):
        cmd(frame, f"py {ROOT.as_posix()}/Art/Unreal/lidar_shadow_probe.py {mode} {out.as_posix()}")

    def shot(frame, name):
        filename = (
            f"{prefix}{name}.png"
            if stage in ("visual", "routefilm", "boundaryfilm", "routehold")
            else f"{out.as_posix()}/{name}.png"
        )
        cmd(frame, f"Shot filename={filename} -nosuffix")

    def window(start, end, name):
        cmd(start, "LogLoc")
        cmd(end, "LogLoc")
        windows.append(dict(name=name, start=start, end=end))

    def relocate(frame, name):
        if name == "bog_entry":
            probe(frame, "bog_entry")
        else:
            pose = poses[name]
            cmd(frame, f"BugItGo {pose['x']} {pose['y']} {pose['z']} 0 {pose['yaw']} 0")

    if stage in ("routefilm", "routetime", "boundaryfilm"):
        if candidate not in ("tree110", "baseline", "saved"):
            raise ValueError(candidate)
        boundary = stage == "boundaryfilm"
        route = ("paddock_mid", "access") if boundary else route_names
        film = stage in ("routefilm", "boundaryfilm")
        cmd(235, "Input.+key SpaceBar")
        probe(300, "init")
        probe(330, "verify_launch" if candidate in ("tree110", "saved") else "verify_stock")
        for index, name in enumerate(route):
            setup = 350 + (970 if boundary else 370 if film else 530) * index
            relocate(setup, name)
            start = setup + 181
            cmd(start - 3, "Input.-key SpaceBar")
            cmd(start - 1, "Input.+action IA_Throttle 0.8")
            duration = 720 if boundary else 144 if film else 300
            window(start, start + duration, name)
            for f in range(start + 12, start + duration, 12):
                cmd(f, "LogLoc")
            if name in ("paddock_mid", "access", "river"):
                cmd(start + 35, "Input.+action IA_Steer 0.22")
                cmd(start + 62, "Input.-action IA_Steer")
            if film:
                interval = 12 if boundary else 3
                for relative in range(0, duration, interval):
                    shot(start + relative, f"r{index}{relative // interval:02}")
            cmd(start + duration + 1, "Input.-action IA_Throttle")
            cmd(start + duration + 3, "Input.+key SpaceBar")
        frames = start + duration + 18
    elif stage == "routehold":
        cmd(235, "Input.+key SpaceBar")
        probe(300, "init")
        probe(330, "verify_launch")
        for index, name in enumerate(route_names):
            setup = 350 + 585 * index
            relocate(setup, name)
            start = setup + 164
            cmd(start - 3, "Input.-key SpaceBar")
            cmd(start - 1, "Input.+action IA_Throttle 0.8")
            window(start, start + 384, name)
            if name in ("paddock_mid", "access", "river"):
                cmd(start + 35, "Input.+action IA_Steer 0.22")
                cmd(start + 62, "Input.-action IA_Steer")
            for n, offset in enumerate((72, 258)):
                sample = 2 * index + n
                f = start + offset
                probe(f, "pause")
                for mark, step, treatment in (
                    ("a", 2, "stock"),
                    ("b", 39, "trial"),
                    ("c", 77, "stock"),
                ):
                    probe(f + step, "hold_" + treatment)
                    cmd(f + step + 8, "r.Shadow.Virtual.Cache 1")
                    shot(f + step + 29, f"h{sample}{mark}0")
                    shot(f + step + 32, f"h{sample}{mark}1")
                    if mark != "c":
                        probe(f + step + 33, f"record_{sample}_{mark}")
                probe(f + 112, "resume")
            cmd(start + 385, "Input.-action IA_Throttle")
            cmd(start + 386, "Input.+key SpaceBar")
        frames = start + 408
    elif stage == "visibilityhold":
        if candidate != "saved":
            raise ValueError("Use the saved profile for the visibility check")
        cmd(235, "Input.+key SpaceBar")
        probe(300, "init")
        probe(335, "verify_launch")
        for index, name in enumerate(("bog552", "access", "paddock_mid")):
            setup = 375 + index * 675
            relocate(setup, name)
            cmd(setup + 168, "Input.-key SpaceBar")
            cmd(setup + 170, "Input.+action IA_Throttle 0.8")
            window(setup + 171, setup + 363, name)
            if name != "bog552":
                cmd(setup + 205, "Input.+action IA_Steer 0.22")
                cmd(setup + 232, "Input.-action IA_Steer")
            hold = setup + 370
            probe(hold, "pause")
            for step, (label, hzb, queries) in enumerate(
                (("stock", 0, 0), ("hzb", 1, 0), ("queries", 1, 1), ("restored", 0, 0))
            ):
                at = hold + step * 42 + 1
                cmd(at, f"r.InstanceCulling.OcclusionCull {hzb}")
                cmd(at, f"r.InstanceCulling.OcclusionQueries {queries}")
                shot(at + 32, name + "_" + label)
                probe(at + 34, f"record_{name}_{label}")
            probe(hold + 180, "resume")
            cmd(hold + 182, "Input.-action IA_Throttle")
            cmd(hold + 183, "Input.+key SpaceBar")
        frames = hold + 205
    elif stage == "efficiency":
        if candidate != "saved":
            raise ValueError("Use the saved profile for rendering efficiency comparisons")
        cmd(235, "Input.+key SpaceBar")
        probe(300, "init")
        probe(335, "verify_launch")
        relocate(375, "bog552")
        # Bracket each group with a stock control inside the same game and thermal session.
        # The truck is braked. These timings isolate rendering at one view, outside driving.
        cases = (
            ("stock", 0, 0, 0),
            ("dry", 1, 0, 0),
            ("hzb", 1, 1, 0),
            ("queries", 1, 1, 1),
            ("dry_repeat", 1, 0, 0),
            ("stock_repeat", 0, 0, 0),
            ("queries_repeat", 1, 1, 1),
            ("hzb_repeat", 1, 1, 0),
            ("stock_end", 0, 0, 0),
        )
        for index, (name, dry, hzb, queries) in enumerate(cases):
            start = 690 + index * 160
            for setting, value in (
                ("gt.Weather.SkipDryOcclusion", dry),
                ("r.InstanceCulling.OcclusionCull", hzb),
                ("r.InstanceCulling.OcclusionQueries", queries),
            ):
                cmd(start, f"{setting} {value}")
            window(start + 52, start + 148, name)
            shot(start + 152, name)
        frames = start + 167
    elif stage == "renderfamilies":
        if candidate != "saved":
            raise ValueError("The render family study requires the saved profile")
        script = (ROOT / "Art/Unreal/lidar_base_pass_probe.py").as_posix()
        cmd(235, "Input.+key SpaceBar")
        probe(300, "init")
        probe(335, "verify_launch")
        relocate(375, "bog552")
        cmd(600, f"py {script} inventory bog552 {out.as_posix()}")
        cases = (
            "control",
            "tree_visibility",
            "hide_trees_and_terrain",
            "hide_trees_and_dressing",
            "tree_visibility",
            "hide_trees_and_all_grass",
            "hide_trees_and_pickup",
            "tree_visibility",
            "control",
        )
        for i, family in enumerate(cases):
            start = 660 + 145 * i
            cmd(start, f"py {script} measure {family} {out.as_posix()}")
            window(start + 45, start + 133, f"{i:02}_{family}")
        frames = start + 145
    elif stage == "weathercheck":
        if candidate != "saved":
            raise ValueError("Weather validation requires the saved map and profile")
        script = (ROOT / "Art/Unreal/lidar_weather_check.py").as_posix()
        cmd(235, "Input.+key SpaceBar")
        probe(300, "init")
        probe(335, "verify_launch")
        relocate(375, "bog552")
        for at, action in (
            (520, "dry1"),
            (550, "dry2"),
            (555, "rain"),
            (557, "onset"),
            (586, "raining"),
            (588, "clear"),
            (610, "drying"),
            (616, "reset_wetness"),
            (645, "dry3"),
            (672, "dry4"),
            (676, "snow"),
            (706, "snowing"),
            (710, "clear"),
            (724, "melting"),
        ):
            cmd(at, f"py {script} {action} {out.as_posix()}")
        for at, label in ((553, "dry"), (587, "rain"), (611, "drying"), (707, "snow")):
            shot(at, label)
        window(640, 669, "clear")
        frames = 740
    elif stage == "basemoving":
        if candidate != "saved":
            raise ValueError("Use the saved LiDAR profile for the moving base-pass test")
        script = (ROOT / "Art/Unreal/lidar_base_pass_probe.py").as_posix()
        cmd(235, "Input.+key SpaceBar")
        probe(300, "init")
        probe(335, "verify_launch")
        relocate(375, "bog552")
        cmd(525, f"py {script} inventory bog552 {out.as_posix()}")
        cmd(555, f"py {script} measure {base_family} {out.as_posix()}")
        cmd(623, "Input.-key SpaceBar")
        cmd(625, "Input.+action IA_Throttle 0.8")
        window(626, 818, f"drive_{base_family}")
        for frame in range(638, 818, 12):
            cmd(frame, "LogLoc")
        cmd(819, "Input.-action IA_Throttle")
        cmd(820, "Input.+key SpaceBar")
        shot(825, "diagnostic")
        cmd(830, f"py {script} measure control {out.as_posix()}")
        frames = 850
    elif stage == "basepass":
        cmd(250, "Input.+key SpaceBar")
        probe(300, "init")
        probe(340, "verify_launch" if candidate in ("tree110", "saved") else "verify_stock")
        cases = (
            "control",
            "near_grass",
            "far_grass",
            "all_grass",
            "control",
            "trees",
            "dressing",
            "terrain",
            "pickup",
            "lowres",
            "lowres_all_grass",
            "lowres_trees",
            "lowres_repeat",
            "control",
        )
        cmd(350, "r.ProfileGPU.ShowUI 0")
        cmd(350, "r.ProfileGPU.UnicodeOutput 0")
        cmd(350, "r.ProfileGPU.ThresholdPercent 0.25")
        name = "bog552"
        setup = 375
        relocate(setup, name)
        script = (ROOT / "Art/Unreal/lidar_base_pass_probe.py").as_posix()
        cmd(setup + 170, f"py {script} inventory {name} {out.as_posix()}")
        cmd(setup + 181, "Input.-key SpaceBar")
        cmd(setup + 183, "Input.+action IA_Throttle 0.8")
        window(setup + 184, setup + 290, "bog552_drive")
        cmd(setup + 291, "Input.-action IA_Throttle")
        cmd(setup + 292, "Input.+key SpaceBar")
        for step, case in enumerate(cases):
            start = setup + 405 + step * 85
            group = {"lowres": "control", "lowres_repeat": "control"}.get(
                case, case.removeprefix("lowres_")
            )
            cmd(start, f"py {script} measure {group} {out.as_posix()}")
            cmd(
                start + 1,
                "r.ScreenPercentage 50" if case.startswith("lowres") else "r.ScreenPercentage 75",
            )
            if case == "lowres":
                cmd(start + 20, "r.DumpRenderTargetPoolMemory")
            window(start + 35, start + 82, f"{name}_{step:02}_{case}")
        # Draw-event instrumentation perturbs cost; enable it only outside the timed windows.
        cmd(start + 83, "r.ShowMaterialDrawEvents 1")
        cmd(start + 83, "r.EmitMeshDrawEvents 1")
        cmd(start + 87, "ProfileGPU")
        cmd(start + 94, "r.EmitMeshDrawEvents 0")
        cmd(start + 94, "r.ShowMaterialDrawEvents 0")
        frames = start + 112
    elif stage == "diagnose":
        cmd(300, "Input.+key SpaceBar")
        probe(420, "init")
        for i, group in enumerate(
            [
                "baseline",
                "trees",
                "landscape",
                "groundflora",
                "groundmesh",
                "vehicle",
                "other",
                "baseline",
                "skip_invalidation",
                "restore",
            ]
        ):
            start = 460 + 140 * i
            if group == "skip_invalidation":
                cmd(start, "r.Shadow.Virtual.Cache.DebugSkipDynamicPageInvalidation 1")
            elif group == "restore":
                cmd(start, "r.Shadow.Virtual.Cache.DebugSkipDynamicPageInvalidation 0")
            else:
                probe(start, "isolate_" + group)
            shot(start + 33, group + str(i))
            cmd(start + 45, "r.Shadow.Virtual.AccumulateStats 24")
            window(start + 82, start + 132, group + str(i))
        frames = 1900
    elif stage == "cache":
        cmd(300, "Input.+key SpaceBar")
        probe(415, "init")
        cases = [
            ("baseline", 1, 3),
            ("receiver_off", 0, 3),
            ("baseline_repeat", 1, 3),
            ("shadow_wind_bias0", 1, 0),
            ("receiver_off_wind_bias0", 0, 0),
            ("receiver_off_repeat", 0, 3),
            ("restore", 1, 3),
        ]
        for i, (name, mask, bias) in enumerate(cases):
            start = 450 + i * 140
            cmd(start, f"r.Shadow.Virtual.UseReceiverMaskDirectional {mask}")
            cmd(start, f"r.Shadow.Virtual.Clipmap.WPODisableDistance.LodBias {bias}")
            shot(start + 35, name)
            cmd(start + 48, "r.Shadow.Virtual.AccumulateStats 20")
            window(start + 80, start + 135, name)
        frames = 1450
    elif stage == "canopy":
        cmd(300, "Input.+key SpaceBar")
        probe(415, "init")
        cases = [
            ("baseline", "restore", 3, 1),
            ("wind50", "5000", 3, 1),
            ("wind50bias0", "5000", 0, 1),
            ("wind50biasNeg2", "5000", -2, 1),
            ("all_tree_wpo_off_diagnostic", "off", 3, 1),
            ("bias125", "restore", 3, 1.25),
            ("bias150", "restore", 3, 1.5),
            ("restore", "restore", 3, 1),
        ]
        for i, (name, distance, bias, res) in enumerate(cases):
            start = 450 + i * 140
            probe(start, "wind_" + distance)
            cmd(start, f"r.Shadow.Virtual.Clipmap.WPODisableDistance.LodBias {bias}")
            cmd(start, f"r.Shadow.Virtual.ResolutionLodBiasDirectional {res}")
            shot(start + 34, name)
            cmd(start + 45, "r.Shadow.Virtual.AccumulateStats 20")
            window(start + 80, start + 135, name)
        frames = 1590
    elif stage == "rebuild":
        cmd(300, "Input.+key SpaceBar")
        probe(415, "init")
        cases = [
            ("baseline", "restore", 3, 1, 1),
            ("tree110", "11000", -3, 1, 1),
            ("tree110soft", "11000", -1, 1, 1),
            ("resolution2", "restore", 3, 2, 1),
            ("shadowlod2", "restore", 3, 1, 2),
            ("restore", "restore", 3, 1, 1),
        ]
        for i, (name, dist, bias, res, lod) in enumerate(cases):
            start = 445 + i * 175
            probe(start, "wind_" + dist)
            cmd(start, f"r.Shadow.Virtual.Clipmap.WPODisableDistance.LodBias {bias}")
            cmd(start, f"r.Shadow.Virtual.ResolutionLodBiasDirectional {res}")
            cmd(start, f"r.Shadow.LODDistanceFactor {lod}")
            cmd(start + 2, "r.Shadow.Virtual.Cache 0")
            shot(start + 20, name + "_uncached")
            cmd(start + 25, "r.Shadow.Virtual.Cache 1")
            shot(start + 75, name)
            cmd(start + 83, "r.Shadow.Virtual.AccumulateStats 20")
            window(start + 116, start + 169, name)
        frames = 1510
    elif stage in ("drive", "visual"):
        cases = {
            "baseline": ("stock", 3, 1),
            "wind50": ("5000", 3, 1),
            "wind50bias0": ("5000", 0, 1),
            "wind50biasNeg2": ("5000", -2, 1),
            "tree110": ("11000", -3, 1),
            "tree110soft": ("11000", -1, 1),
            "bias125": ("restore", 3, 1.25),
            "bias150": ("restore", 3, 1.5),
        }

        def apply(frame, case):
            dist, bias, res = cases[case]
            probe(frame, "wind_" + dist)
            cmd(frame, f"r.Shadow.Virtual.Clipmap.WPODisableDistance.LodBias {bias}")
            cmd(frame, f"r.Shadow.Virtual.ResolutionLodBiasDirectional {res}")
            # Changing cache eligibility in place can leave stale static pages.
            cmd(frame + 1, "r.Shadow.Virtual.Cache 0")
            cmd(frame + 4, "r.Shadow.Virtual.Cache 1")

        cmd(240, "Input.+key SpaceBar")
        probe(360, "init")
        if candidate == "tree110":
            probe(385, "verify_launch")
        else:
            apply(385, candidate)
        if stage == "drive":
            for n, start in enumerate((650, 1370)):
                if n:
                    probe(1055, "approach")
                shot(start - 60, ("bog", "approach")[n])
                cmd(start - 3, "Input.-key SpaceBar")
                cmd(start - 1, "Input.+action IA_Throttle 0.75")
                window(start, start + 360, ("bog", "approach")[n])
                for f in range(start + 10, start + 360, 10):
                    cmd(f, "LogLoc")
                cmd(start + 361, "Input.-action IA_Throttle")
                cmd(start + 363, "Input.+key SpaceBar")
            frames = 1750
        else:
            probe(401, "approach")
            start = 556
            cmd(start - 3, "Input.-key SpaceBar")
            cmd(start - 1, "Input.+action IA_Throttle 0.75")
            window(start, start + 192, "film")
            for frame in range(start, start + 192, 2):
                shot(frame, f"film_{(frame - start) // 2:03}")
                if (frame - start) % 24 == 0 and frame != start:
                    cmd(frame, "LogLoc")
            frames = 758
            if candidate != "baseline":
                # A second drive samples both treatments at the same paused instants.
                # The first 8 seconds above remain uninterrupted for the playback comparison.
                cmd(751, "Input.-action IA_Throttle")
                cmd(752, "Input.+key SpaceBar")
                probe(780, "approach")
                cmd(880, "Input.-key SpaceBar")
                cmd(881, "Input.+action IA_Throttle 0.75")
                for i in range(4):
                    f = 906 + 132 * i
                    probe(f, "pause")
                    apply(f + 2, "baseline")
                    shot(f + 24, f"pair_{i}_a0")
                    shot(f + 28, f"pair_{i}_a1")
                    probe(f + 29, f"record_{i}_a")
                    apply(f + 30, candidate)
                    shot(f + 53, f"pair_{i}_b0")
                    shot(f + 57, f"pair_{i}_b1")
                    probe(f + 58, f"record_{i}_b")
                    apply(f + 59, "baseline")
                    shot(f + 82, f"pair_{i}_a2")
                    probe(f + 84, "resume")
                frames = 1400
    else:
        raise ValueError(stage)
    (out / "shadow-schedule.json").write_text(
        json.dumps(
            dict(
                stage=stage,
                candidate=candidate,
                frames=frames,
                windows=windows,
                image_prefix=prefix,
                commands=[f"{f}:{c}" for f, c in sorted(events, key=lambda v: v[0])],
            ),
            indent=2,
        )
    )


def analyze(out):
    manifest = json.loads((out / f"playperf-{out.name}.json").read_text(encoding="utf-8-sig"))
    assert manifest["exit_code"] == 0
    plan = json.loads((out / "shadow-schedule.json").read_text())
    log = (out / "drive.log").read_text(errors="replace")
    if "LogPython: Error:" in log:
        raise RuntimeError("Unreal Python error in drive.log")
    if plan["stage"] in ("visual", "routefilm", "boundaryfilm", "routehold"):
        # Move only this run's uniquely named shots from the engine output directory.
        # Short Shot commands keep the dual-treatment schedule inside UE's command-line limit.
        screenshots = ROOT / "Saved_LidarDrive/Screenshots/WindowsEditor"
        prefix = plan["image_prefix"]
        for command in plan["commands"]:
            match = re.search(
                r":Shot filename=(" + re.escape(prefix) + r"([a-z0-9_]+\.png)) -nosuffix$", command
            )
            if match:
                source = screenshots / match[1]
                dest = out / match[2]
                if not dest.exists():
                    if source.drive.lower() == dest.drive.lower():
                        source.rename(dest)
                    else:
                        # Commit the complete frame before removing the engine's temporary copy.
                        partial = dest.with_suffix(".partial")
                        shutil.copyfile(source, partial)
                        if partial.stat().st_size != source.stat().st_size:
                            raise OSError(f"Incomplete screenshot {partial}")
                        partial.replace(dest)
                        source.unlink()
                assert dest.is_file()
    metrics = (
        "FrameTime",
        "GPUTime",
        "GPU/ShadowDepths",
        "GPU/Basepass",
        "GPU/RenderVelocities",
        "DrawCall/ShadowDepths",
        "GameThreadTime",
        "RenderThreadTime",
    )
    if plan["stage"] in ("basepass", "basemoving", "routetime", "efficiency", "renderfamilies"):
        metrics += ("DrawCall/Basepass", "RHI/PrimitivesDrawn", "GPU/Prepass")
    with Path(manifest["csv"][0]).open(newline="") as f:
        reader = csv.DictReader(f)
        frames = []
        markers = []
        for row in reader:
            try:
                values = [float(row[k]) for k in metrics]
            except (ValueError, TypeError):
                break
            if "CsvExecCommand : LogLoc" in row["EVENTS"]:
                markers.append(len(frames))
            frames.append(values)
    assert len(frames) == plan["frames"]
    locations = re.findall(r"LogCheatManager: BugItGo ([-.\d]+) ([-.\d]+) ([-.\d]+)", log)
    assert len(markers) == len(locations)

    def stats(values):
        sort = sorted(values)
        return dict(
            mean=round(statistics.mean(values), 3),
            p95=round(sort[round((len(sort) - 1) * 0.95)], 3),
        )

    def timing_stats(rows):
        table = dict(zip(metrics, [stats(column) for column in zip(*rows)]))
        frame_times = sorted(row[0] for row in rows)
        table["FrameTime"].update(
            median=round(statistics.median(frame_times), 3),
            p99=round(frame_times[round((len(frame_times) - 1) * 0.99)], 3),
            maximum=round(frame_times[-1], 3),
            pct_over_60fps_budget=round(
                100 * sum(t > 1000 / 60 for t in frame_times) / len(frame_times), 2
            ),
            over_33_3_ms=sum(t > 33.3 for t in frame_times),
            over_50_ms=sum(t > 50 for t in frame_times),
            over_100_ms=sum(t > 100 for t in frame_times),
        )
        return table

    tabs = []
    vsm_files = re.findall(r"Writing VSM accumulated stats .*? to file '([^']+)'", log)
    diagnostic = plan["stage"] in ("diagnose", "cache", "canopy", "rebuild")
    if diagnostic and len(vsm_files) != len(plan["windows"]):
        raise ValueError("Missing VSM counter window in the Unreal log")
    for w in plan["windows"]:
        lo, hi = w["start"] - 1, w["end"] - 1
        assert lo in markers and hi in markers
        a, b = markers.index(lo), markers.index(hi)
        elapsed = sum(row[0] for row in frames[lo:hi]) / 1000
        xyz = [[float(c) for c in pos] for pos in locations[a : b + 1]]
        import math

        distance = sum(math.dist(v[:2], u[:2]) / 100 for v, u in zip(xyz, xyz[1:]))
        tab = dict(
            name=w["name"],
            frames=hi - lo,
            seconds=round(elapsed, 3),
            fps=round((hi - lo) / elapsed, 2),
            travel_m=round(distance, 2),
            pawn_cm=xyz,
            timings=timing_stats(frames[lo:hi]),
        )
        if plan["stage"] in ("drive", "routetime"):
            # Equal wall-time exposure even when a faster candidate renders more frames.
            times = [r[0] / 1000 for r in frames[lo:hi]]
            import itertools, bisect

            clock = [0.0, *itertools.accumulate(times)]
            stop = bisect.bisect_left(clock, 8.0)
            # Fast complete traversals can end before eight seconds. Retain the full
            # segment and matched-distance data without fabricating an eight-second result.
            if stop < len(clock):
                split = lo + stop
                m = bisect.bisect_left(markers, split)
                dist8 = sum(
                    math.dist(x[:2], y[:2]) / 100 for x, y in zip(xyz[: m - a - 1], xyz[1 : m - a])
                )
                first = markers[m - 1]
                frac = (clock[stop] - clock[first - lo]) / (
                    clock[markers[m] - lo] - clock[first - lo]
                )
                dist8 += frac * math.dist(xyz[m - a - 1][:2], xyz[m - a][:2]) / 100
                tab["eight_seconds"] = dict(
                    frames=stop,
                    seconds=round(clock[stop], 3),
                    fps=round(stop / clock[stop], 2),
                    estimated_travel_m=round(dist8, 2),
                    timings=timing_stats(frames[lo:split]),
                )
            target = {"bog": 1.5, "river": 1.0, "bog_entry": 2.0, "bog552": 1.0}.get(
                w["name"], 12.0
            )
            travel = [
                0.0,
                *itertools.accumulate(math.dist(x[:2], y[:2]) / 100 for x, y in zip(xyz, xyz[1:])),
            ]
            k = bisect.bisect_left(travel, target)
            if k < len(travel):
                weight = (target - travel[k - 1]) / (travel[k] - travel[k - 1])
                last = round(markers[a + k - 1] + weight * (markers[a + k] - markers[a + k - 1]))
                subset = frames[lo:last]
                seconds = sum(row[0] for row in subset) / 1000
                tab["matched_distance"] = dict(
                    target_m=target,
                    frames=len(subset),
                    seconds=round(seconds, 3),
                    fps=round(len(subset) / seconds, 2),
                    timings=timing_stats(subset),
                )
        if diagnostic:
            path = Path(manifest["csv"][0]).parents[1] / Path(vsm_files[len(tabs)]).name
            with path.open() as f:
                samples = list(csv.DictReader(f))
            tab["vsm_mean"] = {
                key: round(statistics.mean(float(row[key]) for row in samples), 2)
                for key in samples[0]
                if key
            }
        tabs.append(tab)
        print(
            w["name"],
            tab["fps"],
            tab["travel_m"],
            tab["timings"]["GPU/ShadowDepths"],
            tab["timings"]["DrawCall/ShadowDepths"]["mean"],
        )
    (out / "shadow-results.json").write_text(json.dumps(tabs, indent=2))


if __name__ == "__main__":
    if sys.argv[1] == "schedule":
        _, action, stage, candidate, out, *family = sys.argv
        schedule(stage, candidate, Path(out), *family)
    elif sys.argv[1] == "analyze":
        analyze(Path(sys.argv[2]))
