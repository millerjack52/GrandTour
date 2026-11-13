"""Benmore integration B1 (docs/BENMORE_INTEGRATION_PLAN.md B1 items 2-5): GR2's ground detail, soil scatter and GT surface types on the
Gaea review level (L_Benmore_GaeaReview).

Shared (GrandTour, usable by any landscape):
- MPC_GT_GroundDetail (/Game/GrandTour/Terrain): GR2's GD* numbers, GroundDetail (gt.Ground.Detail), ScatterScale (gt.Ground.Scatter x
  gt.Ground.ScatterDensity; UGTTrackPaintSubsystem writes both and flushes the landscape grass when the scale changes), the scatter's
  cluster numbers, and BenmoreGravelPOM (Codex's gravel parallax switch, moved here from MPC_Benmore_GravelPOM: a material may
  reference two collections, ParameterCollection.h MaxNumParameterCollectionsPerMaterial, and the review material already had two).
- MF_GT_GroundDetail (/Game/GrandTour/Terrain/GroundDetail): GR2's strip detail code (ground_detail.GD_HLSL) as a function. Inputs Base
  (layer colour), ScrubW and GrassW (the ScrubSoil and SoilUnderGrass weights; their sum is the detail's weight, GrassW's share picks
  the slice), WorldPos, PomEnable, and optional Rough, Normal (the layer's, landscape tangent space), AO. Outputs Colour, Normal,
  Roughness, AO. Every number from MPC_GT_GroundDetail.
- LGT_GT_SoilScatter (clods, pebbles, twigs) and LGT_GT_GrassLitter (litter mats) with GR2's SM_GD_* meshes; the pebbles and twigs as
  SM_GD_*_LG copies whose pivot carries GR2's 30 % sink (a grass variety has no Z offset).

Benmore-owned (/Game/GrandTour/Demo/BenmoreRoads/Gaea):
- attach_surfaces(m): the review terrain material (ShoreRefinement/M_GC_Terrain) back to Codex's wiring (B1's detail and scatter and
  B2's deform hole, apron, far mud and vegetation copy out; the gravel parallax switch back on MPC_Benmore_GravelPOM.Enabled), then the
  Landscape Physical Material Output alone (the material has no paint layers to carry the surface types).
  install_benmore_shore.copy_material calls this, so a rebuild of the review material keeps the surface types and nothing else
  (Benmore triage, 2026-10-12: the owner switched the rest off).
- attach(m, detail=False): attach_surfaces, and with detail=True B1's rest as built: MF_GT_GroundDetail between the river-life passes
  and the channel bed (the CP_Source pass-throughs and the ChannelPilot node; weights from the material's own masks), the two scatter
  grass entries, the parallax switch moved into MPC_GT_GroundDetail, and B2's deform zones (benmore_deform_zones.attach_deform).
- Surfaces/PM_Benmore_GravelFirm, PM_Benmore_GravelLoose, PM_Benmore_WetGround: copies of PM_Benmore_FirmGround (PM_Dirt's numbers,
  no unprofiled sinkage); no gravel row exists, so the gravel ones keep Dirt's traction numbers, with bGravelSpray and the Benmore
  gravel palette's tints.

Run as the B1 apply step (Art/benmore_b1.ps1 -Step apply, a -RenderOffScreen editor): writes Art/Export/BenmoreB1/apply-report.json and
saves the review map after the landscape's physical material has rebuilt. The detail goes on only with -GTGroundDetail on the
command line.
"""
import json
import sys
import time
import traceback
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
sys.path.insert(0, str(ROOT / 'Art/Unreal'))
import ground_detail as gd   # noqa: E402  GR2: GD_HLSL, SCALARS, VECTORS, the TA_GD arrays and SM_GD meshes
from benmore_reference_surface import TRACKS   # noqa: E402  Codex's road-relative wheel paths (compact vs loose)

OUT = ROOT / 'Art/Export/BenmoreB1'
TERRAIN = '/Game/GrandTour/Terrain'
MPC_PATH = TERRAIN + '/MPC_GT_GroundDetail'
FOLDER = TERRAIN + '/GroundDetail'
MF_PATH = FOLDER + '/MF_GT_GroundDetail'
GAEA = '/Game/GrandTour/Demo/BenmoreRoads/Gaea'
LEVEL = GAEA + '/L_Benmore_GaeaReview'
TERRAIN_MATERIAL = GAEA + '/ShoreRefinement/M_GC_Terrain'
SURFACES = GAEA + '/Surfaces'
FIRM = GAEA + '/PM_Benmore_FirmGround'
POM_MPC = '/Game/GrandTour/Demo/BenmoreRoads/ReferenceSurface/MPC_Benmore_GravelPOM'
TAG = 'GTGround:'
eal = u.EditorAssetLibrary
mel = u.MaterialEditingLibrary
assets = u.AssetToolsHelpers.get_asset_tools()
CF1, CF3 = u.CustomMaterialOutputType.CMOT_FLOAT1, u.CustomMaterialOutputType.CMOT_FLOAT3

# ---------------------------------------------------------------- the numbers
MF_VECTORS = ['GDOffsetB', 'GDMaskEdges', 'GDTintEdges', 'GDTintDamp', 'GDTintDry']   # GR2's, less the strips' grass map frame
EXTRA_SCALARS = dict(GroundDetail=1.0, ScatterScale=1.0, BenmoreGravelPOM=1.0,
                     ScatterClusterCm=300.0, ScatterSharpen=0.25, ScatterMin=0.1, ScatterMax=2.5)
# The scatter (GR2 per m^2; a grass weight is at most 1, so each variety's density carries the cluster's peak over its mean:
# lerp(0.1, 2.5, s) with s a sharpened value noise symmetric about 0.5 has mean 1.3, so the peak is 2.5 / 1.3).
CLUSTER_PEAK = 2.5 / 1.3
PER_M2 = dict(Clods=0.6, Pebbles=1.5, Twigs=0.05, Litter=0.25)
# Culls as seen (the plan's, m); the assets carry them over grass.CullDistanceScale (DefaultEngine.ini 0.6).
CULL_M = dict(Clods=(20.0, 35.0), Pebbles=(15.0, 25.0), Twigs=(15.0, 25.0), Litter=(15.0, 25.0))
SCALE = dict(Clods=(0.8, 1.25), Pebbles=(0.8, 1.3), Twigs=(0.75, 1.2), Litter=(0.8, 1.2))
SHADOW = dict(Clods=True, Pebbles=False, Twigs=False, Litter=False)
SINK_SHARE = 0.3   # GR2's SinkShare for the pebbles and twigs (their bottom this share of their height under the ground)
SIZE_EXP = 1.2     # within a family, more of the small meshes: weight ~ size^-1.2
# The Benmore gravel palette (the review material's packed and aggregate grading over gravel_floor_04 / _02's linear luminance): B1's
# 15-35 % and 65-85 % luminance bands and the mean, per surface.
BANDS = dict(PM_Benmore_GravelFirm=((0.1802, 0.1766, 0.1658), (0.2153, 0.2110, 0.1980), (0.2000, 0.1960, 0.1840)),
             PM_Benmore_GravelLoose=((0.0731, 0.0720, 0.0687), (0.3301, 0.3252, 0.3103), (0.2179, 0.2147, 0.2049)))
