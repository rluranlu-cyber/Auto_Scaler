# MtoB Auto Scaler 项目交接说明

> 最后整理日期：2026-10-19  
> 当前版本：v1.4.1  
> 目标宿主：Blender 5.0.1  
> 项目目录：`D:\GitHub\MtoB_Auto_Scaler`

本文档用于把项目交接给后续开发者或 agent。开始修改前，应先阅读本文档，再阅读根目录中的最新脚本和 README。不要把历史归档中的代码误认为当前实现。

## 1. 项目目标

Auto_Scaler 是一个 Blender 单文件插件，用于处理从 3ds Max 等软件导入 Blender 的模型，主要解决两个问题：

1. 清理导入模型中多余的父子关系和 Empty。
2. 将以英寸为单位的模型整体转换为米制，默认换算系数为 `0.0254`。

插件不是自动导入监听器。用户导入模型后，需要保持相关对象处于选中状态，再在 3D Viewport 的 N 侧栏中手动点击操作按钮。

## 2. 当前目录结构

```text
MtoB_Auto_Scaler/
├─ .git/
├─ .workbuddy/
│  └─ memory/
│     ├─ 2026-06-22.md
│     └─ MEMORY.md
├─ Archieve/
│  ├─ auto_scaler_v1.3.0.py
│  ├─ auto_scaler_v1.4.0.py
│  └─ auto_scaler.py
├─ doc/
│  └─ PROJECT_HANDOFF.md
├─ auto_scaler_v1.4.1.py
├─ auto_scaler_v1.4.1.zip
├─ LICENSE
└─ README.md
```

各部分用途：

- `auto_scaler_v1.4.1.py`：当前最新源文件，也是后续修改的基线。
- `auto_scaler_v1.4.1.zip`：当前发布包。包内包含 README 和安装用的 `auto_scaler.py`。
- `Archieve/`：历史版本归档目录。目录名按项目现状拼写为 `Archieve`，不要擅自改名。
- `.workbuddy/memory/`：历史需求、设计取舍、回退记录和版本约定。
- `README.md`：面向使用者的中英文说明，但目前部分版本信息仍停留在 v1.4.0。
- `doc/PROJECT_HANDOFF.md`：面向维护者和后续 agent 的交接文档。

## 3. 文件与版本管理约定

这是用户明确要求，后续开发必须遵守：

1. 根目录只保留最新版本的 `.py` 文件和对应的 `.zip` 发布包。
2. README、LICENSE、`.workbuddy`、`doc` 和 Git 文件不受上一条限制。
3. 开发新版本时，先把根目录中现有版本的 `.py` 和 `.zip` 移入 `Archieve/`。
4. 新版本使用明确版本号命名，例如：
   - `auto_scaler_v1.4.2.py`
   - `auto_scaler_v1.4.2.zip`
5. 历史归档永久保留，不得覆盖、重写或删除。
6. 根目录不再要求保留无版本号的 `auto_scaler.py`。
7. ZIP 内部可以继续使用 `auto_scaler.py` 作为用户安装文件名，但发布包本身必须带版本号。
8. 每次发版应同步更新：
   - 脚本顶部版本注释；
   - `bl_info["version"]`；
   - README 的版本徽章、技术规格和版本历史；
   - 本文档的当前版本与变更说明；
   - `.workbuddy/memory/MEMORY.md` 中的当前版本信息。

## 4. 当前插件入口与界面

安装方式：

1. Blender 5.0.1 中打开 `Edit > Preferences > Add-ons`。
2. 选择 `Install from Disk`。
3. 安装当前 `.py` 文件，或使用 ZIP 中的 `auto_scaler.py`。
4. 启用 `Auto_Scaler`。

界面位置：

```text
3D Viewport > N Sidebar > Tool > Auto Scaler
```

面板提供两个独立按钮：

- 按钮 A：解除父级并删除 Empty。
- 按钮 B：创建 Cube 形态 Empty、保留原有层级并进行单位换算。

## 5. 核心代码结构

当前脚本 `auto_scaler_v1.4.1.py` 的主要组成如下。

### 5.1 插件元数据

`bl_info` 定义插件名称、作者、版本、Blender 版本、界面位置和描述。

当前关键值：

```python
"name": "Auto_Scaler"
"version": (1, 4, 1)
"blender": (5, 0, 1)
"category": "Object"
```

### 5.2 国际化系统

