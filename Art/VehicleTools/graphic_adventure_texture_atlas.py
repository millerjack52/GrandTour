"""Deterministic PBR surface atlas with padded material tiles and real mesh UVs."""
import bpy,numpy as np,math,struct,zlib,json

def png(path,a):
 h,w=a.shape[:2]
 def chunk(t,d):return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
 payload=b''.join(b'\0'+row.tobytes() for row in a)
 path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,6 if a.shape[2]==4 else 2,0,0,0))+chunk(b'IDAT',zlib.compress(payload,6))+chunk(b'IEND',b''))

def pack(parts,palette,out):
 names=sorted(n for n in palette if 'glass' not in n.lower());assert len(names)<=32
 size=512;nx=8;ny=4;w=nx*size;h=ny*size
 base=np.zeros((h,w,4),dtype=np.uint8);orm=np.full((h,w,3),255,dtype=np.uint8)
 rng=np.random.default_rng(412);yy,xx=np.mgrid[0:size,0:size];tiles={}
 for i,name in enumerate(names):
  col=i%nx;row=i//nx;d=palette[name];color=np.array(d['color'][:3]);rough=d['roughness'];metal=d['metallic']
  if name=='Metal':metal=.35
  noise=rng.normal(0,1,(size,size));pattern=noise*.009
  if 'weave' in name:pattern=.075*np.sin(xx*math.pi/3)*np.cos(yy*math.pi/3)+noise*.015
  elif 'carpet' in name:pattern=noise*.10
  elif 'vinyl' in name or 'padded' in name:pattern=noise*.028
  elif 'fittings' in name or name=='Metal':pattern=np.sin(xx*.45)*.026+noise*.009
  linear=np.clip(color[None,None,:]*(1+pattern[:,:,None]),0,1)
  srgb=np.where(linear<=.0031308,linear*12.92,1.055*linear**(1/2.4)-.055)
  pixels=np.empty((size,size,4),dtype=np.uint8);pixels[:,:,:3]=(srgb*255+.5).astype('uint8')
  pixels[:,:,3]=45 if 'ivory markings' in name or 'orange needles' in name else 0
  masks=np.empty((size,size,3),dtype='uint8');masks[:,:,0]=255;masks[:,:,1]=(np.clip(rough+pattern*.4,0,1)*255).astype('uint8');masks[:,:,2]=int(metal*255)
  # PNG rows run down; UV rows run up.
  r=(ny-1-row)*size;base[r:r+size,col*size:(col+1)*size]=pixels;orm[r:r+size,col*size:(col+1)*size]=masks
  tiles[name]={'column':col,'row':row,'roughness':rough,'metallic':metal}
 png(out/'T_GA_BaseColor.png',base);png(out/'T_GA_ORM.png',orm)
 opaque=bpy.data.materials.new('GA_SurfaceAtlas');opaque.use_nodes=True;bs=opaque.node_tree.nodes.get('Principled BSDF')
 for file,channel in [('T_GA_BaseColor.png','Base Color'),('T_GA_ORM.png',None)]:
  image=bpy.data.images.load(str(out/file));tex=opaque.node_tree.nodes.new('ShaderNodeTexImage');tex.image=image
  if channel:opaque.node_tree.links.new(tex.outputs['Color'],bs.inputs[channel])
  else:
   image.colorspace_settings.name='Non-Color';sep=opaque.node_tree.nodes.new('ShaderNodeSeparateColor');opaque.node_tree.links.new(tex.outputs['Color'],sep.inputs[0]);opaque.node_tree.links.new(sep.outputs['Green'],bs.inputs['Roughness']);opaque.node_tree.links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
 glass=bpy.data.materials.new('GA_ClearGlass');glass.use_nodes=True;bs=glass.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.80,.90,.90,1);bs.inputs['Transmission Weight'].default_value=1;bs.inputs['Roughness'].default_value=.065;bs.inputs['IOR'].default_value=1.45
 uvcount=0;glassfaces=0
 for o in parts:
  me=o.data;old=list(me.materials);uv=me.uv_layers.active;assert uv is not None,o.name
  indices=[]
  for p in me.polygons:
   name=old[p.material_index].name
   if 'glass' in name.lower():indices.append(1);glassfaces+=1;continue
   indices.append(0);tile=tiles[name]
   for li in p.loop_indices:
    a,b=uv.data[li].uv;assert math.isfinite(a+b)
    uv.data[li].uv=((tile['column']+.035+a*.93)/nx,(tile['row']+.035+b*.93)/ny);uvcount+=1
  me.materials.clear();me.materials.append(opaque);me.materials.append(glass)
  for p,i in zip(me.polygons,indices):p.material_index=i
 result={'size':[w,h],'tiles':tiles,'uv_loops_mapped':uvcount,'glass_faces':glassfaces,'material_slots':2,'textures':['T_GA_BaseColor.png','T_GA_ORM.png'],'type':'Reusable surface tiles, deliberately shared UV regions; not unique baked damage UVs.'}
 (out/'texture-atlas.json').write_text(json.dumps(result,indent=2));return result
