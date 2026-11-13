"""Create isolated workshop material variants; source masters and maps remain untouched."""
import json, shutil, time, traceback
from pathlib import Path
import unreal as u

ROOT=Path(u.Paths.project_dir()).resolve()
OUT=ROOT/'Saved/WorkshopQA'; OUT.mkdir(parents=True,exist_ok=True)
BACKUP=ROOT/'Saved/WorkshopBackups'/time.strftime('%Y%m%d-%H%M%S-materials')
A=u.EditorAssetLibrary; M=u.MaterialEditingLibrary
DEST='/Game/GrandTour/UI/Workshop'
report={'ok':False,'materials':[]}

def duplicate(source,name):
    path=DEST+'/'+name
    if A.does_asset_exist(path):
        src=ROOT/'Content'/(path.removeprefix('/Game/')+'.uasset')
        BACKUP.mkdir(parents=True,exist_ok=True); shutil.copy2(src,BACKUP/src.name)
        # Update existing isolated assets without deleting referenced packages.
        return A.load_asset(path), False
    result=A.duplicate_asset(source,path)
    assert result, path
    return result, True

def node(mat,cls,**props):
    obj=M.create_material_expression(mat,cls,-2100,-1200)
    for key,value in props.items(): obj.set_editor_property(key,value)
    return obj
def wire(src,out,dst,pin): assert M.connect_material_expressions(src,out,dst,pin),pin
def custom_input(name):
    pin=u.CustomInput();pin.set_editor_property('input_name',name);return pin
def colour_graph(mat):
    # Older rebuilds left disconnected duplicates at identical graph coordinates.
    seen=set();pending=[M.get_material_property_input_node(mat,u.MaterialProperty.MP_BASE_COLOR)]
    while pending:
        expr=pending.pop()
        if not expr or expr in seen:continue
        seen.add(expr);pending.extend(M.get_inputs_for_material_expression(mat,expr))
    return list(seen)
def finish(mat):
    errors=M.recompile_material(mat); assert not errors,list(errors)
    stats=M.get_statistics(mat)
    assert stats.num_pixel_shader_instructions>0,'Material has no GPU shader'
    assert A.save_loaded_asset(mat)
    report['materials'].append({'path':mat.get_path_name(),'pixel_instructions':stats.num_pixel_shader_instructions})

