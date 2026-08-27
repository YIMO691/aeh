"""Portable, policy-enforced process execution for AEH-managed commands.

This module deliberately does not call itself an OS sandbox.  It constrains
process launch semantics; repository code still has the caller's OS authority.
"""
import os
import re
import shlex
import subprocess

import jsonschema
import yaml

from .. import paths as aeh_paths


class ExecutionPolicyError(ValueError):
    pass


_SHELL_SYNTAX = re.compile(r"[\r\n;&|<>`]|\$\(")


def _load_yaml(path):
    with open(path, "r", encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def _policy_paths(target, ae_root=None):
    installed = os.path.join(target, ".aeh", "runtime", "core", "execution-policy.yaml")
    if os.path.isfile(installed):
        root = os.path.join(target, ".aeh", "runtime")
        return installed, os.path.join(root, "schemas", "execution-policy.schema.json")
    root = ae_root or aeh_paths.ae_root()
    return (os.path.join(root, "core", "execution-policy.yaml"),
            os.path.join(root, "schemas", "execution-policy.schema.json"))


def load_policy(target, ae_root=None):
    policy_path, schema_path = _policy_paths(target, ae_root)
    policy = _load_yaml(policy_path)
    jsonschema.validate(policy, _load_yaml(schema_path))
    limits = policy["limits"]
    if limits["default_timeout_seconds"] > limits["max_timeout_seconds"]:
        raise ExecutionPolicyError(
            "BLOCKED_EXECUTION_POLICY: default timeout exceeds maximum")
    return policy


def _resolve_cwd(target, cwd):
    target_real = os.path.realpath(target)
    candidate = target if not cwd else (cwd if os.path.isabs(cwd) else os.path.join(target, cwd))
    candidate_real = os.path.realpath(candidate)
    try:
        if os.path.commonpath([target_real, candidate_real]) != target_real:
            raise ExecutionPolicyError("BLOCKED_CWD_ESCAPE: " + str(cwd))
    except ValueError as exc:
        raise ExecutionPolicyError("BLOCKED_CWD_ESCAPE: " + str(cwd)) from exc
    if not os.path.isdir(candidate_real):
        raise ExecutionPolicyError("BLOCKED_CWD_MISSING: " + str(cwd))
    return candidate_real


def _validate_argv(argv, limits):
    if not isinstance(argv, list) or not argv:
        raise ExecutionPolicyError("BLOCKED_EXECUTION_SPEC: argv must be a non-empty list")
    if len(argv) > limits["max_arguments"]:
        raise ExecutionPolicyError("BLOCKED_EXECUTION_LIMIT: too many arguments")
    normalized = []
    for value in argv:
        if not isinstance(value, str) or not value or "\x00" in value:
            raise ExecutionPolicyError("BLOCKED_EXECUTION_SPEC: invalid argv value")
        if len(value) > limits["max_argument_length"]:
            raise ExecutionPolicyError("BLOCKED_EXECUTION_LIMIT: argument too long")
        normalized.append(value)
    return normalized


def _command_argv(command, limits):
    if not isinstance(command, str) or not command.strip() or "\x00" in command:
        raise ExecutionPolicyError("BLOCKED_EXECUTION_SPEC: command must be a non-empty string")
    if _SHELL_SYNTAX.search(command):
        raise ExecutionPolicyError(
            "BLOCKED_SHELL_SYNTAX: declare shell=true and invoke with --allow-shell")
    try:
        argv = shlex.split(command, posix=(os.name != "nt"))
        if os.name == "nt":
            argv = [
                value[1:-1]
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"')
                else value
                for value in argv
            ]
    except ValueError as exc:
        raise ExecutionPolicyError("BLOCKED_EXECUTION_SPEC: malformed command quoting") from exc
    return _validate_argv(argv, limits)


def _environment(policy, requested):
    allowed = {name.upper() for name in policy["environment"]["inherit_allowlist"]}
    result = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    requested = requested or {}
    if not isinstance(requested, dict):
        raise ExecutionPolicyError("BLOCKED_EXECUTION_ENV: env must be an object")
    for key, value in requested.items():
        if not isinstance(key, str) or key.upper() not in allowed:
            raise ExecutionPolicyError("BLOCKED_EXECUTION_ENV: variable not allowlisted: " + str(key))
        if not isinstance(value, str) or "\x00" in value:
            raise ExecutionPolicyError("BLOCKED_EXECUTION_ENV: invalid value for " + key)
        result[key] = value
    return result


def run_execution(target, spec, allow_shell=False, ae_root=None):
    """Execute one locked plan entry and return exit code, output, receipt text."""
    policy = load_policy(target, ae_root)
    limits = policy["limits"]
    cwd = _resolve_cwd(target, spec.get("cwd"))
    timeout = spec.get("timeout_seconds", limits["default_timeout_seconds"])
    if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout < 1:
        raise ExecutionPolicyError("BLOCKED_EXECUTION_TIMEOUT: positive integer required")
    if timeout > limits["max_timeout_seconds"]:
        raise ExecutionPolicyError("BLOCKED_EXECUTION_TIMEOUT: exceeds policy maximum")

    shell_declared = spec.get("shell", False)
    if not isinstance(shell_declared, bool):
        raise ExecutionPolicyError("BLOCKED_EXECUTION_SPEC: shell must be boolean")
    argv_value = spec.get("argv")
    command = spec.get("command")
    if argv_value is not None and command:
        raise ExecutionPolicyError("BLOCKED_EXECUTION_SPEC: choose argv or command, not both")

    if shell_declared:
        if not allow_shell:
            raise ExecutionPolicyError(
                "BLOCKED_SHELL_AUTHORIZATION_REQUIRED: plan and invocation must both authorize shell")
        if argv_value is not None or not isinstance(command, str) or not command.strip():
            raise ExecutionPolicyError("BLOCKED_EXECUTION_SPEC: shell execution requires command string")
        launch = command
        shell = True
        receipt = "mode=authorized-shell command=" + command
    elif argv_value is not None:
        launch = _validate_argv(argv_value, limits)
        shell = False
        receipt = "mode=argv shell=false argv=" + " ".join(launch)
    elif command:
        launch = _command_argv(command, limits)
        shell = False
        receipt = "mode=compatibility-argv shell=false argv=" + " ".join(launch)
    else:
        raise ExecutionPolicyError("BLOCKED_EXECUTION_SPEC: missing argv or command")

    env = _environment(policy, spec.get("env"))
    try:
        proc = subprocess.run(
            launch,
            shell=shell,
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = (proc.stdout or "") + "\n" + (proc.stderr or "")
        return proc.returncode, output, receipt
    except subprocess.TimeoutExpired:
        return 124, "timeout", receipt + " outcome=timeout"
    except OSError as exc:
        return 127, str(exc), receipt + " outcome=oserror"
