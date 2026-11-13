"""Directional daylight for the accepted tussock style test."""
import unreal as u

def configure(world):
    result={'sun':[],'sky':[],'shadow_components':0}
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.DirectionalLight):
        actor.set_actor_rotation(u.Rotator(pitch=-27,yaw=-58),False)
        light=actor.get_component_by_class(u.DirectionalLightComponent)
        light.set_intensity(10.5)
        light.set_editor_property('light_source_angle',1.5)
        light.set_editor_property('use_temperature',True)
        light.set_temperature(5800)
        result['sun'].append(dict(intensity=10.5,pitch=-27,yaw=-58,source_angle=1.5))
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.SkyLight):
        light=actor.get_component_by_class(u.SkyLightComponent);light.set_intensity(.65)
        result['sky'].append(dict(intensity=.65))
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
        if actor.get_actor_label()!='TS_ApprovedTussock':continue
        for component in actor.get_components_by_class(u.InstancedStaticMeshComponent):
            mesh=component.get_editor_property('static_mesh')
            cast=bool(mesh and mesh.get_name()!='SM_TS_Fine')
            component.set_cast_shadow(cast)
            if cast:result['shadow_components']+=1
    return result
