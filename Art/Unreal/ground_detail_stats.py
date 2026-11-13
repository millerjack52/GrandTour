"""Ground relief GR2 phase B item 4 (docs/GROUND_RELIEF_PLAN.md GR2): the strips' landscape materials' static shader counts - today's
(GT_GD_TAG=baseline, before phase B touched them), and after: each parent with GroundDetail off (its own default) and its
MI_GT_Landscape_Strips with it on - MaterialEditingLibrary.get_statistics, the compiler's static counts at the editor's shader platform
(a branch's or a loop's body counts once; not timing). The baseline run also dumps each graph's outputs and layer-blend pins, which
phase B's material script reads. A landscape material's static counts compile its layer blends at their preview weights (the
Dirt row's 1 here), so the Scrub row - where M_VariantsLandscape / M_LiveLandscape take the detail - is left out of them (a Scrub
preview weight of 1, or the Dirt row fed the Scrub row's input, did not change them either: the counted shader holds no layer row);
the after run also counts a probe copy of each whose three blends are bypassed by the Scrub row's input (the GroundDetail switch
straight into the weather call's BaseColor, the roughness mask and the normal's normalise; GroundDetail/Probe/, off and on), so the
row's path, off and on, is in the counted shader. Run with -RenderOffScreen (a NullRHI run compiles no HLSL): & Art/ground_detail_gr2.ps1 -Step stats.
Writes Art/Export/GroundDetailGR2/shader-stats-<tag>.json."""
import json
import os
import traceback
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
OUT = ROOT / 'Art/Export/GroundDetailGR2'
TAG = os.environ.get('GT_GD_TAG', 'after')
STRIPS = [('L_MudVariants', '/Game/GrandTour/ArtTests/MudVariants/M_VariantsLandscape'),
          ('L_MudDrive', '/Game/GrandTour/ArtTests/LiveMudDrive/M_LiveLandscape'),
          ('L_GravelDeform', '/Game/GrandTour/ArtTests/DeformableGravel/M_GravelLandscape')]
OTHERS = [('The Hide and the legs', '/Game/GrandTour/Materials/M_GT_Landscape'), ('ground scatter', '/Game/GrandTour/ArtTests/GroundDetail/M_GT_GroundScatter')]
mel = u.MaterialEditingLibrary
eal = u.EditorAssetLibrary
report = dict(ok=False, tag=TAG, rows=[], graphs={})
PROPS = ['MP_BASE_COLOR', 'MP_NORMAL', 'MP_ROUGHNESS', 'MP_AMBIENT_OCCLUSION', 'MP_OPACITY_MASK', 'MP_SPECULAR', 'MP_METALLIC']


def stats(role, path, switch=None):
    mat = eal.load_asset(path)
    if mat is None:
        return dict(role=role, material=path, missing=True)
    s = mel.get_statistics(mat)
    row = dict(role=role, material=path, ground_detail=switch, pixel_instructions=s.num_pixel_shader_instructions,
               vertex_instructions=s.num_vertex_shader_instructions, samplers=s.num_samplers,
               pixel_texture_samples=s.num_pixel_texture_samples, vertex_texture_samples=s.num_vertex_texture_samples,
               interpolator_scalars=s.num_interpolator_scalars)
    u.log('GD_SHADER_STATS %s' % json.dumps(row))
    return row


