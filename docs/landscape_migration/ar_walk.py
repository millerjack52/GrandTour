# ar_walk.py - READ-ONLY Asset Registry survey of OWGameUE for the GrandTour migration.
# Never saves, renames, deletes, duplicates, checks out or dirties anything.
import unreal, os, sys, json, time, re, traceback
from collections import deque, defaultdict, Counter

OUT = r"C:\Users\mille\AppData\Local\Temp\claude\C--GrandTour\323b3231-6a8a-43ee-87c7-46a8f7cdaf47\scratchpad\phase0"
CONTENT = r"D:\Dev\OWGameUE\Content"
DL = "/Game/OWGame/Dev/DressingLab"
SHARED = ["/Game/OWGame/Dev/L_OWDressingLab_sharedassets", "/Game/OWGame/Dev/L_OWWorldCanvas_sharedassets"]
INSCOPE_SUB = [DL + "/" + s for s in ("Masters", "Trees", "TreeMIs", "Cliffs", "Roads")]
VENDORS_IN = ["/Game/ANGRY_MESH", "/Game/MWLandscapeAutoMaterial", "/Game/ToonFantasyNature"]
VENDORS_ALL = VENDORS_IN + ["/Game/Fantastic_Village_Pack"]
CALLOUTS = ["/Game/Fantastic_Village_Pack", "/Game/OWGame", "/Game/Characters", "/Game/MetaHumans",
            "/Game/Materials", "/Game/Textures", "/Game/Blueprints"]
EXTS = (".uasset", ".umap", ".uexp", ".ubulk", ".uptnl")
WATER_RE = re.compile(r"river|water|foam|lilly|lily|/OW_Bed|OW_RiverWet", re.I)
KINDS = ["LandscapeLayerBlend", "LandscapeLayerSample", "LandscapeLayerWeight", "LandscapeLayerSwitch",
         "LandscapeVisibilityMask", "LandscapeGrassOutput", "RuntimeVirtualTextureOutput",
         "RuntimeVirtualTextureSample"]
LICENSE = r"D:\Dev\OWGameUE\Content\3DAssets\STYLIZED_COZY_TREES_LICENSE.txt"

T0 = time.time()
report = {"ok": False, "steps": [], "started": time.strftime("%Y-%m-%d %H:%M:%S")}
C = {}


def log(msg):
    try:
        unreal.log("[ar_walk] " + str(msg))
    except Exception:
        pass


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


def under(pkg, folder):
    return pkg.lower().startswith(folder.lower() + "/")


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


def ad_objpath(ad):
    return "%s.%s" % (ad_pkg(ad), ad_name(ad))


def objpath(o):
    try:
        return o.get_path_name() if o is not None else None
    except Exception:
        return str(o)


def norm_tag(v):
    if isinstance(v, tuple):
        if len(v) == 2 and isinstance(v[0], bool):
            return str(v[1]) if v[0] else None
        return str(v)
    return None if v is None else str(v)


def tags(ad, names=("ParentClass", "NativeParentClass")):
    out = {}
    for t in names:
        r = {}
        try:
            r["asset_data"] = norm_tag(ad.get_tag_value(t))
        except Exception as e:
            r["asset_data_err"] = str(e)[:200]
        try:
            r["helpers"] = norm_tag(unreal.AssetRegistryHelpers.get_tag_value(ad, t))
        except Exception as e:
            r["helpers_err"] = str(e)[:200]
        out[t] = r
    return out


def assets_in(path, rec):
    r = C["ar"].get_assets_by_path(path, rec, False)
    return list(r) if r else []


def assets_of_pkg(pkg):
    r = C["ar"].get_assets_by_package_name(pkg, False)
    return list(r) if r else []


def disk_base(pkg):
    return os.path.join(CONTENT, pkg[len("/Game/"):].replace("/", os.sep))


