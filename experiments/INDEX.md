# 正式实验登记

大体积中间产物沿用现有 `work/experiments/`，不迁移历史目录。

| slug | 状态 | 一句结论 | 产物 |
|---|---|---|---|
| lod2-rsi-v001 | 第一候选已定案；研究继续 | 凹轮廓有局部收益但出现退化/失败，未采用 | work/experiments/2026-09-21/lod2-rsi-v001；reports/2026-09-21-stage01 |
| facade-data-acquisition | 已定案：下载与阶段审核完成 | 取得真实/仿真配对数据并导出 78 对样例；不等同全库有效实体或训练成绩 | work/experiments/2026-09-21/facade-data-acquisition；reports/2026-09-21-dataset-audit；../dataset/external |
| point2building-complete-curation | 已定案：完整筛选与封存完成 | 全量闭合池审核得到 363 对；312 项目训练 / 51 封存；当前仍只开发 78 对 | work/experiments/2026-09-21/point2building-complete-curation；reports/2026-09-21-point2building-complete；../dataset/processed/point2building_hq_v001 |
| real-synthetic-collection | 已定案：补齐 mini 全量合格对 | 真实 363 + 仿真 199 = 562 对，432 训练 / 130 封存，仍只开放 78 入门 | work/experiments/2026-09-21/real-synthetic-collection；reports/2026-09-21-real-synthetic-collection；../dataset/processed/complete_pairs_v001 |
| starter78-feedback-pilot | 首轮已定案；机制尚未证明 | F0 改善共同成功几何；F3 恢复6对；两种策略迁移均26/30，无演化收益 | experiments/2026-09-21/starter78-feedback-pilot/summary.md；work/experiments/2026-09-21/starter78-feedback-pilot；reports/2026-09-21-starter78-feedback-pilot |

基准复现、派生数据与第一候选共享本实验；跨日继续使用原目录，不复制整套实验。

| feedback-components-v002 | 单候选探索已定案 | 综合反馈78/78当前拓扑通过；图像候选改善但因果未证实，高度检查零收益；v0.5.1纳入同样本比较 | experiments/2026-09-21/feedback-components-v002/summary.md；reports/2026-09-21-feedback-components-v002 |

| initial-v010-test4000 | 本地生成与打包已定案，未上传 | 3966网格＋34失败空OBJ，4000同名文件ZIP校验通过 | experiments/2026-09-22/initial-v010-test4000/summary.md；reports/2026-09-22-initial-v010-test4000 |
