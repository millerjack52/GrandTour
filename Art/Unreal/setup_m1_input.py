"""setup_m1_input.py - the driving input assets, headless.

Run with Art\\setup_m1_input.bat (close the editor first). Writes /Game/GrandTour/Input/IA_Throttle,
IA_Brake, IA_Steer, IA_Handbrake, IA_Look, IA_Exit, IA_Reel, IA_CameraToggle, IA_DiffLock, IA_LowRange and IMC_Driving through UGTVehicleSetupLibrary, with
exactly the mappings AGTCarPawn builds at runtime (W/S or triggers, A/D or left stick with a 0.2
dead zone, Space or B handbrake, mouse or right stick look). Once they exist the pawn loads them
instead of building its own, so keys can be rebound in the editor; delete them to go back to the
built-in mapping. Safe to re-run: the assets are rewritten.
"""
import unreal

FOLDER = "/Game/GrandTour/Input"


def log(msg):
    unreal.log("SETUP_M1_INPUT " + msg)


saved = unreal.GTVehicleSetupLibrary.create_driving_input_assets(FOLDER)
log("saved %d assets under %s" % (saved, FOLDER))
if saved < 6:
    raise SystemExit("expected 6 input assets, saved %d" % saved)
imc = unreal.EditorAssetLibrary.load_asset(FOLDER + "/IMC_Driving")
# Python cannot see 5.8's mapping storage (the arrays it exposes stay empty); ask C++.
count = unreal.GTVehicleSetupLibrary.get_mapping_count(imc)
log("IMC_Driving has %d mappings" % count)
if count < 15:
    raise SystemExit("IMC_Driving is missing mappings")
log("DONE")
