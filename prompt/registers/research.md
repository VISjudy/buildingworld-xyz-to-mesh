# 当前研究状态与入口

更新：2026-09-21。以实际 JSON、哈希、Git 状态为准。

- 原计划完整保存在 `docs/RSI_RESEARCH_PLAN.md`，包括 F0–F5、E1–E10，不用短状态代替完整设计。
- 原始比赛数据在仓库外 `../dataset/testDataset/LiDAR_xyz`、`../dataset/demo_dataset/demo dataset`；BuildingWorld 完整训练 Mesh 尚未获取。
- 派生数据 v001/v002 保留。用户确认 demo 为屋顶数据，v002 的 26 个几何筛选通过者不再解释为完整立面训练真值；只用于屋顶调试。
- 新下载 Point2Building Zurich 28,415 对真实 ALS/Mesh，PolyGNN mini 200 对仿真 ALS/Mesh；已整理 78 对入门样例。详细审核等级见 `datasets.md`，不把“已下载”当“全库质量通过”。
- Point2Building 完整质量子集 363 对已整理（项目训练 312 / 封存测试 51）。用户指定先在固定 78 对上迭代稳定，再测试完整集；当前尚未运行 78 对算法基准，也没有完整集重建成绩。阶段与测试重叠边界见 `../protocols/dataset-stages.md`。
- 新实验 `work/experiments/2026-09-21/lod2-rsi-v001`；历史三栋 exact Git blob 算法复现、development20 固定基准、candidate001 凹轮廓。
- candidate001：11 改善、6 持平、2 退化、1 失败，未采用。模型 2124 未产生。观测 P95 不能证明补全准确。
- 20 栋为新授权开发样本，和历史训练 20 栋不是同组；输入 SHA 固定，不得互换。
- 原始 Git blob SHA `8b69b7e4f842d9628085adacdc7b27f73c5772f77b1f3c7f10f053c20458053a`；Windows checkout CRLF 的 SHA 不同但原历史 OBJ 可逐字节复现。
- 已实现外部几何评测、反馈包、人工候选接口、冻结与校验；未实现自动模型提议和真正外层反馈演化，未执行多种子/SOTA/比赛提交。
- 报告 `reports/2026-09-21-stage01/index.html`；可视化技能 mini-brief、数据和原图随报告保存。
- Git 交付快照：`releases/v0.1.0-reproduced-historical3-r2`、`v0.1.0-reproduced-dev20-r2`、`v0.1.1-concave-candidate01-r2`。r2 仅修正包装中缓存文件的排除，未修改算法和模型；初次包装保留本地并忽略。
- 后续：以新真实数据诊断立面与屋面装配，核准参考 Mesh 质量/坐标/近重复；固定基础模型/版本/预算后运行正式反馈实验；BuildingWorld 授权数据仍需申请。
- 稳定入口：`harness` CLI、`scripts/buildingworld/run_research_setup.py`、`render_research.py`、`check_derived_blender.py`、`export_research_report.py`。用法见 `docs/HARNESS_USAGE.md`。
- 出版前：所有 source/model/render/evaluator hash 一致；七视角、指标差值和失败表；同等证据/成本实验；冻结重新开始的 E7。
- 新对话入口已统一为 `memory.md`；成功/失败记录追加到 `prompt/knowledge/experiences.jsonl`；旧 PROJECT_MEMORY 原文归档，不再维护双份当前状态。
