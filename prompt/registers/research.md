# 当前研究状态与入口

更新：2026-09-21。以实际 JSON、哈希、Git 状态为准。

- 原计划完整保存在 `docs/RSI_RESEARCH_PLAN.md`，包括 F0–F5、E1–E10，不用短状态代替完整设计。
- 原始数据在仓库外 `../dataset/testDataset/LiDAR_xyz`、`../dataset/demo_dataset/demo dataset`；完整训练 Mesh 未下载。
- 派生数据 `../dataset/processed/wireframe_mesh_v001` 保留；v002 为投影闭环、相容边分割版本，52 对中 44 成功、8 失败，26 通过当前几何筛选。只作派生训练候选。
- 新实验 `work/experiments/2026-09-21/lod2-rsi-v001`；历史三栋 exact Git blob 算法复现、development20 固定基准、candidate001 凹轮廓。
- candidate001：11 改善、6 持平、2 退化、1 失败，未采用。模型 2124 未产生。观测 P95 不能证明补全准确。
- 20 栋为新授权开发样本，和历史训练 20 栋不是同组；输入 SHA 固定，不得互换。
- 原始 Git blob SHA `8b69b7e4f842d9628085adacdc7b27f73c5772f77b1f3c7f10f053c20458053a`；Windows checkout CRLF 的 SHA 不同但原历史 OBJ 可逐字节复现。
- 已实现外部几何评测、反馈包、人工候选接口、冻结与校验；未实现自动模型提议和真正外层反馈演化，未执行多种子/SOTA/比赛提交。
- 报告 `reports/2026-09-21-stage01/index.html`；可视化技能 mini-brief、数据和原图随报告保存。
- Git 交付快照：`releases/v0.1.0-reproduced-historical3-r2`、`v0.1.0-reproduced-dev20-r2`、`v0.1.1-concave-candidate01-r2`。r2 仅修正包装中缓存文件的排除，未修改算法和模型；初次包装保留本地并忽略。
- 后续：诊断凹域与屋面装配不相容；获得完整 Mesh 真值/城市组，核对近重复；固定基础模型/版本/调用预算后运行正式反馈实验。
- 稳定入口：`harness` CLI、`scripts/buildingworld/run_research_setup.py`、`render_research.py`、`check_derived_blender.py`、`export_research_report.py`。用法见 `docs/HARNESS_USAGE.md`。
- 出版前：所有 source/model/render/evaluator hash 一致；七视角、指标差值和失败表；同等证据/成本实验；冻结重新开始的 E7。
