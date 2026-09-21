# 正式实验登记

大体积中间产物沿用现有 `work/experiments/`，不迁移历史目录。

| slug | 状态 | 一句结论 | 产物 |
|---|---|---|---|
| lod2-rsi-v001 | 第一候选已定案；研究继续 | 凹轮廓有局部收益但出现退化/失败，未采用 | work/experiments/2026-09-21/lod2-rsi-v001；reports/2026-09-21-stage01 |
| facade-data-acquisition | 已定案：下载与阶段审核完成 | 取得真实/仿真配对数据并导出 78 对样例；不等同全库有效实体或训练成绩 | work/experiments/2026-09-21/facade-data-acquisition；reports/2026-09-21-dataset-audit；../dataset/external |
| point2building-complete-curation | 已定案：完整筛选与封存完成 | 全量闭合池审核得到 363 对；312 项目训练 / 51 封存；当前仍只开发 78 对 | work/experiments/2026-09-21/point2building-complete-curation；reports/2026-09-21-point2building-complete；../dataset/processed/point2building_hq_v001 |
| real-synthetic-collection | 已定案：补齐 mini 全量合格对 | 真实 363 + 仿真 199 = 562 对，432 训练 / 130 封存，仍只开放 78 入门 | work/experiments/2026-09-21/real-synthetic-collection；reports/2026-09-21-real-synthetic-collection；../dataset/processed/complete_pairs_v001 |

基准复现、派生数据与第一候选共享本实验；跨日继续使用原目录，不复制整套实验。
