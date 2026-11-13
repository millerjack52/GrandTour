"""RS4: world-space rock projection and broken soil/moss transitions on steep ground."""
from pathlib import Path
import unreal as u
import sys,json,hashlib,shutil,time,traceback,gc
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import lidar_road_style as roads
BASE=roads.BASE;OUT=roads.OUT;QA=ROOT/'Saved/LidarAuthoringQA/RS4';VERSION='rs4-2'
mel=u.MaterialEditingLibrary;assets=u.EditorAssetLibrary
CODE=roads.NOISE.replace('RS2Field','RS4Field').replace('rs2','rs4')+'''
float4 s=Texture2DSampleLevel(Style,StyleSampler,saturate((P.xy+185000)/370000),0);
// Derive the actual geometric face normal, not the old top-down soil detail normal.
float3 dx=ddx(P),dy=ddy(P);
float3 face=abs(normalize(cross(dx,dy)));
float3 w=pow(max(face,.001),4.);w/=max(w.x+w.y+w.z,.0001);
[branch] if(s.a<.001)return Native;
float3 xy=Texture2DSampleGrad(Rock,RockSampler,P.xy/550.,dx.xy/550.,dy.xy/550.).rgb;
float3 yz=Texture2DSampleGrad(Rock,RockSampler,P.yz/280.,dx.yz/280.,dy.yz/280.).rgb;
float3 xz=Texture2DSampleGrad(Rock,RockSampler,P.xz/280.,dx.xz/280.,dy.xz/280.).rgb;
float3 projected=pow(max(xy*w.z+yz*w.x+xz*w.y,0),2.2);
float3 old=pow(max(xy,0),2.2);
float steep=1-smoothstep(.70,.93,face.z);
// Larger colour patches soften the high-contrast photographic grain.
float broad=.55*rs4.n(P.xy/850.)+.45*rs4.n(P.xz/1100.+17.);
float detail=.5*rs4.n(P.yz/160.)+.5*rs4.n(P.xz/220.);
float lum=dot(projected,float3(.2126,.7152,.0722));
float3 stone=float3(.235,.220,.185)*clamp(.72+lum*1.6,.75,1.30);
stone=lerp(stone,projected*float3(1.14,1.06,.90),.66);
stone*=lerp(.90,1.08,broad);
// Soft irregular pockets of earth and moss sit among exposed faces.
float soil=smoothstep(.40,.72,broad)*(.25+.35*face.z);
float3 earth=float3(.155,.125,.082)*lerp(.85,1.15,detail);
stone=lerp(stone,earth,soil);
float pocket=.60*rs4.n(P.xy/430.+9.)+.40*rs4.n(P.yz/360.-11.);
float moss=smoothstep(.45,.72,pocket)*smoothstep(.12,.68,face.z)*.62;
float3 mossColour=lerp(float3(.074,.115,.045),float3(.15,.18,.075),detail);
stone=lerp(stone,mossColour,moss);
float3 r=lerp(old,stone,steep);
// Retain the existing atlas mask and upstream road/soil precedence.
return saturate(lerp(Native,r,s.a));
'''
def rocknode(m):
 rows=[n for n in mel.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom) and 'lerp(Native,r,s.a)' in str(n.get_editor_property('code'))]
 assert len(rows)==1,(m.get_name(),len(rows));return rows[0]
def protected(m):
 result=roads.protected(m)
 # Unlike RS2, protect the two road colour programs as well.
 result['other_shader_programs']={n.get_name():hashlib.sha256(str(n.get_editor_property('code')).encode()).hexdigest() for n in mel.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom) and n!=rocknode(m)}
 return result
def apply():
 rows=[]
 for name in ('Terrain','Detail'):
  m=u.load_asset(BASE+'/M_'+name);n=rocknode(m);before=protected(m);count=len(mel.get_material_expressions(m))
  if not assets.get_metadata_tag(m,'RS4OriginalRock'):assets.set_metadata_tag(m,'RS4OriginalRock',str(n.get_editor_property('code')))
  n.set_editor_property('code',CODE)
  assert protected(m)==before and len(mel.get_material_expressions(m))==count
  assert not mel.recompile_material(m);assets.set_metadata_tag(m,'RS4Version',VERSION);assert assets.save_loaded_asset(m,False)
  rows.append(dict(material=name,protected=before,nodes=count,code_sha256=hashlib.sha256(CODE.encode()).hexdigest()))
 return rows
def validate():
 rows=[]
 for name in ('Terrain','Detail'):
  m=u.load_asset(BASE+'/M_'+name);assert str(rocknode(m).get_editor_property('code'))==CODE;assert assets.get_metadata_tag(m,'RS4Version')==VERSION
  rows.append(dict(material=name,protected=protected(m),nodes=len(mel.get_material_expressions(m)),code_sha256=hashlib.sha256(CODE.encode()).hexdigest()))
 return rows
if __name__=='__main__':
 QA.mkdir(parents=True,exist_ok=True);report=dict(ok=False,version=VERSION);busy=False;deadline=0
 def save():(QA/'install.json').write_text(json.dumps(report,indent=2))
 def run():
  content=ROOT/'Content/GrandTour/ArtTests/LidarStudy';backup=ROOT/'Saved/LidarAuthoringBackups'/('RS4-'+str(time.time_ns()));backup.mkdir(parents=True)
  for name in ('M_Terrain','M_Detail'):shutil.copy2(content/(name+'.uasset'),backup/(name+'.uasset'))
  report.update(backup=str(backup),map_sha256=roads.digest(content/'L_LidarStudy.umap'));save()
  report['materials']=apply();save();yield 5
  assert apply()==report['materials'];yield 5
  assert validate()==report['materials'];assert roads.digest(content/'L_LidarStudy.umap')==report['map_sha256']
  report.update(ok=True,idempotent=True,map_unchanged=True);save()
  (OUT/'slope-style.json').write_text(json.dumps(dict(version=VERSION,report=str(QA/'install.json'))));yield 3
 steps=run()
 def tick(dt):
  global busy,deadline,steps
  if busy:return
  busy=True
  try:
   if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
  except StopIteration:u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
  except Exception:
   report.update(ok=False,error=traceback.format_exc());save();u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
  finally:busy=False
 u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