主要符号：

- `TRANSLATIONS`
- `_get_blender_lang()`
- `_t(key, *args)`

支持语言：

- `zh_CN`：简体中文。
- `en_US`：英文。
- `zh_TW` 等中文语言回退到简体中文。
- 其他未支持语言回退到英文。

面板文本和 report 消息会在绘制或执行时调用 `_t()`，因此可以实时跟随 Blender 语言。

Property 的 `name`、`description` 和 Enum items 在类注册时求值。因此切换 Blender 语言后，属性面板文字可能需要禁用并重新启用插件才能刷新。这是当前已知设计限制，不是运行时错误。

### 5.3 对象类型集合

`PARENTABLE_TYPES`：

```text
MESH, ARMATURE, CURVE, SURFACE, META, LATTICE, FONT, EMPTY
```

这些类型可以参与按钮 B 的层级处理。

`GEOMETRY_TYPES`：

```text
MESH, ARMATURE, CURVE, SURFACE, META, LATTICE, FONT
```

这些类型可以参与包围盒计算。Empty 没有几何数据，因此不能参与底部中心计算。

### 5.4 包围盒与根节点工具函数

- `_collect_world_bbox_points(objects)`
  - Mesh：遍历所有顶点，并用 `matrix_world @ v.co` 转换为世界坐标。
  - 其他几何类型：读取 `bound_box` 的 8 个角点并转换到世界坐标。
  - Empty：跳过。
- `_bottom_center_of(objects)`
  - 计算所有几何点的合并包围盒。
  - 返回底部中心、最小点和最大点。
  - 底部中心公式为：`((min_x + max_x) / 2, (min_y + max_y) / 2, min_z)`。
- `_find_roots(objects)`
  - 根对象定义为：没有父级，或者父级不在当前选中集合中的对象。
  - 按钮 B 只把根对象挂到新 Empty 下，从而保留选中集合内部原有层级。

## 6. 按钮 A：解除父级并删除 Empty

Operator：`OBJECT_OT_clear_hierarchy`  
Blender ID：`object.clear_hierarchy`

执行流程：

1. 收集当前所有选中对象。
2. 找出存在父级的对象。
3. 只选中这些对象并执行：

   ```python
   bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
   ```

4. 收集原选中集合中的所有 Empty。
5. 在删除 Empty 前先保存所有非 Empty 对象的引用。
6. 删除 Empty。
7. 恢复剩余对象的选中状态和 active object。
8. 按对象类型显示处理统计。

必须保持的行为：

- 清除父级时保留世界变换。
- 删除范围仅限原选中集合中的 Empty。
- Mesh、Armature、Curve 等非 Empty 对象必须保留。
- 不要把“只保留 Mesh”理解成删除 Armature 或 Curve；现有设计明确避免破坏蒙皮工作流。
- 如果选中对象的父级不在选中集合中，只要该对象本身被选中且存在父级，它仍会被解除父级。

### v1.4.1 的关键修复

Blender 对象经 `bpy.data.objects.remove()` 删除后，旧 Python 引用会变成无效的 StructRNA 引用。继续访问其 `.name` 或 `.type` 可能触发：

```text
ReferenceError: StructRNA of type Object has been removed
```

v1.4.1 在删除前收集 `remaining` 非 Empty 对象，并对待删除对象增加 `ReferenceError` 防御。后续修改按钮 A 时不能重新引入“删除后遍历原 selected 列表并访问全部对象属性”的写法。

## 7. 按钮 B：创建父级并执行单位换算

Operator：`OBJECT_OT_auto_scaler`  
Blender ID：`object.auto_scaler`

默认参数：

| 参数 | 默认值 | 含义 |
|---|---:|---|
| `conversion_factor` | `0.0254` | 英寸到米的换算系数 |
| `empty_name` | `Empty_Parent` | 新建 Empty 的名称 |
| `empty_display_type` | `CUBE` | Empty 的视口显示形态 |
| `empty_display_size` | `0.5` | Empty 的视口显示大小 |

执行流程：

1. 从当前选中对象中筛选 `PARENTABLE_TYPES`。
2. 使用几何对象计算合并包围盒底部中心。
3. 创建一个 Empty：

   ```python
   bpy.data.objects.new(self.empty_name, None)
   ```

