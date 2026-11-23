"""One real pickup path, two broadleaf meshes, identical views and alternating cost samples."""
import json
import math
import shutil
import time

import unreal as u


class BroadleafPair:
    def __init__(self, added, setup):
        self.pilot, = [c for a in added for c in a.get_components_by_class(u.InstancedStaticMeshComponent)
                       if 'ForestAccessPaintedTree' in map(str, c.component_tags)]
        assert self.pilot.get_instance_count() == 1
        self.meshes = [u.load_asset(setup['source']), u.load_asset(setup['mesh'])]
        self.materials = [u.load_asset(setup['old_far']), u.load_asset(setup['far'])]
        assert self.pilot.static_mesh == self.meshes[1] and all(self.materials)
        self.mats = list(self.pilot.get_materials())[:2]
        self.position = self.pilot.get_instance_transform(0, True).translation
        self.mobility = self.pilot.mobility

    def select(self, new):
        c = self.pilot
        if c.static_mesh != self.meshes[new]:
            c.set_mobility(u.ComponentMobility.MOVABLE)
            try:
                assert c.set_static_mesh(self.meshes[new])
                for i, mat in enumerate(self.mats + [self.materials[new]]):
                    c.set_material(i, mat)
            finally:
                c.set_mobility(self.mobility)
        assert c.static_mesh == self.meshes[new] and c.get_material(2) == self.materials[new]


def examine(pair, path, route, ground, camera, pc, cmd, photo, csv_dir, out):
    pc.set_view_target_with_blend(camera,0)
    # Replay a passenger-side look from the pickup's measured XY trajectory.
    # The timed chase run is separate from image readbacks and mesh switches.
    results = []
    aim = pair.position + u.Vector(0,0,310)
    side = math.copysign(1,route.nearest(pair.position.x,pair.position.y)[2])
    for j, requested in enumerate(range(29, 70, 2)):
        station,x,y,_,_ = min(path, key=lambda row: abs(row[0]-requested))
        heading = math.radians(route.at(station)[2])
        x -= 85*side*math.sin(heading)
        y += 85*side*math.cos(heading)
        eye = u.Vector(x,y,ground(x,y)+190)
        rotation = u.MathLibrary.find_look_at_rotation(eye,aim)
        camera.set_actor_location_and_rotation(eye,rotation,False,True)
        for new, label in ((False,'before'),(True,'after')):
            pair.select(new)
            for _ in range(22):
                yield
            yield from photo(f'window-{label}-{j:02d}')
        if j in (4,8,12,16):
            pair.pilot.set_visibility(False)
            try:
                for _ in range(22):
                    yield
                yield from photo(f'window-hidden-{j:02d}')
            finally:
                pair.pilot.set_visibility(True)
        results.append(dict(station=station, eye=eye.to_tuple(), rotation=rotation.to_tuple()))
    (out/'crown-window.json').write_text(json.dumps(results,indent=2))
    # The side-on road view emphasizes the tree, and is repeated in AB, BA, AB order.
    point = min(results,key=lambda row:abs(row['station']-52))
    eye = u.Vector(*point['eye'])
    camera.set_actor_location_and_rotation(eye,u.MathLibrary.find_look_at_rotation(eye,aim),False,True)
    profile = out/'crown-cost'
    profile.mkdir(exist_ok=True)
    for i,new in enumerate((False,True,True,False,False,True)):
        pair.select(new)
        for _ in range(40):
            yield
        previous = set(csv_dir.glob('Profile*.csv*'))
        cmd('csvprofile start')
        for _ in range(128):
            yield
        cmd('csvprofile stop')
        end = time.monotonic()+20
        while time.monotonic()<end:
            available = [p for p in set(csv_dir.glob('Profile*.csv*'))-previous if p.stat().st_size>5000]
            if available:
                break
            yield
        else:
            raise RuntimeError('Broadleaf GPU trace missing')
        for _ in range(8):
            yield
        capture = max(available,key=lambda p:p.stat().st_mtime_ns)
        label = 'after' if new else 'before'
        shutil.copyfile(capture,profile/(f'{i+1}-{label}'+''.join(capture.suffixes)))
    pair.select(True)
