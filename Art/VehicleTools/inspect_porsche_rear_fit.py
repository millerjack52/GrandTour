import bpy,numpy as np,json
bpy.ops.wm.open_mainfile(filepath='C:/GrandTour/Art/Export/VehicleTools/porsche-completion-v04/Porsche_Safari_Review.blend')
o=bpy.data.objects['Rear glass'];ps=np.array([list(v.co) for v in o.data.vertices]);x,y,z=ps.T
A=np.column_stack([np.ones(len(x)),x,z,x*x,x*z,z*z]);coef=np.linalg.lstsq(A,y,rcond=None)[0];err=y-A@coef
print('FIT',json.dumps({'coef':coef.tolist(),'rms':float(np.std(err)),'max':float(abs(err).max()),'bounds':[[float(v) for v in ps.min(axis=0)],[float(v) for v in ps.max(axis=0)]]}))
