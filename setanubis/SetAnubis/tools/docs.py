"""Build SetAnubis Sphinx documentation from a checkout or installed package."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import webbrowser
from pathlib import Path


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file() and (parent / "Docs" / "manual" / "source").is_dir():
            return parent
    # Installed wheels normally do not ship the full Sphinx source tree.
    raise RuntimeError(
        "Cannot locate Docs/manual/source. Run this command from a SetAnubis "
        "checkout, or build docs with `python -m sphinx -b html ...`."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the SetAnubis Sphinx documentation")
    parser.add_argument("--open", action="store_true", help="open the generated index.html in a browser")
    parser.add_argument("--clean", action="store_true", help="remove the previous HTML build before rebuilding")
    parser.add_argument("--strict", action="store_true", help="treat Sphinx warnings as errors")
    parser.add_argument("--builder", default="html", help="Sphinx builder to use; default: html")
    args = parser.parse_args(argv)

    root = _repo_root()
    source = root / "Docs" / "manual" / "source"
    build = root / "Docs" / "manual" / "build" / args.builder

    if args.clean and build.exists():
        import shutil
        shutil.rmtree(build)

    cmd = [sys.executable, "-m", "sphinx", "-b", args.builder]
    if args.strict:
        cmd.append("-W")
    cmd += [str(source), str(build)]
    print(" ".join(cmd))
    subprocess.check_call(cmd, cwd=root)

    index = build / "index.html"
    print(f"Documentation built at: {index}")
    if args.open and index.exists():
        webbrowser.open(index.as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
