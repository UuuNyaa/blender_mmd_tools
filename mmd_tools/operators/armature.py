# -*- coding: utf-8 -*-

from typing import Set

import bpy
from mmd_tools import register_wrap
from mmd_tools.core.model import FnModel
from mmd_tools.properties.armature import MMDDataQuery


DEFAULT_SHOW_ROW_COUNT = 20

@register_wrap
class ShowGlobalTranslationPopup(bpy.types.Operator):
    bl_idname = 'mmd_tools.show_global_translation_popup'
    bl_label = 'Show Global Translation Popup'
    bl_options = {'REGISTER'}

    def draw(self, context):
        layout = self.layout
        mmd_data_query = self._mmd_data_query

        col = layout.column(align=True)
        col.label(text='Filter', icon='FILTER')
        row = col.row()
        row.prop(mmd_data_query, 'filter_types')

        group = row.row(align=True, heading='is Blank:')
        group.alignment = 'RIGHT'
        group.prop(mmd_data_query, 'filter_japanese_blank', toggle=True, text='Japanese')
        group.prop(mmd_data_query, 'filter_english_blank', toggle=True, text='English')

        group = row.row(align=True)
        group.prop(mmd_data_query, 'filter_selected', toggle=True, icon='RESTRICT_SELECT_OFF', icon_only=True)
        group.prop(mmd_data_query, 'filter_visible', toggle=True, icon='HIDE_OFF', icon_only=True)

        col = layout.column(align=True)
        row = col.box().row(align=True)
        row.label(text='', icon='BLENDER')
        row.prop(mmd_data_query, 'operation_target', expand=True)
        row.label(text='', icon='RESTRICT_SELECT_OFF')
        row.label(text='', icon='HIDE_ON')

        if len(mmd_data_query.result_data) > DEFAULT_SHOW_ROW_COUNT:
            row.label(text='', icon='BLANK1')

        col.template_list(
            "MMD_TOOLS_UL_PoseBones", "",
            mmd_data_query, 'result_data',
            mmd_data_query, 'result_data_index',
            rows=DEFAULT_SHOW_ROW_COUNT,
        )

        box = layout.box()
        box.label(text='Batch Operation', icon='MODIFIER')
        box.prop(mmd_data_query, 'operation_script', text='', icon='SCRIPT')
        row = box.row()
        row.prop(mmd_data_query, 'dictionary', text='Dictionary', icon='HELP')
        row.prop(mmd_data_query, 'operation_script_preset', text='Preset', icon='CON_TRANSFORM_CACHE')
        row.operator(ExecuteTranslationScriptOperator.bl_idname, text='Execute')

    def invoke(self, context: bpy.types.Context, _event):
        active_obj = context.active_object

        root = FnModel.find_root(active_obj)
        if root is None:
            return {'CANCELLED'}

        armature_object = FnModel.find_armature(root)
        if armature_object is None:
            return {'CANCELLED'}

        mmd_data_query: MMDDataQuery = armature_object.mmd_data_query
        self._mmd_data_query = mmd_data_query
        MMDDataQuery._update_query(mmd_data_query, None)

        return context.window_manager.invoke_props_dialog(self, width=800)

    def execute(self, _context):
        return {'FINISHED'}


@register_wrap
class ExecuteTranslationScriptOperator(bpy.types.Operator):
    bl_idname = 'mmd_tools.execute_translation_script'
    bl_label = 'Execute Translation Script'
    bl_options = {'INTERNAL'}

    def execute(self, context: bpy.types.Context):
        root = FnModel.find_root(context.active_object)
        if root is None:
            return {'CANCELLED'}

        armature_object = FnModel.find_armature(root)
        if armature_object is None:
            return {'CANCELLED'}

        FnModel.translate_in_presettings(armature_object)

        return {'FINISHED'}
