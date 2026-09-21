# v0.1.2-pilot-f3-v001
Condition: F3. Parent: exact v0.1.0 plus fixed input-only preprocessing.
Status: frozen experimental candidate, not a stable final algorithm.
Source OBJ is model_source.obj; model.obj is canonical analysis geometry, not source units.
Failures and all attempted IDs are retained in reports/results.json.
Seven-view cross-arm comparison: ../../reports/2026-09-21-starter78-feedback-pilot/index.html
Sibling arms must not be interpreted as successive algorithm parents.
Reproduce with `python source/reproduce.py --output NEW_ABSOLUTE_DIRECTORY [--only BUILDING_ID]` and source/requirements-lock.txt. Inputs retain the local standardized paths and hashes in reports/inputs.json. Only input path rebasing is needed on another machine; preserve file bytes and hashes.
