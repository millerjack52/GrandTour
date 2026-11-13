"""Every number the G1 build uses, read through grammar.py from the car sheet and the rules, with the row it came
from. Nothing here types a design number: the build asks for a hard point, a rule value or a construction value and
this module records where it was read."""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.dirname(HERE)
sys.path.insert(0, LIB)
import grammar  # noqa: E402

CAR = "landcruiser80"
CAR_RULE_COLS = ["ID", "Value", "Unit", "Src", "Conf", "Note"]
CONS_COLS = ["Name", "Value", "Unit", "Src", "Note"]
KV_RE = re.compile(r"^\s*([A-Za-z_]+)?\s*(-?\d+(?:\.\d+)?)\s*$")


def kv(text, where):
    """'B 0.118, C 0.113' -> {'B': 0.118, 'C': 0.113}; 'bow 0.010' -> {'bow': 0.01}; '0.020' -> {'': 0.02}."""
    out = {}
    for part in text.split(","):
        m = KV_RE.match(part)
        if not m:
            raise grammar.GrammarError(f"{where}: value part '{part.strip()}' is not 'key number' or 'number'")
        out[m.group(1) or ""] = float(m.group(2))
    return out


class Spec:
    def __init__(self):
        self.g = grammar.load(LIB)
        self.rules = self.g["rules"]
        self.car = self.g["cars"][CAR]
        path = os.path.join(LIB, "cars", CAR + ".md")
        self.car_rules, self.cons = {}, {}
        for t in grammar.read_tables(path):
            if t["header"] == CAR_RULE_COLS:
                for ln, c in t["rows"]:
                    rid = c[0]
                    if rid not in self.rules:
                        raise grammar.GrammarError(f"{path}:{ln}: rule {rid} not in rules/")
                    if any(s not in grammar.SRC_CODES for s in c[3].split("/")) or c[4] not in ("A", "D", "M"):
                        raise grammar.GrammarError(f"{path}:{ln}: bad Src '{c[3]}' or Conf '{c[4]}'")
                    self.car_rules[rid] = {"kv": kv(c[1], f"{path}:{ln}"), "text": c[1], "src": c[3], "conf": c[4], "line": ln}
            elif t["header"] == CONS_COLS:
                for ln, c in t["rows"]:
                    self.cons[c[0]] = {"value": kv(c[1], f"{path}:{ln}")[""], "src": c[3], "line": ln, "note": c[4]}
        if not self.car_rules or not self.cons:
            raise grammar.GrammarError(f"{path}: missing the 'Rule values used for this car' or 'Construction values' table")
        self.prov = {}

    def hp(self, name, use=None):
        h = self.car["hardpoints"][name]
        self.prov[use or name] = f"cars/{CAR}.md hard point {name} = {h['value']:g} ({h['source']}, {h['confidence']}, line {h['line']})"
        return h["value"]

    def rule(self, rid, key=None, idx=0, use=None):
        """Car value of a rule if the car sheet lists it, else the boxy SUV default from rules/."""
        if rid in self.car_rules:
            r = self.car_rules[rid]
            d = r["kv"]
            k = key if key is not None else (next(iter(d)) if len(d) == 1 else None)
            if k not in d:
                raise grammar.GrammarError(f"cars/{CAR}.md:{r['line']}: {rid} has no '{key}' in '{r['text']}'")
            self.prov[use or f"{rid} {key or ''}".strip()] = f"cars/{CAR}.md rule values {rid} {k} = {d[k]:g} (Src {r['src']}, Conf {r['conf']}, line {r['line']})"
            return d[k]
        r = self.rules[rid]
        v = r["values"]["boxy_suv"]
        if idx >= len(v):
            raise grammar.GrammarError(f"{r['file']}:{r['line']}: {rid} boxy value '{r['boxy_suv']}' has no number #{idx}")
        self.prov[use or f"{rid} #{idx}"] = f"{r['file'].replace(os.sep, '/')} {rid} boxy SUV '{r['boxy_suv']}' number {idx + 1} = {v[idx]:g} (Src {r['src']}, Conf {r['conf']}, line {r['line']})"
        return v[idx]

    def con(self, name, use=None):
        c = self.cons[name]
        self.prov[use or name] = f"cars/{CAR}.md construction value {name} = {c['value']:g} (Src {c['src']}, line {c['line']})"
        return c["value"]
