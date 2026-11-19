"""Summarize throttle windows and separately identify sustained pawn movement."""
import argparse
import csv
import json
import math
import re
import statistics
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "Saved/LidarDrivingBaseline"
BUDGET = 1000 / 60
OFFSETS = (501, 650, 800, 950, 1100, 1250)
TIMERS = ("FrameTime", "GPUTime", "GameThreadTime", "RenderThreadTime", "RHIThreadTime")
COUNTERS = ("RHI/DrawCalls", "RHI/PrimitivesDrawn", "TextureStreaming/DesiredDataLoadedPercent",
            "TextureStreaming/PendingStreamInData", "MemoryFreeMB", "GC/Count",
            "Exclusive/GameThread/GarbageCollection", "GameThreadTime_CriticalPath",
            "RenderThreadTime_CriticalPath", "DynamicResolutionPercentage", "PrimaryScreenPercentage",
            "DrawCall/Basepass", "DrawCall/ShadowDepths", "DrawCall/Prepass", "DrawCall/Lights")


def percentile(values, fraction):
    ordered = sorted(values)
    index = fraction * (len(ordered) - 1)
    lower = int(index)
    return ordered[lower] + (index - lower) * (ordered[math.ceil(index)] - ordered[lower])


def distribution(values):
    return {
        "mean": round(statistics.mean(values), 3),
        "min": round(min(values), 3),
        "p50": round(statistics.median(values), 3),
        "p95": round(percentile(values, .95), 3),
        "p99": round(percentile(values, .99), 3),
        "max": round(max(values), 3),
    }


def timings(rows):
    times = [float(row["FrameTime"]) for row in rows]
    passes = {k: round(statistics.fmean(float(r[k]) for r in rows), 3)
              for k in rows[0] if k.startswith("GPU/")}
    return {
        "frames": len(rows),
        "seconds": round(sum(times) / 1000, 3),
        "fps": round(1000 / statistics.mean(times), 2),
        "over_budget_pct": round(100 * sum(t > BUDGET for t in times) / len(times), 2),
        "hitches_over_ms": {str(t): sum(v > t for v in times) for t in (33.3, 50, 100)},
        "timers_ms": {k: distribution([float(r[k]) for r in rows]) for k in TIMERS if k in rows[0]},
        "gpu_pass_means_ms": dict(sorted(passes.items(), key=lambda item: -item[1])[:12]),
        "counters": {k: distribution([float(r[k]) for r in rows]) for k in COUNTERS if k in rows[0]},
    }


def analyze(label, combined=None):
    directory = EVIDENCE / label
    meta = json.loads((directory / f"playperf-{label}.json").read_text(encoding="utf-8-sig"))
    assert meta["exit_code"] == 0 and meta["drive"] and not meta["on_foot"]
    log = Path(meta["log"]).read_text(errors="replace")
    coords = re.findall(r"LogCheatManager: (?:Log: )?BugItGo ([-\d.]+) ([-\d.]+) ([-\d.]+)", log)
    poses = meta["poses"]
    if isinstance(poses, dict):
        poses = poses["value"]
    assert len(coords) == len(OFFSETS) * len(poses), f"Missing pawn samples: {len(coords)}"
    with Path(meta["csv"][0]).open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        columns = [key for key in reader.fieldnames if key in TIMERS or key in COUNTERS or key.startswith("GPU/")]
        rows = []
        location_rows = []
        for row in reader:
            try:
                float(row["FrameTime"])
            except (ValueError, TypeError):
                break
            if "CsvExecCommand : LogLoc" in row["EVENTS"]:
                location_rows.append(len(rows))
            rows.append({key: row[key] for key in columns})
    assert len(location_rows) == len(coords), "CSV and pawn log disagree on the number of location samples"
    result = {"label": label, "raw_csv": meta["csv"][0], "poses": poses, "commands": meta["commands"], "sections": {}}
    for index, pose in enumerate(poses):
        name = pose["name"]
        with (directory / (name + ".png")).open("rb") as f:
            size = struct.unpack(">II", f.read(24)[16:24])
        assert list(size) == meta["resolution"], (name, size)
        points = [[float(v) for v in point] for point in coords[index*len(OFFSETS):(index+1)*len(OFFSETS)]]
        markers = location_rows[index*len(OFFSETS):(index+1)*len(OFFSETS)]
        start, end = markers[0], markers[-1]
        assert [n-start for n in markers] == [n-OFFSETS[0] for n in OFFSETS]
        sample = rows[start:end]
        assert len(sample) == end - start
        distances = [math.dist(a[:2], b[:2]) / 100 for a,b in zip(points, points[1:])]
        moving = []
        for i, distance in enumerate(distances):
            if distance >= 1:
                moving.extend(rows[markers[i]:markers[i+1]])
        if combined is not None:
            group = combined.setdefault(name, {"moving": [], "all": [], "distances_m": []})
            group["all"].extend(sample)
            group["moving"].extend(moving)
            group["distances_m"].append(round(sum(distances), 2))
        entry = timings(sample)
        entry.update(viewport=size, pawn_cm=points, csv_location_rows=markers, interval_travel_m=[round(v,2) for v in distances],
                     travel_m=round(sum(distances),2), moving_intervals=timings(moving) if moving else None)
        native_file = Path(meta["csv"][0]).parent.parent / f"gt_perf_{label}-{name}.json"
        native = json.loads(native_file.read_text(encoding="utf-8-sig"))
        entry["native_scope_window_frames"] = native["frames"]
        entry["native_scopes"] = {k: {"mean_ms_per_window_frame": round(v["total_ms"]/native["frames"], 3),
                                       "max_call_ms": v["max_ms"], "calls_over_4ms": v["over_4ms"]}
                                  for k,v in native["workers"].items()}
        for key in ("DynamicResolutionPercentage", "PrimaryScreenPercentage"):
            if key in sample[0]:
                values = [float(row[key]) for row in sample]
                entry[key] = [min(values), max(values)]
        result["sections"][name] = entry
    (directory/"analysis.json").write_text(json.dumps(result, indent=2)+"\n")
    for name, section in result["sections"].items():
        print(name, section["travel_m"], "m", section["fps"], "fps",
              section["timers_ms"]["FrameTime"]["p95"], "ms p95", list(section["gpu_pass_means_ms"].items())[:4])
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("labels", nargs="+")
    args = parser.parse_args()
    combined = {}
    for label in args.labels:
        analyze(label, combined)
    def summaries(group):
        return {kind: timings(group[kind]) if group[kind] else None for kind in ("all", "moving")}
    report = {"labels": args.labels, "sections": {name: {**summaries(group), "distances_m": group["distances_m"]}
                                                  for name, group in combined.items()}}
    report["overall"] = summaries({key: [row for group in combined.values() for row in group[key]]
                                  for key in ("all", "moving")})
    output = EVIDENCE / ("+".join(args.labels) + "-summary.json")
    output.write_text(json.dumps(report, indent=2) + "\n")
