"""Fetch CC0 mud candidates, retain raw sources on D:, and record reproducible inputs."""
import concurrent.futures,hashlib,json,urllib.request
from pathlib import Path
from PIL import Image,ImageDraw
import numpy as np
R=Path('C:/GrandTour');O=R/'Art/Export/FloraTrail/MudTrial';S=Path('D:/GrandTourAssets/MudTextureTrial')
O.mkdir(parents=True,exist_ok=True);S.mkdir(parents=True,exist_ok=True)
def request(url):return urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'GrandTour-MaterialReview/1.0'}),timeout=120).read()

def import_copies(rows):
 for row in rows:
  for role,f in row['files'].items():
   im=Image.open(f['path'])
   if im.mode in ('I;16','I;16B','I'):
    # Preserve normalized scalar values; a direct 16-bit -> L conversion clips.
    im=Image.fromarray(np.round(np.asarray(im,dtype=np.float32)/257.).clip(0,255).astype('uint8'))
   elif role in ('color','normal'):im=im.convert('RGB')
   else:im=im.convert('RGB').getchannel('R')
   # Strip ancillary profiles: pigment uses sRGB; all other maps are linear data.
   im=Image.frombytes(im.mode,im.size,im.tobytes())
   p=S/row['id']/(role+'_engine8.png');im.save(p);f['engine_path']=str(p)
   f['engine_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
   p=S/row['id']/(role+'_screen.png');im.resize((1024,1024),Image.Resampling.LANCZOS).save(p);f['screen_path']=str(p)
   f['import_note']='8-bit copy, original pixel dimensions, no colour grade; raw source retained'
 normal_audit(rows)

def normal_audit(rows):
 audit={}
 for row in rows:
  h=np.asarray(Image.open(row['files']['height']['screen_path']).convert('L'),dtype=np.float32)/255
  n=np.asarray(Image.open(row['files']['normal']['screen_path']).convert('RGB'),dtype=np.float32)/127.5-1
  dy,dx=np.gradient(h)
  x=float(np.corrcoef((-dx).ravel(),n[:,:,0].ravel())[0,1]);y=float(np.corrcoef((-dy).ravel(),n[:,:,1].ravel())[0,1])
  flip=row['id']=='stylized_dry_mud'
  assert x>.2 and (y<-.2 if flip else y>.2),(row['id'],x,y)
  audit[row['id']]={'x_correlation':x,'y_correlation':y,'flip_green_for_unreal':flip,'method':'1K normalized import copies; normal XY against negative height gradient'}
 (O/'normal-height-audit.json').write_text(json.dumps(audit,indent=2))
def poly(name):
 data=json.loads(request('https://api.polyhaven.com/files/'+name));info=json.loads(request('https://api.polyhaven.com/info/'+name));folder=S/name;folder.mkdir(exist_ok=True)
 files={}
 for role,key in [('color','Diffuse'),('normal','nor_dx'),('roughness','Rough'),('height','Displacement'),('ao','AO')]:
  f=data[key]['4k']['png'];p=folder/(role+'.png')
  if not p.exists() or hashlib.md5(p.read_bytes()).hexdigest()!=f['md5']:p.write_bytes(request(f['url']))
  assert hashlib.md5(p.read_bytes()).hexdigest()==f['md5'];files[role]={'path':str(p),'url':f['url'],'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size':list(Image.open(p).size)}
 print(name,'downloaded',flush=True)
 return {'id':name,'name':info['name'],'source':'https://polyhaven.com/a/'+name,'license':'CC0','author':info['authors'],'tile_cm':info['dimensions'][0]/10,'normal':'DirectX','files':files}
def main():
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(poly,['brown_mud_02','muddy_tracks','mud_forest']))
 ids={'color':'1LpcO0XhZ-rjznNCShsh6yPQJ6884Lhu2','normal':'1fLpLKWazzPv9rWVfy_NlDvuOlmC_J-WI','roughness':'13VvdRE4LK2ReQ5_FvRk2VRD1IUFGY5_w','height':'1Y75lR3VWx8pnotkVaMb4iaTW2GBjcgCM','ao':'1Z3V_X5eNwvlRcKvv0-LIL6y19FcVxCj4'}
 files={}
 for role,id in ids.items():
  p=S/'stylized_dry_mud'/(role+('.png' if role=='height' else '.jpg'));assert p.exists(), 'Fetch the public Google Drive files listed in this script first.'
  files[role]={'path':str(p),'url':'https://drive.google.com/file/d/'+id+'/view','sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size':list(Image.open(p).size)}
 rows.insert(0,{'id':'stylized_dry_mud','name':'Stylized Dry Mud 001','source':'https://3dtextures.me/2021/08/01/stylized-dry-mud-001/','license':'CC0','license_url':'https://3dtextures.me/about/','author':'Katsukagi','tile_cm':200,'tile_note':'No authored real-world scale supplied; 2 m provisional test scale','normal':'OpenGL; check against height before import','files':files})
 import_copies(rows)
 (O/'sources.json').write_text(json.dumps({'ok':True,'candidates':rows,'screen_resolution':1024,'scope':'local study assets only'},indent=2)+'\n')
 board=Image.new('RGB',(1280,380),'#1b2428');d=ImageDraw.Draw(board)
 for i,row in enumerate(rows):
  im=Image.open(row['files']['color']['path']).convert('RGB');im.thumbnail((312,312));board.paste(im,(i*320+4,40));d.text((i*320+5,10),row['name'],fill='white')
 board.save(O/'source_colours.jpg',quality=95)
 print('Prepared',len(rows),'candidates')
if __name__=='__main__':main()
