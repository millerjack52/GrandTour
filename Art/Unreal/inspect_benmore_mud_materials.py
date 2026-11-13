"""Read-only inventory for integrating the approved scanned mud into Benmore."""
import json
from pathlib import Path
import unreal as u

ROOT=Path(u.Paths.project_dir()).resolve()
OUT=ROOT/'Art/Export/BenmoreMudMaterials';OUT.mkdir(parents=True,exist_ok=True)
LEVEL='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview'
assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(LEVEL)
mel=u.MaterialEditingLibrary
report={'level':LEVEL,'actors':[],'materials':{}}
def vec(v):return [v.x,v.y,v.z]
def material(m):
    if not m or m.get_path_name() in report['materials']:return
    r={'class':m.get_class().get_name()};report['materials'][m.get_path_name()]=r
    if not isinstance(m,u.Material):return
    r['tangent_space_normal']=m.get_editor_property('tangent_space_normal')
    r['nodes']=[]
    for e in mel.get_material_expressions(m):
        d={'name':e.get_name(),'class':e.get_class().get_name(),'desc':e.get_editor_property('desc')}
        if isinstance(e,u.MaterialExpressionCustom):
            d['code']=e.get_editor_property('code')
            d['inputs']=[str(v.get_editor_property('input_name')) for v in e.get_editor_property('inputs')]
            d['sources']=[n.get_name() if n else None for n in mel.get_inputs_for_material_expression(m,e)]
        if isinstance(e,(u.MaterialExpressionTextureSample,u.MaterialExpressionTextureObject,u.MaterialExpressionTextureObjectParameter)):
            t=e.get_editor_property('texture');d['texture']=t.get_path_name() if t else None
        r['nodes'].append(d)
    r['outputs']={}
    for name in ['MP_BASE_COLOR','MP_NORMAL','MP_ROUGHNESS','MP_SPECULAR','MP_AMBIENT_OCCLUSION']:
        prop=getattr(u.MaterialProperty,name);n=mel.get_material_property_input_node(m,prop)
        r['outputs'][name]=[n.get_name() if n else None,mel.get_material_property_input_node_output_name(m,prop)]
for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
    d={'label':a.get_actor_label(),'class':a.get_class().get_name(),'location':vec(a.get_actor_location()),'scale':vec(a.get_actor_scale3d())}
    if isinstance(a,u.LandscapeProxy):
        m=a.get_editor_property('landscape_material');d['material']=m.get_path_name();material(m)
        d['nanite']=a.get_editor_property('enable_nanite')
    if isinstance(a,u.CameraActor):
        rot=a.get_actor_rotation();d['rotation']=[rot.pitch,rot.yaw,rot.roll]
    comps=a.get_components_by_class(u.InstancedStaticMeshComponent)
    if comps:
        d['instances']=[]
        for c in comps:
            mesh=c.get_editor_property('static_mesh')
            d['instances'].append({'mesh':mesh.get_path_name() if mesh else None,'count':c.get_instance_count(),
                'materials':[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]})
    report['actors'].append(d)
(OUT/'inventory.json').write_text(json.dumps(report,indent=2))
u.SystemLibrary.quit_editor()
