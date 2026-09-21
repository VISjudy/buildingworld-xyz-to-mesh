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
| EXP-S004 | 成功 / 工程验证 | 完整闭合池审核与独立 Blender 复核导出 363 对，阶段门禁保护 51 对项目封存测试 | reports/2026-09-21-point2building-complete/summary.json |
| EXP-C002 | 纠正 / 测试用途 | 合格作者 test 18 对全在入门开发组；项目封存 51 来自作者 train，不能冒充作者标准未见测试 | reports/2026-09-21-point2building-complete/split-inventory.json |
| EXP-S005 | 成功 / 工程验证 | 真实 363 与已下载 mini 全部合格 199 统一入库，真实/仿真分层、入门/封存隔离 | reports/2026-09-21-real-synthetic-collection/summary.json |
| EXP-S006 | 成功 / 工程验证 | 输入定义的可逆归一化统一562对，GT不能定义变换或向输入补点 | docs/DATASET_METHODS_V001.md；starter78-feedback-pilot/summary.json |
| EXP-H001 | 假设 / 局部支持 | 失败门控重试可恢复样例；共同成功几何收益与恢复率须分开 | starter78-feedback-pilot/summary.json |
| EXP-F002 | 零收益 / 已测范围 | 前48对学习的策略在新30对同起点提议未优于原始策略 | starter78-feedback-pilot/summary.json；policy_evolved.json |

记忆检索使用条件和失败类型，不能按建筑 ID 编写重建特例。建筑知识库规则与实验经验分别冻结：`config/knowledge/rules.json` 是初始规则，经验条目不是自动生效的硬约束。
