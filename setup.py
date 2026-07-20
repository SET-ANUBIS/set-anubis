"""Setuptools build hooks for optional SetAnubis native extensions.

The default PyPI install is pure Python.  The Pythia/HepMC3 binding is compiled
only when explicitly requested with SETANUBIS_BUILD_PYTHIA=1, or when the value
is set to 'auto' and all external dependencies are discoverable.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Iterable, Optional

from setuptools import Extension, setup

ROOT = Path(__file__).resolve().parent
PYTHIA_CPP_DIR = ROOT / "External_Integration" / "Pythia"

TRUE_VALUES = {"1", "true", "yes", "on", "force"}
AUTO_VALUES = {"auto", "detect"}


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.environ.get(name, default)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _run(cmd: list[str]) -> Optional[str]:
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


def _first_existing(paths: Iterable[Path]) -> Optional[Path]:
    for path in paths:
        if path and path.exists():
            return path
    return None


def _prefix_from_config(config_program: str, flag: str) -> Optional[Path]:
    if shutil.which(config_program):
        value = _run([config_program, flag])
        if value:
            return Path(value).expanduser().resolve()
    return None


def _find_prefix(env_name: str, config_program: str, candidates: Iterable[Path]) -> Optional[Path]:
    explicit = _env(env_name)
    if explicit:
        return Path(explicit).expanduser().resolve()
    configured = _prefix_from_config(config_program, "--prefix")
    if configured and configured.exists():
        return configured
    return _first_existing(candidates)


def _lib_dir(prefix: Path, env_name: str) -> Path:
    explicit = _env(env_name)
    if explicit:
        return Path(explicit).expanduser().resolve()
    for name in ("lib", "lib64"):
        candidate = prefix / name
        if candidate.exists():
            return candidate
    return prefix / "lib"


def _include_dir(prefix: Path, env_name: str) -> Path:
    explicit = _env(env_name)
    if explicit:
        return Path(explicit).expanduser().resolve()
    return prefix / "include"


def _shared_library_exists(lib_dir: Path, stem: str) -> bool:
    suffixes = [".so", ".dylib", ".dll", ".a"]
    names = [f"lib{stem}{suffix}" for suffix in suffixes]
    if platform.system() == "Windows":
        names += [f"{stem}.lib", f"{stem}.dll"]
    return any((lib_dir / name).exists() for name in names)


def _dependency_report() -> tuple[bool, dict[str, str]]:
    pythia_prefix = _find_prefix(
        "SETANUBIS_PYTHIA8_DIR",
        "pythia8-config",
        [
            PYTHIA_CPP_DIR / "pythia8315",
            Path("/usr/local"),
            Path("/usr"),
            Path("/opt/pythia8"),
        ],
    )
    hepmc_prefix = _find_prefix(
        "SETANUBIS_HEPMC3_DIR",
        "HepMC3-config",
        [
            ROOT / "External_Integration" / "HepMC3" / "hepmc3-install",
            Path("/usr/local"),
            Path("/usr"),
            Path("/opt/hepmc3"),
        ],
    )

    report: dict[str, str] = {}
    ok = True

    if not pythia_prefix:
        report["pythia8"] = "missing prefix; set SETANUBIS_PYTHIA8_DIR"
        ok = False
    else:
        pythia_inc = _include_dir(pythia_prefix, "SETANUBIS_PYTHIA8_INCLUDE")
        pythia_lib = _lib_dir(pythia_prefix, "SETANUBIS_PYTHIA8_LIB")
        report["pythia8_prefix"] = str(pythia_prefix)
        report["pythia8_include"] = str(pythia_inc)
        report["pythia8_lib"] = str(pythia_lib)
        if not (pythia_inc / "Pythia8" / "Pythia.h").exists():
            report["pythia8_header"] = "missing Pythia8/Pythia.h"
            ok = False
        if not _shared_library_exists(pythia_lib, "pythia8"):
            report["pythia8_library"] = "missing libpythia8"
            ok = False

    if not hepmc_prefix:
        report["hepmc3"] = "missing prefix; set SETANUBIS_HEPMC3_DIR"
        ok = False
    else:
        hepmc_inc = _include_dir(hepmc_prefix, "SETANUBIS_HEPMC3_INCLUDE")
        hepmc_lib = _lib_dir(hepmc_prefix, "SETANUBIS_HEPMC3_LIB")
        report["hepmc3_prefix"] = str(hepmc_prefix)
        report["hepmc3_include"] = str(hepmc_inc)
        report["hepmc3_lib"] = str(hepmc_lib)
        if not (hepmc_inc / "HepMC3" / "GenEvent.h").exists():
            report["hepmc3_header"] = "missing HepMC3/GenEvent.h"
            ok = False
        if not _shared_library_exists(hepmc_lib, "HepMC3"):
            report["hepmc3_library"] = "missing libHepMC3"
            ok = False

    try:
        import pybind11  # noqa: F401
        report["pybind11"] = "available"
    except Exception as exc:
        report["pybind11"] = f"missing: {exc}"
        ok = False

    return ok, report


def _pythia_extension() -> Extension:
    ok, report = _dependency_report()
    if not ok:
        details = "\n".join(f"  - {key}: {value}" for key, value in report.items())
        raise RuntimeError(
            "Cannot build SetAnubis Pythia binding because external dependencies "
            "were not found.\n"
            f"{details}\n\n"
            "Install Pythia8/HepMC3 first or pass paths explicitly, for example:\n"
            "  SETANUBIS_BUILD_PYTHIA=1 \\\n"
            "  SETANUBIS_PYTHIA8_DIR=/path/to/pythia8 \\\n"
            "  SETANUBIS_HEPMC3_DIR=/path/to/hepmc3 \\\n"
            "  python -m pip install .[pythia]\n"
        )

    import pybind11

    pythia_prefix = Path(report["pythia8_prefix"])
    hepmc_prefix = Path(report["hepmc3_prefix"])
    pythia_inc = Path(report["pythia8_include"])
    hepmc_inc = Path(report["hepmc3_include"])
    pythia_lib = Path(report["pythia8_lib"])
    hepmc_lib = Path(report["hepmc3_lib"])

    extra_compile_args = ["-std=c++14", "-O2"]
    extra_link_args = []
    runtime_library_dirs = []

    if platform.system() != "Windows":
        runtime_library_dirs = [str(pythia_lib), str(hepmc_lib)]
        extra_link_args = [f"-Wl,-rpath,{pythia_lib}", f"-Wl,-rpath,{hepmc_lib}"]

    return Extension(
        "SetAnubis.core.Pythia.bindings.pythia_sim",
        sources=[(PYTHIA_CPP_DIR / "bindings.cpp").relative_to(ROOT).as_posix()],
        include_dirs=[
            str(PYTHIA_CPP_DIR),
            str(pythia_inc),
            str(hepmc_inc),
            pybind11.get_include(),
        ],
        library_dirs=[str(pythia_lib), str(hepmc_lib)],
        libraries=["pythia8", "HepMC3"],
        language="c++",
        extra_compile_args=extra_compile_args,
        extra_link_args=extra_link_args,
        runtime_library_dirs=runtime_library_dirs,
        define_macros=[
            ("SETANUBIS_PYTHIA8_PREFIX", f'"{pythia_prefix}"'),
            ("SETANUBIS_HEPMC3_PREFIX", f'"{hepmc_prefix}"'),
        ],
    )


def _requested_pythia_build() -> str:
    return (_env("SETANUBIS_BUILD_PYTHIA", "0") or "0").lower()


def _extension_modules() -> list[Extension]:
    requested = _requested_pythia_build()
    if requested in TRUE_VALUES:
        return [_pythia_extension()]
    if requested in AUTO_VALUES:
        ok, _ = _dependency_report()
        if ok:
            return [_pythia_extension()]
        print("SetAnubis: skipping optional Pythia binding; dependencies were not auto-detected.")
        return []
    print(
        "SetAnubis: optional Pythia binding disabled. "
        "Set SETANUBIS_BUILD_PYTHIA=1 to compile it during pip install."
    )
    return []


setup(ext_modules=_extension_modules())
