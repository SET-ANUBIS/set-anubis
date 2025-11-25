from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface
from SetAnubis.core.Common.MultiSet import MultiSet
from pathlib import Path
import yaml
import json
from typing import Dict
from functools import lru_cache

def decay_name(mother : int, daugthers : MultiSet, nsa : SetAnubisInterface, mapping : dict):
    """Génère un nom de fichier basé sur la mère et les filles (ex: b_c_cbar). mapping est utilisé pour passer 
    de la db ufo à la db Marty."""
    if isinstance(mother, list):
        mother_names = [str(abs(m)) for m in mother]
    else:
        mother_names = [str(abs(mother))]
        
    daugther_names = [str(abs(d)) for d in daugthers]
    
    return "_".join(mother_names + ["s"] + daugther_names)



@lru_cache(maxsize=2)
def _load_ufo_mappings(reversed: bool) -> Dict[str, str]:
    base_path = Path(__file__).resolve()
    for _ in range(6):
        base_path = base_path.parent
    assets_path = base_path / "Assets" / "MARTY" / "model"

    json_file = assets_path / "conversion_sm.json"
    yaml_file = assets_path / "conversion_model.yaml"
    mapping = {}

    if json_file.exists():
        with open(json_file, "r") as f:
            data = json.load(f)
            mapping.update({entry["name"]: entry["ufo_name"]
                            for entry in data if "name" in entry and "ufo_name" in entry})

    if yaml_file.exists():
        with open(yaml_file, "r") as f:
            data = yaml.safe_load(f)
            if data:
                mapping.update({entry["name"]: entry["ufo_name"]
                                for entry in data if "name" in entry and "ufo_name" in entry})
    
    if reversed:
        return {v: k for k, v in mapping.items()}
    return mapping

def load_ufo_mappings(reversed: bool = False) -> Dict[str, str]:
    return _load_ufo_mappings(reversed)


@lru_cache(maxsize=2)
def _load_particle_mappings(reversed: bool) -> Dict[str, str]:
    base_path = Path(__file__).resolve()
    for _ in range(6):
        base_path = base_path.parent
    assets_path = base_path / "Assets" / "MARTY" / "model"

    json_file = assets_path / "sm_particle.json"
    yaml_file = assets_path / "model_particle.yaml"
    mapping = {}

    if json_file.exists():
        with open(json_file, "r") as f:
            data = json.load(f)
            mapping.update({entry["pdg_code"]: entry["name"]
                            for entry in data if "pdg_code" in entry and "name" in entry})

    if yaml_file.exists():
        with open(yaml_file, "r") as f:
            data = yaml.safe_load(f)
            if data:
                mapping.update({entry["pdg_code"]: entry["name"]
                                for entry in data if "pdg_code" in entry and "name" in entry})
    
    if reversed:
        return {v: k for k, v in mapping.items()}
    return mapping

def load_particle_mappings(reversed: bool = False) -> Dict[str, str]:
    return _load_particle_mappings(reversed)

