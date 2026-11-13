"""Apply shared road-frame relief to FloraDrive's CPU/GPU rest field and material masks."""
from pathlib import Path
from PIL import Image
import numpy as np,json,math
from make_mud_road import centre
from road_relief_profile import profile
O=Path('C:/GrandTour/Art/Export/FloraDrive')
def road_frame(x,y):
    return x,(y-centre(x))/math.sqrt(1+(530/1050*math.cos((x+2200)/1050))**2)
def build():
    # The pond authoring tool first restores the unchanged source road + local pond.
    rest=np.array(Image.open(O/'world-rest.png').convert('RGBA'));paint=np.array(Image.open(O/'soil-paint.png').convert('RGBA'));mask=np.zeros_like(rest)
    original=(rest[:,:,0].astype(float)*256+rest[:,:,1])*65/65535-50
    size=rest.shape[0];height=original.copy();changed=0
    for j in range(size):
        y=-3150+(j+.5)*6300/size
        for i in range(size):
            x=-3150+(i+.5)*6300/size;delta,rut,crown,aggregate,cover=profile(*road_frame(x,y))
            if cover<.001:continue
            h=max(-42,min(14,original[j,i]+delta));height[j,i]=h;changed+=abs(h-original[j,i])>.01
            v=round((h+50)/65*65535);rest[j,i,:2]=[v>>8,v&255]
            # Maintain enough layer thickness to represent the new authored bed.
            paint[j,i,0]=max(int(paint[j,i,0]),round(max(0,-h+4)/50*255))
            mask[j,i]=np.uint8(np.round(np.clip([rut,crown,aggregate,cover],0,1)*255))
    Image.fromarray(rest).save(O/'world-rest.png');Image.fromarray(paint).save(O/'soil-paint.png');Image.fromarray(mask).save(O/'road-relief-mask.png')
    np.save(O/'road-rest-heights.npy',height)
    (O/'road-rest-heights.f32').write_bytes(height.astype('<f4').tobytes())
    probes=[]
    for x in [-1900,-1600,-1200,-700,0,1200,1800,2200]:
        row=[]
        for d in [-180,-83,0,83,180]:
            y=centre(x)+d*math.sqrt(1+(530/1050*math.cos((x+2200)/1050))**2)
            i=int((x+3150)/6300*size);j=int((y+3150)/6300*size)
            row.append({'x':x,'y':y,'lateral_cm':d,'before_cm':float(original[j,i]),'after_cm':float(height[j,i])})
        probes.append(row)
    report={'ok':True,'changed_road_cells':int(changed),'height_range_cm':[float(height.min()),float(height.max())],'encoding_range_cm':[-50,15],'grid_spacing_cm':6300/size,'profiles':probes,'layer_thickness_valid':bool(np.all(height>=-paint[:,:,0].astype(float)*50/255-.03))}
    assert report['layer_thickness_valid'] and changed>1000
    (O/'road-relief-authoring.json').write_text(json.dumps(report,indent=2))
    print({k:v for k,v in report.items() if k!='profiles'})
if __name__=='__main__':build()