# Benmore B1c: grit A / B the surface's stone faces (its 65-85 % band) x1.15 and x0.85, so the chips stand off the road; dust the road's
# matrix (the packed fines, GravelFirm's 15-35 % band; the loose surface's own low band is the cavities between its stones) x1.35,
# paler than the road like dry dust.
MATRIX = BANDS['PM_Benmore_GravelFirm'][0]
TINTS = {name: (tuple(round(c * 1.15, 4) for c in b[1]), tuple(round(c * 0.85, 4) for c in b[1]), tuple(round(c * 1.35, 4) for c in MATRIX))
         for name, b in BANDS.items()}


def props(obj, **kw):
    for k, v in kw.items():
        obj.set_editor_property(k, v)
    return obj


def desc(e):
    try:
        return str(e.get_editor_property('desc'))
    except Exception:  # noqa: BLE001
        return ''


# ---------------------------------------------------------------- MPC_GT_GroundDetail
def ensure_mpc():
    mpc = eal.load_asset(MPC_PATH) or assets.create_asset('MPC_GT_GroundDetail', TERRAIN, u.MaterialParameterCollection,
                                                          u.MaterialParameterCollectionFactoryNew())
    want_s = dict(gd.SCALARS, **EXTRA_SCALARS)
    want_v = {k: gd.VECTORS[k] for k in MF_VECTORS}
    scalars = list(mpc.get_editor_property('scalar_parameters'))
    vectors = list(mpc.get_editor_property('vector_parameters'))
    have_s = {str(s.get_editor_property('parameter_name')): i for i, s in enumerate(scalars)}
    have_v = {str(s.get_editor_property('parameter_name')): i for i, s in enumerate(vectors)}
    for k, v in want_s.items():   # existing entries keep their ids (the materials' references); defaults follow GR2's numbers
        if k in have_s:
            scalars[have_s[k]].set_editor_property('default_value', float(v))
        else:
            scalars.append(props(u.CollectionScalarParameter(), parameter_name=k, default_value=float(v)))
    for k, v in want_v.items():
        c = list(v) + [0.0] * (4 - len(v))
        if k in have_v:
            vectors[have_v[k]].set_editor_property('default_value', u.LinearColor(*c))
        else:
            vectors.append(props(u.CollectionVectorParameter(), parameter_name=k, default_value=u.LinearColor(*c)))
    mpc.set_editor_property('scalar_parameters', scalars)
    mpc.set_editor_property('vector_parameters', vectors)
    assert eal.save_loaded_asset(mpc)
    return mpc, dict(path=MPC_PATH, scalars=len(scalars), vectors=len(vectors))


# ---------------------------------------------------------------- MF_GT_GroundDetail
def mf_hlsl():
    """GR2's GD_HLSL with the function's inputs: the weights in, the strips' grass map and apron out, the POM toggle."""
    code = gd.GD_HLSL
    swaps = [
        ('// Ground relief GR2 phase B (Art/Unreal/ground_detail.py): the strips\' soil detail over the row\'s own colour, roughness and normal.',
         '// MF_GT_GroundDetail (Art/Unreal/benmore_gt_ground.py, Benmore B1): GR2\'s soil detail (Art/Unreal/ground_detail.py GD_HLSL) as a\n'
         '// function: the weights are inputs (ScrubW + GrassW = the detail\'s weight; GrassW\'s share = the SoilUnderGrass slice).'),
        ('float gdW = saturate(ScrubW) * (1.0 - saturate(ApronBlend)) * (GroundDetail > 0.5 ? 1.0 : 0.0)',
         'float gdW = saturate(saturate(ScrubW) + saturate(GrassW)) * (GroundDetail > 0.5 ? 1.0 : 0.0)'),
        ('''// The grass ground (slice 1) from the strip's grass map.
float2 gdGuv = (gdXY - GDGrassOrigin.xy) * GDGrassScale.xy;
float gdG = all(gdGuv > 0.0) && all(gdGuv < 1.0) ? saturate(GrassMap.SampleLevel(GrassMapSampler, gdGuv, 0.0).r) : 0.0;''',
         '''// The grass ground (slice 1): GrassW's share of the weight.
float gdG = saturate(GrassW) / max(saturate(ScrubW) + saturate(GrassW), 1e-4);'''),
        ('float pmFade = 1.0 - smoothstep(GDPomNearM * 100.0, max(GDPomFarM, GDPomNearM + 0.01) * 100.0, gdDist);',
         'float pmFade = (1.0 - smoothstep(GDPomNearM * 100.0, max(GDPomFarM, GDPomNearM + 0.01) * 100.0, gdDist)) * saturate(PomEnable);'),
    ]
    for a, b in swaps:
        assert code.count(a) == 1, 'GD_HLSL changed: ' + a[:60]
        code = code.replace(a, b)
    return code


FN_INPUTS = [   # name, type, preview default (None: required)
    ('Base', 'VECTOR3', None), ('ScrubW', 'SCALAR', None), ('GrassW', 'SCALAR', None), ('WorldPos', 'VECTOR3', None),
    ('PomEnable', 'SCALAR', (1.0, 0.0, 0.0)), ('Rough', 'SCALAR', (0.85, 0.0, 0.0)), ('Normal', 'VECTOR3', (0.0, 0.0, 1.0)),
    ('AO', 'SCALAR', (1.0, 0.0, 0.0))]
FN_OUTPUTS = [('Colour', ''), ('Normal', 'GDNormal'), ('Roughness', 'GDRough1'), ('AO', 'GDAO')]


