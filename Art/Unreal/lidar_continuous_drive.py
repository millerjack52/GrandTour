"""Drive the surveyed LiDAR road with the pickup's ordinary steering and pedals."""

import bisect
import itertools
import json
import math
import sys
import time
import traceback
from pathlib import Path

import unreal as u


def closest(points, station, x, y, first, last):
    best = None
    for i in range(first, min(last, len(points) - 1)):
        a, b = points[i : i + 2]
        dx, dy = b[0] - a[0], b[1] - a[1]
        t = max(0, min(1, ((x - a[0]) * dx + (y - a[1]) * dy) / (dx * dx + dy * dy)))
        offset = math.hypot(a[0] + t * dx - x, a[1] + t * dy - y)
        if best is None or offset < best[0]:
            best = offset, i, station[i] + t * (station[i + 1] - station[i])
    return best


class RoadDrive:
    def __init__(self, output, start):
        root = Path(u.Paths.project_dir()).resolve()
        roads = json.loads((root / "Art/Export/LidarStudy/Place/roads.json").read_text())
        routes = {r["name"]: r["points"] for r in roads}
        access = routes["Riverside access"]
        track = routes["Logging mud track fce5"]
        self.points = [p for p, _ in itertools.groupby(access + track)]
        self.station = [
            0,
            *itertools.accumulate(
                math.dist(a, b) / 100 for a, b in zip(self.points, self.points[1:])
            ),
        ]
        junction = self.station[self.points.index(track[0])]
        self.sections = [
            (junction + 45, "forest_access"),
            (junction + 115, "river"),
            (junction + 480, "wooded_track"),
            (junction + 535, "bog_approach"),
            (junction + 630, "deep_bog"),
        ]
        self.world = u.find_object(
            None, "/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy.L_LidarStudy"
        )
        self.pc = u.GameplayStatics.get_player_controller(self.world, 0)
        self.car = self.pc.get_car()
        assert u.GameplayStatics.get_player_pawn(self.world, 0) == self.car
        self.move = self.car.get_chaos_movement()
        p = self.car.get_actor_location()
        offset, self.index, self.start_station = closest(
            self.points, self.station, p.x, p.y, 0, len(self.points) - 1
        )
        poses = json.loads((root / "Art/lidar_driving_baseline_poses.json").read_text())
        pose = next(item for item in poses if item["name"] == start)
        assert offset < 600 and math.hypot(p.x - pose["x"], p.y - pose["y"]) < 1100, (
            start,
            offset,
            p,
        )
        self.output = output
        self.travel = 0
        self.previous = (p.x, p.y)
        self.stall_station = self.start_station
        self.previous_section = ""
        self.started = self.last_progress = time.monotonic()
        self.last_input = 0
        self.recoveries = []
        self.retry_after = self.started + 7
        self.reverse_until = 0
        self.lane_offset = 0
        self.next_report = self.started + 10
        self.samples = []
        self.handle = None
        drive = self.car.get_drivetrain()
        self.drivetrain = drive
        self.traction = self.car.get_traction()
        drive.set_low_range(True)
        drive.set_diff_lock(True)
        self.car.reset_driving_inputs()
        self.move.set_target_gear(1, True)
        self.move.set_brake_input(0)
        self.move.set_handbrake_input(False)
        # The initial checkpoint placement can leave an airborne chassis asleep.
        # Wake it once before sampling. The normal sleep policy applies on the road.
        self.move.set_sleeping(False)

    def command(self, value):
        u.SystemLibrary.execute_console_command(self.world, value, self.pc)

    def finish(self, reason):
        if self.handle is not None:
            u.unregister_slate_post_tick_callback(self.handle)
            self.handle = None
        self.car.reset_driving_inputs()
        self.move.set_handbrake_input(True)
        self.command("gt.Lidar.Present stop")
        payload = dict(
            reason=reason,
            columns=[
                "elapsed_s",
                "section",
                "station_m",
                "lateral_m",
                "x_cm",
                "y_cm",
                "z_cm",
                "speed_mps",
                "wheel_contacts",
                "throttle",
                "brake",
                "steer",
                "gear",
                "engine_rpm",
                "max_sinkage_fraction",
            ],
            start_station_m=self.start_station,
            travel_m=self.travel,
            elapsed_s=time.monotonic() - self.started,
            recoveries=self.recoveries,
            samples=self.samples,
        )
        (self.output / "continuous-drive.json").write_text(
            json.dumps(payload, separators=(",", ":"))
        )
        u.log(
            f"GT_LINKED_END reason={reason} travel_m={self.travel:.2f} samples={len(self.samples)}"
        )
        self.command("CsvProfile STOP")

    def tick(self, delta_seconds):
        try:
            now = time.monotonic()
            if now - self.last_input < 0.10:
                return
            self.last_input = now
            if self.pc.get_workshop().is_open() or u.GameplayStatics.is_game_paused(self.world):
                self.finish("workshop_or_pause")
                return
            if u.GameplayStatics.get_player_pawn(self.world, 0) != self.car:
                self.finish("driver_changed")
                return
            pos = self.car.get_actor_location()
            offset, self.index, here = closest(
                self.points, self.station, pos.x, pos.y, max(0, self.index - 6), self.index + 14
            )
            step = math.dist(self.previous, (pos.x, pos.y)) / 100
            if step > 12:
                self.finish("position_jump")
                return
            self.travel += step
            self.previous = pos.x, pos.y
            section = next((name for limit, name in self.sections if here < limit), None)
            if (
                section is None
                or offset > 1800
                or now - self.last_progress > 35
                or now - self.started > 475
            ):
                reason = (
                    "end_of_route"
                    if section is None
                    else "off_road"
                    if offset > 1800
                    else "stalled"
                    if now - self.last_progress > 35
                    else "time_limit"
                )
                self.finish(reason)
                return
            if section != self.previous_section:
                self.command("gt.Lidar.Present mark " + section)
                u.log(f"GT_LINKED_SECTION {section} station={here:.2f}")
                self.previous_section = section
            if here > self.stall_station + 1:
                self.last_progress, self.stall_station = now, here
            speed = self.car.get_velocity().length() / 100
            # Rock out of a rut as a driver would. The drivetrain uses the brake
            # pedal for reverse at low speed. Keep the original timed stall limit.
            if now - self.last_progress > 6 and now > self.retry_after and speed < 0.7:
                self.lane_offset = 150 if len(self.recoveries) % 2 == 0 else -150
                self.reverse_until = now + 2.5
                self.retry_after = now + 11
                self.recoveries.append(
                    [round(now - self.started, 2), round(here, 2), self.lane_offset / 100]
                )
            target_station = min(self.station[-1], here + max(4, min(18, speed * 0.85)))
            target_index = min(
                len(self.points) - 2, bisect.bisect_right(self.station, target_station) - 1
            )
            a, b = self.points[target_index : target_index + 2]
            t = (target_station - self.station[target_index]) / (
                self.station[target_index + 1] - self.station[target_index]
            )
            dx, dy = b[0] - a[0], b[1] - a[1]
            length = math.hypot(dx, dy)
            target_x = a[0] + t * dx - dy / length * self.lane_offset
            target_y = a[1] + t * dy + dx / length * self.lane_offset
            bearing = math.atan2(target_y - pos.y, target_x - pos.x)
            forward = self.car.get_actor_forward_vector()
            angle = math.remainder(bearing - math.atan2(forward.y, forward.x), 2 * math.pi)
            steer = max(-1, min(1, math.degrees(angle) / 20))
            target_speed = max(3.5, (9 if section == "forest_access" else 6) - 3 * abs(steer))
            throttle = max(0, min(1, 0.45 + 0.32 * (target_speed - speed)))
            brake = max(0, min(0.65, (speed - target_speed - 1) * 0.25))
            if now < self.reverse_until:
                throttle, brake, steer = 0, 0.65, -0.45 * steer
            self.car.set_raw_steer(steer)
            self.move.set_throttle_input(throttle)
            self.move.set_brake_input(brake)
            self.move.set_handbrake_input(False)
            contacts = sum(
                u.ChaosWheeledVehicleMovementComponent.break_wheel_status(
                    self.move.get_wheel_state(i)
                )[0]
                for i in range(4)
            )
            if now >= self.next_report:
                u.log(
                    f"GT_LINKED_DRIVING {section} station={here:.1f} travel_m={self.travel:.1f} speed_mps={speed:.1f} wheel_contacts={contacts}"
                )
                self.next_report = now + 10
            self.samples.append(
                [
                    round(now - self.started, 3),
                    section,
                    round(here, 2),
                    round(offset / 100, 2),
                    round(pos.x, 1),
                    round(pos.y, 1),
                    round(pos.z, 1),
                    round(speed, 2),
                    contacts,
                    round(throttle, 2),
                    round(brake, 2),
                    round(steer, 2),
                    self.drivetrain.get_gear(),
                    round(self.drivetrain.get_engine_rpm()),
                    round(self.traction.get_max_sinkage_fraction(), 3),
                ]
            )
        except Exception:
            u.log_error(traceback.format_exc())
            self.finish("probe_error")


try:
    trial = RoadDrive(Path(sys.argv[1]), sys.argv[2])
    trial.handle = u.register_slate_post_tick_callback(trial.tick)
except Exception:
    world = u.find_object(None, "/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy.L_LidarStudy")
    u.SystemLibrary.execute_console_command(world, "gt.Lidar.Present stop")
    u.SystemLibrary.execute_console_command(world, "CsvProfile STOP")
    raise
