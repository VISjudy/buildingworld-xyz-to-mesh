# 第二批 20 栋训练点云：21–40

版本 0.5.1；20 个新样例全部导出 OBJ，4 栋通过当前全部观测代理门槛（26, 30, 33, 35）。其他候选仍需修复，不能视作合格闭合建筑。

网页：`http://127.0.0.1:8765`。上传 XYZ / TXT，生成 OBJ，可切换点云、网格和叠加，查看排除点与检查报告。停止后运行 `webapp/start.ps1` 启动。

本目录 `index.html` 是静态六视图检查册；`buildingworld_train20.blend` 为 Blender 总览，场景菜单 `Inspect_21...Inspect_40` 可逐栋检查。陈列进行了等比缩放与平移，OBJ 始终保留源坐标。验证使用全部原始点。

## 你圈出的两栋是否为噪声

存在噪声的可能，但保守孤立点规则只排除了 1321 的 1/4032 点、144 的 3/4267 点；这不足以证明层叠屋面由孤立噪声造成，也不能排除面内噪声或系统性偏差。两栋的屋面分区与接缝仍有缺陷，新版 P95 甚至变差，因此不能宣称该问题已修复。不要用强滤波抹掉真实凹角、屋脊和小构件。

| 文件 | 排除点数 | 原 P95 | 新 P95 | 原 / 新面数 |
|---|---:|---:|---:|---:|
| 1321 | 1/4032 | 0.1288 | 0.2455 | 682 / 540 |
| 144 | 3/4267 | 0.5761 | 0.6656 | 1212 / 390 |
| 1048 | 14/8295 | 0.1793 | 0.0785 | 8 / 14 |

P95 是全部原始点到网格的距离，单位为输入坐标单位。没有真值，未计算 CD、ECD 或 FINAL SCORE。

## 本批结果

| 编号 | 训练 ID | 点数 | 排除点 | P95 | 未通过项 |
|---|---|---:|---:|---:|---|
| 21 | 3316 | 216 | 0 | 0.1084 | outline |
| 22 | 1296 | 1230 | 2 | 0.0936 | topology |
| 23 | 2486 | 1694 | 0 | 0.2689 | all_points, topology |
| 24 | 2959 | 2060 | 40 | 0.1738 | all_points, outline |
| 25 | 1647 | 2592 | 0 | 2.2585 | all_points, each_roof_patch, each_observed_facade, topology |
| 26 | 1339 | 3131 | 7 | 0.0614 | 无（仅代理验收） |
| 27 | 2326 | 3585 | 4 | 0.2005 | all_points |
| 28 | 2289 | 4227 | 6 | 0.1391 | each_observed_facade |
| 29 | 1161 | 5197 | 0 | 0.0907 | topology |
| 30 | 763 | 5647 | 0 | 0.0773 | 无（仅代理验收） |
| 31 | 3465 | 6087 | 18 | 1.1866 | all_points, each_roof_patch |
| 32 | 1475 | 7096 | 12 | 0.1940 | all_points, each_observed_facade, topology |
| 33 | 2043 | 7172 | 0 | 0.0747 | 无（仅代理验收） |
| 34 | 1645 | 8575 | 0 | 0.6780 | all_points, each_roof_patch, each_observed_facade, outline, topology |
| 35 | 3178 | 9074 | 0 | 0.0015 | 无（仅代理验收） |
| 36 | 1983 | 10294 | 0 | 0.0840 | each_roof_patch, each_observed_facade, topology, resolved_partition_adjacency |
| 37 | 1358 | 12670 | 21 | 1.0022 | all_points, each_observed_facade, topology |
| 38 | 1817 | 15752 | 0 | 0.3741 | all_points, each_observed_facade, topology |
| 39 | 229 | 32735 | 4 | 2.3438 | all_points, each_roof_patch, each_observed_facade, outline, topology |
| 40 | 321 | 41364 | 16 | 0.7152 | all_points, each_observed_facade, outline, topology |

36 / 1983 的屋面邻接存在歧义。该样例保留已拟合面，跳过无法可靠确定的连接墙，记录 unresolved_partition_edges，并强制邻接验收失败；这是可检查的候选输出，不是自动修复成功。

网页上传、生成、结果预览已通过浏览器实际操作；浏览器下载按钮测试被自动审批超时拦截，未标记验证成功。20 个本地 OBJ 已重新解析并核对坐标与面索引。
