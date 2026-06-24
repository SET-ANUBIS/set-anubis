"""Short public imports for SetAnubis.

Examples
--------
>>> from setanubis import SetAnubisInterface, PythiaRunInterface, asset_path
>>> from SetAnubis import SelectionConfig, ATLASCavern

Objects are imported lazily so optional integrations such as Pythia/HepMC3 do
not break a Python-only installation.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

from SetAnubis._version import __version__
from SetAnubis.resources import asset_path, assets_dir, repository_root, ufo_path

_EXPORTS: dict[str, str | tuple[str, str]] = {
    # Model core
    "SetAnubisInterface": "SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface",
    "SetAnubisManager": "SetAnubis.core.ModelCore.domain.SetAnubisManager",
    "SetAnubisPortsConfig": "SetAnubis.core.ModelCore.domain.SetAnubisManager",
    "QCDRunner": "SetAnubis.core.ModelCore.domain.QCDRunner",
    "MassType": "SetAnubis.core.ModelCore.domain.QCDRunner",

    # Branching ratios and decays
    "DecayInterface": "SetAnubis.core.BranchingRatio.adapters.input.DecayInterface",
    "BranchingRatioManager": "SetAnubis.core.BranchingRatio.domain.BranchingRatioManager",
    "CalculationDecayStrategy": "SetAnubis.core.BranchingRatio.domain.CalculationStrategy",
    "Unit": "SetAnubis.core.BranchingRatio.domain.BranchingRatioManager",
    "DecayChecker": "SetAnubis.core.BranchingRatio.domain.DecayChecker",

    # Database / UFO
    "UFOInterface": "SetAnubis.core.DataBase.adapters.UFOInterface",
    "UFOParser": "SetAnubis.core.DataBase.adapters.UFOParser",
    "YAMLParser": "SetAnubis.core.DataBase.adapters.YAMLParser",
    "JSONExtractor": "SetAnubis.core.DataBase.adapters.JSONExtractor",
    "ParamCardGenerator": "SetAnubis.core.DataBase.domain.ParamCardGenerator",
    "EventDatabaseManager": "SetAnubis.core.DataBase.domain.EventDatabaseManagerv3",
    "EventImporter": "SetAnubis.core.DataBase.domain.EventDatabaseManagerv3",
    "EventAccessor": "SetAnubis.core.DataBase.domain.EventDatabaseManagerv3",
    "DataframeBundleIO": "SetAnubis.core.DataBase.domain.EventDatabaseManagerv3",
    "BundleBuildConfig": "SetAnubis.core.DataBase.domain.EventDatabaseManagerv3",

    # Pythia
    "PythiaCMNDInterface": "SetAnubis.core.Pythia.adapters.input.PythiaCMNDInterface",
    "PythiaRunInterface": "SetAnubis.core.Pythia.adapters.input.PythiaRunInterface",
    "CMNDScanManager": "SetAnubis.core.Pythia.adapters.input.CMNDScanManager",
    "PythiaConfig": "SetAnubis.core.Pythia.domain.PythiaConfig",
    "PythiaConfigFactory": "SetAnubis.core.Pythia.domain.PythiaConfigFactory",
    "NewParticlePythiaConfig": "SetAnubis.core.Pythia.domain.NewParticleConfig",
    "HardProductionQCDList": "SetAnubis.core.Pythia.domain.HardProductionSelection",
    "HardProductionElectroweakList": "SetAnubis.core.Pythia.domain.HardProductionSelection",
    "PythiaBindingError": "SetAnubis.core.Pythia.domain.PythiaRunManager",
    "check_pythia_binding": "SetAnubis.core.Pythia.domain.PythiaRunManager",

    # MadGraph
    "MadgraphInterface": "SetAnubis.core.MadGraph.adapters.input.MadGraphInterface",
    "MadGraphInterface": ("SetAnubis.core.MadGraph.adapters.input.MadGraphInterface", "MadgraphInterface"),
    "MadGraphManager": "SetAnubis.core.MadGraph.domain.MadGraphManager",
    "GeneralCardInterface": "SetAnubis.core.MadGraph.adapters.input.GeneralCardInterface",
    "JobScriptBuilder": "SetAnubis.core.MadGraph.adapters.input.JobscriptBuilder",
    "RunCardBuilder": "SetAnubis.core.MadGraph.adapters.input.RunCardBuilder",
    "ParamCardBuilder": "SetAnubis.core.MadGraph.adapters.input.ParamCardBuilder",
    "PythiaCardBuilder": "SetAnubis.core.MadGraph.adapters.input.PythiaCardBuilder",
    "MadSpinCardAdapter": "SetAnubis.core.MadGraph.adapters.input.MadspinCardBuilder",
    "MadGraphHepmcAnalyzer": "SetAnubis.core.MadGraph.adapters.input.MadGraphHepmcAnalyzer",
    "MadGraphDockerRunner": "SetAnubis.core.MadGraph.adapters.output.MadGraphDockerRunner",
    "MadGraphLocalRunner": "SetAnubis.core.MadGraph.adapters.output.MadGraphLocalRunner",
    "MadGraphCommandCard": "SetAnubis.core.MadGraph.domain.MadGraphCommandCard",
    "MadGraphCommandConfig": "SetAnubis.core.MadGraph.domain.MadGraphCommandConfig",
    "RunCardEditor": "SetAnubis.core.MadGraph.domain.MadGraphRunCardEditor",

    # Geometry
    "ATLASCavern": "SetAnubis.core.Geometry.domain.defineGeometry",
    "ATLASCavernGeometry": "SetAnubis.core.Geometry.adapters.ATLASCavernGeometry",
    "ATLASCavernLayout": "SetAnubis.core.Geometry.adapters.ATLASCavernGeometry",
    "ATLASCavernGeometryConfig": "SetAnubis.core.Geometry.adapters.ATLASCavernGeometryConfig",
    "GeometryBuilder": "SetAnubis.core.Geometry.domain.builder",
    "GeometryBuildConfig": "SetAnubis.core.Geometry.domain.builder",
    "CavernGeometryBuilder": "SetAnubis.core.Geometry.adapters.geometry_builder",
    "CavernQuery": "SetAnubis.core.Geometry.adapters.geometry_query",
    "GeometrySelectionAdapter": "SetAnubis.core.Geometry.adapters.selection_adapter",

    # Selection
    "HepmcFrameBuilder": "SetAnubis.core.Selection.domain.HepMCFrameBuilder",
    "HepmcFrameOptions": "SetAnubis.core.Selection.domain.HepMCFrameBuilder",
    "LLPAnalyzer": "SetAnubis.core.Selection.domain.LLPAnalyzer",
    "SelectionEngine": "SetAnubis.core.Selection.domain.SelectionEngine",
    "SelectionConfig": "SetAnubis.core.Selection.domain.SelectionEngine",
    "SelectionGeometryAdapter": "SetAnubis.core.Selection.adapters.input.SelectionGeometryAdapter",
    "RunConfig": "SetAnubis.core.Selection.domain.SelectionEngine",
    "MinThresholds": "SetAnubis.core.Selection.domain.SelectionEngine",
    "MinDR": "SetAnubis.core.Selection.domain.SelectionEngine",
    "SelectionPipelineBuilder": "SetAnubis.core.Selection.domain.SelectionPipeline",
    "FileCache": "SetAnubis.core.Selection.domain.SelectionPipeline",
    "IDataSource": "SetAnubis.core.Selection.domain.SelectionPipeline",
    "SelectionManager": "SetAnubis.core.Selection.domain.SelectionManager",
    "DatasetSpec": "SetAnubis.core.Selection.domain.SelectionManager",
    "EventsBundleSource": "SetAnubis.core.Selection.domain.DatasetSource",
    "SourceConfig": "SetAnubis.core.Selection.domain.DatasetSource",
    "DataBundle": "SetAnubis.core.Selection.domain.ReweightTransformer",
    "ReweightDecayPositions": "SetAnubis.core.Selection.domain.ReweightTransformer",
    "IsolationComputer": "SetAnubis.core.Selection.domain.isolation",
    "JetClusteringConfig": "SetAnubis.core.Selection.domain.JetBuilder",
    "JetClustering": "SetAnubis.core.Selection.domain.JetBuilder",
    "createJetDF": "SetAnubis.core.Selection.domain.JetBuilder",
}

__all__ = [
    "__version__",
    "asset_path",
    "assets_dir",
    "repository_root",
    "ufo_path",
    *_EXPORTS.keys(),
]


def __getattr__(name: str) -> Any:
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module 'SetAnubis' has no attribute {name!r}")
    if isinstance(target, tuple):
        module_name, attr_name = target
    else:
        module_name, attr_name = target, name
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(__all__)
