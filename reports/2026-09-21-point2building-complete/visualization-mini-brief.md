# OpenAI data visualization mini-brief

媒体：独立离线 HTML；任务：比较全库筛选覆盖、训练/封存数量和执行状态。
主路由：reports-pdfs-and-slide-automation；辅助：visualization-strategy-and-critique、statistical-and-uncertainty-visualization。本地独立复核，不委派。

| 层 | 任务与编码 | QA |
|---|---|---|
| 筛选表 | 从全库 28,415 到实际导出；每行直接标注总体/子集分母，不将阶段数相加 | 与 summary.json 一致；门槛筛选不叫算法成绩 |
| 划分条 | 唯一一幅 HTML/CSS 定宽比例条；312+51=363，训练青色、封存紫色，数值始终在旁边 | 长度与计数比一致；提供同值表格；不以颜色作为唯一标识 |
| 阶段状态 | 78 开发和完整集的集合关系；正文解释 38 真实重叠，不能相加 | 与清单/hash 一致；0 次完整集重建 |

renderer：浏览器 DOM；无外部依赖/脚本/网络/动画；只有原生 details 展开阈值。单页 1 个比例条，移动端同序阅读、表格换行；无持久化或 URL 状态需求。打印 CSS 与无 JS 页面都是静态后备。
验收：桌面/手机截图、无水平溢出、离线网络为零、键盘展开；人工核对可读性、分母、单位和测试来源限制。
