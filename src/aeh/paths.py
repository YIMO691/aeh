"""Resolve AEH's immutable runtime resources in source and wheel installs."""
from importlib import resources
import os
from pathlib import Path


RESOURCE_DOMAINS = frozenset({"core", "schemas", "bootstrap", "adapters"})
_SENTINELS = ("core/workflow.yaml", "schemas/manifest.schema.json")


class AehResourceError(RuntimeError):
    """Raised when the installed AEH resource bundle is missing or incomplete."""


def _package_files():
    return resources.files("aeh")


def _has_sentinels(root):
    return all(root.joinpath(*rel.split("/")).is_file() for rel in _SENTINELS)


def _filesystem_path(root):
    try:
        value = os.fspath(root)
    except TypeError as exc:
        raise AehResourceError(
            "AEH packaged resources are not filesystem-backed; install from a wheel or source tree"
        ) from exc
    return os.path.abspath(value)


def ae_root():
    """Return the directory containing core/schemas/bootstrap/adapters.

    A wheel's generated ``aeh/data`` bundle has priority.  Editable and direct
    source-tree execution fall back to the repository root.  An existing but
    incomplete package bundle is treated as a broken install and never hidden
    by the source fallback.
    """
    packaged = _package_files().joinpath("data")
    if packaged.is_dir():
        if not _has_sentinels(packaged):
            raise AehResourceError(
                "AEH packaged resource bundle is incomplete: expected core/workflow.yaml "
                "and schemas/manifest.schema.json"
            )
        return _filesystem_path(packaged)

    start = Path(__file__).resolve().parent
    for candidate in (start, *start.parents):
        if _has_sentinels(candidate):
            return str(candidate)
    raise AehResourceError(
        "AEH runtime resources were not found in the installed package or source tree"
    )


def join(domain, *relative):
    """Return a safe path below one of AEH's four resource domains."""
    if domain not in RESOURCE_DOMAINS:
        raise AehResourceError("unknown AEH resource domain: " + str(domain))
    base = Path(ae_root(), domain).resolve()
    candidate = base.joinpath(*relative).resolve()
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise AehResourceError("AEH resource path escapes its domain") from exc
    return str(candidate)
