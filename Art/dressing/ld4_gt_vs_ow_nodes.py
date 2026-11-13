"""Leg dressing LD4 (docs/LEG_DRESSING_PLAN.md, "Tests"): the GT graph variants' node counts against the OW graphs.

Plain Python (no Unreal). Reads two graph_node_counts.py reports - the OW graphs and the PCG_GT_* graphs - and checks
each GT graph's node-settings class counts against its OW graph plus the additions LD4 lists:
  - every Forest / Alpine tree stream (size classes): +1 attribute noise, +3 density filters, +4 transforms
    (Sapling and Young: the absolute uniform scale and the Z jitter), +2 spawners;
  - every soft stream (the Forest understorey, all of PCG_GT_Brush): a sampler, a weight filter (a band: 2), the slope
    band (normal-to-density + density filter), the exclusion (difference + density filter), the transform (a size-class
    stream: 2) and a spawner.
PCG_GT_Brush has no OW twin: its base is the graph's input and output nodes and the shared getters (landscape, exclusion
tag, 3 road-class corridors of 4 nodes).
  python Art/dressing/ld4_gt_vs_ow_nodes.py <ow.json> <gt.json> [out.json]
"""
import json
import sys
from collections import Counter

NOISE = "PCGAttributeNoiseSettings"
DFILT = "PCGDensityFilterSettings"
XFORM = "PCGTransformPointsSettings"
SPAWN = "PCGStaticMeshSpawnerSettings"
SAMPLER = "PCGSurfaceSamplerSettings"
AFILT = "PCGAttributeFilteringSettings"
N2D = "PCGNormalToDensitySettings"
DIFF = "PCGDifferenceSettings"


def tree_stream():
    return Counter({NOISE: 1, DFILT: 3, XFORM: 4, SPAWN: 2})


def soft_stream(band=False, size_class=False):
    return Counter({SAMPLER: 1, AFILT: 2 if band else 1, N2D: 1, DFILT: 2, DIFF: 1,
                    XFORM: 2 if size_class else 1, SPAWN: 1})


def expected_additions():
    forest = Counter()
    for _ in range(13):          # the mixed stream + 4 type layers x 3 density tiers
        forest += tree_stream()
    for _ in range(5 * 2):       # 5 forest layers x (bushes, cover plants)
        forest += soft_stream()
    alpine = Counter()
    for _ in range(2):           # dwarf firs, snowfield firs
        alpine += tree_stream()
    brush = Counter({"PCGGraphInputOutputSettings": 2, "PCGGetLandscapeSettings": 1, "PCGDataFromActorSettings": 1, "PCGGetSplineSettings": 3,
                     "PCGSplineSamplerSettings": 3, "PCGProjectionSettings": 3, "PCGBoundsModifierSettings": 3})
    brush += soft_stream()                        # bushes > 0.5
    brush += soft_stream(band=True)               # bushes 0.2-0.5
    brush += soft_stream(size_class=True)         # saplings
    brush += soft_stream(size_class=True)         # young trees
    brush += soft_stream()                        # cover plants
    return {"Forest": forest, "Meadow": Counter(), "Scree": Counter(), "Alpine": alpine, "Brush": brush}


def main(ow_path, gt_path, out_path=None):
    ow = json.load(open(ow_path, encoding="utf-8"))["graphs"]
    gt = json.load(open(gt_path, encoding="utf-8"))["graphs"]
    by_name = lambda graphs: {g.rsplit("/", 1)[-1].split(".")[0]: v for g, v in graphs.items()}
    ow, gt = by_name(ow), by_name(gt)
    adds = expected_additions()
    out, ok = {}, True
    for biome, add in adds.items():
        g = gt.get("PCG_GT_" + biome)
        o = ow.get("PCG_OW" + biome, {"class_counts": {}, "node_count": 0, "edge_count": 0})
        if g is None:
            out[biome] = {"ok": False, "error": "PCG_GT_%s missing from %s" % (biome, gt_path)}
            ok = False
            continue
        want = Counter(o["class_counts"]) + add
        have = Counter(g["class_counts"])
        diff = {k: {"want": want.get(k, 0), "have": have.get(k, 0)} for k in sorted(set(want) | set(have))
                if want.get(k, 0) != have.get(k, 0)}
        rec = {"ow_nodes": o["node_count"], "gt_nodes": g["node_count"], "added": g["node_count"] - o["node_count"],
               "listed_additions": sum(add.values()), "ow_edges": o["edge_count"], "gt_edges": g["edge_count"],
               "added_by_class": {k: have.get(k, 0) - Counter(o["class_counts"]).get(k, 0)
                                  for k in sorted(set(have) | set(o["class_counts"]))
                                  if have.get(k, 0) != Counter(o["class_counts"]).get(k, 0)},
               "mismatch": diff, "ok": not diff}
        ok = ok and rec["ok"]
        out[biome] = rec
        print("PCG_GT_%-7s nodes %4d (OW %4d, +%d; listed +%d)  edges %4d (OW %4d)  %s%s" % (
            biome, rec["gt_nodes"], rec["ow_nodes"], rec["added"], rec["listed_additions"], rec["gt_edges"],
            rec["ow_edges"], "MATCH" if rec["ok"] else "MISMATCH ", "" if rec["ok"] else json.dumps(diff)))
        print("   added by class: %s" % ", ".join("%s %+d" % (k.replace("PCG", "").replace("Settings", ""), v)
                                                   for k, v in rec["added_by_class"].items()))
    result = {"ow": ow_path, "gt": gt_path, "graphs": out, "ok": ok}
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=1)
    print("== GT vs OW node counts: %s" % ("MATCH the listed additions" if ok else "MISMATCH"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
