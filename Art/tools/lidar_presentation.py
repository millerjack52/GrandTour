"""Summarize DXGI presentation timestamps for the marked foreground drives."""

import argparse
import csv
import json
import math
from collections import Counter
from itertools import groupby
from pathlib import Path
from statistics import median


def percentile(values, fraction):
    return round(sorted(values)[round((len(values) - 1) * fraction)], 3)


def timing_summary(frame):
    return dict(
        frames=len(frame),
        fps=round(1000 * len(frame) / sum(frame), 2),
        median_ms=round(median(frame), 3),
        mean_ms=round(sum(frame) / len(frame), 3),
        p95_ms=percentile(frame, 0.95),
        p99_ms=percentile(frame, 0.99),
        maximum_ms=round(max(frame), 3),
        percent_over_budget=round(100 * sum(t > 1000 / 60 for t in frame) / len(frame), 2),
        over_33_3_ms=sum(t > 33.3 for t in frame),
        over_50_ms=sum(t > 50 for t in frame),
        over_100_ms=sum(t > 100 for t in frame),
    )


def continuous_results(folder, observations, data):
    first_engine_frame = observations[0]["engine_frame"]
    manifest = json.loads(next(folder.glob("playperf-*.json")).read_text(encoding="utf-8-sig"))
    drive = json.loads((folder / "continuous-drive.json").read_text())
    samples = drive["samples"]
    data["drive"] = {k: v for k, v in drive.items() if k != "samples"}
    data["drive"]["telemetry_samples"] = len(samples)
    times = []
    origin = None
    with Path(manifest["csv"][0]).open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            try:
                dt = float(row["FrameTime"])
            except (TypeError, ValueError):
                break
            if "CsvExecCommand : gt.Lidar.Present start " in row["EVENTS"]:
                origin = first_engine_frame - len(times)
            times.append(dt)
    if origin is None:
        raise ValueError("No matching display and engine capture start")
    for info in data["sections"]:
        lo = info["first_engine_frame"] - origin
        hi = info["last_engine_frame"] - origin + 1
        if not (0 <= lo < hi <= len(times)):
            raise ValueError("Drive capture missing engine frames")
        frame = times[lo:hi]
        info["engine"] = timing_summary(frame)
        if "speed_mps" in observations[0]:
            moving = [
                times[r["engine_frame"] - origin]
                for r in observations
                if info["first_engine_frame"] <= r["engine_frame"] <= info["last_engine_frame"]
                and r["foreground"]
                and r["driving"]
                and r["speed_mps"] > 0.5
            ]
            info["engine_moving"] = timing_summary(moving) if moving else None
    data["physical_sections"] = []
    for name, group in groupby(samples, key=lambda s: s[1]):
        group = list(group)
        data["physical_sections"].append(
            dict(
                section=name,
                samples=len(group),
                elapsed_s=round(group[-1][0] - group[0][0], 2),
                road_progress_m=round(group[-1][2] - group[0][2], 2),
                travel_m=round(
                    sum(math.dist(a[4:6], b[4:6]) / 100 for a, b in zip(group, group[1:])), 2
                ),
                moving_pct=round(100 * sum(s[7] > 0.5 for s in group) / len(group), 1),
                wheel_contacts_median=median(s[8] for s in group),
            )
        )


def analyze(folder):
    with (folder / "presentation.csv").open(newline="") as source:
        rows = [
            {
                key: val
                if key == "section"
                else float(val)
                if key in ("query_us", "speed_mps")
                else int(val)
                for key, val in row.items()
            }
            for row in csv.DictReader(source)
        ]
    if not rows:
        raise ValueError("No viewport samples")
    hz = rows[0]["qpc_frequency"]
    if hz <= 0 or any(r["qpc_frequency"] != hz for r in rows):
        raise ValueError("No stable performance counter")
    clocks = []
    for a, b in zip(rows, rows[1:]):
        delta = b["sync_refresh"] - a["sync_refresh"]
        ticks = b["sync_qpc"] - a["sync_qpc"]
        if a["result"] == b["result"] == 0 and delta > 0 and ticks > 0:
            clocks.append(ticks / delta)
    period = median(clocks) if clocks else None
    stable = (
        period
        and percentile(clocks, 0.05) > 0.99 * period
        and percentile(clocks, 0.95) < 1.01 * period
    )
    plan = json.loads((folder / "shadow-schedule.json").read_text())
    data = {
        "desktop_refresh_hz": round(hz / period, 3) if period and stable else None,
        "query_median_us": median(r["query_us"] for r in rows),
        "query_p99_us": percentile([r["query_us"] for r in rows], 0.99),
        "sections": [],
    }
    segments = [
        (name, list(frames))
        for name, frames in groupby(rows, key=lambda r: r["section"])
        if name != "None"
    ]
    if plan["stage"] != "linkeddrive":
        observed = [(name, len(frames)) for name, frames in segments]
        expected = [(w["name"], w["end"] - w["start"]) for w in plan["windows"]]
        if observed != expected:
            raise ValueError(
                f"Unexpected presentation section lengths: {observed}, expected {expected}"
            )
    for name, marked in segments:
        info = {
            "section": name,
            "samples": len(marked),
            "first_engine_frame": marked[0]["engine_frame"],
            "last_engine_frame": marked[-1]["engine_frame"],
            "viewport": dict(Counter(f"{r['width']}x{r['height']}" for r in marked)),
            "foreground_samples": sum(r["foreground"] for r in marked),
            "dxgi_status": dict(Counter(r["result"] for r in marked)),
        }
        if "driving" in marked[0]:
            info["drive_view_samples"] = sum(r["driving"] for r in marked)
            info["drive_view_moving_samples"] = sum(
                r["driving"] and r["speed_mps"] > 0.5 for r in marked
            )
        # Allow the queue to drain across the labels. Repeated reports are the
        # same present. A jump in IDs is ambiguous, so never assign its interval
        # to one frame or count the missing IDs as displayed frames.
        last = None
        intervals = []
        gaps = 0
        missing = 0
        for r in marked[8:-8]:
            if r["result"] or not r["foreground"] or not r.get("driving", 1) or r["sync_qpc"] <= 0:
                last = None
                missing += 1
                continue
            offset = r["present_refresh"] - r["sync_refresh"]
            if offset and not stable:
                last = None
                missing += 1
                continue
            timestamp = r["sync_qpc"] + (offset * period if offset else 0)
            if last is not None:
                delta = r["presented"] - last[0]
                if not delta:
                    continue
                if delta == 1 and timestamp > last[1]:
                    intervals.append((timestamp - last[1]) * 1000 / hz)
                else:
                    gaps += 1
            last = r["presented"], timestamp
        complete = len(intervals) == len(marked) - 17 and not gaps and not missing
        info.update(
            intervals=len(intervals),
            discontinuities=gaps,
            invalid_samples=missing,
            complete_inner_window=complete,
        )
        if intervals:
            info.update(
                observed_contiguous_fps=round(1000 * len(intervals) / sum(intervals), 2),
                p95_ms=percentile(intervals, 0.95),
                p99_ms=percentile(intervals, 0.99),
                maximum_ms=round(max(intervals), 3),
                percent_over_16_67_ms=round(
                    100 * sum(t > 1000 / 60 for t in intervals) / len(intervals), 2
                ),
            )
        data["sections"].append(info)
    if plan["stage"] == "linkeddrive":
        continuous_results(folder, rows, data)
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    folder = parser.parse_args().folder
    result = analyze(folder)
    (folder / "presentation-summary.json").write_text(json.dumps(result, indent=2) + "\n")
    for section in result["sections"]:
        print(section)
