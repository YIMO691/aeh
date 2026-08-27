"""Install an AEH wheel into a fresh venv and exercise its minimum CLI chain."""
import argparse
import glob
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import venv


def run(argv, *, cwd=None, expected=(0,)):
    result = subprocess.run(
        [str(x) for x in argv],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode not in expected:
        raise RuntimeError(
            "command failed ({code}): {cmd}\nstdout:\n{out}\nstderr:\n{err}".format(
                code=result.returncode,
                cmd=" ".join(str(x) for x in argv),
                out=result.stdout,
                err=result.stderr,
            )
        )
    return result


def json_output(result, label):
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(label + " did not emit JSON:\n" + result.stdout) from exc


def resolve_wheel(pattern):
    matches = [Path(p).resolve() for p in glob.glob(pattern)]
    if len(matches) != 1 or not matches[0].is_file():
        raise RuntimeError("expected exactly one wheel for {!r}, found {}".format(pattern, matches))
    return matches[0]


def venv_python(root):
    return root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def venv_aeh(root):
    return root / ("Scripts/aeh.exe" if os.name == "nt" else "bin/aeh")


def shape_v01_snapshot(python, target):
    """Turn the fresh candidate install into the repository's v0.1 runtime shape."""
    old_manifest_schema = (
        Path(__file__).resolve().parents[1]
        / "tests" / "fixtures" / "upgrade-v0.1" / "manifest.schema.json"
    )
    code = r'''
import hashlib
import os
from pathlib import Path
import shutil
import sys
import yaml

target = Path(sys.argv[1])
old_manifest_schema = Path(sys.argv[2])
schemas = target / ".aeh" / "runtime" / "schemas"
for name in (
    "repair-plan.schema.json", "repair-rule.schema.json",
    "transaction-journal.schema.json", "upgrade-plan.schema.json",
    "upgrade-policy.schema.json",
):
    path = schemas / name
    if path.exists():
        path.unlink()
shutil.copyfile(old_manifest_schema, schemas / "manifest.schema.json")
transactions = target / ".aeh" / "transactions"
if transactions.exists():
    shutil.rmtree(transactions)
parts = []
runtime = target / ".aeh" / "runtime"
for folder in ("core", "schemas"):
    directory = runtime / folder
    for path in sorted(directory.iterdir()):
        if path.is_file():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            parts.append(folder + "/" + path.name + "\0" + digest)
runtime_digest = hashlib.sha256("\n".join(sorted(parts)).encode("utf-8")).hexdigest()
manifest_path = target / ".aeh" / "manifest.yaml"
manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
manifest["harness"]["version"] = "0.1.0"
manifest["harness"]["source_revision"] = "6513102"
manifest["source_hashes"]["runtime"] = runtime_digest
manifest.pop("upgrade_history", None)
manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=True), encoding="utf-8")
'''
    run([python, "-c", code, target, old_manifest_schema])


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", required=True, help="wheel path or glob resolving to one wheel")
    args = parser.parse_args(argv)
    wheel = resolve_wheel(args.wheel)

    with tempfile.TemporaryDirectory(prefix="aeh-cleanroom-") as tmp:
        root = Path(tmp)
        env_root = root / "venv"
        target = root / "target"
        venv.EnvBuilder(with_pip=True, clear=True).create(env_root)
        python = venv_python(env_root)

        run([python, "-m", "pip", "install", "--disable-pip-version-check", wheel])
        aeh = venv_aeh(env_root)
        if not aeh.is_file():
            raise RuntimeError("wheel installation did not create the aeh console entry point")
        approval_help = run([aeh, "change", "approve", "--help"], cwd=root).stdout
        for required_help in (
            "VERIFY_MANUAL", "REVOKED", "--ttl-seconds", "--key-id", "--credential-file",
        ):
            if required_help not in approval_help:
                raise RuntimeError("installed approval CLI is missing " + required_help)
        green_help = run([aeh, "change", "green", "--help"], cwd=root).stdout
        if "--allow-shell" not in green_help:
            raise RuntimeError("installed execution CLI is missing --allow-shell")

        target.mkdir()
        (target / "README.md").write_text("# AEH wheel smoke target\n", encoding="utf-8")
        run(["git", "init", "--quiet", str(target)])

        before = json_output(
            run([aeh, "doctor", target], cwd=root, expected=(1,)),
            "pre-bootstrap doctor",
        )
        blocked = {c.get("check_id") for c in before.get("checks", []) if c.get("status") == "BLOCKED"}
        if before.get("overall") != "BLOCKED" or "install.aeh_exists" not in blocked:
            raise RuntimeError("pre-bootstrap doctor did not report install.aeh_exists as BLOCKED")

        installed = json_output(
            run([aeh, "bootstrap", target], cwd=root),
            "bootstrap",
        )
        if installed.get("status") != "BOOTSTRAP_COMPLETE":
            raise RuntimeError("bootstrap did not complete: " + repr(installed))
        gates_text = (target / ".aeh" / "runtime" / "core" / "gates.yaml").read_text(
            encoding="utf-8"
        )
        approvals_text = (
            target / ".aeh" / "runtime" / "schemas" / "approvals.schema.json"
        ).read_text(encoding="utf-8")
        execution_policy = (
            target / ".aeh" / "runtime" / "core" / "execution-policy.yaml"
        ).read_text(encoding="utf-8")
        execution_schema = (
            target / ".aeh" / "runtime" / "schemas" / "execution-policy.schema.json"
        ).read_text(encoding="utf-8")
        if "VERIFY_MANUAL" not in gates_text or "REVOKED" not in approvals_text:
            raise RuntimeError("installed wheel is missing M4 gate/schema resources")
        if "constrained_process" not in execution_policy or "shell" not in execution_schema:
            raise RuntimeError("installed wheel is missing M5 execution-policy resources")

        after = json_output(
            run([aeh, "doctor", target], cwd=root),
            "post-bootstrap doctor",
        )
        if after.get("overall") not in ("READY", "READY_WITH_WARNINGS"):
            raise RuntimeError("post-bootstrap doctor is not ready: " + repr(after.get("overall")))

        runtime_file = target / ".aeh" / "runtime" / "core" / "workflow.yaml"
        runtime_file.unlink()
        repair_plan = json_output(
            run([aeh, "repair", target], cwd=root),
            "repair dry-run",
        )
        if repair_plan.get("status") != "REPAIR_PLAN_READY" or runtime_file.exists():
            raise RuntimeError("repair dry-run changed state or did not produce a plan")
        repaired = json_output(
            run([aeh, "repair", target, "--apply"], cwd=root),
            "repair apply",
        )
        if repaired.get("status") != "REPAIR_APPLIED" or not runtime_file.is_file():
            raise RuntimeError("repair apply did not restore the runtime: " + repr(repaired))
        after_repair = json_output(
            run([aeh, "doctor", target], cwd=root),
            "post-repair doctor",
        )
        if after_repair.get("overall") not in ("READY", "READY_WITH_WARNINGS"):
            raise RuntimeError("post-repair doctor is not ready: " + repr(after_repair.get("overall")))

        shape_v01_snapshot(python, target)
        old_doctor = json_output(
            run([aeh, "doctor", target], cwd=root, expected=(1,)),
            "v0.1-shaped doctor",
        )
        if old_doctor.get("overall") != "BLOCKED":
            raise RuntimeError("v0.1-shaped target was not blocked for explicit upgrade")
        manifest_path = target / ".aeh" / "manifest.yaml"
        manifest_before_plan = manifest_path.read_bytes()
        upgrade_plan = json_output(
            run([aeh, "upgrade", target, "--source-revision", "cleanroom-m3"], cwd=root),
            "upgrade dry-run",
        )
        if upgrade_plan.get("status") != "UPGRADE_PLAN_READY":
            raise RuntimeError("upgrade did not produce a dry-run plan: " + repr(upgrade_plan))
        if manifest_path.read_bytes() != manifest_before_plan:
            raise RuntimeError("upgrade dry-run changed the manifest")
        upgraded = json_output(
            run([aeh, "upgrade", target, "--apply", "--source-revision", "cleanroom-m3"], cwd=root),
            "upgrade apply",
        )
        if upgraded.get("status") != "UPGRADE_APPLIED":
            raise RuntimeError("upgrade apply did not complete: " + repr(upgraded))
        after_upgrade = json_output(
            run([aeh, "doctor", target], cwd=root),
            "post-upgrade doctor",
        )
        if after_upgrade.get("overall") not in ("READY", "READY_WITH_WARNINGS"):
            raise RuntimeError("post-upgrade doctor is not ready: " + repr(after_upgrade.get("overall")))

        change = json_output(
            run([
                aeh, "change", "new", "wheel smoke",
                "--level", "LIGHTWEIGHT", "--workdir", target,
            ], cwd=root),
            "change new",
        )
        if change.get("status") != "CHANGE_CREATED":
            raise RuntimeError("change new did not succeed: " + repr(change))

        scm_inspection = json_output(
            run([aeh, "integration", "inspect", target, "--max-depth", "1"], cwd=root),
            "integration inspect",
        )
        if (scm_inspection.get("status") != "INSPECTION_COMPLETE"
                or scm_inspection.get("read_only") is not True
                or scm_inspection.get("network_used") is not False):
            raise RuntimeError("integration inspect contract failed: " + repr(scm_inspection))

        aew_export = json_output(
            run([
                aeh, "integration", "export", change["change_id"],
                "--workdir", target,
                "--project-id", "CLEANROOM-PROJECT",
                "--task-id", "CLEANROOM-TASK",
                "--run-id", "CLEANROOM-RUN",
            ], cwd=root),
            "integration export",
        )
        if (aew_export.get("status") != "EXPORT_COMPLETE"
                or aew_export.get("governance", {}).get("portable_verdict") != "NOT_VERIFIED"):
            raise RuntimeError("integration export contract failed: " + repr(aew_export))

        print("SMOKE_PASS")
        print("wheel=" + wheel.name)
        print("doctor=" + after_upgrade["overall"])
        print("repair_transaction=" + repaired["transaction_id"])
        print("upgrade_transaction=" + upgraded["transaction_id"])
        print("change_id=" + change["change_id"])
        print("integration_inspect=" + scm_inspection["root_repository"]["type"])
        print("integration_export=" + aew_export["governance"]["portable_verdict"])
        print("m4_governance=VERIFY_MANUAL+TTL+REVOKED")
        print("m5_security=SIGNED_APPROVALS+CONSTRAINED_PROCESS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