4. 设置 `empty_display_type='CUBE'`。
5. 把 Empty 放在原模型包围盒的底部中心。
6. 识别选中集合中的根对象。
7. 将新 Empty 设为 active，只选择根对象和新 Empty。
8. 执行：

   ```python
   bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)
   ```

9. 将新 Empty 的位置和三轴缩放都乘以换算系数。

必须保持的行为：

- 创建的是 Empty，不是真正的 Mesh Cube。
- `CUBE` 只表示 Empty 的视口线框样式。
- 只父级化根对象，不能把所有选中对象直接重挂到新 Empty，否则会破坏导入模型内部层级。
- 父级化时必须使用 Keep Transform。
- Empty 可以作为原模型的根节点被父级化，但不能参与包围盒计算。
- 只选择 Empty、没有任何几何对象时，应取消执行并报告无法获取几何数据。

### 为什么同时缩放 location 和 scale

完成 Keep Transform 父级化后，代码执行：

```python
empty.location *= factor
empty.scale *= factor
```

这样子对象的世界位置与世界尺寸都会按 `factor` 缩放，相当于围绕世界原点完成整体单位转换：

```text
新世界位置 = factor × 原世界位置
新世界缩放 = factor × 原世界缩放
```

不要只缩放 `scale`，否则模型尺寸会变化，但模型整体离世界原点的距离不会按相同比例换算，语义将与当前单位转换目标不同。

## 8. 已废弃方案

历史开发中曾尝试：

- 在按钮 B 前自动执行预清除。
- 自动查找网格体上层 Empty 并删除。
- 对名为 `Bip001` 的层级实施特殊保护。

这些方案经历过多次修改和回退，最终全部撤销。当前 v1.4.1 不包含自动预清除和 Bip001 特例。

注意：当前脚本按钮 B 附近仍有少量“预清除后”“Bip001 子树”的遗留注释，但实际代码不存在对应逻辑。这些注释应在后续维护中清理，不能据此恢复旧行为。

## 9. 版本历史摘要

| 版本 | 主要变化 |
|---|---|
| v1.0.0 | 初始底部中心定位、父级化和单位转换 |
| v1.1.0 | 扩展支持 Armature、Curve 等非 Mesh 类型 |
| v1.2.0 | Empty 改为 Cube 显示；识别根对象并保留原始层级 |
| v1.2.1 | 明确 Cube 只是 Empty 的显示形态，无逻辑变化 |
| v1.3.0 | 新增按钮 A，形成双按钮插件；曾由用户确认可用并封装 |
| v1.4.0 | 增加简体中文/英文自动适配 |
| v1.4.1 | 修复删除 Empty 后访问僵尸 StructRNA 引用的问题 |

## 10. 当前已知问题与技术债务

### 文档同步

- README 的版本徽章、技术规格和版本历史仍主要停留在 v1.4.0。
- README 安装步骤仍以 `auto_scaler.py` 为示例，而根目录当前使用版本号文件名。
- 应补充 v1.4.1 的僵尸引用修复记录。

### 源码注释

- 按钮 B 根对象识别附近仍提到已撤销的“预清除”和 `Bip001`。
- 这些是遗留注释，不代表现行需求。

### 性能

- Mesh 包围盒计算会遍历全部顶点，精度高，但超高面数模型可能较慢。
- 如要优化，必须验证使用 `bound_box`、evaluated mesh 或其他方案后，结果是否仍符合用户对底部中心精度的要求。

### Blender 上下文

- 当前 operator 依赖 `bpy.ops.object.parent_clear` 和 `bpy.ops.object.parent_set`。
- 代码的 `poll` 主要检查选择状态，没有完整检查 Object Mode、对象是否可编辑、对象是否来自只读链接库等情况。
- 后续若增强健壮性，应优先补充上下文检查和清晰报错，不要静默失败。

### 参数边界

- `conversion_factor` 当前允许最小值为 `0.0`。系数为零会让父级缩放归零并使模型折叠。
- 是否禁止零值属于产品行为变更，修改前应先与用户确认。

### 选中集合语义

- 如果某个选中对象的父级不在选中集合中，该对象会被视为根，并被重新挂到新 Empty 下。
- 插件的工作范围高度依赖用户当前选择。不要未经确认扩展到整个 Scene 或 Collection。

## 11. 验证状态

历史记录显示：

