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
| 完整真实质量集 | dataset/processed/point2building_hq_v001 | 363 对，作者标签 train 345 / test 18；项目训练 312 / 封存测试 51；当前不运行完整集算法实验 |
| 完整本地仿真质量集 | dataset/processed/polygnn_mini_hq_v001/pairs | 已下载 mini 200 对中的全部 199 合格对；作者 train 100 / test 99，项目训练 120 / 测试 79 |
| 当前统一集合入口 | dataset/processed/complete_pairs_v001 | 合计 562 对，分真实/仿真来源；项目训练 432 / 封存测试 130；78 入门样例是其子集 |
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
6. 原作者 train/test 标签与文件布局保留；额外项目分组明确区分命名、用途、重叠风险，不混称作者标准测试或跨城市泛化。

大体积原始包、解压数据、转换后 XYZ 和 Mesh 只存 `dataset/`；Git 保存下载程序、审计程序、数据清单摘要和报告。空间不足时先报告，不删除旧数据。

## 完整质量集与使用阶段（当前）

- 用户明确要求：先在固定 78 对入门样例上迭代稳定，再去完整集测试。数据审核可以先做，完整集重建/模型评分本次没有运行。
- 全库严格拓扑预筛后的 1,087 对已全部执行原门槛的立面和配对审核，363 对通过；新增 Blender 独立检查全部通过（非相邻三角形 BVH、拓扑、正体积）。这仍不等于全面自交证明或人工语义核验。
- `dataset/external/point2building/audits/facade-complete-v003/`：完整闭合池审计、全目录和 Blender 复核；拓扑未通过的 27,328 对原始数据仍保留，没有删除或修补 GT。
- `dataset/processed/point2building_hq_v001/pairs/`：全部 363 对原坐标 XYZ、Mesh、派生线框和来源，作者目录不变。56,832 个原始解压文件重新核对大小与 SHA256 全部一致。
- `manifests/author_trainset.json` / `author_testset.json`：作者质量子集 345 / 18，仅作清单。其中 18 对作者 test 全在入门集，因此不能继续宣称是未见测试。
- `manifests/project_train.json`：312 对，其中 38 对真实入门样例、274 对暂缓；`project_test.json`：51 对封存，与入门真实组无 ID 重叠。所有测试均来自作者 train。
- 项目划分：源坐标中心距离 ≤200 单位连接空间组，精确哈希/顶点对距离近似再合并；154 组中固定哈希选取 25 个无入门样例的组为测试。最近训练/测试中心距 205.8676 源单位；CRS 未核准，不直接称米。近重复检测不穷尽。
- `manifests/starter78_development.json`：当前算法批处理入口，指向原 78 对，真实/仿真需分层报告。项目全训练和测试使用暂缓/封存角色与 stage_locked 双门禁。
- 证据：`reports/2026-09-21-point2building-complete/summary.json`、`split-inventory.json`、`integrity-verification.json`。详细使用门槛：`../protocols/dataset-stages.md`。
- 正式 SOTA 对比若用作者预训练 Point2Building 权重，51 对项目测试可能已在其训练中。须按项目训练划分重训，或用独立作者标准评测协议，不能把现成权重结果解释为公平未见泛化。

## 补齐仿真数据后的统一集合（最新）

用户补充完整集必须同时包含 Zurich 真实采集与合格仿真数据，并明确回复本轮先纳入已下载 mini 的全部合格数据。PolyGNN Munich 完整发布库不在本轮范围；不能把 mini 称为完整发布库。

- `complete_pairs_v001/manifest.json` 统一登记全部 562 对，直接指向各来源文件，避免重复复制。`summary.json` 记录来源、哈希、数量与阶段。
- 仿真 199/200 沿用原筛选门槛，全部通过新增 Blender 独立 QA；402 个原始解压文件重验大小/SHA256，导出 XYZ/OBJ 重读通过。1 个立面证据不足的原始配对保留。
- 仿真原作者划分 100/99 保留。作者 test 中已有 20 对进入 78 入门集，项目用途转为开发/训练；剩下 79 对封存。归一化形状相似度和精确哈希未发现跨划分重复，缺源坐标故不宣称空间隔离。
- 项目全训练 432 = 真实 312 + 仿真 120；封存测试 130 = 真实 51 + 仿真 79。训练包含全部入门 78，对测试重叠 0。
- 统一入口 `complete_pairs_v001/manifests/starter78_development.json` 与上一版 starter 清单哈希相同。`real_zurich_*`、`synthetic_mini_*` 提供来源分组，`all_*` 用于编排；六份完整运行清单均被门禁阻止提前执行。
- 真实和仿真不是相同坐标单位，最终按来源分别汇报准确度/失败率/成本，不把距离直接混合平均。
- 证据：`reports/2026-09-21-real-synthetic-collection/`；前阶段真实组与全部历史数据保留。

## 统一预处理 v001

- 论文方法：`docs/DATASET_METHODS_V001.md`；固定机器协议：`config/data_protocol_v001.json`。包括GT参与筛选偏差、每步分母、阈值、反例和作者划分重叠。
- 新完整分析数据：`../dataset/processed/standardized_pairs_v001/`，562对；`verification.json`记录全部往返通过。输入定义平移/尺度，XYZ顺序和数量保留，不加地面点，不使用GT确定变换；分析包围盒对角线30，不是米。
- 当前实验入口 `manifests/starter78.json`；`all_train.json`、`all_test.json`继续锁定。原始/前期导出不覆盖。
- 长期命令：`export_standard_dataset.py`（新目录导出）、`run_starter78_pilot.py setup/run`（固定开发划分/超时运行）；Frozen release 的 `source/reproduce.py`使用各自冻结评测器。
- 实验后交付271个成功模型均源坐标OBJ重读核验；失败23次保留在294次尝试中。数据562对往返QA不等于算法271个成功输出质量通过。
