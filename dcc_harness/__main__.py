"""Run from the repository with python -m dcc_harness; installation is optional."""
import argparse
import json
from pathlib import Path
from .evidence import read_json, write_json, evaluate, compare
from .project import Project


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("init"); p.add_argument("project"); p.add_argument("--brief", required=True)
    p = sub.add_parser("status"); p.add_argument("project")
    p = sub.add_parser("begin"); p.add_argument("project"); p.add_argument("script"); p.add_argument("--label", required=True)
    p = sub.add_parser("finish"); p.add_argument("project"); p.add_argument("operation"); p.add_argument("evidence"); p.add_argument("--reconciled", action="store_true")
    p = sub.add_parser("check"); p.add_argument("observation"); p.add_argument("spec"); p.add_argument("--out")
    p = sub.add_parser("diff"); p.add_argument("before"); p.add_argument("after"); p.add_argument("--allow"); p.add_argument("--out")
    p = sub.add_parser("pack-observation", help="Write a new lossless compact observation; never rewrite retained evidence")
    p.add_argument("source"); p.add_argument("destination")
    p = sub.add_parser("start", help="Start continuity from a saved native checkpoint")
    p.add_argument("project"); p.add_argument("--checkpoint", required=True); p.add_argument("--observation", required=True)
    p.add_argument("--brief-file", required=True); p.add_argument("--decisions", required=True); p.add_argument("--handoff"); p.add_argument("--out")
    for command in ("resume", "review"):
        p = sub.add_parser(command); p.add_argument("project"); p.add_argument("--focus", nargs="*", default=[]); p.add_argument("--out")
    p = sub.add_parser("begin-edit", help="Reserve a scoped edit; does not execute it")
    p.add_argument("project"); p.add_argument("--parent", required=True); p.add_argument("--current", required=True)
    p.add_argument("--observation", required=True); p.add_argument("--script", required=True)
    p.add_argument("--contract", required=True); p.add_argument("--label", required=True); p.add_argument("--out")
    p = sub.add_parser("finish-edit", help="Recompute checks and publish a saved result or retain rejection")
    p.add_argument("project"); p.add_argument("edit"); p.add_argument("--checkpoint", required=True)
    p.add_argument("--observation", required=True); p.add_argument("--handoff", required=True)
    p.add_argument("--updates", required=True); p.add_argument("--reconciled", action="store_true"); p.add_argument("--out")
    p.add_argument("--reject-reason", help="Retain this candidate without publication, even if native checks pass")
    args = parser.parse_args()
    if args.command == 'pack-observation':
        from .evidence import file_hash
        source = Path(args.source); source_hash = file_hash(source)
        observation = read_json(source)
        write_json(args.destination, observation, compact_observation=True)
        if file_hash(source) != source_hash:
            raise RuntimeError('Source changed during conversion; inspect the new output')
        result = {'revision': observation['revision'], 'source_unchanged': True,
                  'source_bytes': source.stat().st_size, 'output_bytes': Path(args.destination).stat().st_size,
                  'output': str(Path(args.destination).resolve()), 'native_validation': 'not_performed'}
    elif args.command in ("start", "resume", "review", "begin-edit", "finish-edit"):
        from . import workflow
        if args.command == "start":
            result = workflow.start(args.project, args.checkpoint, args.observation,
                                    Path(args.brief_file).read_text(encoding="utf-8"), read_json(args.decisions), args.handoff)
        elif args.command in ("resume", "review"):
            result = getattr(workflow, args.command)(args.project, args.focus)
        elif args.command == "begin-edit":
            result = workflow.begin_edit(args.project, args.parent, args.current, args.observation,
                                         args.script, args.contract, args.label)
        else:
            result = workflow.finish_edit(args.project, args.edit, args.checkpoint, args.observation,
                                          args.handoff, read_json(args.updates), reconciled=args.reconciled, reject_reason=args.reject_reason)
    elif args.command == "init":
        Project(args.project).init(args.brief); result = Project(args.project).status()
    elif args.command == "status": result = Project(args.project).status()
    elif args.command == "begin": result = {"operation":Project(args.project).begin(args.label,args.script)}
    elif args.command == "finish":
        Project(args.project).finish(args.operation,args.evidence,args.reconciled); result = {"observed":args.operation}
    elif args.command == "check": result = evaluate(read_json(args.observation), read_json(args.spec))
    else: result = compare(read_json(args.before),read_json(args.after),read_json(args.allow) if args.allow else None)
    if getattr(args,"out",None): write_json(args.out,result)
    print(json.dumps(result, indent=2, allow_nan=False))
    if result.get("passed") is False: raise SystemExit(1)


if __name__ == "__main__": main()

