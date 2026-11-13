# G1 import (Docs/OWPainterlyGrassPlan.md): bring the painterly grass card
# PNGs into /Game/OWGame/Dev/DressingLab/Grass. Run AFTER the contact-sheet
# user gate passes. Cards come from DevGeneratePainterlyGrassCards.py, which
# writes them to GrassCards/ next to this script. Headless (editor CLOSED;
# PowerShell):
#   & 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
#     C:\GrandTour\GrandTour.uproject -run=PythonScript
#     "-Script=C:/GrandTour/Art/dressing/ported/ClaudeImportGrassCards.py"
#     -NullRHI -Unattended -NoSplash -NoSound "-abslog=<abs log>"
# Rerunnable: reimports over existing textures. sRGB stays ON (albedo cards).
import json
import traceback
from pathlib import Path

import unreal

SRC_DIR = Path(__file__).resolve().parent / "GrassCards"
DEST = "/Game/OWGame/Dev/DressingLab/Grass"
REPORT_PATH = str(Path(__file__).with_name("ClaudeImportGrassCardsReport.json"))

report = {"ok": True, "imported": [], "errors": []}
try:
    pngs = sorted(p for p in SRC_DIR.glob("T_OW*.png"))
    if not pngs:
        raise RuntimeError("no T_OW*.png cards in " + str(SRC_DIR))
    tasks = []
    for p in pngs:
        t = unreal.AssetImportTask()
        t.set_editor_property("filename", str(p))
        t.set_editor_property("destination_path", DEST)
        t.set_editor_property("automated", True)
        t.set_editor_property("replace_existing", True)
        t.set_editor_property("save", True)
        tasks.append(t)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    for p in pngs:
        ap = "{}/{}".format(DEST, p.stem)
        if not unreal.EditorAssetLibrary.does_asset_exist(ap):
            report["errors"].append("missing after import: " + ap)
            continue
        tex = unreal.EditorAssetLibrary.load_asset(ap)
        if not tex.get_editor_property("srgb"):
            tex.set_editor_property("srgb", True)
            unreal.EditorAssetLibrary.save_loaded_asset(tex, only_if_is_dirty=False)
        report["imported"].append(ap)
    if report["errors"]:
        report["ok"] = False
except Exception as exc:  # noqa: BLE001
    report["ok"] = False
    report["errors"].append("{}: {}".format(type(exc).__name__, exc))
    report["trace"] = traceback.format_exc()

with open(REPORT_PATH, "w") as fh:
    json.dump(report, fh, indent=2)
if not report["ok"]:
    raise RuntimeError("grass card import failed; see report")
unreal.log("GRASS CARDS imported: {}".format(len(report["imported"])))
