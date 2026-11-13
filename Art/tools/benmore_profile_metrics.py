"""Read UE CSVs without Unreal. Preserve memory/counter units and frame hitches."""
import csv
import math
import statistics
from pathlib import Path


def compare_isolation(runs):
    """ABBA screening only: compare capture summaries, not independent frames."""
    groups = {}
    for run in runs:
        if run['feature'] != 'baseline':
            groups.setdefault((run['view'], run['feature']), []).append(run)
    comparisons = []
    for (view, feature), group in groups.items():
        if [r['disabled'] for r in group] != [False, True, True, False]:
            raise ValueError('Incomplete or out-of-order ABBA comparison')
        timing = {}
        for metric in ['FrameTime', 'GPUTime']:
            timing[metric] = {}
            for stat in ['median', 'p95', 'p99']:
                values = [r['analysis']['metrics'][metric][stat] for r in group]
                baseline = statistics.fmean([values[0], values[3]])
                disabled = statistics.fmean(values[1:3])
                drift = abs(values[0] - values[3])
                repeat_difference = abs(values[1] - values[2])
                delta = baseline - disabled
                timing[metric][stat] = {
                    'baseline_mean_of_window_statistics_ms': baseline,
                    'disabled_mean_of_window_statistics_ms': disabled,
                    'saved_ms': delta, 'saved_percent': 100 * delta / baseline if baseline else None,
                    'baseline_drift_ms': drift, 'disabled_repeat_difference_ms': repeat_difference,
                    'exceeds_screening_threshold': delta > max(.5, .05 * baseline, drift, repeat_difference),
                }
        memory_valid = all(r['analysis']['local_memory'] is not None and
                           r['analysis']['local_memory']['over_budget_frames'] == 0 and
                           r['analysis']['local_memory'].get('unavailable_frames',0) == 0 for r in group)
        comparisons.append({'view': view, 'feature': feature, 'timings': timing,
            'memory_budget_valid': memory_valid,
            'promotion_ready': False,
            'note': 'Diagnostic dependency-inclusive delta; confirm repeats, traces, motion and visual quality before promotion. Do not add feature deltas.'})
    return comparisons


def summary(values):
    ordered = sorted(values)
    return {
        "samples": len(values), "mean": statistics.fmean(values),
        "median": statistics.median(values), "min": ordered[0], "max": ordered[-1],
        "p95": ordered[math.ceil(.95 * len(values)) - 1],
        "p99": ordered[math.ceil(.99 * len(values)) - 1],
    }


def analyse(path, minimum_frames=60):
    columns = {}
    memory_pairs = []
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.reader(stream))
        if not rows:
            raise ValueError("Empty CSV capture")
        initial_header = rows[0]
        header = initial_header
        # UE can append counters during recording. Its final header names the
        # additional trailing columns; earlier frames legitimately lack them.
        for row in rows[1:]:
            if row and row[0] == 'EVENTS' and 'FrameTime' in row:
                if row[:len(header)] != header:
                    raise ValueError("CSV header changed column ordering")
                header = row
        if "FrameTime" not in header:
            raise ValueError("Missing FrameTime")
        duplicates = {name for name in header if header.count(name) > 1}
        critical = {'EVENTS', 'FrameTime', 'GPUTime', 'GameThreadTime',
                    'RenderThreadTime', 'RHIThreadTime', 'GPUMem/LocalBudgetMB',
                    'GPUMem/LocalUsedMB', 'VSM/FreePages'}
        if duplicates & critical:
            raise ValueError('Duplicate critical CSV columns: '+', '.join(sorted(duplicates & critical)))
        # UE can emit two unrelated counters under an identical display name
        # (observed FMsgLogf/FMsgLogfCount). Keep each series by column position;
        # never merge them or silently discard one. Retain the raw header for
        # detecting the repeated-header footer and appended-column validation.
        occurrences = {}
        names = []
        for name in header:
            occurrences[name] = occurrences.get(name, 0) + 1
            names.append(f'{name}#{occurrences[name]}' if name in duplicates else name)
        if len(names) != len(set(names)):
            raise ValueError('CSV column disambiguation collision')
        columns = {name: [] for name in names if name != "EVENTS"}
        for row in rows[1:]:
            if not row:
                continue
            if row == header or row == initial_header or row[0].startswith("["):
                break  # UE repeats its header and appends metadata at the end.
            if not len(initial_header) <= len(row) <= len(header):
                raise ValueError("Incomplete CSV row; capture may not have finished")
            frame = {}
            for name, raw in zip(names, row):
                if name == "EVENTS":
                    continue  # Event labels may be populated on legitimate frames.
                try:
                    number = float(raw)
                except ValueError as exc:
                    raise ValueError(f"Non-numeric value in {name}: {raw!r}") from exc
                if not math.isfinite(number):
                    raise ValueError(f"Non-finite value in {name}")
                columns[name].append(number)
                frame[name] = number
            budget = frame.get("GPUMem/LocalBudgetMB")
            used = frame.get("GPUMem/LocalUsedMB")
            if budget is not None and used is not None:
                if budget < 0 or used < 0 or (budget == 0 and used != 0):
                    raise ValueError("Invalid GPU memory budget/usage telemetry")
                # A simultaneous zero budget/usage is a missing RHI sample,
                # observed during CSV startup. Preserve its frame timing, but
                # never interpret it as real headroom or a passed memory gate.
                if budget > 0:
                    memory_pairs.append((budget, used))
    frames = columns["FrameTime"]
    gpu = columns.get("GPUTime", [])
    if len(frames) < minimum_frames or len(gpu) != len(frames):
        raise ValueError("Too few frames or missing GPUTime")
    if any(t <= 0 for t in frames) or any(t < 0 for t in gpu) or not any(t > 0 for t in gpu):
        raise ValueError("Invalid frame/GPU timing")
    metrics = {key: summary(values) for key, values in columns.items() if values}
    warnings = []
    if duplicates:
        warnings.append('Duplicate counters preserved with # occurrence suffixes: '+', '.join(sorted(duplicates)))
    for key in ("GameThreadTime", "RenderThreadTime", "RHIThreadTime"):
        if key not in metrics or metrics[key]["p95"] < .01:
            warnings.append(f"{key} missing or near zero; verify in Timing Insights")
    memory = None
    if memory_pairs:
        headroom = [budget - used for budget, used in memory_pairs]
        memory = {
            "samples": len(memory_pairs), "minimum_headroom_mb": min(headroom),
            "unavailable_frames": len(frames)-len(memory_pairs),
            "coverage_fraction": len(memory_pairs)/len(frames),
            "peak_usage_fraction": max(used / budget for budget, used in memory_pairs),
            "over_budget_frames": sum(used > budget for budget, used in memory_pairs),
            "below_proposed_headroom_frames": sum(
                used > .85 * budget or budget - used < 512 for budget, used in memory_pairs),
        }
        if memory['unavailable_frames']:
            warnings.append(f"GPU memory telemetry unavailable for {memory['unavailable_frames']} frames; memory gate incomplete")
    else:
        warnings.append("Missing DXGI local budget/usage CSV channels")
    return {
        "frames": len(frames), "duration_s": sum(frames) / 1000,
        "frame_hitches": {str(limit): {"count": sum(t > limit for t in frames),
            "percent": 100 * sum(t > limit for t in frames) / len(frames)}
            for limit in (33.33, 50, 100)},
        "metrics": metrics, "local_memory": memory, "warnings": warnings,
        "units_note": "Timing columns are ms; GPUMem/*MB are MB; GTWater/ActiveCells and other counters are not timings.",
    }
