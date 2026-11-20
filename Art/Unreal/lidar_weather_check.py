"""Observe rain capture and material state as a parked LiDAR game changes weather."""

import json
import sys
from pathlib import Path

import unreal as u


action, directory = sys.argv[1:]
world = u.find_object(None, "/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy.L_LidarStudy")
weather = next(s for s in u.ObjectIterator(u.GTWeatherSubsystem) if s.get_outer() == world)
if action in ("rain", "snow", "clear"):
    weather.set_state(weather.find_state(action.title()), True)
elif action == "reset_wetness":
    weather.set_wetness_for_test(0)
else:
    rain = weather.get_rain_emitter()
    mpc = u.load_asset("/Game/GrandTour/Materials/MPC_Weather")
    library = u.MaterialLibrary
    row = dict(
        frame_state=action,
        captures=rain.capture_count,
        drops=rain.live_drops,
        state=weather.get_state_name(),
        wetness=weather.get_wetness(),
        snow=weather.get_snow_amount(),
        enabled=library.get_scalar_parameter_value(world, mpc, "OcclusionEnabled"),
        gate=u.SystemLibrary.get_console_variable_int_value("gt.Weather.SkipDryOcclusion"),
        centre=rain.get_capture_centre().to_tuple(),
    )
    if row["enabled"]:
        rt = u.load_asset("/Game/GrandTour/Materials/RT_RainOcclusion")
        row["depth_cm"] = [
            u.RenderingLibrary.read_render_target_raw_pixel(world, rt, x, y, False).r
            for x, y in ((205, 205), (242, 261), (291, 282), (318, 230))
        ]
    with (Path(directory) / "weather.jsonl").open("a", encoding="utf-8") as log:
        log.write(json.dumps(row) + "\n")
