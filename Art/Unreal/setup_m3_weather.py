"""setup_m3_weather.py - the weather content, headless.

Run with Art\\setup_m3_weather.bat (close the editor first; setup_m1_track and setup_m1_body must
have run before, and setup_m1_masters after them, once). In one commandlet:
- re-runs setup_m1_weather.py (it owns MPC_Weather and MF_Weather, which now carry the rain
  occlusion sample, the puddle mask and the CanPool input, and creates RT_RainOcclusion);
- re-runs setup_m1_body.py and setup_m1_masters.py, in that order: rebuilding MF_Weather severs
  every master's call to it, so the vehicle and glass masters are rebuilt by the body script and
  the rest re-routed by the masters script (which now repairs a severed BaseColor / Roughness
  from the master's own parameter nodes), and the environment master feeds CanPool;
- writes the five weather state assets DA_Weather_Clear / Overcast / Rain / Storm / Snow under
  /Game/GrandTour/Weather from the C++ defaults (UGTVehicleSetupLibrary.create_weather_state_assets).
Safe to re-run. Nothing here compiles HLSL: run Art\\weather_test.bat gpu for that.
"""
import os

import unreal

WEATHER_FOLDER = "/Game/GrandTour/Weather"
SCRIPT_DIR = os.path.join(unreal.Paths.project_dir(), "Art", "Unreal")
lib = unreal.GTVehicleSetupLibrary
eal = unreal.EditorAssetLibrary


def log(msg):
    unreal.log("SETUP_M3_WEATHER " + msg)


def run(name):
    path = os.path.join(SCRIPT_DIR, name)
    log("running " + name)
    src = open(path, encoding="utf-8").read()
    exec(compile(src, path, "exec"), {"__name__": "gt_" + name.replace(".py", ""), "__file__": path})


run("setup_m1_weather.py")
run("setup_m1_body.py")
run("setup_m1_masters.py")

saved = lib.create_weather_state_assets(WEATHER_FOLDER)
log("weather state assets saved: %d (expected 5)" % saved)
if saved < 5:
    raise SystemExit("weather asset writing fell short")
for name in ("DA_Weather_Clear", "DA_Weather_Overcast", "DA_Weather_Rain", "DA_Weather_Storm", "DA_Weather_Snow"):
    state = eal.load_asset(WEATHER_FOLDER + "/" + name)
    if state is None:
        raise SystemExit("missing " + name)
    values = state.get_editor_property("values")
    log("%s: rain %.2f fog %.3f temp %.0f over %.0f s" % (name, values.get_editor_property("rain_intensity"), values.get_editor_property("fog_density"),
                                                            values.get_editor_property("temperature_c"), state.get_editor_property("transition_seconds")))
rt = eal.load_asset("/Game/GrandTour/Materials/RT_RainOcclusion")
if rt is None:
    raise SystemExit("RT_RainOcclusion was not created")
log("DONE")
