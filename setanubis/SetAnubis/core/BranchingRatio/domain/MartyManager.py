"""Orchestrate analytic generation, numerical preparation, and MARTY execution."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from SetAnubis.core.BranchingRatio.adapters.output.MartyFileCopyBuilder import (
    MartyFileCopyBuilder,
)
from SetAnubis.core.BranchingRatio.domain.MartyCompiler import CompilerType, MartyCompiler
from SetAnubis.core.BranchingRatio.domain.MartyAmplitudeConfig import (
    MediatorFermionOrders,
    amplitude_config_suffix,
    normalize_mediator_fermion_orders,
)
from SetAnubis.core.BranchingRatio.domain.MartyCopyManager import CopyManager
from SetAnubis.core.BranchingRatio.domain.MartyParamManager import ParamManager
from SetAnubis.core.BranchingRatio.domain.MartyRuntimeConfig import MartyPathConfig
from SetAnubis.core.BranchingRatio.domain.MartyTemplateManager import (
    MartyTemplateManager,
    TemplateType,
)
from SetAnubis.core.BranchingRatio.domain.MartyUtil import decay_name, load_ufo_mappings
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface
from SetAnubis.resources import repository_root


class MartyManager:
    """Coordinate the two-stage MARTY decay-width workflow.

    Paths can be supplied explicitly so that an editable checkout can provide
    the mappings/model while the Python code itself is imported from
    ``site-packages``. Explicit constructor arguments take precedence over the
    corresponding ``SETANUBIS_MARTY_*`` environment variables.
    """

    def __init__(
        self,
        model_name: str,
        *,
        mapping_dir: str | Path | None = None,
        model_path: str | Path | None = None,
        marty_path: str | Path | None = None,
        workspace_dir: str | Path | None = None,
        template_dir: str | Path | None = None,
        mediator_fermion_orders: MediatorFermionOrders | None = None,
    ) -> None:
        """Configure the MARTY model and all runtime filesystem paths.

        Args:
            model_name: MARTY C++ model prefix, e.g. ``"HNL"`` or ``"SM"``.
            mapping_dir: Directory containing ``sm_particle.json``,
                ``model_particle.yaml``, ``conversion_sm.json`` and
                ``conversion_model.yaml``.
            model_path: Optional explicit C++ model header. For non-SM models,
                the default is ``<mapping_dir>/<model_name.lower()>.h``.
            marty_path: MARTY installation. Accepted forms include the install
                prefix, a parent containing ``MARTY_INSTALL/`` or ``install/``,
                ``include/``, ``lib/``, ``marty.h`` or ``libmarty.*``.
            workspace_dir: Writable directory for generated MARTY sources and
                libraries. In a checkout this defaults to
                ``Assets/MARTY/MartyTemp``; installed wheels use a user cache.
            template_dir: Directory containing the SET-ANUBIS numerical helper
                templates.
            mediator_fermion_orders: Optional mapping from mediator name (or a
                tuple of mediator names forming one diagram family) to the
                fermion order used for that MARTY amplitude. For example
                ``{"W": [2, 0, 3, 1], "Z": [3, 0, 2, 1]}``. Each family is
                calculated separately and all pairwise interference terms are
                included before the decay-width library is generated. ``None``
                preserves the historical all-diagrams/automatic-order behaviour.
        """
        self._model_name = model_name
        self.amplitude_components = normalize_mediator_fermion_orders(
            mediator_fermion_orders
        )
        self.path_config = MartyPathConfig.resolve(
            model_name,
            mapping_dir=mapping_dir,
            model_path=model_path,
            marty_path=marty_path,
            workspace_dir=workspace_dir,
            template_dir=template_dir,
        )
        # Kept for compatibility with code that inspected ``root`` directly.
        self.root = repository_root() or Path(__file__).resolve().parents[5]

    @property
    def resolved_paths(self) -> dict[str, str | None]:
        """Return the concrete paths used by this manager instance."""
        return self.path_config.as_dict()

    def _decay_name(self, mothers_id: Any, daughters_id: Any, model: SetAnubisInterface) -> str:
        base = decay_name(
            mothers_id,
            daughters_id,
            model,
            load_ufo_mappings(True, self.path_config.mapping_dir),
        )
        return base + amplitude_config_suffix(self.amplitude_components)

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
            path_config=self.path_config,
            amplitude_components=self.amplitude_components,
        ).prepare()
        decay = self._decay_name(mothers_id, daughters_id, model)
        cpp_path = self.path_config.workspace_dir / f"{decay}.cpp"
        CopyManager(
            f"decay_widths_{decay}",
            builder_marty,
            path_config=self.path_config,
        ).write_file(source, cpp_path)
        return cpp_path

    def launch_analytic(
        self,
        mothers_id: Any,
        daughters_id: Any,
        model: SetAnubisInterface,
    ) -> Any:
        """Compile and execute the analytic source to generate a MARTY library."""
        decay = self._decay_name(mothers_id, daughters_id, model)
        output_path = self.path_config.workspace_dir
        cpp_path = output_path / f"{decay}.cpp"
        binary_path = output_path / decay
        compiler = MartyCompiler(
            CompilerType.GCC,
            f"decay_widths_{decay}",
            path_config=self.path_config,
        )
        return compiler.compile_run(cpp_path, binary_path, output_path)

    def build_numeric(
        self,
        mothers_id: Any,
        daughters_id: Any,
        model: SetAnubisInterface,
        builder_marty: MartyFileCopyBuilder,
    ) -> Path:
        """Prepare numerical source and parameter tables for the generated library."""
        decay = self._decay_name(mothers_id, daughters_id, model)
        copy_manager = CopyManager(
            f"decay_widths_{decay}",
            builder_marty,
            path_config=self.path_config,
        )
        copy_manager.execute()

        source = MartyTemplateManager(
            self._model_name,
            mothers_id,
            daughters_id,
            TemplateType.NUMERIC,
            model,
            path_config=self.path_config,
            amplitude_components=self.amplitude_components,
        ).prepare()
        output_path = (
            self.path_config.workspace_dir
            / "libs"
            / f"decay_widths_{decay}"
        )
        cpp_path = output_path / "script" / f"example_decay_widths_{decay}.cpp"
        copy_manager.write_file(source, cpp_path, force=True)

        parameters = ParamManager(
            output_path / "include" / "params.h",
            model,
            mapping_dir=self.path_config.mapping_dir,
        )
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
        decay = self._decay_name(mothers_id, daughters_id, model)
        compiler = MartyCompiler(
            CompilerType.MAKE,
            f"decay_widths_{decay}",
            path_config=self.path_config,
        )
        result = compiler.compile_run(
            compiler.libs_path,
            f"example_decay_widths_{decay}.x",
            pattern=r"Value\s*:\s*([+-]?(?:\d+(?:\.\d*)?)(?:[eE][+-]?\d+)?)",
        )
        if result is None:
            raise RuntimeError("MARTY numerical execution produced no decay-width value")
        return float(result)