def build_function(mpc):
    mf = eal.load_asset(MF_PATH)
    if mf is None:
        eal.make_directory(FOLDER)
        mf = assets.create_asset('MF_GT_GroundDetail', FOLDER, u.MaterialFunction, u.MaterialFunctionFactoryNew())
    # The inputs and outputs stay (their ids are what calling materials hold); everything between is rebuilt.
    keep_in, keep_out = {}, {}
    for e in list(mel.get_material_function_expressions(mf)):
        if isinstance(e, u.MaterialExpressionFunctionInput) and str(e.get_editor_property('input_name')) in [n for n, _, _ in FN_INPUTS]:
            keep_in[str(e.get_editor_property('input_name'))] = e
        elif isinstance(e, u.MaterialExpressionFunctionOutput) and str(e.get_editor_property('output_name')) in [n for n, _ in FN_OUTPUTS]:
            keep_out[str(e.get_editor_property('output_name'))] = e
        else:
            mel.delete_material_expression_in_function(mf, e)
    y = [0]

    def expr(cls, x=-1400, **kw):
        y[0] += 90
        return props(mel.create_material_expression_in_function(mf, cls, x, y[0]), **kw)
    mf.set_editor_property('description', "Benmore B1: GR2's soil detail (ScrubSoil / SoilUnderGrass bakes, A2 anti-tile, parallax 15-25 m, "
                                          "faded out 25-40 m) over a layer's colour; every number from MPC_GT_GroundDetail.")
    for i, (name, kind, preview) in enumerate(FN_INPUTS):
        node = keep_in.get(name) or expr(u.MaterialExpressionFunctionInput, x=-2200)
        props(node, input_name=name, input_type=getattr(u.FunctionInputType, 'FUNCTION_INPUT_' + kind), sort_priority=i)
        if preview is not None:
            v = u.Vector4f()
            for axis, value in zip('xyzw', (preview[0], preview[1], preview[2], 0.0)):
                v.set_editor_property(axis, value)
            props(node, use_preview_value_as_default=True, preview_value=v)
        else:
            props(node, use_preview_value_as_default=False)
        keep_in[name] = node
    for i, (name, _) in enumerate(FN_OUTPUTS):
        keep_out[name] = props(keep_out.get(name) or expr(u.MaterialExpressionFunctionOutput, x=200), output_name=name, sort_priority=i)
    c = expr(u.MaterialExpressionCustom, x=-600, code=mf_hlsl(), output_type=CF3, description='Ground detail (MF_GT_GroundDetail)')
    names = ['Base', 'Rough', 'N', 'AOIn', 'ScrubW', 'GrassW', 'WorldPos', 'PomEnable', 'VN', 'CamPos', 'SunDir', 'GroundDetail', 'GC', 'GN', 'GO'] \
        + list(gd.SCALARS) + MF_VECTORS
    c.set_editor_property('inputs', [props(u.CustomInput(), input_name=k) for k in names])
    c.set_editor_property('additional_outputs', [props(u.CustomOutput(), output_name=k, output_type=t) for k, t in
                                                 [('GDRough', CF3), ('GDRough1', CF1), ('GDNormal', CF3), ('GDAO', CF1)]])

    def con(a, out, pin):
        assert mel.connect_material_expressions(a, out, c, pin), 'MF pin ' + pin
    for name, pin in [('Base', 'Base'), ('Rough', 'Rough'), ('Normal', 'N'), ('AO', 'AOIn'), ('ScrubW', 'ScrubW'), ('GrassW', 'GrassW'),
                      ('WorldPos', 'WorldPos'), ('PomEnable', 'PomEnable')]:
        con(keep_in[name], '', pin)
    con(expr(u.MaterialExpressionVertexNormalWS), '', 'VN')
    con(expr(u.MaterialExpressionCameraPositionWS), '', 'CamPos')
    con(expr(u.MaterialExpressionSkyAtmosphereLightDirection, light_index=0), '', 'SunDir')
    con(expr(u.MaterialExpressionCollectionParameter, collection=mpc, parameter_name='GroundDetail'), '', 'GroundDetail')
    for pin, asset, sampler in [('GC', 'TA_GD_Color', 'SAMPLERTYPE_COLOR'), ('GN', 'TA_GD_Normal', 'SAMPLERTYPE_NORMAL'),
                                ('GO', 'TA_GD_ORH', 'SAMPLERTYPE_LINEAR_COLOR')]:
        tex = eal.load_asset(gd.DEST + '/' + asset)
        assert tex, 'no %s/%s' % (gd.DEST, asset)
        con(expr(u.MaterialExpressionTextureObject, texture=tex, sampler_type=getattr(u.MaterialSamplerType, sampler)), '', pin)
    for name in gd.SCALARS:
        con(expr(u.MaterialExpressionCollectionParameter, collection=mpc, parameter_name=name), '', name)
    for name in MF_VECTORS:   # a collection vector is float4; the code reads float3s
        mask = expr(u.MaterialExpressionComponentMask, r=True, g=True, b=True, a=False)
        assert mel.connect_material_expressions(expr(u.MaterialExpressionCollectionParameter, collection=mpc, parameter_name=name), '', mask, '')
        con(mask, '', name)
    for name, out in FN_OUTPUTS:
        assert mel.connect_material_expressions(c, out, keep_out[name], ''), 'MF output ' + name
    mel.update_material_function(mf, None)
    assert eal.save_loaded_asset(mf)
    return mf, dict(path=MF_PATH, inputs=[n for n, _, _ in FN_INPUTS], outputs=[n for n, _ in FN_OUTPUTS],
                    collection=MPC_PATH, mpc_scalars=list(gd.SCALARS) + ['GroundDetail'], mpc_vectors=MF_VECTORS)


# ---------------------------------------------------------------- scatter meshes, grass types
def manifest_rows():
    return json.loads(gd.MANIFEST.read_text())['scatter']


