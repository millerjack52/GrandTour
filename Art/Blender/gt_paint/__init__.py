"""GT Paint: the GrandTour painted look for the owner's models (docs/LOOK_PLAN.md L1, VEHICLE_BUILD_SYSTEM 55).

Apply Style -> (hand paint the colour attribute if you want) -> Bake -> Export, from the "GT Paint" tab of the 3D
view's N sidebar. The preset (Art/Blender/gt_paint_preset.json) holds every number; the addon never sources a texture.
Bake's third output, T_GT_<Asset>_N (painted-dab normals), comes from the owner's OW Painterly Normal Baker extension,
which Bake calls (and imports from its folder when this Blender has not enabled it); Show Bake swaps the viewport to
the bake copy, which carries the UV the _N was baked on.
Unwrap for Paint (follow-up 4) gives each selected object with no UV map one (GT_UV) by the smart projection Bake uses;
Bake does the same to a single source with no UV, so the bake lands on a UV the object, its export and the game carry.
Install: zip the gt_paint folder, Edit > Preferences > Add-ons > Install from Disk, or copy the folder into
%APPDATA%\\Blender Foundation\\Blender\\5.1\\scripts\\addons.
"""
import os

import bpy
from bpy.props import BoolProperty, EnumProperty, PointerProperty, StringProperty

from . import core

bl_info = {
    "name": "GT Paint",
    "author": "GrandTour",
    "version": (0, 3, 0),
    "blender": (5, 1, 0),
    "location": "View3D > Sidebar (N) > GT Paint",
    "description": "Paints a model in the GrandTour preset, bakes an albedo, a wear/grime/roughness mask and "
                   "painted-dab normals (the owner's OW Painterly Normal Baker), exports an FBX for Unreal",
    "category": "Material",
}


class GTPaintSettings(bpy.types.PropertyGroup):
    preset_path: StringProperty(name="Preset", subtype='FILE_PATH', default="",
                                description="The preset JSON; empty = Art/Blender/gt_paint_preset.json")
    asset_name: StringProperty(name="Asset", default="",
                               description="T_GT_<Asset>_D/_M and SM_<Asset>; empty = the active object's name")
    bake_size: EnumProperty(name="Size", default='PRESET',
                            items=[('PRESET', "Preset", "The preset's bake_size"), ('1024', "1K", "1024 x 1024"),
                                   ('2048', "2K", "2048 x 2048")])
    export_dir: StringProperty(name="Export", subtype='DIR_PATH', default="",
                               description="Where <Asset>/ goes; empty = Art/Export")
    unwrap_replace: BoolProperty(name="Replace UV", default=False,
                                 description="Unwrap for Paint re-projects objects that already have a UV map too (their "
                                             "render-active map, name kept); off = they are left alone")


def settings(context):
    return context.scene.gt_paint


def asset_of(context):
    s = settings(context)
    ob = context.active_object
    if s.asset_name.strip():
        return core.clean_name(s.asset_name)
    name = ob.name if ob else "Asset"
    if name.endswith(core.BAKE_SUFFIX):     # the bake copy stands for its asset
        return name[:-len(core.BAKE_SUFFIX)]
    return core.clean_name(name)


def export_dir_of(context):
    s = settings(context)
    return bpy.path.abspath(s.export_dir) if s.export_dir.strip() else core.default_export_dir()


def sources(context):
    obs = core.mesh_objects(context.selected_objects)
    active = context.active_object
    if active is not None and active in obs:
        obs.remove(active)
        obs.insert(0, active)
    return obs


class GTPAINT_OT_apply_style(bpy.types.Operator):
    bl_idname = "gt_paint.apply_style"
    bl_label = "Apply Style"
    bl_description = "Create or refresh the GT_Paint node group and a GT material per selected object from the preset"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return bool(core.mesh_objects(context.selected_objects))

    def execute(self, context):
        try:
            preset, where = core.load_preset(settings(context).preset_path)
            normal = core.normal_preview_of(asset_of(context), export_dir_of(context), preset)
            done = core.apply_style(sources(context), preset, normal)
        except core.GTPaintError as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}
        self.report({'INFO'}, "GT Paint: %d material(s) from %s%s" % (
            len(done), os.path.basename(where),
            ", %s loaded on UV %s" % (os.path.basename(normal[0]), normal[1]) if normal else ", no _N loaded"))
        return {'FINISHED'}


class GTPAINT_OT_unwrap(bpy.types.Operator):
    bl_idname = "gt_paint.unwrap"
    bl_label = "Unwrap for Paint"
    bl_description = ("Give every selected mesh object with no UV map one (GT_UV) by the smart projection Bake uses, over "
                      "its own mesh with its modifiers not applied; objects with a UV map are left alone unless Replace "
                      "UV is ticked")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and bool(core.mesh_objects(context.selected_objects))

    def execute(self, context):
        s = settings(context)
        done, left = [], []
        try:
            preset, _ = core.load_preset(s.preset_path)
            for ob in core.mesh_objects(context.selected_objects):
                (done if core.unwrap_object(context, ob, preset, s.unwrap_replace) else left).append(ob.name)
        except core.GTPaintError as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}
        self.report({'INFO'}, "GT Paint: unwrapped %d object(s)%s%s" % (
            len(done), (": " + ", ".join(done)) if done else "",
            ("; left alone (a UV map already, or no faces): " + ", ".join(left)) if left else ""))
        return {'FINISHED'}