def disk_info(pkg):
    base = disk_base(pkg)
    tot, found = 0, []
    for e in EXTS:
        f = base + e
        if os.path.isfile(f):
            tot += os.path.getsize(f)
            found.append(e)
    return tot, found


def chain(p):
    V = C["V"]
    out, seen = [], set()
    while p is not None and p not in seen and p in V:
        seen.add(p)
        out.append(p)
        p = V[p]["parent"]
    out.reverse()
    return out


def chain_edges(ch):
    return [C["V"][x]["edge"] for x in ch]


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
    dl_flat = assets_in(DL, False)
    dl_rec = assets_in(DL, True)
    C["dl_rec"] = dl_rec
    rules = []  # (rule, ads, pred-for-elsewhere, folder)

    def byname(n):
        return [a for a in dl_flat if ad_name(a).lower() == n.lower()]

    def byprefix(p):
        return [a for a in dl_flat if ad_name(a).lower().startswith(p.lower())]

    for n in ("M_OWDressingLab", "MI_OWDressingLab_Style"):
        rules.append(("DL/" + n, byname(n), (lambda a, n=n: ad_name(a).lower() == n.lower()), None))
    rules.append(("DL/Masters/** (recursive)", assets_in(DL + "/Masters", True), None, DL + "/Masters"))
    for n in ("OW_Meadow_LayerInfo", "OW_Forest_LayerInfo", "OW_Scree_LayerInfo", "OW_Bare_LayerInfo", "LI_OW_Meadow"):
        rules.append(("DL/" + n, byname(n), (lambda a, n=n: ad_name(a).lower() == n.lower()), None))
    rules.append(("DL/LGT_OW* (flat)", byprefix("LGT_OW"), (lambda a: ad_name(a).lower().startswith("lgt_ow")), None))
    rules.append(("DL/Trees/** (recursive)", assets_in(DL + "/Trees", True), None, DL + "/Trees"))
    rules.append(("DL/TreeMIs/** (recursive)", assets_in(DL + "/TreeMIs", True), None, DL + "/TreeMIs"))
    for pfx in ("SM_OWFlowerClump_", "MI_OWFlower_"):
        rules.append(("DL/" + pfx + "* (flat)", byprefix(pfx), (lambda a, p=pfx: ad_name(a).lower().startswith(p.lower())), None))
    for n in ("PCG_OWForest", "PCG_OWMeadow", "PCG_OWScree", "PCG_OWAlpine", "PCG_OWCliff", "PCG_OWRoad"):
        rules.append(("DL/" + n, byname(n), (lambda a, n=n: ad_name(a).lower() == n.lower()), None))
    rules.append(("DL/Cliffs/** (recursive)", assets_in(DL + "/Cliffs", True), None, DL + "/Cliffs"))
    rules.append(("DL/Roads/** (recursive)", assets_in(DL + "/Roads", True), None, DL + "/Roads"))
    shared_all = []
    for f in SHARED:
        shared_all += [(f, a) for a in assets_in(f, True)]
    for pfx in ("Meadow", "Forest", "RoadVerge", "Alpine", "Snow"):
        ads = [a for f, a in shared_all
               if ad_class(a)[0] == "LandscapeLayerInfoObject" and ad_name(a).lower().startswith(pfx.lower())]
        rules.append(("sharedassets LayerInfo " + pfx + "*", ads, None, None))
    for p in ("/Game/OWGame/Dev/WorldPreview/PCG_OWWorldPreview", "/Game/3DAssets/SM_Beech",
              "/Game/3DAssets/SM_Birch", "/Game/3DAssets/SM_FirTree"):
        rules.append(("pkg " + p, assets_of_pkg(p), None, None))

    roots, recs, zeros = {}, [], []
    for rname, ads, pred, folder in rules:
        pk = sorted(set(ad_pkg(a) for a in ads))
        rr = {"rule": rname, "count_assets": len(ads), "count_packages": len(pk),
              "classes": dict(Counter(ad_class(a)[0] for a in ads)),
              "assets": [{"name": ad_name(a), "class": ad_class(a)[0], "package": ad_pkg(a)} for a in ads]}
        if not ads:
            rr["zero"] = True
            zeros.append(rname)
            if pred is not None:
                rr["found_elsewhere_in_DL"] = [ad_objpath(a) for a in dl_rec if pred(a)][:20]
            if folder is not None:
                rr["folder_on_disk"] = os.path.isdir(disk_base(folder))
        for p in pk:
            roots.setdefault(p, []).append(rname)
        recs.append(rr)
    report["roots_rules"] = recs
    report["zero_match_rules"] = zeros
    report["roots"] = {p: roots[p] for p in sorted(roots)}
    report["sharedassets_listing"] = [
        {"folder": f, "name": ad_name(a), "class": ad_class(a)[0], "package": ad_pkg(a), "root": ad_pkg(a) in roots}
        for f, a in sorted(shared_all, key=lambda x: ad_pkg(x[1]))]
    report["tree_license_exists"] = os.path.isfile(LICENSE)
    C["roots"] = roots
    return len(roots)


