import unreal as u
import json,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BigMountain';report={'ok':False}
try:
 mesh=u.load_asset('/Game/GrandTour/ArtTests/BigMountain/SM_Water');d=mesh.get_static_mesh_description(0);assert d
 report['bounds']=str(mesh.get_bounds());report['vertices']=[list(d.get_vertex_position(u.VertexID(i)).to_tuple()) for i in range(12)]
 probe=json.loads((OUT/'water-probe.json').read_text());x,y=probe['point'];near=[]
 for i in range(d.get_vertex_count()):
  p=d.get_vertex_position(u.VertexID(i));dist=(p.x-x)**2+(p.y-y)**2
  if dist<2000**2:near.append([dist,p.x,p.y,p.z])
 report['nearest']=sorted(near)[:12];report['ok']=True
except Exception:report['error']=traceback.format_exc()
(OUT/'audit.json').write_text(json.dumps(report,indent=2));u.SystemLibrary.quit_editor()
