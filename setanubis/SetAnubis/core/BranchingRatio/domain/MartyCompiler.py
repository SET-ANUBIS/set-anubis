"""Compilation helpers for generated MARTY sources.

Commands are executed without a shell. Runtime include/library paths are
resolved explicitly through :mod:`MartyRuntimeConfig` instead of assuming a
fixed checkout layout.
"""

from __future__ import annotations

import os
import re
import subprocess
from enum import Enum
from pathlib import Path
from typing import Sequence

from SetAnubis.core.BranchingRatio.domain.MartyRuntimeConfig import (
    MartyPathConfig,
    require_marty_install,
)


class CompilerType(Enum):
    """Supported compilation modes for generated MARTY code."""

    MAKE = "MAKE"
    GCC = "GCC"


class MartyCompiler:
    """Compile and execute generated MARTY programs without invoking a shell."""

    def __init__(
        self,
        compiler_type: CompilerType,
        ampli_name: str | None = None,
        path_config: MartyPathConfig | None = None,
    ):
        """Configure a direct GCC build or a generated-library Make build."""
        self.compiler_type = compiler_type
        self.path_config = path_config or MartyPathConfig.resolve("SM")
        self.libs_path: Path | None = None
        self.ampli_name: str | None = None
        if ampli_name:
            self.libs_path = self.path_config.workspace_dir / "libs" / ampli_name
            self.ampli_name = ampli_name

        install = self.path_config.marty_install
        self.marty_include_path = None if install is None else install.include_dir
        self.marty_lib_path = None if install is None else install.lib_dir

        if self.libs_path is None and compiler_type == CompilerType.MAKE:
            raise ValueError("ampli_name needs to be specified for compiler if make mode.")

    def check_if_compile(self, output_binary: str | os.PathLike[str] | None) -> bool:
        """Return whether the expected executable already exists and is runnable."""
        if self.compiler_type == CompilerType.MAKE:
            assert self.libs_path is not None
            assert self.ampli_name is not None
            binary = self.libs_path / "bin" / f"example_{self.ampli_name}.x"
            if not binary.is_file() or not os.access(binary, os.X_OK):
                return False

            # Rebuild only when the generated numeric driver itself changed.
            # paramlist.csv and partlist.csv are runtime inputs and therefore do
            # not invalidate the executable during parameter or mass scans.
            source = self.libs_path / "script" / f"example_{self.ampli_name}.cpp"
            if source.is_file() and source.stat().st_mtime_ns > binary.stat().st_mtime_ns:
                return False
            return True

        if output_binary is None:
            raise ValueError("output_binary is required in GCC mode")

        binary = Path(output_binary).expanduser()
        if not binary.is_absolute():
            if self.libs_path is None:
                binary = Path.cwd() / binary
            else:
                binary = self.libs_path / binary
        binary = Path(os.path.abspath(os.fspath(binary)))

        if binary.suffix and binary.suffix != ".x":
            raise ValueError(f"Expected binary path without extension, got: {binary.name}")

        return binary.is_file() and os.access(binary, os.X_OK)

    def compile_run(
        self,
        source_file: str | os.PathLike[str],
        output_binary: str | os.PathLike[str] | None = None,
        output_dir: str | os.PathLike[str] | None = None,
        pattern: str | None = None,
    ):
        """Compile the source when required, execute it, and optionally parse output."""
        if not self.check_if_compile(output_binary):
            self.compile(source_file, output_binary)

        if self.compiler_type == CompilerType.GCC:
            if output_binary is None:
                raise ValueError("output_binary is required in GCC mode")
            binary = Path(output_binary).expanduser()
            cwd = (
                Path(os.path.abspath(os.path.expanduser(os.fspath(output_dir))))
                if output_dir
                else None
            )
            if not binary.is_absolute():
                binary = cwd / binary if cwd else Path.cwd() / binary
            binary = Path(os.path.abspath(os.fspath(binary)))
            command = [str(binary)]
        else:
            assert self.libs_path is not None
            assert self.ampli_name is not None
            cwd = self.libs_path
            command = [
                str(
                    Path(
                        os.path.abspath(
                            os.fspath(
                                self.libs_path
                                / "bin"
                                / f"example_{self.ampli_name}.x"
                            )
                        )
                    )
                )
            ]

        return self.execute_command(command, cwd=cwd, pattern=pattern)

    def compile(
        self,
        source_file: str | os.PathLike[str],
        output_binary: str | os.PathLike[str] | None,
    ):
        """Compile a generated source with GCC or run Make in a MARTY library."""
        if self.compiler_type == CompilerType.GCC:
            if output_binary is None:
                raise ValueError("output_binary is required in GCC mode")

            install = require_marty_install(
                self.path_config,
                context="MARTY analytic compilation",
            )
            self.marty_include_path = install.include_dir
            self.marty_lib_path = install.lib_dir

            source = Path(os.path.abspath(os.path.expanduser(os.fspath(source_file))))
            output = Path(os.path.abspath(os.path.expanduser(os.fspath(output_binary))))
            output.parent.mkdir(parents=True, exist_ok=True)

            # The two macros are consumed by defineLibPath() in the generated
            # analytic source, so the library Makefile emitted by MARTY inherits
            # the same external installation paths.
            command = [
                "g++",
                "-o",
                str(output),
                str(source),
                f"-I{install.include_dir}",
                f"-L{install.lib_dir}",
                f"-Wl,-rpath,{install.lib_dir}",
                f'-DMARTY_INCLUDE_PATH="{install.include_dir}"',
                f'-DMARTY_LIBRARY_PATH="{install.lib_dir}"',
                "-lmarty",
                "-lgfortran",
            ]
            cwd = None
        elif self.compiler_type == CompilerType.MAKE:
            assert self.libs_path is not None
            command = ["make"]
            cwd = self.libs_path
        else:  # pragma: no cover - Enum prevents this in normal use.
            raise ValueError("Unsupported compiler type")

        return self.execute_command(command, cwd=cwd)

    def check_if_executed(self) -> bool:
        """Return whether MARTY has already generated the library example source."""
        if self.libs_path is None or self.ampli_name is None:
            return False
        return (self.libs_path / "script" / f"example_{self.ampli_name}.cpp").exists()

    def execute_command(
        self,
        command: Sequence[str | os.PathLike[str]],
        *,
        cwd: str | os.PathLike[str] | None = None,
        pattern: str | None = None,
    ):
        """Execute a trusted executable with explicit arguments."""
        if isinstance(command, (str, bytes, os.PathLike)):
            raise TypeError("command must be a sequence of arguments, not a shell string")

        if self.compiler_type == CompilerType.GCC and self.check_if_executed():
            return None

        args = [os.fspath(part) for part in command]
        result = subprocess.run(
            args,
            cwd=os.fspath(cwd) if cwd is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            rendered = " ".join(args)
            raise RuntimeError(
                f"Command failed with return code {result.returncode}: {rendered}\n"
                f"stderr: {result.stderr}"
            )

        output = result.stdout
        if output:
            print(output)
        if pattern:
            match = re.search(pattern, output)
            if match:
                return match.group(1)
        return None