def scatter_meshes(report):
    """The grass varieties' meshes: GR2's clods and litter (modelled sunk, origin = ground) and pivot-shifted copies of the pebbles and
    twigs. All of them out of ray tracing (so out of hardware Lumen's scene); the grass varieties also leave distance fields."""
    out = {}
    sm = u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    interchange = u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
    rows = []
    for row in manifest_rows():
        fam = gd.family_of(row['name'])
        if fam == 'TussockBases':
            continue
        src = eal.load_asset(gd.DEST + '/' + row['name'])
        assert src, 'no ' + row['name']
        mesh = src
        if fam in ('Pebbles', 'Twigs'):
            box = src.get_bounding_box()
            height = box.max.z - box.min.z
            dz = -SINK_SHARE * height - box.min.z   # the bottom goes SINK_SHARE of the height under the origin
            name = row['name'] + '_LG'
            mesh = None
            for legacy in (False, True):   # GR2's import path (the session's default) first; the legacy FBX importer if the offset did not take
                u.SystemLibrary.execute_console_command(world, 'Interchange.FeatureFlags.Import.FBX %d' % (0 if legacy else interchange))
                task = props(u.AssetImportTask(), filename=str(ROOT / row['fbx']), destination_path=FOLDER, destination_name=name,
                             automated=True, replace_existing=True, save=False)
                opt = props(u.FbxImportUI(), import_mesh=True, import_as_skeletal=False, import_materials=False, import_textures=False,
                            import_animations=False, mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
                props(opt.static_mesh_import_data, combine_meshes=True, auto_generate_collision=False, generate_lightmap_u_vs=False,
                      vertex_color_import_option=u.VertexColorImportOption.REPLACE, normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,
                      import_translation=u.Vector(0.0, 0.0, dz))
                if legacy:
                    props(opt.static_mesh_import_data, convert_scene=True, convert_scene_unit=True)
                task.options = opt
                assets.import_asset_tasks([task])
                mesh = eal.load_asset(FOLDER + '/' + name)
                assert mesh, 'the import made no ' + name
                nb = mesh.get_bounding_box()
                if abs(nb.min.z - (-SINK_SHARE * height)) < max(0.05, 0.05 * height) and abs((nb.max.z - nb.min.z) - height) < 0.05 + 0.02 * height:
                    report.setdefault('scatter_import_path', {})[name] = 'legacy FBX' if legacy else 'Interchange'
                    break
            u.SystemLibrary.execute_console_command(world, 'Interchange.FeatureFlags.Import.FBX %d' % interchange)
            mesh.set_material(0, src.get_material(0))
            ns = mesh.get_editor_property('nanite_settings')
            ns.enabled = False
            sm.set_nanite_settings(mesh, ns, True)
            try:
                sm.remove_collisions(mesh)
            except Exception:  # noqa: BLE001
                pass
            nb = mesh.get_bounding_box()
            got = nb.min.z
            assert abs(got - (-SINK_SHARE * height)) < max(0.05, 0.05 * height), '%s: min z %.3f, want %.3f' % (name, got, -SINK_SHARE * height)
            assert abs((nb.max.z - nb.min.z) - height) < 0.05 + 0.02 * height, name + ': size changed'
        mesh.set_editor_property('support_ray_tracing', False)
        assert eal.save_loaded_asset(mesh)
        size = float(row.get('size_cm', 5.0))
        bb = mesh.get_bounding_box()
        rows.append(dict(name=mesh.get_name(), family=fam, size_cm=size, min_z_cm=round(bb.min.z, 3), max_z_cm=round(bb.max.z, 3)))
        out.setdefault(fam, []).append((mesh, size))
    report['scatter_meshes'] = rows
    return out


def grass_types(meshes, report):
    cull_scale = u.SystemLibrary.get_console_variable_float_value('grass.CullDistanceScale') or 1.0
    made = {}
    for type_name, families in [('LGT_GT_SoilScatter', ['Clods', 'Pebbles', 'Twigs']), ('LGT_GT_GrassLitter', ['Litter'])]:
        path = FOLDER + '/' + type_name
        lgt = eal.load_asset(path) or assets.create_asset(type_name, FOLDER, u.LandscapeGrassType, u.LandscapeGrassTypeFactory())
        varieties = []
        rows = []
        for fam in families:
            sizes = meshes[fam]
            weights = [s ** -SIZE_EXP for _, s in sizes]
            total = sum(weights)
            start, end = CULL_M[fam]
            for (mesh, size), w in zip(sizes, weights):
                per10 = PER_M2[fam] * 10.0 * CLUSTER_PEAK * w / total
                lo, hi = SCALE[fam]
                v = props(u.GrassVariety(), grass_mesh=mesh, override_materials=[], grass_density=u.PerPlatformFloat(default=per10),
                          start_cull_distance=u.PerPlatformInt(default=int(round(start * 100.0 / cull_scale))),
                          end_cull_distance=u.PerPlatformInt(default=int(round(end * 100.0 / cull_scale))), use_grid=False,
                          random_rotation=True, align_to_surface=True, min_lod=-1, scaling=u.GrassScaling.UNIFORM,
                          scale_x=u.FloatInterval(min=lo, max=hi), scale_y=u.FloatInterval(min=lo, max=hi), scale_z=u.FloatInterval(min=lo, max=hi),
                          cast_dynamic_shadow=SHADOW[fam], cast_contact_shadow=False, affect_distance_field_lighting=False,
                          receives_decals=False, use_landscape_lightmap=False, keep_instance_buffer_cpu_copy=False)
                varieties.append(v)
                rows.append(dict(mesh=mesh.get_name(), family=fam, per_10m2=round(per10, 4), per_m2_mean=round(PER_M2[fam] * w / total, 4),
                                 cull_seen_m=[start, end], cull_asset_cm=[int(round(start * 100.0 / cull_scale)), int(round(end * 100.0 / cull_scale))],
                                 scale=[lo, hi], dynamic_shadow=SHADOW[fam]))
        # The project's grass.DensityScale (0.5, DefaultEngine.ini) is the tussocks' cost setting; the scatter keeps GR2's densities and
        # has its own scale (gt.Ground.ScatterDensity).
        props(lgt, grass_varieties=varieties, enable_density_scaling=False)
        assert eal.save_loaded_asset(lgt)
        made[type_name] = lgt
        report.setdefault('grass_types', {})[type_name] = dict(path=path, varieties=rows, density_scaling=False, cull_distance_scale=cull_scale,
                                                               lighting='no distance-field lighting, mesh out of ray tracing; shadows only for clods',
                                                               align_to_surface=True, random_yaw=True)
    return made


# ---------------------------------------------------------------- physical materials
def surfaces(report):
    firm = eal.load_asset(FIRM)
    assert firm, 'no ' + FIRM
    eal.make_directory(SURFACES)
    made = {}
    rows = {}
    for name in ['PM_Benmore_GravelFirm', 'PM_Benmore_GravelLoose', 'PM_Benmore_WetGround']:
        path = SURFACES + '/' + name
        pm = eal.load_asset(path) or eal.duplicate_asset(FIRM, path)
        assert pm, path
        for k in ('friction', 'rolling_resistance', 'sinkage_rate', 'max_sinkage', 'wet_friction_scale', 'wet_rolling_resistance_scale',
                  'wet_sinkage_scale', 'sinkage_drag_scale', 'plough_drag', 'sinkage_grip_loss', 'track_depth'):
            pm.set_editor_property(k, firm.get_editor_property(k))
        if name == 'PM_Benmore_WetGround':
            # Wet Dirt: the firm ground's numbers at full wetness (friction x WetFrictionScale, rolling x WetRollingResistanceScale); still no
            # unprofiled sinkage, MaxSinkage kept (the crossing profiles' eligibility).
            pm.set_editor_property('friction', firm.get_editor_property('friction') * firm.get_editor_property('wet_friction_scale'))
            pm.set_editor_property('rolling_resistance', firm.get_editor_property('rolling_resistance') * firm.get_editor_property('wet_rolling_resistance_scale'))
            pm.set_editor_property('gravel_spray', False)
        else:
            a, b, d = TINTS[name]
            pm.set_editor_property('gravel_spray', True)
            pm.set_editor_property('spray_tint_a', u.LinearColor(*a, 1.0))
            pm.set_editor_property('spray_tint_b', u.LinearColor(*b, 1.0))
            pm.set_editor_property('dust_tint', u.LinearColor(*d, 1.0))
        assert eal.save_loaded_asset(pm)
        made[name] = pm
        rows[name] = {k: pm.get_editor_property(k) for k in ('friction', 'rolling_resistance', 'sinkage_rate', 'max_sinkage', 'gravel_spray')}
        rows[name]['tints'] = None if name == 'PM_Benmore_WetGround' else TINTS[name]
    rows['PM_Benmore_FirmGround'] = {k: firm.get_editor_property(k) for k in ('friction', 'rolling_resistance', 'sinkage_rate', 'max_sinkage')}
    report['surfaces'] = rows
    return made, firm


# ---------------------------------------------------------------- the review material
WEIGHTS_HLSL = r'''// Benmore B1 (Art/Unreal/benmore_gt_ground.py): MF_GT_GroundDetail's weights from the review material's own masks.
// Off the gravel running surface (RoadMask R), the river-life banks (Ecology R gravel, G silt), the creek and river bed (the bed
// zones' alpha, as the ChannelPilot pass reads it: nothing of it on the bed or under the water), the composition's exposed rock
// (Hills: CompositionZones G plus slope, as the hill pass reads it) and the lake (local z under 48 cm). The verge soil keeps it.
// GrassW: tussock ground (Vegetation G + B, the tussock and clump densities), the SoilUnderGrass slice.
float2 q = P.xy * 0.01;
float2 cuv = float2((q.x + 11463.0) / 13680.0, (4278.0 - q.y) / 12770.0);
float4 geo = Texture2DSampleLevel(Zones, ZonesSampler, cuv, 0.0);
float slope = 1.0 - saturate(normalize(N).z);
float rock = smoothstep(0.16, 0.64, geo.g + slope * 0.10) * 0.90;
float bank = saturate(max(Eco.r, Eco.g) * 1.5);
float2 bedUV = <BEDUV>;
float bed = (any(bedUV < 0.0) || any(bedUV > 1.0)) ? 0.0 : Texture2DSampleLevel(Bed, BedSampler, bedUV, 0.0).a;
float open = (1.0 - saturate(Mask.r)) * (1.0 - bank) * (1.0 - rock) * (P.z < 48.0 ? 0.0 : 1.0) * (1.0 - smoothstep(0.0, 0.25, bed));
float tuss = smoothstep(0.2, 0.5, saturate(Veg.g + Veg.b));
GrassW = open * tuss;
return open * (1.0 - tuss);
'''

MASKS_HLSL = r'''// Benmore B1 (Art/Unreal/benmore_gt_ground.py): the landscape grass scatter's weights and the physical material weights (the grass
// maps and the physical-material render only; nothing here reaches the pixel shader).
struct GTScatterNoise
{
    float Pad;
    float H(float2 i) { return frac(sin(dot(i, float2(127.1, 311.7))) * 43758.5453); }
    float V(float2 c) { float2 i = floor(c); float2 f = c - i; f = f * f * (3.0 - 2.0 * f);
        return lerp(lerp(H(i), H(i + float2(1.0, 0.0)), f.x), lerp(H(i + float2(0.0, 1.0)), H(i + float2(1.0, 1.0)), f.x), f.y); }
};
float2 q = P.xy * 0.01;
float2 cuv = float2((q.x + 11463.0) / 13680.0, (4278.0 - q.y) / 12770.0);
float4 geo = Texture2DSampleLevel(Zones, ZonesSampler, cuv, 0.0);
float slope = 1.0 - saturate(normalize(N).z);
float rock = smoothstep(0.16, 0.64, geo.g + slope * 0.10) * 0.90;
float bank = saturate(max(Eco.r, Eco.g) * 1.5);
float lake = P.z < 48.0 ? 1.0 : 0.0;
float2 bedUV = <BEDUV>;
float bed = (any(bedUV < 0.0) || any(bedUV > 1.0)) ? 0.0 : Texture2DSampleLevel(Bed, BedSampler, bedUV, 0.0).a;
float open = (1.0 - saturate(Mask.r)) * (1.0 - bank) * (1.0 - rock) * (1.0 - lake) * (1.0 - smoothstep(0.0, 0.1, bed));
float tuss = smoothstep(0.2, 0.5, saturate(Veg.g + Veg.b));
<TRACKS>
// Scatter: none on the running surface or within 0.6-1.4 m of its edge (RoadCoordinates), none in the water; GR2's 3 m cluster noise,
// sharpened, over its peak (the varieties' densities carry the peak over the mean).
float beyond = Mask.g > 0.001 ? abs(lateral) - halfWidth : 99.0;
float clear = smoothstep(0.6, 1.4, beyond) * (Mask.r < 0.02 ? 1.0 : 0.0);
GTScatterNoise nz;
nz.Pad = 0.0;
float s = nz.V(P.xy / max(ClusterCm, 50.0) + float2(17.3, 41.9));
float sh = saturate(Sharpen);
s = sh > 0.0 ? smoothstep(0.5 - sh, 0.5 + sh, s) : s;
float cluster = lerp(ClusterMin, ClusterMax, s) / max(ClusterMax, 0.01);
float scale = saturate(ScatterScale);
LitterW = scale * open * clear * tuss * cluster;
// Surfaces: the running surface split by Codex's loose share (centre and edges loose, the wheel paths compact); the bed, the silt
// banks and the lake wet; the rest the firm ground.
float road = saturate(Mask.r);
float wet = max(max(saturate(bed * 1.5), saturate(Eco.g * 1.5)), lake) * (1.0 - road);
Compact = road * (1.0 - loose);
Loose = road * loose;
Wet = wet;
Firm = (1.0 - road) * (1.0 - wet);
return scale * open * clear * cluster;
'''


SURFACES_HLSL = r'''// Benmore B1 (Art/Unreal/benmore_gt_ground.py attach_surfaces): the physical material weights (the physical-material render only;
// nothing here reaches the pixel shader). B1's MASKS_HLSL numbers: the running surface split by Codex's loose share (centre and edges
// loose, the wheel paths compact); the bed, the silt banks and the lake wet; the rest the firm ground.
float lake = P.z < 48.0 ? 1.0 : 0.0;
float2 bedUV = <BEDUV>;
float bed = (any(bedUV < 0.0) || any(bedUV > 1.0)) ? 0.0 : Texture2DSampleLevel(Bed, BedSampler, bedUV, 0.0).a;
<TRACKS>
float road = saturate(Mask.r);
float wet = max(max(saturate(bed * 1.5), saturate(Eco.g * 1.5)), lake) * (1.0 - road);
Compact = road * (1.0 - loose);
Loose = road * loose;
Wet = wet;
Firm = (1.0 - road) * (1.0 - wet);
return road;
'''
SCATTER_ENTRIES = ('GTSoilScatter', 'GTGrassLitter')


def _graph(m):
    """The review material's nodes B1 reads or rewires (Codex's road, river-life, composition and bed nodes)."""
    nodes = list(mel.get_material_expressions(m))

    def one(pred, what):
        hits = [e for e in nodes if pred(e)]
        assert len(hits) == 1, '%s: %d' % (what, len(hits))
        return hits[0]

    def inputs_of(e):
        return [str(x.get_editor_property('input_name')) for x in e.get_editor_property('inputs')]

    def tex_node(cls, name):
        return one(lambda e: isinstance(e, cls) and e.get_editor_property('texture') and e.get_editor_property('texture').get_name() == name, name)
    g = dict(nodes=nodes)
    g['cp'] = one(lambda e: isinstance(e, u.MaterialExpressionCustom) and desc(e) == 'ChannelPilot' and 'Zones' in inputs_of(e), 'ChannelPilot')
    g['src'] = {k: one(lambda e, k=k: isinstance(e, u.MaterialExpressionCustom) and desc(e) == k, k) for k in ('CP_SourceColor|', 'CP_SourceNormal|', 'CP_SourceRough|')}
    refcol = one(lambda e: isinstance(e, u.MaterialExpressionCustom) and 'float3 gravel=' in e.get_editor_property('code') and 'Coords' in inputs_of(e), 'reference colour')
    g['road'] = dict(zip(inputs_of(refcol), mel.get_inputs_for_material_expression(m, refcol)))['Mask']
    assert isinstance(g['road'], u.MaterialExpressionTextureSample) and g['road'].get_editor_property('texture').get_name() == 'T_Benmore_RoadMask'
    g['coords'] = tex_node(u.MaterialExpressionTextureSample, 'T_Benmore_RoadCoordinates')
    g['eco'] = tex_node(u.MaterialExpressionTextureSample, 'T_RL_Ecology')
    g['veg'] = tex_node(u.MaterialExpressionTextureSample, 'T_RL_Vegetation')
    g['zones'] = tex_node(u.MaterialExpressionTextureObject, 'T_Benmore_CompositionZones')
    g['bed'] = tex_node(u.MaterialExpressionTextureObject, 'T_GC_ExtendedBedZones')
    g['gout'] = one(lambda e: isinstance(e, u.MaterialExpressionLandscapeGrassOutput), 'grass output')
    bed_line = next(l for l in g['cp'].get_editor_property('code').splitlines() if l.strip().startswith('float2 maskUV='))
    g['bed_uv'] = bed_line.split('=', 1)[1].strip().rstrip(';')
    return g


def _adder(m, x=1800, y=-2400):
    row = [0]

    def expr(cls, **kw):
        row[0] += 100
        return props(mel.create_material_expression(m, cls, x, y + row[0]), desc=TAG + str(row[0]), **kw)
    return expr


def _con(a, out, b, pin):
    assert mel.connect_material_expressions(a, out, b, pin), '%s -> %s' % (out, pin)


def _strip(m, report):
    """Codex's review material as it was before B1: the GTGround: and GTDeform: nodes out (B2's wrappers back to their root inputs), the
    channel bed's inputs back to the river-life pass-throughs, the gravel parallax switch back on MPC_Benmore_GravelPOM.Enabled, the two
    scatter grass entries out, Morphology/T_RL_Vegetation back in place of B2's bog copy. Repeatable."""
    import benmore_deform_zones
    for e in list(mel.get_material_expressions(m)):
        if desc(e).startswith(TAG):
            mel.delete_material_expression(m, e)
    report['deform_unwrapped'] = benmore_deform_zones._unwrap(m)
    g = _graph(m)
    for pin, s in [('Base', 'CP_SourceColor|'), ('OldN', 'CP_SourceNormal|'), ('OldR', 'CP_SourceRough|')]:
        _con(g['src'][s], '', g['cp'], pin)
    # The parallax switch: the name first, then the collection (as attach_detail moves it, in reverse).
    pom, back = eal.load_asset(POM_MPC), 0
    for e in g['nodes']:
        if isinstance(e, u.MaterialExpressionCollectionParameter):
            c = e.get_editor_property('collection')
            if c and c.get_path_name().split('.')[0] == MPC_PATH and str(e.get_editor_property('parameter_name')) == 'BenmoreGravelPOM':
                e.set_editor_property('parameter_name', 'Enabled')
                e.set_editor_property('collection', pom)
                back += 1
    report['gravel_pom_switch_restored'] = back
    gout = g['gout']
    entries = list(gout.get_editor_property('grass_types'))
    keep = [e for e in entries if str(e.get_editor_property('name')) not in SCATTER_ENTRIES]
    if len(keep) != len(entries):
        before = [x.get_name() if x else None for x in mel.get_inputs_for_material_expression(m, gout)][:len(keep)]
        gout.set_editor_property('grass_types', keep)
        after = [x.get_name() if x else None for x in mel.get_inputs_for_material_expression(m, gout)]
        assert after == before, 'grass wiring changed: %s -> %s' % (before, after)
    report['grass_entries_removed'] = len(entries) - len(keep)
    report['grass_entries'] = [str(e.get_editor_property('name')) for e in keep]
    veg = eal.load_asset(benmore_deform_zones.VEG_SRC)
    assert veg, benmore_deform_zones.VEG_SRC
    restored = 0
    for e in mel.get_material_expressions(m):
        if isinstance(e, (u.MaterialExpressionTextureSample, u.MaterialExpressionTextureObject)):
            t = e.get_editor_property('texture')
            if t and t.get_name() == 'T_RL_Vegetation' and t.get_path_name() != veg.get_path_name():
                e.set_editor_property('texture', veg)
                restored += 1
    report['vegetation_restored'] = restored
    return g


def _compile_save(m):
    errors = mel.recompile_material(m)
    assert not errors, 'M_GC_Terrain: %s' % list(errors)
    assert eal.save_loaded_asset(m)


def attach_surfaces(m, report=None, save=True):
    """The surface types alone on the review terrain material: _strip, then a Landscape Physical Material Output fed from Codex's road
    mask and loose share, the river-life silt, the bed and the lake level. Returns a dict for the report."""
    report = report if report is not None else {}
    g = _strip(m, report)
    expr = _adder(m)
    p = expr(u.MaterialExpressionWorldPosition, world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    k = expr(u.MaterialExpressionCustom, code=SURFACES_HLSL.replace('<BEDUV>', g['bed_uv']).replace('<TRACKS>', TRACKS), output_type=CF1,
             description='Benmore B1 surface weights')
    k.set_editor_property('inputs', [props(u.CustomInput(), input_name=x) for x in ['P', 'Mask', 'Coords', 'Eco', 'Bed']])
    k.set_editor_property('additional_outputs', [props(u.CustomOutput(), output_name=x, output_type=CF1) for x in ['Compact', 'Loose', 'Wet', 'Firm']])
    for a, out, pin in [(p, '', 'P'), (g['road'], 'RGB', 'Mask'), (g['coords'], 'RGB', 'Coords'), (g['eco'], 'RGB', 'Eco'), (g['bed'], '', 'Bed')]:
        _con(a, out, k, pin)
    pms = {x: eal.load_asset(SURFACES + '/' + x) for x in ['PM_Benmore_GravelFirm', 'PM_Benmore_GravelLoose', 'PM_Benmore_WetGround']}
    pms['PM_Benmore_FirmGround'] = eal.load_asset(FIRM)
    phys = expr(u.MaterialExpressionLandscapePhysicalMaterialOutput)
    order = [('PM_Benmore_GravelFirm', 'Compact'), ('PM_Benmore_GravelLoose', 'Loose'), ('PM_Benmore_WetGround', 'Wet'), ('PM_Benmore_FirmGround', 'Firm')]
    phys.set_editor_property('inputs', [props(u.PhysicalMaterialInput(), physical_material=pms[x]) for x, _ in order])
    for x, out in order:
        _con(k, out, phys, x)
    if save:
        _compile_save(m)
    report.update(material=m.get_path_name(), bed_uv=g['bed_uv'], physical_material_output=[x for x, _ in order])
    return report


def attach_detail(m, report):
    """B1's rest as built (off since the triage): MF_GT_GroundDetail before the channel bed, the scatter grass entries, the parallax switch
    moved into MPC_GT_GroundDetail (the two-collection limit), and B2's deform zones. Call after attach_surfaces."""
    mpc = eal.load_asset(MPC_PATH)
    mf = eal.load_asset(MF_PATH)
    assert mpc and mf, 'run ensure_mpc / build_function first'
    g = _graph(m)
    cp, src, road, gout = g['cp'], g['src'], g['road'], g['gout']
    # Codex's gravel parallax switch into MPC_GT_GroundDetail: the name first, then the collection, so the node never names a parameter
    # its collection lacks.
    moved = 0
    for e in g['nodes']:
        if isinstance(e, u.MaterialExpressionCollectionParameter):
            c = e.get_editor_property('collection')
            if c and c.get_path_name().split('.')[0] == POM_MPC and str(e.get_editor_property('parameter_name')) == 'Enabled':
                e.set_editor_property('parameter_name', 'BenmoreGravelPOM')
                e.set_editor_property('collection', mpc)
                moved += 1
    expr = _adder(m, y=-1400)
    p = expr(u.MaterialExpressionWorldPosition, world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    n = expr(u.MaterialExpressionVertexNormalWS)
    w = expr(u.MaterialExpressionCustom, code=WEIGHTS_HLSL.replace('<BEDUV>', g['bed_uv']), output_type=CF1, description='Benmore B1 ground detail weights')
    w.set_editor_property('inputs', [props(u.CustomInput(), input_name=k) for k in ['P', 'N', 'Mask', 'Eco', 'Veg', 'Zones', 'Bed']])
    w.set_editor_property('additional_outputs', [props(u.CustomOutput(), output_name='GrassW', output_type=CF1)])
    for a, out, pin in [(p, '', 'P'), (n, '', 'N'), (road, 'RGB', 'Mask'), (g['eco'], 'RGB', 'Eco'), (g['veg'], 'RGB', 'Veg'), (g['zones'], '', 'Zones'), (g['bed'], '', 'Bed')]:
        _con(a, out, w, pin)
    call = expr(u.MaterialExpressionMaterialFunctionCall)
    call.set_editor_property('material_function', mf)
    for a, out, pin in [(src['CP_SourceColor|'], '', 'Base'), (w, '', 'ScrubW'), (w, 'GrassW', 'GrassW'), (p, '', 'WorldPos'),
                        (src['CP_SourceRough|'], '', 'Rough'), (src['CP_SourceNormal|'], '', 'Normal')]:
        _con(a, out, call, pin)
    for out, pin in [('Colour', 'Base'), ('Normal', 'OldN'), ('Roughness', 'OldR')]:
        _con(call, out, cp, pin)
    assert mel.connect_material_property(call, 'AO', u.MaterialProperty.MP_AMBIENT_OCCLUSION)
    # The scatter weights (custom outputs only; its surface outputs are unused: attach_surfaces feeds the physical material output).
    k = expr(u.MaterialExpressionCustom, code=MASKS_HLSL.replace('<BEDUV>', g['bed_uv']).replace('<TRACKS>', TRACKS), output_type=CF1,
             description='Benmore B1 scatter and surface weights')
    knames = ['P', 'N', 'Mask', 'Coords', 'Eco', 'Veg', 'Zones', 'Bed', 'ScatterScale', 'ClusterCm', 'Sharpen', 'ClusterMin', 'ClusterMax']
    k.set_editor_property('inputs', [props(u.CustomInput(), input_name=x) for x in knames])
    k.set_editor_property('additional_outputs', [props(u.CustomOutput(), output_name=x, output_type=CF1) for x in ['LitterW', 'Compact', 'Loose', 'Wet', 'Firm']])
    for a, out, pin in [(p, '', 'P'), (n, '', 'N'), (road, 'RGB', 'Mask'), (g['coords'], 'RGB', 'Coords'), (g['eco'], 'RGB', 'Eco'), (g['veg'], 'RGB', 'Veg'),
                        (g['zones'], '', 'Zones'), (g['bed'], '', 'Bed')]:
        _con(a, out, k, pin)
    for pin, param in [('ScatterScale', 'ScatterScale'), ('ClusterCm', 'ScatterClusterCm'), ('Sharpen', 'ScatterSharpen'), ('ClusterMin', 'ScatterMin'),
                       ('ClusterMax', 'ScatterMax')]:
        _con(expr(u.MaterialExpressionCollectionParameter, collection=mpc, parameter_name=param), '', k, pin)
    # Grass: the five painterly entries kept as they are (their struct copies hold their wiring), two appended.
    entries = [e for e in gout.get_editor_property('grass_types') if str(e.get_editor_property('name')) not in SCATTER_ENTRIES]
    before = [x.get_name() if x else None for x in mel.get_inputs_for_material_expression(m, gout)][:len(entries)]
    soil = eal.load_asset(FOLDER + '/LGT_GT_SoilScatter')
    litter = eal.load_asset(FOLDER + '/LGT_GT_GrassLitter')
    entries += [props(u.GrassInput(), name='GTSoilScatter', grass_type=soil), props(u.GrassInput(), name='GTGrassLitter', grass_type=litter)]
    gout.set_editor_property('grass_types', entries)
    after = [x.get_name() if x else None for x in mel.get_inputs_for_material_expression(m, gout)]
    assert after[:len(before)] == before, 'grass wiring changed: %s -> %s' % (before, after)
    _con(k, '', gout, 'GTSoilScatter')
    _con(k, 'LitterW', gout, 'GTGrassLitter')
    # Benmore B2 (Art/Unreal/benmore_deform_zones.py): the deform zones' coverage hole and apron, and the bogs' vegetation copy.
    import benmore_deform_zones
    report['deform_zones'] = benmore_deform_zones.attach_deform(m)
    report.update(gravel_pom_switch_moved=moved, grass_entries=[str(e.get_editor_property('name')) for e in entries], painterly_grass_wiring_kept=before,
                  where='between the river-life pass (CP_Source pass-throughs) and the ChannelPilot bed; the bed overrides it')
    return report


def attach(m, report=None, detail=False):
    """attach_surfaces, then (detail=True only) attach_detail; recompiled and saved. Returns a dict for the report."""
    report = attach_surfaces(m, report, save=not detail)
    if detail:
        attach_detail(m, report)
        _compile_save(m)
    report['detail'] = detail
    return report


# ---------------------------------------------------------------- the strips: can they take the function?
def strip_probe(mf, report):
    """A copy of M_VariantsLandscape with the function wired into its emissive: does it compile (the two-collection limit)?"""
    src = '/Game/GrandTour/ArtTests/MudVariants/M_VariantsLandscape'
    probe = '/Game/GrandTour/ArtTests/GroundDetail/Probe/M_VariantsLandscape_MFProbe'
    if eal.does_asset_exist(probe):
        eal.delete_asset(probe)
    m = eal.duplicate_asset(src, probe)
    call = mel.create_material_expression(m, u.MaterialExpressionMaterialFunctionCall, 0, 0)
    call.set_editor_property('material_function', mf)
    one = mel.create_material_expression(m, u.MaterialExpressionConstant3Vector, -200, 0)
    p = mel.create_material_expression(m, u.MaterialExpressionWorldPosition, -200, 100)
    w1 = props(mel.create_material_expression(m, u.MaterialExpressionConstant, -200, 200), r=1.0)
    w0 = props(mel.create_material_expression(m, u.MaterialExpressionConstant, -200, 300), r=0.0)
    for a, pin in [(one, 'Base'), (p, 'WorldPos'), (w1, 'ScrubW'), (w0, 'GrassW')]:
        mel.connect_material_expressions(a, '', call, pin)
    mel.connect_material_property(call, 'Colour', u.MaterialProperty.MP_EMISSIVE_COLOR)
    errors = [str(x) for x in mel.recompile_material(m)]
    stats = mel.get_statistics(m)
    report['strip_probe'] = dict(material=src, errors=errors, pixel=stats.num_pixel_shader_instructions, samplers=stats.num_samplers)
    eal.delete_asset(probe)


# ---------------------------------------------------------------- the editor run
def landscape_layers(land):
    """The paint layers: names, blend, and their weights on a 16 x 16 grid (EditorGetPaintLayerWeightAtLocation)."""
    layers = {}
    comps = list(land.get_components_by_class(u.LandscapeComponent))
    span = 126 * land.get_actor_scale3d().x   # 2016 quads over 16 x 16 components
    origins = [(c, c.get_world_location()) for c in comps]
    for name, setting in dict(land.get_editor_property('target_layers')).items():
        info = setting.get_editor_property('layer_info_obj')
        if not info:
            continue
        blend = None
        for key in ('blend_method', 'no_weight_blend', 'b_no_weight_blend'):
            try:
                blend = str(info.get_editor_property(key))
                break
            except Exception:  # noqa: BLE001
                continue
        vals = []
        for i in range(16):
            for j in range(16):
                x = -124000 + 248000 * (i + 0.5) / 16
                y = -124000 + 248000 * (j + 0.5) / 16
                for c, o in origins:
                    if 0 <= x - o.x < span and 0 <= y - o.y < span:
                        try:
                            vals.append(float(c.editor_get_paint_layer_weight_at_location(u.Vector(x, y, 0), info)))
                        except Exception as e:  # noqa: BLE001
                            vals.append(str(e)[:80])
                        break
        nums = [v for v in vals if isinstance(v, float)]
        layers[str(name)] = dict(info=info.get_path_name(), phys=str(info.get_editor_property('phys_material').get_path_name()) if info.get_editor_property('phys_material') else None,
                                 blend=blend, samples=len(vals), mean=(sum(nums) / len(nums)) if nums else None, nonzero=sum(1 for v in nums if v > 0.01),
                                 error=next((v for v in vals if isinstance(v, str)), None))
    return layers


def road_probes():
    rows = json.loads((ROOT / 'Art/Export/BenmoreRoads/road-manifest.json').read_text())['routes']
    pts = []
    for r in rows:
        n = len(r['points'])
        pts += [(r['points'][i]['x_m'] * 100.0, r['points'][i]['y_m'] * 100.0) for i in (n // 7, 3 * n // 7, 5 * n // 7)]
    return pts


def probe_surface(world, x, y, ignore):
    res = u.GTSurfaceQueryLibrary.trace_landscape_surface(world, u.Vector(x, y, 60000.0), u.Vector(x, y, -60000.0))
    pm = res[0] if isinstance(res, tuple) else res
    return pm.get_name() if pm else None


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    u.EditorPythonScripting.set_keep_python_script_alive(True)
    report = dict(ok=False, level=LEVEL, timings_collected=False)
    state = dict(phase='build', t=time.monotonic())

    def finish(error=None):
        report['ok'] = error is None
        if error:
            report['error'] = error
            u.log_error(error)
        (OUT / 'apply-report.json').write_text(json.dumps(report, indent=1, default=str))
        u.unregister_slate_post_tick_callback(handle)
        u.SystemLibrary.quit_editor()

    def tick(dt):
        try:
            now = time.monotonic()
            if state['phase'] == 'build':
                state['phase'] = 'building'
                world = u.EditorLoadingAndSavingUtils.load_map(LEVEL)
                assert world
                land = next(a for a in u.GameplayStatics.get_all_actors_of_class(world, u.Landscape))
                report['layers'] = landscape_layers(land)
                mpc, report['mpc'] = ensure_mpc()
                mf, report['function'] = build_function(mpc)
                strip_probe(mf, report)
                meshes = scatter_meshes(report)
                grass_types(meshes, report)
                surfaces(report)
                m = eal.load_asset(TERRAIN_MATERIAL)
                assert land.get_editor_property('landscape_material') == m, 'the review landscape wears another material'
                report['attach'] = attach(m, detail='-GTGroundDetail' in u.SystemLibrary.get_command_line())
                report['grass_cull_distance_scale'] = u.SystemLibrary.get_console_variable_float_value('grass.CullDistanceScale')
                report['grass_density_scale'] = u.SystemLibrary.get_console_variable_float_value('grass.DensityScale')
                u.SystemLibrary.execute_console_command(world, 'landscape.RebuildPhysicalMaterial')
                u.SystemLibrary.execute_console_command(world, 'grass.FlushCache')
                state.update(phase='settle', t=now)
            elif state['phase'] == 'settle' and now - state.get('probe', 0) > 15:
                # The landscape renders its physical material after the material's shaders compile (the editor tick runs the tasks
                # and applies them to the collision): wait until road centres across the site trace as gravel, then save.
                state['probe'] = now
                world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
                if 'ignore' not in state:
                    state['ignore'] = [a for a in u.GameplayStatics.get_all_actors_of_class(world, u.Actor) if not isinstance(a, u.LandscapeProxy)]
                got = [probe_surface(world, x, y, state['ignore']) for x, y in road_probes()]
                waited = now - state['t']
                report['physical_material_wait'] = dict(seconds=round(waited), probes=got)
                if all(g in ('PM_Benmore_GravelFirm', 'PM_Benmore_GravelLoose') for g in got) or waited > 1500:
                    state['phase'] = 'saving'
                    report['physical_material_built'] = all(g in ('PM_Benmore_GravelFirm', 'PM_Benmore_GravelLoose') for g in got)
                    assert u.EditorLoadingAndSavingUtils.save_map(world, LEVEL)
                    report['saved'] = True
                    finish()
        except Exception:  # noqa: BLE001
            state['phase'] = 'done'
            finish(traceback.format_exc())

    handle = u.register_slate_post_tick_callback(tick)


if __name__ == '__main__':
    run()
