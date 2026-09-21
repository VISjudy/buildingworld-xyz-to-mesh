# Visualization contract
Route: OpenAI web data visualization → reports / statistical comparison. Standard explanatory report, same established visual style.
Layer 1: method catalog and evidence matrix, semantic HTML tables/details; goal identify exactly what changed. Local specialist pass.
Layer 2: source-stratified paired CD dot plot, Matplotlib SVG+PNG, zero line and mean direct label; no invented confidence interval. Local statistical pass.
Layer 3: seven-view Blender comparisons, same per-building camera/material across versions, source hashes checked. Dedicated visual review.
Layer 4: height audit, tabular precise values + linked full CSV, distinguish coordinate and relative height. Independently audited by height_audit agent.
State: URL-backed mode/view/query with safe defaults, browser history restore. Reviews localStorage only, explicit JSON export, not automatic training evidence.
Mobile: horizontally scrollable comparison strip and tables; no document overflow; labels, alt text, native controls >=44px. No hover-only facts.
Fallback: all CSV/JSON/OBJ assets independent of JavaScript; initial comparison images in HTML. No network dependencies or animation.
QA: render/evaluation hash parity, source coordinate reimport, common evaluator/feedback/knowledge checks, desktop/mobile browser, view switching, URL restore and feedback export.
