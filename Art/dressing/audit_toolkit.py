"""Stage B audit of the ported OW landscape toolkit assets (docs/LandscapeMigrationManifest.md 9.B.3 and 9.B.7).

Headless on GrandTour (Art/dressing/audit_toolkit.bat). Roots = every package under the toolkit folders.
Reports, into docs/landscape_migration/audit_<tag>.json:
  - /Game dependencies that do not resolve, each with the packages that reference it;
  - non-/Game, non-/Script dependencies (engine/plugin content) that do not resolve;
  - water-named packages/assets and water script/mount references;
  - /Script/OWGameUE* dependencies (with blueprint components for any blueprint carrying one);
  - the /Script module union and the mount union;
  - the 3 road blueprints' components (SubobjectDataSubsystem, as docs/landscape_migration/ar_walk.py does).
Environment (set by the .bat):
  GT_AUDIT_TAG     report name tag (default "audit")
  GT_AUDIT_RESAVE  "1" = after the audit, compile + resave the 3 road BPs, but ONLY if all 3 show the
                   OWRoadBed component with class /Script/GrandTour.OWRoadBedComponent (the CoreRedirect works).
Read-only unless GT_AUDIT_RESAVE=1. Code reused from ar_walk.py (registry, deps, bp_components).
"""
import unreal, os, re, json, time, traceback
from collections import Counter, defaultdict

TAG = os.environ.get("GT_AUDIT_TAG", "audit").strip() or "audit"
RESAVE = os.environ.get("GT_AUDIT_RESAVE", "").strip() == "1"
OUT = r"C:\GrandTour\docs\landscape_migration\audit_%s.json" % TAG
CONTENT = r"C:\GrandTour\Content"
ROOT_FOLDERS = ["/Game/OWGame", "/Game/3DAssets", "/Game/Materials", "/Game/Textures",
                "/Game/ANGRY_MESH", "/Game/MWLandscapeAutoMaterial"]
ROAD_BPS = ["/Game/OWGame/Dev/DressingLab/Roads/BP_OWRoad",
            "/Game/OWGame/Dev/DressingLab/Roads/BP_OWRoad_Dusty",
            "/Game/OWGame/Dev/DressingLab/Roads/BP_OWRoad_Gravel"]
ROADBED_CLASS = "/Script/GrandTour.OWRoadBedComponent"
GRAPHS = ["/Game/OWGame/Dev/DressingLab/PCG_OW" + g for g in ("Forest", "Meadow", "Scree", "Road", "Cliff", "Alpine")]
EXTS = (".uasset", ".umap")
WATER_RE = re.compile(r"river|water|foam|lilly|lily|/OW_Bed|OW_RiverWet", re.I)

report = {"ok": False, "tag": TAG, "resave_requested": RESAVE, "steps": [],
          "started": time.strftime("%Y-%m-%d %H:%M:%S")}
C = {}


def log(msg):
    unreal.log("[audit_toolkit] " + str(msg))


def run_step(name, fn):
    rec = {"name": name, "ok": False, "err": None, "count": None}
    t = time.time()
    try:
        rec["count"] = fn()
        rec["ok"] = True
    except Exception:
        rec["err"] = traceback.format_exc()[-3000:]
    rec["secs"] = round(time.time() - t, 2)
    report["steps"].append(rec)
    log("%s ok=%s count=%s" % (name, rec["ok"], rec["count"]))
    return rec["ok"]


def gp(obj, prop, default=None):
    try:
        return obj.get_editor_property(prop)
    except Exception:
        try:
            return getattr(obj, prop)
        except Exception:
            return default


def ad_pkg(ad):
    return str(gp(ad, "package_name"))


def ad_name(ad):
    return str(gp(ad, "asset_name"))


def ad_class(ad):
    p = gp(ad, "asset_class_path")
    if p is not None:
        pn = gp(p, "package_name")
        an = gp(p, "asset_name")
        if an is not None and str(an) != "None":
            return str(an), "%s.%s" % (pn, an)
    c = gp(ad, "asset_class")
    return str(c), str(c)


def objpath(o):
    try:
        return o.get_path_name() if o is not None else None
    except Exception:
        return str(o)


def assets_of_pkg(pkg):
    r = C["ar"].get_assets_by_package_name(pkg, False)
    return list(r) if r else []


def mkopts(hard, soft):
    o = unreal.AssetRegistryDependencyOptions()
    for k, v in (("include_soft_package_references", soft), ("include_hard_package_references", hard),
                 ("include_searchable_names", False), ("include_soft_management_references", False),
                 ("include_hard_management_references", False)):
        o.set_editor_property(k, v)
    return o


def deps(pkg, opts):
    r = C["ar"].get_dependencies(pkg, opts)
    return [str(x) for x in r] if r else []


def on_disk(pkg):
    if not pkg.startswith("/Game/"):
        return False
    base = os.path.join(CONTENT, pkg[len("/Game/"):].replace("/", os.sep))
    return any(os.path.isfile(base + e) for e in EXTS)


