"""VP2: bounded bank materials and plant shading; no mesh/map/physics edits."""
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
sys.path.insert(0, str(ROOT / 'Art/Unreal'))
from benmore_river_life_materials import Graph, props

BASE = '/Game/GrandTour/ArtTests/LidarStudy/FirstSection'
QA = ROOT / 'Saved/LidarAuthoringQA/VP2Materials'
MATERIALS = ['M_BankSurface', 'M_BankEarth', 'M_BankLeaf',
             'M_BankGroundLeaf', 'PerceivedDetail/M_PD_Fern']
mel = u.MaterialEditingLibrary
assets = u.EditorAssetLibrary

# A single coherent surface evaluation replaces the stacked RS7 + PD evaluation.
# At most four triplanar textures (12 samples), plus the unchanged edge/contact
# samples. No iterative parallax, extra textures, displacement or geometry.
SURFACE = r'''
float3 n=normalize(N),w=pow(abs(n),4);w/=max(.001,w.x+w.y+w.z);
float3 q=P-float3(-45800,-31600,4800);
float2 uv[3]={q.yz,q.xz,q.xy};
float3 soil=0,stone=0;float4 sn=0,rn=0;
for(int i=0;i<3;i++){
 float weight=i==0?w.x:i==1?w.y:w.z;
 soil+=Texture2DSample(Soil,SoilSampler,uv[i]/200).rgb*weight;
 stone+=Texture2DSample(Rock,RockSampler,uv[i]/110).rgb*weight;
 sn+=Texture2DSample(SoilNH,SoilNHSampler,uv[i]/200)*weight;
 rn+=Texture2DSample(RockNH,RockNHSampler,uv[i]/110)*weight;
}
float rock=smoothstep(.47,.73,C.b/max(C.r,.001));
float moss=smoothstep(.94,1.38,C.g/max(C.r,.001))*(1-rock);
float sv=dot(soil,float3(.3,.5,.2)),rv=dot(stone,float3(.3,.5,.2));
float colourDetail=lerp(clamp((sv-.055)*11+1,.62,1.6),
                       clamp((rv-.38)*3.2+1,.38,1.58),rock);
float4 data=lerp(sn,rn,rock);
// Height, occlusion and roughness describe the same authored small forms.
// Retain the inherited rock fissure relief; the new authored field supplies
// small mineral structure. Replacing the fissures with microdetail alone
// made the first candidate's exposed rock visibly too smooth.
Height=lerp(sn.b*4,rv*8+rn.b*.8,rock)*lerp(1,.65,moss);
float cavity=saturate(data.a);
float wet=(1-smoothstep(4400,4660,P.z))*(.65+.35*(1-cavity));
Rough=clamp(lerp(.86,.76,rock)+moss*.06+(1-cavity)*.12-wet*.17,.56,.96);
AO=lerp(.82,1,cavity);
// Keep the established pigment and modest variation; cavity shadow belongs
// primarily in AO, rather than being multiplied deeply into albedo again.
return C*colourDetail*lerp(.96,1.06,smoothstep(.12,.8,data.b))*(1-wet*.08);
'''

BUMP = r'''
float3 n=normalize(N),sx=ddx(P),sy=ddy(P);
float3 r1=cross(sy,n),r2=cross(n,sx);float det=dot(sx,r1);
float3 grad=(ddx(H)*r1+ddy(H)*r2)*sign(det)/max(abs(det),.00001);
// Pixel footprint and camera distance suppress detail that cannot be resolved.
float footprint=max(length(sx),length(sy));
float fade=(1-smoothstep(1400,3500,length(Camera-P)))*(1-smoothstep(2,9,footprint));
grad*=fade*.85;grad*=min(1.,.65/max(length(grad),.0001));
return normalize(n-grad);
'''

CONTACT = r'''
float2 p=P.xy-float2(-45800,-31600);
float2 ab=float2(.6*p.x-.8*p.y,-.8*p.x-.6*p.y);
float2 uv=float2(ab.x/2200+.5,.5-ab.y/1560);
float inside=(abs(ab.x)<1100 && abs(ab.y)<780)?1:0;
float occ=lerp(1,Texture2DSample(Contact,ContactSampler,uv).r,inside);
occ=lerp(1,occ,Strength);OutAO=min(OldAO,occ);
// Retain the static contact footprint, with less double-darkening under
// the restored dynamic plant shadows. This is not a directional light bake.
float covered=smoothstep(.08,.48,1-occ);
float mottled=.70+.30*sin(P.x*.047+sin(P.y*.051))*sin(P.y*.039);
float value=dot(OldColour,float3(.25,.6,.15));
float3 earth=float3(.18,.125,.065)*(value/.15);
return lerp(OldColour,earth,covered*mottled*.40)*(.64+.36*max(.3,occ));
'''

