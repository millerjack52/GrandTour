"""Read-only retail Island STG study; prefix traced in native TerrainSTGSave.

Keeps the experimental decoder's strict empty-header assumptions unchanged.
Geometry spline payloads are framed/skipped, not interpreted as road controls.
"""
from pathlib import Path
import collections, hashlib, json, sys
import numpy as np
import decode_mudrunner_editor_stg as stg

ROOT = Path(__file__).resolve().parents[1] / 'Export/MudRunnerEditorResearch/Island'
SOURCE = ROOT / 'level_coast.stg'
sys.path.insert(0,str(Path(__file__).resolve().parents[1] / 'Tools/island-re-python'))

def prefix(path):
    data = Path(path).read_bytes(); r = stg.Reader(data)
    version, guid = r.get('II'); assert version == 0x0133ed03
    trucks = []
    for _ in range(r.u32()):
        name = r.string(); r.raw(64)
        addons = [r.string() for _ in range(r.u32())]
        trailer = r.string(); r.raw(9)
        trucks.append(dict(name=name, addons=addons, trailer=trailer))
    drive = r.u32(); locators = []
    for _ in range(r.u32()):
        kind = r.u32(); shape = r.get('6f'); name = r.string()
        if kind in (7,8): r.raw(64)
        locators.append(dict(kind=kind, shape=shape, name=name))
    size = r.get('2f'); origin = r.get('2f'); mutator = r.string()
    materials = [(r.string(), r.string()) for _ in range(r.u32())]
    overlays = [r.string() for _ in range(r.u32())]
    grasses = {}
    for _ in range(r.u32()):
        name = r.string(); grasses[name] = r.raw(r.u32())
    brands = [r.string() for _ in range(r.u32())]
    geometry = []
    for _ in range(r.u32()):
        name = r.string(); wire = r.get('B')[0]; count = r.u32()
        assert wire in (0,1) and count < 10000
        kinds = collections.Counter()
        for _ in range(count):
            if wire:
                n = r.u32(); assert n < 10000; r.raw(64*n)
            else:
                length, kind = r.get('fI'); kinds[kind] += 1
                assert np.isfinite(length) and kind in (0,1,2,3), (name,length,kind,r.p)
                if kind == 1: r.raw(8)
                elif kind == 2: r.raw(24)
                else:
                    for axis in range(2):
                        n = r.u32(); assert 0 < n < 10000, (name, n, r.p)
                        r.raw((5*n+2)*4)
        geometry.append(dict(name=name, wire=wire, curves=count, types=dict(kinds)))
    chunks = []; plants = collections.Counter()
    for _ in range(r.u32()):
        n = r.u32(); assert n < 1000000; chunks.append(n)
        for _ in range(n):
            brand = r.get('H')[0]; assert brand < len(brands)
            xyz = r.get('3f'); r.raw(8)
            assert all(np.isfinite(xyz))
            plants[brands[brand]] += 1
    waters = [(r.string(), r.string()) for _ in range(r.u32())]
    bx,bz = r.get('II'); assert (bx*16,bz*16) == size, (bx,bz,r.p)
    return dict(version=version,guid=guid,sha256=hashlib.sha256(data).hexdigest(),
        size=size,origin=origin,materials=materials,overlays=overlays,waters=waters,
        grass_buffer_bytes={k:len(v) for k,v in grasses.items()},
        geometry=geometry,plant_counts=dict(plants),plant_chunks=chunks,
        blocks=[bx,bz],block_payload_offset=r.p), grasses

