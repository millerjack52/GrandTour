"""Read-only serialized actor inventory used before/after the Benmore FX install."""
import unreal as u

LEVEL = '/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview'

def actors_in(world):
    prefix = world.get_path_name() + ':PersistentLevel.'
    return [a for a in u.ObjectIterator(u.Actor) if a.get_path_name().startswith(prefix)]

def inventory(world):
    rows = []
    for a in actors_in(world):
        if isinstance(a, u.GTVehicleSurfaceEffects): continue
        p, r, s = a.get_actor_location(), a.get_actor_rotation(), a.get_actor_scale3d()
        meshes = []
        for c in a.get_components_by_class(u.MeshComponent):
            materials = [c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]
            mesh = c.get_editor_property('static_mesh') if isinstance(c,u.StaticMeshComponent) else None
            meshes.append([c.get_name(), mesh.get_path_name() if mesh else None, materials])
        rows.append([a.get_name(),a.get_actor_label(),a.get_class().get_path_name(),
                     [round(v,4) for v in (p.x,p.y,p.z,r.pitch,r.yaw,r.roll,s.x,s.y,s.z)],sorted(meshes,key=str)])
    return sorted(rows,key=str)
