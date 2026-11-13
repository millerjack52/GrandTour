"""Leg dressing LD8a step 4 (docs/LEG_DRESSING_PLAN.md LD8a): the tables from Art/dressing/ld8_profile.ps1's logs.

Plain Python, no Unreal:  python Art/dressing/ld8_profile.py
Reads docs/landscape_migration/ld8_profile_runs.json and each run's Saved/Logs/ld8_<run>.log. In a log, every
"GTPROFILE capture <picture> ..." line (FGTM6TestRunner::TickProfile) is followed by ProfileGPU's dump (UE 5.8's RHI
GPU profiler: a box table per pipeline, the event tree in its last column). For each capture this keeps:
  - the Graphics pipeline's tree, trimmed (the event name, inclusive ms, draws, dispatches, primitives; depth <= the
    Scene node + 3, events >= 0.01 ms) -> docs/landscape_migration/ld8_profile/<run>__<picture>__<n>.txt;
  - the top-level passes: the children of "Scene" (same-named siblings summed), plus "(outside Scene)" = the frame
    less Scene; the Compute pipeline's Scene children as "[async] <pass>" (they overlap the graphics pipeline, so the
    graphics frame does not contain them; async_compute_ms is that pipeline's total).
Tables: per view and state (dressing 1 / 0) the median over the captures of each pass; per view the delta; the average
over the views; the top 8 passes by the average dressing-on time; the 5 passes that grow the most, with their per-view
deltas. The GTPERF step lines of the hide runs give the overall means: per run the mean of the step means over steps
1-30 (steps with >= 10 frames), then the mean over the runs of a state.
Writes docs/landscape_migration/ld8_profile.json and docs/landscape_migration/ld8_profile/ld8_profile.md.
"""
import io
import json
import os
import re
import statistics
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
LOGS = os.path.join(ROOT, "Saved", "Logs")
DOCS = os.environ.get("GT_LD8_DOCS") or os.path.join(ROOT, "docs", "landscape_migration")
# LD8b: env GT_LD8_TAG (default ld8) names the runs file and the outputs (<tag>_profile_runs.json, <tag>_profile.json,
# <tag>_profile/); env GT_LD8_COMPARE (an earlier <tag>_profile.json) adds a before/after table of that profile's 5
# fastest-growing passes, averaged over the views both profiles share.
TAG = os.environ.get("GT_LD8_TAG", "ld8")
TITLE = {"ld8": "LD8a", "ld8b": "LD8b"}.get(TAG, TAG)
COMPARE = os.environ.get("GT_LD8_COMPARE", "")
DUMPS = os.path.join(DOCS, TAG + "_profile")
RUNS = os.path.join(DOCS, TAG + "_profile_runs.json")
BAR = "┃"   # the box table's heavy vertical
CELL = "│"  # its light vertical
CAPTURE = re.compile(r'GTPROFILE capture (\S+) (\d+)/(\d+) dressing (-?\d+) res (\d+)x(\d+) sp (\S+) voxels (-?\d+) gpu "([^"]*)" \| (.*)$')
PERF = re.compile(r"step (\d+): GTPERF (\d+) frames, frame ([\d.]+) ms mean / ([\d.]+) max, GPU ([\d.]+) ms mean; gt.Look.Dressing (-?\d+)")


def payload(line):
    k = line.find("Display: ")
    return line[k + 9:] if k >= 0 else line


def parse_table(rows):
    """[(depth, name, incl_ms, draws, dispatches, prims)] from a pipeline table's data rows."""
    out = []
    for r in rows:
        parts = r.split(BAR)
        if len(parts) < 4:
            continue
        cols = [c.strip() for c in parts[2].split(CELL)]
        name_col = parts[3].rstrip()
        m = re.match(r"^([\d.]+) ms$", cols[-1]) if cols else None
        if not m:
            continue
        stripped = name_col.lstrip(" ")
        depth = (len(name_col) - len(stripped) - 1) // 3
        out.append((depth, stripped.strip(), float(m.group(1)), cols[0], cols[1], cols[2]))
    return out


def split_pipelines(block):
    """{'graphics': rows, 'compute': rows} from the dump lines after a capture line."""
    pipes, cur = {}, None
    for line in block:
        p = payload(line)
        if "Graphics pipeline" in p and "GPU" in p:
            cur = pipes.setdefault("graphics", [])
            continue
        if "Compute pipeline" in p and "GPU" in p:
            cur = pipes.setdefault("compute", [])
            continue
        if "Copy pipeline" in p and "GPU" in p:
            cur = None
            continue
        if cur is not None and BAR in p:
            cur.append(p)
    return {k: parse_table(v) for k, v in pipes.items()}


