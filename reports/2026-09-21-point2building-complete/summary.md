slug: point2building-complete-curation
日期: 2026-09-21
状态: 已定案
一句结论: 28,415 原始配对全部保留；完整闭合池审核并导出 363 对，项目训练 312 / 封存测试 51，当前仅允许在固定 78 对迭代。
产物路径: ../dataset/processed/point2building_hq_v001；reports/2026-09-21-point2building-complete；../dataset/external/point2building/audits/facade-complete-v003
下一步: 在固定 78 对建立同输入基准，完成算法迭代稳定性验收与冻结后再进入完整集测试。

本次无重建算法执行。候选数 1,087、联合筛选 363；363 均通过独立 Blender 拓扑/正体积/非相邻 BVH 候选检查。56,832 原始文件大小与 SHA256 复核通过；20 项相关测试通过。

作者质量子集标签 345 train / 18 test，18 test 已全在入门组。项目封存 51 源于作者 train；不能称作者标准未见测试或直接用于其预训练权重的公平泛化声明。空间+形状连通组 154，选 25 组为测试。完整训练/测试均被阶段门禁拒绝执行；未改写任何历史输出。
