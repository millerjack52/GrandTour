"""Map-local haze controls, independent of surface lighting and source materials."""
import unreal as u

FIELDS=['fog_density','fog_height_falloff','start_distance','fog_max_opacity',
        'volumetric_fog_extinction_scale','volumetric_fog_scattering_distribution',
        'volumetric_fog_start_distance','volumetric_fog_near_fade_in_distance']

def snapshot(fog,sun):
    result={k:fog.get_editor_property(k) for k in FIELDS}
    c=fog.get_editor_property('fog_inscattering_luminance')
    result['fog_colour']=[c.r,c.g,c.b]
    result['sun_volumetric_scattering']=sun.get_editor_property('volumetric_scattering_intensity')
    return result

def apply(fog,sun,cfg):
    for k in FIELDS:fog.set_editor_property(k,cfg[k])
    fog.set_editor_property('fog_inscattering_luminance',u.LinearColor(*cfg['fog_colour'],1))
    sun.set_editor_property('volumetric_scattering_intensity',cfg['sun_volumetric_scattering'])

restore=apply
