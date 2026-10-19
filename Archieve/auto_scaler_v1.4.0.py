# Auto_Scaler v1.4.0
#
# Blender 5.0.1 兼容插件
#
# 本插件包含两个手动操作按钮，UI 文本根据 Blender 界面语言自动适配
# （支持简体中文 / English，其他语言回退到 English）
#
# 【按钮 A：解除父级并删除 Empty】
#   - 对用户选中的所有物体执行 Alt+P → Clear and Keep Transformation
#     （不管父级是什么类型，完全打散选中集合内的父子层级）
#   - 删除选中集合中的所有 Empty 物体
#   - 保留 Mesh / Armature / Curve 等其他几何体（仅删 Empty）
#
# 【按钮 B：创建 Cube 形态空物体并父级化】
#   1. 用户从外部导入模型（导入后 Blender 默认会自动选中这些物体）
#   2. 用户点击按钮执行
#   3. 插件收集当前选中的所有可处理物体
#      （Mesh / Armature / Curve / Surface / Meta / Lattice / Font / Empty），
#      其中几何体参与底部中心计算
#      —— Mesh 用顶点（最精确），其余几何类型用 bound_box
#   4. 在底部中心点创建一个空物体（Empty 对象，type='EMPTY'），
#      显示形态设为 Cube 线框（empty_display_type='CUBE'）——
#      注意是空物体的 Cube 显示形态，不是真正的 Mesh Cube
#   5. 识别选中集合中的"根物体"（父级为 None 或不在选中集合中），
#      只将根物体通过 Ctrl+P（Keep Transform）方式父级化到新 Cube 下
#      —— 这样保留导入文件原有的父子层级（包括导入文件自带的父级空物体），
#         仅把最顶层挂到新 Cube 下，原父级空物体之下的网格体随之联动
#   6. 将新 Cube 空物体的 location（三轴）和 scale（三轴）都乘以 0.0254
#      —— 子物体会跟随父级联动，等效于把英寸单位的模型整体转换为米制
#
# 安装：Edit > Preferences > Add-ons > Install from Disk > 选择本文件 > 勾选启用
# 位置：3D Viewport 侧栏（按 N）> Tool 标签 > "Auto Scaler" 面板

bl_info = {
    "name": "Auto_Scaler",
    "author": "WorkBuddy",
    "version": (1, 4, 0),
    "blender": (5, 0, 1),
    "location": "View3D > Sidebar (N) > Tool > Auto Scaler",
    "description": "Two buttons with auto i18n (zh_CN/en_US): (A) Clear parents & delete Empties; (B) Create Cube-empty at bottom-center, parent roots with Keep Transform, multiply location/scale by 0.0254 (inches to meters).",
    "category": "Object",
}

import bpy
from bpy.types import Operator, Panel
from bpy.props import FloatProperty, StringProperty, EnumProperty
from mathutils import Vector


# ===========================================================================
# i18n：多语言适配（根据 Blender 界面语言自动选择）
# ===========================================================================
# Blender 语言设置在 preferences.view.language，常见值：
#   'en_US'  - English
#   'zh_CN'  - 简体中文 (Simplified Chinese)
#   'zh_TW'  - 繁体中文 (Traditional Chinese) —— 回退到 zh_CN
#   'ja_JP'  - 日本語 —— 回退到 en_US
#   其他语言 —— 回退到 en_US

