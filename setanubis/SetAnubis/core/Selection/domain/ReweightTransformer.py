from __future__ import annotations
from dataclasses import dataclass, replace
from typing import Dict, List, Optional, Protocol, Iterable, Tuple
import ast
import numpy as np
import pandas as pd


class PhysicsConstants:
    # m/s
    C = 299_792_458.0
    # mm per meter
    MM_PER_M = 1000.0




def _parse_fourvec(x) -> Tuple[float, float, float, float]:
    """FourVector needed (x,y,z,t). If str '(...)', parsing"""
    if isinstance(x, tuple) and len(x) == 4:
        return x 
    if isinstance(x, list) and len(x) == 4:
        return tuple(x)
    if isinstance(x, str):
        try:
            v = ast.literal_eval(x)
            if isinstance(v, (list, tuple)) and len(v) == 4:
                return tuple(float(z) for z in v)
        except Exception:
            pass
    # fallback 4-tuple with zeros
    return (0.0, 0.0, 0.0, 0.0)


def _add_fourvec(a: Tuple[float, float, float, float],
                 b: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2], a[3] + b[3])



@dataclass(frozen=True)
class DataBundle:
    """
    Not mutable contener for df producted by analyzer.
    """
    finalStates: pd.DataFrame
    LLPs: pd.DataFrame
    LLPchildren: pd.DataFrame
    finalStates_NoLLP: pd.DataFrame
    finalStates_Neutrinos: pd.DataFrame
    chargedFinalStates: pd.DataFrame
    neutralFinalStates: pd.DataFrame

    @staticmethod
    def from_dict(d: Dict[str, pd.DataFrame]) -> "DataBundle":
        # Copy to avoid mutability
        return DataBundle(**{k: v.copy() for k, v in d.items()})

    def to_dict(self) -> Dict[str, pd.DataFrame]:
        # Defensive copy.
        return {
            "finalStates": self.finalStates.copy(),
            "LLPs": self.LLPs.copy(),
            "LLPchildren": self.LLPchildren.copy(),
            "finalStates_NoLLP": self.finalStates_NoLLP.copy(),
            "finalStates_Neutrinos": self.finalStates_Neutrinos.copy(),
            "chargedFinalStates": self.chargedFinalStates.copy(),
            "neutralFinalStates": self.neutralFinalStates.copy(),
        }


#Random service (DIP)
class RandomProvider:
    """
    Injected RNG service (avoid global state from numpy)
    Service RNG injecté (au lieu d'utiliser l'état global numpy).
    """
    def __init__(self, seed: Optional[int | str] = None) -> None:
        # string → hash stable
        if seed is None or seed == "":
            self._rng = np.random.default_rng()
        else:
            # if string, derive an 64 bits int.
            if isinstance(seed, str):
                seed_val = np.uint64(abs(hash(seed)) & ((1 << 63) - 1))
            else:
                seed_val = seed
            self._rng = np.random.default_rng(seed_val)

    @property
    def rng(self) -> np.random.Generator:
        return self._rng


# Strategy: reweight kernels (OCP/LSP)
class ReweightKernel(Protocol):
    """
    reweight strategy : calculate a distance vertex (mm) for every LLps rows.
    """
    name: str

    def sample_decay_length_mm(self, df_llp: pd.DataFrame, lifetime_s: float,
                               rng: np.random.Generator) -> np.ndarray:
        ...


class LifetimeKernel:
    """
    Éq. 49.14 (PDG 2022) — legacy from Paul:
    np.random.exponential(scale = lifetime * gamma) * beta * c * 1000  [mm]
    """
    name = "weighted"

    def sample_decay_length_mm(self, df_llp: pd.DataFrame, lifetime_s: float,
                               rng_ignored: np.random.Generator | None) -> np.ndarray:
        gamma = df_llp["boost"].to_numpy(dtype=float, copy=False)
        beta  = df_llp["beta"].to_numpy(dtype=float, copy=False)
        #  [s]
        t_lab = np.random.exponential(scale=lifetime_s * gamma, size=gamma.shape)
        # mm
        L_mm = t_lab * beta * PhysicsConstants.C * PhysicsConstants.MM_PER_M
        return L_mm.astype(float)


class PositionKernel:
    """
    Éq. 49.15 (PDG 2022) — legacy from Paul:
    np.random.exponential(scale = lifetime * gamma * beta * c) * 1000  [mm]
    (directly in mm)
    """
    name = "posWeighted"

    def sample_decay_length_mm(self, df_llp: pd.DataFrame, lifetime_s: float,
                               rng_ignored: np.random.Generator | None) -> np.ndarray:
        gamma = df_llp["boost"].to_numpy(dtype=float, copy=False)
        beta  = df_llp["beta"].to_numpy(dtype=float, copy=False)
        scale_L_mm = lifetime_s * gamma * beta * PhysicsConstants.C * PhysicsConstants.MM_PER_M
        L_mm = np.random.exponential(scale=scale_L_mm, size=gamma.shape)
        return L_mm.astype(float)


