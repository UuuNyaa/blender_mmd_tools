# -*- coding: utf-8 -*-

import itertools
from logging import root
import re
from abc import ABC, abstractmethod
from enum import Enum
from typing import Callable, Set

import bpy
from mmd_tools import register_wrap
from mmd_tools.core.model import FnModel, Model
from mmd_tools.properties.morph import _MorphBase
from mmd_tools.properties.rigid_body import MMDRigidBody
from mmd_tools.properties.root import MMDRoot
from mmd_tools.translations import DictionaryEnum


class MMDDataType(Enum):
    BONE = 'Bones'
    MORPH = 'Morphs'
    MATERIAL = 'Materials'
    DISPLAY = 'Display'
    PHYSICS = 'Physics'
    INFO = 'Information'


MMD_DATA_TYPE_ENUM_ITEMS = [
    (MMDDataType.BONE.name, MMDDataType.BONE.value, 'Bones', 1),
    (MMDDataType.MORPH.name, MMDDataType.MORPH.value, 'Morphs', 2),
    (MMDDataType.MATERIAL.name, MMDDataType.MATERIAL.value, 'Materials', 4),
    (MMDDataType.DISPLAY.name, MMDDataType.DISPLAY.value, 'Display frames', 8),
    (MMDDataType.PHYSICS.name, MMDDataType.PHYSICS.value, 'Rigidbodies and joints', 16),
    (MMDDataType.INFO.name, MMDDataType.INFO.value, 'Model name and comments', 32),
]


@register_wrap
class MMDDataReference(bpy.types.PropertyGroup):
    type: bpy.props.EnumProperty(items=MMD_DATA_TYPE_ENUM_ITEMS)
    object: bpy.props.PointerProperty(type=bpy.types.Object)
    data_path: bpy.props.StringProperty()


class MMDDataHandlerABC(ABC):
    @staticmethod
    @abstractmethod
    def draw_item(self, layout: bpy.types.UILayout, mmd_data_ref: MMDDataReference):
        pass

    @staticmethod
    @abstractmethod
    def update_index(mmd_data_ref: MMDDataReference):
        pass

    @staticmethod
    @abstractmethod
    def update_query(mmd_data_query: 'MMDDataQuery', check_data_visible: Callable[[bool, bool], bool], check_blank_name: Callable[[str, str], bool]):
        pass


class MMDBoneHandler(MMDDataHandlerABC):
    type_name = MMDDataType.BONE.name

    @staticmethod
    def draw_item(layout: bpy.types.UILayout, mmd_data_ref: MMDDataReference):
        pose_bone: bpy.types.PoseBone = mmd_data_ref.object.path_resolve(mmd_data_ref.data_path)
        row = layout.row(align=True)
        row.label(text='', icon='BONE_DATA')
        row.prop(pose_bone, 'name', text='')
        row.prop(pose_bone.mmd_bone, 'name_j', text='')
        row.prop(pose_bone.mmd_bone, 'name_e', text='')
        row.prop(pose_bone.bone, 'select', text='', emboss=False, icon_only=True, icon='RESTRICT_SELECT_OFF' if pose_bone.bone.select else 'RESTRICT_SELECT_ON')
        row.prop(pose_bone.bone, 'hide', text='', emboss=False, icon_only=True, icon='HIDE_ON' if pose_bone.bone.hide else 'HIDE_OFF')

    @staticmethod
    def update_index(mmd_data_ref: MMDDataReference):
        bpy.context.view_layer.objects.active = mmd_data_ref.object
        mmd_data_ref.id_data.data.bones.active = mmd_data_ref.object.path_resolve(mmd_data_ref.data_path).bone

    @staticmethod
    def update_query(mmd_data_query: 'MMDDataQuery', check_data_visible: Callable[[bool, bool], bool], check_blank_name: Callable[[str, str], bool]):
        id_data: bpy.types.Object = mmd_data_query.id_data
        pose_bone: bpy.types.PoseBone
        for index, pose_bone in enumerate(id_data.pose.bones):
            if check_data_visible(pose_bone.bone.select, pose_bone.bone.hide):
                continue

            if check_blank_name(pose_bone.mmd_bone.name_j, pose_bone.mmd_bone.name_e):
                continue

            mmd_data_ref: MMDDataReference = mmd_data_query.result_data.add()
            mmd_data_ref.type = MMDDataType.BONE.name
            mmd_data_ref.object = id_data
            mmd_data_ref.data_path = f'pose.bones[{index}]'


