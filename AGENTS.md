# Working in this project

Read `PROJECT_MEMORY.md`, `README.md`, and `docs/BUILDING_RECONSTRUCTION_ALGORITHM.md` before algorithm changes.

- Preserve observed contours, small supported features and facade evidence. Do not relax validation to improve pass counts.
- Never report observation proxies as official CD/ECD/NC. Ground truth and the official evaluator are not available yet.
- Keep input data and intermediate jobs out of Git, including XYZ embedded in Blender scenes.
- Write experiments under `work/`; publish new versions under `releases/` without overwriting historical geometry.
- User instructions take precedence. This file does not require extra approval or delegate work.
