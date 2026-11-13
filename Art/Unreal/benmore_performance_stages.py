"""Independent Benmore render candidates; no map or source-asset saves.

Prepare before PIE, bind after the camera settles, then apply(False/True) for
an ABBA comparison. The caller must restore() before ending PIE, even on error.
Both foliage versions stay loaded throughout: memory deltas therefore include
candidate overhead and are not a shipping-memory estimate.
"""
from pathlib import Path


STAGES = ('foliage_far_lod', 'foliage_lod2_segments', 'foliage_nanite', 'foliage_nanite_plain', 'foliage_nanite_volume', 'foliage_nanite_willows', 'foliage_vertex_colour', 'lumen_lighting_updates', 'lumen_card_capture_budget', 'spray_sparse_updates')
LUMEN_UPDATES = {
    # UE 5.8 High's amortized lighting cadence, without switching the whole GI
    # group (which also changes RT build mode, hit lighting and foliage shading).
    'r.LumenScene.DirectLighting.UpdateFactor': 64,
    'r.LumenScene.Radiosity.UpdateFactor': 128,
}
PROTECTED_CVARS = (
    'r.Lumen.HardwareRayTracing', 'r.Lumen.Reflections.Allow',
    'sg.ReflectionQuality', 'r.Lumen.HardwareRayTracing.HitLighting.Allowed',
    'r.RayTracing.Scene.BuildMode', 'r.ScreenPercentage',
    'grass.DensityScale', 'grass.CullDistanceScale',
)
CVAR_STAGES = {'lumen_lighting_updates': LUMEN_UPDATES,
               'lumen_card_capture_budget': {'r.LumenScene.SurfaceCache.CardCaptureFactor': 128},
               'spray_sparse_updates': {'gt.Spray.SparseUpdates': 1}}


def component_count(component):
    import unreal as u
    return component.get_instance_count() if isinstance(component,u.InstancedStaticMeshComponent) else 1


def swap_mesh(component, mesh):
    """Temporarily allow an authored static component to accept a PIE swap."""
    import unreal as u
    if component.static_mesh == mesh:
        return
    mobility = component.get_editor_property('mobility')
    try:
        if mobility == u.ComponentMobility.STATIC:
            component.set_mobility(u.ComponentMobility.MOVABLE)
        assert component.set_static_mesh(mesh), 'Runtime mesh replacement rejected'
    finally:
        component.set_mobility(mobility)
    assert component.get_editor_property('mobility') == mobility


