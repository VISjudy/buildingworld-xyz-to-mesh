# 数据注册表

更新：2026-09-21。下载完成、配对完成、立面观测、Mesh 完整性、可训练是不同状态。数据不进入 Git。

## 需求

主目标：真实机载 LiDAR 独栋点云，包含实际立面回波，配对有屋顶/墙面/底面的完整 LoD2 Mesh。允许另建仿真 ALS 辅助组，但不得混入真实测试。Mesh 来自作者/测绘数据源，不由当前待评算法反推充当独立真值。

## 当前来源

| 数据 | 本机位置（相对工作区 lidar2building） | 性质与状态 |
|---|---|---|
| BuildingWorld 比赛测试点云 | dataset/testDataset/LiDAR_xyz | 4000 XYZ；无配对 Mesh。已使用的 20 栋属于开发集 |
| 原 demo | dataset/demo_dataset/demo dataset | 用户确认只有屋顶；54 点云、53 线框、52 对；无真实立面/完整 Mesh GT |
| demo 派生 v001/v002 | dataset/processed/wireframe_mesh_v001、v002 | 保留历史转换。v002 44 候选、26 几何筛选通过，不构成完整立面训练真值 |
| Point2Building 作者资源 | dataset/external/point2building/raw/archives | 已完整下载 1,612,680,162 字节；已解压 Zurich 28,415 对（train 25,724 / test 2,691） |
| PolyGNN mini 作者资源 | dataset/external/polygnn_mini/raw/archives | 已完整下载 163,238,451 字节；已解压 200 对（train 100 / test 100），仿真 ALS |
| 可直接使用的配对样例 | dataset/processed/facade_pairs_v001 | 78 对：真实 train 20 / test 18，仿真 train 20 / test 20；原 split 保留，无人工补面/补点 |
| BuildingWorld 完整训练 | 未下载 | 官方 Hugging Face 需审核访问；不能绕过申请，也不将其列为当前本地数据 |

Point2Building 论文研究 Zurich/Berlin/Tallinn，但实际下载包只包含 Zurich 数据，不能宣称三城均已获取。PolyGNN mini 的点云由 pyhelios 仿真，Mesh 源于巴伐利亚 LoD2 数据。原数据许可遵守各来源，仓库不再分发数据。

## 下载与检查证据

- Point2Building SHA256：`3669db18b74b860608c43cc28d16effa5305836b2ea740b6e0a5f21295aff57a`。
- PolyGNN mini SHA256：`ce7715924118d76c4c9ecc324784c6d165886bd5bc109ebcb313a6fc46a73a86`。
- 以上为本地完整下载的哈希，不冒充作者发布校验和。压缩包已完整读取；解压清单记录逐文件哈希。
- Point2Building 全部 28,415 个 Mesh 严格拓扑预筛有 1,087 个闭合且朝向一致。初次 120 对审计有 93 对立面支持，但只有 2 对通过全部联合条件。
- 在闭合 Mesh 池内进一步审计 228 对（train 150 / test 78），71 对通过联合条件（train 53 / test 18）。这是预筛后的分层子集，不能解释为全库通过率。
- PolyGNN 全 200 对审计，199 对通过（train 100 / test 99）；一栋立面支持不足，保留失败记录。
- 审计采用主墙面法向、近面距离、排除屋檐/底边的垂向范围、点数/占比/高度跨度，不仅看 Mesh 外观。参数和所有结果见 `reports/2026-09-21-dataset-audit/`；仍未完成自交和逐点人工语义审核。
- Point2Building 按作者 `world = normalized * scale + center` 还原入门样例；XYZ/OBJ 重新读取验证。CRS 与高程基准未独立核准。PolyGNN mini 缺原始 CRS 变换，保留归一化坐标。
- 作者 Point2Building 训练加载器存在由 GT Mesh 高程添加人工底面点的预处理；本项目直接读取原始 XYZ，未采用。正式基线比较必须披露并分离这种处理。
- `raw/extracted-v001/` 保存完整配对数据；`audits/` 保存全目录、拓扑、立面和重复检查；完整压缩包含权重但未加载，未执行包内代码。

## 来源链接

- https://github.com/prs-eth/point2building
- https://doi.org/10.1016/j.isprsjprs.2024.07.012
- https://github.com/chenzhaiyu/polygnn
- https://zenodo.org/records/14254264
- https://huggingface.co/datasets/BuildingWorld/BuildingWorld

## 纠正 demo 的用途

2026-09-21 用户确认 demo 只有屋顶。此前派生 Mesh 的墙面、底面全部来自补全假设；局部最低屋顶点不能确定地面，拓扑闭合也不能验证建筑全高。26 个筛选通过仅指有限几何检查。

后续 demo 限于屋顶/结构线算法调试；不得进入完整建筑 Mesh 主评测，不应把推断墙面、底面作为可靠立面监督。旧文件不删，保留来源和撤回范围。此结论优先于旧阶段报告“训练候选”的宽泛表述。

## 入库准则

1. 保留作者压缩包和下载 SHA256，不执行包内代码或反序列化不可信 pickle。
2. 配对按内部建筑 ID +文件路径+坐标检查，不能只按同名猜测。
3. Mesh 独立检查实际墙面/底面、开放边、法向、体积；点云检查近墙面点数、占比、垂向跨度及覆盖，而不是只看最低 Z。
4. 记录坐标单位/尺度/局部变换；使用作者预处理或真值轮廓裁点的事实必须披露。
5. 完整性、噪声和时间差逐项记录；保留全部失败，筛选阈值固定并输出全清单。
6. 训练/验证/测试保持作者分组；额外筛选组为开发/审计，不擅自宣称独立泛化。

大体积原始包、解压数据、转换后 XYZ 和 Mesh 只存 `dataset/`；Git 保存下载程序、审计程序、数据清单摘要和报告。空间不足时先报告，不删除旧数据。
