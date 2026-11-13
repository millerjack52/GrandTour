"""G0 4d: hardpoints-drawing.png - the approved sheet with every measured line drawn and labelled, one colour per
subsystem, and a legend table of values. Reads measurements.json written by measure_lc80_sheet.py.
System Python (PIL)."""
import json
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
OUT_DIR = os.path.join(ROOT, "Art", "Export", "VehicleTools", "landcruiser-grammar-g0-v01")
K = 2  # sheet upscale

COL = {"reg": (0, 140, 0), "dims": (25, 25, 25), "gh": (0, 85, 230), "bs": (235, 110, 0), "bs2": (255, 170, 60),
       "fr": (215, 0, 30), "lay": (150, 0, 200)}
SUB_NAME = {"reg": "registration, wheels, ground", "dims": "overall dimensions", "gh": "greenhouse (GH)",
            "bs": "bodyside, arches, flares (BS)", "fr": "front and rear (FR, RR)", "lay": "layout (LAY)"}
HP_SUB = {"WB": "reg", "TYRE_R": "reg", "TYRE_W": "reg", "TRACK_F": "reg", "TRACK_R": "reg",
          "OH_F": "dims", "OH_R": "dims", "W_BODY": "dims", "GROUND_CLEAR": "dims",
          "H_ROOF": "gh", "W_ROOF": "gh", "H_BELT": "gh", "H_COWL": "gh", "Y_COWL": "gh", "Y_A_BASE": "gh", "Y_ROOF_F": "gh",
          "Y_ROOF_R": "gh", "Y_RS_BASE": "gh", "RAKE_WS": "gh", "RAKE_RS": "gh", "TUMBLEHOME": "gh",
          "H_SILL": "bs", "W_FLARE": "bs", "ARCH_R": "bs", "ARCH_TOP_FLAT": "bs",
          "H_BONNET_F": "fr", "H_BUMPER_T": "fr", "H_BUMPER_B": "fr", "H_LAMP": "fr", "RAKE_FRONT": "fr", "RAKE_REAR": "fr",
          "Y_B": "lay", "Y_C": "lay", "Y_D": "lay"}
RULE_SUB = {"GH": "gh", "BS": "bs", "FR": "fr", "RR": "fr", "LA": "lay"}