class RestLifetimeKernel:
    """
    Legacy "rest": np.random.exponential(scale = lifetime) [s] and boost:
    L_mm = t_rest * gamma * beta * c * 1000
    """
    name = "restWeighted"

    def sample_decay_length_mm(self, df_llp: pd.DataFrame, lifetime_s: float,
                               rng_ignored: np.random.Generator | None) -> np.ndarray:
        gamma = df_llp["boost"].to_numpy(dtype=float, copy=False)
        beta  = df_llp["beta"].to_numpy(dtype=float, copy=False)
        t_rest = np.random.exponential(scale=lifetime_s, size=gamma.shape)
        L_mm = t_rest * gamma * beta * PhysicsConstants.C * PhysicsConstants.MM_PER_M
        return L_mm.astype(float)


# Transformer (SRP)
def to_theta(eta): # Theta is polar angle [0,pi] where 0 is aligned with the +ve z axis
    if eta == np.nan:
        return 0 # When pseudorapidity is undefined aligned with longitudinal axis (z)
    elif eta == -np.nan:
        return np.pi
    else:
        return 2 * np.arctan(np.exp(-eta))

def _to_cartesian(r: float, eta: float, phi: float):
    """
    - Input: distance L in mm, pseudo-rapidity eta, azimuth phi (rad)
    - Output: (x,y,z) in mm
    Stables relations:
      cosθ = tanh(eta)
      sinθ = 1/cosh(eta)
    """
    x = r * np.sin(to_theta(eta)) * np.cos(phi)
    y = r * np.sin(to_theta(eta)) * np.sin(phi)
    z = r * np.cos(to_theta(eta))
    return [x, y, z]


def _get_reweighted_decay_position_row(row: pd.Series, dist_col: str):
    """
    Return a tuple (x,y,z) in mm (without 't', Paul doesn't use it for translation).
    """
    L = row[dist_col]
    eta = row["eta"]
    phi = row["phi"]
    return _to_cartesian(L, eta, phi)

class Transformer(Protocol):
    def apply(self, bundle: DataBundle) -> DataBundle:
        ...