TRANSLATIONS = {
    'en_US': {
        # Panel
        'panel_title':         "Auto Scaler",
        'panel_usage':         "Usage:",
        'panel_step_a':        "• Button A: Clear parents & delete Empties",
        'panel_step_b':        "• Button B: Create empty & parent after import",
        'panel_factor_hint':   "  Default factor 0.0254 = inches to meters",
        'panel_supports':      "Supports Mesh/Armature/Curve/Empty etc.",
        'panel_preserves':     "Auto-detects roots, preserves hierarchy",
        'panel_selected':      "Selected processable objects: {}",
        'panel_select_first':  "(Select at least one Mesh/Armature/Curve/Empty first)",

        # Button A
        'btn_a_text':          "Clear Parents & Delete Empties",
        'btn_a_done':          "Cleared {} parent relationships | Deleted {} Empties | Remaining {} objects ({})",
        'btn_a_no_selection':  "Please select at least one object first",

        # Button B
        'btn_b_text':          "Create Cube Empty & Parent",
        'btn_b_no_targets':    "Please select at least one processable object (Mesh/Armature/Curve/Empty etc.)",
        'btn_b_no_geom':       "Cannot get geometry data (all selected may be Empty or empty)",
        'btn_b_done':          "Created Cube-empty '{}' | Parented {} root(s) (of {} selected, {}{}) | Original bbox: {:.4f} x {:.4f} x {:.4f} | Factor: {}",
        'btn_b_kept_hierarchy': ", kept {} child hierarchy",

        # Properties
        'prop_factor':         "Factor",
        'prop_factor_desc':    "Multiplier for empty's location and scale (default 0.0254 = inches to meters)",
        'prop_empty_name':     "Empty Name",
        'prop_display_type':   "Empty Display Type",
        'prop_display_type_desc': "Display type of the empty in viewport",
        'prop_display_size':   "Empty Display Size",

        # Enum items
        'type_cube':           "Cube",
        'type_cube_desc':      "Cube wireframe (default)",
        'type_arrows':         "Arrows",
        'type_arrows_desc':    "Default arrows, good direction sense",
        'type_plain_axes':     "Plain Axes",
        'type_plain_axes_desc': "Three axis lines",
        'type_single_arrow':   "Single Arrow",
        'type_single_arrow_desc': "Single direction arrow",
        'type_circle':         "Circle",
        'type_circle_desc':    "Circle",
        'type_sphere':         "Sphere",
        'type_sphere_desc':    "Sphere wireframe",
    },
    'zh_CN': {
        # Panel
        'panel_title':         "Auto Scaler",
        'panel_usage':         "使用步骤：",
        'panel_step_a':        "• 按钮 A：解除选中物体父级 + 删 Empty",
        'panel_step_b':        "• 按钮 B：导入模型后创建空物体并父级化",
        'panel_factor_hint':   "  默认系数 0.0254 = 英寸→米",
        'panel_supports':      "支持 Mesh/Armature/Curve/Empty 等",
        'panel_preserves':     "自动识别根物体，保留导入层级",
        'panel_selected':      "当前选中可处理物体数：{}",
        'panel_select_first':  "（请先选中至少一个 Mesh/Armature/Curve/Empty 等）",

        # Button A
        'btn_a_text':          "解除父级并删除 Empty",
        'btn_a_done':          "已解除 {} 个父级关系 | 已删除 {} 个 Empty | 剩余 {} 个物体 ({})",
        'btn_a_no_selection':  "请先选中至少一个物体",

        # Button B
        'btn_b_text':          "创建 Cube 形态空物体并父级化",
        'btn_b_no_targets':    "请先选中至少一个可处理物体（Mesh / Armature / Curve / Empty 等）",
        'btn_b_no_geom':       "无法获取几何数据（可能选中物体均为 Empty 或为空）",
        'btn_b_done':          "已创建 Cube 形态空物体 '{}' | 父级化 {} 个根物体（共 {} 个选中物体，{}{}）| 原包围盒尺寸: {:.4f} x {:.4f} x {:.4f} | 已乘系数: {}",
        'btn_b_kept_hierarchy': "，保留 {} 个子级层级",

        # Properties
        'prop_factor':         "换算系数",
        'prop_factor_desc':    "乘以空物体位移和缩放的系数（默认 0.0254 = 英寸→米）",
        'prop_empty_name':     "空物体名称",
        'prop_display_type':   "空物体显示样式",
        'prop_display_type_desc': "空物体在视口中的显示类型",
        'prop_display_size':   "空物体显示尺寸",

        # Enum items
        'type_cube':           "立方体 (Cube)",
        'type_cube_desc':      "立方体框（默认）",
        'type_arrows':         "箭头 (Arrows)",
        'type_arrows_desc':    "默认箭头，方向感强",
        'type_plain_axes':     "普通轴 (Plain Axes)",
        'type_plain_axes_desc': "三轴坐标线",
        'type_single_arrow':   "单箭头",
        'type_single_arrow_desc': "单方向箭头",
        'type_circle':         "圆圈",
        'type_circle_desc':    "圆圈",
        'type_sphere':         "球体",
        'type_sphere_desc':    "球体框",
    },
}


def _get_blender_lang():
    """获取 Blender 当前界面语言代码。
    返回如 'en_US' / 'zh_CN' 等；读取失败返回 'en_US'。"""
    try:
        return bpy.context.preferences.view.language
    except Exception:
        return 'en_US'


