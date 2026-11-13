"""Car grammar loader.

Parses the Markdown tables of Art/CarGrammar (schema, rules, body types, car sheets) into Python
dictionaries. The tables are the single source of truth; this module only reads them. Any malformed
row raises GrammarError naming the file and line.

    python Art/CarGrammar/grammar.py                 # load and check everything, print a summary
    python Art/CarGrammar/grammar.py --selftest      # also prove that malformed rows are rejected

Library use:
    import grammar
    g = grammar.load()                 # {"schema", "rules", "bodytypes", "cars"}
    g["rules"]["GH-02"]["boxy_suv"]    # 'RAKE_WS 32 (28 to 38)'
    g["rules"]["GH-02"]["values"]["boxy_suv"]   # [32.0, 28.0, 38.0]
    g["cars"]["landcruiser80"]["hardpoints"]["WB"]["value"]   # 2.85
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

RULE_COLS = ["ID", "Rule", "Boxy SUV", "Sedan", "Src", "Conf"]
RULE_FILES = {"greenhouse.md": ("GH",), "bodyside.md": ("BS",), "front_rear.md": ("FR", "RR"), "layout.md": ("LAY",)}
ID_RE = re.compile(r"^(GH|BS|FR|RR|LAY)-\d{2}$")
SRC_CODES = {"R", "S", "P", "O"}
CONF_HEADS = {"A", "D", "M", "measure", "defaults"}
SCHEMA_COLS = ["Name", "Meaning", "Unit"]
NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
UNITS = {"m", "deg"}
BODYTYPE_COLS = ["ID", "Subsystem", "Rule", "Boxy SUV", "Src", "Conf"]
CAR_HP_COLS = ["Name", "Value", "Unit", "Source", "Confidence", "Real car", "Evidence"]
CAR_RULE_COLS = ["ID", "Default (boxy SUV)", "Measured", "Unit", "Evidence"]
CAR_OVERALL_COLS = ["Quantity", "Sheet", "Real car", "Status", "Difference", "Source"]
CAR_SOURCES = ("sheet pixels", "real-car data", "rule default", "owner")
CAR_CONF = {"measured", "derived", "assumed"}
NUM_RE = re.compile(r"(?<![A-Za-z_])-?\d+(?:\.\d+)?")


class GrammarError(ValueError):
    pass


def numbers(text):
    """All numbers written in a cell ('RAKE_WS 32 (28 to 38)' -> [32.0, 28.0, 38.0])."""
    return [float(x) for x in NUM_RE.findall(text)]


def _split_row(line):
    s = line.strip()
    if not (s.startswith("|") and s.endswith("|")):
        return None
    body = s[1:-1]
    cells, cur, i = [], "", 0
    while i < len(body):
        if body[i] == "\\" and i + 1 < len(body) and body[i + 1] == "|":
            cur += "|"
            i += 2
            continue
        if body[i] == "|":
            cells.append(cur.strip())
            cur = ""
        else:
            cur += body[i]
        i += 1
    cells.append(cur.strip())
    return cells


def read_tables(path):
    """Every pipe table in a Markdown file: [{"header", "line", "rows": [(line_no, cells)]}]."""
    if not os.path.isfile(path):
        raise GrammarError(f"{path}: file missing")
    lines = open(path, encoding="utf-8").read().splitlines()
    tables, i = [], 0
    while i < len(lines):
        head = _split_row(lines[i])
        sep = _split_row(lines[i + 1]) if i + 1 < len(lines) else None
        if head and sep and all(re.fullmatch(r":?-{3,}:?", c) for c in sep):
            if len(sep) != len(head):
                raise GrammarError(f"{path}:{i + 2}: separator has {len(sep)} cells, header has {len(head)}")
            t = {"header": head, "line": i + 1, "rows": []}
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                cells = _split_row(lines[j])
                if cells is None:
                    raise GrammarError(f"{path}:{j + 1}: table row does not end with '|'")
                if len(cells) != len(head):
                    raise GrammarError(f"{path}:{j + 1}: expected {len(head)} cells ({' | '.join(head)}), got {len(cells)}")
                t["rows"].append((j + 1, cells))
                j += 1
            if not t["rows"]:
                raise GrammarError(f"{path}:{i + 1}: table has no rows")
            tables.append(t)
            i = j
        else:
            if lines[i].strip().startswith("|") and head and not sep:
                raise GrammarError(f"{path}:{i + 1}: table row outside a table (missing header separator?)")
            i += 1
    return tables


def _table(path, cols, required=True):
    ts = [t for t in read_tables(path) if t["header"] == cols]
    others = [t for t in read_tables(path) if t["header"] != cols]
    if required and not ts:
        found = "; ".join(" | ".join(t["header"]) for t in others) or "none"
        raise GrammarError(f"{path}: no table with columns {' | '.join(cols)} (found: {found})")
    return ts


def _need(path, ln, cols, cells, names):
    for n in names:
        if not cells[cols.index(n)]:
            raise GrammarError(f"{path}:{ln}: empty '{n}' cell")


def load_schema(root=ROOT):
    path = os.path.join(root, "schema", "hardpoints.md")
    out = {}
    for t in _table(path, SCHEMA_COLS):
        for ln, c in t["rows"]:
            _need(path, ln, SCHEMA_COLS, c, SCHEMA_COLS)
            name, meaning, unit = c
            if not NAME_RE.match(name):
                raise GrammarError(f"{path}:{ln}: bad hard point name '{name}'")
            if unit not in UNITS:
                raise GrammarError(f"{path}:{ln}: unit '{unit}' not in {sorted(UNITS)}")
            if name in out:
                raise GrammarError(f"{path}:{ln}: duplicate hard point '{name}' (first at line {out[name]['line']})")
            out[name] = {"meaning": meaning, "unit": unit, "line": ln}
    return out


def load_rules(root=ROOT):
    out = {}
    for fname, prefixes in RULE_FILES.items():
        path = os.path.join(root, "rules", fname)
        for t in _table(path, RULE_COLS):
            for ln, c in t["rows"]:
                _need(path, ln, RULE_COLS, c, ["ID", "Rule", "Boxy SUV", "Src", "Conf"])
                rid, rule, suv, sedan, src, conf = c
                if not ID_RE.match(rid):
                    raise GrammarError(f"{path}:{ln}: bad rule ID '{rid}' (expected e.g. GH-01)")
                if rid.split("-")[0] not in prefixes:
                    raise GrammarError(f"{path}:{ln}: rule {rid} does not belong in {fname} (prefixes {prefixes})")
                if rid in out:
                    raise GrammarError(f"{path}:{ln}: duplicate rule ID {rid} (first in {out[rid]['file']}:{out[rid]['line']})")
                bad = [s for s in src.split("/") if s.strip() not in SRC_CODES]
                if bad:
                    raise GrammarError(f"{path}:{ln}: Src '{src}' has unknown code(s) {bad}; use {sorted(SRC_CODES)} joined by '/'")
                head = conf.split(",")[0].strip()
                if head not in CONF_HEADS:
                    raise GrammarError(f"{path}:{ln}: Conf '{conf}' must start with one of {sorted(CONF_HEADS)}")
                out[rid] = {"subsystem": rid.split("-")[0], "rule": rule, "boxy_suv": suv, "sedan": sedan, "src": src,
                            "conf": conf, "to_measure": "measure" in conf,
                            "values": {"boxy_suv": numbers(suv), "sedan": numbers(sedan)},
                            "file": os.path.relpath(path, root), "line": ln}
    return out


def load_bodytype(name, rules, root=ROOT):
    path = os.path.join(root, "bodytypes", name + ".md")
    out = {}
    for t in _table(path, BODYTYPE_COLS):
        for ln, c in t["rows"]:
            _need(path, ln, BODYTYPE_COLS, c, ["ID", "Boxy SUV"])
            rid, _sub, _rule, val, src, conf = c
            if rid not in rules:
                raise GrammarError(f"{path}:{ln}: rule {rid} is not in rules/")
            if val != rules[rid]["boxy_suv"]:
                raise GrammarError(f"{path}:{ln}: {rid} value '{val}' differs from {rules[rid]['file']}:{rules[rid]['line']} "
                                   f"'{rules[rid]['boxy_suv']}'")
            if src != rules[rid]["src"] or conf != rules[rid]["conf"]:
                raise GrammarError(f"{path}:{ln}: {rid} Src/Conf differ from {rules[rid]['file']}:{rules[rid]['line']}")
            if rid in out:
                raise GrammarError(f"{path}:{ln}: duplicate rule ID {rid}")
            out[rid] = {"value": val, "values": numbers(val), "line": ln}
    missing = sorted(set(rules) - set(out))
    if missing:
        raise GrammarError(f"{path}: rules missing from the body type: {missing}")
    return out


def _num(path, ln, text, what):
    try:
        return float(text)
    except ValueError:
        raise GrammarError(f"{path}:{ln}: {what} '{text}' is not a number") from None


def load_car(name, schema, rules, root=ROOT):
    path = os.path.join(root, "cars", name + ".md")
    hps = {}
    for t in _table(path, CAR_HP_COLS):
        for ln, c in t["rows"]:
            _need(path, ln, CAR_HP_COLS, c, ["Name", "Value", "Unit", "Source", "Confidence", "Evidence"])
            hp, val, unit, src, conf, real, ev = c
            if hp not in schema:
                raise GrammarError(f"{path}:{ln}: '{hp}' is not a hard point in schema/hardpoints.md")
            if hp in hps:
                raise GrammarError(f"{path}:{ln}: duplicate hard point {hp}")
            if unit != schema[hp]["unit"]:
                raise GrammarError(f"{path}:{ln}: {hp} unit '{unit}' but the schema says '{schema[hp]['unit']}'")
            if not src.startswith(CAR_SOURCES):
                raise GrammarError(f"{path}:{ln}: Source '{src}' must start with one of {CAR_SOURCES}")
            if conf not in CAR_CONF:
                raise GrammarError(f"{path}:{ln}: Confidence '{conf}' not in {sorted(CAR_CONF)}")
            hps[hp] = {"value": _num(path, ln, val, hp), "unit": unit, "source": src, "confidence": conf, "real_car": real,
                       "evidence": ev, "line": ln}
    missing = [n for n in schema if n not in hps]
    if missing:
        raise GrammarError(f"{path}: hard points missing from the car sheet: {missing}")
    rr = {}
    for t in _table(path, CAR_RULE_COLS, required=False):
        for ln, c in t["rows"]:
            _need(path, ln, CAR_RULE_COLS, c, ["ID", "Default (boxy SUV)", "Measured", "Evidence"])
            rid, default, meas, unit, ev = c
            if rid not in rules:
                raise GrammarError(f"{path}:{ln}: rule {rid} is not in rules/")
            if default != rules[rid]["boxy_suv"]:
                raise GrammarError(f"{path}:{ln}: {rid} default '{default}' differs from the rule's '{rules[rid]['boxy_suv']}'")
            if not numbers(meas):
                raise GrammarError(f"{path}:{ln}: {rid} measured cell '{meas}' has no number")
            if rid in rr:
                raise GrammarError(f"{path}:{ln}: duplicate rule row {rid}")
            rr[rid] = {"default": default, "measured": meas, "values": numbers(meas), "unit": unit, "evidence": ev, "line": ln}
    overall = {}
    for t in _table(path, CAR_OVERALL_COLS, required=False):
        for ln, c in t["rows"]:
            _need(path, ln, CAR_OVERALL_COLS, c, ["Quantity", "Sheet", "Real car", "Status"])
            overall[c[0]] = {"sheet": _num(path, ln, c[1], "Sheet"), "real": _num(path, ln, c[2], "Real car"), "status": c[3],
                             "difference": c[4], "source": c[5], "line": ln}
    return {"hardpoints": hps, "rules": rr, "overall": overall}


def load(root=ROOT):
    schema = load_schema(root)
    rules = load_rules(root)
    bodytypes = {os.path.splitext(f)[0]: load_bodytype(os.path.splitext(f)[0], rules, root)
                 for f in sorted(os.listdir(os.path.join(root, "bodytypes"))) if f.endswith(".md")}
    cars = {os.path.splitext(f)[0]: load_car(os.path.splitext(f)[0], schema, rules, root)
            for f in sorted(os.listdir(os.path.join(root, "cars"))) if f.endswith(".md")}
    return {"schema": schema, "rules": rules, "bodytypes": bodytypes, "cars": cars}


def _selftest():
    """Malformed rows must raise; run against a temporary copy of the library."""
    import shutil
    import tempfile
    cases = {
        "missing cell": ("rules/greenhouse.md", "| GH-01 |", "| GH-01 | only two |"),
        "bad ID": ("rules/bodyside.md", "| BS-07 |", "| BS-7 |"),
        "wrong file prefix": ("rules/layout.md", "| LAY-06 |", "| GH-99 |"),
        "unknown Src": ("rules/front_rear.md", "| P | A |", "| X | A |"),
        "body type mismatch": ("bodytypes/boxy_suv.md", "| sag 0.030 |", "| sag 0.031 |"),
        "car value not a number": ("cars/landcruiser80.md", "| WB | 2.850 |", "| WB | two |"),
        "car hard point missing": ("cars/landcruiser80.md", "| GROUND_CLEAR |", "| GROUND_CLEARANCE |"),
    }
    ok = True
    for what, (rel, old, new) in cases.items():
        tmp = tempfile.mkdtemp()
        try:
            dst = os.path.join(tmp, "g")
            shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns("tools", "__pycache__"))
            p = os.path.join(dst, rel)
            s = open(p, encoding="utf-8").read()
            if old not in s:
                print(f"  selftest {what}: pattern not found in {rel}, skipped")
                continue
            if what == "missing cell":
                lines = s.splitlines()
                idx = next(i for i, l in enumerate(lines) if l.startswith(old))
                lines[idx] = new
                s = "\n".join(lines) + "\n"
            else:
                s = s.replace(old, new, 1)
            open(p, "w", encoding="utf-8").write(s)
            try:
                load(dst)
                print(f"  selftest {what}: NOT rejected")
                ok = False
            except GrammarError as e:
                print(f"  selftest {what}: rejected -> {str(e).replace(dst + os.sep, '')}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return ok


def main(argv):
    try:
        g = load()
    except GrammarError as e:
        print(f"GRAMMAR ERROR: {e}", file=sys.stderr)
        return 1
    print(f"schema: {len(g['schema'])} hard points")
    by_sub = {}
    for rid, r in g["rules"].items():
        by_sub.setdefault(r["subsystem"], []).append(rid)
    print("rules: " + ", ".join(f"{k} {len(v)}" for k, v in by_sub.items()) + f" ({len(g['rules'])} total, "
          f"{sum(r['to_measure'] for r in g['rules'].values())} marked measure)")
    for k, v in g["bodytypes"].items():
        print(f"body type {k}: {len(v)} rules, matches rules/")
    for k, v in g["cars"].items():
        conf = {}
        for h in v["hardpoints"].values():
            conf[h["confidence"]] = conf.get(h["confidence"], 0) + 1
        print(f"car {k}: {len(v['hardpoints'])} hard points {conf}, {len(v['rules'])} rule rows measured, "
              f"{len(v['overall'])} overall rows")
    if "--selftest" in argv:
        if not _selftest():
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