def top_level(tree):
    frame = next((t for t in tree if t[1].startswith("Frame ")), None)
    scene_i = next((i for i, t in enumerate(tree) if t[1] == "Scene"), None)
    if frame is None or scene_i is None:
        return None, {}, []
    sd = tree[scene_i][0]
    passes, trimmed = {}, []
    for t in tree[scene_i + 1:]:
        if t[0] <= sd:
            break
        if t[0] == sd + 1:
            rec = passes.setdefault(t[1], {"ms": 0.0, "draws": 0, "dispatches": 0, "prims": []})
            rec["ms"] += t[2]
            rec["draws"] += int(t[3]) if t[3].isdigit() else 0
            rec["dispatches"] += int(t[4]) if t[4].isdigit() else 0
            rec["prims"].append(t[5])
    passes["(outside Scene)"] = {"ms": max(0.0, frame[2] - tree[scene_i][2]), "draws": 0, "dispatches": 0, "prims": []}
    for t in tree:
        if t[0] <= sd + 3 and t[2] >= 0.01:
            trimmed.append("%s%-70s %8.3f ms  draws %s  dispatches %s  prims %s" % ("   " * t[0], t[1][:70], t[2], t[3], t[4], t[5]))
    return frame[2], passes, trimmed


def view_key(picture):
    for suffix in ("_on", "_dress0"):
        if picture.endswith(suffix):
            return picture[: -len(suffix)]
    return picture


