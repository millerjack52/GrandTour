"""Map-local grounding: broadleaf cast shadows and short fine-foliage contact shadows."""
import unreal as u
import json
from pathlib import Path
O=Path('C:/GrandTour/Art/Export/FloraDrive')
DEFAULTS=dict(contact_length_cm=60.,contact_casting_intensity=1.,contact_noncasting_intensity=.65,broadleaf_dynamic_shadows=True)

def apply():
    file=O/'ground-shadow-settings.json'
    if not file.exists():file.write_text(json.dumps(DEFAULTS,indent=2))
    cfg=json.loads(file.read_text());actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    report=dict(settings=cfg,components=[],sun={},tree_positions=[])
    sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    for a in actors:
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            mesh=c.static_mesh
            if not mesh or not mesh.get_name().startswith('SM_Path_FP_'):continue
            name=mesh.get_name()
            if 'Tree' in name:
                for i in range(c.get_instance_count()):report['tree_positions'].append(c.get_instance_transform(i,True).translation.to_tuple())
            if not any(k in name for k in ['Small_Plants','Grass','Flower','Ferns','Shrubbery']):continue
            row=dict(mesh=name,instances=c.get_instance_count(),before_cast_shadow=c.get_editor_property('cast_shadow'))
            c.modify();c.set_editor_property('cast_contact_shadow',True)
            if 'Small_Plants' in name and cfg['broadleaf_dynamic_shadows']:
                c.set_cast_shadow(True);c.set_editor_property('cast_dynamic_shadow',True);c.set_editor_property('cast_shadow_as_two_sided',True)
                assert all(sm.is_section_cast_shadow_enabled(mesh,lod,section) for lod in range(sm.get_lod_count(mesh)) for section in range(mesh.get_num_sections(lod))),name
            row.update(cast_shadow=c.get_editor_property('cast_shadow'),cast_contact_shadow=c.get_editor_property('cast_contact_shadow'))
            report['components'].append(row)
    for a in actors:
        if isinstance(a,u.DirectionalLight) and a.get_actor_label()=='FloraDrive_Sun':
            c=a.light_component;c.modify()
            for key,val in [('ContactShadowLength',cfg['contact_length_cm']),('ContactShadowLengthInWS',True),('ContactShadowCastingIntensity',cfg['contact_casting_intensity']),('ContactShadowNonCastingIntensity',cfg['contact_noncasting_intensity'])]:
                c.set_editor_property(key,val);report['sun'][key]=c.get_editor_property(key)
    assert report['sun'] and report['components']
    report['new_dynamic_shadow_instances']=sum(r['instances'] for r in report['components'] if r['cast_shadow'] and not r['before_cast_shadow'])
    report['broadleaf_shadow_instances']=sum(r['instances'] for r in report['components'] if 'Small_Plants' in r['mesh'] and r['cast_shadow'])
    return report
