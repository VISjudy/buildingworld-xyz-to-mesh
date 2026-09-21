"""Evidence packets for the F0-F5 ablation; no inferred score is invented."""
from pathlib import Path
import copy
from .io import read_json, write_json, sha256


def make_feedback(report, knowledge, output, condition="F3", images=(), include_knowledge=True):
    if condition not in [f"F{i}" for i in range(6)]:
        raise ValueError("Unknown feedback condition")
    out=Path(output);out.mkdir(parents=True,exist_ok=False)
    r=read_json(report);k=read_json(knowledge)
    requested={kid for issue in r["issues"] for kid in issue.get("rule_ids",[])}
    rules=[x for x in k["rules"] if x["id"] in requested] if include_knowledge else []
    obs=r.get("observed")
    metrics={"p95": obs["all_points_to_surface"]["p95"] if obs else None,
             "coverage":obs["all_points_to_surface"]["coverage"] if obs else None,
             "open_edges":len(r["topology"]["open_edges"]),
             "nonmanifold_edges":len(r["topology"]["nonmanifold_edges"])}
    evidence={"condition":condition,"metric_scope":"local observation proxy, not official score"}
    if condition=="F1":evidence["scalar_p95"]=metrics["p95"]
    if condition in ["F2","F3","F5"]:evidence["metrics"]=metrics
    if condition in ["F3","F5"]:
        evidence["issues"]=copy.deepcopy(r["issues"]);evidence["knowledge"]=rules
    if condition in ["F4","F5"]:
        if not images:raise ValueError("Image feedback requires actual diagnostic images")
        evidence["images"]=[{"path":str(Path(p).resolve()),"sha256":sha256(p)} for p in images]
    if condition=="F0":evidence={"condition":"F0","instruction":"Propose a general algorithm change; no result feedback is provided."}
    write_json(out/"packet.json",evidence)
    # Provenance is kept OUTSIDE the model-facing packet, especially for F0/F4.
    write_json(out/"provenance.json",{"report_sha256":sha256(report),"knowledge_sha256":sha256(knowledge),
                                      "include_knowledge":include_knowledge,"condition":condition})
    text=[f"# {condition} external feedback", "", "Only packet.json is model-facing; provenance is evaluator bookkeeping."]
    if condition in ["F3","F5"]:
        text += ["", "Propose one bounded code change. State evidence, applicable rule IDs, expected benefit and regression risks.",
                 "Do not alter the evaluator, input data, sample identities or acceptance thresholds."]
        text += [f"- {i['kind']}" for i in r["issues"]]
    (out/"README.md").write_text("\n".join(text),encoding="utf-8")
    return evidence
