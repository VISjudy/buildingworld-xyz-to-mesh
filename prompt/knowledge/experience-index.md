# 成功与失败经验索引

机器可读记录：[experiences.jsonl](experiences.jsonl)。新增记录追加，纠正用新 ID 和 supersedes；不能删除失败以提升成功率。

| ID | 类型 / 状态 | 适用结论 | 证据 |
|---|---|---|---|
| EXP-S001 | 成功 / 工程验证 | 原始 Git blob 与路径适配可逐字节复现历史三栋 | v0.1.0-reproduced-historical3-r2/reports/results.json |
| EXP-F001 | 失败 / 假设 | 仅将凸轮廓替换凹轮廓会触发部分分区不相容；11 提升不能掩盖 2 退化、1 失败 | v0.1.1-concave-candidate01-r2/reports/decision.json |
| EXP-S002 | 成功 / 工程验证 | 冻结文件禁换行转换、排除字节码，并从 Git 归档检验，能保持快照一致 | reports/2026-09-21-stage01/git-snapshot-verification.json |
| EXP-C001 | 纠正 / 数据边界 | demo 为屋顶，26 个几何筛选通过 Mesh 不构成完整立面训练真值 | datasets.md、stage01/derived_qa.json |
| EXP-L001 | 限制 / 尚未完成 | 观测 P95 不检测无观测区域真实性，当前不能宣称官方分数或递归改进 | docs/RSI_RESEARCH_PLAN.md |
| EXP-S003 | 成功 / 工程验证 | 真实 ALS 中能筛出立面与完整参考 Mesh 配对，但需把下载数、闭合数和立面审核数分开 | reports/2026-09-21-dataset-audit/dataset-audit-summary.json |
| EXP-L002 | 限制 / 公平性 | Point2Building 作者加载器会用 GT 高程补底面点；不要把这种预处理当原始实测数据 | docs/DATA_ACQUISITION.md |

记忆检索使用条件和失败类型，不能按建筑 ID 编写重建特例。建筑知识库规则与实验经验分别冻结：`config/knowledge/rules.json` 是初始规则，经验条目不是自动生效的硬约束。
