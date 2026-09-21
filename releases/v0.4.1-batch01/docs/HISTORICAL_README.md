# 20 栋训练样例检查包

算法：0.4.1。固定抽样 20 栋，导出 20 个 OBJ；1 栋通过当前全部观测代理门槛，7 栋通过拓扑门槛。其余均保留供人工检查，不能作为合格建筑模型使用。

打开 `index.html` 逐栋查看六视图与下载链接，或在 Blender 打开 `buildingworld_train20.blend`。总览左为点云、右为网格；场景菜单 `Inspect_01...Inspect_20` 提供单栋叠加，关闭 `02_ALIGNED_XYZ_TOGGLE` 只看网格。`03_FULL_XYZ_VERTICES_TOGGLE` 保存全部输入顶点；总览与叠加显示最多 3500 个真实点以便浏览。

OBJ 保持源 XYZ 坐标。Blender 单栋采用同一平移/等比缩放显示点云和网格，缩放仅用于陈列，不能跨栋比较显示尺寸。验证使用全部输入点，不使用显示抽样。

没有真值网格和官方评测脚本，CD、ECD、NC、V_Ratio、F_Ratio、FINAL SCORE 均未计算。P95、覆盖率与轮廓 IoU 是观测一致性代理。规则阈值没有为本批次放宽。

## 检查结果

| 编号 | 训练 ID | 点数 | 点面 P95 | 0.15 内比例 | 未通过门槛 |
|---|---|---:|---:|---:|---|
| 01 | 1667 | 488 | 0.0599 | 99.8% | outline |
| 02 | 2811 | 796 | 0.1710 | 93.3% | all_points, outline |
| 03 | 2879 | 1938 | 0.0863 | 98.2% | outline |
| 04 | 1936 | 1991 | 0.0858 | 97.7% | topology |
| 05 | 2623 | 2807 | 0.2348 | 87.9% | all_points, each_observed_facade, topology |
| 06 | 944 | 3110 | 0.1083 | 96.6% | each_roof_patch, topology |
| 07 | 1321 | 4032 | 0.1288 | 95.8% | outline, topology |
| 08 | 144 | 4267 | 0.5761 | 83.1% | all_points, each_roof_patch, each_observed_facade, topology |
| 09 | 2078 | 4802 | 0.1866 | 94.5% | all_points, each_observed_facade |
| 10 | 480 | 5847 | 0.3658 | 86.1% | all_points, outline, topology |
| 11 | 945 | 6439 | 0.5064 | 89.7% | all_points, each_observed_facade, topology |
| 12 | 1102 | 6944 | 0.1253 | 97.2% | 通过代理门槛 |
| 13 | 1751 | 7302 | 0.3038 | 91.4% | all_points, topology |
| 14 | 1048 | 8295 | 0.1793 | 89.6% | all_points, each_roof_patch |
| 15 | 46 | 9012 | 0.2069 | 93.8% | all_points, each_roof_patch, topology |
| 16 | 1985 | 9996 | 0.4580 | 88.2% | all_points, each_observed_facade, outline |
| 17 | 1710 | 11982 | 1.3912 | 65.1% | all_points, each_roof_patch, each_observed_facade, outline, topology |
| 18 | 2754 | 17737 | 0.1201 | 96.6% | each_roof_patch, each_observed_facade, topology |
| 19 | 1725 | 29466 | 1.0980 | 71.8% | all_points, each_roof_patch, each_observed_facade, outline, topology |
| 20 | 1572 | 57978 | 0.0926 | 96.7% | each_observed_facade, topology |

## 原 3 栋回归检查

旧 V2 产物保留未改。新独立脚本的回归结果如下；拓扑失败需要继续修复，不能用几何误差较小掩盖：

- 10：全点 P95 0.0886；未通过：无；开放边 0。
- 1000：全点 P95 0.0505；未通过：无；开放边 0。
- 2000：全点 P95 0.0750；未通过：topology；开放边 4。

下一轮优先检查：屋面交汇的共形拓扑、复杂/低坡屋面分区、高低附楼的接缝位置、轮廓规整对斜边与小凹角的影响。

反馈请写“编号 + 部位 + 问题”，例如“14，主屋脊，低坡屋顶被压平”。可填 `feedback.csv`，也可在 `index.html` 填写后导出 JSON。
