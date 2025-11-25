import os
import re
import numpy as np
import scipy.interpolate
import six
from typing import Dict, Set, Tuple
from SetAnubis.core.Common.MultiSet import MultiSet
from SetAnubis.core.BranchingRatio.domain.IDecayCalculation import IDecayCalculation

class HNLDecayBRCalculator(IDecayCalculation):
    def __init__(self):
        self.histograms = self._make_interpolators()
        self.decay_map = self._build_decay_map()

    def calculate(self, mother: int, daughters: MultiSet[int], parameters: Dict[str, float]) -> float:
        key = (mother, frozenset(daughters))
        decay_str = self.decay_map.get(key)
        return 1.0
        if decay_str is None:
            raise ValueError(f"No decay mapping for mother={mother} daughters={daughters}")

        interpolator = self.histograms.get(decay_str)
        if interpolator is None:
            raise ValueError(f"No interpolator found for decay '{decay_str}'")

        mass = parameters.get("mN1")["value"]
        if mass is None:
            raise ValueError("Parameter 'mN1' is required")
        return float(interpolator(float(mass.real)))

    def _make_interpolators(self, kind: str = "linear") -> Dict[str, scipy.interpolate.interp1d]:
        filepath = os.path.join(os.path.dirname(__file__), "N1_branchingratios.dat")
        histogram_data = self._parse_histograms(filepath)
        histograms = {}
        for hist_string, (masses, br) in six.iteritems(histogram_data):
            histograms[hist_string] = scipy.interpolate.interp1d(
                masses, br, kind=kind, bounds_error=False, fill_value=0, assume_sorted=True
            )
        return histograms

    def _parse_histograms(self, filepath: str) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
        with open(filepath, 'r') as f:
            lines = f.readlines()

        th1f_exp = re.compile(r'^TH1F\|.+')
        header_exp = re.compile(r'^TH1F\|(.+?)\|B(?:R|F)/U2(.+?)\|.+? mass \(GeV\)\|?')
        subheader_exp = re.compile(r'^\s*?(\d+?),\s*(\d+?\.\d+?),\s*(\d+\.\d+)\s*$')
        data_exp = re.compile(r'^\s*(\d+)\s*,\s*(\d+\.\d+)\s*$')

        header_line_idx = [i for i in range(len(lines)) if th1f_exp.match(lines[i]) is not None]

        histograms = {}
        for offset in header_line_idx:
            mh = header_exp.match(lines[offset])
            if mh is None or len(mh.groups()) != 2:
                raise ValueError(f"Malformed header: {lines[offset]}")

            decay_code = mh.group(1)
            ms = subheader_exp.match(lines[offset + 1])
            if ms is None or len(ms.groups()) != 3:
                raise ValueError(f"Malformed sub-header: {lines[offset + 1]}")

            npoints = int(ms.group(1))
            min_mass = float(ms.group(2))
            max_mass = float(ms.group(1))

            masses = np.linspace(min_mass, max_mass, npoints, endpoint=False)
            branching_ratios = np.zeros(npoints)

            for line in lines[offset + 2:offset + 1 + npoints]:
                md = data_exp.match(line)
                if md is None or len(md.groups()) != 2:
                    raise ValueError(f"Malformed data line: {line}")

                idx = int(md.group(1))
                br = float(md.group(2))
                branching_ratios[idx] = br

            histograms[decay_code] = (masses, branching_ratios)
        return histograms

    def _build_decay_map(self) -> Dict[Tuple[int, frozenset], str]:
        return {
            (15, frozenset([-11, 12, 9900012])): "tau_nu_e_bar_e",
            (15, frozenset([-13, 14, 9900012])): "tau_nu_mu_bar_mu",
            (15, frozenset([-11, 16, 9900012])): "tau_nu_tau_e",
            (15, frozenset([-13, 16, 9900012])): "tau_nu_tau_mu",
            (15, frozenset([-211, 9900012])): "tau_pi-",
            (15, frozenset([-321, 9900012])): "tau_K-",
            (15, frozenset([-213, 9900012])): "tau_rho-",
            (411, frozenset([-13, 9900012])): "d_mu",
            (411, frozenset([-11, 9900012])): "d_e",
            (411, frozenset([-15, 9900012])): "d_tau",
            (411, frozenset([-311, -11, 9900012])): "d_K0_e",
            (411, frozenset([-311, -13, 9900012])): "d_K0_mu",
            (411, frozenset([-313, -11, 9900012])): "d_K*bar0_e",
            (411, frozenset([-313, -13, 9900012])): "d_K*bar0_mu",
            (421, frozenset([-321, -11, 9900012])): "d0_K-_e",
            (421, frozenset([-323, -11, 9900012])): "d0_K*-_e",
            (421, frozenset([-321, -13, 9900012])): "d0_K-_mu",
            (421, frozenset([-323, -13, 9900012])): "d0_K*-_mu",
            (431, frozenset([-13, 9900012])): "ds_mu",
            (431, frozenset([-11, 9900012])): "ds_e",
            (431, frozenset([-15, 9900012])): "ds_tau",
            (431, frozenset([-11, 221, 9900012])): "ds_eta_e",
            (431, frozenset([-13, 221, 9900012])): "ds_eta_mu",
            (511, frozenset([-411, -11, 9900012])): "b0_D-_e",
            (511, frozenset([-413, -11, 9900012])): "b0_D*-_e",
            (511, frozenset([-411, -13, 9900012])): "b0_D-_mu",
            (511, frozenset([-413, -13, 9900012])): "b0_D*-_mu",
            (511, frozenset([-411, -15, 9900012])): "b0_D-_tau",
            (511, frozenset([-413, -15, 9900012])): "b0_D*-_tau",
            (511, frozenset([-211, -11, 9900012])): "b0_pi-_e",
            (511, frozenset([-211, -13, 9900012])): "b0_pi-_mu",
            (511, frozenset([-211, -15, 9900012])): "b0_pi-_tau",
            (511, frozenset([-213, -11, 9900012])): "b0_rho-_e",
            (511, frozenset([-213, -13, 9900012])): "b0_rho-_mu",
            (511, frozenset([-213, -15, 9900012])): "b0_rho-_tau",
            (521, frozenset([-15, 9900012])): "b_tau",
            (521, frozenset([-13, 9900012])): "b_mu",
            (521, frozenset([-11, 9900012])): "b_e",
            (521, frozenset([-11, 421, 9900012])): "b_D0_bar_e",
            (521, frozenset([-11, 423, 9900012])): "b_D*0_bar_e",
            (521, frozenset([-13, 421, 9900012])): "b_D0_bar_mu",
            (521, frozenset([-13, 423, 9900012])): "b_D*0_bar_mu",
            (521, frozenset([-15, 421, 9900012])): "b_D0_bar_tau",
            (521, frozenset([-15, 423, 9900012])): "b_D*0_bar_tau",
            (521, frozenset([-11, 111, 9900012])): "b_pi0_e",
            (521, frozenset([-13, 111, 9900012])): "b_pi0_mu",
            (521, frozenset([-15, 111, 9900012])): "b_pi0_tau",
            (521, frozenset([-11, 113, 9900012])): "b_rho0_e",
            (521, frozenset([-13, 113, 9900012])): "b_rho0_mu",
            (521, frozenset([-15, 113, 9900012])): "b_rho0_tau",
            (531, frozenset([-431, -11, 9900012])): "bs_D_s-_e",
            (531, frozenset([-433, -11, 9900012])): "bs_D*_s-_e",
            (531, frozenset([-431, -13, 9900012])): "bs_D_s-_mu",
            (531, frozenset([-433, -13, 9900012])): "bs_D*_s-_mu",
            (531, frozenset([-431, -15, 9900012])): "bs_D_s-_tau",
            (531, frozenset([-433, -15, 9900012])): "bs_D*_s-_tau",
            (531, frozenset([-321, -11, 9900012])): "bs_K-_e",
            (531, frozenset([-321, -13, 9900012])): "bs_K-_mu",
            (531, frozenset([-321, -15, 9900012])): "bs_K-_tau",
            (531, frozenset([-323, -11, 9900012])): "bs_K*-_e",
            (531, frozenset([-323, -13, 9900012])): "bs_K*-_mu",
            (531, frozenset([-323, -15, 9900012])): "bs_K*-_tau",
            (541, frozenset([-15, 9900012])): "bc_tau",
            (541, frozenset([-11, 9900012])): "bc_e",
            (541, frozenset([-11, 531, 9900012])): "bc_B_s0_e",
            (541, frozenset([-11, 511, 9900012])): "bc_B0_e",
            (541, frozenset([-11, 513, 9900012])): "bc_B*0_e",
            (541, frozenset([-11, 533, 9900012])): "bc_B*_s0_e",
            (541, frozenset([-13, 9900012])): "bc_mu",
            (541, frozenset([-13, 531, 9900012])): "bc_B_s0_mu",
            (541, frozenset([-13, 511, 9900012])): "bc_B0_mu",
            (541, frozenset([-13, 513, 9900012])): "bc_B*0_mu",
            (541, frozenset([-13, 533, 9900012])): "bc_B*_s0_mu",
            (4122, frozenset([-11, 3122, 9900012])): "lambdac_Lambda0_e",
            (4122, frozenset([-13, 3122, 9900012])): "lambdac_Lambda0_mu",
            (4132, frozenset([-11, 3312, 9900012])): "xic0_Xi-_e",
            (4132, frozenset([-13, 3312, 9900012])): "xic0_Xi-_mu",
            (5122, frozenset([11, 4122, 9900012])): "lambdab_Lambda_c+_e",
            (5122, frozenset([13, 4122, 9900012])): "lambdab_Lambda_c+_mu",
            (5122, frozenset([15, 4122, 9900012])): "lambdab_Lambda_c+_tau",
            (5232, frozenset([15, 9900012, 4232])): "Xib_Xi_c+_tau",
            (5232, frozenset([13, 9900012, 4232])): "Xib_Xi_c+_mu",
            (5232, frozenset([11, 9900012, 4232])): "Xib_Xi_c+_e",
            (5332, frozenset([15, 9900012])): "Omega_b-_tau",
            (5332, frozenset([13, 9900012])): "Omega_b-_mu",
            (5332, frozenset([11, 9900012])): "Omega_b-_e",
        }
        
        
if __name__ == "__main__":
    test = HNLDecayBRCalculator()
    
    print(test.calculate(4132, (-11, 3312, 9900012), {"mN1" : 0.5}))
