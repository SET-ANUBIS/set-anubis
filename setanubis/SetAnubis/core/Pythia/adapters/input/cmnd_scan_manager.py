import itertools
import os
from typing import List, Dict, Any, Tuple
from pathlib import Path
from SetAnubis.core.Pythia.adapters.input.pythia_cmnd_interface import PythiaCMNDInterface
from SetAnubis.core.Pythia.infrastructure.enums import AbstractEnumProduction
from SetAnubis.core.BranchingRatio.adapters.input.DecayInterface import DecayInterface
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface
from SetAnubis.core.Pythia.domain.special_cases import Specials, GeneralParams, GeneralType
from SetAnubis.core.Common.MultiSet import MultiSet

class CMNDScanManager:
    """
    Interface to generate CMND cards from a scan over NeoSetAnubis parameters.
    """

    def __init__(self, nsa : SetAnubisInterface, decay_interface : DecayInterface, output_dir: str):
        self.nsa = nsa  # NeoSetAnubisInterface
        self.dm = decay_interface  # DecayInterface
        self.output_dir = Path(output_dir)
        self.scan_params: Dict[str, List[Any]] = {}
        self.new_particles: List[int] = []
        self.sm_changes: List[tuple] = []  # [(pdg_list, file_path)]
        self.decay_from_bsm: List[int] = []
        self.decay_to_bsm: List[int] = []
        self.production_channel: AbstractEnumProduction = None
        self.specials : Dict[Specials,Dict[Any, Any]] = {}
        self.general_modif : Dict[Tuple[GeneralType, GeneralParams],Any] = {}

    def register_scan(self, param: str, values: List[float]):
        self.scan_params[param] = values

    def set_new_particle(self, pdg_id: int):
        self.new_particles.append(pdg_id)

    def set_sm_changes(self, pdg_ids: List[int], file_path: str):
        self.sm_changes.append((pdg_ids, Path(file_path)))

    def add_decay_from_bsm(self, pdg_id: int):
        self.decay_from_bsm.append(pdg_id)

    def add_decay_to_bsm(self, pdg_id: int):
        self.decay_to_bsm.append(pdg_id)

    def set_production(self, production_enum: AbstractEnumProduction):
        self.production_channel = production_enum

    def special_changes(self,spec : Specials, cases : Dict[Any, Any]):
        self.specials[spec] = cases

    def general_changes(self, generaltype : GeneralType, generalparam : GeneralParams, value):
        self.general_modif[(generaltype, generalparam)] = value

    def generate_all_cmnds(self):
        os.makedirs(self.output_dir, exist_ok=True)
        keys = list(self.scan_params.keys())
        combinations = list(itertools.product(*[self.scan_params[k] for k in keys]))

        print(f"🔁 Generating {len(combinations)} CMND files in {self.output_dir}")

        for combo in combinations:
            param_values = dict(zip(keys, combo))
            for k, v in param_values.items():
                self.nsa.set_leaf_param(k, v)
                self.dm.nsa = self.nsa
            suffix = "_".join(f"{k}{str(v).replace('.', 'p')}" for k, v in param_values.items())
            cmnd_name = f"scan_{suffix}.cmnd"
            cmnd_path = self.output_dir / cmnd_name

            # Setup CMND
            interface = PythiaCMNDInterface(self.nsa, self.dm)

            for (gentype, genparam), val in self.general_modif.items():
                interface.add_general_changes(gentype, genparam, val)

            for spec, val in self.specials.items():
                interface.special_change(spec, val)

            for pdg in self.new_particles:
                interface.add_new_particles([pdg])
            for pdg_ids, file_path in self.sm_changes:
                interface.change_sm_particles(pdg_ids, file_path)
            for pdg in self.decay_from_bsm:
                interface.add_decay_from_bsm_particles(pdg)
            for pdg in self.decay_to_bsm:
                interface.add_decay_to_bsm_particles(pdg)
            if self.production_channel:
                interface.add_hard_production(self.production_channel)

            # Write to file
            with open(cmnd_path, "w") as f:
                f.write(interface.serialize())

        print(f"✅ CMND generation complete. Files in: {self.output_dir}")
