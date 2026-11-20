"""Count duplicated triangles and coincident geometry without exporting asset data."""

from collections import Counter
import json
from pathlib import Path
import sys

import unreal as u


out = Path(sys.argv[1])
summary = []
for kind in range(3):
    mesh = u.load_asset(f"/Game/GrandTour/ArtTests/LidarStudy/FloraWorld/Canopy/SM_Canopy_{kind}")
    for lod in range(mesh.get_num_lods()):
        for section in range(mesh.get_num_sections(lod)):
            vertices, indices, normals, uv, _ = (
                u.ProceduralMeshLibrary.get_section_from_static_mesh(mesh, lod, section)
            )
            indices = list(indices)
            pos = [v.to_tuple() for v in vertices]
            keys = [(p, n.to_tuple(), t.to_tuple()) for p, n, t in zip(pos, normals, uv)]
            faces = Counter()
            split_tris = Counter()
            degenerate = 0
            for i in range(0, len(indices), 3):
                a, b, c = indices[i : i + 3]
                tri = tuple(sorted((pos[a], pos[b], pos[c])))
                degenerate += len(set(tri)) != 3
                faces[tri] += 1
                split_tris[tuple(sorted((keys[a], keys[b], keys[c])))] += 1
            summary.append(
                dict(
                    mesh=mesh.get_name(),
                    lod=lod,
                    section=section,
                    vertices=len(vertices),
                    unique_positions=len(set(pos)),
                    unique_position_normal_uv=len(set(keys)),
                    triangles=len(indices) // 3,
                    coincident_faces=sum(v - 1 for v in faces.values()),
                    coincident_position_normal_uv_faces=sum(v - 1 for v in split_tris.values()),
                    degenerate_positions=degenerate,
                )
            )
(out / "tree-mesh-counts.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
