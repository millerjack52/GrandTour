exec(compile(open('C:/GrandTour/Art/VehicleTools/prado_lamp_audit_inspect.py').read().split("render('rear-v08'")[0],'<audit_setup>','exec'))
from mathutils.bvhtree import BVHTree
c=Vector((.17,.43,.255))*5;cam.location=c+Vector((1.7,3,.4))*5;cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=1.0;bpy.context.view_layer.update()
body=bpy.data.objects['Prado | fixed shell and underbody'];vs=[body.matrix_world@v.co for v in body.data.vertices];ps=[list(p.vertices) for p in body.data.polygons];tree=BVHTree.FromPolygons(vs,ps)
for x,y in [(659,414),(670,418),(680,420),(682,934),(672,943),(690,944),(681,955),(680,419),(654,408),(704,413),(709,432)]:
 orig=cam.matrix_world@Vector(((x/1600-.5)*1.0,(.5-y/1300)*(1300/1600),0));dire=cam.matrix_world.to_3x3()@Vector((0,0,-1));p,n,i,d=tree.ray_cast(orig,dire)
 if p is not None:print('PICK',x,y,'face',i,'point',list(p/5),'normal',list(n),'vertices',[list(vs[j]/5) for j in ps[i]])
