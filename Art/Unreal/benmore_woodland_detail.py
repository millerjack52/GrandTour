"""Remove the retired scanned-soil override and restore recovered mud outputs.

Original inputs survive in passthrough nodes. Install/Repair also call this,
so the unwanted appearance cannot return. No physics or relief changes.
"""
import unreal as u
import benmore_woodland_materials as mat

TAG = 'WoodlandSoilDetail'
mel = u.MaterialEditingLibrary
SLOTS = [('Color', u.MaterialProperty.MP_BASE_COLOR),
         ('Normal', u.MaterialProperty.MP_NORMAL),
         ('Rough', u.MaterialProperty.MP_ROUGHNESS),
         ('Specular', u.MaterialProperty.MP_SPECULAR),
         ('AO', u.MaterialProperty.MP_AMBIENT_OCCLUSION)]


def restore(m):
    assert m
    nodes = list(mel.get_material_expressions(m))
    wrappers = [n for n in nodes if str(n.get_editor_property('desc')) == TAG]
    markers = {key: next((n for n in nodes if
               str(n.get_editor_property('desc')) == TAG + 'Source:' + key), None)
               for key, _ in SLOTS}
    if wrappers or any(markers.values()):
        assert all(markers.values()), 'Incomplete saved native material inputs'
        for key, prop in SLOTS:
            source = markers[key]
            assert str(source.get_editor_property('code')).strip() == 'return Value;'
            assert any(mel.get_inputs_for_material_expression(m, source)), key
            assert mel.connect_material_property(source, '', prop)
        for node in wrappers:
            mel.delete_material_expression(m, node)
        mat.save(m)
        for key, prop in SLOTS:
            assert mel.get_material_property_input_node(m, prop) == markers[key]
    assert not any(str(n.get_editor_property('desc')) == TAG
                   for n in mel.get_material_expressions(m))
    return dict(material=m.get_path_name(), removed_nodes=len(wrappers),
                restored_outputs=[key for key, _ in SLOTS if markers[key]],
                scanned_soil_override=False)


def install():
    return [restore(u.load_asset(mat.BASE + '/M_' + name))
            for name in ['Terrain', 'Detail']]
