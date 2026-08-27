"""AEH command-line entry point for install health, repair, and change assurance."""
import argparse
import json
import sys


def _emit(report):
    """Write JSON that is safe on legacy Windows console encodings."""
    print(json.dumps(report, ensure_ascii=True, indent=2, default=str))


def _approval_key_map(values):
    result = {}
    for value in values or []:
        if "=" not in value:
            raise ValueError("--approval-key must use KEY_ID=PATH")
        key_id, path = value.split("=", 1)
        if not key_id or not path or key_id in result:
            raise ValueError("--approval-key requires unique non-empty KEY_ID=PATH")
        result[key_id] = path
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(prog="aeh")
    sub = parser.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("bootstrap", help="install AEH into a target repository")
    b.add_argument("target")
    b.add_argument("--dry-run", action="store_true", help="compute plan only, zero writes")
    b.add_argument("--answers", default=None, help="path to answers.yaml (interview answers)")
    b.add_argument("--source-revision", default="dev", help="AEH source revision recorded in manifest")
    d = sub.add_parser("doctor", help="observe/validate/diagnose an AEH installation (read-only)")
    d.add_argument("target")
    rp = sub.add_parser("repair", help="plan, apply, or roll back installation repair")
    rp.add_argument("target")
    repair_mode = rp.add_mutually_exclusive_group()
    repair_mode.add_argument("--apply", action="store_true", help="explicitly apply the generated plan")
    repair_mode.add_argument("--rollback", metavar="TRANSACTION_ID", help="roll back an applied transaction")
    up = sub.add_parser("upgrade", help="plan, apply, or roll back a runtime snapshot upgrade")
    up.add_argument("target")
    upgrade_mode = up.add_mutually_exclusive_group()
    upgrade_mode.add_argument("--apply", action="store_true", help="explicitly apply the generated plan")
    upgrade_mode.add_argument("--rollback", metavar="TRANSACTION_ID", help="roll back an applied upgrade")
    up.add_argument("--source-revision", default="dev", help="destination AEH revision recorded in manifest")
    integration = sub.add_parser(
        "integration", help="read-only workspace/SCM integration surfaces")
    integration_sub = integration.add_subparsers(dest="integration_cmd", required=True)
    integration_inspect = integration_sub.add_parser(
        "inspect", help="inspect Git/SVN and nested repository boundaries without writes")
    integration_inspect.add_argument("target")
    integration_inspect.add_argument("--max-depth", type=int, default=4)
    integration_inspect.add_argument("--max-directories", type=int, default=5000)
    integration_export = integration_sub.add_parser(
        "export", help="export AEH Change Assurance truth for an external Task/Run")
    integration_export.add_argument("change_id")
    integration_export.add_argument("--workdir", default=".", help="AEH target repository")
    integration_export.add_argument("--project-id", default=None, help="optional external project ID")
    integration_export.add_argument("--task-id", required=True, help="external canonical Task ID")
    integration_export.add_argument("--run-id", required=True, help="external canonical Run ID")
    ci = sub.add_parser("ci", help="read-only CI acceptance replay")
    ci_sub = ci.add_subparsers(dest="ci_cmd", required=True)
    ci_verify = ci_sub.add_parser("verify", help="replay committed Change Assurance evidence")
    ci_verify.add_argument("change_id")
    ci_verify.add_argument("--workdir", default=".", help="exact Git checkout to inspect")
    ci_verify.add_argument("--repository-id", required=True, help="stable SCM repository identity")
    ci_verify.add_argument("--base-sha", required=True, help="full base Git object ID")
    ci_verify.add_argument("--head-sha", required=True, help="full head Git object ID")
    ci_verify.add_argument("--observed-at", required=True, help="RFC3339 approval evaluation time")
    ci_verify.add_argument("--approval-key", action="append", default=[], metavar="KEY_ID=PATH",
                           help="external approval credential; repeat for multiple signer keys")
    ci_verify.add_argument("--report", default=None,
                           help="optional JSON path outside the inspected repository")
    ch = sub.add_parser("change", help="change workspace shell (Phase 8)")
    chsub = ch.add_subparsers(dest="change_cmd", required=True)
    cn = chsub.add_parser("new", help="create a change workspace")
    cn.add_argument("title")
    cn.add_argument("--level", default=None, help="suggested classification level")
    cn.add_argument("--workdir", default=".", help="AEH target repository")
    cs = chsub.add_parser("status", help="read-only change status")
    cs.add_argument("change_id")
    cs.add_argument("--workdir", default=".", help="AEH target repository")
    ctr = chsub.add_parser("transition", help="advance change state")
    ctr.add_argument("change_id")
    ctr.add_argument("--to", required=True)
    ctr.add_argument("--condition", default=None)
    ctr.add_argument("--workdir", default=".", help="AEH target repository")
    cg = chsub.add_parser("ground", help="run change-scoped repository grounding")
    cg.add_argument("change_id")
    cg.add_argument("--workdir", default=".", help="AEH target repository")
    csp = chsub.add_parser("spec", help="compile machine spec (Phase 10)")
    csp.add_argument("change_id")
    csp.add_argument("--reqs", default=None, help="user requirements yaml")
    csp.add_argument("--workdir", default=".", help="AEH target repository")
    ctd = chsub.add_parser("test-design", help="compile test plan and install tests (Phase 11)")
    ctd.add_argument("change_id")
    ctd.add_argument("--plan", required=True, help="test plan yaml")
    ctd.add_argument("--test-src", default=None, help="test source directory")
    ctd.add_argument("--workdir", default=".", help="AEH target repository")
    crd = chsub.add_parser("red", help="execute RED tests (Phase 11)")
    crd.add_argument("change_id")
    crd.add_argument("--workdir", default=".", help="AEH target repository")
    crd.add_argument("--allow-shell", action="store_true",
                     help="authorize plan-declared shell execution for this invocation")
    cgn = chsub.add_parser("green", help="validate GREEN (Phase 12)")
    cgn.add_argument("change_id")
    cgn.add_argument("--scope", default=None, help="production scope manifest yaml")
    cgn.add_argument("--workdir", default=".", help="AEH target repository")
    cgn.add_argument("--allow-shell", action="store_true",
                     help="authorize plan-declared shell execution for this invocation")
    crf = chsub.add_parser("refactor", help="validate REFACTOR (Phase 12)")
    crf.add_argument("change_id")
    crf.add_argument("--scope", default=None, help="production scope manifest yaml")
    crf.add_argument("--workdir", default=".", help="AEH target repository")
    crf.add_argument("--allow-shell", action="store_true",
                     help="authorize plan-declared shell execution for this invocation")
    cvf = chsub.add_parser("verify", help="run risk-based verification + traceability (Phase 13)")
    cvf.add_argument("change_id")
    cvf.add_argument("--workdir", default=".", help="AEH target repository")
    cvf.add_argument("--allow-shell", action="store_true",
                     help="authorize plan-declared shell execution for this invocation")
    cvf.add_argument("--approval-key", action="append", default=[], metavar="KEY_ID=PATH",
                     help="external approval credential; repeat for multiple signer keys")
    cap = chsub.add_parser("approve", help="record trusted human approval (Phase 13)")
    cap.add_argument("change_id")
    cap.add_argument("--gate", required=True,
                     help="SPEC_REVIEW | RED_GATE | VERIFY_MANUAL | MERGE_GATE")
    cap.add_argument("--status", required=True, help="APPROVED | REJECTED | REVOKED")
    cap.add_argument("--actor", required=True, help="human attestor identity (honest attestation)")
    cap.add_argument("--evidence-ref", default=None, help="optional reference (decision/artifact id)")
    cap.add_argument("--ttl-seconds", type=int, default=None,
                     help="optional APPROVED lifetime (1..2678400 seconds)")
    cap.add_argument("--key-id", required=True,
                     help="approval credential identifier (secret is never stored in approvals.yaml)")
    cap.add_argument("--credential-file", default=None,
                     help="credential path; defaults to .aeh/private/approval-keys/<key-id>.key")
    cap.add_argument("--workdir", default=".", help="AEH target repository")
    crv = chsub.add_parser("review", help="project review.md from machine artifacts (Phase 13, read-only)")
    crv.add_argument("change_id")
    crv.add_argument("--workdir", default=".", help="AEH target repository")
    crp = chsub.add_parser("repair", help="enter TEST_REPAIR or SPEC_REPAIR through the state machine")
    crp.add_argument("change_id")
    crp.add_argument("--kind", required=True, choices=("test", "spec"))
    crp.add_argument("--workdir", default=".", help="AEH target repository")
    args = parser.parse_args(argv)

    if args.cmd == "bootstrap":
        from .bootstrap import pipeline
        report = pipeline.bootstrap(
            target=args.target,
            answers_path=args.answers,
            dry_run=args.dry_run,
            source_revision=args.source_revision,
        )
        _emit(report)
        return 0 if report["status"] in ("PLAN_READY", "BOOTSTRAP_COMPLETE") else 1
    if args.cmd == "doctor":
        from .doctor import doctor as doc
        report = doc.run_doctor(args.target)
        _emit(report)
        return 0 if report["overall"] != "BLOCKED" else 1
    if args.cmd == "repair":
        from . import repair as repair_module
        if args.rollback:
            report = repair_module.rollback(args.target, args.rollback)
            _emit(report)
            return 0 if report["status"] == "REPAIR_ROLLED_BACK" else 1
        report = repair_module.run_repair(args.target, apply=args.apply)
        _emit(report)
        return 0 if report["status"] in ("REPAIR_PLAN_READY", "REPAIR_APPLIED", "REPAIR_NOOP") else 1
    if args.cmd == "upgrade":
        from . import upgrade as upgrade_module
        if args.rollback:
            report = upgrade_module.rollback(args.target, args.rollback)
            _emit(report)
            return 0 if report["status"] == "UPGRADE_ROLLED_BACK" else 1
        report = upgrade_module.run_upgrade(
            args.target, apply=args.apply, source_revision=args.source_revision)
        _emit(report)
        return 0 if report["status"] in ("UPGRADE_PLAN_READY", "UPGRADE_APPLIED", "UPGRADE_NOOP") else 1
    if args.cmd == "integration":
        from .integrations import aew as integration_module
        try:
            if args.integration_cmd == "inspect":
                report = integration_module.inspect_scm(
                    args.target,
                    max_depth=args.max_depth,
                    max_directories=args.max_directories,
                )
            else:
                report = integration_module.export_change(
                    args.workdir,
                    args.change_id,
                    project_id=args.project_id,
                    task_id=args.task_id,
                    run_id=args.run_id,
                )
            _emit(report)
            return 0
        except (integration_module.IntegrationError, OSError) as exc:
            _emit({"status": "INTEGRATION_FAILED", "error": str(exc)})
            return 1
    if args.cmd == "ci":
        from . import ci as ci_module
        try:
            approval_keys = _approval_key_map(args.approval_key)
        except ValueError as exc:
            _emit({"status": "BLOCKED_BAD_APPROVAL_KEY", "error": str(exc)})
            return 1
        report = ci_module.verify(
            args.workdir, args.change_id, args.repository_id, args.base_sha,
            args.head_sha, args.observed_at, credential_files=approval_keys)
        if args.report:
            try:
                ci_module.write_report(report, args.report, args.workdir)
            except (ci_module.ReplayFailure, OSError) as exc:
                report = dict(report)
                report["verdict"] = "INVALID"
                report["checks"] = list(report["checks"]) + [{
                    "id": "output.boundary", "status": "INVALID", "message": str(exc)}]
                report.pop("canonical_digest", None)
                report["canonical_digest"] = ci_module._sha256_bytes(ci_module._canonical(report))
        _emit(report)
        return 0 if report["verdict"] == "PASS" else 1
    if args.cmd == "change":
        from .runtime import change as chmod
        if args.change_cmd == "new":
            report = chmod.change_new(args.workdir, args.title, suggested_level=args.level)
            _emit(report)
            return 0 if report["status"] == "CHANGE_CREATED" else 1
        if args.change_cmd == "status":
            report = chmod.change_status(args.workdir, args.change_id)
            _emit(report)
            return 0
        if args.change_cmd == "transition":
            report = chmod.change_transition(args.workdir, args.change_id, args.to, condition=args.condition)
            _emit(report)
            return 0 if report["status"] == "TRANSITION_OK" else 1
        if args.change_cmd == "ground":
            from .runtime import grounding as gmod
            report = gmod.change_ground(args.workdir, args.change_id)
            _emit(report)
            return 0 if report["status"] == "GROUNDING_COMPLETE" else 1
        if args.change_cmd == "spec":
            from .runtime import specification as smod
            report = smod.build_spec(args.workdir, args.change_id, reqs_path=args.reqs)
            _emit(report)
            return 0 if report["status"] == "SPEC_COMPLETE" else 1
        if args.change_cmd == "test-design":
            from .runtime import test_design as tdmod
            report = tdmod.change_test_design(args.workdir, args.change_id, args.plan, test_src=args.test_src)
            _emit(report)
            return 0 if report["status"] == "TEST_DESIGN_COMPLETE" else 1
        if args.change_cmd == "red":
            from .runtime import red as rmod
            report = rmod.change_red(
                args.workdir, args.change_id, allow_shell=args.allow_shell)
            _emit(report)
            return 0 if report["status"] == "RED_COMPLETE" else 1
        if args.change_cmd == "green":
            from .runtime import green as gmod
            report = gmod.change_green(
                args.workdir, args.change_id, scope_path=args.scope,
                allow_shell=args.allow_shell)
            _emit(report)
            return 0 if report["status"] == "GREEN_COMPLETE" else 1
        if args.change_cmd == "refactor":
            from .runtime import green as gmod2
            report = gmod2.change_refactor(
                args.workdir, args.change_id, scope_path=args.scope,
                allow_shell=args.allow_shell)
            _emit(report)
            return 0 if report["status"] == "REFACTOR_COMPLETE" else 1
        if args.change_cmd == "verify":
            from .runtime import verify as vmod
            try:
                approval_keys = _approval_key_map(args.approval_key)
            except ValueError as exc:
                _emit({"status": "BLOCKED_BAD_APPROVAL_KEY", "error": str(exc)})
                return 1
            report = vmod.change_verify(
                args.workdir, args.change_id, allow_shell=args.allow_shell,
                credential_files=approval_keys)
            _emit(report)
            return 0 if report["status"] == "VERIFY_COMPLETE" else 1
        if args.change_cmd == "approve":
            from .runtime import approval as apmod
            report = apmod.record_approval(
                args.workdir, args.change_id, args.gate, args.status, args.actor,
                evidence_ref=args.evidence_ref, ttl_seconds=args.ttl_seconds,
                key_id=args.key_id, credential_file=args.credential_file,
            )
            _emit(report)
            return 0 if report["status"] in ("APPROVAL_RECORDED", "APPROVAL_REVOKED") else 1
        if args.change_cmd == "review":
            from .runtime import verify as vmod2
            report = vmod2.change_review(args.workdir, args.change_id)
            _emit(report)
            return 0 if report["status"] == "REVIEW_READY" else 1
        if args.change_cmd == "repair":
            report = chmod.change_repair(args.workdir, args.change_id, args.kind)
            _emit(report)
            return 0 if report["status"] == "TRANSITION_OK" else 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