- v1.3.0 曾得到用户“成功了，可以永久封装”的反馈。
- 早期迭代主要完成过 Python 语法检查，但没有完整保存 Blender 自动化测试结果。
- v1.4.1 的修复逻辑经过静态代码核对，但当前交接时没有新的 Blender 5.0.1 全量回归测试记录。

因此，后续任何功能修改都不能只依赖静态阅读，应在 Blender 中进行实际验证。

## 12. 建议的测试矩阵

### 按钮 A

1. 单个无父级 Mesh。
2. 单个有父级 Mesh，父级为 Empty。
3. 同时选择 Empty 和多个子 Mesh。
4. Empty、Mesh、Armature、Curve 混合选择。
5. 只选择 Empty。
6. 选择对象的父级未被选择。
7. 连续执行按钮 A 两次。
8. 被删除 Empty 恰好是 active object。
9. 多层嵌套父子关系。
10. Undo/Redo 是否正确恢复。

重点观察：世界变换是否保持、非 Empty 是否保留、是否出现 StructRNA ReferenceError、选中状态是否合理。

### 按钮 B

1. 单个 Mesh，原点位于任意位置。
2. 多个分散的 Mesh。
3. Empty > Mesh 的原有层级。
4. Empty > Armature > Mesh 的混合层级。
5. 多个独立根对象。
6. 只选择 Empty，应明确报错且不创建新对象。
7. Mesh 数据为空。
8. 父级在选择集合外的对象。
9. 自定义换算系数 `1.0`。
10. 默认换算系数 `0.0254`。
11. 重复执行按钮 B。
12. Undo/Redo。

重点观察：底部中心位置、原始层级、世界位置和世界尺寸是否按系数换算、骨骼蒙皮是否保持正常。

### 国际化

1. Blender 为 `zh_CN`。
2. Blender 为 `en_US`。
3. Blender 为 `zh_TW`。
4. Blender 为其他语言。
5. 切换语言后面板文本是否实时变化。
6. 重新启用插件后 Property 文本是否更新。

## 13. 推荐的开发与发布流程

1. 查看 Git 状态，确认没有需要保留但来源不明的修改。
2. 阅读最新根目录脚本，不要直接基于 `Archieve/` 中的旧代码开发。
3. 判断版本类型：
   - 仅修复错误：补丁版本，例如 v1.4.2。
   - 新增兼容功能或界面功能：次版本，例如 v1.5.0。
4. 把当前根目录 `.py` 和 `.zip` 移入 `Archieve/`，不得覆盖同名历史文件。
5. 在根目录创建带新版本号的 `.py`。
6. 修改代码，并同步更新所有版本标识和文档。
7. 做静态语法检查。
8. 在目标 Blender 版本中完成测试矩阵中与改动相关的用例。
9. 生成带版本号的 ZIP。ZIP 内应至少包含安装用脚本和 README。
10. 检查 ZIP 内脚本与根目录最新脚本的逻辑和版本是否一致。
11. 查看 Git diff，确保未意外修改历史归档。
12. 经用户确认后再提交或发布；不要默认替用户执行 Git commit、push 或创建 Release。

## 14. 后续 agent 开始工作的最小阅读顺序

1. `doc/PROJECT_HANDOFF.md`
2. 根目录最新版本 `.py`
3. `README.md`
4. `.workbuddy/memory/MEMORY.md`
5. 仅在追溯历史决策时阅读 `.workbuddy/memory/2026-06-22.md`
6. 仅在比较版本差异时阅读 `Archieve/`

如本文档、README、`.workbuddy` 和实际代码发生冲突，应以以下优先级判断：

1. 用户最新明确指令。
2. 根目录最新版本代码的实际行为。
3. 本交接文档。
4. README。
5. 历史记忆和归档代码。

发现冲突后，应先向用户说明，再决定是否修改行为；不要仅凭历史注释恢复已经撤销的功能。

## 15. 当前建议的优先维护事项

在没有新功能需求时，建议按以下顺序处理：

1. 把 README 从 v1.4.0 同步到 v1.4.1。
2. 清理当前脚本中关于预清除和 Bip001 的遗留注释。
3. 在 Blender 5.0.1 中完成一轮 v1.4.1 回归测试并记录结果。
4. 评估是否需要兼容 Blender 4.2+ Extension 格式；这属于产品升级，不能未经用户确认直接改造。
5. 评估是否为核心纯计算逻辑增加可自动运行的测试，减少对 Blender UI 操作的依赖。