def resolves(pkg):
    if assets_of_pkg(pkg):
        return True
    if on_disk(pkg):
        return True
    try:
        return bool(unreal.EditorAssetLibrary.does_asset_exist(pkg))
    except Exception:
        return False


def bp_components(op, sds):
    try:
        bp = unreal.load_asset(op)
    except Exception as ex:
        return None, None, [], "load: " + str(ex)[:300]
    if bp is None:
        return None, None, [], "load returned None"
    parent = None
    try:
        parent = objpath(bp.get_editor_property("parent_class"))
    except Exception:
        pass
    if sds is None:
        return bp, parent, [], "no SubobjectDataSubsystem"
    try:
        handles = sds.k2_gather_subobject_data_for_blueprint(bp)
    except Exception as ex:
        return bp, parent, [], "gather: " + str(ex)[:300]
    L = unreal.SubobjectDataBlueprintFunctionLibrary
    comps = []
    for h in handles or []:
        c = {}
        try:
            d = L.get_data(h)
            try:
                c["var"] = str(L.get_variable_name(d))
            except Exception as ex:
                c["var_err"] = str(ex)[:150]
            o = L.get_object(d)
            if o is not None:
                c["name"] = o.get_name()
                c["class"] = o.get_class().get_path_name()
            else:
                c["object"] = None
        except Exception as ex:
            c["err"] = str(ex)[:300]
        comps.append(c)
    return bp, parent, comps, None


# ---------------------------------------------------------------- steps
def s_registry():
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    ar.search_all_assets(True)
    try:
        ar.wait_for_completion()
    except Exception:
        pass
    C["ar"] = ar
    return 1


def s_roots():
    roots, per = set(), {}
    for f in ROOT_FOLDERS:
        r = C["ar"].get_assets_by_path(f, True, False)
        pk = set(ad_pkg(a) for a in (r or []))
        per[f] = len(pk)
        roots |= pk
    C["roots"] = sorted(roots)
    report["root_packages_per_folder"] = per
    report["root_packages_total"] = len(roots)
    return len(roots)


def s_deps():
    H, S = mkopts(True, False), mkopts(False, True)
    game_refs = defaultdict(set)       # dep -> referencers
    other_refs = defaultdict(set)      # mount dep -> referencers
    script_refs = defaultdict(dict)    # pkg -> {module: [kinds]}
    mods, mounts = Counter(), Counter()
    per_pkg_script = {}
    for p in C["roots"]:
        smods, smounts = set(), set()
        for kind, opts in (("hard", H), ("soft", S)):
            for d in deps(p, opts):
                if d.startswith("/Game/"):
                    game_refs[d].add(p)
                elif d.startswith("/Script/"):
                    smods.add(d)
                    if d.startswith("/Script/OWGameUE"):
                        script_refs[p].setdefault(d, [])
                        if kind not in script_refs[p][d]:
                            script_refs[p][d].append(kind)
                else:
                    other_refs[d].add(p)
                    parts = d.split("/")
                    smounts.add("/" + parts[1] if len(parts) > 1 else d)
        for m in smods:
            mods[m] += 1
        for m in smounts:
            mounts[m] += 1
        per_pkg_script[p] = sorted(smods)
    rootset = set(C["roots"])
    missing_game, outside_ok = [], {}
    for d in sorted(game_refs):
        if d in rootset:
            continue
        if resolves(d):
            outside_ok[d] = sorted(game_refs[d])
        else:
            missing_game.append({"dep": d, "referenced_by": sorted(game_refs[d])})
    missing_other = []
    for d in sorted(other_refs):
        if not resolves(d):
            missing_other.append({"dep": d, "referenced_by": sorted(other_refs[d])})
    C["script_refs"] = script_refs
    C["per_pkg_script"] = per_pkg_script
    C["game_refs"] = game_refs
    report["missing_game_deps"] = missing_game
    report["missing_game_deps_count"] = len(missing_game)
    report["resolved_game_deps_outside_roots"] = outside_ok
    report["missing_nongame_deps"] = missing_other
    report["missing_nongame_deps_count"] = len(missing_other)
    report["script_modules_union"] = dict(mods.most_common())
    report["mounts_union"] = dict(mounts.most_common())
    return len(missing_game)


def s_water():
    hits = []
    for p in C["roots"]:
        reasons = []
        if WATER_RE.search(p):
            reasons.append("path")
        for a in assets_of_pkg(p):
            if WATER_RE.search(ad_name(a)):
                reasons.append("name:" + ad_name(a))
        for s in C["per_pkg_script"].get(p, []):
            if "water" in s.lower() or "river" in s.lower():
                reasons.append("script:" + s)
        if reasons:
            hits.append({"package": p, "reasons": reasons})
    for d, refs in C["game_refs"].items():
        if d not in set(C["roots"]) and WATER_RE.search(d):
            hits.append({"package": d, "reasons": ["dep outside roots"], "referenced_by": sorted(refs)})
    report["water_hits"] = hits
    report["water_hits_count"] = len(hits)
    return len(hits)


