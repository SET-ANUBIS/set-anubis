"""Orchestrate analytic generation, numerical preparation, and MARTY execution."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from SetAnubis.core.BranchingRatio.adapters.output.MartyFileCopyBuilder import (
    MartyFileCopyBuilder,
)
from SetAnubis.core.BranchingRatio.domain.MartyCompiler import CompilerType, MartyCompiler
from SetAnubis.core.BranchingRatio.domain.MartyCopyManager import CopyManager
from SetAnubis.core.BranchingRatio.domain.MartyParamManager import ParamManager
from SetAnubis.core.BranchingRatio.domain.MartyTemplateManager import (
    MartyTemplateManager,
    TemplateType,
)
from SetAnubis.core.BranchingRatio.domain.MartyUtil import decay_name, load_ufo_mappings
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface


class MartyManager:
    """Coordinate the two-stage MARTY decay-width workflow."""

    def __init__(self, model_name: str) -> None:
        """Configure the MARTY model class name and repository workspace."""
        self._model_name = model_name
        self.root = Path(__file__).resolve().parents[5]

    def calculate_process(
        self,
        mothers_id: Any,
        daughters_id: Any,
        model: SetAnubisInterface,
        builder_marty: MartyFileCopyBuilder,
    ) -> float:
        """Build and execute analytic and numerical stages for one process."""
        self.build_analytic(mothers_id, daughters_id, model, builder_marty)
        self.launch_analytic(mothers_id, daughters_id, model)
        self.build_numeric(mothers_id, daughters_id, model, builder_marty)
        return self.launch_numeric(mothers_id, daughters_id, model)

    def build_analytic(
        self,
        mothers_id: Any,
        daughters_id: Any,
        model: SetAnubisInterface,
        builder_marty: MartyFileCopyBuilder,
    ) -> Path:
        """Render and write the analytic C++ source without compiling it."""
        source = MartyTemplateManager(
            self._model_name,
            mothers_id,
            daughters_id,
            TemplateType.ANALYTIC,
            model,
        ).prepare()
        decay = decay_name(mothers_id, daughters_id, model, load_ufo_mappings(True))
        cpp_path = self.root / "Assets" / "MARTY" / "MartyTemp" / f"{decay}.cpp"
        CopyManager(f"decay_widths_{decay}", builder_marty).write_file(source, cpp_path)
        return cpp_path

    def launch_analytic(
        self,
        mothers_id: Any,
        daughters_id: Any,
        model: SetAnubisInterface,
    ) -> Any:
        """Compile and execute the analytic source to generate a MARTY library."""
        decay = decay_name(mothers_id, daughters_id, model, load_ufo_mappings(True))
        output_path = self.root / "Assets" / "MARTY" / "MartyTemp"
        cpp_path = output_path / f"{decay}.cpp"
        binary_path = output_path / decay
        compiler = MartyCompiler(CompilerType.GCC, f"decay_widths_{decay}")
        return compiler.compile_run(cpp_path, binary_path, output_path)

    def build_numeric(
        self,
        mothers_id: Any,
        daughters_id: Any,
        model: SetAnubisInterface,
        builder_marty: MartyFileCopyBuilder,
    ) -> Path:
        """Prepare numerical source and parameter tables for the generated library."""
        decay = decay_name(mothers_id, daughters_id, model, load_ufo_mappings(True))
        copy_manager = CopyManager(f"decay_widths_{decay}", builder_marty)
        copy_manager.execute()

        source = MartyTemplateManager(
            self._model_name,
            mothers_id,
            daughters_id,
            TemplateType.NUMERIC,
            model,
        ).prepare()
        output_path = (
            self.root
            / "Assets"
            / "MARTY"
            / "MartyTemp"
            / "libs"
            / f"decay_widths_{decay}"
        )
        cpp_path = output_path / "script" / f"example_decay_widths_{decay}.cpp"
        copy_manager.write_file(source, cpp_path, force=True)

        parameters = ParamManager(output_path / "include" / "params.h", model)
        copy_manager.write_file(
            parameters.create_csv(), output_path / "bin" / "paramlist.csv", force=True
        )
        copy_manager.write_file(
            parameters.create_particle_csv(mothers_id, daughters_id),
            output_path / "bin" / "partlist.csv",
            force=True,
        )
        return cpp_path

    def launch_numeric(
        self,
        mothers_id: Any,
        daughters_id: Any,
        model: SetAnubisInterface,
    ) -> float:
        """Build and execute the numerical integration program."""
        decay = decay_name(mothers_id, daughters_id, model, load_ufo_mappings(True))
        compiler = MartyCompiler(CompilerType.MAKE, f"decay_widths_{decay}")
        result = compiler.compile_run(
            compiler.libs_path,
            f"example_decay_widths_{decay}.x",
            pattern=r"Value\s*:\s*([+-]?(?:\d+(?:\.\d*)?)(?:[eE][+-]?\d+)?)",
        )
        if result is None:
            raise RuntimeError("MARTY numerical execution produced no decay-width value")
        return float(result)