LEAF = r'''
float dry=saturate((C.r-C.g)*8+.08);
float tip=saturate(Tip);
// Age and position follow existing authored vertex data, not world-space noise.
Rough=lerp(lerp(.76,.61,tip),.86,dry);
Spec=lerp(.27,.16,dry);
Transmission=Colour*lerp(.22,.34,tip)*(1-dry*.45);
return Colour;
'''


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package(name):
    return ROOT / 'Content/GrandTour/ArtTests/LidarStudy/FirstSection' / (name+'.uasset')


def enabled():
    path=ROOT/'Art/Export/LidarStudy/FirstSection/MaterialPolish/recipe.json'
    return path.exists() and json.loads(path.read_text()).get('enabled',False)


def protect():
    QA.mkdir(parents=True, exist_ok=True)
    manifest=QA/'backup.json'
    if manifest.exists():
        return json.loads(manifest.read_text())
    backup=ROOT/'Saved/LidarAuthoringBackups'/('VP2Materials-'+str(time.time_ns()))
    paths=list((ROOT/'Content/GrandTour/ArtTests/LidarStudy/FirstSection').rglob('*.uasset'))
    paths += [ROOT/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap',
              ROOT/'Config/DefaultEngine.ini',ROOT/'Art/lidar_performance.json']
    hashes={}
    for path in paths:
        rel=path.relative_to(ROOT); dest=backup/rel
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
        hashes[str(rel)]=digest(path)
    record=dict(backup=str(backup),sha256=hashes,created=time.time())
    manifest.write_text(json.dumps(record,indent=2))
    return record


def ground(name):
    import peat_moss_ground
    if name=='M_BankSurface' and peat_moss_ground.enabled():
        return peat_moss_ground.ground()
    m=u.load_asset(BASE+'/'+name);assert m
    mel.delete_all_material_expressions(m)
    g=Graph(m,'VP2Ground')
    props(m,tangent_space_normal=False)
    p=g.node(u.MaterialExpressionWorldPosition)
    n=g.node(u.MaterialExpressionVertexNormalWS)
    vc=g.node(u.MaterialExpressionVertexColor)
    textures={
        'Soil':(BASE+'/T_BankSoilColour',False),
        'Rock':('/Game/GrandTour/ArtTests/BenmoreWoodland/T_tiles_rock_slope__d_a',True),
        'SoilNH':(BASE+'/PerceivedDetail/T_PD_SoilNH',True),
        'RockNH':(BASE+'/PerceivedDetail/T_PD_RockNH',True)}
    inputs={}
    for key,(path,linear) in textures.items():
        texture=u.load_asset(path);assert texture,path
        inputs[key]=g.node(u.MaterialExpressionTextureObject,texture=texture,
            sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR if linear else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    surf=g.custom(['C','P','N',*textures],SURFACE,outputs=[(k,u.CustomMaterialOutputType.CMOT_FLOAT1) for k in ['Height','Rough','AO']])
    for key,node in dict(C=vc,P=p,N=n,**inputs).items():g.wire(node,surf,key)
    g.output(surf,u.MaterialProperty.MP_BASE_COLOR)
    g.output(surf,u.MaterialProperty.MP_ROUGHNESS,'Rough')
    g.output(surf,u.MaterialProperty.MP_AMBIENT_OCCLUSION,'AO')
    bump=g.custom(['H','P','N','Camera'],BUMP)
    g.wire(surf,bump,'H','Height');g.wire(p,bump,'P');g.wire(n,bump,'N')
    g.wire(g.node(u.MaterialExpressionCameraPositionWS),bump,'Camera')
    g.output(bump,u.MaterialProperty.MP_NORMAL)
    g.output(g.scalar(.18),u.MaterialProperty.MP_SPECULAR)
    if name=='M_BankSurface':
        # Preserve the existing coverage calculation and clip value exactly.
        mask=g.custom(['A','P','EdgeTex'],'float n=Texture2DSample(EdgeTex,EdgeTexSampler,(P.xy-float2(-45800,-31600))*.032).g;return A-n*.98;',u.CustomMaterialOutputType.CMOT_FLOAT1)
        g.wire(vc,mask,'A','A');g.wire(p,mask,'P');g.wire(inputs['Rock'],mask,'EdgeTex')
        g.output(mask,u.MaterialProperty.MP_OPACITY_MASK)
        import fern_floor
        fern_floor.install_material()
        contact=next(x for x in mel.get_material_expressions(m) if isinstance(x,u.MaterialExpressionCustom) and str(x.get_editor_property('desc'))=='FFContact')
        contact.set_editor_property('code',CONTACT)
    assert not mel.recompile_material(m)
    assert assets.save_loaded_asset(m,False)
    return m


def leaf(name):
    m=u.load_asset(BASE+'/'+name);assert m
    # Idempotent: surface wrapper has no base-colour output and never stacks.
    for node in list(mel.get_material_expressions(m)):
        if str(node.get_editor_property('desc'))=='VP2Leaf':mel.delete_material_expression(m,node)
    g=Graph(m,'VP2Leaf')
    colour=mel.get_material_property_input_node(m,u.MaterialProperty.MP_BASE_COLOR)
    out=mel.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_BASE_COLOR)
    assert colour
    node=g.custom(['C','Tip','Colour'],LEAF,outputs=[('Rough',u.CustomMaterialOutputType.CMOT_FLOAT1),('Spec',u.CustomMaterialOutputType.CMOT_FLOAT1),('Transmission',u.CustomMaterialOutputType.CMOT_FLOAT3)])
    vc=g.node(u.MaterialExpressionVertexColor)
    g.wire(vc,node,'C');g.wire(vc,node,'Tip','A');g.wire(colour,node,'Colour',out)
    for prop,pin in [(u.MaterialProperty.MP_ROUGHNESS,'Rough'),(u.MaterialProperty.MP_SPECULAR,'Spec'),(u.MaterialProperty.MP_SUBSURFACE_COLOR,'Transmission')]:g.output(node,prop,pin)
    # Preserve the one species' proven UVs, geometry and baked self-occlusion.
    if name.endswith('M_PD_Fern'):
        for x in mel.get_material_expressions(m):
            if not isinstance(x,u.MaterialExpressionCustom) or str(x.get_editor_property('desc'))!='PDLeaf':continue
            code=x.get_editor_property('code')
            if 'float2 xy=' in code:x.set_editor_property('code','float2 xy=(T.rg*2-1)*.65;return normalize(float3(xy,sqrt(saturate(1-dot(xy,xy)))));')
            if 'T.a*SelfAO.x' in code:x.set_editor_property('code','return clamp(lerp(1,T.a*SelfAO.x,.70),.65,1);')
    assert not mel.recompile_material(m)
    assert assets.save_loaded_asset(m,False)


