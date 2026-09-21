import argparse
import json
from pathlib import Path
from .io import read_json, write_json


def main():
    ap=argparse.ArgumentParser(description="Offline LoD2 research harness; immutable outputs")
    commands=ap.add_subparsers(dest="command",required=True)
    p=commands.add_parser("reconstruct");p.add_argument("--source",required=True);p.add_argument("--manifest",required=True);p.add_argument("--output",required=True);p.add_argument("--timeout",type=float,default=180)
    p=commands.add_parser("evaluate");p.add_argument("--mesh",required=True);p.add_argument("--points");p.add_argument("--gt-mesh");p.add_argument("--gt-wireframe");p.add_argument("--output",required=True)
    p=commands.add_parser("derive");p.add_argument("--dataset",required=True);p.add_argument("--output",required=True)
    p=commands.add_parser("make-feedback");p.add_argument("--report",required=True);p.add_argument("--knowledge",required=True);p.add_argument("--output",required=True);p.add_argument("--condition",default="F3");p.add_argument("--images",nargs="*",default=[]);p.add_argument("--no-knowledge",action="store_true")
    p=commands.add_parser("compare");p.add_argument("--baseline",required=True);p.add_argument("--previous",required=True);p.add_argument("--current",required=True);p.add_argument("--output",required=True)
    p=commands.add_parser("freeze");p.add_argument("--run",required=True);p.add_argument("--version",required=True);p.add_argument("--knowledge",required=True);p.add_argument("--baseline");p.add_argument("--previous")
    p=commands.add_parser("verify");p.add_argument("release")
    p=commands.add_parser("evolve");p.add_argument("--parent",required=True);p.add_argument("--proposal",required=True);p.add_argument("--manifest",required=True);p.add_argument("--output",required=True);p.add_argument("--knowledge",required=True);p.add_argument("--hypothesis",required=True);p.add_argument("--rule-ids",nargs="+",required=True)
    args=vars(ap.parse_args());command=args.pop("command")
    from . import workflow
    if command=="reconstruct":result=workflow.run_batch(**args)
    elif command=="derive":
        from .derive import derive_dataset
        result=derive_dataset(args["dataset"],args["output"])
    elif command=="evaluate":
        from .evaluate import evaluate
        result=evaluate(args["mesh"],args["points"],args["gt_mesh"],args["gt_wireframe"]);write_json(args["output"],result)
    elif command=="make-feedback":
        from .feedback import make_feedback
        args["include_knowledge"]=not args.pop("no_knowledge");result=make_feedback(**args)
    elif command=="compare":
        output=args.pop("output");result=workflow.compare_runs(**args);write_json(output,result)
    elif command=="freeze":result=str(workflow.freeze_release(**args))
    elif command=="verify":
        result=workflow.verify_release(args["release"])
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result["valid"] else 1
    elif command=="evolve":result=workflow.evolve(**args)
    print(json.dumps({"command":command,"output":args.get("output"),"completed":True},ensure_ascii=False))
    return 0


if __name__=="__main__":raise SystemExit(main())
