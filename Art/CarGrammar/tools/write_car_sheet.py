"""G0 4c: write cars/landcruiser80.md from measurements.json (one time). The Markdown file is the record
after that: this script refuses to overwrite it unless --force is given, so owner corrections are not lost.
System Python."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.dirname(HERE)
ROOT = os.path.normpath(os.path.join(LIB, "..", ".."))
sys.path.insert(0, LIB)
import grammar  # noqa: E402

OUT_DIR = os.path.join(ROOT, "Art", "Export", "VehicleTools", "landcruiser-grammar-g0-v01")
CAR = os.path.join(LIB, "cars", "landcruiser80.md")
EXTRA_IDS = {"GH-03 A-pillar width seen from the side": "GH-03", "GH-08 rear screen rake": "GH-08",
             "LAY-01 front door leading edge rake": "LAY-01", "FR-03 bonnet leading edge round": "FR-03"}


def cell(s):
    return str(s).replace("|", "/").replace("\n", " ")


def fmt(v):
    if isinstance(v, dict):
        return ", ".join(f"{k} {fmt(x)}" for k, x in v.items() if x is not None)
    if isinstance(v, list):
        return "/".join(fmt(x) for x in v)
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def main():
    if os.path.exists(CAR) and "--force" not in sys.argv:
        print(f"{CAR} exists; not overwritten (pass --force to regenerate from measurements.json)")
        return 1
    m = json.load(open(os.path.join(OUT_DIR, "measurements.json"), encoding="utf-8"))
    schema = grammar.load_schema(LIB)
    rules = grammar.load_rules(LIB)
    hp = m["hardpoints"]
    vs = m["views"]
    L = ["# Land Cruiser 80 car sheet", "",
         "Hard points of `schema/hardpoints.md` for the Land Cruiser 80, measured on the approved sheet",
         f"`{m['sheet'].replace(os.sep, '/')}` by `tools/measure_lc80_sheet.py` (G0, 2026-10-02). Car frame: metres,",
         "front = -Y, Z up, origin mid-wheelbase on the ground; angles in degrees. Pixel coordinates are sheet pixels",
         "(x right, y down; a boundary between rows k-1 and k is written k - 0.5). The sheet wins over the real car;",
         "differences are in the Real car column. The drawing of every line is",
         "`Art/Export/VehicleTools/landcruiser-grammar-g0-v01/hardpoints-drawing.png`.", "",
         "## Registration", "",
         f"- Side view (authority): hub centres ({vs['side']['front_hub_px'][0]}, {vs['side']['front_hub_px'][1]}) and "
         f"({vs['side']['rear_hub_px'][0]}, {vs['side']['rear_hub_px'][1]}) px, rim circle fits rms "
         f"{vs['side']['rim_fit_rms_px'][0]} / {vs['side']['rim_fit_rms_px'][1]} px; wheelbase {vs['side']['wheelbase_px']} px = "
         f"2.850 m, so {vs['side']['px_per_m']} px/m; ground (Z = 0) at y {vs['side']['ground_y_px']} px; mid-wheelbase "
         f"(Y = 0) at x {vs['side']['x_mid_px']} px.",
         f"- Roof clipped in the side view: {'yes' if vs['side']['roof_clipped'] else 'no'} "
         f"({vs['side']['roof_margin_px']} px of background above the roof outline).",
         f"- Front view {vs['front']['px_per_m']} px/m ({vs['front']['ratio_to_side']:.3f} x side), rear view "
         f"{vs['rear']['px_per_m']} px/m ({vs['rear']['ratio_to_side']:.3f} x side), from their roof height against the side "
         f"view's H_ROOF; both differ from the side view by more than 3 %, so heights come from the side view and the front "
         f"and rear views are used at their own registered scale for widths only.",
         f"- Top view {vs['top']['px_per_m']} px/m ({vs['top']['ratio_to_side']:.3f} x side) from the length; within 3 %. "
         f"{vs['top']['note'][0].upper() + vs['top']['note'][1:]}.", "",
         "## Hard points", "",
         "| " + " | ".join(grammar.CAR_HP_COLS) + " |", "|" + "---|" * len(grammar.CAR_HP_COLS)]
    for name, sch in schema.items():
        h = hp[name]
        nd = 3 if sch["unit"] == "m" else 1
        real = h.get("real_car")
        if real:
            rtxt = f"{real['value']:.3f} {real['status']} ({real['source']}); sheet - real {h['value'] - real['value']:+.3f}"
        else:
            rtxt = "-"
        extra = {k: v for k, v in h.items() if k not in ("value", "unit", "source", "confidence", "evidence", "real_car")}
        ev = h["evidence"] + ("; " + ", ".join(f"{k} {fmt(v)}" for k, v in extra.items()) if extra else "")
        src = "real-car data (registration)" if name == "WB" else h["source"]
        L.append(f"| {name} | {h['value']:.{nd}f} | {sch['unit']} | {cell(src)} | {h['confidence']} | {cell(rtxt)} | {cell(ev)} |")
    L += ["", "## Overall against the real car", "",
          "| " + " | ".join(grammar.CAR_OVERALL_COLS) + " |", "|" + "---|" * len(grammar.CAR_OVERALL_COLS)]
    srcs = {"length": "toyota-global id60013935 (4820 mm HDJ81V and HZJ81V; FJ80G 4970)",
            "height": "toyota-global id60013935 (1900 mm; Fable's note said 1.86)",
            "width": "toyota-global id60013935 (1900 mm; HZJ81V narrow body 1830; Fable's note said 1.93); sheet = W_FLARE",
            "wheelbase": "toyota-global id60013935 (2850 mm); used for registration"}
    for k, rc in m["real_car"].items():
        diff = f"{rc['difference_m']:+.3f}" if rc.get("difference_m") is not None else "0 (registration)"
        L.append(f"| {k} | {rc['sheet_m']:.3f} | {rc['real_m']:.3f} | {rc['status'].split(' ')[0]} | {diff} | {cell(srcs.get(k, ''))} |")
    L += ["", "Not on the Toyota pages, so unverified: tracks 1.595 / 1.615, tyre 275/70R16 (radius 0.396), ground "
          "clearance 0.22 (Fable's recollection).", "",
          "## Rule rows measured on the sheet", "",
          "The rule default is the boxy SUV value in `rules/`; the measured value is the Land Cruiser on the approved sheet.",
          "Rows after LAY-06 are rules not marked measure that were measured on the way.", "",
          "| " + " | ".join(grammar.CAR_RULE_COLS) + " |", "|" + "---|" * len(grammar.CAR_RULE_COLS)]
    for rid, r in m["rules"].items():
        meas = fmt(r["measured"])
        L.append(f"| {rid} | {cell(rules[rid]['boxy_suv'])} | {cell(meas)} | {r['unit']} | {cell(r['evidence'])} |")
    for key, rid in EXTRA_IDS.items():
        e = m["extras"].get(key)
        if e and e.get("measured") is not None:
            unit = "deg" if "rake" in key else "m"
            L.append(f"| {rid} | {cell(rules[rid]['boxy_suv'])} | {fmt(e['measured'])} | {unit} | {cell('extra, ' + key + ': ' + e['evidence'])} |")
    open(CAR, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(f"wrote {CAR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
