"""Read-only content audit. No timing, profiling or driving measurements."""
import unreal as u
import json, traceback
from pathlib import Path

ROOT=Path(u.Paths.project_dir()).resolve()
OUT=ROOT/'Art/Export/BenmoreGaea/RiverScale';OUT.mkdir(parents=True,exist_ok=True)
LEVEL='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview'
report={'ok':False,'level':LEVEL,'timings_collected':False,'actors':[],'meshes':{},'materials':{},'grass':{}}

def prop(o,key):
    try:
        value=o.get_editor_property(key)
        if hasattr(value,'get_path_name'):return value.get_path_name()
        if hasattr(value,'to_tuple'):return list(value.to_tuple())
        if isinstance(value,(bool,int,float,str)) or value is None:return value
        return str(value)
    except Exception:return None

def material(m):
    if not m or m.get_path_name() in report['materials']:return
    name=m.get_path_name();row={'class':m.get_class().get_name()};report['materials'][name]=row
    if not isinstance(m,u.Material):
        parent=m.get_editor_property('parent');row['parent']=parent.get_path_name() if parent else None;material(parent);return
    nodes=list(u.MaterialEditingLibrary.get_material_expressions(m))
    row.update(nodes=len(nodes),shading_model=prop(m,'shading_model'),blend_mode=prop(m,'blend_mode'),custom=[])
    for n in nodes:
        if isinstance(n,u.MaterialExpressionCustom):row['custom'].append({'desc':prop(n,'desc'),'code':prop(n,'code'),'inputs':[str(v.get_editor_property('input_name')) for v in n.get_editor_property('inputs')]})
        if isinstance(n,u.MaterialExpressionLandscapeGrassOutput):
            row['grass_types']=[]
            for g in n.get_editor_property('grass_types'):
                gt=g.get_editor_property('grass_type')
                if not gt:continue
                key=gt.get_path_name();row['grass_types'].append(key);report['grass'][key]=[]
                for v in gt.get_editor_property('grass_varieties'):
                    report['grass'][key].append({k:prop(v,k) for k in ['grass_mesh','grass_density','start_cull_distance','end_cull_distance','cast_dynamic_shadow','cast_contact_shadow','affect_distance_field_lighting','min_lod','instance_world_position_offset_disable_distance','override_materials']})
                    mesh(v.get_editor_property('grass_mesh'))

def mesh(m):
    if not m or m.get_path_name() in report['meshes']:return
    key=m.get_path_name();report['meshes'][key]={};row=report['meshes'][key]
    row['lod_count']=m.get_num_lods();row['triangles']=[]
    for i in range(m.get_num_lods()):
        d=m.get_static_mesh_description(i);row['triangles'].append(d.get_triangle_count() if d else None)
    row['nanite']=str(m.get_editor_property('nanite_settings'))
    for slot in m.static_materials:material(slot.material_interface)

try:
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(LEVEL)
    actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    report['water_sheet_count']=sum(isinstance(a,u.GTWaterSheet) for a in actors)
    for a in actors:
        row={'name':a.get_actor_label(),'class':a.get_class().get_name(),'components':[]}
        if isinstance(a,u.LandscapeProxy):material(a.landscape_material)
        for c in a.get_components_by_class(u.StaticMeshComponent):
            m=c.static_mesh
            if not m:continue
            mesh(m);entry={'mesh':m.get_path_name(),'instances':c.get_instance_count() if isinstance(c,u.InstancedStaticMeshComponent) else 1}
            for key in ['cast_shadow','affect_distance_field_lighting','visible_in_ray_tracing','ld_max_draw_distance','instance_start_cull_distance','instance_end_cull_distance','world_position_offset_disable_distance','bounds_scale']:
                entry[key]=prop(c,key)
            entry['materials']=[]
            for i in range(c.get_num_materials()):
                mat=c.get_material(i);material(mat);entry['materials'].append(mat.get_path_name() if mat else None)
            row['components'].append(entry)
        if row['components'] or isinstance(a,(u.LandscapeProxy,u.GTWaterSheet)):report['actors'].append(row)
    report['ok']=True
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'content-audit.json').write_text(json.dumps(report,indent=2))
u.log('BENMORE_RENDER_AUDIT '+str(report['ok']))
