# PipeAnnotator 管线流程文档

## 最终目标

**多边形精细化标注 → 正确的标注数据集 → YOLO 训练 → 管件识别模型**

---

## 一、图库建设 (Gallery Building)

### 1.1 从已知品类图片提取特征

输入：按文件夹分类的管件图片（如管件1/2/3/4）
输出：`gallery_v2/gallery.json` + `gallery_feats.npy`

**流程：**
- 读取图片 → FastSAM 分割 → 物理过滤（面积/长宽比/颜色）→ MobileNetV2 提取 1280 维特征 → 标签来自文件夹名 → 入库

**文件：** `build_gallery_from_*.py`

**当前状态：**
- gallery_v2：35,168 ROIs / 21 类（镀锌三通、弯头、活接、异径三通、内丝直接、钢制三通）
- gallery_v3：11,311 ROIs / 8 类（塑料管、表接头、镀锌丝堵、镀锌异径内丝、钢制弯头90°×4）
- gallery_v4：暂缺（穿墙管/钢制三通/钢制异径三通图片损坏）

---

## 二、检测管线 (Detection Pipeline) — `gui.py`

### 2.1 FastSAM 分割 (`_run_fastsam_detection`)

**输入：** 2560×1440 BGR 图片
**输出：** 管件 ROI 列表（mask + bbox + contour）

**流程：**
1. 图片缩放到 576×1024
2. FastSAM 推理（约 6-7 秒/张，CPU）
3. IoM 空间合并 + 几何过滤（去小碎片、合并邻近 mask）
4. 面积上限门控：bbox 超过图像 50% 的直接丢弃
5. 返回兼容下游的 result 列表

**功能：** 替代传统的 Otsu CV 分割。FastSAM 基于学习的分割在钢台面低对比度场景下仍有一定召回率。

### 2.2 GridRescue 漏检救援 (`_grid_rescue_missed`)

**输入：** 原图 + FastSAM 已有结果
**输出：** 额外发现的管件（经 IoU 去重）

**流程：**
1. Otsu 网格扫描 2560×1440 全图
2. 网格单元有前景但 FastSAM 未覆盖 → 标记为待检查区域
3. 局部 FastSAM 返校（仅处理候选区域）
4. IoU > 0.3 去重（避免与已有结果重叠）
5. 按 x 坐标排序后合并到结果列表

**功能：** 弥补 FastSAM 遗漏的管件，尤其是钢制暗色管件。

### 2.3 分类管线 (`_classify_pipeline`)

**输入：** FastSAM 产出的 ROI（mask + bbox 区域）
**输出：** 赋予品类标签和置信度的检测结果

**四层递进分类：**

```
Layer 1: HSV 预过滤
    └─ 颜色/亮度/饱和度物理门控
    └─ 材质初步判定（镀锌亮/钢制暗/铜塑料有色）
    └─ 通过率 73-100%

Layer 2: CNN KNN 匹配 (MobileNetV2)
    └─ 提取 1280 维特征向量
    └─ 与 gallery_v2/v3 所有样本进行 KNN(k=3) 加权匹配
    └─ 返回最佳品类 + 置信度
    └─ 钢制/铜/塑料等新材质自动推断

Layer 3: DN 面积查找 (`dn_lookup.py`)
    └─ 基于 ROI 像素面积估算管径
    └─ 1280×720 下标定：6.5062 px/mm
    └─ DN48/DN57/DN89 面积零重叠
    └─ 缩小候选范围

Layer 4: NCC 模板匹配 (`fitting_matcher.py`)
    └─ 同类内细分（如钢制弯头 DN89 vs DN50）
    └─ 三步状态：Hit(≥0.60) / Uncertain(≥0.45) / Miss(<0.45)

Layer 5: SKU Override 覆盖
    └─ 用户手动修正过的 SKU 优先
    └─ 映射 key 格式：`编号|材质|类型|管径`
    └─ 编号精确匹配 > 品类模糊匹配
```

---

## 三、人工修正与闭环学习 (Correction Loop)

### 3.1 用户操作入口 (`gui.py`)

| 操作 | 触发点 | 功能 |
|------|--------|------|
| **修正标签** | 审核视图 → 点击待修正行 | 从下拉框选择正确分类 |
| **标注缺失管件** | 增加手动标注 | 在图上画框，指定品类别 |
| **标记错误** | 标记错误按钮 | 排除此检测项（不影响 YOLO 统计） |
| **多边形精修** | 勾选"多边形精修" | GrabCut 迭代 2 次精化边缘 |
| **确认/更新** | 点"更新"按钮 | 触发学习闭环 |

### 3.2 闭环学习 (`_learn_from_corrections`)

**用户确认修正后，系统自动做 5 件事：**

```
1. corrections_db SQLite 记录
   └─ 保存修正坐标 + 原标签 + 新标签

2. CNN Gallery 更新
   └─ 将修正 ROI 的特征 + 标签追加到 gallery_v2

3. DN 面积校准更新
   └─ 根据修正 ROI 的面积更新 DN 查找表

4. SKU Override 写入
   └─ 编号|材质|类型|管径 → 具体 SKU
   └─ 后续同型号管件自动匹配正确标签

5. NCC 模板注入（运行时缓存）
   └─ 重启后需手动"更新"恢复
   └─ 从 corrections_db 重建模板
```

