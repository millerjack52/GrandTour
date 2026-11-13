"""Showcase-only host bridges. Source shader math is kept distinct from these fixes."""
import unreal as u
from benmore_river_life_materials import props
mel=u.MaterialEditingLibrary

def repair(m,kind):
    for e in mel.get_material_expressions(m):
        if not isinstance(e,u.MaterialExpressionCustom):continue
        c=e.get_editor_property('code')
        c=c.replace('float thickness=min(50,','float thickness=min(124,')
        c=c.replace('paint.r=saturate(paint.r*DepthScale);','paint.r=clamp(paint.r*DepthScale,0,2.48);')
        if kind in ['M_Soil','M_Tread']:
            c=c.replace('float3(.48,.68,.24)','float3(.52,.62,.36)')
        if kind=='M_Soil':
            # Terrain_003 retains its recovered optical arithmetic. The host
            # overlay coverage and final grade are authored: near-opaque grey
            # overlay hid the source dirt texture across the entire exposed bank.
            c=c.replace('float coverage=saturate(.8+field.a*.2);','float coverage=saturate(.45+field.a*.25);')
            c=c.replace('rich=lerp(rich,sandy,sandCover);','rich=lerp(rich,sandy*float3(.72,.60,.44),sandCover);')
        if kind=='M_Tread':
            # A ribbon vertex can lie between grid corners with different style masks.
            # Match each displaced corner's own mask, not the ribbon vertex's mask.
            c=c.replace('*saturate(1-sandCover-grassCover);\n float h=',
                '*saturate(1-dot(Texture2DSampleLevel(Style,StyleSampler,saturate(q),0).rg,float2(1,1)));\n float h=')
            # The source height map carries the tread detail; alpha is its outer footprint.
            # Retain native height/slip mixing and use its relief slope in the host
            # unlit lighting bridge. Original screen-space POM remains unported.
            old='float3 trackColour=trackBase*.86*lerp(float3(1,1,1),pigment,(.15*wet+.5)*relief);'
            new='''float3 turfTrack=Texture2DSample(Grass,GrassSampler,materialXY*.0012).rgb*float3(.52,.62,.36);
float exposedTrack=saturate(field.a*.75+max(0,-height)*.10);
turfTrack=lerp(turfTrack,oC0.rgb*float3(.8,.65,.43),exposedTrack);
trackBase=lerp(trackBase*float3(.96,.84,.68),turfTrack,grassCover);
float2 te=float2(1./256,0);
float slope=Texture2DSample(TrackHeight,TrackHeightSampler,tuv+te).r-Texture2DSample(TrackHeight,TrackHeightSampler,tuv-te).r;
float treadLight=clamp(1+slope*3.5*(1-TrackData.g),.60,1.25);
float3 trackColour=trackBase*.86*lerp(float3(1,1,1),pigment,(.15*wet+.5)*relief)*treadLight;'''
            if 'float3 turfTrack=' not in c:c=c.replace(old,new)
        if kind in ['M_Water','M_River']:
            # G is now signed on dry bank cells. Don't raise a dry cell to its bed,
            # and don't let a simulated crest turn an entirely dry cell into water.
            c=c.replace('float waterDepth=min(wave.g,max(0,Level+wave.r-baseBed-height));',
                'float shoreDepth=min(wave.g,Level+wave.r-baseBed-height); float waterDepth=max(0,shoreDepth);')
            c=c.replace('float waterDepth=max(0,wave.g);','float shoreDepth=wave.g; float waterDepth=max(0,shoreDepth);')
            # Host shallow-water field already carries the pressure/wake height.
            # Adding the native state height doubles that response. Keep native
            # sediment/foam transport; use the conserved field for surface geometry.
            c=c.replace('float nativeRippleCm=max(-waterDepth,(nativeState.r-.50195998)*80)*NativeWaterReady;',
                'float nativeRippleCm=0; // one physical height source in the UE bridge')
            c=c.replace('smoothstep(.05,.65,waterDepth)','smoothstep(.05,1.25,shoreDepth)')
            # Normalize the legacy shortcut before patch() replaces this entire
            # normal expression with recovered direction/speed lookup sampling.
            c=c.replace('float2 q=float2(dot(P.xy*.01,direction),dot(P.xy*.01,float2(-direction.y,direction.x)))*.14;',
                'float2 q=P.xy*.0014;')
            c=c.replace('n*=lerp(.2,1,fade)*saturate(depthM/.2);',
                'n*=fade*sqrt(saturate((length(movingFlow)-.02)*1.04166663))*saturate(depthM/.2); // Water_001 c42.w/c43.x speed envelope')
            c=c.replace('float2 slopes=direction*n.x+float2(-direction.y,direction.x)*n.y-',
                'float2 slopes=n-')
            # Native simulation normals must not be added on top of the physical
            # field's own height derivative after removing the duplicate height.
            c=c.replace(')*80*NativeWaterReady;',')*0;')
        if kind in ['M_WaterSim','M_Sediment']:
            # Canvas UVs are already texel-centred. The old c0 offset advected all
            # state half a cell per step even in still water.
            c=c.replace('float4 c0=float4(.5/FieldTexels.xy,0,0),c1=0;',
                'float4 c0=0,c1=0; // UE canvas UV is already at the texel centre')
            # Persistent source velocity is in WaterMap. Feeding it into the
            # transient state again every step prevents its native damping.
            c=c.replace('float2 disturbance=dot(flow,flow)>dot(old,old)?clamp(flow,-1,1):old;',
                'float2 disturbance=old;')
            c=c.replace('0,w.g*.01);','0,max(0,w.g)*.01);')
        e.set_editor_property('code',c)
    if kind in ['M_Water','M_River']:props(m,tangent_space_normal=False)
    if kind in ['M_Water','M_River']:
        from siberian_wave_materials import patch
        patch(m)
    assert not mel.recompile_material(m)
    u.EditorAssetLibrary.save_loaded_asset(m)
    return m

def grass(source,path):
    m=u.EditorAssetLibrary.load_asset(path) or u.EditorAssetLibrary.duplicate_asset(source,path)
    props(m,opacity_mask_clip_value=.25)
    for e in mel.get_material_expressions(m):
        if isinstance(e,u.MaterialExpressionCustom):
            e.set_editor_property('code',e.get_editor_property('code').replace('float3(.64,.95,.38)','float3(.62,.78,.46)'))
    assert not mel.recompile_material(m);u.EditorAssetLibrary.save_loaded_asset(m);return m
