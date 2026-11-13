from pathlib import Path
from PIL import Image
out=Path('C:/GrandTour/Art/Export/VehicleTools/pathfinder-articulation-v08')
paths=sorted((out/'demo-frames').glob('*.png'))
assert len(paths)==24,len(paths)
frames=[Image.open(p).convert('RGB') for p in paths]
frames[0].save(out/'movement-preview.gif',save_all=True,append_images=frames[1:],duration=210,loop=0,optimize=False)
check=Image.open(out/'movement-preview.gif');duration=0
for i in range(check.n_frames):check.seek(i);duration+=check.info['duration']
assert check.n_frames>=18 and duration==5040,(check.n_frames,duration)
print('Saved native-render preview; identical hold frames coalesced:',check.n_frames,'frames,',duration,'ms')
