"""Build an unassigned material candidate for a later controlled comparison.

Import inside the sole Unreal editor, before PIE. Does not launch Unreal,
load/save a map, change any component, or overwrite an existing material.
The source must still match the audited painterly shader. This is a GPU shading
trial, not a claim of reduced VRAM or improved performance. Compile and visual
validation in Unreal remain required before assignment or promotion.
"""
from pathlib import PurePosixPath

import benmore_painterly_surface as paint

SOURCE = '/Game/GrandTour/Demo/BenmoreRoads/Painterly/M_Painterly_Tussock'
TRIAL_ROOT = '/Game/GrandTour/Demo/BenmoreRoads/PerformanceTrials/'


def split_colour_code(code):
    """Keep the root/tip palette in pixel shading; interpolate only coverage."""
    if code != paint.FOLIAGE:
        raise ValueError('Source shader changed; review it before constructing this trial')
    return paint.NOISE + 'return cover;', code[len(paint.NOISE):]


def create_candidate(destination):
    import unreal as u

    path = PurePosixPath(destination)
    if (not destination.startswith(TRIAL_ROOT) or '..' in path.parts
            or '.' in path.name or not path.name.startswith('M_')):
        raise ValueError('Use a new M_ asset beneath PerformanceTrials')
    eal = u.EditorAssetLibrary
    mel = u.MaterialEditingLibrary
    if eal.does_asset_exist(destination):
        raise ValueError('Trial destination already exists; refusing overwrite')
    if u.EditorLevelLibrary.get_game_world():
        raise RuntimeError('Create the candidate before Play mode')
    source = u.load_asset(SOURCE)
    if not source or not isinstance(source, u.Material):
        raise ValueError('Expected the audited base foliage material')

    def colour_node(material):
        matches = [node for node in mel.get_material_expressions(material)
                   if isinstance(node, u.MaterialExpressionCustom)
                   and node.get_editor_property('code') == paint.FOLIAGE]
        if len(matches) != 1:
            raise ValueError('Expected exactly one audited foliage colour node')
        return matches[0]

    # Validate before duplicating; clone preserves all other material settings.
    colour_node(source)
    cover_code, pixel_code = split_colour_code(paint.FOLIAGE)
    candidate = eal.duplicate_asset(SOURCE, destination)
    assert candidate, 'Could not duplicate material'
    colour = colour_node(candidate)
    names = [str(x.get_editor_property('input_name'))
             for x in colour.get_editor_property('inputs')]
    connections = list(mel.get_inputs_for_material_expression(candidate, colour))
    assert names == ['P', 'Base'] and len(connections) == 2 and all(connections)
    position, base = connections

    def inputs(*names):
        values = []
        for name in names:
            value = u.CustomInput()
            value.set_editor_property('input_name', name)
            values.append(value)
        return values

    cover = mel.create_material_expression(candidate, u.MaterialExpressionCustom)
    cover.set_editor_property('inputs', inputs('P'))
    cover.set_editor_property('code', cover_code)
    cover.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT1)
    cover.set_editor_property('desc', 'Broad pigment coverage evaluated per vertex')
    interpolate = mel.create_material_expression(candidate, u.MaterialExpressionVertexInterpolator)
    colour.set_editor_property('inputs', inputs('Base', 'cover'))
    colour.set_editor_property('code', pixel_code)
    # UE 5.8 VertexInterpolator names its input VS (verified in engine source).
    for a, b, pin in [(position, cover, 'P'), (cover, interpolate, 'VS'),
                      (base, colour, 'Base'), (interpolate, colour, 'cover')]:
        assert mel.connect_material_expressions(a, '', b, pin), pin
    mel.recompile_material(candidate)
    # Caller decides whether to save this isolated asset after shader validation.
    # Nothing assigns it to meshes, grass types or landscape materials here.
    return candidate