def main():
    meta,_ = prefix(SOURCE)
    (ROOT/'header.json').write_text(json.dumps(meta,indent=2))
    # Reuse the previously verified complete block framing, with this retail prefix.
    stg.decode = prefix
    blocks = stg.blocks(SOURCE)
    summary = dict(complete_block_payloads=len(blocks),mud_blocks=0,water_blocks=0,
        mud_water_blocks=0,road_overlay_blocks=0,road_mud_blocks=0,road_mud_water_blocks=0)
    h = {k:np.zeros(256,dtype=np.int64) for k in ['relief','control','road_relief','road_control']}
    atlas = np.full((1024,1024),np.nan,dtype=np.float32)
    control_atlas = atlas.copy(); water_atlas = np.zeros_like(atlas)
    road_atlas = np.zeros_like(atlas)
    candidates=[]
    for i,b in enumerate(blocks):
        mud=b['mud'] is not None; water=b['watermap'] is not None; road=b['overlay'] is not None
        summary['mud_blocks']+=int(mud); summary['water_blocks']+=int(water)
        summary['mud_water_blocks']+=int(mud and water); summary['road_overlay_blocks']+=int(road)
        summary['road_mud_blocks']+=int(road and mud); summary['road_mud_water_blocks']+=int(road and mud and water)
        x,z=[round((b['xz'][j]-meta['origin'][j])/16) for j in range(2)]
        assert 0<=x<64 and 0<=z<64,(x,z,b['xz'])
        sl=np.s_[z*16:(z+1)*16,x*16:(x+1)*16]
        if road: road_atlas[sl]=1
        if water: water_atlas[sl]=1
        if mud:
            red=b['mud'][:,:,1]; ctrl=b['control']
            h['relief']+=np.bincount(red.ravel(),minlength=256)
            h['control']+=np.bincount(ctrl.ravel(),minlength=256)
            atlas[sl]=(red.astype(np.float32).reshape(16,8,16,8).mean(axis=(1,3))-155)*.008
            control_atlas[sl]=np.array(stg.Image.fromarray(ctrl).resize((16,16)))/255
            if road:
                h['road_relief']+=np.bincount(red.ravel(),minlength=256)
                h['road_control']+=np.bincount(ctrl.ravel(),minlength=256)
                if water: candidates.append((float(red.std()),i))
    def stats(a,relief):
        ids=np.flatnonzero(a); values=(np.arange(256)-155)*.008 if relief else np.arange(256)
        qs=np.searchsorted(np.cumsum(a),np.array([.01,.1,.5,.9,.99])*a.sum())
        return dict(samples=int(a.sum()),distinct_values=len(ids),range=[float(values[ids[0]]),float(values[ids[-1]])],
                    quantiles_01_10_50_90_99=values[qs].tolist())
    summary['distributions']={k:stats(v,'relief' in k) for k,v in h.items()}
    summary['limits']='Road statistics include entire 16m blocks with overlays, not only the wheel path. Relief is authored height offset, not sinkable depth. Control is raw 0..255; no unverified physical unit conversion.'
    summary['selected_road_mud_water_blocks']=[i for _,i in sorted(candidates,reverse=True)[:8]]
    (ROOT/'analysis.json').write_text(json.dumps(summary,indent=2))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axs=plt.subplots(2,2,figsize=(12,11),constrained_layout=True)
    for ax,data,title,cmap in zip(axs.flat,[road_atlas,atlas,control_atlas,water_atlas],
        ['Blocks containing road overlays','Authored mud relief (m), block averaged','Mud control (raw byte / 255), block resampled','Blocks containing water'],['Greys','RdBu_r','viridis','Blues']):
        im=ax.imshow(data,origin='lower',extent=(-512,512,-512,512),cmap=cmap)
        ax.set_title(title); ax.set_xlabel('Native X (m)'); ax.set_ylabel('Native Z (m)')
        fig.colorbar(im,ax=ax,shrink=.75)
    fig.suptitle('MudRunner Island / level_coast.stg — independent saved layers')
    fig.savefig(ROOT/'island-layers.png',dpi=140); plt.close(fig)
    selected=summary['selected_road_mud_water_blocks'][:3]
    fig,axs=plt.subplots(len(selected),3,figsize=(12,4*len(selected)),constrained_layout=True)
    for row,i in enumerate(selected):
        b=blocks[i]
        for ax,data,title,cmap in zip(axs[row],[ (b['mud'][:,:,1].astype(float)-155)*.008,b['control'],b['watermap'][:,:,3]],
            ['Authored relief (m)','Mud control (raw byte)','Water opacity (saved alpha byte)'],['RdBu_r','viridis','Blues']):
            im=ax.imshow(data,origin='lower',extent=(0,16,0,16),cmap=cmap)
            ax.set_title(f'Block {i}: {title}'); ax.set_xlabel('m'); ax.set_ylabel('m')
            if data.ndim==2: fig.colorbar(im,ax=ax,shrink=.7)
    fig.savefig(ROOT/'island-road-details.png',dpi=140); plt.close(fig)
    print(json.dumps(summary,indent=2))

if __name__=='__main__': main()
