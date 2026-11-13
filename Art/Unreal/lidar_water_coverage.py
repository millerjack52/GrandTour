"""Clip the static river against final built ground, not pre-road elevations.

The live river uses the same bounded source-level envelope. No landscape edits.
"""
import array,hashlib,json,math,struct
from pathlib import Path
import unreal as u
from lidar_grounding import GroundSampler
from benmore_river_life_materials import props
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/LidarStudy/Place'
BASE='/Game/GrandTour/ArtTests/LidarStudy';VERSION='LP6-coverage-2'

def install(author,force=False):
 raw=(OUT/'River-domain.bin').read_bytes();key=hashlib.sha256(raw+str(author.output_digest).encode()+VERSION.encode()).hexdigest()
 report_path=OUT/'watercoverage.json'
 if not force and report_path.exists():
  prior=json.loads(report_path.read_text())
  mesh=u.load_asset(BASE+'/SM_RiverWater')
  if prior.get('key')==key and mesh and u.EditorAssetLibrary.get_metadata_tag(mesh,'LP6CoverageKey')==key:return prior
 _,nx,ny,_,_,ox,oy,cell=struct.unpack('<5i3f',raw[:32]);data=array.array('f');data.frombytes(raw[32:-1])
 assert cell==200,'Review subdivision budget for another source resolution'
 wet=[i for i in range(nx*ny) if data[i*4+1]>.005]
 cells=set()
 for i in wet:
  x,y=(i%nx)*2,(i//nx)*2
  cells.update((x+dx,y+dy) for dx in range(-3,3) for dy in range(-3,3))
 ground=GroundSampler(author);cache={}
 def vertex(x,y):
  if (x,y) in cache:return cache[x,y]
  qx,qy=x*.5,y*.5;cx,cy=math.floor(qx),math.floor(qy);fx,fy=qx-cx,qy-cy
  total=level=0
  for dx,dy,w in [(0,0,(1-fx)*(1-fy)),(1,0,fx*(1-fy)),(0,1,(1-fx)*fy),(1,1,fx*fy)]:
   xx,yy=cx+dx,cy+dy
   if 0<=xx<nx and 0<=yy<ny:
    i=(yy*nx+xx)*4
    if data[i+1]>.005:total+=w;level+=data[i]*w
  supported=total>=.5;envelope=10000
  if supported:level/=total
  else:
   best=float('inf');found=None
   for yy in range(max(0,cy-2),min(ny,cy+3)):
    for xx in range(max(0,cx-2),min(nx,cx+3)):
     i=(yy*nx+xx)*4;d=((xx-qx)**2+(yy-qy)**2)*cell**2
     if data[i+1]>.005 and d<=best:best=d;found=i
   supported=found is not None
   level=data[found] if supported else (level/total if total else 0)
   envelope=250-math.sqrt(best) if supported else -10000
  wx,wy=ox+cell*.5+x*100,oy+cell*.5+y*100
  depth=min(level-ground.height(wx,wy)-.2,envelope) if supported else -10000
  cache[x,y]=((wx,wy,level),depth);return cache[x,y]
 vertices=[];faces=[];indices={}
 def index(p):
  key=tuple(round(v,3) for v in p)
  if key not in indices:indices[key]=len(vertices)+1;vertices.append(key)
  return indices[key]
 for x,y in sorted(cells):
  corners=[vertex(x,y),vertex(x+1,y),vertex(x,y+1),vertex(x+1,y+1)]
  for ids in [(0,2,1),(1,2,3)]:
   poly=[corners[i] for i in ids];clip=[]
   for a,b in zip(poly,poly[1:]+poly[:1]):
    if a[1]>0:clip.append(a[0])
    if (a[1]>0)!=(b[1]>0):
     t=a[1]/(a[1]-b[1]);clip.append(tuple(a[0][k]+(b[0][k]-a[0][k])*t for k in range(3)))
   if len(clip)>=3:
    ii=[index(p) for p in clip]
    faces.extend((ii[0],ii[j],ii[j+1]) for j in range(1,len(ii)-1))
 assert 100000<len(faces)<400000,('Unexpected river geometry budget',len(faces))
 path=OUT/'River-LP6.obj'
 path.write_text('\n'.join(['v %.3f %.3f %.3f'%(x,-y,z) for x,y,z in vertices]+['f %d %d %d'%f for f in faces]))
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.OBJ 0')
 ui=props(u.FbxImportUI(),import_mesh=True,import_materials=False,import_textures=False,import_as_skeletal=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
 props(ui.static_mesh_import_data,combine_meshes=True,auto_generate_collision=False,convert_scene=False,convert_scene_unit=False,generate_lightmap_u_vs=False)
 task=props(u.AssetImportTask(),filename=str(path),destination_path=BASE,destination_name='SM_RiverWater',automated=True,replace_existing=True,save=True,options=ui)
 u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);mesh=u.load_asset(BASE+'/SM_RiverWater');assert mesh
 mesh.set_material(0,u.load_asset(BASE+'/M_RiverWater'));u.get_editor_subsystem(u.StaticMeshEditorSubsystem).remove_collisions(mesh);u.EditorAssetLibrary.set_metadata_tag(mesh,'LP6CoverageKey',key);assert u.EditorAssetLibrary.save_loaded_asset(mesh)
 result=dict(ok=True,version=VERSION,key=key,triangles=len(faces),vertices=len(vertices),ground_samples=len(cache),source_domain_sha=hashlib.sha256(raw).hexdigest(),ground_digest=str(author.output_digest),margin_cm=250,grid_cm=100)
 report_path.write_text(json.dumps(result,indent=2));return result

if __name__=='__main__':
 import traceback
 qa=ROOT/'Saved/LidarAuthoringQA/LP6';result={'ok':False}
 try:
  les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(BASE+'/L_LidarStudy')
  author=next(a for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors() if isinstance(a,u.GTProceduralGround))
  result=install(author)
  from lidar_level_polish import water_material
  water_material(u.load_asset(BASE+'/M_RiverWater'))
 except Exception:result={'ok':False,'error':traceback.format_exc()};u.log_error(result['error'])
 (qa/'coverage.json').write_text(json.dumps(result,indent=2));u.SystemLibrary.quit_editor()
