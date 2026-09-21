slug: real-synthetic-collection
日期: 2026-09-21
状态: 已定案
一句结论: 纳入 Zurich 363 对及已下载 mini 全部合格 199 对，统一 562 对；项目训练 432 / 封存测试 130，仍仅开放固定 78 对。
产物路径: ../dataset/processed/complete_pairs_v001；../dataset/processed/polygnn_mini_hq_v001；reports/2026-09-21-real-synthetic-collection
下一步: 只在 78 对上建立基准和迭代；稳定验收与冻结后再启用完整本地集合。

用户明确本轮不下载 Munich 完整发布库。mini 全量 200 中 199 通过既定质量门槛，全部通过 Blender 独立有限几何 QA；402 个原始文件哈希一致。仿真作者 test 中 20 已用于入门，项目 test 剔除这些样例，79 栋封存；没有源坐标，不能宣称空间隔离。

相关测试 21 项通过。六份完整运行清单实际触发门禁、未执行重建。旧真实集合与旧入门数据未改写。
