"""Small cupped near leaves; deterministic CD branch design, bounded LOD0 cost."""
import bpy,sys,math,random,json
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import build_lidar_forest as F
L=F.L;B=F.B
OUT=Path(__file__).resolve().parents[1]/'Export/LidarStudy/LeafGeometry'
FACTORS={'Mature':(1.65,1.48),'Pole':(2.,1.65),'Edge':(1.40,1.32)}
old_bough=F.bough;active_scale=1.;lengths=[];folds=[]
def old_broad(g,c,r,seed,lod,pole=False):
 start=len(g.v);old_bough(g,c,r,seed,lod,pole)
 for i in range(start,len(g.v)):
  p=g.v[i]-c;g.v[i]=c+Vector((p.x*active_scale,p.y*active_scale,p.z))
def small_bough(g,c,r,seed,lod,pole=False):
 rng=random.Random(seed);original_count=30 if pole else 84
 golden=math.pi*(3-math.sqrt(5));phase=rng.uniform(0,math.tau)
 for j in range(original_count):
  z=1-2*(j+.5)/original_count;az=j*golden+phase;q=math.sqrt(max(0,1-z*z));n=Vector((q*math.cos(az),q*math.sin(az),z))
  ripple=1+.12*math.sin(az*3+seed)+.09*math.sin(az*5+z*4)
  centre=c+Vector((n.x*r.x*active_scale,n.y*r.y*active_scale,n.z*r.z))*ripple*rng.uniform(.60,1.)
  if j%2:continue
  for k in range(12):
   rr=random.Random(seed+j*1597+k*7907)
   # Separate leaves occupy a layered twig-sized volume, not one shared plane.
   p=centre+B.jit(rr,.34 if not pole else .22)
   normal=(n*.40+L.Z*.62+B.jit(rr,.52)).normalized()
   axis=L.rot(L.perp(normal),normal,rr.uniform(0,math.tau));side=normal.cross(axis).normalized()
   length=rr.uniform(.13,.28)*(1.12 if k%7==0 else 1.);width=length*rr.uniform(.40,.67)
   cup=rr.uniform(.07,.16)*length;curl=rr.uniform(-.15,.18)*length;twist=rr.uniform(-.13,.13)*length
   # Six boundary vertices / four triangles: taper, real cup, curled tip and twist.
   uv=[(0,.5),(.30,0),(.70,.07),(1,.5),(.70,.93),(.30,1)]
   verts=[]
   for t,v in uv:
    s=(v-.5)*2
    h=cup*s*s*math.sin(math.pi*t)+curl*t*t+twist*s*t
    verts.append(p+axis*(t-.45)*length+side*s*width*.5+normal*h)
   shade=L.clamp(.47+.20*n.z+rr.uniform(-.14,.14));colour=L.mix(B.LEAF_DARK,B.LEAF_LIGHT,shade)
   tint=rr.uniform(.86,1.13);warm=rr.uniform(-.07,.07)
   cols=[(min(.95,colour[0]*tint*(1+warm)),min(.95,colour[1]*tint),min(.95,colour[2]*tint*(1-warm)))]*6
   faces=[(0,1,5),(1,2,5),(2,4,5),(2,3,4)]
   if (verts[1]-verts[0]).cross(verts[5]-verts[0]).dot(normal)<0:faces=[tuple(reversed(f)) for f in faces]
   g.add(verts,faces,cols,uv,1);g.counts['leaves']+=1;lengths.append(length);folds.append(cup/length)
 g.counts['clusters']+=1
def main():
 global active_scale
 OUT.mkdir(parents=True,exist_ok=True);bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
 mats=L.plant_materials();mats[1].name='M_LeafGeometry';rows=[]
 for kind,(reach,lobe) in FACTORS.items():
  lengths.clear();folds.clear();active_scale=lobe;F.SPECS[kind]['radius']*=reach
  F.bough=old_broad;D,n=F.design(kind);g,_=B.emit(D,0,1000000);scale=F.SPECS[kind]['height']/max(v.z for v in g.v)
  F.bough=small_bough;g,_=B.emit(D,0,1000000);g.v=[v*scale for v in g.v]
  ob,dropped=L.to_object(g,'SM_LG_'+kind+'_LOD0',mats,[0,1])
  # Smooth each independent leaf; disconnected leaves do not share normals.
  for poly in ob.data.polygons:
   if poly.material_index==1:poly.use_smooth=True
  ob.data.update();ob.data.calc_loop_triangles();tri=len(ob.data.loop_triangles)
  assert tri<70000 if kind!='Pole' else tri<24000,(kind,tri)
  L.export(ob,out=OUT)
  row=dict(kind=kind,name=ob.name,triangles=tri,leaves=g.counts['leaves'],length_cm=[round(min(lengths)*scale*100,2),round(sum(lengths)/len(lengths)*scale*100,2),round(max(lengths)*scale*100,2)],cup_fraction=[min(folds),max(folds)],dropped_degenerate=dropped,scale=scale)
  rows.append(row);print(row,flush=True);ob.hide_set(True);ob.hide_render=True
 (OUT/'manifest.json').write_text(json.dumps(dict(ok=True,models=rows,scope='LOD0 only; 4 triangles per cupped leaf'),indent=2))
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'LeafGeometry.blend'))
if __name__=='__main__':main()
