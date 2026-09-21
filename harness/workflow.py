"""Immutable runs and releases. No hidden mutation or overwrite of older results."""
from pathlib import Path
from datetime import datetime, timezone
import json
import re
import shutil
import subprocess
import sys
import time
import numpy as np
from .io import read_json, write_json, sha256, read_obj
from .evaluate import evaluate, structure_edges

REPO=Path(__file__).resolve().parents[1]


def run_batch(source, manifest, output, timeout=180):
    source, manifest, output=Path(source).resolve(),Path(manifest).resolve(),Path(output).resolve()
    spec=read_json(manifest)
    if (spec.get("stage_locked") or spec.get("reconstruction_testing_authorized_now") is False
            or spec.get("role") not in ["development","historical_regression","synthetic_test"]):
        raise ValueError("Evolution cannot consume sealed test manifests")
    ids=[s["id"] for s in spec["samples"]]
    if len(set(ids))!=len(ids) or not all(re.fullmatch(r"[A-Za-z0-9_-]+",x) for x in ids):
        raise ValueError("Unique safe sample IDs required")
    output.mkdir(parents=True,exist_ok=False)
    frozen=output/"source";frozen.mkdir()
    shutil.copyfile(source,frozen/"algorithm.py")
    shutil.copytree(REPO/"harness",frozen/"harness",ignore=shutil.ignore_patterns("__pycache__"))
    write_json(output/"inputs.json",spec)
    rows=[]
    for s in spec["samples"]:
        row={"id":s["id"],"input_sha256":s["sha256"],"status":"failed"}
        start=time.monotonic()
        try:
            p=Path(s["points"])
            if not p.is_file() or sha256(p)!=s["sha256"]:
                raise ValueError("Input absent or SHA mismatch; sample cannot be replaced")
            cmd=[sys.executable,"-B","-m","harness.adapter","--source",str(frozen/"algorithm.py"),
                 "--points",str(p.resolve()),"--output",str(output/"samples"/s["id"]),
                 "--columns",*[str(c) for c in s.get("columns",[0,1,2])]]
            if s.get("localize",False):cmd.append("--localize")
            proc=subprocess.run(cmd,cwd=frozen,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=timeout)
            if proc.returncode:
                raise RuntimeError(proc.stderr[-3000:])
            mesh=output/"samples"/s["id"]/"model.obj"
            report=evaluate(mesh,p,gt_mesh=s.get("gt_mesh"),gt_wireframe=s.get("gt_wireframe"),columns=tuple(s.get("columns",[0,1,2])))
            write_json(output/"samples"/s["id"]/"evaluation.json",report)
            obj=read_obj(mesh);edges,_=structure_edges(obj)
            with (mesh.parent/"wireframe.obj").open("x",encoding="utf-8") as f:
                for q in obj["vertices"]:f.write("v "+" ".join(map(str,q))+"\n")
                for a,b in edges:f.write(f"l {a+1} {b+1}\n")
            row.update(status="evaluated",mesh_sha256=sha256(mesh),
                       p95=report["observed"]["all_points_to_surface"]["p95"],
                       open_edges=len(report["topology"]["open_edges"]),
                       nonmanifold_edges=len(report["topology"]["nonmanifold_edges"]),
                       winding_edges=len(report["topology"]["inconsistent_winding_edges"]),
                       local_reference=report["local_reference"])
            if s.get("historical_mesh"):
                old=read_obj(s["historical_mesh"])
                same_shape=old["vertices"].shape==obj["vertices"].shape
                delta=float(np.abs(old["vertices"]-obj["vertices"]).max()) if same_shape else None
                row["historical_reproduction"]={"same_faces":old["faces"]==obj["faces"],
                    "max_vertex_delta":delta,"byte_identical":sha256(s["historical_mesh"])==sha256(mesh),
                    "geometry_matches":same_shape and delta<=1e-7 and old["faces"]==obj["faces"]}
        except Exception as exc:
            row["error"]=str(exc)
        row["seconds"]=time.monotonic()-start;rows.append(row)
        write_json(output/"progress"/(s["id"]+".json"),row)
        print(s["id"],row["status"],flush=True)
    result={"created_utc":datetime.now(timezone.utc).isoformat(),"manifest_sha256":sha256(manifest),
            "source_sha256":sha256(source),"role":spec["role"],"samples":rows,
            "not_official":True,"independent_test":False}
    write_json(output/"results.json",result)
    return result


def compare_runs(baseline, previous, current):
    runs=[read_json(Path(p)/"results.json") for p in [baseline,previous,current]]
    maps=[{s["id"]:s for s in r["samples"]} for r in runs]
    if not (maps[0].keys()==maps[1].keys()==maps[2].keys()):
        raise ValueError("Comparison requires identical sample identities, including failures")
    rows=[]
    for bid in sorted(maps[0]):
        b,p,c=[m[bid] for m in maps]
        if len({x["input_sha256"] for x in [b,p,c]})!=1:
            raise ValueError("Same ID is not proof of same input")
        protocols=[]
        for root,row in zip([baseline,previous,current],[b,p,c]):
            if row["status"]=="evaluated":protocols.append(read_json(Path(root)/"samples"/bid/"evaluation.json")["protocol"])
        if any(x!=protocols[0] for x in protocols[1:]):raise ValueError("Evaluator protocols differ; re-evaluate all versions")
        row={"id":bid,"input_sha256":c["input_sha256"],"baseline":b,"previous":p,"current":c}
        for name,ref in [("baseline",b),("previous",p)]:
            row["delta_"+name]=c.get("p95",0)-ref.get("p95",0) if c["status"]==ref["status"]=="evaluated" else None
        row["classification"]="failed" if c["status"]!="evaluated" else "not_comparable"
        if row["delta_previous"] is not None:
            topo_worse=any(c[k]>p[k] for k in ["open_edges","nonmanifold_edges","winding_edges"])
            row["classification"]="regressed" if topo_worse or row["delta_previous"]>1e-6 else ("improved" if row["delta_previous"]< -1e-6 else "unchanged")
        rows.append(row)
    return {"metric":"all-input point-to-surface P95; not official score","samples":rows,
            "baseline":str(Path(baseline).resolve()),"previous":str(Path(previous).resolve()),"current":str(Path(current).resolve())}