class MMDMorphHandler(MMDDataHandlerABC):
    type_name = MMDDataType.MORPH.name

    @staticmethod
    def draw_item(layout: bpy.types.UILayout, mmd_data_ref: MMDDataReference):
        morph: _MorphBase = mmd_data_ref.object.path_resolve(mmd_data_ref.data_path)
        row = layout.row(align=True)
        row.label(text='', icon='SHAPEKEY_DATA')
        row.prop(morph, 'name', text='')
        row.label(text=morph.name)
        row.prop(morph, 'name_e', text='')
        row.label(text='', icon='BLANK1')
        row.label(text='', icon='BLANK1')

    MORPH_DATA_PATH_EXTRACT = re.compile(r"mmd_root\.(?P<morphs_name>[^\[]*)\[(?P<index>\d*)\]")

    @staticmethod
    def update_index(mmd_data_ref: MMDDataReference):
        match = MMDMorphHandler.MORPH_DATA_PATH_EXTRACT.match(mmd_data_ref.data_path)
        if not match:
            return

        mmd_data_ref.object.mmd_root.active_morph_type = match['morphs_name']
        mmd_data_ref.object.mmd_root.active_morph = int(match['index'])

    @staticmethod
    def update_query(mmd_data_query: 'MMDDataQuery', _check_data_visible: Callable[[bool, bool], bool], check_blank_name: Callable[[str, str], bool]):
        root_object: bpy.types.Object = FnModel.find_root(mmd_data_query.id_data)
        mmd_root: MMDRoot = root_object.mmd_root

        for morphs_name, morphs in {
            'material_morphs': mmd_root.material_morphs,
            'uv_morphs': mmd_root.uv_morphs,
            'bone_morphs': mmd_root.bone_morphs,
            'vertex_morphs': mmd_root.vertex_morphs,
            'group_morphs': mmd_root.group_morphs,
        }.items():
            morph: _MorphBase
            for index, morph in enumerate(morphs):
                if check_blank_name(morph.name, morph.name_e):
                    continue
                mmd_data_ref: MMDDataReference = mmd_data_query.result_data.add()
                mmd_data_ref.type = MMDDataType.MORPH.name
                mmd_data_ref.object = root_object
                mmd_data_ref.data_path = f'mmd_root.{morphs_name}[{index}]'


class MMDMaterialHandler(MMDDataHandlerABC):
    type_name = MMDDataType.MATERIAL.name

    @staticmethod
    def draw_item(layout: bpy.types.UILayout, mmd_data_ref: MMDDataReference):
        mesh_object: bpy.types.Object = mmd_data_ref.object
        material: bpy.types.Material = mmd_data_ref.object.path_resolve(mmd_data_ref.data_path)
        row = layout.row(align=True)
        row.label(text='', icon='MATERIAL_DATA')
        row.prop(material, 'name', text='')
        row.prop(material.mmd_material, 'name_j', text='')
        row.prop(material.mmd_material, 'name_e', text='')
        row.prop(mesh_object, 'select', text='', emboss=False, icon_only=True, icon='RESTRICT_SELECT_OFF' if mesh_object.select else 'RESTRICT_SELECT_ON')
        row.prop(mesh_object, 'hide', text='', emboss=False, icon_only=True, icon='HIDE_ON' if mesh_object.hide else 'HIDE_OFF')

    MATERIAL_DATA_PATH_EXTRACT = re.compile(r"data\.materials\[(?P<index>\d*)\]")

    @staticmethod
    def update_index(mmd_data_ref: MMDDataReference):
        id_data: bpy.types.Object = mmd_data_ref.object
        bpy.context.view_layer.objects.active = id_data

        match = MMDMaterialHandler.MATERIAL_DATA_PATH_EXTRACT.match(mmd_data_ref.data_path)
        if not match:
            return

        id_data.active_material_index = int(match['index'])

    @staticmethod
    def update_query(mmd_data_query: 'MMDDataQuery', check_data_visible: Callable[[bool, bool], bool], check_blank_name: Callable[[str, str], bool]):
        checked_materials: Set[bpy.types.Material] = set()
        mesh_object: bpy.types.Object
        for mesh_object in FnModel.child_meshes(mmd_data_query.id_data):
            if check_data_visible(mesh_object.select, mesh_object.hide):
                continue

            material: bpy.types.Material
            for index, material in enumerate(mesh_object.data.materials):
                if material in checked_materials:
                    continue

                checked_materials.add(material)

                if not hasattr(material, 'mmd_material'):
                    continue

                if check_blank_name(material.mmd_material.name_j, material.mmd_material.name_e):
                    continue

                mmd_data_ref: MMDDataReference = mmd_data_query.result_data.add()
                mmd_data_ref.type = MMDDataType.MATERIAL.name
                mmd_data_ref.object = mesh_object
                mmd_data_ref.data_path = f'data.materials[{index}]'