def mkopts(hard, soft):
    o = unreal.AssetRegistryDependencyOptions()
    for k, v in (("include_soft_package_references", soft), ("include_hard_package_references", hard),
                 ("include_searchable_names", False), ("include_soft_management_references", False),
                 ("include_hard_management_references", False)):
        o.set_editor_property(k, v)  # our own local struct, not an asset
    return o


def deps(pkg, opts):
    r = C["ar"].get_dependencies(pkg, opts)
    return [str(x) for x in r] if r else []


def s_closure():
    H, S = mkopts(True, False), mkopts(False, True)
    V = {}
    q = deque()
    for p in sorted(C["roots"]):
        V[p] = {"parent": None, "edge": "root", "ref_kinds": []}
        q.append(p)
    while q:
        p = q.popleft()
        info = V[p]
        ads = assets_of_pkg(p)
        info["assets"] = [{"name": ad_name(a), "class": ad_class(a)[0], "class_path": ad_class(a)[1]} for a in ads]
        info["registry_found"] = bool(ads)
        b, found = disk_info(p)
        info["bytes"] = b
        info["files"] = found
        info["missing_main_file"] = not (".uasset" in found or ".umap" in found)
        info["script_deps"] = {}
        info["mount_deps"] = {}
        info["game_deps"] = {"hard": [], "soft": []}
        for kind, opts in (("hard", H), ("soft", S)):
            for d in deps(p, opts):
                if d.startswith("/Game/"):
                    info["game_deps"][kind].append(d)
                    if d not in V:
                        V[d] = {"parent": p, "edge": kind, "ref_kinds": []}
                        q.append(d)
                    if kind not in V[d]["ref_kinds"]:
                        V[d]["ref_kinds"].append(kind)
                elif d.startswith("/Script/"):
                    info["script_deps"].setdefault(d, []).append(kind)
                else:
                    info["mount_deps"].setdefault(d, []).append(kind)
    C["V"] = V
    report["closure"] = {p: V[p] for p in sorted(V)}
    report["closure_total_packages"] = len(V)
    report["closure_total_bytes"] = sum(v["bytes"] for v in V.values())
    report["closure_edge_counts"] = dict(Counter(v["edge"] for v in V.values()))
    report["missing_files"] = sorted(p for p, v in V.items() if v["missing_main_file"])
    report["registry_missing"] = sorted(p for p, v in V.items() if not v["registry_found"])
    return len(V)


