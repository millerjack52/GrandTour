"""RS2 road pigment pass. Changes two colour nodes in the LiDAR materials only.

Live geometry, normals, roughness, water, wheel contact and masks stay connected.
"""
from pathlib import Path
import unreal as u
import sys, json, hashlib, shutil, time, traceback, gc
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_life_materials import Graph, props
BASE='/Game/GrandTour/ArtTests/LidarStudy'
OUT=ROOT/'Art/Export/LidarStudy/Place'
QA=ROOT/'Saved/LidarAuthoringQA/RS2'
VERSION='rs2-1'
mel=u.MaterialEditingLibrary;assets=u.EditorAssetLibrary
COLOUR_TAGS={'RD1Gravel','LT4Final'}
NOISE='''struct RS2Field {
float h(float2 p){uint2 q=uint2(int2(p));uint h=q.x*374761393u+q.y*668265263u;h=(h^(h>>13))*1274126177u;return float((h^(h>>16))&0x00ffffffu)/16777215.0;}
float n(float2 p){float2 i=floor(p),f=frac(p);f=f*f*(3-2*f);return lerp(lerp(h(i),h(i+float2(1,0)),f.x),lerp(h(i+float2(0,1)),h(i+1),f.x),f.y);}
};RS2Field rs2;
'''
GRAVEL=NOISE+'''// RS2: quiet stone contrast, warm-neutral binder, softer wheel lanes.
float2 uvC=saturate((P.xy+185000)/370000);
float4 style=Texture2DSampleLevel(Style,StyleSampler,uvC,0);
float ad=abs((Texture2DSampleLevel(LidarClay,LidarClaySampler,uvC,0).a-.5)*6.4);
float gw=1-smoothstep(2.0,2.6,ad);
float grassMix=smoothstep(.12,.6,style.g);
[branch] if(gw<.002)return Native;
float3 gr=lerp(GravelA,GravelB,.30);
float lum=dot(gr,float3(.2126,.7152,.0722));
float3 target=float3(.235,.224,.202);
gr=lerp(lum.xxx,gr,.20)*(target/float3(.1185,.1097,.1021));
// Keep individual stone shapes while compressing photographic black/white grain.
gr=max(0,target+(gr-target)*.66);
float patch=rs2.n(P.xy/720.);
gr*=lerp(.94,1.06,patch);
float wl=1-smoothstep(.10,.30,abs(ad-.82));
wl*=lerp(.55,1,rs2.n(P.xy/3.1+9.));
gr*=1-.18*wl;
float shoulder=smoothstep(1.25,2.40,ad);
gr*=lerp(float3(1,1,1),float3(1.04,1.015,.96),shoulder*.5);
return lerp(Native,gr,gw*(1-grassMix));
'''
MUD=NOISE+'''// RS2: retain native churn pigment and its live relief, lift dark midtones.
float coverage=saturate(Coverage*Strength);
[branch] if(coverage<.001)return Base;
float3 pigment=pow(max(NativeRoad,0),.88)*float3(1.00,.965,.90);
float lum=dot(pigment,float3(.2126,.7152,.0722));
pigment=lerp(lum*float3(1.10,.98,.83),pigment,.85);
float broad=rs2.n(P.xy/460.);
pigment*=lerp(.96,1.05,broad);
// State is the existing native field: R vertical displacement, A disturbance.
// Material shading only: no physical depth/wetness or simulation writes.
float rut=saturate(-State.r/10.)*saturate(State.a);
float lip=saturate(State.r/6.)*saturate(State.a);
pigment*=lerp(1.,.82,rut)*lerp(1.,1.10,lip);
return lerp(Base,pigment,coverage);
'''

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def tagged(m,tag):
    hits=[n for n in mel.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('desc'))==tag]
    assert len(hits)==1,(m.get_name(),tag,len(hits))
    return hits[0]

def protected(m):
    codes={n.get_name():hashlib.sha256(str(n.get_editor_property('code')).encode()).hexdigest()
           for n in mel.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom)
           and str(n.get_editor_property('desc')) not in COLOUR_TAGS}
    connections={}
    for name in ('BASE_COLOR','NORMAL','ROUGHNESS','WORLD_POSITION_OFFSET','OPACITY_MASK','EMISSIVE_COLOR'):
        prop=getattr(u.MaterialProperty,'MP_'+name)
        node=mel.get_material_property_input_node(m,prop)
        connections[name]=[str(node.get_editor_property('desc')) or node.get_class().get_name() if node else None,str(mel.get_material_property_input_node_output_name(m,prop)) if node else '']
    return dict(other_shader_programs=codes,output_connections=connections)

