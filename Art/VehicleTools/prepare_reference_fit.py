"""Prepare explicit image-space observations, never invent measured blueprints.
Pixel annotations are editable estimates. Original A hero outranks generated views.
"""
from pathlib import Path
import json,math
import numpy as np
from PIL import Image
OUT=Path('C:/GrandTour/Art/Export/VehicleTools/reference-fit-v01');OUT.mkdir(exist_ok=True)
REF=Path('C:/GrandTour/Art/References/Vehicles/BoardDerived_2026-09-30')
sheet=Image.open(REF/'01-crafted-utility-views.png');board=Image.open(REF/'00-user-source-board.png')
sheet.crop((20,100,860,500)).save(OUT/'side-reference.png')
sheet.crop((30,545,435,915)).save(OUT/'front-reference.png')
board.crop((0,100,513,450)).save(OUT/'original-a-reference.png')
# Side annotations in ORIGINAL sheet coordinates, including intentionally curved
# roof/bonnet and the window opening, rather than only a bounding rectangle.
traces={
 'roof_crown':[[367,133],[376,126],[400,120],[454,116],[520,114],[630,114],[717,116],[758,121],[774,130]],
 'roof_gutter':[[363,135],[395,136],[520,134],[640,135],[744,137],[779,139]],
 'bonnet_silhouette':[[58,270],[67,257],[79,247],[105,240],[146,234],[192,230],[240,227],[275,226],[295,227]],
 'bonnet_shoulder':[[60,269],[133,264],[216,258],[294,251]],
 'belt':[[300,239],[490,238],[650,238],[829,236]],
 'sill':[[240,375],[400,377],[583,377]],
 'front_arch':[[87,329],[98,313],[120,298],[146,290],[174,290],[201,299],[223,315],[237,340]],
 'rear_arch':[[588,339],[605,314],[628,298],[653,290],[678,291],[704,302],[724,323],[738,352]],
 'windscreen_rake':[[299,235],[367,138]],
 'rear_rake':[[779,140],[829,234]],
 'front_window':[[309,232],[487,232],[490,144],[374,145],[309,224]],
 'rear_window':[[505,231],[641,231],[628,144],[507,144],[505,231]],
 'cargo_window':[[662,231],[785,231],[750,145],[644,145],[662,231]],
}
scale=(658-162)/2.64
side=dict(width=840,height=400,crop=[20,100,860,500],pixels_per_metre=scale,
          axle_front_world=-1.39,axle_rear_world=1.25,axle_z=.405,
          front_hub_px=[142,291],rear_hub_px=[638,291],uncertainty_px=3,
          projection='Approximate orthographic registration using two wheel hubs, uniform scale only',
          traces={k:[[u-20,v-100] for u,v in pts] for k,pts in traces.items()})
# Front is a supporting image only. Its camera is not treated as a measured ortho.
front=dict(width=405,height=370,pixels_per_metre=177,center_u=201,ground_v=355,
           status='Provisional front registration. Generated front has visible hood/roof; not calibrated perspective.',
           traces={'roof':[[74,37],[81,28],[116,22],[169,19],[226,19],[285,22],[319,27],[326,36]],
                   'cabin':[[49,128],[79,40],[320,40],[347,128]],
                   'bonnet':[[28,170],[38,139],[56,129],[96,123],[107,120],[284,120],[300,125],[344,130],[359,145],[369,170]]})

def project(params,points,w=513,h=350):
    yaw,pitch,dist,dx,dy=params;yaw=math.radians(yaw);pitch=math.radians(pitch)
    target=np.array([0.,.12,.90]);eye=target+dist*np.array([math.sin(yaw)*math.cos(pitch),-math.cos(yaw)*math.cos(pitch),math.sin(pitch)])
    f=(target-eye);f/=np.linalg.norm(f);right=np.cross(f,[0,0,1]);right/=np.linalg.norm(right);up=np.cross(right,f)
    q=np.asarray(points)-eye;depth=q@f;focal=w*60/36
    return np.column_stack([w/2+dx+focal*(q@right)/depth,h/2+dy-focal*(q@up)/depth]),eye,target

