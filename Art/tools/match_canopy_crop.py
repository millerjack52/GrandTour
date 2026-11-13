from PIL import Image
import numpy as np,json
from pathlib import Path
root=Path('C:/GrandTour');qa=root/'Saved/LidarAuthoringQA/CanopyInterior'
src=Image.open(root/'Art/Export/LidarStudy/CohesiveStyle/WarmthReview/valley-after.png').convert('L')
ref=Image.open('C:/Users/mille/AppData/Local/Temp/codex-clipboard-51c9de1b-6e63-4bd0-9666-6ee3c4c6fa30.png').convert('L')
a=np.asarray(src.resize((222,125)),dtype=float);best=(-1,None)
for scale in np.arange(.6,1.61,.025):
 w,h=round(ref.width*scale/4),round(ref.height*scale/4)
 if w>a.shape[1] or h>a.shape[0]:continue
 t=np.asarray(ref.resize((w,h)),dtype=float);t-=t.mean();shape=(a.shape[0]+h-1,a.shape[1]+w-1)
 corr=np.fft.irfft2(np.fft.rfft2(a,s=shape)*np.fft.rfft2(t[::-1,::-1],s=shape),s=shape)[h-1:a.shape[0],w-1:a.shape[1]]
 def sums(v):
  p=np.pad(v,((1,0),(1,0))).cumsum(0).cumsum(1);return p[h:,w:]-p[:-h,w:]-p[h:,:-w]+p[:-h,:-w]
 denom=np.sqrt(np.maximum(1,sums(a*a)-sums(a)**2/(w*h))*(t*t).sum())
 score=corr/denom;y,x=np.unravel_index(score.argmax(),score.shape)
 if score[y,x]>best[0]:best=(float(score[y,x]),[int(x*4),int(y*4),int((x+w)*4),int((y+h)*4)])
r=dict(correlation=best[0],rectangle=best[1],source='WarmthReview/valley-after.png',reference='User selected forest gap crop')
(qa/'crop.json').write_text(json.dumps(r,indent=2));print(r)
