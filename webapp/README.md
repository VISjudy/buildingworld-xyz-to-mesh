# 本地点云 → OBJ 网页

运行 `webapp/start.ps1`，浏览器打开 http://127.0.0.1:8765 。服务只绑定本机；无账号、无云端上传、不依赖远程 JavaScript 库。

1. 选择或拖入单栋 `.xyz` / `.txt` 点云，每行三个有限数值 X Y Z。支持 20–300000 点、24 MB 以内。
2. 保守过滤只标记非常孤立的点，可关闭。底高可留空或填写可信 Z 值；留空采用最低回波分位数假设。
3. 点击“生成建筑网格”，等待本地计算与全原始点验证。
4. 切换点云、网格、叠加；拖动旋转、滚轮缩放、Shift 拖动平移。结果面板显示失败项，不将导出成功等同于重建合格。
5. 用“下载 OBJ”保存模型，用“检查报告”保存参数、过滤数量、拓扑及观测代理指标。

最多顺序排队 6 个任务，每个任务 10 分钟超时。任务数据保存在 `work/runtime/web_jobs/<任务ID>`，包括 `input.xyz`、`model.obj`、`model.json`、`validation.json`、`result.json`。服务重启后可以读取已完成任务。

网页预览最多显示 22000 个原始点；算法与验证使用完整输入。显示变换不写入 OBJ。前端是原生 HTML/CSS/JavaScript + WebGL，后端使用 Python 标准库 HTTP 服务与子进程，调用根目录的 `pointcloud_to_mesh.py`。

也可前台启动：

```powershell
python webapp/server.py --port 8765
```

此电脑的启动脚本优先使用已安装的可用 Python。换电脑执行 `python -m pip install -r webapp/requirements.txt`，同时安装重建依赖及验证模块使用的 Matplotlib。

第二批固定样例是 21–40，点击样例选择框可以查看。静态检查册位于 `releases/v0.5.1-batch02/index.html`。

测试范围：浏览器已实测上传 `data/inputs/xyz/1667.xyz`、生成任务、预览结果和报告入口；下载按钮的浏览器验证被自动审批超时拦截，未确认下载动作成功。原型尚有复杂屋面分区、开放边、非流形连接等问题，见算法说明及各模型检查报告。
