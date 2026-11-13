import bpy,bmesh,hashlib,json
from pathlib import Path
P=Path('C:/GrandTour/Art/Export/VehicleTools/prado-exterior-v04');f=P/'Prado_Exterior.blend'
assert hashlib.sha256(f.read_bytes()).hexdigest()=='8f3b6c6407683f9a209e9a1344a274b7bd51c190f5e3e8e56bfdac1eb75f4ed2','Generated file changed; preserve manual work'
bpy.ops.wm.open_mainfile(filepath=str(f))
o=bpy.data.objects['Glass | RearWindow'];bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.00001);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
readme='''PRADO — EXTERIOR WORKING REVISION

Source: C:/Users/mille/Downloads/pradotripo.glb
Working scale: uniform 5x; dimensions have not been checked against a real vehicle.

Completed in this pass:
- Source body and 208 retained accessory meshes preserve their vertex positions.
- Separate named collections for body, glazing, road wheels, spare, equipment and underbody.
- Corrected face normals and controlled smoothing on retained components.
- Rebuilt four road wheels and spare, using source centres, width and radius.
- Closed vented wheel dishes, separate tyre carcasses, tread, barrels, hubs and lugs.
- Rebuilt panes from actual body aperture loops, retaining each window outline.
- Fitted six source window dividers to those panes, correcting intermittent protrusion.
- Capped only tiny closed source holes; original GLB and earlier revisions are retained.
- Actual Blender renders reviewed from both sides, front, rear, top, underside and close views.

This is NOT a completed retopology or game-ready asset.
The source body still contains open seams and overconnected edges requiring local repair.
Doors, bonnet, bumpers and fixed shell remain in the original main body mesh.
Interior, complete panel separation, UVs, LODs, collision, rigging, movement checks and
Unreal import are outstanding. Basic materials are for inspection; no textures are supplied.
Workbench preview shows glass as opaque despite its transmission material.

Continue with the saved assembly, keeping the source silhouette as the authority.
Do not replace it with the rejected Porsche generator or a generic SUV profile.
Before an interior: inspect real apertures with glazing hidden, the floor footprint,
wheelhouses and seam coverage. Give the moving panels actual fitted returns.

Evidence and reproducibility:
verification.json: reopened-file source position and static tyre/body checks.
divider-fit.json: scoped fitted divider changes.
../prado-prepared-v02/local-repair-report.json: pane and wheel-web repairs.
Builder scripts are in C:/GrandTour/Art/VehicleTools/ with Prado-specific names.
'''
(P/'README.txt').write_text(readme)
if 'START HERE — Prado status' in bpy.data.texts:bpy.data.texts.remove(bpy.data.texts['START HERE — Prado status'])
bpy.data.texts.new('START HERE — Prado status').write(readme)
bpy.context.scene['asset_status']='Exterior working revision; unfinished topology and interior; not game ready'
bpy.ops.wm.save_as_mainfile(filepath=str(f))