def _t(key, *args):
    """根据当前 Blender 语言返回对应翻译文本。
    - 优先按当前语言查找
    - 繁体中文 (zh_TW) 回退到简体中文 (zh_CN)
    - 其他未支持语言回退到英文 (en_US)
    - 若 key 不存在则返回 key 本身（防御性）
    支持传入 format 参数（会自动用 *args 填充占位符 {}）"""
    lang = _get_blender_lang()
    # 繁中回退简中
    table = TRANSLATIONS.get(lang) or TRANSLATIONS.get('zh_CN' if lang.startswith('zh') else 'en_US') or TRANSLATIONS['en_US']
    text = table.get(key, TRANSLATIONS['en_US'].get(key, key))
    if args:
        try:
            text = text.format(*args)
        except Exception:
            pass
    return text


# 可被处理的物体类型（导入模型常见组件，含 Empty 用于保留导入层级）
PARENTABLE_TYPES = {
    'MESH', 'ARMATURE', 'CURVE', 'SURFACE', 'META', 'LATTICE', 'FONT', 'EMPTY',
}

# 参与包围盒计算的物体类型（Empty 无几何，不参与底部中心计算）
GEOMETRY_TYPES = {
    'MESH', 'ARMATURE', 'CURVE', 'SURFACE', 'META', 'LATTICE', 'FONT',
}


# ---------------------------------------------------------------------------
# 工具函数：计算一组物体的合并世界包围盒
# ---------------------------------------------------------------------------
def _collect_world_bbox_points(objects):
    """返回所有传入几何物体包围盒角点的世界坐标列表。
    Mesh 用顶点（最精确），其余几何类型用 bound_box。
    Empty 不参与（无几何数据，会污染包围盒）。"""
    points = []
    for obj in objects:
        if obj.type not in GEOMETRY_TYPES:
            continue
        mw = obj.matrix_world
        if obj.type == 'MESH' and obj.data is not None and len(obj.data.vertices) > 0:
            # Mesh：直接读顶点，最精确
            for v in obj.data.vertices:
                points.append(mw @ v.co)
        else:
            # Armature / Curve / Surface / Meta / Lattice / Font：用 bound_box
            # bound_box 是 8 个 Vector((x, y, z))，局部坐标
            for corner in obj.bound_box:
                points.append(mw @ Vector(corner))
    return points


def _bottom_center_of(objects):
    """计算合并包围盒的底部中心点（世界坐标）。
    返回 (bottom_center, bbox_min, bbox_max) 或 None（无几何数据时）。"""
    points = _collect_world_bbox_points(objects)
    if not points:
        return None
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    zs = [p.z for p in points]
    bbox_min = Vector((min(xs), min(ys), min(zs)))
    bbox_max = Vector((max(xs), max(ys), max(zs)))
    bottom_center = Vector((
        (min(xs) + max(xs)) * 0.5,
        (min(ys) + max(ys)) * 0.5,
        min(zs),
    ))
    return bottom_center, bbox_min, bbox_max


def _find_roots(objects):
    """找出选中集合中的"根物体"。
    根物体 = 父级为 None，或父级不在选中集合中的物体。
    只父级化根物体可保留导入文件原有的父子层级结构
    （例如导入文件自带 Empty_A → Mesh_1 的层级，只把 Empty_A 挂到新 Cube 下，
     Mesh_1 仍保持为 Empty_A 的子级）。"""
    obj_set = set(objects)
    roots = []
    for obj in objects:
        if obj.parent is None or obj.parent not in obj_set:
            roots.append(obj)
    return roots


