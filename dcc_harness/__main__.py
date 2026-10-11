"""Run from the repository with python -m dcc_harness; installation is optional."""
import argparse
import json
from pathlib import Path
from .evidence import read_json, write_json, evaluate, compare
from .project import Project


COORDINATION_COMMANDS = {
    'feedback-add': ('feedback.add', 'note'), 'feedback-respond': ('feedback.respond', 'response'),
    'feedback-verify': ('feedback.verify', 'verification'), 'feedback-decide': ('feedback.decide', 'decision'),
    'workflow-bind': ('workflow.bind', 'binding'), 'stage-submit': ('stage.submit', 'submission'),
    'stage-complete': ('stage.complete', 'review'), 'stage-reopen': ('stage.reopen', 'decision')}


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("brief", help="Start here: where the project stands and the exact next commands, as Markdown")
    p.add_argument("project"); p.add_argument("--focus", nargs="*", default=[]); p.add_argument("--out")
    p = sub.add_parser("next", help="The permitted next steps with commands filled from the record; reads only")
    p.add_argument("project"); p.add_argument("--out")
    p = sub.add_parser("requirements", help="What a stage submission needs, with a skeleton for fill-hashes")
    p.add_argument("project"); p.add_argument("stage"); p.add_argument("--out")
    for name, (kind, argument) in COORDINATION_COMMANDS.items():
        p = sub.add_parser(name)
        p.add_argument('project'); p.add_argument('--' + argument, required=True)
        p.add_argument('--expected-revision', required=True); p.add_argument('--request-id', required=True)
        p.add_argument('--evidence-root', help='Base for relative input artifacts; defaults to input JSON folder')
        p.add_argument('--out')
        if name == 'workflow-bind':
            p.add_argument('--manifest', help='Optional override of the packaged environment template')
        if name == 'stage-complete':
            p.add_argument('--submission-id', required=True)
    p = sub.add_parser('workflow-template'); p.add_argument('--out')
    p = sub.add_parser("init", help="Legacy pilot journal: create a journal-only project")
    p.add_argument("project"); p.add_argument("--brief", required=True)
    p = sub.add_parser("status", help="Legacy pilot journal: list status; use resume for continuity projects")
    p.add_argument("project")
    p = sub.add_parser("begin", help="Legacy pilot journal: record a planned script before dispatch")
    p.add_argument("project"); p.add_argument("script"); p.add_argument("--label", required=True)
    p = sub.add_parser("finish", help="Legacy pilot journal: record observed or reconciled evidence")
    p.add_argument("project"); p.add_argument("operation"); p.add_argument("evidence"); p.add_argument("--reconciled", action="store_true")
    p = sub.add_parser("check"); p.add_argument("observation"); p.add_argument("spec"); p.add_argument("--out")
    p = sub.add_parser("diff"); p.add_argument("before"); p.add_argument("after"); p.add_argument("--allow"); p.add_argument("--out")
    p = sub.add_parser("observe", help="Observe a saved .blend in fresh background Blender; never saves")
    p.add_argument("source"); p.add_argument("--blender", required=True, help="Path to Blender executable")
    p.add_argument("--output-dir", required=True, help="New folder for the observation, request and log")
    p.add_argument("--expanded", action="store_true", help="Write formatted JSON instead of compact storage")
    p = sub.add_parser("render", help="Render a project's fixed review views of a saved .blend in fresh background Blender; never saves")
    p.add_argument("source"); p.add_argument("--blender", required=True, help="Path to Blender executable")
    p.add_argument("--output-dir", required=True, help="New folder for the images, settings, receipt and log")
    views = p.add_mutually_exclusive_group(required=True)
    views.add_argument("--project", help="Use the project's review_views decision")
    views.add_argument("--views", help="A dcc.review.views.v1 file")
    p.add_argument("--detach", action="store_true", help="Queue in a separate process and return at once; wait with render-wait")
    p = sub.add_parser("render-wait", help="Wait for a detached render and return its state")
    p.add_argument("job", help="The render's output folder"); p.add_argument("--timeout", type=float, default=100)
    p = sub.add_parser("render-job", help=argparse.SUPPRESS); p.add_argument("job")
    p = sub.add_parser("fill-hashes", help="Fill and verify {path, sha256} references; writes a new payload")
    p.add_argument("payload"); p.add_argument("destination")
    p.add_argument("--evidence-root", help="Base for relative paths; defaults to the payload's folder")
    p = sub.add_parser("pack-observation", help="Write a new lossless compact observation; never rewrite retained evidence")
    p.add_argument("source"); p.add_argument("destination")
    for command in ("adopt-preview", "adopt-apply"):
        p = sub.add_parser(command, help="Preview or apply initial identities in fresh background Blender")
        p.add_argument("input", help="Saved .blend for preview; plan.json for apply")
        p.add_argument("--blender", required=True, help="Path to Blender executable")
        p.add_argument("--output-dir", required=True, help="New folder; existing folders are never reused")
    p = sub.add_parser("preview-revision", help="Freeze and check an already-saved external revision")
    p.add_argument("project"); p.add_argument("--parent", required=True)
    p.add_argument("--checkpoint", required=True); p.add_argument("--observation", required=True)
    p.add_argument("--contract", required=True); p.add_argument("--handoff", required=True)
    p.add_argument("--updates", required=True); p.add_argument("--label", required=True)
    p.add_argument("--note", required=True); p.add_argument("--output-dir", required=True)
    p = sub.add_parser("accept-revision", help="Recheck and publish a frozen external revision")
    p.add_argument("project"); p.add_argument("preview"); p.add_argument("--preview-sha", required=True)
    p.add_argument("--review-note", required=True); p.add_argument("--out")
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
    return parser