def s_water():
    V = C["V"]
    hits, broad = [], []
    for p in sorted(V):
        i = V[p]
        reasons = []
        if WATER_RE.search(p):
            reasons.append("path")
        for a in i["assets"]:
            if WATER_RE.search(a["name"]):
                reasons.append("name:" + a["name"])
        for m in i["mount_deps"]:
            if m.lower().startswith("/water/") or "meshpartitionwater" in m.lower():
                reasons.append("mount:" + m)
        for s in i["script_deps"]:
            if s.lower() in ("/script/water", "/script/meshpartitionwater"):
                reasons.append("script:" + s)
        ch = chain(p)
        if reasons:
            hits.append({"package": p, "reasons": reasons, "classes": [a["class"] for a in i["assets"]],
                         "chain": ch, "chain_edges": chain_edges(ch)})
        wr = [d for d in list(i["script_deps"]) + list(i["mount_deps"]) if "water" in d.lower()]
        if wr:
            broad.append({"package": p, "refs": wr, "chain": ch, "chain_edges": chain_edges(ch)})
    report["water_hits"] = hits
    report["water_script_or_mount_refs"] = broad
    return len(hits)


def in_scope(p):
    if p in C["roots"]:
        return True
    return any(under(p, f) for f in INSCOPE_SUB + VENDORS_IN)


def group2(p):
    parts = p.split("/")[2:-1]
    return "/Game/" + "/".join(parts[:2]) if parts else "/Game"


def s_oos():
    V = C["V"]
    groups, callouts = {}, defaultdict(list)
    n, b = 0, 0
    for p in sorted(V):
        if in_scope(p):
            continue
        i = V[p]
        ch = chain(p)
        e = {"package": p, "classes": [a["class"] for a in i["assets"]], "bytes": i["bytes"],
             "edge": i["edge"], "ref_kinds": i["ref_kinds"], "chain": ch, "chain_edges": chain_edges(ch)}
        groups.setdefault(group2(p), []).append(e)
        n += 1
        b += i["bytes"]
        for c in CALLOUTS:
            if under(p, c):
                if c == "/Game/OWGame":
                    if under(p, DL):
                        continue
                    callouts["/Game/OWGame (outside DressingLab)"].append(e)
                else:
                    callouts[c].append(e)
    report["out_of_scope"] = {"count": n, "bytes": b, "groups": groups, "callouts": dict(callouts),
                              "callout_counts": {c: len(v) for c, v in callouts.items()}}
    return n


def bp_components(op, sds):
    try:
        bp = unreal.load_asset(op)
    except Exception as ex:
        return None, [], "load: " + str(ex)[:300]
    if bp is None:
        return None, [], "load returned None"
    parent = None
    try:
        parent = objpath(bp.get_editor_property("parent_class"))
    except Exception:
        pass
    if sds is None:
        return parent, [], "no SubobjectDataSubsystem"
    try:
        handles = sds.k2_gather_subobject_data_for_blueprint(bp)
    except Exception as ex:
        return parent, [], "gather: " + str(ex)[:300]
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
            for fn in ("is_inherited_component", "is_native_component", "is_root_component"):
                try:
                    c[fn] = bool(getattr(L, fn)(d))
                except Exception:
                    pass
        except Exception as ex:
            c["err"] = str(ex)[:300]
        comps.append(c)
    return parent, comps, None


def s_script_refs():
    V = C["V"]
    sds, sds_err = None, None
    try:
        sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    except Exception as ex:
        sds_err = str(ex)[:300]
    out = []
    for p in sorted(V):
        mods = [s for s in V[p]["script_deps"] if s in ("/Script/OWGameUE", "/Script/OWGameUEEditor")]
        if not mods:
            continue
        ch = chain(p)
        e = {"package": p, "modules": mods, "chain": ch, "chain_edges": chain_edges(ch), "assets": []}
        for a in assets_of_pkg(p):
            cn, cp = ad_class(a)
            ae = {"name": ad_name(a), "class": cn, "class_path": cp, "tags": tags(a)}
            if "blueprint" in cn.lower():
                par, comps, err = bp_components(ad_objpath(a), sds)
                ae["bp_parent_class"] = par
                ae["components"] = comps
                ae["component_err"] = err
            e["assets"].append(ae)
        out.append(e)
    report["script_refs"] = out
    report["subobject_subsystem_err"] = sds_err
    return len(out)


