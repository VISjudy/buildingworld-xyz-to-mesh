# 本地 Harness 操作

本程序是已运行的研究基础设施，不是已完成递归自我改进实验。重建与评测无需大模型；`evolve` 当前接收明确给定的候选脚本，并独立复测。固定模型自动提议、外层策略优化、多种子试验尚待接入。所有输出目录必须不存在；历史目录禁止覆盖。

```powershell
python -m pip install -r requirements-harness.txt
python scripts/buildingworld/run_research_setup.py --points ../dataset/testDataset/LiDAR_xyz --output work/experiments/<run>/setup
python -m harness reconstruct --source work/experiments/<run>/setup/baseline_original.py --manifest work/experiments/<run>/setup/development20.json --output work/experiments/<run>/baseline
python -m harness evaluate --mesh model.obj --points input.xyz --output work/evaluation.json
python -m harness derive --dataset "../dataset/demo_dataset/demo dataset" --output ../dataset/processed/wireframe_mesh_<new-version>
python -m harness make-feedback --report evaluation.json --knowledge config/knowledge/rules.json --condition F3 --output work/feedback/<new-id>
python -m harness evolve --parent work/experiments/<run>/baseline --proposal candidate.py --manifest work/experiments/<run>/setup/development20.json --output work/experiments/<run>/candidate --knowledge config/knowledge/rules.json --hypothesis "Bounded change and expected benefit" --rule-ids K01 K06
python -m harness freeze --run work/experiments/<run>/candidate --version <new-version> --knowledge config/knowledge/rules.json --baseline work/experiments/<run>/baseline --previous work/experiments/<run>/baseline
python -m harness verify releases/<new-version>
python -m pytest -q
```

输入 manifest 中指定 `role`、每栋 `id/points/sha256/columns/localize`。多列只用显式 XYZ；源坐标通过适配器恢复，OBJ 重读校验。原始脚本路径参数之外不作算法修改。

`evaluate --gt-mesh` 需要真实有面的 OBJ；只含 v/l 的线框被拒绝作 Mesh 真值。`--gt-wireframe` 单独计算本地结构距离，使用前必须核准屋顶/完整建筑域。当前法向为单尺度局部 PCA 代理；自交未在主评价器完成，因此不宣称完整有效实体。几何筛选脚本另用 Blender 检查非相邻三角形 BVH 重叠。

Blender 后台入口：

```powershell
& 'D:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --factory-startup --python scripts/buildingworld/render_research.py -- --request request.json
& 'D:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --factory-startup --python scripts/buildingworld/check_derived_blender.py -- --dataset ../dataset/processed/<version> --output ../dataset/processed/<version>/blender_qa.json
```

渲染 request 包含新 `output`、`seven_views:true`、`samples:[{id,points,models:{baseline,previous,current}}]`。缺失 Mesh 保留失败状态，报告生成器显示空位。GUI 端口 9876 已记录；本轮后台进程不修改用户打开的 Blender 场景。

派生训练目录保存 `wireframe_surface.obj`、`completed_hypothesis.obj`、`provenance.json`。`provisional_training_manifest.json` 仅列当前几何筛选通过者；人工语义复核仍待完成，不是训练完成证明。

逐版本 source 内直接运行冻结的 `python -B -m harness.adapter --source algorithm.py --points <original.xyz> --output <new-dir>` 可重建单栋；原始输入 SHA 应先与 reports/input_manifest.json 核对。`-B` 避免在冻结目录写字节码。依赖锁由本次环境生成。正式快照使用 `-r2` 包装版本：第一轮本地包装发现了 Python 缓存，保留但不上传；r2 排除缓存，算法和模型未改变。

信任边界：当前本地受控候选是研究者审核代码，子进程不是恶意代码沙箱。自动执行模型生成代码前，需要操作系统级隔离、只读评测器与输入、网络/时间/资源限制；不能只凭提示词宣称防止评分篡改。
