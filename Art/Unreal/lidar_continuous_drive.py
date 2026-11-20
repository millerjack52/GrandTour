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
        self.track_start_m = junction
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
        recovery_starts = {"track_start": (1, 3), "track192": (2, 192), "track270": (3, 270), "bog530": (4, 530)}
        if start in recovery_starts:
            lane, track_station = recovery_starts[start]
            (route,) = u.GameplayStatics.get_all_actors_of_class(self.world, u.GTMudRoute)
            checkpoint = route.get_editor_property("RecoveryPoints")[lane - 1].translation
            assert self.pc.get_editor_property("SelectedLane") == lane
            assert abs(self.start_station - junction - track_station) < 12
            expected_xy = checkpoint.x, checkpoint.y
        else:
            poses = json.loads((root / "Art/lidar_driving_baseline_poses.json").read_text())
            pose = next(item for item in poses if item["name"] == start)
            expected_xy = pose["x"], pose["y"]
        assert offset < 600 and math.dist((p.x, p.y), expected_xy) < 1100, (
            start,
            offset,
            p,
        )
        self.output = output
        self.clearance = None
        clearance_file = output / "log-clearance.json"
        if clearance_file.exists():
            assert start == "track270"
            sys.path.insert(0, str(root / "Art/Unreal"))
            from lidar_log_clearance import lane_offset
            shift = json.loads(clearance_file.read_text())["chosen_cm"]
            if shift is None:
                raise ValueError("No surveyed line cleared the log and supported the pickup")
            self.clearance = lambda track_station: lane_offset(track_station, shift)
        support = u.SystemLibrary.line_trace_single(
            self.world,
            p + u.Vector(0, 0, 250),
            p - u.Vector(0, 0, 650),
            u.TraceTypeQuery.TRACE_TYPE_QUERY1,
            True,
            [self.car],
            u.DrawDebugTrace.NONE,
            True,
        )
        hit = support.to_tuple() if support else ()
        floor = next((v.z for v in hit if isinstance(v, u.Vector)), None)
        self.placement = dict(
            start=start,
            expected_xy_cm=expected_xy,
            position_cm=p.to_tuple(),
            rotation=self.car.get_actor_rotation().to_tuple(),
            up_z=self.car.get_actor_up_vector().z,
            ground_trace_z_cm=floor,
            ground_objects=[
                v.get_path_name() for v in hit if isinstance(v, (u.Actor, u.PrimitiveComponent))
            ],
        )
        (output / "drive-placement.json").write_text(json.dumps(self.placement, indent=2))
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
        self.throttle_limit = 1.0
        drive = self.car.get_drivetrain()
        self.drivetrain = drive
        self.traction = self.car.get_traction()
        drive.set_low_range(True)
        drive.set_diff_lock(True)
        self.car.reset_driving_inputs()
        self.move.set_target_gear(1, True)
        self.move.set_brake_input(0)
        self.move.set_handbrake_input(False)
        # Wake the chassis once after placement. Wheel contacts are recorded throughout.
        self.move.set_sleeping(False)

    def command(self, value):
        u.SystemLibrary.execute_console_command(self.world, value, self.pc)

    def inspect_stall(self):
        location = self.car.get_actor_location()
        forward = self.car.get_actor_forward_vector()
        angle = math.atan2(forward.y, forward.x)
        front = u.Vector(math.cos(angle), math.sin(angle), 0)
        right = u.Vector(-math.sin(angle), math.cos(angle), 0)

        def trace(a, b):
            result = u.SystemLibrary.line_trace_single(
                self.world, a, b, u.TraceTypeQuery.TRACE_TYPE_QUERY1, True,
                [self.car], u.DrawDebugTrace.NONE, True,
            )
            values = result.to_tuple() if result else ()
            if not values or not values[0]:
                return None
            point = next(v for v in values if isinstance(v, u.Vector))
            return dict(
                point_cm=point.to_tuple(),
                objects=[obj.get_path_name() for obj in values if isinstance(obj, (u.Actor, u.PrimitiveComponent))],
                meshes=[obj.static_mesh.get_path_name() for obj in values if isinstance(obj, u.StaticMeshComponent) and obj.static_mesh],
            )

        checks = []
        for lateral in (-110, 0, 110):
            origin = location + right * lateral
            for height in (35, 80):
                start = origin + u.Vector(0, 0, height)
                checks.append(dict(lateral_cm=lateral, height_cm=height, forward_to_cm=950,
                                   hit=trace(start, start + front * 950)))
            for ahead in (0, 300, 600, 950):
                column = origin + front * ahead
                checks.append(dict(lateral_cm=lateral, ahead_cm=ahead,
                                   ground=trace(column + u.Vector(0, 0, 225), column - u.Vector(0, 0, 600))))
        return dict(position_cm=location.to_tuple(), yaw_degrees=math.degrees(angle), visibility_traces=checks)

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
                "slipping_wheels",
                "largest_slip_cm_s",
                "throttle_limit",
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
        if reason == "stalled":
            # Read the obstacles and road heights after the measured driving window.
            try:
                (self.output / "stall-collision.json").write_text(json.dumps(self.inspect_stall(), indent=2))
            except Exception:
                u.log_warning(traceback.format_exc())
        u.log(
            f"GT_LINKED_END reason={reason} travel_m={self.travel:.2f} samples={len(self.samples)}"
        )
        self.command("CsvProfile STOP")

    def tick(self, delta_seconds):
        try:
            now = time.monotonic()
            if now - self.last_input < 0.10:
                return
            input_dt = min(0.3, now - self.last_input)
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
            lateral = self.lane_offset
            track_station = target_station - self.track_start_m
            if self.clearance and 356 <= track_station <= 408:
                lateral = self.clearance(track_station)
            target_x = a[0] + t * dx - dy / length * lateral
            target_y = a[1] + t * dy + dx / length * lateral
            bearing = math.atan2(target_y - pos.y, target_x - pos.x)
            forward = self.car.get_actor_forward_vector()
            angle = math.remainder(bearing - math.atan2(forward.y, forward.x), 2 * math.pi)
            steer = max(-1, min(1, math.degrees(angle) / 20))
            target_speed = max(3.5, (9 if section == "forest_access" else 6) - 3 * abs(steer))
            throttle = max(0, min(1, 0.45 + 0.32 * (target_speed - speed)))
            brake = max(0, min(0.65, (speed - target_speed - 1) * 0.25))
            wheels = [
                u.ChaosWheeledVehicleMovementComponent.break_wheel_status(
                    self.move.get_wheel_state(i)
                )
                for i in range(4)
            ]
            contacts = sum(w[0] for w in wheels)
            slipping = [abs(w[7]) for w in wheels if w[0] and w[6]]
            slip = max(slipping, default=0)
            # The previous driver kept the accelerator floored through sustained
            # wheelspin. Ease the pedal until tyres bite, then feed power back in.
            if len(slipping) >= 2 and slip > 100 and speed < 3:
                self.throttle_limit = max(0.20, self.throttle_limit - input_dt * 0.8)
            else:
                self.throttle_limit = min(1.0, self.throttle_limit + input_dt * 0.35)
            throttle = min(throttle, self.throttle_limit)
            if now < self.reverse_until:
                throttle, brake, steer = 0, min(0.65, self.throttle_limit), -0.45 * steer
            self.car.set_raw_steer(steer)
            self.move.set_throttle_input(throttle)
            self.move.set_brake_input(brake)
            self.move.set_handbrake_input(False)
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
                    len(slipping),
                    round(slip, 1),
                    round(self.throttle_limit, 2),
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