def s_unions():
    V = C["V"]
    mods, mounts, ef = Counter(), Counter(), Counter()
    for i in V.values():
        for s in i["script_deps"]:
            mods[s] += 1
        ms, fs = set(), set()
        for m in i["mount_deps"]:
            parts = m.split("/")
            mt = "/" + parts[1] if len(parts) > 1 else m
            ms.add(mt)
            if mt == "/Engine":
                fs.add(parts[2] if len(parts) > 3 else "(package at /Engine root: %s)" % m)
        for mt in ms:
            mounts[mt] += 1
        for f in fs:
            ef[f] += 1
    report["script_modules_union"] = dict(mods.most_common())
    report["mounts_union"] = dict(mounts.most_common())
    report["engine_top_folders"] = dict(ef.most_common())
    return len(mods)


def node_info(x):
    d = {}
    try:
        d["kind"] = x.get_class().get_name().replace("MaterialExpression", "")
        pn = x.get_path_name()
        d["path"] = pn
        d["owner"] = pn.split(":")[0]
    except Exception as ex:
        d["err"] = str(ex)[:200]
        return d
    k = d["kind"]
    try:
        if k == "LandscapeLayerBlend":
            d["layers"] = [{"layer_name": str(gp(l, "layer_name")), "blend_type": str(gp(l, "blend_type"))}
                           for l in (x.get_editor_property("layers") or [])]
        elif k in ("LandscapeLayerSample", "LandscapeLayerWeight", "LandscapeLayerSwitch"):
            d["parameter_name"] = str(x.get_editor_property("parameter_name"))
        elif k == "LandscapeGrassOutput":
            d["grass"] = [{"name": str(gp(g, "name")), "grass_type": objpath(gp(g, "grass_type"))}
                          for g in (x.get_editor_property("grass_types") or [])]
        elif k == "RuntimeVirtualTextureSample":
            d["rvt"] = objpath(x.get_editor_property("virtual_texture"))
        elif k == "RuntimeVirtualTextureOutput":
            for prop in ("virtual_texture", "output_type"):
                try:
                    v = x.get_editor_property(prop)
                    d[prop] = objpath(v) if hasattr(v, "get_path_name") else str(v)
                except Exception:
                    pass
    except Exception as ex:
        d["prop_err"] = str(ex)[:300]
    return d


