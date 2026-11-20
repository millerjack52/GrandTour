"""Export counted UV footprints of rendered LiDAR leaf triangles for a local coverage audit."""

from collections import Counter
import os
from pathlib import Path
import struct
from zipfile import ZIP_DEFLATED, ZipFile

import unreal as u


output = Path(os.environ["GT_LIDAR_FOOTPRINT_FILE"])
with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
    for kind in range(3):
        mesh = u.load_asset(
            f"/Game/GrandTour/ArtTests/LidarStudy/FloraWorld/Canopy/SM_Canopy_{kind}"
        )
        for lod in (1, 2):
            # The live map binds its painted leaf material to slot one on all three
            # species; the render-section audit verifies the two sections on these LODs.
            assert mesh.get_num_sections(lod) == 2
            vertices, indices, _, uv, _ = u.ProceduralMeshLibrary.get_section_from_static_mesh(
                mesh, lod, 1
            )
            points = [v.to_tuple() for v in uv]
            ids = list(indices)
            counts = Counter()
            areas = {}
            for first in range(0, len(ids), 3):
                a, b, c = ids[first : first + 3]
                tri = tuple(sorted([points[a], points[b], points[c]]))
                counts[tri] += 1
                pa, pb, pc = vertices[a], vertices[b], vertices[c]
                area = (pb - pa).cross(pc - pa).length() * 0.5
                areas[tri] = areas.get(tri, 0.0) + area
            with archive.open(f"tree{kind}-lod{lod}.bin", "w") as out:
                for tri, count in counts.items():
                    out.write(struct.pack("<6fId", *tri[0], *tri[1], *tri[2], count, areas[tri]))
            u.log(
                f"GT_LEAF_FOOTPRINT mesh={kind} lod={lod} triangles={len(ids) // 3} unique={len(counts)}"
            )
u.log("GT_FOOTPRINT_READY")
