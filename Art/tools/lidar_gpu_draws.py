"""Group the two native graphics profiles from a moving LiDAR material study."""

import argparse
from collections import Counter
import json
from pathlib import Path
import re


HEADER = re.compile(r"GPU Profile for Frame (\d+) - Graphics pipeline (\d+) - GPU (\d+)")
ROW = re.compile(r"( *)([\d.]+)%\s+([\d.]+)ms(?: \+ [\d.]+ Wait)?   (.+)")
DRAW = re.compile(r"(.+) (\S+) \(\d+ instances\)")
PASSES = ("BasePass", "RenderVelocities(Opaque)", "ShadowDepths")


def read_profiles(log):
    profiles = []
    active = None
    for line in log.splitlines():
        body = line.partition("LogRHI: Display: ")[2]
        header = HEADER.fullmatch(body)
        if header:
            frame, queue, device = map(int, header.groups())
            if queue != 0 or device != 0:
                raise ValueError(f"Unexpected graphics queue at frame {frame}")
            active = {"frame": frame, "passes": {}}
            profiles.append(active)
            path = []
            continue
        if re.fullmatch(r".+ pipeline \d+ - GPU \d+", body):
            active = None
        if active is None:
            continue
        row = ROW.fullmatch(body)
        if not row:
            continue
        depth = len(row[1]) // 3
        busy, event = float(row[3]), row[4]
        if depth > len(path):
            raise ValueError(f"Missing event parent at {event}")
        path[depth:] = [event]
        if event in PASSES:
            if event in active["passes"]:
                raise ValueError(f"Duplicate inclusive pass {event}")
            active["passes"][event] = dict(busy_ms=busy, draws=Counter(), costs=Counter())
        match = DRAW.fullmatch(event)
        if match:
            scope = next((name for name in path if name in PASSES), None)
            if scope:
                data = active["passes"][scope]
                key = match.groups()
                data["costs"][key] += busy
                data["draws"][key] += 1
    if len(profiles) != 2 or profiles[0]["frame"] >= profiles[1]["frame"]:
        raise ValueError("Expected two distinct, ordered graphics frames")
    for profile in profiles:
        if set(profile["passes"]) != set(PASSES):
            raise ValueError(f"Incomplete pass hierarchy in frame {profile['frame']}")
        for data in profile["passes"].values():
            costs, draws = data.pop("costs"), data.pop("draws")
            if not costs or data["busy_ms"] <= 0:
                raise ValueError("No timed material draws")
            data["named_draw_ms"] = round(sum(costs.values()), 2)
            data["unattributed_ms"] = round(data["busy_ms"] - data["named_draw_ms"], 2)
            data["materials"] = [
                dict(
                    material=material, mesh=mesh, events=draws[material, mesh], busy_ms=round(ms, 2)
                )
                for (material, mesh), ms in costs.most_common()
            ]
    return profiles


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    folder = parser.parse_args().folder
    data = read_profiles((folder / "drive.log").read_text(errors="replace"))
    (folder / "material-draws.json").write_text(json.dumps(data, indent=2) + "\n")