def s_landscape():
    V = C["V"]
    L = {}
    report["landscape"] = L
    MEL = unreal.MaterialEditingLibrary
    L["mel_expression_methods"] = [m for m in dir(MEL) if "xpression" in m.lower()]
    targets = [(DL + "/M_OWDressingLab", "M_OWDressingLab")]
    for p in sorted(V):
        if under(p, "/Game/OWGame"):
            for a in V[p]["assets"]:
                if a["class"].startswith("MaterialFunction"):
                    targets.append((p, a["name"]))
    loaded, tl = {}, []
    for p, n in targets:
        op = p + "." + n
        r = {"objpath": op}
        try:
            o = unreal.load_asset(op)
            r["loaded"] = o is not None
            if o is not None:
                loaded[op] = o
                r["class"] = o.get_class().get_name()
        except Exception as ex:
            r["loaded"] = False
            r["err"] = str(ex)[:300]
        tl.append(r)
    L["targets"] = tl
    nodes, found_by = {}, defaultdict(set)
    # method 1: MaterialEditingLibrary getters that mention expressions
    m1 = {}
    for op, o in loaded.items():
        r = {}
        for m in L["mel_expression_methods"]:
            if not m.startswith("get_") or "expressions" not in m:
                continue
            try:
                v = getattr(MEL, m)(o)
                if hasattr(v, "__len__") and not isinstance(v, str):
                    items = list(v)
                    r[m] = {"len": len(items)}
                    for x in items:
                        try:
                            if x.get_class().get_name().replace("MaterialExpression", "") in KINDS:
                                nodes[x.get_path_name()] = x
                                found_by[x.get_path_name()].add("mel:" + m)
                        except Exception:
                            pass
                else:
                    r[m] = repr(v)[:200]
            except Exception as ex:
                r[m] = "ERR " + str(ex)[:200]
        m1[op] = r
    L["method1_mel"] = m1
    # method 2: find_object on conventional names
    m2 = Counter()
    for op in loaded:
        for k in KINDS:
            for i in range(81):
                path = "%s:MaterialExpression%s_%d" % (op, k, i)
                try:
                    x = unreal.find_object(None, path)
                except Exception:
                    x = None
                if x is not None:
                    nodes[path] = x
                    found_by[path].add("find_object")
                    m2[k] += 1
    L["method2_find_object_counts"] = dict(m2)
    # method 3: ObjectIterator per expression class, filtered to target packages
    tpk = set(p for p, n in targets)
    m3, missing_cls = Counter(), []
    for k in KINDS:
        cls = getattr(unreal, "MaterialExpression" + k, None)
        if cls is None:
            missing_cls.append(k)
            continue
        try:
            for x in unreal.ObjectIterator(cls):
                try:
                    pn = x.get_path_name()
                except Exception:
                    continue
                if pn.split(".")[0] in tpk:
                    nodes[pn] = x
                    found_by[pn].add("object_iterator")
                    m3[k] += 1
        except Exception as ex:
            L.setdefault("method3_errs", []).append("%s: %s" % (k, str(ex)[:200]))
    L["method3_object_iterator_counts"] = dict(m3)
    L["missing_expression_classes"] = missing_cls
    nl = []
    for pn in sorted(nodes):
        d = node_info(nodes[pn])
        d["found_by"] = sorted(found_by[pn])
        nl.append(d)
    L["nodes"] = nl
    layer_names = Counter()
    grass = []
    rvts = set()
    for d in nl:
        for l in d.get("layers", []):
            layer_names[l["layer_name"]] += 1
        if "parameter_name" in d:
            layer_names[d["parameter_name"]] += 1
        grass += d.get("grass", [])
        if d.get("rvt"):
            rvts.add(d["rvt"])
    L["layer_names_union"] = dict(layer_names.most_common())
    L["grass_outputs"] = grass
    L["rvt_assets"] = sorted(rvts)
    # MI parent chain
    ch = []
    try:
        cur = unreal.load_asset(DL + "/MI_OWDressingLab_Style.MI_OWDressingLab_Style")
        n = 0
        while cur is not None and n < 20:
            ch.append({"path": cur.get_path_name(), "class": cur.get_class().get_name()})
            try:
                cur = cur.get_editor_property("parent")
            except Exception:
                break
            n += 1
    except Exception as ex:
        ch.append({"err": str(ex)[:300]})
    L["mi_style_parent_chain"] = ch
    return len(nl)


def folder4(p):
    parts = p.split("/")[2:-1]
    return "/Game/" + "/".join(parts[:4]) if parts else "/Game"


def disk_walk(base):
    files, pk, b = 0, 0, 0
    for r, ds, fs in os.walk(base):
        for f in fs:
            files += 1
            try:
                b += os.path.getsize(os.path.join(r, f))
            except Exception:
                pass
            if f.lower().endswith((".uasset", ".umap")):
                pk += 1
    return files, pk, b


