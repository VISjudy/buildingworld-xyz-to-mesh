# Working in this project

Read `PROJECT_MEMORY.md`, `README.md`, and `docs/BUILDING_RECONSTRUCTION_ALGORITHM.md` before algorithm changes.

- Preserve observed contours, small supported features and facade evidence. Do not relax validation to improve pass counts.
- Never report observation proxies as official CD/ECD/NC. Ground truth and the official evaluator are not available yet.
- Keep input data and intermediate jobs out of Git, including XYZ embedded in Blender scenes.
- Write experiments under `work/`; publish new versions under `releases/` without overwriting historical geometry.
- User instructions take precedence. This file does not require extra approval or delegate work.

| Task | Keywords | Load |
|---|---|---|
| Research harness | RSI, Harness, 反馈, 实验, 冻结, 训练 | prompt/registers/research.md; docs/RSI_RESEARCH_PLAN.md |
| Literature | 文献, 知识库, City3D, BWFormer | docs/LITERATURE_REVIEW_RSI.md |
