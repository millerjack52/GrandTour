"""Author a lower crown envelope from the accepted hydraulic state, preserving every wet cell."""
from pathlib import Path
import numpy as np,json
from scipy.ndimage import distance_transform_edt,maximum_filter
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/BenmoreRivers'
SOURCE=ROOT/'Art/Export/BenmoreRivers_BeforeLowBanks'
d=np.load(SOURCE/'river_bake.npz');state=np.load(SOURCE/'solver_banked_state.npz')
h=np.zeros_like(d['bed']);h.ravel()[state['cell_indices']]=state['h']
surface=d['bed']+h
nearest=distance_transform_edt(h<.025,return_distances=False,return_indices=True)
# A nearby upstream cell can have a higher head than the nearest downstream
# cell: protect against the local maximum, including a modest surge margin.
envelope=maximum_filter(np.where(h>.025,surface,-1e6),size=25,mode='nearest')
envelope=np.maximum(envelope,surface[tuple(nearest)])
guard=np.maximum(0,envelope+.30-d['base'])
minimum=np.minimum(d['bank_delta'],guard)
minimum=np.where(h>1e-5,d['bank_delta'],minimum)
np.savez_compressed(OUT/'bank-crown-reference.npz',x=d['x'],y=d['y'],minimum_fill=minimum)
print(json.dumps({'reference':str(SOURCE),'freeboard_m':.30,'head_envelope_radius_m':12,'wet_cells_preserved':int((h>1e-5).sum()),'potential_fill_reduction_m3':float((d['bank_delta']-minimum).sum())}))