class MMDDisplayHandler(MMDDataHandlerABC):
    type_name = MMDDataType.DISPLAY.name

    @staticmethod
    def draw_item(layout: bpy.types.UILayout, mmd_data_ref: MMDDataReference):
        bone_group: bpy.types.BoneGroup = mmd_data_ref.object.path_resolve(mmd_data_ref.data_path)
        row = layout.row(align=True)
        row.label(text='', icon='GROUP_BONE')
        row.prop(bone_group, 'name', text='')
        row.label(text=bone_group.name)
        row.label(text='')
        row.label(text='', icon='BLANK1')
        row.label(text='', icon='BLANK1')

    DISPLAY_DATA_PATH_EXTRACT = re.compile(r"pose\.bone_groups\[(?P<index>\d*)\]")

    @staticmethod
    def update_index(mmd_data_ref: MMDDataReference):
        id_data: bpy.types.Object = mmd_data_ref.object
        bpy.context.view_layer.objects.active = id_data

        match = MMDDisplayHandler.DISPLAY_DATA_PATH_EXTRACT.match(mmd_data_ref.data_path)
        if not match:
            return

        id_data.pose.bone_groups.active_index = int(match['index'])

    @staticmethod
    def update_query(mmd_data_query: 'MMDDataQuery', check_data_visible: Callable[[bool, bool], bool], check_blank_name: Callable[[str, str], bool]):
        id_data: bpy.types.Object = mmd_data_query.id_data
        bone_group: bpy.types.BoneGroup
        for index, bone_group in enumerate(id_data.pose.bone_groups):
            if check_blank_name(bone_group.name, ''):
                continue

            mmd_data_ref: MMDDataReference = mmd_data_query.result_data.add()
            mmd_data_ref.type = MMDDataType.DISPLAY.name
            mmd_data_ref.object = id_data
            mmd_data_ref.data_path = f'pose.bone_groups[{index}]'


