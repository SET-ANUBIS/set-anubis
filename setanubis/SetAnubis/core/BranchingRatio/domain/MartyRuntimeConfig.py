"""Runtime path resolution for SET-ANUBIS MARTY workflows.

The MARTY integration historically assumed a source checkout containing
``External_Integration/Marty/MARTY_INSTALL`` and mapping/model files below the
checkout ``Assets`` directory.  This module makes those locations explicit and
runtime-configurable while keeping the historical checkout layout as the
default when it is available.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Optional

from SetAnubis.resources import asset_path, repository_root


_ENV_MARTY_PATH = "SETANUBIS_MARTY_PATH"
_ENV_MAPPING_DIR = "SETANUBIS_MARTY_MAPPING_DIR"
_ENV_MODEL_PATH = "SETANUBIS_MARTY_MODEL_PATH"
_ENV_WORKSPACE = "SETANUBIS_MARTY_WORKSPACE"
_ENV_TEMPLATE_DIR = "SETANUBIS_MARTY_TEMPLATE_DIR"


@dataclass(frozen=True)
class MartyInstall:
    """Resolved MARTY installation used for compilation/linking."""

    requested_path: Path
    prefix: Path
    include_dir: Path
    lib_dir: Path
    header: Path
    library: Path
    executable: Optional[Path] = None


@dataclass(frozen=True)
class MartyPathConfig:
    """Concrete filesystem paths used by one MARTY manager instance."""

    mapping_dir: Path
    model_path: Optional[Path]
    workspace_dir: Path
    template_dir: Path
    marty_install: Optional[MartyInstall]

    @classmethod
    def resolve(
        cls,
        model_name: str,
        *,
        mapping_dir: str | os.PathLike[str] | None = None,
        model_path: str | os.PathLike[str] | None = None,
        marty_path: str | os.PathLike[str] | None = None,
        workspace_dir: str | os.PathLike[str] | None = None,
        template_dir: str | os.PathLike[str] | None = None,
    ) -> "MartyPathConfig":
        """Resolve explicit arguments, environment overrides and defaults.

        Precedence is ``explicit argument > environment variable > default``.
        MARTY itself is validated when an explicit/environment path is supplied;
        when no override is supplied the historical bundled installation is used
        if it exists, otherwise compilation will raise a targeted error later.
        """

        mapping = _resolve_existing_dir(
            mapping_dir,
            _ENV_MAPPING_DIR,
            default=asset_path("MARTY", "model"),
            label="MARTY mapping directory",
        )
        templates = _resolve_existing_dir(
            template_dir,
            _ENV_TEMPLATE_DIR,
            default=asset_path("MARTY", "templates"),
            label="MARTY template directory",
        )

        raw_model = _first_nonempty(model_path, os.environ.get(_ENV_MODEL_PATH))
        if raw_model is not None:
            resolved_model = _resolve_existing_file(raw_model, "MARTY model header")
        elif model_name.upper() == "SM":
            # Keep the native MARTY SM header as the default for the SM model.
            resolved_model = None
        else:
            candidate = mapping / f"{model_name.lower()}.h"
            if not candidate.is_file():
                raise FileNotFoundError(
                    f"MARTY model header not found: {candidate}. "
                    f"Pass model_path=... or set {_ENV_MODEL_PATH}."
                )
            resolved_model = candidate.resolve()

        raw_workspace = _first_nonempty(
            workspace_dir,
            os.environ.get(_ENV_WORKSPACE),
        )
        if raw_workspace is None:
            repo = repository_root()
            if repo is not None:
                workspace = (repo / "Assets" / "MARTY" / "MartyTemp").resolve()
            else:
                workspace = (Path.home() / ".cache" / "setanubis" / "marty").resolve()
        else:
            workspace = Path(raw_workspace).expanduser().resolve()
        workspace.mkdir(parents=True, exist_ok=True)

        raw_marty = _first_nonempty(marty_path, os.environ.get(_ENV_MARTY_PATH))
        install: Optional[MartyInstall]
        if raw_marty is not None:
            install = resolve_marty_install(raw_marty, required=True)
        else:
            install = _resolve_default_marty_install()

        return cls(
            mapping_dir=mapping,
            model_path=resolved_model,
            workspace_dir=workspace,
            template_dir=templates,
            marty_install=install,
        )

    def as_dict(self) -> dict[str, str | None]:
        """Return resolved paths in a small serialisable mapping."""
        install = self.marty_install
        return {
            "mapping_dir": str(self.mapping_dir),
            "model_path": None if self.model_path is None else str(self.model_path),
            "workspace_dir": str(self.workspace_dir),
            "template_dir": str(self.template_dir),
            "marty_prefix": None if install is None else str(install.prefix),
            "marty_include_dir": None if install is None else str(install.include_dir),
            "marty_lib_dir": None if install is None else str(install.lib_dir),
        }


def _first_nonempty(*values):
    for value in values:
        if value is not None and os.fspath(value) != "":
            return value
    return None


def _resolve_existing_dir(value, env_name: str, *, default: Path, label: str) -> Path:
    raw = _first_nonempty(value, os.environ.get(env_name), default)
    path = Path(raw).expanduser().resolve()
    if not path.is_dir():
        raise FileNotFoundError(f"{label} not found: {path}")
    return path


def _resolve_existing_file(value, label: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"{label} not found: {path}")
    return path


def _is_marty_library(path: Path) -> bool:
    return path.name in {"libmarty.so", "libmarty.dylib", "libmarty.a"}


def _find_marty_library(lib_dir: Path) -> Optional[Path]:
    for name in ("libmarty.so", "libmarty.dylib", "libmarty.a"):
        candidate = lib_dir / name
        if candidate.is_file():
            return candidate.resolve()
    return None


def _normalise_marty_prefix(requested: Path) -> Path:
    p = requested.expanduser().resolve()

    if p.is_file():
        if p.name == "marty.h" or _is_marty_library(p):
            return p.parent.parent.resolve()
        return p

    if p.name == "include" and (p / "marty.h").is_file():
        return p.parent.resolve()
    if p.name == "lib" and _find_marty_library(p) is not None:
        return p.parent.resolve()

    if (p / "include" / "marty.h").is_file():
        return p
    if (p / "MARTY_INSTALL" / "include" / "marty.h").is_file():
        return (p / "MARTY_INSTALL").resolve()
    if (p / "install" / "include" / "marty.h").is_file():
        return (p / "install").resolve()

    return p


def resolve_marty_install(
    path: str | os.PathLike[str],
    *,
    required: bool = True,
) -> Optional[MartyInstall]:
    """Resolve a MARTY installation from several convenient path forms.

    ``path`` may point to the install prefix, a parent containing
    ``MARTY_INSTALL``/``install``, the ``include`` or ``lib`` directory,
    ``marty.h`` itself, or ``libmarty.so/.dylib/.a``.
    """

    requested = Path(path).expanduser()
    prefix = _normalise_marty_prefix(requested)
    include_dir = prefix / "include"
    lib_dir = prefix / "lib"
    header = include_dir / "marty.h"
    library = _find_marty_library(lib_dir)

    errors: list[str] = []
    if not prefix.exists():
        errors.append(f"prefix does not exist: {prefix}")
    if not header.is_file():
        errors.append(f"missing header: {header}")
    if library is None:
        errors.append(f"missing libmarty in: {lib_dir}")

    if errors:
        if required:
            raise FileNotFoundError(
                "Invalid MARTY installation path. " + "; ".join(errors)
            )
        return None

    executable = prefix / "bin" / "marty"
    return MartyInstall(
        requested_path=requested.resolve(),
        prefix=prefix.resolve(),
        include_dir=include_dir.resolve(),
        lib_dir=lib_dir.resolve(),
        header=header.resolve(),
        library=library,
        executable=executable.resolve() if executable.is_file() else None,
    )


def _resolve_default_marty_install() -> Optional[MartyInstall]:
    repo = repository_root()
    candidates: list[Path] = []
    if repo is not None:
        candidates.append(repo / "External_Integration" / "Marty" / "MARTY_INSTALL")

    # Also honour common MARTY environment conventions if present.
    for name in ("MARTY_INSTALL", "MARTY_ROOT"):
        value = os.environ.get(name)
        if value:
            candidates.append(Path(value))

    for candidate in candidates:
        resolved = resolve_marty_install(candidate, required=False)
        if resolved is not None:
            return resolved
    return None


def require_marty_install(config: MartyPathConfig, context: str = "MARTY") -> MartyInstall:
    """Return the configured install or raise an actionable error."""
    if config.marty_install is not None:
        return config.marty_install
    raise FileNotFoundError(
        f"{context} requires a MARTY installation, but none could be resolved. "
        "Pass marty_path=... to MartyManager/MartyCalculationAdapter or set "
        f"{_ENV_MARTY_PATH}. The path may be the MARTY install prefix, a parent "
        "containing MARTY_INSTALL/, include/, lib/, marty.h, or libmarty.*."
    )
