"""Digitize visible priority features in registered aerial, anchored by user house coordinate."""
from pathlib import Path
import json,numpy as np
from PIL import Image,ImageDraw
from shapely.geometry import Polygon,LineString,mapping
from rasterio.features import rasterize
from affine import Affine
D=Path('Art/Export/LidarStudy/Reference');p=D/'aligned-features.json';data=json.loads(p.read_text());data['features']=[f for f in data['features'] if f['properties'].get('source')!='priority aerial']
# Points read in the displayed 1182x2048 reference, transformed to original extent.
def xy(p):return [1196250+p[0]*750/1182-1197144.5,4865011.5-(4865500-p[1]*1300/2048)]
road=[[170,2048],[350,1955],[450,1885],[570,1840],[670,1800],[720,1760],[738,1720],[742,1640],[759,1590],[760,1540],[747,1480],[733,1420],[716,1350],[701,1280],[691,1220],[691,1185],[679,1155],[655,1125],[638,1100],[635,1074],[640,1040],[650,1000],[655,977],[649,956],[626,958],[591,967],[560,981],[541,1003],[522,1033],[505,1072],[495,1107],[485,1131],[473,1134],[458,1110],[448,1075],[429,1034],[416,1005],[405,970],[397,930],[384,893],[375,859],[368,826],[372,787],[384,747],[403,718],[432,694],[468,673],[498,647],[518,619],[535,593],[562,567],[583,543],[592,519],[597,495],[596,469],[587,440],[577,410],[574,383],[582,360],[590,346]]
spur=[[649,956],[657,924],[637,889],[600,873],[566,862],[528,845],[524,832],[557,820],[592,800],[634,774],[676,749],[705,729]]
clearings=[[[800,417],[880,444],[1004,475],[1050,541],[1114,583],[1127,683],[1102,729],[1015,740],[875,734],[750,732],[710,718],[698,647],[720,567],[763,520]],[[855,238],[934,236],[1015,219],[1090,225],[1105,335],[1073,349],[1008,319],[950,288],[892,289]],[[167,869],[232,880],[275,930],[302,990],[342,1030],[373,1082],[390,1163],[405,1234],[410,1345],[300,1393],[207,1407],[81,1384],[15,1329],[23,1227],[1,1150],[87,1172],[142,1179],[210,1289],[262,1323],[266,1233],[240,1179],[209,1118],[194,1065],[179,1010],[143,970],[126,924]],[[568,991],[615,978],[638,995],[631,1050],[625,1090],[643,1125],[684,1170],[683,1200],[602,1187],[549,1157],[520,1118],[537,1049]],[[872,1110],[919,1110],[988,1151],[1078,1206],[1063,1254],[1026,1325],[970,1366],[902,1390],[800,1395],[746,1373],[728,1291],[708,1216],[767,1177],[813,1133]],[[420,1260],[687,1240],[715,1364],[728,1423],[688,1481],[681,1544],[637,1572],[504,1582],[452,1645],[400,1645],[347,1599],[320,1510],[298,1443]],[[559,332],[575,312],[603,320],[624,343],[609,376],[574,388]],[[547,778],[530,749],[554,708],[571,686],[591,702],[578,754],[566,806],[603,807],[695,748],[718,762],[654,804],[575,850],[526,850],[509,822]]]
pond=[[669,932],[700,935],[720,954],[712,976],[690,979],[681,1002],[669,995],[662,971],[660,949]]
def add(kind,name,geom):data['features'].append(dict(type='Feature',properties=dict(kind=kind,name=name,source='priority aerial',accuracy='Approximately 2-5m visual digitization; not a survey'),geometry=mapping(geom)))
add('road','Riverside access',LineString([xy(v) for v in road]));add('road','Pond field spur',LineString([xy(v) for v in spur]));add('pond','Access-road pond',Polygon([xy(v) for v in pond]));add('house','User house anchor',__import__('shapely').geometry.Point(-522.6444549,-262.5674983))
p.write_text(json.dumps(data))
fm=np.array(Image.open(D/'forest-mask.png'));A=Affine(3700/2048,0,-1850,0,3700/2048,-1850)
# Only alter the digitized clearing interiors; the wider mapped forest remains intact.
clear=rasterize([(Polygon([xy(v) for v in poly]).buffer(0),1) for poly in clearings],out_shape=fm.shape,transform=A,dtype='uint8')
fm[clear>0]=0;Image.fromarray(fm).save(D/'forest-mask.png')
(D/'priority-digitization.json').write_text(json.dumps(dict(house_latlon=[-46.24619444444444,167.767],house_world_cm=[-52264.44549,-26256.74983],reference='priority-aerial.jpg',extent='priority-extent.json',source='Esri World Imagery; reference only, not shipped as terrain texture',roads=[road,spur],clearings=clearings,pond=pond),indent=2))
print('Priority access road, pond, house anchor and clearing outlines registered')
