"""Build the forest-access broadleaf from its own painted cards and bark."""
import math
from collections import defaultdict
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
BASE = '/Game/GrandTour/ArtTests/LidarStudy'
FOLDER = BASE + '/ForestAccessBend'
ORIGINAL = BASE + '/FloraWorld/Canopy/SM_Canopy_1'
VARIANT = FOLDER + '/SM_BendBroadleafTufts'
VERSION = '2'
assets = u.EditorAssetLibrary
sm = u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
geo = u.GeometryScript_AssetUtils
lists = u.GeometryScript_List


def target(actors):
    items = [c for a in actors if a.get_actor_label() == 'LidarStudy_ForestAccessBend_v1'
             for c in a.get_components_by_class(u.InstancedStaticMeshComponent)
             if 'ForestAccessPaintedTree' in map(str, c.component_tags)]
    assert len(items) == 1 and items[0].get_instance_count() == 1
    return items[0]


def leaf_islands(mesh):
    _, positions, holes = mesh.get_all_vertex_positions(False)
    assert not holes
    positions = [p.to_tuple() for p in lists.convert_vector_list_to_array(positions)]
    _, triangles, holes = mesh.get_all_triangle_indices(False)
    assert not holes
    get_ids = next(name for name in dir(u.GeometryScript_Materials)
                   if name.replace('_', '') == 'getalltrianglematerialids')
    _, ids, valid = getattr(u.GeometryScript_Materials, get_ids)(mesh)
    assert valid
    triangles = lists.convert_triangle_list_to_array(triangles)
    ids = lists.convert_index_list_to_array(ids)
    assert set(ids) == {0, 1} and len(triangles) == len(ids)
    parents = {}
    def root(i):
        while i != parents[i]:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i
    bark = set()
    for tri, slot in zip(triangles, ids):
        vertices = (tri.x, tri.y, tri.z)
        if slot == 0:
            bark.update(vertices)
            continue
        for i in vertices:
            parents.setdefault(i, i)
        a, b, c = map(root, vertices)
        parents[b] = a
        parents[c] = a
    islands = defaultdict(list)
    for i in parents:
        islands[root(i)].append(i)
    assert not bark.intersection(parents), 'A bark vertex belongs to a leaf island'
    return positions, list(islands.values()), [positions[i] for i in sorted(bark)]


def centre(points):
    return tuple(sum(v) / len(points) for v in zip(*points))


def separation(p, q):
    return (p[0]-q[0])**2 + (p[1]-q[1])**2 + 1.65*(p[2]-q[2])**2


def branch_groups(cards, bark):
    # Start at the uppermost fan and spread seeds across the actual leaf distribution.
    anchors = [max(cards, key=lambda p: p[2])]
    nearest = [separation(p, anchors[0]) for p in cards]
    for _ in range(11):
        anchors.append(cards[max(range(len(cards)), key=nearest.__getitem__)])
        nearest = [min(d, separation(p, anchors[-1])) for d, p in zip(nearest, cards)]
    for _ in range(9):
        groups = [[] for _ in anchors]
        for p in cards:
            groups[min(range(len(anchors)), key=lambda k: separation(p, anchors[k]))].append(p)
        anchors = [centre(group) if group else old for group, old in zip(groups, anchors)]
    # Seat each fan near an existing woody branch without pulling its tips into the trunk.
    return [tuple(.83*v + .17*w for v, w in zip(a, min(bark, key=lambda p: separation(a, p))))
            for a in anchors]


def regroup(mesh, anchors):
    points, islands, bark = leaf_islands(mesh)
    card_centres = [centre([points[i] for i in island]) for island in islands]
    if anchors is None:
        anchors = branch_groups(card_centres, bark)
    z_min = min(a[2] for a in anchors)
    z_range = max(a[2] for a in anchors) - z_min
    centre_x, centre_y, _ = centre(anchors)
    for island, p in zip(islands, card_centres):
        anchor = min(anchors, key=lambda a: separation(a, p))
        dx,dy,dz = (v-a for v,a in zip(p,anchor))
        ax,ay = anchor[0]-centre_x, anchor[1]-centre_y
        length = max(.01,math.hypot(ax,ay))
        ax,ay = ax/length,ay/length
        along = dx*ax + dy*ay
        top = (anchor[2]-z_min)/z_range
        # Keep projecting tips and overlap across the upper crown. Side-facing
        # fans still gather around their branch, with a different pitch per bough.
        along_weight = .22-.11*top
        across_weight = .47-.11*top
        pitch = .11+.27*math.sin(3*math.atan2(ay,ax)+2*top)
        shift = (-(across_weight*(dx-along*ax) + along_weight*along*ax),
                 -(across_weight*(dy-along*ay) + along_weight*along*ay),
                 -(.60-.34*top)*(dz-pitch*along))
        for i in island:
            q = points[i]
            points[i] = tuple(c + d + stretch*(v-c) for c, d, stretch, v in
                              zip(p, shift, (.98, .98, .94), q))
    mesh.set_all_mesh_vertex_positions(lists.convert_array_to_vector_list([u.Vector(*p) for p in points]))
    return anchors, len(islands)


def make_geometry(source):
    tree = u.load_asset(VARIANT) if assets.does_asset_exist(VARIANT) else assets.duplicate_asset(ORIGINAL, VARIANT)
    assert tree and tree != source and sm.get_lod_count(tree) == 4
    anchors = None
    cards = []
    for lod in range(3):
        read = u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.RENDER_DATA, lod_index=lod)
        dynamic, result = geo.copy_mesh_from_static_mesh_v2(source, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), read, False)
        assert result == u.GeometryScriptOutcomePins.SUCCESS
        anchors, count = regroup(dynamic, anchors)
        options = u.GeometryScriptCopyMeshToAssetOptions()
        options.set_editor_property('emit_transaction', False)
        _, result = geo.copy_mesh_to_static_mesh(dynamic, tree, options, u.GeometryScriptMeshWriteLOD(lod_index=lod), False)
        assert result == u.GeometryScriptOutcomePins.SUCCESS
        cards.append(count)
    # Explicit render LODs already embody the source reductions.
    for lod in range(3):
        reduction = sm.get_lod_reduction_settings(tree, lod)
        reduction.percent_triangles = 1.
        reduction.percent_vertices = 1.
        reduction.base_lod_model = lod
        sm.set_lod_reduction_settings(tree, lod, reduction)
    tree.set_editor_property('static_materials', source.static_materials)
    assert sm.set_lod_screen_sizes(tree, list(sm.get_lod_screen_sizes(source)))
    for lod in range(4):
        assert tree.get_num_triangles(lod) == source.get_num_triangles(lod), (lod, tree.get_num_triangles(lod), source.get_num_triangles(lod))
        assert tree.get_num_sections(lod) == source.get_num_sections(lod)
        for section in range(source.get_num_sections(lod)):
            sm.enable_section_cast_shadow(tree, sm.is_section_cast_shadow_enabled(source, lod, section), lod, section)
    assert assets.save_loaded_asset(tree, False)
    return tree, cards
