"""Current-terrain Gaea 2 handoff, exact reference data, protection masks and starter graphs."""
from pathlib import Path
import json,hashlib,uuid,copy
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/BenmoreGaea';N=2048
DATUM=360.531005859375;ZERO=256.;RANGE=512.

def resample(a,n):
    p=np.linspace(0,a.shape[0]-1,n);lo=p.astype(int);hi=np.minimum(lo+1,a.shape[0]-1);f=p-lo
    row=a[lo]*(1-f[:,None])+a[hi]*f[:,None]
    return row[:,lo]*(1-f[None,:])+row[:,hi]*f[None,:]
def smooth01(t):
    t=np.clip(t,0,1);return t*t*(3-2*t)
def write16(path,a):Image.fromarray(np.rint(np.clip(a,0,1)*65535).astype('uint16')).save(path)
def graph(path,study=False):
    nodes={};nextid=100
    def node(kind,name,x,y,inputs=None,outputs=('Out',),**kw):
        nonlocal nextid
        i=nextid;nextid+=1;ref=str(i);ports=[]
        for pin,source in (inputs or {'In':None}).items():
            p={'Name':pin,'Type':'PrimaryIn, Required' if pin=='In' and kind!='File' else 'In','Parent':{'$ref':ref}}
            if source:p['Record']={'From':source[0],'To':i,'FromPort':source[1],'ToPort':pin,'IsValid':True}
            ports.append(p)
        for pin in outputs:ports.append({'Name':pin,'Type':'PrimaryOut' if pin=='Out' else 'Out','IsExporting':True,'Parent':{'$ref':ref}})
        nodes[str(i)]={'$id':ref,'$type':'QuadSpinner.Gaea.Nodes.'+kind+', Gaea.Nodes','Id':i,'Name':name,'Position':{'X':x,'Y':y},'Ports':{'$values':ports},'Modifiers':{'$values':[]},**kw}
        return (i,'Out')
    def file(name,filename,x,y):return node('File',name,x,y,FileName=str(OUT/'input'/filename),IsRGB=False,EnforceLinearGamma=False,RelativePath=False)
    def export(name,source,x,y,folder):
        p=node('Export',name,x,y,{'In':source},Format='TIFF32',Location='Explicit',OutputPath=str(OUT/folder/name),IfFileExists='Overwrite',ExportState='WillExport')
        nodes[str(p[0])]['SaveDefinition']={'Node':p[0],'Filename':name,'Format':'TIFF32','IsEnabled':True}
        return p
    original=file('01_CurrentTerrain','H_CurrentTerrain_2048.png',26500,26000)
    export('H_InputCheck',original,26500,26400,'return' if study else 'roundtrip')
    end=original
    if study:
        erosion=node('Erosion2','02_GentleErosion',26800,26000,{'In':original},('Out','Flow','Wear','Deposits'),Duration=3.,Downcutting=.12,ErosionScale=120.,Shape=.05,Seed=81026,SuspendedLoadDischargeAmount=.35,BedLoadDischargeAmount=.15,CoarseSedimentsDischargeAmount=.05)
        head=file('03_HeadwaterArea','M_HeadwaterArea_2048.png',26800,25650)
        rivers=node('Rivers','04_ChannelStudy',27100,26000,{'In':erosion,'Headwaters':head},('Out','Rivers','Depth','Surface','Direction'),Water=.40,Width=.12,Depth=.12,Downcutting=0.,Headwaters=1000,RenderSurface=False,RiverValleyWidth='zero',Seed=81026)
        mask=file('05_FirstCatchmentMask','M_FirstPass_Edit_2048.png',27400,25650)
        end=node('Combine','06_ProtectedTerrain',27400,26000,{'In':original,'Input2':rivers,'Mask':mask},Ratio=.5,Mode='Blend',Clamp='Clamp',Enhance='None')
        for name,src,y in [('M_Rivers',(rivers[0],'Rivers'),26400),('M_Depth',(rivers[0],'Depth'),26580),('H_WaterSurface',(rivers[0],'Surface'),26760),('M_Wear',(erosion[0],'Wear'),26940),('M_Deposits',(erosion[0],'Deposits'),27120)]:export(name,src,27800,y,'return')
    export('H_Eroded',end,27800 if study else 26800,26000,'return' if study else 'roundtrip')
    asset={'Terrain':{'Id':str(uuid.uuid4()),'Metadata':{'Version':'2.3.0.1','ModifiedVersion':'2.3.0.1'},'Nodes':nodes,'Groups':{},'Notes':{},'GraphTabs':{'$values':[{'Name':'Benmore','Color':'Brass','ZoomFactor':.7,'ViewportLocation':{'X':26300,'Y':25500}}]},'Width':2500.,'Height':512.,'Ratio':512/2500},'BuildDefinition':{'Type':'Standard','Destination':str(OUT/('return' if study else 'roundtrip')),'Resolution':2048,'BakeResolution':2048,'TileResolution':1024,'BucketResolution':2048,'FlipY':False,'OrganizeFiles':'None','ColorSpace':'LinearGray','OpenFolder':False,'RemovePrimaryPortName':True},'State':{'PreviewResolution':1024,'BakeResolution':2048,'SelectedNode':end[0],'Viewport':{'RenderMode':'Realistic','SunAltitude':35.,'SunAzimuth':240.,'AmbientOcclusion':True,'Shadows':True}}}
    asset['Automation']={'Bindings':{'$values':[]},'Expressions':{},'VariablesEx':{},'Variables':{}}
    asset['State']['NodeBookmarks']={'$values':[]}
    asset['State']['Viewport']['Camera']={}
    doc={'Assets':{'$values':[asset]},'Id':str(uuid.uuid4()),'Branch':1,'Metadata':{'Name':path.stem,'Version':'2.3.0.1','ModifiedVersion':'2.3.0.1','Description':'Benmore terrain study. Preserve dimensions. Compare the untouched export before integration.'}}
    path.write_text(json.dumps(doc,indent=2))