class GTPAINT_OT_bake(bpy.types.Operator):
    bl_idname = "gt_paint.bake"
    bl_label = "Bake"
    bl_description = ("Bake the selected objects as one asset: unlit albedo T_GT_<Asset>_D, mask T_GT_<Asset>_M "
                      "(R wear, G grime, B roughness) and painted-dab normal T_GT_<Asset>_N (DirectX, from the OW "
                      "Painterly Normal Baker), PNG, into <Export>/<Asset>/")
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and bool(core.mesh_objects(context.selected_objects))

    def execute(self, context):
        s = settings(context)
        try:
            preset, _ = core.load_preset(s.preset_path)
            size = None if s.bake_size == 'PRESET' else int(s.bake_size)
            info = core.bake(context, sources(context), asset_of(context), export_dir_of(context), size, preset)
        except core.GTPaintError as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}
        self.report({'INFO'}, "GT Paint: baked %s at %d px in %.1f s%s -> %s"
                    % (info["asset"], info["size"], info["seconds_total"],
                       " (+ _N, %.1f s, dabs %s)" % (info["normal"]["seconds"], "/".join(str(n) for n in info["normal"]["dabs"]))
                       if info.get("normal") else " (no _N: normal_enable false)",
                       os.path.dirname(info["files"]["D"])))
        return {'FINISHED'}


class GTPAINT_OT_show_bake(bpy.types.Operator):
    bl_idname = "gt_paint.show_bake"
    bl_label = "Show Bake"
    bl_description = ("Swap the viewport between the sources and the bake copy <Asset>_GTBake, which carries the UV the "
                      "_N was baked on (so the dabs show on it). Viewport hiding only")
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        try:
            shown = core.toggle_bake_view(context, asset_of(context))
        except core.GTPaintError as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}
        self.report({'INFO'}, "GT Paint: showing the %s" % ("bake copy" if shown == "bake" else "sources"))
        return {'FINISHED'}


class GTPAINT_OT_export(bpy.types.Operator):
    bl_idname = "gt_paint.export"
    bl_label = "Export"
    bl_description = "Write the last bake's mesh as <Export>/<Asset>/SM_<Asset>.fbx, pivot at the active object's origin"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        s = settings(context)
        try:
            preset, _ = core.load_preset(s.preset_path)
            info = core.export_fbx(context, asset_of(context), export_dir_of(context), context.active_object, preset)
        except core.GTPaintError as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}
        self.report({'INFO'}, "GT Paint: %s (%d KB)" % (info["file"], info["bytes"] // 1024))
        return {'FINISHED'}


class GTPAINT_PT_panel(bpy.types.Panel):
    bl_label = "GT Paint"
    bl_idname = "GTPAINT_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "GT Paint"

    def draw(self, context):
        s = settings(context)
        layout = self.layout
        col = layout.column(align=True)
        col.prop(s, "preset_path")
        col.prop(s, "asset_name")
        col.prop(s, "bake_size")
        col.prop(s, "export_dir")
        try:
            preset, where = core.load_preset(s.preset_path)
            box = layout.box()
            box.label(text="Preset: %s" % os.path.basename(where))
            box.label(text="tones %s, strokes %.0f %% over %.2f m, wear %.0f cm x %.2f, scuffs %.0f %% over %.2f m, grime %.2f"
                      % (preset["tones"], float(preset["grain_strength"]) * 100.0, float(preset["grain_scale_m"]),
                         float(preset["wear_width_m"]) * 100.0, float(preset["wear_lighten"]),
                         float(preset["scuff_cover"]) * 100.0, float(preset["scuff_scale_m"]),
                         float(preset["grime_strength"])))
            box.label(text=core.normal_status(core.mesh_objects(context.selected_objects), asset_of(context),
                                              export_dir_of(context), preset))
            if preset.get("normal_enable", True):
                path = core.normal_baker_dir(preset)
                box.label(text="Baker: " + ("enabled in this Blender" if core.normal_baker_registered() else
                                            "found, Bake imports it" if os.path.isfile(os.path.join(path, "__init__.py"))
                                            else "MISSING at %s" % path))
        except Exception as error:   # a broken JSON must not break the panel
            layout.label(text="Preset unreadable: %s" % error)
        layout.label(text="Asset: %s -> %s" % (asset_of(context), os.path.basename(os.path.normpath(export_dir_of(context)))))
        layout.label(text=core.uv_plan(sources(context)))
        col = layout.column(align=True)
        col.operator("gt_paint.apply_style")
        row = col.row(align=True)
        row.operator("gt_paint.unwrap")
        row.prop(s, "unwrap_replace", text="Replace")
        col.operator("gt_paint.bake")
        col.operator("gt_paint.export")
        col.operator("gt_paint.show_bake")


CLASSES = (GTPaintSettings, GTPAINT_OT_apply_style, GTPAINT_OT_unwrap, GTPAINT_OT_bake, GTPAINT_OT_export,
           GTPAINT_OT_show_bake, GTPAINT_PT_panel)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.gt_paint = PointerProperty(type=GTPaintSettings)


def unregister():
    del bpy.types.Scene.gt_paint
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
