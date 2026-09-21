slug: facade-data-acquisition
日期: 2026-09-21
状态: 已定案（数据下载与当前审计）
一句结论: 已下载 Point2Building Zurich 28415 对真实 ALS 和 PolyGNN mini 200 对仿真 ALS，导出 78 对经过当前筛选的入门配对。
产物路径: 本目录 index.html、dataset-audit-summary.json；本机 dataset/external 与 dataset/processed/facade_pairs_v001
下一步: 参考 Mesh 进一步质量审核；真实/仿真分别进行重建回归；补近重复、坐标和自交检查。

真实与仿真严格分开。71/228 是闭合预筛池内进一步审核的结果，不是全库通过率。
本阶段完成数据准备与 QA，没有训练新模型或证明重建精度提升。
