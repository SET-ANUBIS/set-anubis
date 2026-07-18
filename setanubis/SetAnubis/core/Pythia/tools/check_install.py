"""Diagnostics for the optional SetAnubis Pythia/HepMC3 runtime."""

from __future__ import annotations

from SetAnubis.branding import show_banner

import argparse
import ctypes.util
import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from SetAnubis.core.Pythia.domain.PythiaRunManager import check_pythia_binding, _load_pythia_sim, PythiaBindingError


def _run(cmd: list[str]) -> str | None:
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT).strip()
    except Exception:
        return None


def _path_from_env(name: str) -> str | None:
    value = os.environ.get(name)
    if value:
        return str(Path(value).expanduser())
    return None


def _exists(path: str | None) -> bool:
    return bool(path) and Path(path).expanduser().exists()


def _binding_build_info() -> dict[str, Any] | None:
    try:
        module = _load_pythia_sim()
    except PythiaBindingError:
        return None
    getter = getattr(module, "get_build_info", None)
    return dict(getter()) if getter else None


def collect_diagnostics() -> dict[str, Any]:
    """Return a JSON-serialisable diagnostic report."""
    pythia8_config = shutil.which("pythia8-config")
    hepmc3_config = shutil.which("HepMC3-config")

    pythia8_prefix = _path_from_env("SETANUBIS_PYTHIA8_DIR") or (
        _run([pythia8_config, "--prefix"]) if pythia8_config else None
    )
    hepmc3_prefix = _path_from_env("SETANUBIS_HEPMC3_DIR") or (
        _run([hepmc3_config, "--prefix"]) if hepmc3_config else None
    )

    report = {
        "python_binding": check_pythia_binding(),
        "binding_build_info": _binding_build_info(),
        "environment": {
            "SETANUBIS_BUILD_PYTHIA": os.environ.get("SETANUBIS_BUILD_PYTHIA"),
            "SETANUBIS_PYTHIA8_DIR": os.environ.get("SETANUBIS_PYTHIA8_DIR"),
            "SETANUBIS_HEPMC3_DIR": os.environ.get("SETANUBIS_HEPMC3_DIR"),
            "LD_LIBRARY_PATH": os.environ.get("LD_LIBRARY_PATH"),
            "DYLD_LIBRARY_PATH": os.environ.get("DYLD_LIBRARY_PATH"),
        },
        "tools": {
            "pythia8-config": pythia8_config,
            "HepMC3-config": hepmc3_config,
        },
        "prefixes": {
            "pythia8": pythia8_prefix,
            "hepmc3": hepmc3_prefix,
            "pythia8_exists": _exists(pythia8_prefix),
            "hepmc3_exists": _exists(hepmc3_prefix),
        },
        "libraries": {
            "pythia8": ctypes.util.find_library("pythia8"),
            "HepMC3": ctypes.util.find_library("HepMC3"),
        },
        "python_modules": {
            "pybind11": importlib.util.find_spec("pybind11") is not None,
            "pyhepmc": importlib.util.find_spec("pyhepmc") is not None,
        },
    }
    return report


def print_human(report: dict[str, Any]) -> None:
    binding = report["python_binding"]
    status = "OK" if binding["available"] else "MISSING"
    print(f"Pythia Python binding: {status}")
    if binding["available"]:
        print(f"  module: {binding['module']}")
        print(f"  path  : {binding['path']}")
        build_info = report.get("binding_build_info")
        if build_info:
            print("  build : " + ", ".join(f"{k}={v}" for k, v in build_info.items()))
    else:
        print(f"  error : {binding['error']}")

    print("External tools:")
    for name, path in report["tools"].items():
        print(f"  {name}: {path or 'not found'}")

    print("External prefixes:")
    print(f"  Pythia8: {report['prefixes']['pythia8'] or 'not found'}")
    print(f"  HepMC3 : {report['prefixes']['hepmc3'] or 'not found'}")

    print("Python modules:")
    for name, ok in report["python_modules"].items():
        print(f"  {name}: {'OK' if ok else 'missing'}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check SetAnubis optional Pythia runtime installation")
    parser.add_argument("--json", action="store_true", help="print the full diagnostic report as JSON")
    args = parser.parse_args(argv)

    # Machine-readable modes must keep stdout free from decorative output.
    # The human-readable command still displays the SET-ANUBIS banner once.
    if not args.json:
        show_banner(force=True)

    report = collect_diagnostics()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_human(report)
    return 0 if report["python_binding"]["available"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