class MMDPhysicsHandler(MMDDataHandlerABC):
    type_name = MMDDataType.PHYSICS.name

    @staticmethod
    def draw_item(layout: bpy.types.UILayout, mmd_data_ref: MMDDataReference):
        mesh_object: bpy.types.Object = mmd_data_ref.object

        if mesh_object.mmd_type == 'RIGID_BODY':
            row = layout.row(align=True)
            row.label(text='', icon='MESH_ICOSPHERE')
            row.prop(mesh_object, 'name', text='')
            row.prop(mesh_object.mmd_rigid, 'name_j', text='')
            row.prop(mesh_object.mmd_rigid, 'name_e', text='')
            row.prop(mesh_object, 'select', text='', emboss=False, icon_only=True, icon='RESTRICT_SELECT_OFF' if mesh_object.select else 'RESTRICT_SELECT_ON')
            row.prop(mesh_object, 'hide', text='', emboss=False, icon_only=True, icon='HIDE_ON' if mesh_object.hide else 'HIDE_OFF')

        elif mesh_object.mmd_type == 'JOINT':
            row = layout.row(align=True)
            row.label(text='', icon='CONSTRAINT')
            row.prop(mesh_object, 'name', text='')
            row.prop(mesh_object.mmd_joint, 'name_j', text='')
            row.prop(mesh_object.mmd_joint, 'name_e', text='')
            row.prop(mesh_object, 'select', text='', emboss=False, icon_only=True, icon='RESTRICT_SELECT_OFF' if mesh_object.select else 'RESTRICT_SELECT_ON')
            row.prop(mesh_object, 'hide', text='', emboss=False, icon_only=True, icon='HIDE_ON' if mesh_object.hide else 'HIDE_OFF')

    @staticmethod
    def update_index(mmd_data_ref: MMDDataReference):
        bpy.context.view_layer.objects.active = mmd_data_ref.object

    @staticmethod
    def update_query(mmd_data_query: 'MMDDataQuery', check_data_visible: Callable[[bool, bool], bool], check_blank_name: Callable[[str, str], bool]):
        root_object: bpy.types.Object = FnModel.find_root(mmd_data_query.id_data)
        model = Model(root_object)

        mesh_object: bpy.types.Object
        for mesh_object in model.rigidBodies():
            if check_data_visible(mesh_object.select_get(), mesh_object.hide_get()):
                continue

            mmd_rigid: MMDRigidBody = mesh_object.mmd_rigid
            if check_blank_name(mmd_rigid.name_j, mmd_rigid.name_e):
                continue

            mmd_data_ref: MMDDataReference = mmd_data_query.result_data.add()
            mmd_data_ref.type = MMDDataType.PHYSICS.name
            mmd_data_ref.object = mesh_object
            mmd_data_ref.data_path = 'mmd_rigid'

        mesh_object: bpy.types.Object
        for mesh_object in model.joints():
            if check_data_visible(mesh_object.select_get(), mesh_object.hide_get()):
                continue

            mmd_joint: MMDRigidBody = mesh_object.mmd_joint
            if check_blank_name(mmd_joint.name_j, mmd_joint.name_e):
                continue

            mmd_data_ref: MMDDataReference = mmd_data_query.result_data.add()
            mmd_data_ref.type = MMDDataType.PHYSICS.name
            mmd_data_ref.object = mesh_object
            mmd_data_ref.data_path = 'mmd_joint'


class MMDInfoHandler(MMDDataHandlerABC):
    type_name = MMDDataType.INFO.name

    TYPE_TO_ICONS = {
        'EMPTY': 'EMPTY_DATA',
        'ARMATURE': 'ARMATURE_DATA',
        'MESH': 'MESH_DATA',
    }

    @staticmethod
    def draw_item(layout: bpy.types.UILayout, mmd_data_ref: MMDDataReference):
        info_object: bpy.types.Object = mmd_data_ref.object
        row = layout.row(align=True)
        row.label(text='', icon=MMDInfoHandler.TYPE_TO_ICONS.get(info_object.type, 'OBJECT_DATA'))
        row.prop(info_object, 'name', text='')
        row.label(text=info_object.name)
        row.label(text='')
        row.prop(info_object, 'select', text='', emboss=False, icon_only=True, icon='RESTRICT_SELECT_OFF' if info_object.select else 'RESTRICT_SELECT_ON')
        row.prop(info_object, 'hide', text='', emboss=False, icon_only=True, icon='HIDE_ON' if info_object.hide else 'HIDE_OFF')

    @staticmethod
    def update_index(mmd_data_ref: MMDDataReference):
        bpy.context.view_layer.objects.active = mmd_data_ref.object

    @staticmethod
    def update_query(mmd_data_query: 'MMDDataQuery', check_data_visible: Callable[[bool, bool], bool], check_blank_name: Callable[[str, str], bool]):
        root_object: bpy.types.Object = FnModel.find_root(mmd_data_query.id_data)
        armature_object: bpy.types.Object = FnModel.find_armature(root_object)

        info_object: bpy.types.Object
        for info_object in itertools.chain([root_object], [armature_object], FnModel.child_meshes(armature_object)):
            if check_data_visible(info_object.select, info_object.hide):
                continue

            if check_blank_name(info_object.name, ''):
                continue

            mmd_data_ref: MMDDataReference = mmd_data_query.result_data.add()
            mmd_data_ref.type = MMDInfoHandler.type_name
            mmd_data_ref.object = info_object
            mmd_data_ref.data_path = ''


MMD_DATA_HANDLERS = {
    MMDBoneHandler,
    MMDMorphHandler,
    MMDMaterialHandler,
    MMDDisplayHandler,
    MMDPhysicsHandler,
    MMDInfoHandler,
}