def s_script_refs():
    try:
        sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    except Exception as ex:
        sds = None
        report["subobject_subsystem_err"] = str(ex)[:300]
    C["sds"] = sds
    out = []
    for p in sorted(C["script_refs"]):
        e = {"package": p, "modules": C["script_refs"][p], "assets": []}
        for a in assets_of_pkg(p):
            cn, cp = ad_class(a)
            ae = {"name": ad_name(a), "class": cn}
            if "blueprint" in cn.lower():
                _bp, par, comps, err = bp_components("%s.%s" % (p, ad_name(a)), sds)
                ae["bp_parent_class"] = par
                ae["components"] = comps
                ae["component_err"] = err
            e["assets"].append(ae)
        out.append(e)
    report["owgameue_script_refs"] = out
    report["owgameue_script_refs_count"] = len(out)
    report["owgameue_refs_only_on_road_bps"] = all(x["package"] in ROAD_BPS for x in out)
    return len(out)


def s_road_bps():
    rb, all_ok = {}, True
    C["road_bp_objs"] = {}
    for p in ROAD_BPS:
        name = p.rsplit("/", 1)[1]
        bp, par, comps, err = bp_components("%s.%s" % (p, name), C["sds"])
        C["road_bp_objs"][p] = bp
        roadbed = [c for c in comps if c.get("var") == "OWRoadBed" or str(c.get("name", "")).startswith("OWRoadBed")]
        ok = bool(roadbed) and all(c.get("class") == ROADBED_CLASS for c in roadbed) and err is None
        all_ok = all_ok and ok
        rb[p] = {"parent_class": par, "components": comps, "err": err, "roadbed": roadbed, "roadbed_ok": ok,
                 "script_deps": C["per_pkg_script"].get(p, [])}
    report["road_bps"] = rb
    report["road_bps_roadbed_ok"] = all_ok
    return sum(1 for v in rb.values() if v["roadbed_ok"])


def s_graphs():
    rootset = set(C["roots"])
    g = {}
    for p in GRAPHS:
        if p not in rootset:
            g[p] = {"present": False}
            continue
        gd = sorted(d for d, refs in C["game_refs"].items() if p in refs)
        g[p] = {"present": True, "game_deps": len(gd),
                "game_deps_missing": [x["dep"] for x in report["missing_game_deps"] if p in x["referenced_by"]],
                "script_deps": C["per_pkg_script"].get(p, [])}
    report["graphs"] = g
    return sum(1 for v in g.values() if v["present"])


def s_resave():
    if not RESAVE:
        report["resave"] = "not requested"
        return 0
    if not report.get("road_bps_roadbed_ok"):
        report["resave"] = "REFUSED: not all 3 road BPs show OWRoadBed : " + ROADBED_CLASS
        raise RuntimeError(report["resave"])
    res, H, S = {}, mkopts(True, False), mkopts(False, True)
    for p in ROAD_BPS:
        bp = C["road_bp_objs"][p]
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        saved = bool(unreal.EditorAssetLibrary.save_loaded_asset(bp, only_if_is_dirty=False))
        after = sorted(set(d for o in (H, S) for d in deps(p, o) if d.startswith("/Script/")))
        res[p] = {"saved": saved, "script_deps_in_process_after_save": after}
        if not saved:
            raise RuntimeError("save failed: " + p)
    report["resave"] = res
    return len(res)


run_step("registry", s_registry) and run_step("roots", s_roots) and run_step("deps", s_deps)
if "script_refs" in C:
    run_step("water", s_water)
    run_step("script_refs", s_script_refs)
    run_step("road_bps", s_road_bps)
    run_step("graphs", s_graphs)
    run_step("resave", s_resave)
report["ok"] = all(s["ok"] for s in report["steps"])
report["summary"] = {
    "root_packages": report.get("root_packages_total"),
    "missing_game_deps": report.get("missing_game_deps_count"),
    "missing_nongame_deps": report.get("missing_nongame_deps_count"),
    "water_hits": report.get("water_hits_count"),
    "owgameue_script_ref_packages": [x["package"] for x in report.get("owgameue_script_refs", [])],
    "road_bps_roadbed_ok": report.get("road_bps_roadbed_ok"),
    "road_bp_roadbed_classes": {p: [c.get("class") for c in v.get("roadbed", [])]
                                for p, v in report.get("road_bps", {}).items()},
    "road_bp_script_deps": {p: v.get("script_deps") for p, v in report.get("road_bps", {}).items()},
    "graphs_present": [p for p, v in report.get("graphs", {}).items() if v.get("present")],
}
report["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=1, default=str)
log("AUDIT_TOOLKIT done ok=%s report=%s summary=%s" % (report["ok"], OUT, json.dumps(report["summary"], default=str)))