def scrub_probe(level, path):
    """A copy of a strip's landscape material whose colour, roughness and normal blends feed the Dirt row (preview weight 1) the
    Scrub row's input (the GroundDetail switch), counted with GroundDetail off (the copy) and on (an MI of it)."""
    name = path.rsplit('/', 1)[1]
    probe = '/Game/GrandTour/ArtTests/GroundDetail/Probe/' + name + '_ScrubPreview'
    if eal.does_asset_exist(probe):
        eal.delete_asset(probe)
    m = eal.duplicate_asset(path, probe)
    exprs = list(mel.get_material_expressions(m))
    by_desc = {str(e.get_editor_property('desc')): e for e in exprs}
    for blend, (target, pin) in [('Landscape:colour', ('Weather:call', 'BaseColor')), ('Landscape:roughness', ('Landscape:roughmask', '')),
                                 ('Landscape:normal', ('Landscape:normalsafe', 'N'))]:
        e = by_desc[blend]
        names = [str(n) for n in mel.get_material_expression_input_names(e)]
        src = dict(zip(names, list(mel.get_inputs_for_material_expression(m, e))))['Layer Scrub']
        assert isinstance(src, u.MaterialExpressionStaticSwitchParameter), 'the Scrub row is not the GroundDetail switch'
        assert mel.connect_material_expressions(src, '', by_desc[target], pin), blend

    mel.recompile_material(m)
    eal.save_loaded_asset(m)
    rows = [stats(level + ' (the Scrub row bypassing the blends)', probe, 'off (probe copy)')]
    mi_path = probe + '_On'
    mi = eal.load_asset(mi_path) or u.AssetToolsHelpers.get_asset_tools().create_asset(mi_path.rsplit('/', 1)[1], probe.rsplit('/', 1)[0],
                                                                                        u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mi, m)
    mel.set_material_instance_static_switch_parameter_value(mi, 'GroundDetail', True)
    mel.update_material_instance(mi)
    eal.save_loaded_asset(mi)
    rows.append(stats(level + ' (the Scrub row bypassing the blends)', mi_path, 'on (probe MI)'))
    return rows


def label(e):
    if e is None:
        return None
    d = ''
    for k in ('desc', 'parameter_name'):
        try:
            v = str(e.get_editor_property(k))
            if v and v != 'None':
                d += '%s=%s ' % (k, v)
        except Exception:
            pass
    return '%s %s(%s)' % (e.get_class().get_name(), d, e.get_name())


def graph(path):
    mat = eal.load_asset(path)
    if mat is None:
        return None
    out = dict(tangent_space_normal=bool(mat.get_editor_property('tangent_space_normal')), outputs={}, blends={}, customs={})
    for name in PROPS:
        prop = getattr(u.MaterialProperty, name)
        node = mel.get_material_property_input_node(mat, prop)
        out['outputs'][name] = None if node is None else [label(node), str(mel.get_material_property_input_node_output_name(mat, prop))]
    for e in mel.get_material_expressions(mat):
        if isinstance(e, u.MaterialExpressionLandscapeLayerBlend):
            names = [str(n) for n in mel.get_material_expression_input_names(e)]
            srcs = list(mel.get_inputs_for_material_expression(mat, e))
            pins = {}
            for n, s in zip(names, srcs):
                o = None
                try:
                    o = str(mel.get_input_node_output_name_for_material_expression(e, n))
                except Exception as error:
                    o = 'n/a (%s)' % type(error).__name__
                pins[n] = None if s is None else [label(s), o]
            out['blends'][label(e)] = pins
        elif isinstance(e, u.MaterialExpressionCustom):
            out['customs'][label(e)] = dict(inputs=[str(i.get_editor_property('input_name')) for i in e.get_editor_property('inputs')],
                                            outputs=[str(o.get_editor_property('output_name')) for o in e.get_editor_property('additional_outputs')],
                                            code_chars=len(str(e.get_editor_property('code'))))
    out['expressions'] = len(mel.get_material_expressions(mat))
    return out


try:
    for level, path in STRIPS:
        report['rows'].append(stats(level, path, 'off (the parent)' if TAG != 'baseline' else 'today'))
        mi = path.rsplit('/', 1)[0] + '/MI_GT_Landscape_Strips'
        if TAG != 'baseline' and eal.does_asset_exist(mi):
            report['rows'].append(stats(level, mi, 'on (MI_GT_Landscape_Strips)'))
            if 'Gravel' not in path:
                report['rows'] += scrub_probe(level, path)
        if TAG == 'baseline':
            report['graphs'][path] = graph(path)
    for role, path in OTHERS:
        if eal.does_asset_exist(path):
            report['rows'].append(stats(role, path))
    mpc = eal.load_asset('/Game/GrandTour/Terrain/MPC_TrackPaint')
    report['mpc_track_paint'] = dict(scalars=[str(p.get_editor_property('parameter_name')) for p in mpc.get_editor_property('scalar_parameters')],
                                     vectors=len(mpc.get_editor_property('vector_parameters')))
    report['ok'] = True
except Exception:
    report['error'] = traceback.format_exc()
    u.log_error(report['error'])
finally:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / ('shader-stats-%s.json' % TAG)).write_text(json.dumps(report, indent=2))
    u.SystemLibrary.quit_editor()