def run(mode='final'):
    assert mode in ['ground','leaf','final','check']
    import lidar_first_section as section
    record=protect();before=section.snapshot();outside=section.outside_snapshot()
    if mode in ['ground','final']:
        for name in MATERIALS[:2]:ground(name)
    if mode in ['leaf','final']:
        for name in MATERIALS[2:]:leaf(name)
    assert section.snapshot()==before and section.outside_snapshot()==outside
    allowed={str(package(n).relative_to(ROOT)) for n in MATERIALS}
    changed=[]
    for rel,sha in record['sha256'].items():
        if digest(ROOT/rel)!=sha:
            assert rel in allowed, 'Unexpected change: '+rel
            changed.append(rel)
    # Actual saved asset graph summary and engine-reported compiler statistics.
    graphs={}
    for name in MATERIALS:
        m=u.load_asset(BASE+'/'+name)
        stats=mel.get_statistics(m)
        graphs[name]=dict(nodes=len(mel.get_material_expressions(m)),
            compiler_statistics={k:stats.get_editor_property(k) for k in ['num_pixel_shader_instructions','num_vertex_shader_instructions','num_samplers','num_pixel_texture_samples']},
            shading_model=str(m.get_editor_property('shading_model')),
            two_sided=m.get_editor_property('two_sided'),
            normal_space='tangent' if m.get_editor_property('tangent_space_normal') else 'world',
            sha256=digest(package(name)))
    report=dict(ok=True,mode=mode,time=time.time(),local=before,outside=outside,
                changed_packages=changed,graphs=graphs,backup=record['backup'],
                map_geometry_config_unchanged=True)
    (QA/(mode+'-install.json')).write_text(json.dumps(report,indent=2))
    # Exact material-package variants, allowing fresh-process A/B without
    # rewinding unrelated trees, geometry, map edits or renderer configuration.
    if mode!='check':
        for name in MATERIALS:
            src=package(name);dst=QA/'Variants'/mode/src.relative_to(ROOT)
            dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
    print('VP2_MATERIALS_OK',json.dumps(report))
    return report