def run():
    for folder in ['input','return','roundtrip','candidate','review']:(OUT/folder).mkdir(parents=True,exist_ok=True)
    report=json.loads((OUT/'source/unreal-export-report.json').read_text());assert report['ok']
    raw=(OUT/'source/H_Current_Unreal_2017.r16').read_bytes();assert hashlib.sha256(raw).hexdigest()==report['height_sha256']
    base=(np.frombuffer(raw,dtype='<u2').reshape(2017,2017).astype(float)-32768)/64
    h=resample(base,N);normalized=(h+DATUM-ZERO)/RANGE;assert normalized.min()>0 and normalized.max()<1
    write16(OUT/'input/H_CurrentTerrain_2048.png',normalized)
    # The delivered integer input is the reference, including its quantization.
    reference=np.asarray(Image.open(OUT/'input/H_CurrentTerrain_2048.png')).astype(float)/65535
    np.save(OUT/'source/input_reference_normalized.npy',reference)
    xy=np.linspace(-1250,1250,N);X,Y=np.meshgrid(xy,xy)
    # South-up calculations; every Gaea image is flipped north-up on disk.
    route=json.loads((ROOT/'Art/Export/BenmoreRoads/road-manifest.json').read_text())
    protect_road=np.zeros_like(h);route_lines=[]
    for r in route['routes']:
        p=np.array([[q['x_m'],q['y_m']] for q in r['points']]);route_lines.append(p.tolist())
        d=cKDTree(p).query(np.c_[X.ravel(),Y.ravel()],workers=2)[0].reshape(h.shape)
        # 2 m sample pitch; full preservation includes the entire graded shoulder.
        core=r['width_m']/2+(10 if r['closed'] else 8)+2
        protect_road=np.maximum(protect_road,1-smooth01((d-core)/25.))
    edge=np.minimum(1250-np.abs(X),1250-np.abs(Y))
    protect_boundary=1-smooth01((edge-25)/65)
    protect_lake=1-smooth01((h-.8)/3.2)
    protect=np.maximum.reduce([protect_road,protect_boundary,protect_lake])
    # Broad first-study area around the north gully. This is an art constraint,
    # not a computed watershed or a requirement to copy the old river path.
    box=np.minimum.reduce([X+1230,-120-X,Y+25,1100-Y])
    catchment=smooth01(box/65.)
    edit=(1-protect)*catchment
    head=1-smooth01((np.hypot(X+420,Y-750)-90)/140)
    masks={'M_ProtectRoads':protect_road,'M_ProtectLake':protect_lake,'M_ProtectBoundary':protect_boundary,'M_ProtectAll':protect,'M_EditTerrain':1-protect,'M_FirstPass_Edit':edit,'M_HeadwaterArea':head}
    # All Gaea data have north at the top, unlike the canonical UE transfer grid.
    write16(OUT/'input/H_CurrentTerrain_2048.png',reference[::-1])
    np.save(OUT/'source/input_reference_normalized.npy',reference[::-1])
    for name,v in masks.items():write16(OUT/'input'/(name+'_2048.png'),v[::-1])
    np.save(OUT/'source/protect_2017.npy',np.maximum.reduce([resample(protect_road,2017),resample(protect_boundary,2017),resample(protect_lake,2017)]))
    # An exact maximum plateau is required for unchanged road and boundary samples.
    p=resample(protect,2017);p[p>1-1e-6]=1;np.save(OUT/'source/protect_2017.npy',p)
    manifest={'ok':True,'source_level':report['source_level'],'source_map_sha256':report['source_map_sha256'],'source_height_sha256':report['height_sha256'],'width_m':2500,'gaea_height_range_m':512,'gaea_zero_nzvd2016_m':256,'unreal_datum_nzvd2016_m':DATUM,'gaea_resolution':N,'unreal_resolution':2017,'gaea_row_zero':'north (+Y)','unreal_row_zero':'south (-Y)','height_decode':'local_m = normalized * 512 + 256 - 360.531005859375','placements_snapshot':{'actors':report['actor_count'],'instances':report['instance_count']},'files':{}}
    graph(OUT/'Benmore_00_RoundTrip.terrain',False);graph(OUT/'Benmore_01_RiverStudy.terrain',True)
    for p in sorted((OUT/'input').glob('*.png')):manifest['files'][p.name]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
    (OUT/'package-manifest.json').write_text(json.dumps(manifest,indent=2))
    # Numerical map preview, not a terrain texture or Gaea input.
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import LightSource
    shade=LightSource(azdeg=315,altdeg=40).shade(h,plt.get_cmap('gist_earth'),vert_exag=1,dx=2500/(N-1),dy=2500/(N-1),blend_mode='soft')
    fig,ax=plt.subplots(figsize=(10,10),layout='constrained');ax.imshow(shade,origin='lower',extent=(-1250,1250,-1250,1250))
    ax.contour(X,Y,edit,levels=[.15],colors=['#46ecdc'],linewidths=2)
    for p in route_lines:
        p=np.array(p);ax.plot(p[:,0],p[:,1],color='#ffb454',linewidth=2)
    ax.scatter([-420],[750],s=90,c='#54e5ff',edgecolors='black');ax.annotate('Suggested headwater area',(-420,750),xytext=(-1000,1000),color='white',arrowprops={'arrowstyle':'->','color':'white'},bbox={'facecolor':'#17292b','alpha':.9})
    ax.set(xlabel='East / Unreal X (m)',ylabel='North / Unreal Y (m)',title='BENMORE / FIRST GAEA PASS\nOrange: protected roads   Cyan: editable catchment boundary')
    fig.savefig(OUT/'review/FirstPass_Map.png',dpi=160);plt.close(fig)
    print(json.dumps({k:v for k,v in manifest.items() if k!='files'},indent=2))

if __name__=='__main__':run()
