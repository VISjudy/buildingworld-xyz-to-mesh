# Visualization mini-brief

OpenAI data visualization：reports-pdfs-and-slide-automation + strategy/critique + statistical honesty，本地复核。
任务：比较两种来源的合格、训练、测试数量，明确使用阶段；媒介：独立离线 HTML。
唯一核心视觉：语义表格，行=真实/仿真，列=合格/训练/测试；合计只加计数，禁止跨单位混合误差。每个数据点都有文字，不靠颜色编码。
前后段落说明 78 对为子集、作者与项目 test 的差异、mini 范围。原生 details 折叠背景；无 JS、网络依赖或需持久化状态。
DOM 渲染，手机保持阅读顺序，打印可用；表格行列标题与键盘 details 可访问。验收：桌面/手机无水平溢出、截图人工检查、计数守恒、门禁生效、无远程加载。
