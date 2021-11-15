# -*- coding: utf-8 -*-

bl_info = {
    "name": "mmd_tools",
    "author": "sugiany",
    "version": (1, 0, 2),
    "blender": (2, 80, 0),
    "location": "View3D > Tool Shelf > MMD Tools Panel",
    "description": "Utility tools for MMD model editing. (UuuNyaa's forked version)",
    "warning": "",
    "doc_url": "https://mmd-blender.fandom.com/wiki/MMD_Tools",
    "wiki_url": "https://mmd-blender.fandom.com/wiki/MMD_Tools",
    "tracker_url": "https://github.com/UuuNyaa/blender_mmd_tools/issues",
    "category": "Object",
}

__bl_classes = []
def register_wrap(cls):
    #print('%3d'%len(__bl_classes), cls)
    #assert(cls not in __bl_classes)
    if __make_annotations:
        bl_props = {k:v for k, v in cls.__dict__.items() if isinstance(v, __bpy_property)}
        if bl_props:
            if '__annotations__' not in cls.__dict__:
                setattr(cls, '__annotations__', {})
            annotations = cls.__dict__['__annotations__']
            for k, v in bl_props.items():
                #print('   -', k, v)
                #assert(v.__class__.__name__ == '_PropertyDeferred' or getattr(v[0], '__module__', None) == 'bpy.props' and isinstance(v[1], dict))
                annotations[k] = v
                delattr(cls, k)
    if hasattr(cls, 'bl_rna'):
        __bl_classes.append(cls)
    return cls

if "bpy" in locals():
    if bpy.app.version < (2, 71, 0):
        import imp as importlib
    else:
        import importlib
    importlib.reload(properties)
    importlib.reload(operators)
    importlib.reload(panels)
else:
    import bpy
    import logging
    from bpy.app.handlers import persistent

    __make_annotations = (bpy.app.version >= (2, 80, 0))
    __bpy_property = (bpy.props._PropertyDeferred if hasattr(bpy.props, '_PropertyDeferred') else tuple)
    from . import properties
    from . import operators
    from . import panels

if bpy.app.version < (2, 80, 0):
    bl_info['blender'] = (2, 70, 0)

logging.basicConfig(format='%(message)s', level=logging.DEBUG)

def get_update_candidate_branches(_, __):
    updater = operators.addon_updater.AddonUpdaterManager.get_instance()
    if not updater.candidate_checked():
        return []

    return [(name, name, "") for name in updater.get_candidate_branch_names()]

@register_wrap
class MMDToolsAddonPreferences(bpy.types.AddonPreferences):
    # this must match the addon name, use '__package__'
    # when defining this in a submodule of a python package.
    bl_idname = __name__

    shared_toon_folder = bpy.props.StringProperty(
            name="Shared Toon Texture Folder",
            description=('Directory path to toon textures. This is normally the ' +
                         '"Data" directory within of your MikuMikuDance directory'),
            subtype='DIR_PATH',
            )
    base_texture_folder = bpy.props.StringProperty(
            name='Base Texture Folder',
            description='Path for textures shared between models',
            subtype='DIR_PATH',
            )
    dictionary_folder = bpy.props.StringProperty(
            name='Dictionary Folder',
            description='Path for searching csv dictionaries',
            subtype='DIR_PATH',
            default=__file__[:-11],
            )
    non_collision_threshold = bpy.props.FloatProperty(
            name='Non-Collision Threshold',
            description='The distance threshold for creating extra non-collision constraints while building physics',
            min=0,
            soft_max=10,
            default=1.5,
            )

    # for add-on updater
    updater_branch_to_update = bpy.props.EnumProperty(
        name='Branch',
        description='Target branch to update add-on',
        items=get_update_candidate_branches
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "shared_toon_folder")
        layout.prop(self, "base_texture_folder")
        layout.prop(self, "dictionary_folder")
        layout.prop(self, "non_collision_threshold")


        # add-on updater
        update_col = layout.box().column(align=False)
        update_col.label(text='Add-on update', icon='RECOVER_LAST')
        updater = operators.addon_updater.AddonUpdaterManager.get_instance()


        if updater.updated():
            col = update_col.column()
            col.scale_y = 2
            col.alert = True
            col.operator(
                "wm.quit_blender",
                text="Restart Blender to complete update",
                icon="ERROR"
            )
            return

        if not updater.candidate_checked():
            col = update_col.column()
            col.scale_y = 2
            col.operator(
                operators.addon_updater.CheckAddonUpdate.bl_idname,
                text="Check mmd_tools add-on update",
                icon='FILE_REFRESH'
            )
        else:
            row = update_col.row(align=True)
            row.scale_y = 2
            col = row.column()
            col.operator(
                operators.addon_updater.CheckAddonUpdate.bl_idname,
                text="Check mmd_tools add-on update",
                icon='FILE_REFRESH'
            )
            col = row.column()
            if updater.update_ready():
                col.enabled = True
                col.operator(
                    operators.addon_updater.UpdateAddon.bl_idname,
                    text=bpy.app.translations.pgettext_iface("Update to the latest release version ({})").format(updater.latest_version()),
                    icon='TRIA_DOWN_BAR'
                ).branch_name = updater.latest_version()
            else:
                col.enabled = False
                col.operator(
                    operators.addon_updater.UpdateAddon.bl_idname,
                    text="No updates are available"
                )

            update_col.separator()
            update_col.label(text="(Danger) Manual Update:")
            row = update_col.row(align=True)
            row.prop(self, "updater_branch_to_update", text="Target")
            row.operator(
                operators.addon_updater.UpdateAddon.bl_idname, text="Update",
                icon='TRIA_DOWN_BAR'
            ).branch_name = self.updater_branch_to_update

            update_col.separator()
            if updater.has_error():
                box = update_col.box()
                box.label(text=updater.error(), icon='CANCEL')
            elif updater.has_info():
                box = update_col.box()
                box.label(text=updater.info(), icon='ERROR')