class Candidate:
    def __init__(self, name, root, run_id, far_lod_screen=.008):
        import unreal as u
        if name not in STAGES:
            raise ValueError('Unknown performance stage: ' + name)
        if u.EditorLevelLibrary.get_game_world():
            raise RuntimeError('Prepare candidates before PIE')
        self.name = name
        self.meshes = {}
        self.material = None
        self.bindings = []
        self.grass_bindings = []
        self.grass_reference_counts = {}
        self.original_cvars = {}
        self.protected = {}
        self.world = self.pc = None
        self.active = False
        self.metadata = {'stage': name, 'saved_assets': False,
                         'authored_foliage_only': name.startswith('foliage_')}
        if not run_id or any(not (ch.isalnum() or ch in '_-') for ch in run_id):
            raise ValueError('Invalid run ID')
        destination = '/Game/GrandTour/Demo/BenmoreRoads/PerformanceTrials/Run_' + run_id.replace('-', '_')
        if name == 'foliage_far_lod':
            from benmore_far_tussock_trial import create_candidates
            manifest = Path(root) / 'Art/Export/BenmoreGaea/FarTussockTrial_20261010_v2/manifest.json'
            rows = create_candidates(manifest, destination, screen_size=far_lod_screen)
            self.metadata['far_lod_screen'] = far_lod_screen
            self.meshes = {r['source']: r['candidate'] for r in rows}
            self.metadata['meshes'] = {key: mesh.get_path_name() for key, mesh in self.meshes.items()}

        elif name == 'foliage_lod2_segments':
            from benmore_tussock_segments_trial import create_candidates
            rows=create_candidates(Path(root)/'Art/Export/BenmoreGaea/TussockSegments_20261011T023511Z/manifest.json',destination)
            self.meshes={r['source']:r['candidate'] for r in rows}
            self.metadata['geometry']=[r['geometry'] for r in rows]
            self.metadata['meshes']={key:mesh.get_path_name() for key,mesh in self.meshes.items()}
        elif name == 'foliage_vertex_colour':
            from benmore_foliage_detail_trial import create_candidate, SOURCE
            self.material = create_candidate(destination + '/M_Tussock_VertexColour')
            self.source_material = u.load_asset(SOURCE)
            self.metadata['material'] = self.material.get_path_name()
        elif name in ('foliage_nanite','foliage_nanite_plain','foliage_nanite_volume','foliage_nanite_willows'):
            from benmore_far_tussock_trial import SOURCE_ROOT
            eal = u.EditorAssetLibrary
            sm = u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
            prefix=('/Game/GrandTour/Demo/BenmoreRoads/Scenery/SM_Willow_' if name=='foliage_nanite_willows' else SOURCE_ROOT+'SM_TS_')
            variants=('Young','Windswept','Weathered','Broad') if name=='foliage_nanite_willows' else ('Fine','Rust','Straw','Weathered')
            for variant in variants:
                source = u.load_asset(prefix + variant)
                assert source and not source.get_editor_property('nanite_settings').enabled
                path = destination + '/' + source.get_name() + '_Nanite'
                assert not eal.does_asset_exist(path)
                clone = eal.duplicate_asset(source.get_path_name(), path)
                assert clone
                # Prepare shader usage before PIE. Runtime auto-usage cannot
                # compile these permutations and would silently benchmark the
                # default fallback material. These flag changes remain unsaved.
                for slot in clone.get_editor_property('static_materials'):
                    material=slot.get_editor_property('material_interface')
                    while isinstance(material,u.MaterialInstance):material=material.get_editor_property('parent')
                    assert isinstance(material,u.Material)
                    u.MaterialEditingLibrary.set_material_usage(material,u.MaterialUsage.MATUSAGE_NANITE)
                    assert material.get_editor_property('used_with_nanite')
                    self.metadata.setdefault('prepared_nanite_materials',[])
                    if material.get_path_name() not in self.metadata['prepared_nanite_materials']:
                        self.metadata['prepared_nanite_materials'].append(material.get_path_name())
                settings = clone.get_editor_property('nanite_settings')
                settings.enabled = True
                settings.shape_preservation = {'foliage_nanite_volume':u.NaniteShapePreservation.VOXELIZE,
                    'foliage_nanite_plain':u.NaniteShapePreservation.NONE,
                    'foliage_nanite_willows':u.NaniteShapePreservation.NONE,
                    'foliage_nanite':u.NaniteShapePreservation.PRESERVE_AREA}[name]
                sm.set_nanite_settings(clone, settings, True)
                assert clone.get_editor_property('nanite_settings').enabled
                assert clone.get_editor_property('static_materials') == source.get_editor_property('static_materials')
                self.meshes[source.get_path_name()] = clone
            self.metadata['meshes'] = {key: mesh.get_path_name() for key, mesh in self.meshes.items()}
            self.metadata['shape_preservation'] = {'foliage_nanite_volume':'Voxelize',
                'foliage_nanite_plain':'None','foliage_nanite_willows':'None','foliage_nanite':'PreserveArea'}[name]

        # Landscape-generated grass has GPU-owned instance data. Swapping its
        # live component mesh can discard that data, giving a false speedup.
        # Instead, edit only the in-memory variety references before regenerating
        # the grass cache. Keep every original reference for rollback; never save.
        if self.meshes or self.material:
            grass_types = {}
            for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
                if not isinstance(actor, u.LandscapeProxy):
                    continue
                base = actor.get_editor_property('landscape_material')
                while isinstance(base, u.MaterialInstance):
                    base = base.get_editor_property('parent')
                if not isinstance(base, u.Material):
                    continue
                for node in u.MaterialEditingLibrary.get_material_expressions(base):
                    if isinstance(node, u.MaterialExpressionLandscapeGrassOutput):
                        for entry in node.get_editor_property('grass_types'):
                            grass = entry.get_editor_property('grass_type')
                            if grass:
                                grass_types[grass.get_path_name()] = grass
            for grass in grass_types.values():
                for index, variety in enumerate(grass.get_editor_property('grass_varieties')):
                    mesh = variety.get_editor_property('grass_mesh')
                    if not mesh:
                        continue
                    candidate_mesh = self.meshes.get(mesh.get_path_name(), mesh)
                    original_overrides = list(variety.get_editor_property('override_materials'))
                    candidate_overrides = list(original_overrides)
                    if self.material:
                        for slot in range(len(mesh.get_editor_property('static_materials'))):
                            material = original_overrides[slot] if slot < len(original_overrides) and original_overrides[slot] else mesh.get_material(slot)
                            if material == self.source_material:
                                while len(candidate_overrides) <= slot:
                                    candidate_overrides.append(None)
                                candidate_overrides[slot] = self.material
                    if candidate_mesh != mesh or candidate_overrides != original_overrides:
                        self.grass_bindings.append((grass,index,mesh,candidate_mesh,original_overrides,candidate_overrides))
            self.metadata['authored_foliage_only'] = not bool(self.grass_bindings)
            self.metadata['landscape_varieties'] = [dict(asset=g.get_path_name(),variety=i,source=m.get_path_name(),candidate=c.get_path_name())
                for g,i,m,c,_,_ in self.grass_bindings]

    def bind(self, world, pc):
        import unreal as u
        if self.world is not None:
            self.restore()
        self.world, self.pc = world, pc
        self.bindings = []
        self.grass_reference_counts = {}
        self.protected = {flag: u.SystemLibrary.get_console_variable_float_value(flag)
                          for flag in PROTECTED_CVARS}
        if self.name in CVAR_STAGES:
            settings = CVAR_STAGES[self.name]
            self.original_cvars = {flag: u.SystemLibrary.get_console_variable_int_value(flag)
                                   for flag in settings}
            self.reference_cvars = dict(self.original_cvars)
            if self.name.startswith('lumen_'):
                if not any(self.original_cvars[f] < v for f, v in settings.items()):
                    raise RuntimeError('Lighting update cadence is already at or below candidate cost')
                # Do not increase the work of an already cheaper user override.
                self.candidate_cvars = {f: max(v, self.original_cvars[f]) for f, v in settings.items()}
            else:
                self.reference_cvars = {'gt.Spray.SparseUpdates': 0}
                self.candidate_cvars = dict(settings)
            self.metadata.update(loaded=self.original_cvars, baseline=self.reference_cvars,
                                 candidate=self.candidate_cvars)
        else:
            for actor in u.GameplayStatics.get_all_actors_of_class(world, u.Actor):
                for c in actor.get_components_by_class(u.StaticMeshComponent):
                    # Generated landscape grass has a separate streaming lifecycle;
                    # regenerated varieties are handled separately from authored groups.
                    if isinstance(c, u.GrassInstancedStaticMeshComponent) or not c.static_mesh:
                        continue
                    if self.meshes:
                        candidate = self.meshes.get(c.static_mesh.get_path_name())
                        if candidate:
                            self.bindings.append((c, c.static_mesh, candidate, None, component_count(c)))
                    else:
                        for slot, material in enumerate(c.get_materials()):
                            # Never flatten a material instance or replace its overrides.
                            if material == self.source_material:
                                self.bindings.append((c, material, self.material, slot, component_count(c)))
            if not self.bindings and not self.grass_bindings:
                raise RuntimeError('No exact authored foliage bindings for ' + self.name)
        return {'bindings': [{'component': c.get_path_name(), 'source': original.get_path_name(),
                             'candidate': candidate.get_path_name(), 'slot': slot, 'instances': count}
                            for c, original, candidate, slot, count in self.bindings],
                'protected_cvars': self.protected,
                'lod_cvars': {flag:u.SystemLibrary.get_console_variable_float_value(flag) for flag in
                    ('r.ForceLOD','foliage.ForceLOD','foliage.MinLOD','foliage.LODDistanceScale','r.StaticMeshLODDistanceScale')}}

    def verify_ready(self):
        """Check regenerated grass, after warmup, not just variety references.

        GPU-owned grass reports zero CPU instances. Component counts and mesh /
        material bindings still catch an empty or incompletely regenerated cache.
        Screenshots and moving-camera review remain necessary for coverage.
        """
        import unreal as u
        self.verify()
        expected = {mesh.get_path_name(): (candidate if self.active else mesh)
                    for _,_,mesh,candidate,_,_ in self.grass_bindings}
        counts = {source: 0 for source in expected}
        for actor in u.GameplayStatics.get_all_actors_of_class(self.world, u.LandscapeProxy):
            for component in actor.get_components_by_class(u.GrassInstancedStaticMeshComponent):
                for source, mesh in expected.items():
                    if component.static_mesh == mesh and component.is_visible():
                        if self.material and self.active and self.source_material in component.get_materials():
                            raise RuntimeError('Generated grass retained the reference material')
                        counts[source] += 1
        if expected and not any(counts.values()):
            raise RuntimeError('Landscape grass cache has not regenerated; no timing accepted')
        if not self.grass_reference_counts and not self.active:
            self.grass_reference_counts = counts
        for source, reference in self.grass_reference_counts.items():
            if reference and counts[source] < reference * .95:
                raise RuntimeError('Generated grass coverage count fell by over 5%: ' + source)
        return {'generated_grass_components': counts,
                'reference_components': self.grass_reference_counts,
                'note': 'GPU instance counts are unavailable; component counts do not prove pixel coverage.'}

    def apply(self, active):
        import unreal as u
        # Record first so the caller always attempts rollback after partial errors.
        self.active = active
        if self.name in CVAR_STAGES:
            values = self.candidate_cvars if active else self.reference_cvars
            for flag, value in values.items():
                u.SystemLibrary.execute_console_command(self.world, f'{flag} {value}', self.pc)
                if u.SystemLibrary.get_console_variable_int_value(flag) != value:
                    raise RuntimeError('CVar override rejected: ' + flag)
        for c, original, candidate, slot, count in self.bindings:
            value = candidate if active else original
            if slot is None:
                swap_mesh(c, value)
                actual = c.static_mesh
            else:
                c.set_material(slot, value)
                actual = c.get_material(slot)
            if actual != value or component_count(c) != count:
                raise RuntimeError('Foliage binding/instance count changed: ' + c.get_path_name())
        self.apply_grass(active)
        self.verify()

    def apply_grass(self, active):
        import unreal as u
        grouped = {}
        for grass,index,mesh,candidate,overrides,candidate_overrides in self.grass_bindings:
            key = grass.get_path_name()
            if key not in grouped:
                grouped[key] = (grass,list(grass.get_editor_property('grass_varieties')))
            varieties = grouped[key][1]
            varieties[index].set_editor_property('grass_mesh', candidate if active else mesh)
            varieties[index].set_editor_property('override_materials', candidate_overrides if active else overrides)
        for grass,varieties in grouped.values():
            grass.set_editor_property('grass_varieties', varieties)
        if grouped and self.world:
            # Retain baked grass density/height maps; only rebuild instances.
            u.SystemLibrary.execute_console_command(self.world, 'grass.FlushCachePIE', self.pc)

    def verify(self):
        import unreal as u
        if self.name in CVAR_STAGES:
            expected = self.candidate_cvars if self.active else self.reference_cvars
            for flag, value in expected.items():
                if u.SystemLibrary.get_console_variable_int_value(flag) != value:
                    raise RuntimeError('Candidate CVar changed during capture: ' + flag)
        for flag, original in self.protected.items():
            if u.SystemLibrary.get_console_variable_float_value(flag) != original:
                raise RuntimeError('Protected setting changed during candidate: ' + flag)
        for c, original, candidate, slot, count in self.bindings:
            actual = c.static_mesh if slot is None else c.get_material(slot)
            if actual != (candidate if self.active else original) or component_count(c) != count:
                raise RuntimeError('Foliage changed during capture: ' + c.get_path_name())
        for grass,index,mesh,candidate,overrides,candidate_overrides in self.grass_bindings:
            variety = grass.get_editor_property('grass_varieties')[index]
            if variety.get_editor_property('grass_mesh') != (candidate if self.active else mesh):
                raise RuntimeError('Landscape grass mesh changed during capture')
            if list(variety.get_editor_property('override_materials')) != (candidate_overrides if self.active else overrides):
                raise RuntimeError('Landscape grass material changed during capture')

    def restore(self):
        import unreal as u
        errors = []
        # Attempt every binding even if one has become invalid during a failed run.
        for c, original, _, slot, _ in self.bindings:
            try:
                if slot is None:
                    swap_mesh(c, original)
                    assert c.static_mesh == original
                else:
                    c.set_material(slot, original)
                    assert c.get_material(slot) == original
            except Exception as exc:
                errors.append(str(exc))
        for flag, value in self.original_cvars.items():
            try:
                u.SystemLibrary.execute_console_command(self.world, f'{flag} {value}', self.pc)
                assert u.SystemLibrary.get_console_variable_int_value(flag) == value
            except Exception as exc:
                errors.append(str(exc))
        try:
            self.apply_grass(False)
        except Exception as exc:
            errors.append(str(exc))
        self.active = False
        if errors:
            raise RuntimeError('Candidate rollback failed: ' + '; '.join(errors))
