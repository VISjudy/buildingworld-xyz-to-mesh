# 当前研究状态与入口

更新：2026-09-21。以实际 JSON、哈希、Git 状态为准。

- 原计划完整保存在 `docs/RSI_RESEARCH_PLAN.md`，包括 F0–F5、E1–E10，不用短状态代替完整设计。
- 原始比赛数据在仓库外 `../dataset/testDataset/LiDAR_xyz`、`../dataset/demo_dataset/demo dataset`；BuildingWorld 完整训练 Mesh 尚未获取。
- 派生数据 v001/v002 保留。用户确认 demo 为屋顶数据，v002 的 26 个几何筛选通过者不再解释为完整立面训练真值；只用于屋顶调试。
- 新下载 Point2Building Zurich 28,415 对真实 ALS/Mesh，PolyGNN mini 200 对仿真 ALS/Mesh；已整理 78 对入门样例。详细审核等级见 `datasets.md`，不把“已下载”当“全库质量通过”。
- Point2Building 完整质量子集 363 对已整理（项目训练 312 / 封存测试 51）。78 对基准和首轮反馈/迁移小试已运行；完整集尚无重建成绩，仍待入门集稳定。阶段与测试重叠边界见 `../protocols/dataset-stages.md`。
- 最新完整本地集合补齐 mini 仿真 199 对，统一为 562 对（432 训练 / 130 封存测试）；用户明确本轮不下载 Munich 完整发布库。入口 `../dataset/processed/complete_pairs_v001`；仅入门 78 当前可用，按真实/仿真分别评价。
- 新实验 `work/experiments/2026-09-21/lod2-rsi-v001`；历史三栋 exact Git blob 算法复现、development20 固定基准、candidate001 凹轮廓。
- candidate001：11 改善、6 持平、2 退化、1 失败，未采用。模型 2124 未产生。观测 P95 不能证明补全准确。
- 20 栋为新授权开发样本，和历史训练 20 栋不是同组；输入 SHA 固定，不得互换。
- 原始 Git blob SHA `8b69b7e4f842d9628085adacdc7b27f73c5772f77b1f3c7f10f053c20458053a`；Windows checkout CRLF 的 SHA 不同但原历史 OBJ 可逐字节复现。
- 已实现外部几何评测、反馈包、隔离模型候选、一次经验生成策略及同起点迁移复测、冻结与校验。未观察到首轮策略迁移收益；完整多轮演化、多种子/SOTA/比赛提交未完成。
- 报告 `reports/2026-09-21-stage01/index.html`；可视化技能 mini-brief、数据和原图随报告保存。
- Git 交付快照：`releases/v0.1.0-reproduced-historical3-r2`、`v0.1.0-reproduced-dev20-r2`、`v0.1.1-concave-candidate01-r2`。r2 仅修正包装中缓存文件的排除，未修改算法和模型；初次包装保留本地并忽略。
- 后续：以新真实数据诊断立面与屋面装配，核准参考 Mesh 质量/坐标/近重复；固定基础模型/版本/预算后运行正式反馈实验；BuildingWorld 授权数据仍需申请。
- 稳定入口：`harness` CLI、`scripts/buildingworld/run_research_setup.py`、`render_research.py`、`check_derived_blender.py`、`export_research_report.py`。用法见 `docs/HARNESS_USAGE.md`。
- 出版前：所有 source/model/render/evaluator hash 一致；七视角、指标差值和失败表；同等证据/成本实验；冻结重新开始的 E7。
- 新对话入口已统一为 `memory.md`；成功/失败记录追加到 `prompt/knowledge/experiences.jsonl`；旧 PROJECT_MEMORY 原文归档，不再维护双份当前状态。

## 当前小试（2026-09-21）

- `experiments/2026-09-21/starter78-feedback-pilot/summary.md` 为验收入口；完整原始运行在同 slug 的 `work/experiments/`。
- 562 对统一数据规范见 `docs/DATASET_METHODS_V001.md`、`config/data_protocol_v001.json`；数据入口 `../dataset/processed/standardized_pairs_v001/manifests/starter78.json`。30 是分析包围盒对角线，不是米。
- 原始 v0.1.0 + 同一预处理：71/78 成功；F0 71/78，改善共同成功样例均值；F3 77/78，恢复6对、共同成功指标不变。两者是同父基准的独立候选，不能把 F0 称为 F3 算法父版。
- 策略只由 discovery24+selection24 经验生成。transfer30 重启同一原始算法，原始/演化策略均26/30且共同成功差值为0；两迁移候选不采用。不把负结果解释为已证明整个研究方向无效。
- 总294次重建尝试，4个候选、1个元策略、1个种子；模型继承相同配置但提供方快照/Token不可观测，不宣称严格等Token实验。
- 交付：`reports/2026-09-21-starter78-feedback-pilot/`，5个独立冻结版本见其 summary。27项测试通过；具体冻结、浏览器与往返验证跟随报告 QA 文件。
- 下一步：在78对内检验支持点不足与轮廓误差的直接诊断，进行组合/消融与多次独立提议；尚无稳定高准确率证明，不切换完整集。

## 最新：反馈组成、图像与高度（v002）

入口 `experiments/2026-09-21/feedback-components-v002/summary.md`；报告 `reports/2026-09-21-feedback-components-v002/index.html`；方法 `docs/FEEDBACK_COMPONENTS_V002.md`。3个隔离提议T/TK/FULL，6组批量468次新尝试（含保留的原T API失败与历史v0.5.1）；完整集未启用。

FULL与TK均78/78当前拓扑通过；T兼容版77输出/76通过；原归档v0.5.1为76输出/28通过。FULL相对TK两来源共同成功CD/ECD均值降低，单候选/多算子与不等信息量不能证明图像因果。高度检查开关78份OBJ完全一致。FULL未在所有指标上优于F0或历史版。

旧知识K01–K08不改；新 `config/knowledge/rules-v002.json` 增K09和X01/X02，仅供新实验使用。六层反馈增强，FULL确实查看2张诊断图；旧图片没有进入模型反馈。尚未完成逐层去除和新迁移验证。v002报告、六冻结包、模型来源、兼容修正和七视角均独立保留。下一步多次独立提议及真实底高/多屋面问题，不能依据拓扑通过升级完整集。
