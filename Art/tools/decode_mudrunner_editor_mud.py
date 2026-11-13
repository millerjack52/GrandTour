"""Decode the editor's sparse prebuild mud container, validated against its loader.

Keeps the native 25x25 extrudeMap raw: its byte-to-physical mapping is not yet proven.
All writes go to the research folder, never the installed editor or Unreal.
"""
from pathlib import Path
import hashlib, json, struct
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
from mudrunner_editor_re import SOURCE, OUT

def decode(path):
    data=path.read_bytes();version,bx,bz,count=struct.unpack_from('<4I',data)
    assert version in (0x133293e,0x13379ba),(str(path),version)
    assert 0<bx<=512 and 0<bz<=512 and count<=bx*bz
    cursor=16;records=[];seen=set()
    for i in range(count):
        x,z=struct.unpack_from('<II',data,cursor);cursor+=8
        assert x<bx and z<bz and (x,z) not in seen
        seen.add((x,z))
        control=np.frombuffer(data,'u1',625,cursor).copy().reshape(25,25);cursor+=625
        size,=struct.unpack_from('<I',data,cursor);cursor+=4
        assert size<=0x100000 and cursor+size<=len(data)
        dds=data[cursor:cursor+size];cursor+=size
        assert dds[:4]==b'DDS ' and struct.unpack_from('<I',dds,4)[0]==124
        h,w=struct.unpack_from('<II',dds,12)
        fourcc,bits,rm,gm,bm,am=struct.unpack_from('<6I',dds,84)
        assert (w,h,fourcc,bits,rm,gm,bm,am)==(128,128,0,32,0xff0000,0xff00,0xff,0xff000000)
        assert size==128+w*h*4
        bgra=np.frombuffer(dds,'u1',offset=128).reshape(h,w,4).copy()
        if version==0x133293e:
            # Loader 0x14025b750: copy old B to A, set G/B to 128, preserve R.
            bgra[:,:,3]=bgra[:,:,0];bgra[:,:,:2]=128
        records.append((x,z,control,bgra[:,:,[2,1,0,3]]))
    assert cursor==len(data),(str(path),cursor,len(data))
    return version,bx,bz,records

def main():
    out=OUT/'Deep';out.mkdir(exist_ok=True)
    paths=sorted((SOURCE/'Media/prebuild').glob('*/mud'))+sorted((SOURCE/'Samples/mod_level/prebuild').glob('*/mud'))
    results=[];total=0
    for path in paths:
        source_hash=hashlib.sha256(path.read_bytes()).hexdigest()
        version,bx,bz,records=decode(path);total+=len(records)
        item=dict(source=str(path),sha256=source_hash,version=version,blocks=[bx,bz],records=len(records),
                  red_min=min((int(r[:,: ,0].min()) for x,z,c,r in records),default=155),
                  red_max=max((int(r[:,:,0].max()) for x,z,c,r in records),default=155),
                  alpha_max=max((int(r[:,:,3].max()) for x,z,c,r in records),default=0))
        item['height_offset_range_m']=[round((item[k]-155)*.008,3) for k in ['red_min','red_max']]
        results.append(item)
        if path.parent.name=='ref_road_muddy':
            rgba=np.zeros((bz*128,bx*128,4),dtype='u1');rgba[:,:,0]=155;rgba[:,:,1:3]=128
            rawcontrol=np.zeros((bz*24+1,bx*24+1),dtype='u1')
            for x,z,c,r in records:
                rgba[z*128:(z+1)*128,x*128:(x+1)*128]=r
                # Overlap border vertices: this preview uses max, not a claim
                # about the engine's seam resolution order.
                view=rawcontrol[z*24:z*24+25,x*24:x*24+25];np.maximum(view,c,out=view)
            relief=(rgba[:,:,0].astype(np.float32)-155)*.008
            np.savez_compressed(out/'muddy-road-decoded-mud.npz',rgba=rgba,height_offset_m=relief,raw_control_preview_max_seams=rawcontrol)
            tiles=[('Stored relief: zero = middle grey',Image.fromarray(np.uint8(np.clip(.5+relief/(2*1.24),0,1)*255))),
                   ('Track channel: raw alpha',Image.fromarray(rgba[:,:,3])),
                   ('25x25 extrudeMap: raw bytes',Image.fromarray(rawcontrol))]
            canvas=Image.new('RGB',(1230,680),'#18211f');d=ImageDraw.Draw(canvas)
            f=lambda s:ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',s)
            d.text((24,18),'Native muddy-road data, decoded from the editor container',font=f(27),fill='white')
            d.text((24,60),f'26 sparse blocks; stored relief {item["height_offset_range_m"][0]:.3f} to {item["height_offset_range_m"][1]:.3f} m. Native grid orientation.',font=f(18),fill='#b5c6b7')
            for i,(title,im) in enumerate(tiles):
                im=ImageOps.contain(im.convert('RGB'),(380,500),Image.Resampling.NEAREST)
                canvas.paste(im,(25+405*i+(380-im.width)//2,110))
                d.text((25+405*i,625),title,font=f(18),fill='white')
            canvas.save(out/'muddy-road-decoded-mud.png')
        assert hashlib.sha256(path.read_bytes()).hexdigest()==source_hash
    report=dict(ok=True,files=len(results),blocks_decoded=total,versions=sorted(set(r['version'] for r in results)),
                loader='0x14025b2c0',format='Header: version,u32 blocksX,blocksZ,count; each record u32 x,z; 625 control bytes; u32 DDS byte count; DDS.',
                limits='25x25 grid identified as extrudeMap by native assertions and copy path; physical byte mapping unresolved. No re-encoding or native map rebuild claimed.',sources=results)
    (out/'mud-container-check.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='sources'},indent=2))

if __name__=='__main__':main()
