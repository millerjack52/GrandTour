"""Preview a physical bank bake in the open LiDAR editor world. Writes only to Saved."""

import array
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import traceback

import unreal as u


ROOT = Path(u.Paths.project_dir()).resolve()
LEVEL = "/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy"
PLACE = Path(os.environ.get("GT_BANK_PLACE", ROOT / "Art/Export/LidarStudy/Place"))
run_id = re.search(r"(?:^|\s)-GTBankPreviewRun=([0-9a-fA-F-]+)(?:\s|$)", u.SystemLibrary.get_command_line())
OUT = ROOT / "Saved/LidarBankRelief" / (run_id.group(1) if run_id else str(time.time_ns()))
OUT.mkdir(parents=True)
ACTORS = u.get_editor_subsystem(u.EditorActorSubsystem)
LEVELS = u.get_editor_subsystem(u.LevelEditorSubsystem)
EDITOR = u.get_editor_subsystem(u.UnrealEditorSubsystem)


def survey(actors):
    bounds = {"tiles": [], "fitted": [], "water": []}
    for actor in actors:
        if isinstance(actor, u.GTRoadReliefTile):
            pos = actor.get_actor_location()
            bounds["tiles"].append([pos.x / 100, pos.y / 100, actor.span_cm / 100])
            continue
        label = actor.get_actor_label()
        if "BankSkin" in label:
            key = "fitted"
        elif isinstance(actor, u.StaticMeshActor) and "Pond" in label and "Water" in label:
            key = "water"
        else:
            continue
        center, extent = actor.get_actor_bounds(False)
        bounds[key].append([(center.x - extent.x) / 100, (center.y - extent.y) / 100,
                            (center.x + extent.x) / 100, (center.y + extent.y) / 100])
    (OUT / "surface.json").write_text(json.dumps(bounds))


def capture_current_height(author, landscape):
    # The controller's normal base predates the road recesses. Capture the saved
    # surface with a temporary controller, then verify every encoded height.
    digest = author.current_terrain_digest().lower()
    probe = ACTORS.spawn_actor_from_class(u.GTProceduralGround, u.Vector())
    try:
        for prop in ["surface", "output_asset_root", "paint_texture", "style_texture", "macro_texture"]:
            probe.set_editor_property(prop, author.get_editor_property(prop))
        probe.set_editor_property("scatter_rules", [])
        author.landscape = None
        probe.landscape = landscape
        if not probe.capture_base() or probe.base_terrain_digest().lower() != digest:
            raise RuntimeError("Failed to capture live landscape: " + str(probe.last_message))
        scale = landscape.get_actor_scale3d()
        base_z = landscape.get_actor_location().z
        grid = dict(origin_m=[-1850., -1850.], cell_m=scale.x / 100, unit_m=scale.z / 12800,
                    zero_m=(base_z - 32768 * scale.z / 128) / 100, md5=digest)
        xs = [-185000 + i * scale.x for i in range(2017)]
        data = array.array("H")
        for j in range(2017):
            y = -185000 + j * scale.y
            data.extend(round((probe.base_height_at(u.Vector2D(x, y)) - base_z) * 128 / scale.z) + 32768
                        for x in xs)
            if j % 100 == 0:
                yield .01
        raw = data.tobytes()
        if hashlib.md5(raw).hexdigest() != digest:
            raise RuntimeError("The survey did not reproduce the current terrain byte for byte")
        (OUT / "original.r16").write_bytes(raw)
        (OUT / "grid.json").write_text(json.dumps(grid))
        return grid
    finally:
        probe.landscape = None
        author.landscape = landscape
        ACTORS.destroy_actor(probe)


def run():
    if not LEVELS.load_level(LEVEL):
        raise RuntimeError("Could not load the LiDAR study")
    yield 3
    actors = ACTORS.get_all_level_actors()
    landscape, = [a for a in actors if isinstance(a, u.Landscape)]
    author, = [a for a in actors if isinstance(a, u.GTProceduralGround)]
    survey(actors)
    grid = yield from capture_current_height(author, landscape)
    python = ROOT / "Saved/Tools/TerrainPython/Scripts/python.exe"
    scripts = ROOT / "Art/tools"
    subprocess.run([python, scripts / "prepare_lidar_bank_masks.py", PLACE, OUT / "surface.json",
                    OUT / "grid.json", OUT], check=True)
    command = [python, scripts / "bake_riverbank_relief.py", OUT / "original.r16", OUT / "course.json",
               OUT / "river-wet.png", OUT / "protected.png", OUT / "candidate.r16", "--origin",
               *map(str, grid["origin_m"]), "--unit", str(grid["unit_m"]), "--zero", str(grid["zero_m"]),
               "--cell", str(grid["cell_m"])]
    reach = os.environ.get("GT_BANK_REACH_M", "3140 3520")
    if reach != "all":
        command.extend(["--reach", *reach.split()])
    report = json.loads(subprocess.check_output(command))
    views = [((-50900, -35250, 4700), (-47900, -33100, 4580)),
             ((-49500, -33800, 4635), (-48270, -30650, 4610)),
             ((-54880, -34150, 4660), (-56210, -35480, 4830))]
    world = EDITOR.get_editor_world()
    for setting in json.loads((ROOT / "Art/lidar_performance.json").read_text())["commands"]:
        u.SystemLibrary.execute_console_command(world, setting)
    LEVELS.editor_set_game_view(True)
    LEVELS.editor_set_viewport_realtime(True)
    for variant in ("original", "candidate"):
        if variant == "candidate":
            result = OUT / "candidate.r16"
            if not u.GTLandscapeSurfaceSetupLibrary.import_lidar_authoring_heights(landscape, str(result)):
                raise RuntimeError("Unreal rejected the candidate terrain")
            if author.current_terrain_digest().lower() != hashlib.md5(result.read_bytes()).hexdigest():
                raise RuntimeError("Candidate terrain readback differed")
        for index, (position, target) in enumerate(views):
            p = u.Vector(*position)
            EDITOR.set_level_viewport_camera_info(p, u.MathLibrary.find_look_at_rotation(p, u.Vector(*target)))
            yield 12
            photo = OUT / f"{variant}-{index}.png"
            u.AutomationLibrary.take_high_res_screenshot(1280, 720, str(photo))
            for _ in range(90):
                yield .5
                if photo.exists():
                    break
            else:
                raise RuntimeError(f"Missing capture {photo}")
    report.update(original_md5=grid["md5"], candidate_md5=author.current_terrain_digest().lower(),
                  source_place=str(PLACE), reach_metres=reach, captures="Unreal editor viewport")
    (OUT / "report.json").write_text(json.dumps(report, indent=2))


work = run()
busy = False
due = 0


def tick(_dt):
    global busy, due
    if busy or time.monotonic() < due:
        return
    busy = True
    try:
        delay = next(work)
        due = time.monotonic() + delay
        return
    except StopIteration:
        pass
    except Exception:
        (OUT / "error.txt").write_text(traceback.format_exc())
        u.log_error(traceback.format_exc())
    finally:
        busy = False
    u.unregister_slate_post_tick_callback(handle)
    u.SystemLibrary.quit_editor()


u.EditorPythonScripting.set_keep_python_script_alive(True)
handle = u.register_slate_post_tick_callback(tick)
