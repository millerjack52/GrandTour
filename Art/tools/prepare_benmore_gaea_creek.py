"""Build a separate coherent Gaea creek study; never overwrite returned source."""
from pathlib import Path
import argparse,copy,json,uuid

def extract_network():
    """Follow the built Gaea mask; do not recompute a terrain drainage route."""
    import heapq
    import numpy as np
    from scipy.ndimage import binary_dilation,distance_transform_edt,gaussian_filter1d
    from scipy.spatial import cKDTree
    from convert_benmore_gaea import read_height
    from prepare_benmore_gaea import resample
    from reshape_benmore_channel import native
    mask=resample(read_height(OUT/'build/M_Rivers.tif')[::-1],2017)>.05
    allowed=binary_dilation(mask,iterations=2);distance=distance_transform_edt(mask)
    pixels=np.argwhere(mask);step=2500/2016
    xy=np.c_[-1250+pixels[:,1]*step,-1250+pixels[:,0]*step];tree=cKDTree(xy)
    end=tuple(pixels[np.argmin(abs(xy[:,0]+1250)*30+abs(xy[:,1]+50))])
    targets=[(-350.94,709.32),(-394.35,689.48),(-282.74,710.57)]
    starts=[tuple(pixels[tree.query(q)[1]]) for q in targets]
    costs={end:0};parents={};queue=[(0,end)];needed=set(starts)
    while queue and needed:
        cost,k=heapq.heappop(queue)
        if cost>costs[k]:continue
        needed.discard(k)
        for dj,di in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
            j,i=k[0]+dj,k[1]+di
            if not(0<=j<2017 and 0<=i<2017 and allowed[j,i]):continue
            v=(j,i);d=cost+np.hypot(di,dj)*(1+max(0,1-distance[v])*3)
            if d<costs.get(v,1e99):costs[v]=d;parents[v]=k;heapq.heappush(queue,(d,v))
    assert not needed,needed
    h=np.fromfile(BASE/'candidate/height_local_south_up.f32','<f4').reshape(2017,2017)
    paths=[]
    for start in starts:
        p=[start]
        while p[-1]!=end:p.append(parents[p[-1]])
        p=np.array(p);p=np.c_[-1250+p[:,1]*step,-1250+p[:,0]*step]
        arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))];s=np.arange(0,arc[-1]+.1,2)
        p=np.c_[np.interp(s,arc,p[:,0]),np.interp(s,arc,p[:,1])]
        p=gaussian_filter1d(p,2,axis=0,mode='nearest')
        paths.append(np.c_[p,native(h,p[:,0],p[:,1])])
    np.savez_compressed(OUT/'network-paths.npz',**{str(i):p for i,p in enumerate(paths)})
    print('GAEA_NETWORK_EXTRACTED')

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'Art/Export/BenmoreGaea'
OUT=BASE/'review/CoherentCreek'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    doc=json.loads((BASE/'Benmore_01_RiverStudy.terrain').read_text())
    doc['Id']=str(uuid.uuid4());doc['Metadata']['Name']='Benmore_PairedCreek'
    doc['Metadata']['Description']='Protected erosion BEFORE Rivers; all channel outputs from one final Rivers state. Source graph untouched.'
    asset=doc['Assets']['$values'][0];asset['Terrain']['Id']=str(uuid.uuid4())
    nodes=asset['Terrain']['Nodes'];blend=nodes['106'];river=nodes['104']
    blend['Name']='03_ProtectedErosion'
    for p in blend['Ports']['$values']:
        if p['Name']=='Input2':p['Record']['From']=102
    for p in river['Ports']['$values']:
        if p['Name']=='In':p['Record']['From']=106
    river['Name']='04_FinalCreek';river['Position']={'X':27700,'Y':26000}
    # Retain original node controls initially; judge the built shape before tuning.
    for n in nodes.values():
        if n['$type'].startswith('QuadSpinner.Gaea.Nodes.Export'):
            n['OutputPath']=str(OUT/'build'/n['Name'])
            if n['Name']=='H_Eroded':
                for p in n['Ports']['$values']:
                    if p['Name']=='In':p['Record']['From']=104
    export=copy.deepcopy(nodes['112']);export['$id']='113';export['Id']=113;export['Name']='H_PreRiver'
    export['OutputPath']=str(OUT/'build/H_PreRiver');export['SaveDefinition'].update(Node=113,Filename='H_PreRiver')
    for p in export['Ports']['$values']:
        p['Parent']['$ref']='113'
        if 'Record' in p:p['Record'].update(From=106,To=113)
    nodes['113']=export
    asset['BuildDefinition']['Destination']=str(OUT/'build')
    asset['State']['SelectedNode']=104
    path=OUT/'Benmore_PairedCreek.terrain';path.write_text(json.dumps(doc,indent=2))
    (OUT/'graph-contract.json').write_text(json.dumps(dict(source_graph=str(BASE/'Benmore_01_RiverStudy.terrain'),
        graph=str(path),terrain_final_node=104,water_surface_node=104,river_mask_node=104,depth_node=104,
        post_river_blend=False,width_m=2500,height_range_m=512,resolution=2048,source_preserved=True),indent=2))
    print(path)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--extract',action='store_true');args=p.parse_args()
    if args.extract:extract_network()
    else:main()
