# 项目记忆入口（L1）

更新：2026-09-21。只保留稳定背景、阶段状态和索引；证据优先于本页摘要。

## 研究背景

独栋机载 LiDAR → 保持源坐标的 LoD2 OBJ、结构线框和质量报告。参加 BuildingWorld 比赛，并研究 Recursive Self-Improvement Harness：固定基础大模型，通过外部程序反馈与建筑知识改进算法，再演化反馈/经验策略。最终重建推理无需大模型，不训练基础大模型。

两项待验证贡献：外部反馈的内容/模态是否提高修改效果；演化后的 Harness 从相同初始算法在新任务上是否提高后续改进效率。完整 F0–F5、E1–E10 协议保存在 `docs/RSI_RESEARCH_PLAN.md`，不得以本摘要代替。

## 当前事实

- 起始仓库提交 `46a2c3e`；工作分支 `research/lod2-rsi-harness`。Git 远程：VISjudy/buildingworld-xyz-to-mesh。继续前核对当前 Git 状态。
- 主线基准 `v0.1.0-baseline`；历史 10/1000/2000 已逐字节复现。v0.5.1 是此前工程版本，不能把其人工改进收益归入新 Harness。
- 新 development20 来自用户授权测试目录，已转为开发用途，和历史训练 20 栋不同；不能承担封存测试结论。
- 第一候选凹轮廓：11 改善、6 持平、2 退化、1 失败，未采用。保存失败与全批次对比。
- 外部评测、隔离模型提议、反馈包、候选复测、冻结和渲染已跑通首轮。78 对小试：基准/F0 71 成功，F3 77 成功；原始/演化 Harness 迁移均 26/30，没有观察到迁移收益。仅单候选单种子，不证明递归改进；正式多种子/SOTA/比赛提交未完成。
- 用户已确认 demo_dataset 只有屋顶。44 个线框派生 Mesh、26 个几何筛选通过者仍没有真实立面监督；不再作为完整建筑 GT。具体纠正见数据注册表。
- 新数据已下载：Point2Building Zurich 28,415 对真实 ALS/参考 Mesh；PolyGNN mini 200 对仿真 ALS/Mesh。闭合与立面联合筛选分别得到 71/228、199/200；真实组分母是闭合预筛子集，不代表总体比例。已导出 78 对入门样例；详见数据注册表和审计。
- 全量扩展审核已完成：Point2Building 全部 1,087 个闭合候选中，363 对通过联合质量门槛与 Blender 复核，完整导出；项目训练 312 / 封存测试 51，作者划分另存。当前只允许用固定 78 对迭代，稳定并冻结后再启用完整集；未在完整集执行重建。
- 18 对合格作者 test 已在入门组；51 对项目测试来自作者 train，不冒充作者标准测试或作者预训练模型的未见样本。阶段协议见 `prompt/protocols/dataset-stages.md`。
- 当前完整本地集合为真实 363 + 仿真 mini 199 = 562 对，入口 `../dataset/processed/complete_pairs_v001/`；项目训练 432 / 封存测试 130，包含原 78 对。用户已明确本轮仅纳入已下载 mini 的全部合格数据，不下载 Munich 完整发布版；真实/仿真指标分开报告。
- 全 562 对统一预处理到 `../dataset/processed/standardized_pairs_v001/`，仅用输入 XYZ 确定变换、保留所有点并往返校验。方法见 `docs/DATASET_METHODS_V001.md`。最新实验报告 `reports/2026-09-21-feedback-components-v002/`；完整训练432/测试130仍未重建。

- v002综合反馈/文本知识均78/78当前拓扑通过，历史v0.5.1为76输出/28通过；单候选图像差异未证明因果，高度检查开关全部OBJ相同。新知识v002增K09与2条经验；旧8条规则不改。真实37/38最低回波不足以代表底高，禁止绝对Z推断立面。方法与版本解释见 `docs/FEEDBACK_COMPONENTS_V002.md`；完整集保持锁定。

## 快速恢复（顺序）

1. `git status --short`，确认目录和未提交变动。
2. 读本文件及 `prompt/registers/research.md`，判断已完成、进行中与未验证项。
3. 按下表只加载命中文档；需要精确数字时跟随原始 JSON/manifest。
4. 查正在执行的任务和 `.part` 文件，不重复下载或重复运行正式实验。
5. 完成阶段后按 `prompt/protocols/memory-management.md` 更新记录并运行校验。

| 任务 | 关键词 | L2 入口 |
|---|---|---|
| 研究接续 | 继续、背景、RSI、Harness、基准、反馈、当前 | prompt/registers/research.md |
| 数据获取/审核 | 数据集、立面、屋顶、GT、Mesh、Point2Building、PolyGNN | prompt/registers/datasets.md |
| 经验复用 | 成功、失败、回归、经验、候选、教训 | prompt/knowledge/experience-index.md |
| 记忆维护 | memory、记忆、记录、接续、归档 | prompt/protocols/memory-management.md |
| 文献/建筑规则 | 文献、建筑知识、City3D、BWFormer、规则 | docs/LITERATURE_REVIEW_RSI.md；config/knowledge/rules.json |
| 完整实验 | 消融、实验矩阵、E1、F0、统计、迁移 | docs/RSI_RESEARCH_PLAN.md；experiments/INDEX.md |

## 目录与边界

- `../dataset/`：原始数据、外部下载；`../dataset/processed/`：有来源记录的派生数据。
- `work/experiments/`：可重跑中间产物和完整日志，不进 Git。
- `releases/`：算法/知识/依赖/模型/反馈/指标/渲染冻结包，旧版本不可覆盖。
- `reports/`：可交付 HTML/图表/证据；阶段报告使用 OpenAI data visualization 技能。
- `prompt/`：L2 按需上下文；`experiments/INDEX.md`：L3 原始证据入口。

当前缺正式 Mesh GT 的旧分数均为观测代理，不能称官方 CD/ECD。几何闭合不代表建筑语义正确；没有点不代表不存在。所有数据、代码、知识与评测器版本必须可追踪。

旧 `PROJECT_MEMORY.md` 的原文保存在 `docs/history/PROJECT_MEMORY_legacy_2026-09-21.md`。其中训练数据数量、旧本机路径是历史环境记录，不代表当前机器存在这些数据。