def font(size, bold=False):
    for name in (("arialbd.ttf" if bold else "arial.ttf"), "segoeui.ttf", "calibri.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def fmt(v):
    if isinstance(v, dict):
        return ", ".join(f"{k} {fmt(x)}" for k, x in v.items())
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def main():
    m = json.load(open(os.path.join(OUT_DIR, "measurements.json"), encoding="utf-8"))
    sheet = Image.open(os.path.join(ROOT, m["sheet"])).convert("RGB")
    W, H = sheet.size
    base = sheet.resize((W * K, H * K), Image.LANCZOS)
    # fade the sheet so the lines read
    base = Image.blend(base, Image.new("RGB", base.size, (255, 255, 255)), 0.35)
    ov = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    f_lab = font(17)
    hpv = m["hardpoints"]
    labels = []

    def P(p):
        return (p[0] * K, p[1] * K)

    def lab(text, xy, sub):
        if not text:
            return
        if text in hpv:
            v = hpv[text]
            text = f"{text} {v['value']:g}{' m' if v['unit'] == 'm' else ' deg'}"
        labels.append((text, xy, COL[sub]))

    for e in m["draw"]:
        c = COL[e["sub"]] + (255,)
        k = e["kind"]
        if k == "hline":
            y = e["y"] * K
            d.line([(e["x"][0] * K, y), (e["x"][1] * K, y)], fill=c, width=2)
            if e.get("label_at") == "mid":
                lab(e.get("label"), (0.5 * (e["x"][0] + e["x"][1]) * K - 40, y + 4), e["sub"])
            else:
                lab(e.get("label"), (e["x"][1] * K + 4, y - 10), e["sub"])
        elif k == "vline":
            x = e["x"] * K
            d.line([(x, e["y"][0] * K), (x, e["y"][1] * K)], fill=c, width=2)
            if e.get("label_at") == "bottom":
                lab(e.get("label"), (x + 4, e["y"][1] * K + 26), e["sub"])
            else:
                lab(e.get("label"), (x + 4, e["y"][0] * K - 20), e["sub"])
        elif k == "line":
            d.line([P(e["p"]), P(e["q"])], fill=c, width=2)
            if e.get("label_at") == "mid":
                lab(e.get("label"), (0.5 * (P(e["p"])[0] + P(e["q"])[0]), 0.5 * (P(e["p"])[1] + P(e["q"])[1]) - 22), e["sub"])
            else:
                lab(e.get("label"), (P(e["p"])[0] + 6, P(e["p"])[1] - 20), e["sub"])
        elif k == "circle":
            cx, cy = P(e["c"])
            r = e["r"] * K
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=c, width=2)
        elif k == "arc":
            cx, cy = P(e["c"])
            r = e["r"] * K
            d.arc([cx - r, cy - r, cx + r, cy + r], e["a"][0], e["a"][1], fill=c, width=3)
            lab(e.get("label"), (cx - 40, cy - r - 26), e["sub"])
        elif k == "cross":
            cx, cy = P(e["c"])
            d.line([cx - 8, cy, cx + 8, cy], fill=c, width=2)
            d.line([cx, cy - 8, cx, cy + 8], fill=c, width=2)
            lab(e.get("label"), (cx + 8, cy + 4), e["sub"])
        elif k == "point":
            cx, cy = P(e["c"])
            d.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=c)
        elif k == "span" and e.get("xv") is not None:  # vertical span at x = xv
            x = e["xv"] * K
            y0, y1 = e["x"][0] * K, e["x"][1] * K
            d.line([(x, y0), (x, y1)], fill=c, width=2)
            d.line([(x - 7, y0), (x + 7, y0)], fill=c, width=2)
            d.line([(x - 7, y1), (x + 7, y1)], fill=c, width=2)
            lab(e.get("label"), (x + 8, 0.5 * (y0 + y1) - 10), e["sub"])
        elif k == "span":
            y = e["y"] * K
            x0, x1 = e["x"][0] * K, e["x"][1] * K
            d.line([(x0, y), (x1, y)], fill=c, width=2)
            d.line([(x0, y - 7), (x0, y + 7)], fill=c, width=2)
            d.line([(x1, y - 7), (x1, y + 7)], fill=c, width=2)
            lab(e.get("label"), (0.5 * (x0 + x1) - 30, y + 6), e["sub"])
        elif k == "box":
            d.rectangle([e["x"][0] * K, e["y"][0] * K, e["x"][1] * K, e["y"][1] * K], outline=c, width=2)
            lab(e.get("label"), (e["x"][0] * K, e["y"][1] * K + 4), e["sub"])
        elif k == "poly":
            d.line([P(p) for p in e["pts"]], fill=c, width=2)
            lab(e.get("label"), (P(e["pts"][-1])[0] + 6, P(e["pts"][-1])[1] - 10), e["sub"])
    for text, (x, y), col in labels:
        bb = d.textbbox((x, y), text, font=f_lab)
        d.rectangle([bb[0] - 2, bb[1] - 1, bb[2] + 2, bb[3] + 1], fill=(255, 255, 255, 215))
        d.text((x, y), text, fill=col + (255,), font=f_lab)
    img = Image.alpha_composite(base.convert("RGBA"), ov).convert("RGB")

    # legend
    f_h = font(22, True)
    f_t = font(17)
    rows_hp = [(n, v) for n, v in hpv.items()]
    rows_hp.sort(key=lambda nv: (list(SUB_NAME).index(HP_SUB.get(nv[0], "dims")), nv[0]))
    line_h = 23
    col_w = W * K // 3
    n_hp_rows = (len(rows_hp) + 1) // 2
    rules = list(m["rules"].items())
    legend_h = 400 + line_h * (n_hp_rows + len(rules) + len(m["real_car"]) + 12)
    leg = Image.new("RGB", (W * K, legend_h), (255, 255, 255))
    dl = ImageDraw.Draw(leg)
    y = 14
    dl.text((16, y), "Hard points (car frame: metres, front = -Y, Z up, origin mid-wheelbase on the ground; angles in degrees)", fill=(0, 0, 0), font=f_h)
    x = W * K - 1100
    for sub, name in SUB_NAME.items():
        dl.rectangle([x, y + 4, x + 18, y + 22], fill=COL[sub])
        dl.text((x + 24, y + 2), name, fill=(0, 0, 0), font=f_t)
        x += 24 + dl.textlength(name, font=f_t) + 22
        if x > W * K - 160:
            x = W * K - 1100
            y += line_h
    y += 44
    for i, (n, v) in enumerate(rows_hp):
        cx = 16 + (i // n_hp_rows) * (W * K // 2)
        cy = y + (i % n_hp_rows) * line_h
        sub = HP_SUB.get(n, "dims")
        real = v.get("real_car")
        rtxt = f"   real {real['value']:g} ({real['status']})" if real else ""
        dl.text((cx, cy), f"{n}", fill=COL[sub], font=f_t)
        dl.text((cx + 150, cy), f"{v['value']:g} {v['unit']}", fill=(0, 0, 0), font=f_t)
        dl.text((cx + 260, cy), f"{v['source']}, {v['confidence']}{rtxt}", fill=(90, 90, 90), font=f_t)
    y += n_hp_rows * line_h + 30
    dl.text((16, y), "Rule rows measured on the sheet (default for a boxy SUV -> measured)", fill=(0, 0, 0), font=f_h)
    y += 34
    for rid, r in rules:
        sub = RULE_SUB.get(rid[:2], "dims")
        dl.text((16, y), rid, fill=COL[sub], font=f_t)
        dl.text((100, y), f"default {r['default']}", fill=(0, 0, 0), font=f_t)
        dl.text((560, y), f"measured {fmt(r['measured'])} {r['unit'] if not isinstance(r['measured'], dict) else ''}", fill=(0, 0, 0), font=f_t)
        y += line_h
    y += 20
    vs = m["views"]
    dl.text((16, y), "View scales", fill=(0, 0, 0), font=f_h)
    y += 34
    dl.text((16, y), f"side (authority): {vs['side']['px_per_m']} px/m from WB 2.850 m on the hub centres; roof clipped: "
                     f"{vs['side']['roof_clipped']} ({vs['side']['roof_margin_px']} px of background above the roof outline)", fill=(0, 0, 0), font=f_t)
    y += line_h
    for v in ("front", "rear", "top"):
        dl.text((16, y), f"{v}: {vs[v]['px_per_m']} px/m = {vs[v]['ratio_to_side']:.3f} x side"
                         f"{'  (differs by more than 3 %, side view is authority)' if vs[v]['disagrees_over_3pct'] else ''}  -  {vs[v]['method']}",
                fill=(0, 0, 0), font=f_t)
        y += line_h
    dl.text((16, y), vs["top"].get("note", ""), fill=(0, 0, 0), font=f_t)
    y += line_h + 14
    dl.text((16, y), "Sheet against the real car (the sheet wins)", fill=(0, 0, 0), font=f_h)
    y += 34
    for kk, rc in m["real_car"].items():
        diff = f", difference {rc['difference_m']:+.3f} m" if rc.get("difference_m") is not None else ""
        dl.text((16, y), f"{kk}: sheet {rc['sheet_m']:g} m, real {rc['real_m']:g} m ({rc['status']}){diff}", fill=(0, 0, 0), font=f_t)
        y += line_h
    leg = leg.crop((0, 0, W * K, y + 16))
    out = Image.new("RGB", (W * K, img.height + leg.height), (255, 255, 255))
    out.paste(img, (0, 0))
    out.paste(leg, (0, img.height))
    p = os.path.join(OUT_DIR, "hardpoints-drawing.png")
    out.save(p)
    print(p, out.size)


if __name__ == "__main__":
    main()
