"""Diagnose (and self-heal) the commandlet-built biome PCG graphs.

RUN IN-EDITOR with the map holding the DRESSLAB_PCG_* actors open (the
regenerate step needs a ticking editor):
  py "C:/GrandTour/Art/dressing/ported/ClaudeDiagnoseBiomePCG.py"

Dumps every node's saved configuration into the report. Known suspect
(verified in 5.8 source): UPCGGetLandscapeSettings created in a commandlet may
save ActorSelection=ByClass with a NULL ActorSelectionClass (the PostLoad
fallback only fires for non-ByClass) -> getter matches nothing -> every branch
spawns zero. If found, this script PATCHES the class to LandscapeProxy, saves
the graph, and regenerates. Node enumeration goes edges -> pins -> node
(GetNodes is not script-exposed).
"""

from __future__ import annotations

import json
from pathlib import Path
import traceback

import unreal


ASSET_DIR = "/Game/OWGame/Dev/DressingLab"
GRAPHS = ["PCG_OWForest", "PCG_OWMeadow", "PCG_OWScree"]
ACTORS = ["DRESSLAB_PCG_Forest", "DRESSLAB_PCG_Meadow", "DRESSLAB_PCG_Scree"]
REPORT_PATH = Path(__file__).with_name("ClaudeDiagnoseBiomePCGReport.json")

result = {"ok": True, "steps": {}}


def step(name):
    def decorate(func):
        try:
            value = func()
            result["steps"][name] = {"ok": True, "value": value}
            return value
        except Exception as exc:
            result["ok"] = False
            result["steps"][name] = {
                "ok": False,
                "error": repr(exc),
                "traceback": traceback.format_exc(),
            }
            unreal.log_error(f"BIOME_DIAG {name}: {exc!r}")
            return None

    return decorate


def _nodes_of(graph):
    nodes = {}
    for edge in graph.get_all_edges():
        for pin_prop in ("input_pin", "output_pin"):
            pin = edge.get_editor_property(pin_prop)
            if pin is None:
                continue
            node = pin.get_editor_property("node")
            if node is not None:
                nodes[node.get_name()] = node
    return nodes


def _describe_settings(s, patches):
    """Return a dict describing one settings object; append patch notes."""
    info = {"class": type(s).__name__}
    try:
        if isinstance(s, unreal.PCGGetLandscapeSettings):
            sel = s.get_editor_property("actor_selector")
            cls = sel.get_editor_property("actor_selection_class")
            info["actor_filter"] = str(sel.get_editor_property("actor_filter"))
            info["actor_selection"] = str(sel.get_editor_property("actor_selection"))
            info["actor_selection_class"] = str(cls) if cls else "NULL"
            info["must_overlap_self"] = bool(sel.get_editor_property("must_overlap_self"))
            if cls is None:
                sel.set_editor_property("actor_selection_class",
                                        unreal.LandscapeProxy.static_class())
                s.set_editor_property("actor_selector", sel)
                s.modify()
                info["PATCHED"] = "actor_selection_class NULL -> LandscapeProxy"
                patches.append(info["PATCHED"])
        elif isinstance(s, unreal.PCGSurfaceSamplerSettings):
            info["points_per_m2"] = float(s.get_editor_property("points_per_squared_meter"))
            info["unbounded"] = bool(s.get_editor_property("unbounded"))
        elif isinstance(s, unreal.PCGAttributeFilteringSettings):
            helpers = unreal.PCGAttributePropertySelectorBlueprintHelpers
            info["target_attribute"] = str(helpers.get_attribute_name(
                s.get_editor_property("target_attribute")))
            info["operator"] = str(s.get_editor_property("operator"))
            info["use_constant_threshold"] = bool(s.get_editor_property("use_constant_threshold"))
            const = s.get_editor_property("attribute_types")
            info["threshold_type"] = str(const.get_editor_property("type"))
            info["threshold_value"] = float(const.get_editor_property("double_value"))
        elif isinstance(s, unreal.PCGDensityFilterSettings):
            info["bounds"] = [float(s.get_editor_property("lower_bound")),
                              float(s.get_editor_property("upper_bound"))]
        elif isinstance(s, unreal.PCGDistanceSettings):
            info["set_density"] = bool(s.get_editor_property("set_density"))
            info["maximum_distance"] = float(s.get_editor_property("maximum_distance"))
        elif isinstance(s, unreal.PCGStaticMeshSpawnerSettings):
            entries = []
            params = s.get_editor_property("mesh_selector_parameters")
            for e in params.get_editor_property("mesh_entries"):
                desc = e.get_editor_property("descriptor")
                mesh = desc.get_editor_property("static_mesh")
                mesh_path = str(mesh.get_path_name()) if mesh else "NULL"
                loadable = unreal.load_asset(mesh_path.split(".")[0] + "." +
                                             mesh_path.split(".")[-1]) is not None if mesh else False
                entries.append({"mesh": mesh_path, "loads": loadable,
                                "weight": int(e.get_editor_property("weight"))})
            info["entries"] = entries
    except Exception as exc:
        info["dump_error"] = repr(exc)
    return info


def _diagnose_graph(name):
    patches = []
    path = f"{ASSET_DIR}/{name}"
    graph = unreal.load_asset(path)
    if graph is None:
        raise RuntimeError(f"graph missing: {path}")
    nodes = _nodes_of(graph)
    dump = {"edges": len(graph.get_all_edges()), "nodes": len(nodes), "detail": {}}
    for node_name, node in sorted(nodes.items()):
        s = node.get_editor_property("settings_interface")
        dump["detail"][node_name] = _describe_settings(s, patches) if s else {"class": "NO SETTINGS"}
    if patches:
        if not unreal.EditorAssetLibrary.save_loaded_asset(graph):
            raise RuntimeError(f"patched {name} but save failed")
        dump["patched_and_saved"] = patches
    return dump


for graph_name in GRAPHS:
    step(f"diag_{graph_name}")(lambda n=graph_name: _diagnose_graph(n))


@step("regenerate")
def regenerate():
    actors_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    found = {a.get_actor_label(): a for a in actors_sub.get_all_level_actors()
             if a.get_actor_label() in ACTORS}
    out = {}
    for label in ACTORS:
        actor = found.get(label)
        if actor is None:
            out[label] = "ACTOR MISSING"
            continue
        comp = actor.get_component_by_class(unreal.PCGComponent)
        if comp is None:
            out[label] = "NO PCGComponent"
            continue
        graph = comp.get_graph() if hasattr(comp, "get_graph") else None
        out[label] = f"graph={graph.get_name() if graph else 'UNKNOWN'}; generate fired"
        comp.generate(True)
    return out


REPORT_PATH.write_text(json.dumps(result, indent=2, default=str))
if not result["ok"]:
    raise RuntimeError(f"one or more steps failed - see {REPORT_PATH}")
unreal.log("BIOME_DIAG complete - read the report; generation is async, give it a few seconds")