def menu_func_import(self, context):
    self.layout.operator(operators.fileio.ImportPmx.bl_idname, text='MikuMikuDance Model (.pmd, .pmx)', icon='OUTLINER_OB_ARMATURE')
    self.layout.operator(operators.fileio.ImportVmd.bl_idname, text='MikuMikuDance Motion (.vmd)', icon='ANIM')
    self.layout.operator(operators.fileio.ImportVpd.bl_idname, text='Vocaloid Pose Data (.vpd)', icon='POSE_HLT')

def menu_func_export(self, context):
    self.layout.operator(operators.fileio.ExportPmx.bl_idname, text='MikuMikuDance Model (.pmx)', icon='OUTLINER_OB_ARMATURE')
    self.layout.operator(operators.fileio.ExportVmd.bl_idname, text='MikuMikuDance Motion (.vmd)', icon='ANIM')
    self.layout.operator(operators.fileio.ExportVpd.bl_idname, text='Vocaloid Pose Data (.vpd)', icon='POSE_HLT')

def menu_func_armature(self, context):
    self.layout.operator(operators.model.CreateMMDModelRoot.bl_idname, text='Create MMD Model', icon='OUTLINER_OB_ARMATURE')

def menu_view3d_object(self, context):
    self.layout.separator()
    self.layout.operator('mmd_tools.clean_shape_keys')

def header_view3d_pose_draw(self, context):
    obj = context.active_object
    if obj and obj.type == 'ARMATURE' and obj.mode == 'POSE':
        self.layout.operator('mmd_tools.flip_pose', text='', icon='ARROW_LEFTRIGHT')

@persistent
def load_handler(dummy):
    from mmd_tools.core.sdef import FnSDEF
    FnSDEF.clear_cache()
    FnSDEF.register_driver_function()


def register():
    for cls in __bl_classes:
        bpy.utils.register_class(cls)
    print(__name__, 'registed %d classes'%len(__bl_classes))
    properties.register()
    bpy.app.handlers.load_post.append(load_handler)
    bpy.types.VIEW3D_HT_header.append(header_view3d_pose_draw)
    bpy.types.VIEW3D_MT_object.append(menu_view3d_object)
    if bpy.app.version < (2, 80, 0):
        bpy.types.INFO_MT_file_import.append(menu_func_import)
        bpy.types.INFO_MT_file_export.append(menu_func_export)
        bpy.types.INFO_MT_armature_add.append(menu_func_armature)
        #bpy.context.user_preferences.system.use_scripts_auto_execute = True
    else:
        bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
        bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
        bpy.types.VIEW3D_MT_armature_add.append(menu_func_armature)
        #bpy.context.preferences.filepaths.use_scripts_auto_execute = True

    from mmd_tools.m17n import translation_dict
    bpy.app.translations.register(bl_info['name'], translation_dict)

    operators.addon_updater.register_updater(bl_info, __file__)

def unregister():
    operators.addon_updater.unregister_updater()

    bpy.app.translations.unregister(bl_info['name'])

    if bpy.app.version < (2, 80, 0):
        bpy.types.INFO_MT_file_import.remove(menu_func_import)
        bpy.types.INFO_MT_file_export.remove(menu_func_export)
        bpy.types.INFO_MT_armature_add.remove(menu_func_armature)
    else:
        bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
        bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
        bpy.types.VIEW3D_MT_armature_add.remove(menu_func_armature)
    bpy.types.VIEW3D_MT_object.remove(menu_view3d_object)
    bpy.types.VIEW3D_HT_header.remove(header_view3d_pose_draw)
    bpy.app.handlers.load_post.remove(load_handler)
    properties.unregister()
    for cls in reversed(__bl_classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
