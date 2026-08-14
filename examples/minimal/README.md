# Example: minimal

Smallest possible AEH onboarding (this exact sequence was verified clean-room).

## 1. Install

    pip install -e /path/to/adaptive-engineering-harness

## 2. Bootstrap a new project

    mkdir myproj && cd myproj
    mkdir src
    echo 'def greet():' > src/hello.py
    echo '    return "hi"' >> src/hello.py
    aeh bootstrap .
    aeh doctor .

bootstrap applies fail-safe defaults when no --answers file is given; their
provenance is recorded as default_applied (confidence UNKNOWN). Provide
--answers answers.yaml to set your real policy.

## 3. First change

    aeh change new "add greeting module docstring" --level DIRECT
    aeh change status CHG-2026-0001

DIRECT changes use the short workflow (INTAKE → CLASSIFY → IMPLEMENT →
BASIC_VERIFY → DONE) — AEH does not force a tiny change through full TDD.