def main():
    runs = []

    def collect(o):
        # Windows PowerShell 5.1 nests an appended array in "value" wrappers: take every run record at any depth
        if isinstance(o, dict):
            if "name" in o and "log" in o:
                runs.append(o)
                return
            for v in o.values():
                collect(v)
        elif isinstance(o, list):
            for v in o:
                collect(v)

    collect(json.load(io.open(RUNS, encoding="utf-8-sig")))
    os.makedirs(DUMPS, exist_ok=True)
    records, perf = [], []
    for run in runs:
        path = os.path.join(LOGS, run["log"])
        if not os.path.isfile(path):
            continue
        lines = io.open(path, encoding="utf-8", errors="replace").read().split("\n")
        if run["kind"] == "hide":
            steps = {}
            for line in lines:
                m = PERF.search(line)
                if m and 1 <= int(m.group(1)) <= 30 and int(m.group(2)) >= 10:
                    steps[int(m.group(1))] = (float(m.group(3)), float(m.group(5)), int(m.group(6)))
            if steps:
                perf.append({"run": run["name"], "pair": run["pair"], "dressing": list(steps.values())[0][2], "steps": len(steps),
                             "frame_ms": statistics.mean(v[0] for v in steps.values()), "gpu_ms": statistics.mean(v[1] for v in steps.values()),
                             "gpu_before_c": run.get("gpu_before_c"), "gpu_after_c": run.get("gpu_after_c"), "result": run.get("result", "")[:80]})
        starts = [i for i, l in enumerate(lines) if "GTPROFILE capture " in l]
        for n, i in enumerate(starts):
            m = CAPTURE.search(lines[i])
            if not m:
                continue
            end = starts[n + 1] if n + 1 < len(starts) else len(lines)
            end = next((j for j in range(i + 1, end) if "GTPROFILE end" in lines[j] or "GTPROFILE capture" in lines[j]), end)
            pipes = split_pipelines(lines[i + 1:end])
            frame, passes, trimmed = top_level(pipes.get("graphics", []))
            compute = pipes.get("compute", [])
            async_ms = compute[0][2] if compute else 0.0
            _cf, cpasses, ctrimmed = top_level(compute)
            cpasses.pop("(outside Scene)", None)
            for k, v in cpasses.items():
                passes["[async] " + k] = v
            picture = m.group(1)
            gpu = [x.strip() for x in m.group(9).split(",")]
            rec = {"run": run["name"], "pair": run["pair"], "picture": picture, "view": view_key(picture), "capture": int(m.group(2)),
                   "dressing": int(m.group(4)), "res": "%sx%s" % (m.group(5), m.group(6)), "r.ScreenPercentage": float(m.group(7)),
                   "r.Nanite.AllowVoxels": int(m.group(8)), "gpu_temp_c": int(gpu[0]) if gpu and gpu[0].isdigit() else None,
                   "gpu_clock_reasons": gpu[1] if len(gpu) > 1 else None,
                   "gpu_clock_mhz": int(re.sub(r"\D", "", gpu[2]) or 0) if len(gpu) > 2 else None,
                   "scene": m.group(10), "frame_ms": frame, "async_compute_ms": async_ms,
                   "passes": {k: {"ms": round(v["ms"], 4), "draws": v["draws"], "dispatches": v["dispatches"], "prims": v["prims"]} for k, v in passes.items()}}
            if frame is None:
                rec["error"] = "no Graphics pipeline tree with a Scene node after the capture line"
            records.append(rec)
            name = "%s__%s__%d.txt" % (run["name"], picture, int(m.group(2)))
            with io.open(os.path.join(DUMPS, name), "w", encoding="utf-8") as f:
                f.write("# %s  %s  dressing %s  res %s  sp %s  gpu %s\n# %s\n" % (run["name"], picture, m.group(4), rec["res"], m.group(7), m.group(9), m.group(10)))
                f.write("# frame %.3f ms (graphics), async compute %.3f ms\n" % (frame or -1, async_ms))
                f.write("\n".join(trimmed) + "\n")
                f.write("# async compute pipeline (overlaps the graphics one)\n" + "\n".join(ctrimmed) + "\n")

    good = [r for r in records if r.get("frame_ms") is not None]
    views = sorted({r["view"] for r in good})
    names = sorted({p for r in good for p in r["passes"]})

    def med(view, state, p):
        vals = [r["passes"].get(p, {"ms": 0.0})["ms"] for r in good if r["view"] == view and r["dressing"] == state]
        return statistics.median(vals) if vals else None

    def med_frame(view, state, key):
        vals = [r[key] for r in good if r["view"] == view and r["dressing"] == state]
        return statistics.median(vals) if vals else None

    per_view = {}
    for v in views:
        per_view[v] = {"captures": {s: sum(1 for r in good if r["view"] == v and r["dressing"] == s) for s in (0, 1)},
                       "frame": {"off": med_frame(v, 0, "frame_ms"), "on": med_frame(v, 1, "frame_ms")},
                       "async_compute": {"off": med_frame(v, 0, "async_compute_ms"), "on": med_frame(v, 1, "async_compute_ms")},
                       "gpu_clock_mhz": {"off": med_frame(v, 0, "gpu_clock_mhz"), "on": med_frame(v, 1, "gpu_clock_mhz")},
                       "gpu_temp_c": {"off": med_frame(v, 0, "gpu_temp_c"), "on": med_frame(v, 1, "gpu_temp_c")},
                       "passes": {}}
        for p in names:
            off, on = med(v, 0, p), med(v, 1, p)
            if off is None or on is None:
                continue
            per_view[v]["passes"][p] = {"off": round(off, 3), "on": round(on, 3), "delta": round(on - off, 3)}
        f = per_view[v]["frame"]
        if f["off"] is not None and f["on"] is not None:
            f["delta"] = round(f["on"] - f["off"], 3)
    complete = [v for v in views if per_view[v]["frame"].get("delta") is not None]
    avg = {}
    for p in names:
        rows = [per_view[v]["passes"][p] for v in complete if p in per_view[v]["passes"]]
        if len(rows) == len(complete) and rows:
            avg[p] = {k: round(statistics.mean(r[k] for r in rows), 3) for k in ("off", "on", "delta")}
    frame_avg = {k: round(statistics.mean(per_view[v]["frame"][k] for v in complete), 3) for k in ("off", "on", "delta")} if complete else {}
    async_avg = {k: round(statistics.mean(per_view[v]["async_compute"][k] for v in complete), 3) for k in ("off", "on")} if complete else {}
    if async_avg:
        async_avg["delta"] = round(async_avg["on"] - async_avg["off"], 3)
    top8 = sorted(avg, key=lambda p: -avg[p]["on"])[:8]
    grow5 = sorted(avg, key=lambda p: -avg[p]["delta"])[:5]
    overall = {}
    for s in (0, 1):
        rs = [x for x in perf if x["dressing"] == s]
        if rs:
            overall["on" if s else "off"] = {"runs": len(rs), "frame_ms": round(statistics.mean(x["frame_ms"] for x in rs), 2),
                                             "gpu_ms": round(statistics.mean(x["gpu_ms"] for x in rs), 2)}
    if "on" in overall and "off" in overall:
        overall["delta"] = {k: round(overall["on"][k] - overall["off"][k], 2) for k in ("frame_ms", "gpu_ms")}
    scene_stats = {}
    for r in good:
        scene_stats.setdefault("%s d%d" % (r["picture"], r["dressing"]), r["scene"])
    out = {"about": __doc__.split("\n")[0], "route": "ProfileGPU under -game -RenderOffScreen (UE 5.8 RHI GPU profiler, log dump)",
           "captures": len(records), "captures_parsed": len(good), "views": views, "views_with_both_states": complete,
           "frame_average": frame_avg, "async_compute_average": async_avg, "average": avg, "top8_by_on_ms": top8, "grow5": grow5, "per_view": per_view,
           "overall_gtperf": overall, "gtperf_runs": perf, "scene_stats_first": scene_stats, "records": records}
    if COMPARE and os.path.isfile(COMPARE):
        before = json.load(io.open(COMPARE, encoding="utf-8"))
        shared = [v for v in complete if v in before.get("per_view", {}) and before["per_view"][v]["frame"].get("delta") is not None]

        def mean_delta(pv, p):
            vals = [pv[v]["passes"].get(p, {}).get("delta") for v in shared]
            return round(statistics.mean(vals), 3) if shared and all(x is not None for x in vals) else None
        rows = []
        for p in list(before.get("grow5", [])) + [x for x in grow5 if x not in before.get("grow5", [])]:
            rows.append({"pass": p, "before": mean_delta(before["per_view"], p), "after": mean_delta(per_view, p)})
        fb = [before["per_view"][v]["frame"]["delta"] for v in shared]
        fa = [per_view[v]["frame"]["delta"] for v in shared]
        out["compare"] = {"with": COMPARE, "views": shared, "frame_delta": {"before": round(statistics.mean(fb), 3) if fb else None,
                          "after": round(statistics.mean(fa), 3) if fa else None}, "passes": rows}
    with io.open(os.path.join(DOCS, TAG + "_profile.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)

    md = ["# %s GPU profile: The Hide, dressing off / on (ms)" % TITLE, "",
          "ProfileGPU, `-game -RenderOffScreen`, %s, Graphics pipeline; the median of the captures per view and state (with 2 captures: their mean), then "
          "the mean over the %d views (%s). Generated by `Art/dressing/ld8_profile.py`; raw trees in this folder." %
          (good[0]["res"] if good else "?", len(complete), ", ".join(complete)), "",
          "| pass | off | on | delta |", "|---|---|---|---|"]
    if frame_avg:
        md.append("| **frame (graphics)** | %.2f | %.2f | %+.2f |" % (frame_avg["off"], frame_avg["on"], frame_avg["delta"]))
        md.append("| **async compute total (overlapped)** | %.2f | %.2f | %+.2f |" % (async_avg["off"], async_avg["on"], async_avg["delta"]))
    for p in top8:
        md.append("| %s | %.2f | %.2f | %+.2f |" % (p, avg[p]["off"], avg[p]["on"], avg[p]["delta"]))
    md += ["", "The 5 passes that grow the most (delta per view, ms):", "",
           "| pass | mean | " + " | ".join(complete) + " |", "|---|---|" + "---|" * len(complete)]
    for p in grow5:
        md.append("| %s | %+.2f | " % (p, avg[p]["delta"]) + " | ".join("%+.2f" % per_view[v]["passes"][p]["delta"] for v in complete) + " |")
    md += ["", "Per view, the frame (graphics pipeline):", "", "| view | captures off/on | off | on | delta | GPU clock MHz off/on | GPU C off/on |", "|---|---|---|---|---|---|---|"]
    for v in complete:
        f = per_view[v]["frame"]
        c, t = per_view[v]["gpu_clock_mhz"], per_view[v]["gpu_temp_c"]
        md.append("| %s | %d/%d | %.2f | %.2f | %+.2f | %s/%s | %s/%s |" % (v, per_view[v]["captures"][0], per_view[v]["captures"][1], f["off"], f["on"], f["delta"], c["off"], c["on"], t["off"], t["on"]))
    if overall:
        md += ["", "GTPERF over hide_shots steps 1-30 (mean of the step means, then over the runs):", "",
               "| state | runs | frame | GPU |", "|---|---|---|---|"]
        for k in ("off", "on"):
            if k in overall:
                md.append("| %s | %d | %.2f | %.2f |" % (k, overall[k]["runs"], overall[k]["frame_ms"], overall[k]["gpu_ms"]))
        if "delta" in overall:
            md.append("| delta | | %+.2f | %+.2f |" % (overall["delta"]["frame_ms"], overall["delta"]["gpu_ms"]))
    if "compare" in out:
        c = out["compare"]
        md += ["", "Delta (on - off) before -> after, mean over the %d shared views (%s):" % (len(c["views"]), os.path.basename(c["with"])), "",
               "| pass | before | after |", "|---|---|---|",
               "| **frame (graphics)** | %s | %s |" % (c["frame_delta"]["before"], c["frame_delta"]["after"])]
        for r in c["passes"]:
            md.append("| %s | %s | %s |" % (r["pass"], r["before"], r["after"]))
    with io.open(os.path.join(DUMPS, TAG + "_profile.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print("LD8_PROFILE captures %d (parsed %d), views %s" % (len(records), len(good), complete))
    print("\n".join(md))


if __name__ == "__main__":
    main()
