"""BT2 v02 (plan 8.5): master-compare.png at the v02 root. Rows: blueprint, R100, R60; columns: front and rear
three-quarter. Master rows are the zones renders (clay with the glass vertex tint and wheel proxies).
System Python (PIL)."""
import os
import sys

os.environ.setdefault("BT2_VERSION", "v02")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bt2_compose as P  # noqa: E402

ROOT = P.OUT_ROOT


def main():
    rows = []
    bp = os.path.join(ROOT, "R100", "debug", "renders")
    rows.append(P.row([P.label(P.on_grey(os.path.join(bp, "view_front34_blueprint.png")), "blueprint (scaffold mesh), front three-quarter"),
                       P.label(P.on_grey(os.path.join(bp, "view_rear34_blueprint.png")), "blueprint, rear three-quarter")]))
    for var, text in (("R100", "R100 (measured R)"), ("R60", "R60 (measured R x 0.6, floor 0.03)")):
        rd = os.path.join(ROOT, var, "debug", "renders")
        rows.append(P.row([P.label(P.on_grey(os.path.join(rd, "zones_front34.png")), f"{text}: clay, glass tint, wheel proxies, front three-quarter"),
                           P.label(P.on_grey(os.path.join(rd, "zones_rear34.png")), f"{text}: rear three-quarter")]))
    out = os.path.join(ROOT, "master-compare.png")
    P.stack(rows).save(out)
    print(out)


if __name__ == "__main__":
    main()