# ---------------------------------------------------------------------------
# Operator A：解除父级并删除 Empty
# ---------------------------------------------------------------------------
class OBJECT_OT_clear_hierarchy(Operator):
    """对选中物体执行 Alt+P (Clear and Keep Transformation) 解除所有父级关系，
    然后删除选中集合中的所有 Empty，保留 Mesh / Armature / Curve 等几何体。"""

    bl_idname = "object.clear_hierarchy"
    bl_label = "Clear Hierarchy"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # 至少选中一个物体才允许执行
        return len(context.selected_objects) > 0

    def execute(self, context):
        # 收集所有选中物体（含 Empty）
        selected = list(context.selected_objects)
        if not selected:
            self.report({'ERROR'}, _t('btn_a_no_selection'))
            return {'CANCELLED'}

        # 步骤 1：识别有父级的物体（需要 Alt+P 的候选）
        has_parent = [obj for obj in selected if obj.parent is not None]
        cleared_count = 0
        if has_parent:
            # 取消所有选中，仅选中有父级的物体
            for obj in context.selected_objects:
                obj.select_set(False)
            for obj in has_parent:
                obj.select_set(True)
            context.view_layer.objects.active = has_parent[0]
            # 执行 Alt+P → Clear and Keep Transformation
            bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
            cleared_count = len(has_parent)

        # 步骤 2：删除选中集合中的所有 Empty
        # 重新收集"原选中集合中仍存在的 Empty"（Alt+P 不删除物体，引用仍有效）
        empties_to_delete = [obj for obj in selected if obj.type == 'EMPTY'
                             and obj.name in bpy.data.objects]

        # 设置一个不会被删除的物体为 active（避免删除 active 物体报错）
        for obj in context.selected_objects:
            obj.select_set(False)
        safe_active = None
        for obj in selected:
            if obj.type != 'EMPTY' and obj.name in bpy.data.objects:
                safe_active = obj
                break
        context.view_layer.objects.active = safe_active

        deleted_count = 0
        for empty in empties_to_delete:
            if empty.name not in bpy.data.objects:
                continue
            bpy.data.objects.remove(empty, do_unlink=True)
            deleted_count += 1

        # 恢复剩余选中物体的选中状态（非 Empty 且仍存在的）
        remaining = [obj for obj in selected
                     if obj.name in bpy.data.objects and obj.type != 'EMPTY']
        for obj in remaining:
            obj.select_set(True)
        if remaining:
            context.view_layer.objects.active = remaining[0]

        # 类型统计
        type_counts = {}
        for obj in remaining:
            type_counts[obj.type] = type_counts.get(obj.type, 0) + 1
        type_summary = ", ".join(f"{t}:{c}" for t, c in sorted(type_counts.items()))

        self.report(
            {'INFO'},
            _t('btn_a_done', cleared_count, deleted_count, len(remaining), type_summary)
        )
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# Operator B：创建 Cube 形态空物体并父级化（核心执行逻辑）
# ---------------------------------------------------------------------------
class OBJECT_OT_auto_scaler(Operator):
    """在选中物体的底部中心创建 Cube 形态空物体，识别选中集合中的根物体
    （保留导入文件原有层级，含父级空物体）以 Keep Transform 方式父级化到
    新 Cube，然后将新 Cube 的位移与缩放（三轴）乘以换算系数。"""

    bl_idname = "object.auto_scaler"
    bl_label = "Auto Scaler"
    bl_options = {'REGISTER', 'UNDO'}

    # 可调参数（F6 / 重新执行面板可修改）
    # 注意：property 的 name/description 在类注册时求值，切换语言后需重启插件生效
    conversion_factor: FloatProperty(
        name=_t('prop_factor'),
        description=_t('prop_factor_desc'),
        default=0.0254,
        min=0.0,
        precision=6,
    )

    empty_name: StringProperty(
        name=_t('prop_empty_name'),
        default="Empty_Parent",
    )

    empty_display_type: EnumProperty(
        name=_t('prop_display_type'),
        description=_t('prop_display_type_desc'),
        items=[
            ('CUBE', _t('type_cube'), _t('type_cube_desc')),
            ('ARROWS', _t('type_arrows'), _t('type_arrows_desc')),
            ('PLAIN_AXES', _t('type_plain_axes'), _t('type_plain_axes_desc')),
            ('SINGLE_ARROW', _t('type_single_arrow'), _t('type_single_arrow_desc')),
            ('CIRCLE', _t('type_circle'), _t('type_circle_desc')),
            ('SPHERE', _t('type_sphere'), _t('type_sphere_desc')),
        ],
        default='CUBE',
    )

    empty_display_size: FloatProperty(
        name=_t('prop_display_size'),
        default=0.5,
        min=0.001,
        precision=3,
    )

    @classmethod
    def poll(cls, context):
        # 至少选中一个可处理物体才允许执行
        return any(obj.type in PARENTABLE_TYPES for obj in context.selected_objects)

    def execute(self, context):
        factor = float(self.conversion_factor)
        targets = [obj for obj in context.selected_objects
                   if obj.type in PARENTABLE_TYPES]

        if not targets:
            self.report({'ERROR'}, _t('btn_b_no_targets'))
            return {'CANCELLED'}

        # 1) 计算底部中心（仅几何体参与，Empty 不参与）
        result = _bottom_center_of(targets)
        if result is None:
            self.report({'ERROR'}, _t('btn_b_no_geom'))
            return {'CANCELLED'}
        bottom_center, bbox_min, bbox_max = result

        # 2) 创建空物体（type='EMPTY'）并将其显示形态设为 Cube 线框
        #    注意：此处是 Empty 对象，不是 Mesh Cube
        #      - bpy.data.objects.new(name, None) 第二参数为 None → 创建 Empty
        #      - empty.empty_display_type = 'CUBE' 仅决定视口显示样式（立方体线框）
        #      - 对象类型 obj.type 仍为 'EMPTY'，无 mesh data，不会参与渲染
        empty = bpy.data.objects.new(self.empty_name, None)
        empty.empty_display_type = self.empty_display_type  # 默认 'CUBE'，仅显示形态
        empty.empty_display_size = self.empty_display_size
        empty.location = bottom_center.copy()
        empty.scale = (1.0, 1.0, 1.0)
        empty.rotation_euler = (0.0, 0.0, 0.0)

        # 链接到当前激活的 collection
        target_collection = context.collection or context.scene.collection
        target_collection.objects.link(empty)

        # 3) 识别预清除后的根物体
        #    - Bip001 子树：Bip001 自身作为根（其内部骨骼层级保留），
        #      整棵子树挂到新 Cube 下，整体跟随缩放联动
        #    - 其他预清除后的独立物体：parent 为 None 的成为根
        roots = _find_roots(targets)

        # 4) 设置选中状态：新 Cube 为 active，并与所有根物体一起被选中
        #    （parent_set 要求 active 为父级，其他选中物体为子级）
        for obj in context.selected_objects:
            obj.select_set(False)
        for obj in roots:
            obj.select_set(True)
        empty.select_set(True)
        context.view_layer.objects.active = empty

        # 5) 父级化：等价于 Ctrl+P > Object (Keep Transform)
        #    建立父子关系时保持子物体的世界变换
        #    —— 根物体（含导入的父级空物体）挂到新 Cube 下后，
        #       其下属的所有子物体（网格/骨骼等）都会跟随新 Cube 变换
        bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)

        # 6) 将新 Cube 空物体的 location 和 scale（三轴）都乘以换算系数
        #    由于根物体已父级化（且当时保持了世界变换），新 Cube 变换改变后
        #    所有子物体（含导入层级下的网格体）世界变换会同步联动：
        #      新世界位置 = factor * 原世界位置
        #      新世界缩放 = factor * 原世界缩放
        #    这正是把英寸单位的模型整体转换为米制的效果
        empty.location = empty.location * factor
        empty.scale = Vector((
            empty.scale.x * factor,
            empty.scale.y * factor,
            empty.scale.z * factor,
        ))

        # 7) 汇报
        dims = bbox_max - bbox_min
        type_counts = {}
        for obj in targets:
            type_counts[obj.type] = type_counts.get(obj.type, 0) + 1
        type_summary = ", ".join(f"{t}:{c}" for t, c in sorted(type_counts.items()))
        non_root_count = len(targets) - len(roots)
        hierarchy_note = _t('btn_b_kept_hierarchy', non_root_count) if non_root_count > 0 else ""
        self.report(
            {'INFO'},
            _t('btn_b_done',
               empty.name, len(roots), len(targets),
               type_summary, hierarchy_note,
               dims.x, dims.y, dims.z, factor)
        )
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# Panel：侧栏 UI
# ---------------------------------------------------------------------------
class VIEW3D_PT_auto_scaler(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tool"
    bl_label = "Auto Scaler"

    def draw(self, context):
        layout = self.layout

        # ==================== 按钮 A：解除父级并删除 Empty ====================
        col = layout.column(align=True)
        col.scale_y = 1.1
        col.operator(
            "object.clear_hierarchy",
            text=_t('btn_a_text'),
            icon='TRASH',
        )

        layout.separator()

        # ==================== 按钮 B：创建 Cube 形态空物体并父级化 ====================
        col = layout.column(align=True)
        col.scale_y = 1.1
        col.operator(
            "object.auto_scaler",
            text=_t('btn_b_text'),
            icon='MESH_CUBE',
        )

        layout.separator()
        col = layout.column(align=True)
        col.label(text=_t('panel_usage'), icon='INFO')
        col.label(text=_t('panel_step_a'))
        col.label(text=_t('panel_step_b'))
        col.label(text=_t('panel_factor_hint'))
        col.label(text=_t('panel_supports'))
        col.label(text=_t('panel_preserves'), icon='LINKED')

        layout.separator()
        col = layout.column(align=True)
        targets = [o for o in context.selected_objects if o.type in PARENTABLE_TYPES]
        col.label(text=_t('panel_selected', len(targets)),
                  icon='MESH_CUBE' if targets else 'ERROR')
        if not targets:
            col.label(text=_t('panel_select_first'),
                      icon='BLANK1')


# ---------------------------------------------------------------------------
# 注册
# ---------------------------------------------------------------------------
classes = (
    OBJECT_OT_clear_hierarchy,
    OBJECT_OT_auto_scaler,
    VIEW3D_PT_auto_scaler,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
