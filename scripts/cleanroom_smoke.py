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

        after = json_output(
            run([aeh, "doctor", target], cwd=root),
            "post-bootstrap doctor",
        )
        if after.get("overall") not in ("READY", "READY_WITH_WARNINGS"):
            raise RuntimeError("post-bootstrap doctor is not ready: " + repr(after.get("overall")))

        change = json_output(
            run([
                aeh, "change", "new", "wheel smoke",
                "--level", "LIGHTWEIGHT", "--workdir", target,
            ], cwd=root),
            "change new",
        )
        if change.get("status") != "CHANGE_CREATED":
            raise RuntimeError("change new did not succeed: " + repr(change))

        print("SMOKE_PASS")
        print("wheel=" + wheel.name)
        print("doctor=" + after["overall"])
        print("change_id=" + change["change_id"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
