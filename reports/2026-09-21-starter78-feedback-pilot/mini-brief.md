# Report design contract
Analytical job: source-stratified paired comparison and failure accounting.
Route: OpenAI web data visualization → reports + statistical visualization.
Reading path: measured finding → limits → data method → protocol → paired results → all buildings.
Renderer: static Matplotlib SVG/PNG; Blender seven-view evidence; HTML table and filter.
Budget: 108 cards, images lazy-loaded, no network dependencies, no animation.
State: phase/query URL parameters; invalid phase resets; browser back restores; no local storage.
Mobile: single column, horizontal table only, explicit labels, native 44px controls, no hover-only values.
Colors: navy context, source-independent labeled F0/F3 marks, amber caution; values remain visible without color.
Fallback: JSON/CSV and static assets readable without JavaScript; all records remain in source.
QA: verify evaluator/source/render hashes and coordinate roundtrip; desktop/mobile browser and filter checks.
