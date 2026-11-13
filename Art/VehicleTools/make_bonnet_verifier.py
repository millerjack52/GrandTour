from pathlib import Path
p=Path('C:/GrandTour/Art/VehicleTools')
s=(p/'verify_pathfinder_exterior.py').read_text()
s=s.replace('Pathfinder_Exterior.blend','Pathfinder_Bonnet_Wheels.blend').replace("out/'component-manifest.json'","out/'parent-component-manifest.json'")
s=s.replace("tree=bvh(o);vs,_=geom(o);cx,cy,cz=o['centre'];r=max(math.hypot(v.y-cy,v.z-cz) for v in vs)","tree=bvh(o);vs,_=geom(o);cx,cy,cz=o['centre'];tread=bpy.data.objects[o.name.replace('tyre envelope','tread blocks')];tv,_=geom(tread);r=max(math.hypot(v.y-cy,v.z-cz) for v in vs+tv)")
s=s.replace("if tree.overlap(t):crossings.append([o.name,n])","if tree.overlap(t) or bvh(tread).overlap(t):crossings.append([o.name,n])")
s=s.replace("expected=manifest.get('saved_primary_hashes',manifest.get('primary_hashes',{}));hash_mismatch=[]","refinement=json.loads((out/'refinement-manifest.json').read_text());expected=refinement['protected_hashes'];hash_mismatch=[]")
s=s.replace("report={'stage'",'''# Test whole interpolated wing boundary against the original side skin.
wing_joins=[]
for side,label in [(-1,'Right'),(1,'Left')]:
    ob=bpy.data.objects[label+' | fitted front wing top']
    skin=next(o for o in skins if o.name.startswith(label))
    raw=BVHTree.FromPolygons([v.co for v in skin.data.vertices],[tuple(p.vertices) for p in skin.data.polygons])
    ids=list(range(8 if side>0 else 0,len(ob.data.vertices),9));dist=[]
    for a,b in zip(ids,ids[1:]):
        for t in [0,.25,.5,.75,1]:dist.append(raw.find_nearest(ob.data.vertices[a].co.lerp(ob.data.vertices[b].co,t))[3])
    wing_joins.append({'side':label,'samples':len(dist),'maximum_distance_m':max(dist)})
hood=bpy.data.objects['Bonnet | defined crown and shoulder folds'];rows=refinement['bonnet_side_boundary_rows'];cols=len(hood.data.vertices)//rows;gap=[]
for side,label in [(-1,'Right'),(1,'Left')]:
    wing=bpy.data.objects[label+' | fitted front wing top']
    for j in range(rows):
        h=hood.data.vertices[j*cols+(cols-1 if side>0 else 0)].co
        w=wing.data.vertices[j*9+(0 if side>0 else 8)].co;gap.append((h-w).length)
source_unchanged=hashlib.sha256(Path(refinement['source']).read_bytes()).hexdigest()==refinement['source_sha256']
report={'wing_to_body_joins':wing_joins,'hood_wing_reveal_m':{'min':min(gap),'max':max(gap)},'source_unchanged':source_unchanged,'stage' ''')
s=s.replace("'Exterior detail study, no interior/rig/export certification'","'Bonnet and wheel revision, no interior/rig/export certification'")
s=s.replace("report['passed']=not crossings","report['passed']=source_unchanged and all(r['maximum_distance_m']<.001 for r in wing_joins) and min(gap)>.0029 and max(gap)<.0031 and not crossings")
(p/'verify_pathfinder_bonnet_wheels.py').write_text(s)