try:
    mat,fresh=duplicate('/Game/GrandTour/Materials/M_GT_Vehicle','M_GT_WorkshopVehicle')
    nodes=M.get_material_expressions(mat)
    if not any(isinstance(e,u.MaterialExpressionScalarParameter) and str(e.get_editor_property('parameter_name'))=='WorkshopPaintAmount' for e in nodes):
        albedo=next(e for e in nodes if isinstance(e,u.MaterialExpressionTextureSampleParameter2D) and str(e.get_editor_property('parameter_name'))=='PaintAlbedo')
        lit=next(e for e in nodes if isinstance(e,u.MaterialExpressionLinearInterpolate) and M.get_material_expression_node_position(e)==(-1250,-850))
        tint=node(mat,u.MaterialExpressionVectorParameter,parameter_name='WorkshopPaint',default_value=u.LinearColor(.2,.25,.12,1))
        amount=node(mat,u.MaterialExpressionScalarParameter,parameter_name='WorkshopPaintAmount',default_value=0.)
        custom=node(mat,u.MaterialExpressionCustom,description='Workshop / painted panels only',output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,
            inputs=[custom_input(n) for n in ['Original','Tint','Amount']],code='''
float hi=max(Original.r,max(Original.g,Original.b));
float lo=min(Original.r,min(Original.g,Original.b));
// Saturated paint is recoloured; neutral edging, rubber and bright worn edges survive.
float mask=smoothstep(.045,.16,hi-lo)*smoothstep(.02,.08,hi);
float luminance=dot(Original,float3(.2126,.7152,.0722));
float3 recoloured=Tint.rgb*clamp(luminance/.24,.35,1.8);
return lerp(Original,recoloured,saturate(Amount)*mask);
''')
        wire(albedo,'RGB',custom,'Original');wire(tint,'',custom,'Tint');wire(amount,'',custom,'Amount');wire(custom,'',lit,'A')
    # Connect the active colour path, even when recovering a previously generated variant.
    live=colour_graph(mat)
    albedo=next(e for e in live if isinstance(e,u.MaterialExpressionTextureSampleParameter2D) and str(e.get_editor_property('parameter_name'))=='PaintAlbedo')
    lit=next(e for e in live if isinstance(e,u.MaterialExpressionLinearInterpolate) and M.get_material_expression_node_position(e)==(-1250,-850))
    custom=next(e for e in M.get_material_expressions(mat) if isinstance(e,u.MaterialExpressionCustom) and 'float3 recoloured=' in e.get_editor_property('code'))
    wire(albedo,'RGB',custom,'Original');wire(custom,'',lit,'A')
    assert custom in colour_graph(mat),'Workshop recolour must reach BaseColor'
    report['paint_graph']={}
    for expr in M.get_material_expressions(mat):
        entry={'class':expr.get_class().get_name(),'position':M.get_material_expression_node_position(expr),
            'inputs':{str(k):v.get_name() if v else None for k,v in zip(M.get_material_expression_input_names(expr),M.get_inputs_for_material_expression(mat,expr))}}
        if isinstance(expr,(u.MaterialExpressionScalarParameter,u.MaterialExpressionVectorParameter,u.MaterialExpressionTextureSampleParameter2D)):entry['parameter']=str(expr.get_editor_property('parameter_name'))
        if isinstance(expr,u.MaterialExpressionCustom):entry['code']=expr.get_editor_property('code')
        report['paint_graph'][expr.get_name()]=entry
    report['paint_output']=M.get_material_property_input_node(mat,u.MaterialProperty.MP_BASE_COLOR).get_name()
    finish(mat)
    # Include the actual course's coating override, preserving its mud normal graph.
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    assert level.load_level('/Game/GrandTour/ArtTests/RallyHandling/L_RallyHandling')
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    sources={'/Game/GrandTour/Materials/M_GT_Tyre'}
    for surface in u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface):
        source=surface.get_editor_property('tyre_coating_material')
        if source: sources.add(source.get_path_name().split('.')[0])
    for source in sorted(sources):
        mat,fresh=duplicate(source,'M_GT_WorkshopTyre_'+source.rsplit('/',1)[-1])
        nodes=M.get_material_expressions(mat)
        shader=next(e for e in colour_graph(mat) if isinstance(e,u.MaterialExpressionCustom) and 'float rim = ' in e.get_editor_property('code'))
        if 'float treadFace=' not in shader.get_editor_property('code'):
            shader.set_editor_property('inputs',list(shader.get_editor_property('inputs'))+[custom_input('WorkshopTread')])
            code=shader.get_editor_property('code')
            needle='float3 base = lerp(RubberColour.rgb, RimColour.rgb, rim);'
            assert needle in code
            code=code.replace(needle,needle+'''
// Broad blocks on the tread face, in rest-pose coordinates so they rotate with the wheel.
float angle=atan2(p.z-WheelGeom.z,p.x-(front?axF:axR));
float treadFace=(1.0-smoothstep(.45,.8,abs(n.y)))*smoothstep(.82,.94,r);
float row=floor((p.y+200.0)/7.0);
float block=step(.23,frac(angle*14.0+row*.5))*step(.18,frac((p.y+200.0)/7.0));
base*=lerp(1.0,lerp(.28,1.22,block),treadFace*saturate(WorkshopTread));
''')
            shader.set_editor_property('code',code)
            amount=next((e for e in nodes if isinstance(e,u.MaterialExpressionScalarParameter) and str(e.get_editor_property('parameter_name'))=='WorkshopTread'),None)
            if not amount:amount=node(mat,u.MaterialExpressionScalarParameter,parameter_name='WorkshopTread',default_value=0.)
            wire(amount,'',shader,'WorkshopTread')
        finish(mat)
    report['ok']=True
except Exception:
    report['error']=traceback.format_exc();u.log_error(report['error'])
finally:
    (OUT/'setup.json').write_text(json.dumps(report,indent=2))
    u.SystemLibrary.quit_editor()
