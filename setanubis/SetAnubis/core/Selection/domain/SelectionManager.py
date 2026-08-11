from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any, Mapping

import pandas as pd

from SetAnubis.core.Selection.domain.SelectionPipeline import SelectionPipeline, SelectionPipelineBuilder, IDataSource
from SetAnubis.core.Selection.domain.DatasetSource import EventsBundleSource
from SetAnubis.core.Selection.domain.SelectionEngine import SelectionConfig, RunConfig

@dataclass
class DatasetSpec:
    name: str
    source: IDataSource


@dataclass
class SampleResult:
    name: str
    cutFlow: Dict[str, float | int]
    finalDF: pd.DataFrame
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CombinedResult:
    per_sample: List[SampleResult]
    cutflow_sum: Dict[str, float | int]

class SelectionManager:
    """
    Use a unique pipeline on multiple sources. Do not construct a pipeline itself but 
    allows for GPU and CPU optimization.
    """
    def __init__(self, pipeline: SelectionPipeline) -> None:
        self.pipeline = pipeline

    def run_many(
        self,
        named_sources: List[Tuple[str, EventsBundleSource]],
        sel_cfg: SelectionConfig,
        run_cfg: RunConfig,
        *,
        store: bool = False,
        results_db: Any = None,
        analysis_name: str = "default",
        on_conflict: str = "replace",
        extra_metadata: Optional[Mapping[str, Any]] = None,
    ) -> CombinedResult:
        """Run one pipeline over many sources and optionally persist each cut flow."""
        per_sample: List[SampleResult] = []
        sum_cutflow: Dict[str, float | int] = {}

        for name, source in named_sources:
            if store or results_db is not None or analysis_name != "default" or on_conflict != "replace" or extra_metadata:
                res = self.pipeline.run(
                    source,
                    sel_cfg,
                    run_cfg,
                    store=store,
                    results_db=results_db,
                    analysis_name=analysis_name,
                    on_conflict=on_conflict,
                    extra_metadata=extra_metadata,
                )
            else:
                # Preserve compatibility with lightweight/custom pipelines that
                # implement the original three-argument run() contract.
                res = self.pipeline.run(source, sel_cfg, run_cfg)
            sample = SampleResult(
                name=name,
                cutFlow=res.get("cutFlow", {}),
                finalDF=res.get("finalDF", pd.DataFrame()),
                details={k: v for k, v in res.items() if k not in {"cutFlow", "finalDF"}},
            )
            per_sample.append(sample)

            for k, v in sample.cutFlow.items():
                if isinstance(v, (int, float)):
                    sum_cutflow[k] = sum_cutflow.get(k, 0) + v

        return CombinedResult(per_sample=per_sample, cutflow_sum=sum_cutflow)
