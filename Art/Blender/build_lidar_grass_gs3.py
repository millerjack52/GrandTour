"""GS3: map-owned broad grass blades, authored LODs, no cards/textures/collision.
Run with Blender --background --python this_file. Units follow native_plant_lib.
Near: 48/32/18 curved blades (144/64/36 triangles), 70 cm root footprint.
Far: 36/12 blades (72/12 triangles), 2 m root footprint. One shared material slot.
"""
import bpy, math, random, json, sys
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import native_plant_lib as L
OUT=Path(__file__).resolve().parents[1]/'Export/LidarStudy/Place/GrassGS3'
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
mat=bpy.data.materials.new('Grass');mat.diffuse_color=(.19,.25,.095,1)
rows=[]
for variant in range(5):
    far=variant==3;verge=variant==4;name='SM_GS3_Verge' if verge else ('SM_GS3_Far' if far else 'SM_GS3_Near_'+chr(65+variant))
    rng=random.Random(73100+variant)
    design=[]
    for i in range(72 if verge else (36 if far else 48)):
        # Stratified roots avoid holes without a rigid visible lattice.
        side=9 if verge else (6 if far else 7);span=1.0 if verge else (2.0 if far else .70)
        x=((i%side+rng.uniform(.1,.9))/side-.5)*span
        y=((i//side+rng.uniform(.1,.9))/side-.5)*span
        design.append((x,y,rng.uniform(.22,.57) if verge else rng.uniform(.27,.47),rng.uniform(.014,.027) if verge else (rng.uniform(.07,.13) if far else rng.uniform(.025,.05)),rng.uniform(0,math.tau),rng.uniform(.12,.30),rng.uniform(.90,1.1),rng.random()<(.20 if verge else .09)))
    lods=[]
    for lod,n in enumerate(([72,48,30] if verge else ([36,12] if far else [48,32,18]))):
        verts=[];faces=[];colors=[]
        chosen=[design[int(i*len(design)/n)] for i in range(n)]
        for x,y,h,w,ang,lean,tint,dry in chosen:
            w*=([1,2.3] if far else ([1,1.4,1.8] if verge else [1,1.35,1.7]))[lod]
            direction=Vector((math.cos(ang),math.sin(ang),0));cross=Vector((-direction.y,direction.x,0))
            base=Vector((x,y,-.025));mid=base+direction*lean*.33+Vector((0,0,h*.55));tip=base+direction*lean+Vector((0,0,h))
            # A curved five-vertex strip close up; tapered quads/triangles in lower LODs.
            points=[base-cross*w*.5,base+cross*w*.5,mid-cross*w*.34,mid+cross*w*.34,tip] if not far and lod==0 else ([base-cross*w*.5,base+cross*w*.5,tip] if far and lod==1 else [base-cross*w*.5,base+cross*w*.5,tip+cross*w*.10,tip-cross*w*.10])
            weights=[0,0,.55,.55,1] if len(points)==5 else ([0,0,1] if len(points)==3 else [0,0,1,1])
            start=len(verts);verts.extend(points)
            for weight in weights:
                low=(.070,.100,.038);high=(.225,.285,.112)
                if dry:low=(.105,.115,.055);high=(.30,.285,.16)
                colors.append(tuple((a+(b-a)*weight)*tint for a,b in zip(low,high))+(weight,))
            fs=[(0,1,2),(1,3,2),(2,3,4)] if len(points)==5 else ([(0,1,2)] if len(points)==3 else [(0,1,2),(0,2,3)])
            faces.extend(tuple(start+j for j in f) for f in fs)
        mesh=bpy.data.meshes.new(name+str(lod));mesh.from_pydata(verts,[],faces);mesh.update()
        vc=mesh.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
        for poly in mesh.polygons:
            for li in poly.loop_indices:vc.data[li].color=colors[mesh.loops[li].vertex_index]
        mesh.materials.append(mat)
        ob=bpy.data.objects.new(name+'_LOD'+str(lod),mesh);bpy.context.collection.objects.link(ob)
        L.export(ob,out=OUT)
        lods.append(dict(file=ob.name+'.fbx',triangles=len(faces),vertices=len(verts)))
        ob.hide_set(True)
    rows.append(dict(asset=name,far=far,verge=verge,lods=lods))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'GrassGS3.blend'))
(OUT/'manifest.json').write_text(json.dumps(dict(version='vq2-1',assets=rows),indent=2))
print('GS3_GEOMETRY_OK',[(r['asset'],[l['triangles'] for l in r['lods']]) for r in rows])
