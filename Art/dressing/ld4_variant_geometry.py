"""Leg dressing LD4 step 1 (docs/LEG_DRESSING_PLAN.md, LD4 "Tree variants"): READ-ONLY record of the tree variants.

Headless through ld4_variant_geometry.bat (PythonScript commandlet); loads meshes, never saves. Per variant in
/Game/OWGame/Dev/DressingLab/Trees:
  - the source geometry (mesh description LOD0): vertex, triangle and polygon counts, and a position checksum
    (sum and sum of squares of every vertex position, so a moved vertex shows up even when the counts hold);
  - the built render data: LOD count, LOD0 vertices / triangles / sections, Nanite on/off, Nanite vertices / triangles;
  - the bounding box and the material slots (slot name -> material path);
  - no collision: Python cannot read a body setup, and in a commandlet the StaticMeshEditorSubsystem is None and the
    deprecated EditorStaticMeshLibrary getters return -1 (measured 2026-09-27). OWCreateTreeVariants logs each variant's
    shapes and trace flag itself, and OWCreateBiomePCG -Variant=GT checks the vendor Solid meshes.
  env GT_REPORT  the report path (default docs/landscape_migration/ld4_variants.json)
Compare two reports:  python Art/dressing/ld4_variant_geometry.py diff <before.json> <after.json>
  prints every field that differs per variant (exit 1 on any: collision is not recorded here, so none may change).
"""
import json
import os
import sys
import time
import traceback

TREES = "/Game/OWGame/Dev/DressingLab/Trees"


def diff_mode(before_path, after_path):
    b = json.load(open(before_path, encoding="utf-8"))["variants"]
    a = json.load(open(after_path, encoding="utf-8"))["variants"]
    geometry_diffs = {}
    for name in sorted(set(a) | set(b)):
        vb, va = b.get(name, {}), a.get(name, {})
        for key in sorted(set(va) | set(vb)):
            if key.startswith("_") or vb.get(key) == va.get(key):
                continue
            geometry_diffs.setdefault(name, {})[key] = [vb.get(key), va.get(key)]
    print("variants: %d before, %d after" % (len(b), len(a)))
    print("geometry/material differences: %s" % (json.dumps(geometry_diffs, indent=1) if geometry_diffs else "NONE"))
    return 0 if not geometry_diffs else 1


def collect_mode():
    import unreal
    out_path = os.environ.get("GT_REPORT", "").strip() or r"C:\GrandTour\docs\landscape_migration\ld4_variants.json"
    report = {"ok": True, "started": time.strftime("%Y-%m-%d %H:%M:%S"), "variants": {}, "errors": []}

    def record(path):
        mesh = unreal.load_asset(path)
        if mesh is None:
            raise RuntimeError("cannot load " + path)
        rec = {}
        desc = mesh.get_static_mesh_description(0)
        nv = desc.get_vertex_count()
        rec["src_vertices"] = int(nv)
        rec["src_triangles"] = int(desc.get_triangle_count())
        rec["src_polygons"] = int(desc.get_polygon_count())
        s = [0.0, 0.0, 0.0]
        q = 0.0
        valid = 0
        for i in range(nv):
            vid = unreal.VertexID(i)
            if not desc.is_vertex_valid(vid):
                continue
            p = desc.get_vertex_position(vid)
            s[0] += p.x
            s[1] += p.y
            s[2] += p.z
            q += p.x * p.x + p.y * p.y + p.z * p.z
            valid += 1
        rec["src_valid_vertices"] = valid
        rec["src_position_sum"] = [round(v, 1) for v in s]
        rec["src_position_sumsq"] = round(q, -2)
        rec["lods"] = int(mesh.get_num_lods())
        rec["lod0_vertices"] = int(mesh.get_num_vertices(0))
        rec["lod0_triangles"] = int(mesh.get_num_triangles(0))
        rec["lod0_sections"] = int(mesh.get_num_sections(0))
        rec["nanite_enabled"] = bool(mesh.get_editor_property("nanite_settings").get_editor_property("enabled"))
        rec["nanite_vertices"] = int(mesh.get_num_nanite_vertices())
        rec["nanite_triangles"] = int(mesh.get_num_nanite_triangles())
        box = mesh.get_bounding_box()
        rec["bounds_min"] = [round(box.min.x, 1), round(box.min.y, 1), round(box.min.z, 1)]
        rec["bounds_max"] = [round(box.max.x, 1), round(box.max.y, 1), round(box.max.z, 1)]
        rec["materials"] = [[str(m.get_editor_property("material_slot_name")),
                             m.get_editor_property("material_interface").get_path_name()
                             if m.get_editor_property("material_interface") else None]
                            for m in mesh.get_editor_property("static_materials")]
        return rec

    try:
        paths = sorted(unreal.EditorAssetLibrary.list_assets(TREES, False, False))
        for p in paths:
            name = p.rsplit("/", 1)[-1].split(".")[0]
            try:
                t0 = time.time()
                report["variants"][name] = record(p)
                report["variants"][name]["_seconds"] = round(time.time() - t0, 1)
            except Exception as exc:
                report["ok"] = False
                report["errors"].append("%s: %r" % (name, exc))
    except Exception as exc:
        report["ok"] = False
        report["errors"].append(traceback.format_exc())
    # _seconds is timing noise, not a property: keep it out of the diff.
    for v in report["variants"].values():
        v["_timing_note"] = v.pop("_seconds", None)
    report["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, sort_keys=True)
    unreal.log("LD4_VARIANT_GEOMETRY ok=%s variants=%d errors=%d -> %s"
               % (report["ok"], len(report["variants"]), len(report["errors"]), out_path))


if __name__ == "__main__" and len(sys.argv) >= 4 and sys.argv[1] == "diff":
    sys.exit(diff_mode(sys.argv[2], sys.argv[3]))
else:
    collect_mode()
