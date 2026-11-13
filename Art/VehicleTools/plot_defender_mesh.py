import json,numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from pathlib import Path
p=Path('C:/GrandTour/Art/Export/VehicleTools/defender-tripo-v01')
d=json.loads((p/'island-geometry.json').read_text())[0];v=np.array(d['vertices'])
for name,axes,mask in [('side',(1,2),lambda t:t[:,0].mean()>.17),('top',(1,0),lambda t:t[:,2].mean()>.26)]:
 polys=[v[f][:,axes] for f in d['faces'] if mask(v[f])]
 fig,ax=plt.subplots(figsize=(16,8));ax.add_collection(PolyCollection(polys,facecolors='#cbd5d9',edgecolors='#4b5b61',linewidths=.3));ax.autoscale();ax.set_aspect('equal');ax.set_xticks(np.arange(-.5,.51,.025));ax.set_yticks(np.arange(0,.51,.025) if name=='side' else np.arange(-.25,.251,.025));ax.grid(alpha=.5);ax.tick_params(axis='x',rotation=90);fig.savefig(p/('mesh-'+name+'.png'),dpi=140);plt.close(fig)