def patch_material(m):
    before=protected(m)
    gravel=tagged(m,'RD1Gravel');mud=tagged(m,'LT4Final')
    # Preserve the exact pre-pass code for an inspectable restoration source.
    for node in (gravel,mud):
        key='RS2Original:'+str(node.get_editor_property('desc'))
        if not assets.get_metadata_tag(m,key):assets.set_metadata_tag(m,key,str(node.get_editor_property('code')))
    gravel.set_editor_property('code',GRAVEL)
    nodes=list(mel.get_material_expressions(m))
    main=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and 'float3 rich=' in n.get_editor_property('code'))
    assert 'RR1State' in [str(v.get_editor_property('output_name')) for v in main.get_editor_property('additional_outputs')]
    g=Graph(m,'RS2Position')
    position=next((n for n in nodes if str(n.get_editor_property('desc'))=='RS2Position'),None)
    if position is None:position=g.node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    names=[str(i.get_editor_property('input_name')) for i in mud.get_editor_property('inputs')]
    if not all(n in names for n in ('P','State')):
        # Build off the live output chain. Adding an unwired named input to the
        # connected custom node triggers an immediate error compile in UE.
        old=mud;links=list(mel.get_inputs_for_material_expression(m,old))
        assert names==['Base','NativeRoad','Coverage','Strength'] and len(links)==4 and all(links)
        mud=Graph(m,'LT4Final').custom(names+['P','State'],MUD)
        # The native program uses non-default outputs for pigment and mask.
        g.wire(links[0],mud,'Base')
        g.wire(main,mud,'NativeRoad','LT4Colour');g.wire(main,mud,'Coverage','LT4Coverage')
        g.wire(links[3],mud,'Strength')
        g.wire(position,mud,'P');g.wire(main,mud,'State','RR1State')
        for consumer in nodes:
            incoming=list(mel.get_inputs_for_material_expression(m,consumer))
            if old not in incoming:continue
            pins=[str(i.get_editor_property('input_name')) for i in consumer.get_editor_property('inputs')] if isinstance(consumer,u.MaterialExpressionCustom) else [str(n) for n in mel.get_material_expression_input_names(consumer)]
            assert len(pins)==len(incoming)
            for pin,source in zip(pins,incoming):
                if source==old:g.wire(mud,consumer,pin)
        if mel.get_material_property_input_node(m,u.MaterialProperty.MP_BASE_COLOR)==old:g.output(mud,u.MaterialProperty.MP_BASE_COLOR)
        mel.delete_material_expression(m,old)
    g.wire(position,mud,'P');g.wire(main,mud,'State','RR1State')
    mud.set_editor_property('code',MUD)
    assert protected(m)==before,('Non-colour program or output connection changed',m.get_name())
    assert not mel.recompile_material(m),m.get_name()
    assets.set_metadata_tag(m,'RS2Version',VERSION);assert assets.save_loaded_asset(m,False)
    return dict(material=m.get_path_name(),preserved=before,nodes=len(mel.get_material_expressions(m)),gravel_sha256=hashlib.sha256(GRAVEL.encode()).hexdigest(),mud_sha256=hashlib.sha256(MUD.encode()).hexdigest())

def apply():
    return [patch_material(u.load_asset(BASE+'/M_'+n)) for n in ('Terrain','Detail')]

def validate():
    rows=[]
    for name in ('Terrain','Detail'):
        m=u.load_asset(BASE+'/M_'+name);assert assets.get_metadata_tag(m,'RS2Version')==VERSION
        assert str(tagged(m,'RD1Gravel').get_editor_property('code'))==GRAVEL
        assert str(tagged(m,'LT4Final').get_editor_property('code'))==MUD
        names=[str(i.get_editor_property('input_name')) for i in tagged(m,'LT4Final').get_editor_property('inputs')]
        links=list(mel.get_inputs_for_material_expression(m,tagged(m,'LT4Final')))
        assert len(links)==len(names) and all(links),(name,'Disconnected mud input')
        rows.append(dict(material=name,preserved=protected(m),nodes=len(mel.get_material_expressions(m))))
    return rows

if __name__=='__main__':
    QA.mkdir(parents=True,exist_ok=True)
    report=dict(ok=False,version=VERSION);busy=False;deadline=0
    def save():(QA/'install.json').write_text(json.dumps(report,indent=2))
    def run():
        content=ROOT/'Content/GrandTour/ArtTests/LidarStudy'
        backup=ROOT/'Saved/LidarAuthoringBackups'/('RS2-'+str(time.time_ns()));backup.mkdir(parents=True)
        for name in ('M_Terrain','M_Detail'):shutil.copy2(content/(name+'.uasset'),backup/(name+'.uasset'))
        report.update(backup=str(backup),map_sha256=digest(content/'L_LidarStudy.umap'));save()
        report['materials']=apply();save();yield 4
        # Reapplication must not accumulate graph nodes or change protected code.
        repeat=apply();assert repeat==report['materials'];yield 4
        report['validation']=validate()
        assert digest(content/'L_LidarStudy.umap')==report['map_sha256'],'Saved map changed'
        report.update(ok=True,idempotent=True,map_unchanged=True,owner_accepted=False);save()
        (OUT/'road-style.json').write_text(json.dumps(dict(version=VERSION,report=str(QA/'install.json')),indent=2))
        yield 3
    steps=run()
    def tick(dt):
        global busy,deadline,steps
        if busy:return
        busy=True
        try:
            if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
        except StopIteration:
            u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
        except Exception:
            report.update(ok=False,error=traceback.format_exc());save();u.log_error(report['error'])
            u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
        finally:busy=False
    u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
