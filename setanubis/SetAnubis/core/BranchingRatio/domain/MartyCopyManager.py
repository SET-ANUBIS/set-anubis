"""Prepare helper sources inside a generated MARTY library workspace."""

from pathlib import Path

from SetAnubis.core.BranchingRatio.adapters.output.MartyFileCopyBuilder import (
    MartyFileCopyBuilder,
)
from SetAnubis.core.BranchingRatio.domain.MartyRuntimeConfig import MartyPathConfig


class CopyManager:
    """Copy integration helpers and update their generated namespace."""

    def __init__(
        self,
        ampli_name: str,
        builder: MartyFileCopyBuilder,
        path_config: MartyPathConfig | None = None,
    ):
        """Configure the target library name, paths and copy backend."""
        self.ampli_name = ampli_name
        # MARTY normalizes generated C++ library namespaces to lowercase.
        # Keep the filesystem/library name unchanged, but always refer to the
        # generated namespace using the same convention.
        self.namespace_name = ampli_name.lower()
        self.path_config = path_config or MartyPathConfig.resolve("SM")
        self.template_dir = self.path_config.template_dir
        self.target_base = (
            self.path_config.workspace_dir / "libs" / ampli_name
        )
        self.builder = builder

    def prepare_files(self):
        """Queue helper sources, headers, and the generated Makefile update."""
        files_to_copy = [
            "integration.cpp",
            "kinematics.cpp",
            "kinematics.h",
            "integration.h",
            "csv_helper.cpp",
            "csv_helper.h",
        ]

        for file_name in files_to_copy:
            src = self.template_dir / file_name
            is_header = file_name.endswith(".h")
            dest_dir = self.target_base / ("include" if is_header else "src")
            dest = dest_dir / file_name

            modifications = []
            if file_name in {"kinematics.h", "integration.h"}:
                modifications.append(
                    (
                        "using namespace decay_widths;",
                        f"using namespace {self.namespace_name};",
                    )
                )

            self.builder.add_file(src, dest, modifications)

        makefile_path = self.target_base / "Makefile"
        makefile_modifications = [
            ("CXXSTD  = -std=c++17", "CXXSTD  = -std=c++20")
        ]
        self.builder.add_file(makefile_path, makefile_path, makefile_modifications)

    def write_file(self, cpp_code: str, cpp_path, force: bool = False):
        """Write generated C++ source code to ``cpp_path``."""
        cpp_path = Path(cpp_path)
        cpp_path.parent.mkdir(parents=True, exist_ok=True)

        if cpp_path.exists():
            if cpp_path.read_text(encoding="utf-8") == cpp_code:
                return cpp_path
            if not force:
                return cpp_path

        cpp_path.write_text(cpp_code, encoding="utf-8")
        return cpp_path

    def execute(self):
        """Prepare and execute the complete copy plan."""
        self.prepare_files()
        self.builder.execute()
