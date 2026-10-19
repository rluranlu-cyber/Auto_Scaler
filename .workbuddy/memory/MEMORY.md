# Auto_Scaler 项目长期记忆

## 当前版本：v1.4.1（最新）

**当前发布文件（项目根目录）**:
- `auto_scaler_v1.4.1.py`
- `auto_scaler_v1.4.1.zip`

**历史归档目录**: `Archieve/`
- `auto_scaler_v1.3.0.py`（v1.3.0 永久归档，不可覆盖）
- `auto_scaler_v1.4.0.py`（v1.4.0 永久归档，不可覆盖）
- `auto_scaler.py`（旧工作文件，内容为 v1.4.1）

## 用户明确约定

- 各版本归档文件（`auto_scaler_vX.Y.Z.py`）**永久保留，不可覆盖**
- 项目根目录只保留最新版本的 `.py` 文件和对应 `.zip` 发布包（README、LICENSE、项目配置等非发布文件不受此限制）
- 开发新版本时，将根目录中现有版本的 `.py` 和 `.zip` 移入 `Archieve/`，再在根目录放置新版本文件
- 新版本使用明确版本号命名（如 `auto_scaler_v1.5.0.py` 和 `auto_scaler_v1.5.0.zip`）
- 不再要求根目录保留无版本号的 `auto_scaler.py`

## v1.4.1 功能概要（当前最新）

双按钮单文件插件，适配 Blender 5.0.1，UI 文本根据 Blender 界面语言自动适配（zh_CN / en_US）：

**按钮 A：解除父级并删除 Empty**（`object.clear_hierarchy`）
- 对选中物体执行 Alt+P (Clear and Keep Transformation) 解除所有父级关系
- 删除选中集合中的所有 Empty
- 保留 Mesh / Armature / Curve 等其他几何体（仅删 Empty）

**按钮 B：创建 Cube 形态空物体并父级化**（`object.auto_scaler`）
- 计算选中物体合并包围盒底部中心
- 创建 Cube 形态空物体（Empty 对象，display_type='CUBE'）
- 识别根物体，以 Keep Transform 方式父级化到新 Cube
- 新 Cube 的 location 和 scale 三轴都乘以 0.0254（英寸→米）

**i18n 系统**:
- `TRANSLATIONS` 字典含 en_US 和 zh_CN 两套完整翻译
- `_get_blender_lang()` 读 `bpy.context.preferences.view.language`
- `_t(key, *args)` 自动选择语言 + format 填充
- 回退规则：zh_TW → zh_CN；其他语言 → en_US
- Property name/description 在类注册时求值，切换语言需重启插件
- Panel draw 内文本每次重绘实时跟随语言

## 关键技术决策（用户确认）

- Cube 是 Empty 的显示形态，不是真正的 Mesh Cube
- 按钮 B 保留导入文件原有父子层级，仅父级化根物体
- 按钮 A 仅删 Empty，不删 Armature/Curve（避免破坏蒙皮）
- 命名保持简洁：插件名 Auto_Scaler，不带版本号后缀

## 安装位置

3D Viewport 侧栏（按 N）> Tool 标签 > "Auto Scaler" 面板

## 版本历史

- v1.0.0 → v1.2.0 → v1.2.1（措辞澄清）→ v1.3.0（双按钮封装）→ v1.4.0（i18n）→ v1.4.1（修复僵尸引用报错）
- 中间尝试过 v1.3/v1.4 的 Bip001 保护方案，已废弃
- v1.3.0 是在 v1.2.0 基础上新增按钮 A 的最终版本
- v1.4.0 是在 v1.3.0 基础上新增 i18n 语言适配
- v1.4.1 修复按钮 A 删除 Empty 后遍历僵尸引用导致 ReferenceError 的问题