class ReweightDecayPositions(Transformer):
    """
    Apply a reweight of position and desintegration for LLPs and propagate translation to the desintegration products (LLPchildren).
    Add for deach kernel columns decayVertexDist_<name>, decayVertex_<name>, ctau_<name>
    Add decayVertex_translation (4-vector, Δx,Δy,Δz,0)
    Add in LLPchildren:
        prodVertex_<name>, decayVertex_<name>
    """
    def __init__(
        self,
        lifetime_s: float,
        llp_pid: int,
        rng: Optional[RandomProvider] = None,
        kernels: Optional[Iterable[ReweightKernel]] = None,
        seed_for_compat = None
    ) -> None:
        self.lifetime_s = float(lifetime_s)
        self.llp_pid = int(llp_pid)
        self.rng = rng.rng if isinstance(rng, RandomProvider) else RandomProvider().rng
        self.kernels: List[ReweightKernel] = list(kernels) if kernels is not None else [
            LifetimeKernel(), PositionKernel(), RestLifetimeKernel()
        ]
        self.seed_for_compat = seed_for_compat

    @staticmethod
    def _ensure_fourvectors(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
        out = df.copy()
        for c in cols:
            if c in out.columns:
                out[c] = out[c].map(_parse_fourvec)
        return out

    @staticmethod
    def _build_translation(original: pd.Series, reweighted_xyz: pd.Series) -> pd.Series:
        """
        Δ = reweighted_xyz( x,y,z ) - original( x,y,z ) ; Δt = 0
        - original : 4-vector (x,y,z,t) (legacy from Paul)
        - reweighted_xyz : 3-vector (x,y,z) (legacy from Paul)
        """

        def _to_xyz3(v):
            # v can be (x,y,z), (x,y,z,t) or str with the same form
            if isinstance(v, (list, tuple)):
                if len(v) == 3:
                    x, y, z = v
                    return float(x), float(y), float(z)
                if len(v) == 4:
                    x, y, z, _t = v
                    return float(x), float(y), float(z)
            if isinstance(v, str):
                try:
                    vv = ast.literal_eval(v)
                    return _to_xyz3(vv)
                except Exception:
                    pass
            # fallback
            return 0.0, 0.0, 0.0

        def _to_xyzt4(v):
            if isinstance(v, (list, tuple)):
                if len(v) == 4:
                    x, y, z, t = v
                    return float(x), float(y), float(z), float(t)
                if len(v) == 3:
                    x, y, z = v
                    return float(x), float(y), float(z), 0.0
            if isinstance(v, str):
                try:
                    vv = ast.literal_eval(v)
                    return _to_xyzt4(vv)
                except Exception:
                    pass
            return 0.0, 0.0, 0.0, 0.0

        def _delta(a4, b3):
            ax, ay, az, _at = _to_xyzt4(a4)
            bx, by, bz = _to_xyz3(b3)
            return (bx - ax, by - ay, bz - az, 0.0)

        return pd.Series((_delta(a, b) for a, b in zip(original, reweighted_xyz)),
                        index=original.index)

    @staticmethod
    def _translate_vertex(row: pd.Series, vertex_col: str, translation: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
        """
        if (final state or status==1) and decayvertex traduction then (-1,-1,-1,-1)
        else vertex + translation (4-vector sum).
        """
        if ( ((row.get("nChildren", 0) == 0) or (row.get("status", 0) == 1)) and ("prodVertex" not in vertex_col) ):
            return (-1.0, -1.0, -1.0, -1.0)
        v = _parse_fourvec(row[vertex_col])
        return _add_fourvec(v, translation)


    def apply(self, bundle: DataBundle) -> DataBundle:
        llps = bundle.LLPs.copy()
        children = bundle.LLPchildren.copy()

        if self.seed_for_compat is not None and self.seed_for_compat != "":
            try:
                s = int(self.seed_for_compat)
            except ValueError:
                import hashlib
                s = int(hashlib.sha256(str(self.seed_for_compat).encode("utf-8")).hexdigest()[:16], 16)
            np.random.seed(s)
    
        #if multiple pid.
        mask_pid = (llps["PID"].astype(int) == self.llp_pid)

        llps = self._ensure_fourvectors(llps, ["decayVertex"])
        children = self._ensure_fourvectors(children, ["prodVertex", "decayVertex"])

        for kernel in self.kernels:
            name = kernel.name  # "weighted", "posWeighted", "restWeighted"

            # Distances (mm) only for target pid
            dist = np.zeros(len(llps), dtype=float)
            if mask_pid.any():
                dist[mask_pid.to_numpy()] = kernel.sample_decay_length_mm(
                    llps.loc[mask_pid], self.lifetime_s, self.rng
                )

            col_dist = f"decayVertexDist_{name}"
            col_ctau = f"ctau_{name}"
            llps[col_dist] = dist
            # ctau in s : L(mm) / (γβ c (mm/s))
            gamma = llps["boost"].to_numpy(dtype=float, copy=False)
            beta = llps["beta"].to_numpy(dtype=float, copy=False)
            denom = np.maximum(gamma * beta, 1e-300)
            llps[col_ctau] = llps[col_dist].to_numpy() / denom

            llps[f"decayVertex_{name}"] = [
                _get_reweighted_decay_position_row(row, col_dist) for _, row in llps.iterrows()
            ]

        # Principal vector for translation based on the kernel “weighted”
        # Δ = decayVertex_weighted - decayVertex ; Δt = 0
        if "decayVertex_weighted" not in llps.columns:
            raise RuntimeError("Kernel 'weighted' needed for decayVertex_translation.")
        llps["decayVertex_translation"] = self._build_translation(llps["decayVertex"], llps["decayVertex_weighted"])

        # Propagation to children
        if "LLPindex" not in children.columns:
            raise ValueError("LLPchildren needs the columns 'LLPindex'.")

        child = children.merge(
            llps[["decayVertex_translation"]], how="left",
            left_on="LLPindex", right_index=True, validate="many_to_one"
        )

        for kernel in self.kernels:
            name = kernel.name

            # prodVertex_<name>
            tgt_col = f"prodVertex_{name}"
            child[tgt_col] = [
                self._translate_vertex(row, "prodVertex", row["decayVertex_translation"])
                for _, row in child.iterrows()
            ]

            # decayVertex_<name>
            tgt_col2 = f"decayVertex_{name}"
            child[tgt_col2] = [
                self._translate_vertex(row, "decayVertex", row["decayVertex_translation"])
                for _, row in child.iterrows()
            ]

        return replace(bundle, LLPs=llps, LLPchildren=child.drop(columns=["decayVertex_translation"]))


if __name__ == "__main__":
    # analyzer = LLPAnalyzer(df, pt_min_cfg={"chargedTrack": 0.5})
    # dict_out = analyzer.create_sample_dataframes(llpid=21)
    from write_and_load_selection_dict import load_bundle, save_bundle
    
    dict_out = load_bundle("paul_dict.pkl.gz")
    
    bundle = DataBundle.from_dict(dict_out)

    transform = ReweightDecayPositions(
        lifetime_s=1.0e-10,
        llp_pid=9900012,
        rng=RandomProvider(seed=42)
    )

    bundle2 = transform.apply(bundle)
    dict_out2 = bundle2.to_dict()

    LLPs_new = dict_out2["LLPs"]
    LLPchildren_new = dict_out2["LLPchildren"]