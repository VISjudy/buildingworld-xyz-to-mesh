# 带立面点云与完整参考 Mesh 的数据获取

日期：2026-09-21。原始数据与提取文件保存在仓库外 `../dataset/external/`，不推送 Git。

## 实际下载

| 数据 | 一手来源 | 本包配对数 | 扫描与参考 |
|---|---|---:|---|
| Point2Building | [作者仓库](https://github.com/prs-eth/point2building) / [论文](https://doi.org/10.1016/j.isprsjprs.2024.07.012) | Zurich 28,415 | 真实机载 LiDAR，作者处理的市政 LoD2 参考 Mesh |
| PolyGNN mini | [作者仓库](https://github.com/chenzhaiyu/polygnn) / [数据说明](https://zenodo.org/records/14254264) | Munich 200 | pyhelios 仿真机载点云，巴伐利亚 LoD2 Mesh |

Point2Building 原作者划分 train 25,724 / test 2,691；PolyGNN mini 为 100 / 100。论文提到的其他城市不在本次 Point2Building 包内。BuildingWorld 完整库仍需申请访问。

保留公开作者包及下载字节数/SHA256；仅安全解压指定数据扩展名，不执行 Shell，不加载 Torch/CC pickle。完整原包中的模型权重仍在归档里，未启动训练。

## 可直接使用

`../dataset/processed/facade_pairs_v001/manifest.json`：38 对真实 ALS（train 20 / test 18）和 40 对仿真 ALS（20 / 20）。每栋包含 points.xyz、gt.obj、派生 wireframe.obj、provenance.json。

真实 XYZ/OBJ 按作者 scale/center 共同还原源坐标，并验证重读误差。仿真 mini 保留作者归一化坐标；缺少 CRS 还原文件，不能直接把距离标成米。没有改造参考几何，也没有补出人工立面点。

该入门集合按固定质量筛选产生，是开发与审核样例；原作者完整测试集仍保留。不可把入门样例的效果当无偏全数据测试。

## 审计结论与限制

Point2Building 的原参考 Mesh 包含墙面和底面，但很多面片连接不闭合：全 28,415 Mesh 中 1,087 通过当前严格三角面拓扑检查。随机性由固定哈希顺序提供；初次 120 对有 93 对立面支持、2 对满足闭合联合筛选。另在闭合池中审计 228 对，71 对满足联合条件；分母不同，不能直接比较比例。

PolyGNN mini 200 对全部审计，199 对满足联合条件。质量门槛、逐栋哈希、失败和样例渲染见 [可视化审计报告](../reports/2026-09-21-dataset-audit/index.html)。该检查尚不含完整自交测试或逐点人工语义标注，不能保证每面墙均有回波，也不能宣称所有下载模型完美闭合。

主墙面要求法向近水平、垂向延伸到底部附近；支持点要求近参考表面且处在墙面中段。至少 10 个支持点、占输入 0.5%、跨建筑高度 15%；点面容差使用对角线比例。屋顶边缘不会仅因碰到墙边就计作立面支持。合成立面/屋顶单元测试覆盖这个区别。

## 避免数据泄漏

[作者 data_modules.py](https://github.com/prs-eth/point2building/blob/main/src/modules/data_modules.py) 的 PVDataset.__getitem__ 在读取 Mesh/XYZ 后，用 Mesh 高程生成底面点并加入输入（检索到的版本约第 53–56 行）。本次审计不执行该加载器，不添加这些点。后续基线复现应分别报告“作者预处理”和“仅允许 XYZ”条件。

Point2Building 论文还说明用参考轮廓提取独栋点云，因此实例裁切带有参考信息。这个数据适合已分割单栋重建，不能拿来证明无需参考的整城检测/分割能力。

原作者 GT 是测绘/市政抽象模型，存在年代、测量、简化和拓扑误差；不等于完美物理实况。不要通过按当前模型预测修补 GT 来制造改进。

## 复现入口

- `download_research_data.py`：公开 HTTPS 下载、大小限制、独占写入、SHA256。
- `analyze_paired_building_data.py extract`：防路径逃逸的选择性提取。
- `analyze_paired_building_data.py screen-topology`：全库参考 Mesh 闭合筛选。
- `analyze_paired_building_data.py audit`：固定参数立面与配对审核，真实/仿真分开。
- `export_facade_pairs.py`：保留作者 split、坐标还原、OBJ/XYZ 重读与来源记录。
- `export_data_audit_report.py`：使用 OpenAI data visualization 技能工作流生成离线报告。

全部脚本在 `scripts/buildingworld/`。原始数据遵守作者及原地理数据来源条款；下载公开资源不意味着本项目可以重新授予数据许可。

## 后续全量整理（2026-09-21，当前阶段）

在保持上述初始报告与入门样例不变的情况下，审核范围扩展到全部 1,087 个闭合候选，联合门槛通过 363 对；独立 Blender 检查亦全部通过。完整质量集保存在 `../dataset/processed/point2building_hq_v001`，原数据 28,415 对全部保留。

作者标签仍是 train 345 / test 18。现有 18 对作者 test 全已在入门 78 中，不能再当未见测试；新增项目划分为训练 312 / 封存测试 51。按空间相邻与几何相似组划分，测试 51 来自作者 train，不能冒充作者标准基准。详见 [完整数据报告](../reports/2026-09-21-point2building-complete/index.html) 与 [阶段协议](../prompt/protocols/dataset-stages.md)。

当前算法仅用固定 78 对迭代，稳定并冻结后才开启完整集实验。新清单 `manifests/starter78_development.json` 指向原 78 对；项目全训练与测试清单都带阶段锁。数据 QA 不使用算法预测结果，不代表训练或重建成绩。

新增长期入口：

- `analyze_paired_building_data.py audit --per-split 0 --topology-screen ...`：审核预筛后的全部配对。
- `check_reference_meshes_blender.py --audit ... --output ...`：Blender 后台独立参考 Mesh 检查，无几何修改。局限：只筛非相邻三角形相交候选，不能声称全面无自交。
- `export_point2building_complete.py --audit-file ... --topology-file ... --blender-file ... --starter-file ... --output ...`：全量导出、近邻/形状分组、作者与项目清单、逐个未通过原因、阶段锁。输出目录必须不存在。
- `export_complete_data_report.py --dataset ... --verification ... --output ...`：依据核验结果创建新版本离线 HTML 报告。

空间阈值为 200 源坐标单位；近似形状用排序的顶点对距离（容差 0.05 源单位、相对容差 0.005），哈希固定选择 20% 无入门样例的连通组作为测试。不同城市、阈值、网格版本变化须建立新版本，不能事后根据测试成绩调整划分。

## 真实 + 仿真统一入库（同日补充）

用户明确本轮仅纳入已下载 PolyGNN mini 的全部合格数据。完整本地集合 `../dataset/processed/complete_pairs_v001/` 共 562 对：Zurich 真实 363、mini 仿真 199，项目训练 432 / 封存测试 130。全部 78 入门样例包含在训练中，阶段安排不变。

仿真文件单独保存在 `../dataset/processed/polygnn_mini_hq_v001/pairs/`。199 对均经过 Blender 补充复核，402 个原始文件经哈希复核。作者 train 100 / test 99 标签保留；20 个作者 test 已入门，故项目训练 120 / 测试 79。归一化形状对距离筛查使用绝对容差 1e-6、相对容差 1e-4，并核对点云/Mesh 精确哈希；不宣称 mini 空间隔离。

新增入口：`export_paired_collection.py` 接收真实组件、仿真组件、原始提取目录、审核、Blender 复核与 starter 清单，完整核验后生成独立统一索引；`export_paired_collection_report.py` 生成新阶段报告并实际验证六份完整运行清单会被阶段门禁拒绝。仿真文件仍由 `export_facade_pairs.py --max-per-split 0` 全部导出。

报告：[真实与仿真统一集合](../reports/2026-09-21-real-synthetic-collection/index.html)。[PolyGNN 作者说明](https://github.com/chenzhaiyu/polygnn)将 200 对 mini 与 [Munich 完整发布库](https://zenodo.org/records/14254264) 区分；本轮未下载后者。“全部”仅指用户确认的本地包覆盖范围。
