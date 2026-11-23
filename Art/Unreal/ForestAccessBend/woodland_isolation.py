"""Attribute foreground plants and moss by toggling actual runtime components at a fixed camera."""

import json
import math
import unreal as u


def inspect_floor(eye, look, ground, root, out, world):
    folder = root / "Saved/WoodlandHabitats"
    if not (folder / "habitat.rgba").is_file():
        return
    field = json.loads((folder / "field.json").read_text())
    data = (folder / "habitat.rgba").read_bytes()
    n = field["size"]
    ox, oy = field["origin"]
    rot = u.MathLibrary.find_look_at_rotation(eye, look)
    f = u.MathLibrary.get_forward_vector(rot)
    r = u.MathLibrary.get_right_vector(rot)
    v = u.MathLibrary.get_up_vector(rot)
    focal = 800 / math.tan(math.radians(73 / 2))
    result = {}
    local = []
    for a in u.GameplayStatics.get_all_actors_of_class(world, u.Actor):
        hit, ext = a.get_actor_bounds(False)
        if abs(hit.x - eye.x) > ext.x + 1300 or abs(hit.y - eye.y) > ext.y + 1300:
            continue
        for c in a.get_components_by_class(u.MeshComponent):
            if isinstance(c, u.InstancedStaticMeshComponent) or not c.visible or c.hidden_in_game:
                continue
            mats = [m.get_path_name() for m in c.get_materials() if m]
            if not mats:
                continue
            local.append([a.get_actor_label(), c.get_name(), mats])
    (out / "nearby-ground-materials.json").write_text(json.dumps(local, indent=2))
    for name, x, y in [
        ("lichen below tree", 576, 590),
        ("lower moss band", 895, 811),
        ("leaf pile", 336, 651),
        ("near stone", 1112, 553),
    ]:
        ray = f + r * ((x - 800) / focal) + v * ((450 - y) / focal)
        for step in range(5, 650):
            p = eye + ray * (step * 5)
            if p.z > ground(p.x, p.y):
                continue
            i = math.floor((p.x - ox) * n / field["span"])
            j = math.floor((p.y - oy) * n / field["span"])
            result[name] = [
                round(p.x),
                round(p.y),
                list(data[(j * n + i) * 4 : (j * n + i) * 4 + 4]),
            ]
            break
    (out / "forest-floor-probes.json").write_text(json.dumps(result))


def isolate(actors, photo, out, eye):
    groups = {}
    for a in actors:
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            if not c.visible or c.hidden_in_game or not c.static_mesh:
                continue
            found = c.get_instances_overlapping_sphere(eye, 2100, True)
            if not found:
                continue
            mesh = c.static_mesh.get_name()
            groups.setdefault(mesh, []).append(c)
    (out / "local-families.json").write_text(
        json.dumps(
            {
                m: [
                    [
                        c.get_owner().get_actor_label(),
                        c.get_name(),
                        [t.get_path_name() if t else None for t in c.get_materials()],
                    ]
                    for c in cc
                ]
                for m, cc in groups.items()
            },
            indent=2,
        )
    )
    for mesh, cc in sorted(groups.items()):
        if "Canopy" in mesh or "Trunk" in mesh:
            continue
        try:
            for c in cc:
                c.set_visibility(False)
            for _ in range(6):
                yield
            yield from photo("without-" + mesh)
        finally:
            for c in cc:
                c.set_visibility(True)
