# 环境与复现

使用标准 Python 环境安装 `webapp/requirements.txt`，它包含命令行依赖与验证所需 Matplotlib。历史本机实际依赖：NumPy 2.5.3、SciPy 1.18.1、Shapely 2.1.2、Matplotlib 3.11.2、mapbox-earcut 2.1.0。这些是环境记录，不代表所有平台都有同名版本；安装失败时使用 requirements 的兼容范围，并记录实际版本和回归结果。

本地缓存位置 `work/runtime/deps`，不提交仓库。重建不依赖 Blender；历史场景由 Blender 5.2 生成，接口端口 9876。浏览器使用本地 WebGL，无 CDN 和 Node 构建步骤。

推荐运行顺序：安装依赖 → 单栋 CLI → 网页 → 固定批次与人工审查。`scripts/buildingworld/` 是研究辅助脚本，一些 finalizer 为特定历史引擎 SHA 设计；不要为通过检查随意删除 SHA 校验。`build_standalone.py` 是历史代码生成器，可能覆盖当前入口，不应作为安装步骤运行。
