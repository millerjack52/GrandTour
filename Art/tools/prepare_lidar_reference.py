from pathlib import Path
import xml.etree.ElementTree as ET,json
import numpy as np
from pyproj import Transformer
from shapely.geometry import LineString,Polygon,box,mapping
from shapely.ops import polygonize,unary_union,linemerge
from rasterio.features import rasterize
from rasterio.transform import from_origin
from PIL import Image,ImageDraw
OUT=Path('Art/Export/LidarStudy');D=OUT/'Reference'
nodes={};ways={};rels={}
for f in D.glob('*.osm'):
 root=ET.parse(f).getroot()
 for n in root.findall('node'):nodes[n.attrib['id']]=(float(n.attrib['lon']),float(n.attrib['lat']))
 for w in root.findall('way'):ways[w.attrib['id']]=w
 for r in root.findall('relation'):rels[r.attrib['id']]=r
tr=Transformer.from_crs(4326,2193,always_xy=True)
def coords(w):
 ll=[nodes[n.attrib['ref']] for n in w.findall('nd')];e,n=tr.transform(*zip(*ll));return [(x-1197144.5,4865011.5-y) for x,y in zip(e,n)]
def tags(a):return {v.attrib['k']:v.attrib['v'] for v in a.findall('tag')}
bounds=box(-1818.5,-1850.5,1818.5,1850.5);forests=[];scrubs=[];roads=[];rivers=[];ponds=[]
for r in rels.values():
 t=tags(r)
 if t.get('natural') not in ['wood','scrub']:continue
 by={k:[] for k in ['outer','inner']}
 for m in r.findall('member'):
  if m.attrib['type']=='way' and m.attrib['ref'] in ways:by[m.attrib.get('role') or 'outer'].append(LineString(coords(ways[m.attrib['ref']])))
 outer=unary_union(list(polygonize(unary_union(by['outer']))));inner=unary_union(list(polygonize(unary_union(by['inner']))))
 g=outer.difference(inner).intersection(bounds)
 (forests if t['natural']=='wood' else scrubs).append(g)
for w in ways.values():
 t=tags(w)
 if len(w.findall('nd'))<2:continue
 c=coords(w);line=LineString(c)
 if t.get('highway'):
  g=line.intersection(bounds)
  if not g.is_empty:roads.append((t.get('name','Road'),g))
 if t.get('waterway') in ['river','stream']:
  g=line.intersection(bounds)
  if not g.is_empty:rivers.append((t.get('name','Stream'),g))
 if c[0]!=c[-1] or len(c)<4:continue
 g=Polygon(c).buffer(0).intersection(bounds)
 if t.get('natural')=='wood' or t.get('landuse')=='forest':forests.append(g)
 if t.get('natural') in ['scrub','heath']:scrubs.append(g)
 if t.get('natural')=='water':ponds.append(g)
forest=unary_union(forests);scrub=unary_union(scrubs)
features=[]
for name,items in [('forest',[forest]),('scrub',[scrub]),('pond',ponds)]:
 for g in items:
  if not g.is_empty:features.append(dict(type='Feature',properties=dict(kind=name),geometry=mapping(g)))
for kind,items in [('road',roads),('river',rivers)]:
 for name,g in items:features.append(dict(type='Feature',properties=dict(kind=kind,name=name),geometry=mapping(g)))
(D/'aligned-features.json').write_text(json.dumps(dict(type='FeatureCollection',coordinate_system='local metres: east positive X, south positive Y, NZTM centre E1197144.5 N4865011.5',features=features)))
N=2048;step=3700/N
# Raster y is south-positive; use an affine with positive row step.
from affine import Affine
A=Affine(step,0,-1850,0,step,-1850)
fm=rasterize([(forest,1)],out_shape=(N,N),transform=A,dtype='uint8');sm=rasterize([(scrub,1)],out_shape=(N,N),transform=A,dtype='uint8')
Image.fromarray(fm*255).save(D/'forest-mask.png');Image.fromarray(sm*255).save(D/'scrub-mask.png')
H=np.fromfile(OUT/'height.r16',dtype='<u2').reshape(2017,2017).astype(float)/65535*327.68
H=np.array(Image.fromarray(H.astype('float32')).resize((N,N)))
dy,dx=np.gradient(H,step);shade=np.clip(.78-dx*.4-dy*.3,.25,1)
rgb=np.where(fm[...,None]>0,np.array([.12,.3,.19]),np.array([.55,.63,.35]))*shade[...,None]
im=Image.fromarray(np.uint8(np.clip(rgb,0,1)*255));d=ImageDraw.Draw(im)
def lines(g):return [g] if g.geom_type=='LineString' else list(g.geoms)
summary=[]
for kind,items,color in [('road',roads,'#e6c28a'),('river',rivers,'#61c9ee')]:
 for name,g in items:
  for a in lines(g):
   ps=[((x+1850)/step,(y+1850)/step) for x,y in a.coords];d.line(ps,fill=color,width=4);d.text(ps[len(ps)//2],name,fill='white')
  summary.append(dict(kind=kind,name=name,length_m=g.length,bounds=g.bounds))
for g in ponds:
 if not g.is_empty:
  for a in ([g] if g.geom_type=='Polygon' else g.geoms):d.polygon([((x+1850)/step,(y+1850)/step) for x,y in a.exterior.coords],fill='#61c9ee')
im.resize((1100,1100)).save(D/'aligned-plan.png')
print(json.dumps(dict(forest_coverage=float(fm.mean()),scrub_coverage=float(sm.mean()),features=summary,ponds=len(ponds)),indent=2))