def freeze_release(run, version, knowledge, baseline=None, previous=None, renders=None):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*",version):raise ValueError("Invalid version identifier")
    run=Path(run);r=read_json(run/"results.json")
    dest=REPO/"releases"/version;dest.mkdir(exist_ok=False)
    for sub in ["models","reports","renders","feedback","knowledge"]:(dest/sub).mkdir()
    shutil.copytree(run/"source",dest/"source",ignore=shutil.ignore_patterns("__pycache__","*.pyc"))
    shutil.copyfile(knowledge,dest/"knowledge"/"rules.json")
    for sub in ["renders","feedback"]:
        origin=Path(renders) if sub=="renders" and renders else run/sub
        if origin.is_dir():shutil.copytree(origin,dest/sub,dirs_exist_ok=True)
    spec=read_json(run/"inputs.json")
    write_json(dest/"reports"/"input_manifest.json",{**{k:v for k,v in spec.items() if k!="samples"},
        "samples":[{k:v for k,v in s.items() if k not in ["points","historical_mesh","gt_mesh","gt_wireframe"]} for s in spec["samples"]]})
    if (run/"decision.json").is_file():
        decision=read_json(run/"decision.json")
        if "comparison" in decision:
            decision["comparison"]={k:v for k,v in decision["comparison"].items() if k not in ["baseline","previous","current"]}
        write_json(dest/"reports"/"decision.json",decision)
    # Raw/staged point clouds and absolute local input paths do NOT enter releases.
    for row in r["samples"]:
        if row["status"]=="evaluated":
            for name in ["model.obj","wireframe.obj"]:
                shutil.copyfile(run/"samples"/row["id"]/name,dest/"models"/(row["id"]+"_"+name))
            shutil.copyfile(run/"samples"/row["id"]/"evaluation.json",dest/"reports"/(row["id"]+".json"))
    write_json(dest/"reports"/"results.json",r)
    if baseline and previous:
        comparison=compare_runs(baseline,previous,run)
        # Do not publish local workspace paths.
        comparison={k:v for k,v in comparison.items() if k not in ["baseline","previous","current"]}
        write_json(dest/"reports"/"comparison.json",comparison)
    env=subprocess.run([sys.executable,"-m","pip","freeze"],capture_output=True,text=True,check=True)
    (dest/"source"/"requirements-lock.txt").write_text(env.stdout,encoding="utf-8")
    state=read_json(run/"decision.json")["status"] if (run/"decision.json").is_file() else "baseline_reproduction"
    (dest/"summary.md").write_text(f"# {version}\n\nStatus: {state}; not an official benchmark result.\n\n"
        f"Source SHA256: {r['source_sha256']}\n\nSamples: {len(r['samples'])}; failures: {sum(s['status']!='evaluated' for s in r['samples'])}.\n"
        "\nRaw inputs are external. Match recorded input hashes before reproduction.\n",encoding="utf-8")
    seal_release(dest)
    return dest


def seal_release(dest):
    dest=Path(dest)
    files=[{"path":p.relative_to(dest).as_posix(),"sha256":sha256(p)} for p in sorted(dest.rglob("*")) if p.is_file() and p.name!="manifest.json"]
    write_json(dest/"manifest.json",{"version":dest.name,"files":files,"immutable":True})


def verify_release(dest):
    dest=Path(dest);m=read_json(dest/"manifest.json")
    errors=[]
    expected={x["path"] for x in m["files"]}
    actual={p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file() and p.name!="manifest.json"}
    for entry in m["files"]:
        p=(dest/entry["path"]).resolve()
        if not p.is_relative_to(dest.resolve()) or not p.is_file() or sha256(p)!=entry["sha256"]:errors.append(entry["path"])
    return {"valid":not errors and actual==expected,"changed_or_missing":errors,"unexpected":sorted(actual-expected)}


def evolve(parent, proposal, manifest, output, knowledge, hypothesis, rule_ids):
    """Evaluate one explicitly supplied candidate; never rewrite the evaluator or parent."""
    rules={x["id"] for x in read_json(knowledge)["rules"]}
    if not hypothesis.strip() or not rule_ids or not set(rule_ids)<=rules:raise ValueError("Hypothesis and valid rule IDs required")
    result=run_batch(proposal,manifest,output)
    comparison=compare_runs(parent,parent,output)
    rows=comparison["samples"]
    eligible=all(r["current"]["status"]=="evaluated" and r["classification"]!="regressed" for r in rows)
    improved=any(r["classification"]=="improved" for r in rows)
    decision={"status":"candidate_promoted_on_development_proxy" if eligible and improved else "not_promoted",
              "hypothesis":hypothesis,"rule_ids":rule_ids,"knowledge_sha256":sha256(knowledge),
              "budget_candidates_consumed":1,"is_generalization_evidence":False,
              "full_solid_validated":False,"comparison":comparison}
    write_json(Path(output)/"decision.json",decision)
    return decision