def s_sizes():
    V = C["V"]
    fs = {}
    for p, i in V.items():
        g = folder4(p)
        e = fs.setdefault(g, {"count": 0, "bytes": 0})
        e["count"] += 1
        e["bytes"] += i["bytes"]
    for e in fs.values():
        e["mb"] = round(e["bytes"] / 1048576.0, 2)
    report["folder_sizes"] = dict(sorted(fs.items(), key=lambda kv: -kv[1]["bytes"]))
    report["folder_sizes_grouping"] = "package folder truncated to 4 folders below /Game (the brief's example depth)"
    folders = []
    for v in VENDORS_ALL:
        base = disk_base(v)
        if v == "/Game/ANGRY_MESH" and os.path.isdir(base):
            for d in sorted(os.listdir(base)):
                if os.path.isdir(os.path.join(base, d)):
                    folders.append(v + "/" + d)
            loose = [f for f in os.listdir(base) if os.path.isfile(os.path.join(base, f))]
            if loose:
                folders.append(v + " (loose files)")
        else:
            folders.append(v)
    vt = []
    for f in folders:
        loose = f.endswith(" (loose files)")
        fv = f.replace(" (loose files)", "")
        base = disk_base(fv)
        e = {"folder": f, "exists": os.path.isdir(base)}
        if loose:
            fl = [x for x in os.listdir(base) if os.path.isfile(os.path.join(base, x))]
            e["disk_files"] = len(fl)
            e["disk_packages"] = len([x for x in fl if x.lower().endswith((".uasset", ".umap"))])
            e["disk_bytes"] = sum(os.path.getsize(os.path.join(base, x)) for x in fl)
            cps = [p for p in V if under(p, fv) and "/" not in p[len(fv) + 1:]]
        else:
            if e["exists"]:
                e["disk_files"], e["disk_packages"], e["disk_bytes"] = disk_walk(base)
            cps = [p for p in V if under(p, fv)]
        e["closure_packages"] = len(cps)
        e["closure_bytes"] = sum(V[p]["bytes"] for p in cps)
        e["disk_mb"] = round(e.get("disk_bytes", 0) / 1048576.0, 2)
        e["closure_mb"] = round(e["closure_bytes"] / 1048576.0, 2)
        vt.append(e)
    report["vendor_totals"] = vt
    return len(fs)


def s_left():
    V = C["V"]
    groups = defaultdict(list)
    for a in C["dl_rec"]:
        p = ad_pkg(a)
        if p in V:
            continue
        rel = p[len(DL) + 1:]
        sub = rel.rsplit("/", 1)[0] if "/" in rel else "(DressingLab root)"
        groups[sub].append({"name": ad_name(a), "class": ad_class(a)[0], "package": p})
    report["left_behind"] = {k: groups[k] for k in sorted(groups)}
    report["left_behind_count"] = sum(len(v) for v in groups.values())
    return report["left_behind_count"]


def write_outputs():
    report["ok"] = bool(report["steps"]) and all(s["ok"] for s in report["steps"])
    report["wall_secs"] = round(time.time() - T0, 1)
    with open(os.path.join(OUT, "ar_closure.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, ensure_ascii=True, default=str)
    V = report.get("closure") or {}
    with open(os.path.join(OUT, "closure_packages.txt"), "w", encoding="utf-8") as f:
        for p in sorted(V):
            i = V[p]
            f.write("%s\t%s\t%s\t%s\n" % (p, i.get("bytes", 0), i.get("edge"),
                                          ",".join(a["class"] for a in i.get("assets", []))))
    try:
        sys.path.insert(0, OUT)
        import render_summary
        render_summary.render(report, OUT)
    except Exception:
        with open(os.path.join(OUT, "render_err.txt"), "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())


try:
    log("start")
    if run_step("registry", s_registry) and run_step("roots", s_roots) and run_step("closure", s_closure):
        run_step("water", s_water)
        run_step("out_of_scope", s_oos)
        run_step("script_refs", s_script_refs)
        run_step("unions", s_unions)
        run_step("landscape", s_landscape)
        run_step("sizes", s_sizes)
        run_step("left_behind", s_left)
except Exception:
    report["fatal"] = traceback.format_exc()[-3000:]
finally:
    try:
        write_outputs()
    except Exception:
        with open(os.path.join(OUT, "write_err.txt"), "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
    log("done ok=%s" % report.get("ok"))