### 3.3 自动传播匹配 (`_rematch_unnamed_items`)

**当用户修正一个管件后：**
1. 扫描当前图中所有"未命名"管件
2. NCC + CNN 双路比对修正后的模板
3. 高度匹配（NCC≥0.60）→ 自动填入
4. 中等匹配（NCC≥0.45）→ 候选提示
5. 低匹配 → 保持"未知"等待手动

---

## 四、YOLO 训练数据导出

### 4.1 YOLOExporter (`yolo_exporter.py`)

**触发条件：** 用户完成修正 + 点"更新"按钮

**输出：** `D:\pipe-annotator-desktop\training_data\`

```
training_data/
  images/          # 原图（2560×1440 JPEG）
  labels/          # 标注文件（两格式混合）
    └── *.txt (bbox)      # 5 字段：class_id x y w h
    └── *.txt (segment)   # 多字段：class_id x1 y1 x2 y2 ...
```

**多边形 vs 矩形判定：**
- 管件轮廓有效（有正确 mask）→ 保存为 **segment 格式**（多边形坐标点）
- 只有 bbox 无轮廓 → 保存为 **bbox 格式**

**当前数据量：**
- 40 个 segment 格式文件
- 1,653 个 bbox 格式文件
- 共计 1,693 个标注文件

### 4.2 自动训练 (`auto_train_yolo.py`)

**功能：** 检测标注数量达到阈值后自动触发 YOLO 训练

**流程：**
1. 扫描 `training_data/labels/` 统计各品类数量
2. 重建 `data.yaml`（品类名 → ID 映射）
3. 启动 YOLO11n 训练（imgsz=320, batch=1, epochs=100）
4. 保存最佳模型到 `models/yolo11n_trained.pt`

**约束：**
- 8GB RAM / 4 核 CPU，仅支持 batch=1
- 训练数据含大量噪声背景框（需要人工清理）

---

## 五、完整运行流程

```
┌──────────────────────────────────────────────────────────┐
│  用户启动：python src/gui.py                              │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ① 加载模型：FastSAM-x.pt + MobileNetV2 + gallery_v2      │
│     ├─ FastSAM（138MB，首次约 11s）                        │
│     ├─ Gallery（35,168 ROIs / 21 品类）                   │
│     └─ SKU Override / corrections_db                      │
│                                                          │
│  ② 导入图片：全图或单张                                   │
│     └─ 文件选择 → 显示在检测视图                          │
│                                                          │
│  ③ 自动检测                                              │
│     ├─ FastSAM 分割（6-7s/张）                              │
│     ├─ GridRescue 漏检救援（Otsu + 局部 FastSAM）          │
│     ├─ HSV 预过滤                                          │
│     ├─ CNN KNN 分类                                        │
│     ├─ DN 面积查找                                         │
│     ├─ NCC 同类内细分                                      │
│     └─ SKU Override 最终覆盖                                │
│                                                          │
│  ④ 人工审查（核心步骤）                                    │
│     ├─ 检查自动检测结果 → 修正错误标签                     │
│     ├─ 补充漏检管件 → 手动标注                             │
│     ├─ 多边形精修 → 勾选"多边形精修"后用 GrabCut           │
│     ├─ 标记错误 → 排除错误检测                             │
│     └─ 点"更新" → 触发闭环学习                              │
│                                                          │
│  ⑤ 闭环学习                                              │
│     ├─ corrections_db 持久化                               │
│     ├─ Gallery 增量更新                                    │
│     ├─ SKU Override 写入                                   │
│     ├─ DN 校准更新                                         │
│     └─ YOLO 标注导出（segment优先/bbox回退）                │
│                                                          │
│  ⑥ 迭代：换下一张图 → 回到步骤③                           │
│                                                          │
│  ⑦ 导出 + 训练                                           │
│     ├─ YOLOExporter：training_data/                       │
│     └─ auto_train_yolo.py → models/yolo11n_trained.pt     │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 六、当前瓶颈与待办

### 已知问题

| 问题 | 影响 | 状态 |
|------|------|------|
| 穿墙管/钢制三通/钢制异径三通图片损坏 | gallery_v4 缺失 776 张 | 需重新获取 |
| CNN 标签格式不统一（有的有 SKU 编号，有的没有） | KNN 匹配可能错误 | 已修复正则 |
| SKU Override material 提取 Bug | `52-E273` 开头类别材质检测失败 | 已修复 |
| GridRescue bbox 格式混用（xyxy vs xywh） | IoU 去重失效 → 重复框 | 已修复 |
| 钢制暗色管件 FastSAM 召回率低 | 部分管件漏检 | 需更多数据 |
| YOLO 训练数据噪声（background 框） | 模型精度低 | 需人工清理 |
| 8GB RAM，YOLO 训练仅 batch=1 | 训练慢 | 硬件限制 |

### 优先级路线

```
P0: 获取管件4图片（图片损坏原因调查 + 重新获取或修复）
P1: 合并 gallery_v3 → gallery_v2（新增 11,311 ROIs / 8 类）
P2: 用新 Gallery 跑 10 张端到端测试 → 确认 KNN 准确率
P3: 批量标注 → 积累更多 segment 格式 YOLO 数据
P4: YOLO 训练 → 验证模型效果
P5: 迭代优化 → 提升准确率
```
