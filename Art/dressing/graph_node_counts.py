"""Stage B structural check (docs/LandscapeMigrationManifest.md 9.B.6). READ-ONLY: loads graphs, never saves.

Collect mode (inside Unreal, headless PythonScript commandlet; works on either project):
  env GT_GRAPHS  comma-separated graph package paths (default: the 6 DressingLab biome graphs)
  env GT_REPORT  absolute report JSON path (default docs/landscape_migration/graph_nodes_<project>.json)
  Per graph: node count, node-settings class counts, getter actor classes, edge count and edge
  signature counts ("<from settings class>.<pin> -> <to settings class>.<pin>").
  Target: Art/dressing/graph_node_counts.bat [tag].  Source (read-only run, own -abslog outside the source):
  UnrealEditor-Cmd.exe D:\\Dev\\OWGameUE\\OWGameUE.uproject -run=PythonScript "-Script=C:\\GrandTour\\Art\\dressing\\graph_node_counts.py"
      -NullRHI -Unattended -NoSplash -NoSound "-abslog=<scratch or docs path>"   (with GT_REPORT set)

Diff mode (plain Python, no Unreal):
  python graph_node_counts.py diff <source.json> <target.json> [out.json]
  Prints and writes the per-graph class-count and edge-signature differences.
"""
import os, sys, json, time, traceback
from collections import Counter

DEFAULT_GRAPHS = ["/Game/OWGame/Dev/DressingLab/PCG_OW" + g
                  for g in ("Forest", "Meadow", "Scree", "Road", "Cliff", "Alpine")]


def _diff_counts(a, b):
    keys = sorted(set(a) | set(b))
    return {k: {"source": a.get(k, 0), "target": b.get(k, 0), "delta": b.get(k, 0) - a.get(k, 0)}
            for k in keys if a.get(k, 0) != b.get(k, 0)}


def diff_mode(src_path, dst_path, out_path=None):
    S = json.load(open(src_path, encoding="utf-8"))
    T = json.load(open(dst_path, encoding="utf-8"))
    out = {"source": src_path, "target": dst_path, "graphs": {}}
    for g in sorted(set(S["graphs"]) | set(T["graphs"])):
        s, t = S["graphs"].get(g, {}), T["graphs"].get(g, {})
        d = {"nodes": [s.get("node_count"), t.get("node_count")],
             "edges": [s.get("edge_count"), t.get("edge_count")],
             "class_diff": _diff_counts(s.get("class_counts", {}), t.get("class_counts", {})),
             "getter_class_diff": _diff_counts(Counter(s.get("getter_actor_classes", [])),
                                               Counter(t.get("getter_actor_classes", []))),
             "edge_sig_diff": _diff_counts(s.get("edge_signatures", {}), t.get("edge_signatures", {}))}
        d["identical"] = not (d["class_diff"] or d["getter_class_diff"] or d["edge_sig_diff"])
        out["graphs"][g] = d
        print("%s  nodes %s -> %s  edges %s -> %s  %s" % (g.rsplit("/", 1)[1], d["nodes"][0], d["nodes"][1],
              d["edges"][0], d["edges"][1], "IDENTICAL" if d["identical"] else "DIFFERS"))
        for k, v in d["class_diff"].items():
            print("   class  %-45s %+d" % (k, v["delta"]))
        for k, v in d["getter_class_diff"].items():
            print("   getter %-45s %+d" % (k, v["delta"]))
        for k, v in d["edge_sig_diff"].items():
            print("   edge   %-70s %+d" % (k, v["delta"]))
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=1)
    return out


def collect_mode():
    import unreal
    proj = os.path.splitext(os.path.basename(unreal.Paths.get_project_file_path()))[0]
    graphs = [g.strip() for g in os.environ.get("GT_GRAPHS", "").split(",") if g.strip()] or DEFAULT_GRAPHS
    out_path = os.environ.get("GT_REPORT", "").strip() or \
        r"C:\GrandTour\docs\landscape_migration\graph_nodes_%s.json" % proj
    report = {"ok": False, "project": proj, "started": time.strftime("%Y-%m-%d %H:%M:%S"), "graphs": {}, "steps": []}

    def settings_of(node):
        s = node.get_editor_property("settings_interface")
        if s is None:
            return None, "NO_SETTINGS"
        cn = s.get_class().get_name()
        if cn == "PCGSettingsInstance":
            try:
                inner = s.get_editor_property("settings")
                cn = "PCGSettingsInstance:" + (inner.get_class().get_name() if inner else "None")
            except Exception:
                pass
        return s, cn

    def pin_sig(pin):
        node = pin.get_editor_property("node") if pin else None
        _s, cn = settings_of(node) if node else (None, "NO_NODE")
        try:
            label = str(pin.get_editor_property("properties").get_editor_property("label"))
        except Exception:
            label = "?"
        return "%s.%s" % (cn, label)

    for g in graphs:
        rec = {"name": g, "ok": False, "err": None}
        try:
            graph = unreal.load_asset(g)
            if graph is None:
                raise RuntimeError("graph not found: " + g)
            nodes = list(graph.get_editor_property("nodes") or [])
            for extra in (graph.get_input_node(), graph.get_output_node()):
                if extra is not None and extra not in nodes:
                    nodes.append(extra)
            classes, getters = Counter(), []
            for n in nodes:
                s, cn = settings_of(n)
                classes[cn] += 1
                sel = None
                try:
                    sel = s.get_editor_property("actor_selector") if s is not None else None
                except Exception:
                    sel = None
                if sel is not None:
                    try:
                        ac = sel.get_editor_property("actor_selection_class")
                        getters.append("%s:%s" % (cn, ac.get_path_name() if ac else "None"))
                    except Exception:
                        getters.append("%s:?" % cn)
            edges = list(graph.get_all_edges() or [])
            sigs = Counter("%s -> %s" % (pin_sig(e.get_editor_property("input_pin")),
                                         pin_sig(e.get_editor_property("output_pin"))) for e in edges)
            report["graphs"][g] = {"node_count": len(nodes), "class_counts": dict(sorted(classes.items())),
                                   "getter_actor_classes": sorted(getters), "edge_count": len(edges),
                                   "edge_signatures": dict(sorted(sigs.items()))}
            rec["ok"] = True
        except Exception:
            rec["err"] = traceback.format_exc()[-2000:]
        report["steps"].append(rec)
    report["ok"] = all(s["ok"] for s in report["steps"])
    report["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    unreal.log("GRAPH_NODE_COUNTS done ok=%s project=%s graphs=%d report=%s" % (report["ok"], proj, len(graphs), out_path))


if len(sys.argv) >= 4 and sys.argv[1] == "diff":
    diff_mode(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
else:
    collect_mode()
