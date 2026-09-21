# Working in this project

Start new conversations with `memory.md`, then load only the matching L2 entries. Before algorithm changes also read `README.md` and `docs/BUILDING_RECONSTRUCTION_ALGORITHM.md`.

- Preserve observed contours, small supported features and facade evidence. Do not relax validation to improve pass counts.
- Never report observation proxies as official CD/ECD/NC. Author reference meshes are available in external datasets; BuildingWorld challenge GT and the official evaluator remain unavailable. Check the dataset register for quality and coordinate scope.
- Keep input data and intermediate jobs out of Git, including XYZ embedded in Blender scenes.
- Write experiments under `work/`; publish new versions under `releases/` without overwriting historical geometry.
- User instructions take precedence. This file does not require extra approval or delegate work.

| Task | Keywords | Load |
|---|---|---|
| Research harness | RSI, Harness, 反馈, 实验, 冻结, 训练 | prompt/registers/research.md; docs/RSI_RESEARCH_PLAN.md |
| Literature | 文献, 知识库, City3D, BWFormer | docs/LITERATURE_REVIEW_RSI.md |
| Data audit | 数据集, 立面, 屋顶, GT, Point2Building, PolyGNN | prompt/registers/datasets.md |
| Dataset stages | 78, 完整集, 封存, 稳定, 测试集 | prompt/protocols/dataset-stages.md |
| Experience | 经验, 成功, 失败, 回归 | prompt/knowledge/experience-index.md |
| Memory updates | memory, 记忆, 记录, 接续 | prompt/protocols/memory-management.md |

After milestones update the relevant register and append evidence-backed experience records; run `python scripts/buildingworld/check_project_memory.py`. Preserve old runs and corrections. `PROJECT_MEMORY.md` is a compatibility pointer, not a second current-state store.