def _write_failed(parser, exc):
    parser.exit(2, f"Result printed above was not written to --out ({exc}). Any committed change "
                   "stands; do not repeat the command to get a receipt.\n")


def main():
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "brief":
        from .guidance import brief
        text = brief(args.project, args.focus)
        print(text, end="")
        if args.out:
            try:
                Path(args.out).parent.mkdir(parents=True, exist_ok=True)
                with Path(args.out).open("x", encoding="utf-8", newline="\n") as stream:
                    stream.write(text)
            except OSError as exc:
                _write_failed(parser, exc)
        return
    if args.command in COORDINATION_COMMANDS:
        from . import feedback, environment_workflow
        kind, argument = COORDINATION_COMMANDS[args.command]
        source = Path(getattr(args, argument))
        payload = read_json(source)
        if kind == 'workflow.bind':
            payload = {'manifest': read_json(args.manifest) if args.manifest else environment_workflow.default_manifest(), 'binding': payload}
        elif kind == 'stage.complete':
            payload = {'submission_id': args.submission_id, 'review': payload}
        module = feedback if kind.startswith('feedback.') else environment_workflow
        result = module.apply(args.project, kind, payload, args.expected_revision, args.request_id, args.evidence_root or source.absolute().parent)
    elif args.command == 'next':
        from .guidance import next_steps
        result = next_steps(args.project)
    elif args.command == 'requirements':
        from .guidance import requirements
        result = requirements(args.project, args.stage)
    elif args.command == 'workflow-template':
        from .environment_workflow import default_manifest
        result = default_manifest()
    elif args.command in ('preview-revision', 'accept-revision'):
        from . import revisions
        if args.command == 'preview-revision':
            result = revisions.preview_revision(args.project, args.parent, args.checkpoint, args.observation,
                args.contract, args.handoff, read_json(args.updates), args.label, args.note, args.output_dir)
        else:
            result = revisions.accept_revision(args.project, args.preview, args.preview_sha, args.review_note)
    elif args.command in ('adopt-preview', 'adopt-apply'):
        from . import adoption
        action = adoption.preview if args.command == 'adopt-preview' else adoption.apply
        result = action(args.input, args.output_dir, args.blender)
    elif args.command == 'observe':
        from .observe import observe_file
        result = observe_file(args.source, args.output_dir, args.blender, expanded=args.expanded)
    elif args.command in ('render', 'render-wait', 'render-job'):
        from . import render
        if args.command == 'render-wait':
            result = render.wait(args.job, args.timeout)
        elif args.command == 'render-job':
            result = render.run_job(args.job)
        else:
            action = render.start_detached if args.detach else render.render_file
            result = action(args.source, args.output_dir, args.blender, project=args.project, views=args.views)
    elif args.command == 'fill-hashes':
        from .payloads import fill_hashes
        result = fill_hashes(args.payload, args.destination, args.evidence_root)
    elif args.command == 'pack-observation':
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
    # Print before exporting: a committed result must stay visible even if the receipt cannot be written.
    print(json.dumps(result, indent=2, allow_nan=False))
    if getattr(args, "out", None):
        try:
            write_json(args.out, result)
        except OSError as exc:
            _write_failed(parser, exc)
    nested = result.get("result")
    if result.get("passed") is False or (isinstance(nested, dict) and nested.get("passed") is False):
        raise SystemExit(1)


if __name__ == "__main__": main()

