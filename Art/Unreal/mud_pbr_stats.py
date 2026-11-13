"""MudRunner MRP item 4 (docs/MUDRUNNER_LESSONS_PLAN.md MRP): static shader stats of every material that draws mud.

Not timing (the owner measures performance): MaterialEditingLibrary.get_statistics, a synchronous compile at the editor's
shader platform, per material: pixel and vertex instruction counts, samplers, pixel texture samples. The counts are the
compiler's static ones (a dynamic branch's or a loop's body counts once, whether or not it runs).
Run with -RenderOffScreen (a NullRHI run compiles no HLSL) and GT_STATS_TAG set (before / after):
writes Art/Export/MudVariants/shader-stats-<tag>.json and quits.
"""
import json
import os
import traceback
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
OUT = ROOT / 'Art/Export/MudVariants'
OUT.mkdir(parents=True, exist_ok=True)
TAG = os.environ.get('GT_STATS_TAG', 'now')
MATERIALS = [
    ('mud ground', '/Game/GrandTour/Materials/M_GT_Mud'),
    ('rut water', '/Game/GrandTour/Materials/M_GT_MudWater'),
    ('car body', '/Game/GrandTour/Materials/M_GT_Vehicle'),
    ('tyre', '/Game/GrandTour/Materials/M_GT_Tyre'),
    ('glass', '/Game/GrandTour/Materials/M_GT_Glass'),
    ('MF_MudCover user', '/Game/GrandTour/Materials/M_GT_Landscape'),
    ('MF_MudCover user', '/Game/GrandTour/Materials/M_GT_Environment'),
    ('MF_MudCover user', '/Game/GrandTour/ArtTests/LiveMudDrive/M_LiveLandscape'),
    ('MF_MudCover user', '/Game/GrandTour/ArtTests/MudVariants/M_VariantsLandscape'),
    ('splat decal', '/Game/GrandTour/Mud/Splats/M_GT_MudSplatDecal'),
    ('clods', '/Game/GrandTour/Materials/M_GT_Clod'),
]
report = dict(tag=TAG, ok=False, rows=[])
try:
    mel = u.MaterialEditingLibrary
    for role, path in MATERIALS:
        mat = u.EditorAssetLibrary.load_asset(path)
        if mat is None:
            report['rows'].append(dict(role=role, material=path, missing=True))
            continue
        s = mel.get_statistics(mat)
        report['rows'].append(dict(role=role, material=path, pixel_instructions=s.num_pixel_shader_instructions,
                                   vertex_instructions=s.num_vertex_shader_instructions, samplers=s.num_samplers,
                                   pixel_texture_samples=s.num_pixel_texture_samples, vertex_texture_samples=s.num_vertex_texture_samples,
                                   interpolator_scalars=s.num_interpolator_scalars))
        u.log('MUD_PBR_STATS %s %s: %s' % (TAG, path, report['rows'][-1]))
    # MRP follow-up 3 (the owner's 6 GB card): the textures every mud and snow material reads, and their whole video-memory size from
    # the built platform data - every mip of every slice in the built format (UGTMudArtLibrary::TextureAllMipsBytes); MRP follow-up
    # 2's Blueprint_GetMemorySize reported only what was resident (4 KB for an array nothing had drawn). Not timing.
    groups = {
        'mud': ['/Game/GrandTour/Materials/M_GT_Mud', '/Game/GrandTour/Materials/M_GT_Clod', '/Game/GrandTour/Materials/M_GT_MudWater',
                '/Game/GrandTour/Materials/M_GT_Landscape', '/Game/GrandTour/ArtTests/MudVariants/M_VariantsLandscape',
                '/Game/GrandTour/ArtTests/LiveMudDrive/M_LiveLandscape', '/Game/GrandTour/Mud/Splats/M_GT_MudSplatDecal',
                '/Game/GrandTour/Materials/M_GT_Vehicle', '/Game/GrandTour/Materials/M_GT_Tyre'],
        'snow': ['/Game/GrandTour/Materials/M_GT_Snow', '/Game/GrandTour/Materials/M_GT_Clod_Snow',
                 '/Game/GrandTour/ArtTests/LiveSnowDrive/M_SnowLandscape'],
    }
    loose = ['/Game/GrandTour/ArtTests/MudStyle/' + n for n in ('TA_MS_BogORH', 'TA_MS_BogOR', 'TA_MS_BogHeightPOM', 'TA_MS_BogHeightPOM8',
                                                                 'TA_MS_BogRough', 'TA_MS_BogHeight')]
    report['texture_groups'] = {}
    sized = {}

    def size_of(tex):
        path = tex.get_path_name().split('.')[0]
        if path not in sized:
            fmt = ''
            n, fmt = u.GTMudArtLibrary.texture_all_mips_bytes(tex)
            sized[path] = dict(texture=path, cls=tex.get_class().get_name(), format=str(fmt), bytes=int(n),
                               size=[int(tex.blueprint_get_size_x()), int(tex.blueprint_get_size_y())] if hasattr(tex, 'blueprint_get_size_x') else None)
        return sized[path]

    for group, mats in groups.items():
        seen, rows = set(), []
        for path in mats:
            mat = u.EditorAssetLibrary.load_asset(path)
            if mat is None:
                rows.append(dict(material=path, missing=True))
                continue
            for tex in mel.get_used_textures(mat):
                info = size_of(tex)
                if info['texture'] not in seen:
                    seen.add(info['texture'])
                    rows.append(dict(info, first_used_by=path.split('/')[-1]))
        total = sum(r.get('bytes', 0) for r in rows)
        report['texture_groups'][group] = dict(textures=rows, total_bytes=total, total_mb=round(total / 1048576.0, 1))
        u.log('MUD_PBR_STATS %s textures %s: %.1f MB over %d' % (TAG, group, total / 1048576.0, len(rows)))
    report['loose_arrays'] = []
    for path in loose:
        tex = u.EditorAssetLibrary.load_asset(path)
        report['loose_arrays'].append(size_of(tex) if tex else dict(texture=path, missing=True))
    report['ok'] = True
except Exception:
    report['error'] = traceback.format_exc()
    u.log_error(report['error'])
finally:
    (OUT / ('shader-stats-%s.json' % TAG)).write_text(json.dumps(report, indent=2))
    u.SystemLibrary.quit_editor()
