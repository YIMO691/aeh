"""Setuptools build hook for AEH's generated wheel resource bundle."""
from pathlib import Path
import shutil

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py


RESOURCE_DIRS = ("core", "schemas", "bootstrap", "adapters")
PROJECT_ROOT = Path(__file__).resolve().parent


class BuildPyWithResources(_build_py):
    """Copy canonical root resources into build_lib/aeh/data at build time."""

    def run(self):
        super().run()
        data_root = Path(self.build_lib, "aeh", "data")
        if data_root.exists():
            shutil.rmtree(data_root)
        data_root.mkdir(parents=True)
        for name in RESOURCE_DIRS:
            source = PROJECT_ROOT / name
            if not source.is_dir():
                raise RuntimeError("missing AEH resource directory: " + str(source))
            shutil.copytree(
                source,
                data_root / name,
                copy_function=shutil.copy2,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )


setup(cmdclass={"build_py": BuildPyWithResources})