@register_wrap
class MMD_TOOLS_UL_PoseBones(bpy.types.UIList):
    handlers = {h.type_name: h.draw_item for h in MMD_DATA_HANDLERS}

    def draw_item(self, context, layout: bpy.types.UILayout, data, mmd_data_ref: MMDDataReference, icon, active_data, active_propname, index):
        self.handlers[mmd_data_ref.type](layout, mmd_data_ref)


@register_wrap
class MMDDataQuery(bpy.types.PropertyGroup):
    update_index_handlers = {h.type_name: h.update_index for h in MMD_DATA_HANDLERS}

    @staticmethod
    def _update_index(mmd_data_query: 'MMDDataQuery', _context):
        """Display the selected data in the Property Editor"""
        if mmd_data_query.result_data_index < 0:
            return

        mmd_data_ref: MMDDataReference = mmd_data_query.result_data[mmd_data_query.result_data_index]

        MMDDataQuery.update_index_handlers[mmd_data_ref.type](mmd_data_ref)

    @staticmethod
    def _update_query(mmd_data_query: 'MMDDataQuery', _context):
        """Update the data by the query"""

        id_data: bpy.types.Object = mmd_data_query.id_data
        mmd_data_query.result_data.clear()
        mmd_data_query.result_data_index = -1

        filter_japanese_blank: bool = mmd_data_query.filter_japanese_blank
        filter_english_blank: bool = mmd_data_query.filter_english_blank

        filter_selected: bool = mmd_data_query.filter_selected
        filter_visible: bool = mmd_data_query.filter_visible

        def check_data_visible(select: bool, hide: bool) -> bool:
            return (
                filter_selected and not select
                or
                filter_visible and hide
            )

        def check_blank_name(name_j: str, name_e: str) -> bool:
            return (
                filter_japanese_blank and name_j
                or
                filter_english_blank and name_e
            )

        for handler in MMD_DATA_HANDLERS:
            if handler.type_name in mmd_data_query.filter_types:
                handler.update_query(mmd_data_query, check_data_visible, check_blank_name)

    @staticmethod
    def _update_operation_script_preset(mmd_data_query: 'MMDDataQuery', _context):
        if mmd_data_query.operation_script_preset == 'NOTHING':
            return

        if mmd_data_query.operation_script_preset == 'TO_MMD_LR':
            mmd_data_query.operation_script = 'to_mmd_lr(name)'
            return

        if mmd_data_query.operation_script_preset == 'TO_BLENDER_LR':
            mmd_data_query.operation_script = 'to_blender_lr(name)'
            return

    filter_japanese_blank: bpy.props.BoolProperty(name='Japanese Blank', default=False, update=_update_query.__func__)
    filter_english_blank: bpy.props.BoolProperty(name='English Blank', default=False, update=_update_query.__func__)
    filter_selected: bpy.props.BoolProperty(name='Selected', default=False, update=_update_query.__func__)
    filter_visible: bpy.props.BoolProperty(name='Visible', default=False, update=_update_query.__func__)
    filter_types: bpy.props.EnumProperty(
        items=MMD_DATA_TYPE_ENUM_ITEMS,
        default={'BONE', 'MORPH', 'MATERIAL', 'DISPLAY', 'PHYSICS', },
        options={'ENUM_FLAG'},
        update=_update_query.__func__,
    )
    result_data_index: bpy.props.IntProperty(update=_update_index.__func__)
    result_data: bpy.props.CollectionProperty(type=MMDDataReference)

    dictionary = bpy.props.EnumProperty(
        items=DictionaryEnum.get_dictionary_items,
        name='Dictionary',
    )

    operation_target: bpy.props.EnumProperty(
        items=[
            ('BLENDER', 'Blender Name (name)', '', 1),
            ('JAPANESE', 'Japanese Name (name_j)', '', 2),
            ('ENGLISH', 'English Name (name_e)', '', 3),
        ],
        name='Operation Target',
        default='JAPANESE',
    )

    operation_script_preset: bpy.props.EnumProperty(
        items=[
            ('NOTHING', '', '', 1),
            ('TO_MMD_LR', 'Blender L/R to MMD L/R', 'to_mmd_lr(name)', 2),
            ('TO_BLENDER_LR', 'MMD L/R to Blender L/R', 'to_blender_lr(name_j)', 3),
        ],
        name='Operation Script Preset',
        default='NOTHING',
        update=_update_operation_script_preset.__func__,
    )

    operation_script: bpy.props.StringProperty()
