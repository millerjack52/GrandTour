"""Author seasonal/mood color variants of the OW tree foliage MIs.

RUN IN-EDITOR: py "C:/GrandTour/Art/dressing/ported/ClaudeAuthorFoliageVariants.py"

For each species (Beech/Birch/FirTree) creates three variants of
MI_OWFoliage_<species> in /Game/OWGame/Dev/DressingLab/TreeMIs/:
  _Spring - fresher, brighter, shifted toward young green
  _Autumn - warmer, saturated, shifted toward orange/red
  _Cold   - desaturated, darker, shifted toward teal (mountain/dusk)

Variants are HSV TRANSFORMS of each species' current effective palette (all
five vector params move together), so species identity and the shader's
internal color relationships survive. The base MI_OWFoliage_* stay untouched
as the 'default' option. Rerunnable: existing variants are re-tinted from the
CURRENT base MI values (tune a base, rerun to refresh its variants).
Trunks have no color params on MM_Trunk (texture-driven) - trunk tinting
would need an adapted master copy; out of scope here.
"""

from __future__ import annotations

import colorsys
import json
from pathlib import Path
import traceback

import unreal


OWN_DIR = "/Game/OWGame/Dev/DressingLab/TreeMIs"
SPECIES = ["Beech", "Birch", "FirTree"]
COLOR_PARAMS = ["TopColor", "NoiseColor", "SubsurfaceColor",
                "GradientColor1", "GradientColor2"]

# (suffix, target hue deg, hue blend 0-1, sat mul, val mul)
VARIANTS = [
    ("Spring", 95.0, 0.50, 0.90, 1.20),
    ("Autumn", 28.0, 0.65, 1.15, 1.00),
    ("Cold", 185.0, 0.45, 0.65, 0.85),
    # Subtle per-tree tones (spawner mixes these with the base MI so trees of
    # one species differ slightly - NOT seasonal looks, keep them gentle):
    ("ToneWarm", 40.0, 0.15, 1.05, 1.06),
    ("ToneCool", 160.0, 0.12, 0.88, 0.96),
]

REPORT_PATH = Path(__file__).with_name("ClaudeAuthorFoliageVariantsReport.json")

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
            unreal.log_error(f"FOLIAGE_VARIANTS {name}: {exc!r}")
            return None

    return decorate


def _shift(color, target_hue_deg, blend, sat_mul, val_mul):
    h, s, v = colorsys.rgb_to_hsv(
        max(0.0, float(color.r)), max(0.0, float(color.g)), max(0.0, float(color.b)))
    target = (target_hue_deg / 360.0) % 1.0
    # shortest-path hue blend so reds don't detour through cyan
    delta = ((target - h + 0.5) % 1.0) - 0.5
    h = (h + delta * blend) % 1.0
    s = min(1.0, s * sat_mul)
    v = max(0.0, v * val_mul)   # HDR-safe: no upper clamp, painterly glows allowed
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return unreal.LinearColor(r, g, b, float(color.a))


@step("author_variants")
def author_variants():
    mel = unreal.MaterialEditingLibrary
    made = {}
    for species in SPECIES:
        base_path = f"{OWN_DIR}/MI_OWFoliage_{species}"
        base = unreal.load_asset(base_path)
        if base is None:
            raise RuntimeError(f"missing base MI {base_path} - run "
                               "ClaudeSetupFoliageMIs.py first")
        palette = {p: mel.get_material_instance_vector_parameter_value(base, p)
                   for p in COLOR_PARAMS}
        for suffix, hue, blend, sat, val in VARIANTS:
            dst_path = f"{OWN_DIR}/MI_OWFoliage_{species}_{suffix}"
            if not unreal.EditorAssetLibrary.does_asset_exist(dst_path):
                if unreal.EditorAssetLibrary.duplicate_asset(base_path, dst_path) is None:
                    raise RuntimeError(f"duplicate failed for {dst_path}")
            mi = unreal.load_asset(dst_path)
            applied = {}
            for pname, color in palette.items():
                new_color = _shift(color, hue, blend, sat, val)
                mel.set_material_instance_vector_parameter_value(mi, pname, new_color)
                applied[pname] = [round(new_color.r, 4), round(new_color.g, 4),
                                  round(new_color.b, 4)]
            mi.modify()
            unreal.EditorAssetLibrary.save_asset(dst_path, only_if_is_dirty=False)
            made[f"MI_OWFoliage_{species}_{suffix}"] = applied
    return made


REPORT_PATH.write_text(json.dumps(result, indent=2, default=str))
if not result["ok"]:
    raise RuntimeError(f"one or more steps failed - see {REPORT_PATH}")
unreal.log("FOLIAGE_VARIANTS complete - 9 variant MIs in " + OWN_DIR)
