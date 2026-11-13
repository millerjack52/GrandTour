"""Unpaused vehicle-drive capture support. Route suitability is checked at runtime.

Uses real vehicle controls and existing physics. Placement happens before the
capture; no screenshot, forced velocity, teleport, or paused frame occurs inside
the measurement. The simple 10 Hz driver is included in the measured CPU cost.
"""
import json
import math
import time


class Driver:
    def __init__(self, world, pc, root):
        import unreal as u
        self.world, self.pc = world, pc
        cars = list(u.GameplayStatics.get_all_actors_of_class(world, u.GTCarPawn))
        if not cars:
            raise RuntimeError('No real vehicle for driving measurement')
        possessed = u.GameplayStatics.get_player_pawn(world, 0)
        self.car = possessed if isinstance(possessed, u.GTCarPawn) else sorted(cars, key=lambda c: c.get_path_name())[0]
        pc.possess(self.car)
        self.car.disable_input(pc)
        self.car.reset_driving_inputs()
        self.move = self.car.get_chaos_movement()
        self.body = self.car.get_component_by_class(u.SkeletalMeshComponent)
        self.ignore = [a for a in u.GameplayStatics.get_all_actors_of_class(world, u.Actor)
                       if not isinstance(a, u.LandscapeProxy)]
        road = json.loads((root/'Art/Export/BenmoreRoads/road-manifest.json').read_text())
        crossing = json.loads((root/'Art/Export/BenmoreGaea/GaeaCreek/crossings.json').read_text())[0]
        cx, cy, _ = crossing['center_m']
        dx, dy = crossing['cross_direction']
        self.routes = {
            'Vegetation': [(p['x_m'], p['y_m']) for p in road['routes'][0]['points'] if 25 <= p['arc_m'] <= 750],
            # Westward from the authored panoramic viewpoint, overlooking the
            # valley. Runtime contacts/corridor checks still validate the route.
            'Long_Vista': [(float(x),500.) for x in range(750,100,-2)],
            'Ford': [(cx+dx*s, cy+dy*s) for s in range(-12, 250, 2)],
            'Lake_Mouth': [(-1160., float(y)) for y in range(-200, 250, 2)],
        }
        self.active = False

    def place(self, name):
        import unreal as u
        self.stop()
        self.name = name
        self.points = self.routes[name]
        self.index = 0
        x, y = self.points[0]
        end_x, end_y = self.points[1]
        hit = u.SystemLibrary.line_trace_single(self.world, u.Vector(x*100, y*100, 100000),
            u.Vector(x*100, y*100, -10000), u.TraceTypeQuery.TRACE_TYPE_QUERY1,
            True, self.ignore, u.DrawDebugTrace.NONE, True)
        if not hit:
            raise RuntimeError('Drive placement missed landscape: ' + name)
        z = next(v.z for v in hit.to_tuple() if isinstance(v, u.Vector))
        self.car.reset_driving_inputs()
        self.move.reset_vehicle()
        self.move.set_target_gear(1, True)
        self.move.set_brake_input(1)
        self.move.set_handbrake_input(True)
        self.car.set_actor_location_and_rotation(u.Vector(x*100, y*100, z+150),
            u.Rotator(yaw=math.degrees(math.atan2(end_y-y, end_x-x))), False, True)
        self.body.set_physics_linear_velocity(u.Vector())
        self.body.set_physics_angular_velocity_in_degrees(u.Vector())
        self.car.set_chase_camera(True)
        self.pc.set_view_target_with_blend(self.car, 0)
        return {'car': self.car.get_path_name(), 'path_m': self.points,
                'camera': 'vehicle chase', 'target_speed_mps': 3 if name in ('Ford','Lake_Mouth') else 6,
                'note': 'Scripted route; runtime motion/corridor checks and visual route review required.'}

    def begin(self):
        import unreal as u
        contacts = [bool(u.ChaosWheeledVehicleMovementComponent.break_wheel_status(self.move.get_wheel_state(i))[0])
                    for i in range(4)]
        if sum(contacts) < 3:
            raise RuntimeError('Drive car did not settle on its wheels')
        self.move.set_target_gear(1, True)
        self.move.set_handbrake_input(False)
        self.move.set_brake_input(0)
        self.active = True
        self.started = time.monotonic()
        self.stopped_since = None
        self.samples = []
        self.distance = 0.
        self.previous = self.car.get_actor_location()
        self.next_sample = 0.

    def step(self):
        import unreal as u
        if not self.active:
            return
        p = self.car.get_actor_location()
        speed = self.car.get_velocity().length()*.01
        elapsed = time.monotonic()-self.started
        self.distance += (p-self.previous).length()*.01
        self.previous = p
        if abs(self.car.get_actor_rotation().roll) > 40:
            raise RuntimeError('Drive car rolled; this is not a valid performance route')
        indices = range(max(0,self.index-3), min(len(self.points),self.index+25))
        self.index = min(indices, key=lambda i: (self.points[i][0]-p.x*.01)**2+(self.points[i][1]-p.y*.01)**2)
        lateral = math.hypot(self.points[self.index][0]-p.x*.01,self.points[self.index][1]-p.y*.01)
        if lateral > 12:
            raise RuntimeError('Drive left the route corridor')
        if self.index >= len(self.points)-5:
            raise RuntimeError('Drive exhausted the route before capture completed')
        ahead = self.points[min(len(self.points)-1,self.index+max(4,int(speed*.7)))]
        wanted = math.atan2(ahead[1]-p.y*.01,ahead[0]-p.x*.01)
        delta = (wanted-math.radians(self.car.get_actor_rotation().yaw)+math.pi)%(2*math.pi)-math.pi
        steer = math.atan2(2*2.6*math.sin(delta),max(8.,speed*1.2))/math.radians(33)
        self.car.set_raw_steer(max(-.8,min(.8,steer)))
        target = 3 if self.name in ('Ford','Lake_Mouth') else 6
        self.move.set_throttle_input(max(0,min(.75,(target-speed)*.25+.20)))
        self.move.set_brake_input(max(0,min(.65,(speed-target-.6)*.25)))
        now = time.monotonic()
        if speed < .1 and elapsed > 5:
            self.stopped_since = self.stopped_since or now
        else:
            self.stopped_since = None
        if self.stopped_since and now-self.stopped_since > 8:
            raise RuntimeError('Drive stalled; no handling parameters will be changed to pass')
        if elapsed >= self.next_sample:
            self.samples.append({'elapsed_s':elapsed,'position_cm':list(p.to_tuple()),'speed_mps':speed,
                'distance_m':self.distance,'corridor_error_m':lateral,
                'water_particles':self.car.get_spray().get_live_count(u.GTSprayKind.WATER),
                'bow_rate':self.car.get_spray().get_bow_rate_now(),
                'splash_rate':self.car.get_spray().get_splash_rate_now(),
                'fine_live':[self.car.get_spray().get_fine_live_count(e) for e in range(3)],
                'fine_rates':[[self.car.get_spray().get_fine_rate(w,e) for e in range(3)] for w in range(4)]})
            self.next_sample = elapsed+1

    def stop(self):
        self.active = False
        self.move.set_throttle_input(0)
        self.move.set_brake_input(1)
        self.move.set_handbrake_input(True)
        self.car.set_raw_steer(0)
