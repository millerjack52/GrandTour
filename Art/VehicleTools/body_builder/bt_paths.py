"""Run parameters for the BT1 scripts, from environment variables (they reach Blender's Python too).

BT_VERSION: v01 (default, plan section 4 as run first) or v02 (plan section 6).
BT_VARIANT: P1, P4 or P16 (v02 only): penalty = the v01 penalty x 1, 4 or 16.
Output: Art/Export/VehicleTools/impreza-builder-bt1-<version>/ (v01) or .../<version>/<variant>/ (v02).
"""
import os

ROOT = r"C:\GrandTour"
VERSION = os.environ.get("BT_VERSION", "v01")
V2 = VERSION != "v01"
VARIANT = os.environ.get("BT_VARIANT", "P1")
PENALTY_FACTOR = {"P1": 1.0, "P4": 4.0, "P16": 16.0}[VARIANT]
IN_DIR = os.path.join(ROOT, r"Art\Export\VehicleTools\impreza-scaffold-cage-v02")
V01_DIR = os.path.join(ROOT, r"Art\Export\VehicleTools\impreza-builder-bt1-v01")
OUT_ROOT = os.path.join(ROOT, r"Art\Export\VehicleTools", "impreza-builder-bt1-" + VERSION)
OUT_DIR = os.path.join(OUT_ROOT, VARIANT) if V2 else OUT_ROOT
DEBUG_DIR = os.path.join(OUT_DIR, "debug")
