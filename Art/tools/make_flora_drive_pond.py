"""Map-local pond extension; preserve the road's authored heights and native simulation."""
from pathlib import Path
from PIL import Image
import numpy as np,json
from flora_drive_ground import pond_delta
from make_mud_road import centre
O=Path('C:/GrandTour/Art/Export/FloraDrive');S=Path('C:/GrandTour/Art/Export/MudRoad')
rest=np.array(Image.open(S/'world-rest.png').convert('RGBA'));paint=np.array(Image.open(S/'soil-paint.png').convert('RGBA'))
size=rest.shape[0];changed=0;road_changes=0;wet=0
for j in range(size):
    y=-3150+(j+.5)*6300/size
    for i in range(size):
        x=-3150+(i+.5)*6300/size;p=pond_delta(x,y)
        if p>=-.01:continue
        old=(int(rest[j,i,0])*256+int(rest[j,i,1]))*65/65535-50
        h=min(old,p);v=round((h+50)/65*65535)
        rest[j,i,:2]=[v>>8,v&255];paint[j,i,0]=max(int(paint[j,i,0]),185);paint[j,i,3]=max(int(paint[j,i,3]),140)
        changed+=1;wet+=h<-26*50/255
        road_changes+=abs(y-centre(x))<300
assert changed>100 and road_changes==0
Image.fromarray(rest).save(O/'world-rest.png');Image.fromarray(paint).save(O/'soil-paint.png')
(O/'pond-authoring.json').write_text(json.dumps({'centre_cm':[900,1050],'radii_cm':[700,500],'bed_depth_cm':32,'changed_cells':changed,'road_cells_changed':road_changes,'wet_area_m2':wet*(6300/size)**2/10000},indent=2))