def fit(points,observed,weights):
    # Small bounded least-squares camera-only fit; geometry is never modified.
    # The original visibly shows the roof: disallow the below-roof camera that
    # fitting the partly hidden far wheel alone would otherwise propose.
    lo=np.array([15,8,5,-150,-150]);hi=np.array([75,25,20,150,150]);best=None
    for yaw in [25,40,55]:
        x=np.array([yaw,9.,10.,0.,0.]);lam=.1
        for _ in range(160):
            pred,_,_=project(x,points);r=((pred-observed)*weights[:,None]).ravel();cost=r@r
            j=np.empty((len(r),5));steps=[.01,.01,.001,.02,.02]
            for k,step in enumerate(steps):
                xx=x.copy();xx[k]+=step;j[:,k]=(((project(xx,points)[0]-pred)*weights[:,None])/step).ravel()
            delta=np.linalg.solve(j.T@j+lam*np.diag(np.maximum(np.diag(j.T@j),1e-5)),-j.T@r)
            xx=np.clip(x+delta,lo,hi);rr=((project(xx,points)[0]-observed)*weights[:,None]).ravel()
            if rr@rr<cost:x=xx;lam=max(1e-8,lam*.5)
            else:lam=min(1e8,lam*4)
            if np.linalg.norm(delta)<1e-7:break
        pred,eye,target=project(x,points);cost=float(np.sum(((pred-observed)*weights[:,None])**2))
        if best is None or cost<best[0]:best=(cost,x,pred,eye,target)
    return best
# Original-board wheel anchors. Far front hub is partly occluded: reduced weight.
points=np.array([[.935,-1.39,.405],[.935,1.25,.405],[-.935,-1.39,.405],[.88,-1.39,.81],[.88,-1.39,0]])
pixels=np.array([[302,273],[449,238],[98,270],[293,215],[293,333]])
weights=np.array([1.,1.,.45,.35,.6]);cost,pars,pred,eye,target=fit(points,pixels,weights)
hero=dict(width=513,height=350,lens_mm=60,sensor_mm=36,parameters=pars.tolist(),location=eye.tolist(),target=target.tolist(),
          shift_x=-float(pars[3])/513,shift_y=float(pars[4])/513,
          points=points.tolist(),observed=pixels.tolist(),predicted=pred.tolist(),weights=weights.tolist(),
          weighted_rms_px=float(math.sqrt(cost/(len(points)*2))),
          status='Provisional camera fitted to wheel observations, with elevation >=8 degrees because the source shows the roof. Focal length fixed. Not proof of a unique camera or exact image geometry.')
hero['active_fit_bounds']=['elevation_lower'] if abs(pars[1]-8)<.001 else []
hero['shape_optimization_allowed']=False
# Synthetic camera recovery checks that the solver can lower known projection error.
truth=np.array([39.,11.,9.4,4.,-3.]);synthetic=project(truth,points)[0]
test=fit(points,synthetic,np.ones(5));assert np.max(np.abs(test[2]-synthetic))<.02
data=dict(source_priority=['original-a-reference.png','side-reference.png','front-reference.png'],
          side=side,front=front,hero=hero,
          constraints='Manual reference traces have pixel uncertainty; side/front are generated and may disagree. Fix camera first, then freeze it during shape comparisons. Do not optimize shape to one view only.',
          tests={'synthetic_camera_max_error_px':float(np.max(np.abs(test[2]-synthetic)))})
(OUT/'reference-observations.json').write_text(json.dumps(data,indent=2))
print(json.dumps({'hero_parameters':hero['parameters'],'hero_rms':hero['weighted_rms_px'],'tests':data['tests']},indent=2))
