"""Plot the returned height data and inspect the unblended channel export."""
from pathlib import Path
import copy,json,sys
import numpy as np
from scipy.ndimage import label
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource
from convert_benmore_gaea import OUT,read_height

out=OUT/'review/native-inspection';out.mkdir(parents=True,exist_ok=True)
doc=json.loads((OUT/'Benmore_01_RiverStudy.terrain').read_text())
asset=doc['Assets']['$values'][0];nodes=asset['Terrain']['Nodes']
export=next(n for n in nodes.values() if n['Name']=='H_Eroded')
for n in nodes.values():
    if n['$type'].startswith('QuadSpinner.Gaea.Nodes.Export'):
        n['OutputPath']=str(out/n['Name'])
for name,src,idx in [('H_ChannelBed','04_ChannelStudy',200),('H_GentleErosion','02_GentleErosion',201)]:
    n=copy.deepcopy(export);n['$id']=str(idx);n['Id']=idx;n['Name']=name;n['OutputPath']=str(out/name)
    n['SaveDefinition'].update(Node=idx,Filename=name)
    for p in n['Ports']['$values']:
        p['Parent']['$ref']=str(idx)
        if 'Record' in p:p['Record'].update(From=next(v['Id'] for v in nodes.values() if v['Name']==src),To=idx)
    nodes[str(idx)]=n
asset['BuildDefinition']['Destination']=str(out)
(out/'Inspect.terrain').write_text(json.dumps(doc,indent=2))
h=read_height(OUT/'return/H_Eroded.tif')[::-1]*512+256-360.531005859375
river=read_height(OUT/'return/M_Rivers.tif')[::-1]
mask=read_height(OUT/'input/M_FirstPass_Edit_2048.png')[::-1]
shade=LightSource(315,40).shade(h,plt.get_cmap('gist_earth'),vert_exag=1,dx=2500/2047,dy=2500/2047,blend_mode='soft')
fig,ax=plt.subplots(figsize=(11,9),layout='constrained');ax.imshow(shade,origin='lower',extent=(-1250,1250,-1250,1250))
xx=np.linspace(-1250,1250,2048);ax.contour(xx,xx,river,levels=[.5],colors=['#08afff'],linewidths=1)
ax.contour(xx,xx,mask,levels=[.15],colors=['white'],linewidths=.8)
old=np.load(OUT.parent/'BenmoreRivers/river_bake.npz')['path'];ax.plot(old[:,0],old[:,1],'r--',lw=1,label='Previous authored channel')
route=json.loads((OUT.parent/'BenmoreRoads/road-manifest.json').read_text())
for r in route['routes']:
    p=np.array([[q['x_m'],q['y_m']] for q in r['points']]);ax.plot(p[:,0],p[:,1],color='#ffc64b')
ax.set(xlim=(-1250,-100),ylim=(-100,1120),title='Gaea return: blue channel, white edit boundary, red old channel',xlabel='East / X (m)',ylabel='North / Y (m)');ax.legend()
fig.savefig(OUT/'review/Returned_Channel_Map.png',dpi=145);plt.close(fig)
