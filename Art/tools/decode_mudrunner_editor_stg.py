"""Strict partial STG decoder traced through native TerrainSTGSave 0x14029ca70.

Decodes the reference's complete block records, terrain/mud/water data, plant
records and grass ranges. Superblock textures and the trailing global sections
are not interpreted. The only accepted version and empty truck/locator/geometry
sections are those used by the owned experiments. Source STGs stay read-only.
"""
from pathlib import Path
import struct, json, hashlib, collections, io, math
import numpy as np
from PIL import Image

class Reader:
    def __init__(self,b):self.b=b;self.p=0
    def raw(self,n):
        assert 0<=n<=len(self.b)-self.p,(self.p,n,len(self.b))
        b=self.b[self.p:self.p+n];self.p+=n;return b
    def get(self,f):return struct.unpack('<'+f,self.raw(struct.calcsize('<'+f)))
    def u32(self):return self.get('I')[0]
    def string(self):
        n=self.get('H')[0];assert 1<=n<512
        b=self.raw(n);assert b[-1]==0;return b[:-1].decode('ascii')

def decode(path):
    b=Path(path).read_bytes();r=Reader(b);version,guid=r.get('II')
    assert version==0x0133ed03,hex(version)
    assert r.u32()==0,'Trucks not decoded'
    drive=r.u32();assert r.u32()==0,'Locators not decoded'
    size=r.get('2f');origin=r.get('2f');mutator=r.string()
    materials=[(r.string(),r.string()) for _ in range(r.u32())]
    overlays=[r.string() for _ in range(r.u32())]
    grasses={}
    for _ in range(r.u32()):
        name=r.string();n=r.u32();grasses[name]=r.raw(n)
    brands=[r.string() for _ in range(r.u32())]
    assert r.u32()==0,'Geometry overlays not decoded'
    chunks=[];plants=[]
    for k in range(r.u32()):
        n=r.u32();chunks.append(n)
        for _ in range(n):
            brand=r.get('H')[0];assert brand<len(brands)
            pos=r.get('3f');packed=r.raw(8)
            assert all(np.isfinite(pos)) and abs(pos[0])<size[0] and abs(pos[2])<size[1]
            plants.append(dict(brand=brands[brand],native_xyz=list(pos),packed=packed.hex(),chunk=k))
    waters=[(r.string(),r.string()) for _ in range(r.u32())]
    bx,bz=r.get('II');assert (bx*16,bz*16)==size
    return dict(version=version,guid=guid,sha256=hashlib.sha256(b).hexdigest(),size=list(size),origin=list(origin),mutator=mutator,materials=materials,overlays=overlays,grass_buffers={k:dict(bytes=len(v),sha256=hashlib.sha256(v).hexdigest()) for k,v in grasses.items()},brands=brands,plant_chunks=chunks,plants=plants,plant_counts=dict(collections.Counter(p['brand'] for p in plants)),waters=waters,blocks=[bx,bz],block_payload_offset=r.p),grasses

def blocks(path):
    meta,_=decode(path);r=Reader(Path(path).read_bytes());r.p=meta['block_payload_offset'];bx,bz=meta['blocks']
    assert bx%2==bz%2==0,'Superblock edge layout not established'
    for _ in range(bx*bz//4):r.raw(r.u32())
    result=[]
    for i in range(bx*bz):
        blob=r.raw(r.u32());q=Reader(blob);flags=q.get('B')[0];xz=q.get('2f');size=q.get('2f');corners=q.get('4f');bounds=q.get('2f');q.raw(48)
        def tex():
            d=q.raw(q.u32());assert d[:4]==b'DDS '
            return np.array(Image.open(io.BytesIO(d)).convert('RGBA'))
        bm=tex();assert bm.shape==(32,32,4)
        overlay=q.get('B')[0];ov=None
        if overlay!=255:uv=q.get('4f');ov=tex()
        mud=bool(q.get('B')[0]);control=relief=None
        if mud:
            control=np.frombuffer(q.raw(625),'u1').reshape(25,25).copy()
            relief=np.frombuffer(q.raw(32768),'u1').reshape(128,128,2).copy()
        water=bool(q.get('B')[0]);wm=wd=None
        if water:
            wi=q.get('B')[0];wm=tex();wd=np.frombuffer(q.raw(200),'<f4').copy();q.raw(192)
        plant_indices=[q.u32() for _ in range(q.u32())]
        geometry_refs=q.raw(q.u32()*6)
        grass_ranges=[q.get('HI16I') for _ in range(q.u32())]
        tail=q.get('4I');assert q.p==len(blob),(i,q.p,len(blob))
        yy,xx=np.mgrid[:25,:25]/24
        a,b,c,d=corners;base=(a*(1-xx)+b*xx)*(1-yy)+(d*(1-xx)+c*xx)*yy
        height=base+bm[:25,:25,0].astype(float)/255*16
        result.append(dict(xz=xz,corners=corners,height=height,blockmap=bm,overlay=ov,control=control,mud=relief,watermap=wm,waterdata=wd,plant_indices=plant_indices,grass_ranges=grass_ranges,payload_bytes=len(blob),decoded_bytes=q.p))
    return result

def grass_instances(path):
    meta,buffers=decode(path);names=list(buffers);used={name:set() for name in names};result=[]
    for bi,b in enumerate(blocks(path)):
        for brand,first,*counts in b['grass_ranges']:
            name=names[brand];count=sum(counts);data=np.frombuffer(buffers[name],dtype='u1').reshape(-1,8)
            assert first+count<=len(data)
            ids=set(range(first,first+count));assert not used[name]&ids
            used[name]|=ids
            for raw in data[first:first+count]:
                u,v=float(raw[2])/255,float(raw[1])/255;a,c,d,e=b['corners']
                height=((1-u)*a+u*c)*(1-v)+((1-u)*e+u*d)*v+float(raw[3])/255*16
                index=math.floor(float(raw[0])/255*16)
                result.append(dict(brand=name,block=bi,native_xyz=[b['xz'][0]+u*16,height,b['xz'][1]+v*16],scale=(.25+float(raw[7])/255*3.75)*(.8+index*.1),variant=index,packed=bytes(raw).hex()))
    assert all(len(used[n])*8==len(buffers[n]) for n in names),'Unmapped grass buffer data'
    return result

if __name__=='__main__':
    import sys
    p=Path(sys.argv[1]);report,grasses=decode(p)
    parsed=blocks(p);grass=grass_instances(p)
    report['complete_block_payloads']=len(parsed)
    report['grass_records_verified']=len(grass)
    p.with_suffix('.decoded.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='plants'},indent=2))
