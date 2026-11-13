"""Read the actual map lighting rather than inferring it from old authoring scripts."""
import unreal as u

def read(o,names):
    out={}
    for key in names:
        try:
            value=o.get_editor_property(key)
            out[key]=value if isinstance(value,(float,int,bool,str)) else str(value)
        except Exception:pass
    return out

def snapshot(actors):
    result=[]
    for a in actors:
        item={'label':a.get_actor_label(),'class':a.get_class().get_name()}
        if isinstance(a,u.SkyLight):
            item['properties']=read(a.get_component_by_class(u.SkyLightComponent),['intensity','source_type','real_time_capture','cubemap','lower_hemisphere_is_black','lower_hemisphere_color','cloud_ambient_occlusion','cloud_ambient_occlusion_strength','occlusion_max_distance','occlusion_exponent','min_occlusion','indirect_lighting_intensity','affect_global_illumination','light_color'])
        elif isinstance(a,u.DirectionalLight):
            item['properties']=read(a.light_component,['intensity','light_source_angle','indirect_lighting_intensity','cast_cloud_shadows','cloud_shadow_strength','cloud_shadow_on_surface_strength','dynamic_shadow_distance_movable_light','far_shadow_distance','far_shadow_cascade_count','shadow_distance_fadeout_fraction','shadow_amount','contact_shadow_length'])
        elif isinstance(a,u.PostProcessVolume):
            item.update(read(a,['enabled','priority','blend_weight','unbound']))
            s=a.get_editor_property('settings')
            keys=['auto_exposure_min_brightness','auto_exposure_max_brightness','auto_exposure_bias','color_contrast','color_gain_shadows','color_offset_shadows','local_exposure_shadow_contrast_scale','local_exposure_highlight_contrast_scale','ambient_occlusion_intensity','ambient_occlusion_radius','dynamic_global_illumination_method','lumen_scene_lighting_quality','lumen_final_gather_quality','indirect_lighting_intensity']
            item['properties']=read(s,keys+['override_'+k for k in keys])
        else:continue
        result.append(item)
    return result
