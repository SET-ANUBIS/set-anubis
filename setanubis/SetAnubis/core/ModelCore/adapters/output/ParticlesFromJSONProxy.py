from __future__ import annotations
from typing import Dict, Any, Mapping, Optional
from SetAnubis.core.DataBase.ports.IExtractor import IExtractor
from SetAnubis.core.ModelCore.ports.output.IParticleJSONProxy import IParticleJSONProxy

class ParticlesFromJSONProxy(IParticleJSONProxy) : 
    """
    Proxy qui enrichit un catalogue de particules existant avec des entrées
    provenant d'une source JSON via un IExtractor. N'ajoute que les PDG manquants.
    """

    def __init__(
        self,
        base_particles: Mapping[int, Dict[str, Any]],
        extractor: IExtractor,
        json_path: str,
        *,
        mass_scale: float = 1.0, 
        mass_as_complex: bool = True,
    ) -> None:
        self._base = dict(base_particles)
        self._extractor = extractor
        self._json_path = json_path
        self._mass_scale = mass_scale
        self._mass_as_complex = mass_as_complex

    def get_all_particles(self) -> Dict[int, Dict[str, Any]]:
        """Return merged dictionnary PDG -> props."""
        extra = self._safe_extract()
        merged = dict(self._base)

        for key, payload in extra.items():
            try:
                pdg = int(key)
            except (TypeError, ValueError):
                continue

            if pdg in merged:
                continue

            merged[pdg] = self._normalize_payload(pdg, payload)

        return merged

    # --- intern ---

    def _safe_extract(self) -> Dict[str, Any]:
        data = self._extractor.extract(self._json_path)
        return data if isinstance(data, dict) else {}

    def _normalize_payload(self, pdg: int, raw: Mapping[str, Any]) -> Dict[str, Any]:
        """
        JSON Scheme normalized with manager needs:
        Normalise le schéma du JSON vers celui attendu par ton manager.
        {
          "1": {"name": "d", "antiName": "dbar", "spin": 2.0, "charge": -0.333..., "colour": 1.0, "mass": 0.33},
          ...
        }
        """
        name = raw.get("name", "")
        antiname = raw.get("antiname", raw.get("antiName", ""))
        spin = raw.get("spin", None)
        spin_int: Optional[int] = int(spin) if spin is not None else None

        charge = raw.get("charge", 0.0)
        mass_val = raw.get("mass", 0.0)

        mass_val = (mass_val or 0.0) * self._mass_scale
        mass = complex(mass_val) if self._mass_as_complex else mass_val

        particle: Dict[str, Any] = {
            "name": name,
            "antiname": antiname,
            "spin": spin_int,
            "charge": charge,
            "pdg_code": pdg,
            "mass": mass,
        }

        for extra_key in ("colour", "color", "lha_block", "lha_code"):
            if extra_key in raw:
                particle[extra_key] = raw[extra_key]

        return particle
