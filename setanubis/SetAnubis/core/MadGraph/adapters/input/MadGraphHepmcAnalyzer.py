from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Protocol, Optional, Dict, List

from collections import Counter
import numpy as np


class EventSource(Protocol):
    """MinimalInterface for a HEPMC event source."""
    def __iter__(self) -> Iterable["hp.GenEvent"]:
        ...


class ParticlePlotter(Protocol):
    """Plotters interface."""
    def plot_kinematics(self, stats: "ParticleStats", bins: int = 50) -> None:
        ...

    def plot_relations(self, stats: "ParticleStats", top_n: int = 10) -> None:
        ...


@dataclass
class HepMCFileSource:
    """
    Event source based on pyhepmc.open()

    path: path to the .hepmc file (HepMC2/3 ASCII, éventuellement .gz, .bz2, .xz)
    """

    path: str

    def __iter__(self) -> Iterable["hp.GenEvent"]:
        import pyhepmc as hp  # local import to lower coupling
        with hp.open(self.path) as f:
            for event in f:
                yield event


@dataclass
class ParticleStats:
    """
    Aggregate all informations for a given particle (pdg id)
    """

    pdg_id: int

    energies: List[float] = field(default_factory=list)
    pts: List[float] = field(default_factory=list)
    etas: List[float] = field(default_factory=list)
    phis: List[float] = field(default_factory=list)
    thetas: List[float] = field(default_factory=list)

    parent_counts: Counter[int] = field(default_factory=Counter)
    child_counts: Counter[int] = field(default_factory=Counter)

    n_events: int = 0
    n_events_with_particle: int = 0
    n_particles: int = 0

    momentum_unit: Optional[str] = None


    def register_event(self, has_particle: bool, event_momentum_unit: Optional[str]) -> None:
        self.n_events += 1
        if has_particle:
            self.n_events_with_particle += 1
        if self.momentum_unit is None and event_momentum_unit is not None:
            self.momentum_unit = event_momentum_unit

    def add_particle(self, p: "hp.GenParticle", ignore_self_decays: bool = True) -> None:
        self.n_particles += 1

        mom = p.momentum

        self.energies.append(mom.e)

        def _val(x):
            return x() if callable(x) else x

        pt    = _val(mom.pt)
        eta   = _val(mom.eta)
        phi   = _val(mom.phi)
        theta = _val(mom.theta)

        self.pts.append(float(pt))
        self.etas.append(float(eta))
        self.phis.append(float(phi))
        self.thetas.append(float(theta))

        for parent in p.parents:
            if ignore_self_decays and parent.pid == p.pid:
                continue
            self.parent_counts[parent.pid] += 1

        for child in p.children:
            if ignore_self_decays and child.pid == p.pid:
                continue
            self.child_counts[child.pid] += 1


    def _describe_array(self, values: List[float], name: str) -> str:
        if not values:
            return f"  {name:>8} : aucun point\n"
        print(values)
        arr = np.asarray(values, dtype=float)
        return (
            f"  {name:>8} : N={len(arr)}, "
            f"mean={arr.mean():.3g}, "
            f"std={arr.std(ddof=1):.3g}, "
            f"min={arr.min():.3g}, "
            f"max={arr.max():.3g}\n"
        )

    def _describe_counter(self, counter: Counter[int], name: str, top_n: int = 10) -> str:
        if not counter:
            return f"  {name}: aucun\n"
        lines = [f"  {name} (top {top_n}):"]
        for pdg, count in counter.most_common(top_n):
            lines.append(f"    PDG {pdg:>8} : {count}")
        return "\n".join(lines) + "\n"

    def summary(self) -> str:
        """Résumé humainement lisible."""
        if self.n_events == 0:
            return " No event analyzed."

        frac_events = (
            self.n_events_with_particle / self.n_events if self.n_events > 0 else 0.0
        )
        mult_per_event = (
            self.n_particles / self.n_events_with_particle
            if self.n_events_with_particle > 0
            else 0.0
        )

        unit = self.momentum_unit or "unknown-unit"
        s = []
        s.append(f"=== Analyze for PDG {self.pdg_id} ===")
        s.append(f"Analyzed events       : {self.n_events}")
        s.append(f"Events with ≥1 particles    : {self.n_events_with_particle}"
                 f" ({frac_events*100:.2f} %)")
        s.append(f"Total number of particles: {self.n_particles}")
        s.append(f"Multiplicity mean/event (conditioned) : {mult_per_event:.3g}")
        s.append(f"Momentum Unit (HepMC)       : {unit}")
        s.append("")
        s.append("Kinematics distributions :")
        s.append(self._describe_array(self.energies, f"E [{unit}]"))
        s.append(self._describe_array(self.pts, f"pT [{unit}]"))
        s.append(self._describe_array(self.etas, "eta"))
        s.append(self._describe_array(self.phis, "phi"))
        s.append(self._describe_array(self.thetas, "theta"))
        s.append("")
        s.append(self._describe_counter(self.parent_counts, "Mother particles"))
        s.append(self._describe_counter(self.child_counts, "Dauther particles"))
        return "\n".join(s)



class MatplotlibPlotter:
    """
    Simple plotter based on matplotlib

    Single Responsibility: Only vizualisation.
    """

    def plot_kinematics(self, stats: ParticleStats, bins: int = 50) -> None:
        import matplotlib.pyplot as plt

        if stats.n_particles == 0:
            print("Nothing to plot: No particle")
            return

        fig, axes = plt.subplots(2, 3, figsize=(14, 8))
        axes = axes.ravel()

        unit = stats.momentum_unit or "arb. unit"

        # E
        axes[0].hist(stats.energies, bins=bins, histtype="step")
        axes[0].set_xlabel(f"E [{unit}]")
        axes[0].set_ylabel("Entries")
        axes[0].set_title(f"Energy (PDG {stats.pdg_id})")

        # pT
        axes[1].hist(stats.pts, bins=bins, histtype="step")
        axes[1].set_xlabel(f"pT [{unit}]")
        axes[1].set_ylabel("Entries")
        axes[1].set_title("pT")

        # eta
        axes[2].hist(stats.etas, bins=bins, histtype="step")
        axes[2].set_xlabel("η")
        axes[2].set_ylabel("Entries")
        axes[2].set_title("Pseudorapidity")

        # phi
        axes[3].hist(stats.phis, bins=bins, histtype="step")
        axes[3].set_xlabel("φ [rad]")
        axes[3].set_ylabel("Entries")
        axes[3].set_title("Azimuthal angle")

        # theta
        axes[4].hist(stats.thetas, bins=bins, histtype="step")
        axes[4].set_xlabel("θ [rad]")
        axes[4].set_ylabel("Entries")
        axes[4].set_title("Polar angle")

        fig.delaxes(axes[5])

        fig.suptitle(f"Kinematics distributions for PDG {stats.pdg_id}")
        fig.tight_layout()
        plt.show()

    def plot_relations(self, stats: ParticleStats, top_n: int = 10) -> None:
        import matplotlib.pyplot as plt

        if not stats.parent_counts and not stats.child_counts:
            print("No relation mother/daugther to plot.")
            return

        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        if stats.parent_counts:
            parents = stats.parent_counts.most_common(top_n)
            pdgs, counts = zip(*parents)
            axes[0].bar(range(len(pdgs)), counts)
            axes[0].set_xticks(range(len(pdgs)))
            axes[0].set_xticklabels([str(p) for p in pdgs], rotation=45, ha="right")
            axes[0].set_ylabel("Occurrences")
            axes[0].set_title(f"Top {top_n} mothers of PDG {stats.pdg_id}")
        else:
            axes[0].text(0.5, 0.5, "No mother", ha="center", va="center")
            axes[0].set_axis_off()

        if stats.child_counts:
            children = stats.child_counts.most_common(top_n)
            pdgs, counts = zip(*children)
            axes[1].bar(range(len(pdgs)), counts)
            axes[1].set_xticks(range(len(pdgs)))
            axes[1].set_xticklabels([str(p) for p in pdgs], rotation=45, ha="right")
            axes[1].set_ylabel("Occurrences")
            axes[1].set_title(f"Top {top_n} daugther of PDG {stats.pdg_id}")
        else:
            axes[1].text(0.5, 0.5, "No dauther", ha="center", va="center")
            axes[1].set_axis_off()

        fig.tight_layout()
        plt.show()


@dataclass
class MadGraphHepmcAnalyzer:
    """
    HepMC analyzer, MadGraph oriented for a given PDG

    - Abstraction dependencies (EventSource, ParticlePlotter) -> Dependency Inversion
    - Open to extension (new plotters / new sources) -> Open/Closed
    - Every class has a single responsability -> Single Responsibility
    """

    source: EventSource
    plotter: ParticlePlotter = field(default_factory=MatplotlibPlotter)

    @classmethod
    def from_file(cls, path: str) -> "MadGraphHepmcAnalyzer":
        """Easy way to construct the analyzer from a HepMC file."""
        return cls(HepMCFileSource(path))

    def analyze(
        self,
        pdg_id: int,
        max_events: Optional[int] = None,
        status: Optional[int] = None,
        ignore_self_decays: bool = True,
    ) -> ParticleStats:
        """
        Analyze all events for a given PDG

        - pdg_id : PDG code of the particle (e.g: 9900012)
        - max_events : if not None, limit the number of read events
        - status : if not None, only keep particle with this code
        - ignore_self_decays : If True, we ignore mother/dauthter with same pdg ID (MadGraph case of particle -> particle)
        """
        import pyhepmc as hp

        stats = ParticleStats(pdg_id=pdg_id)

        for i_event, event in enumerate(self.source):
            try:
                unit_name = getattr(event.momentum_unit, "name", None)
            except AttributeError:
                unit_name = None

            has_particle = False

            for p in event.particles:
                if p.pid != pdg_id:
                    continue
                if status is not None and p.status != status:
                    continue

                has_particle = True
                stats.add_particle(p, ignore_self_decays=ignore_self_decays)

            stats.register_event(has_particle=has_particle, event_momentum_unit=unit_name)

            if max_events is not None and stats.n_events >= max_events:
                break

        return stats


    def summarize(
        self,
        pdg_id: int,
        max_events: Optional[int] = None,
        status: Optional[int] = None,
        ignore_self_decays: bool = True,
    ) -> str:
        """Analyze ten send a resume text."""
        stats = self.analyze(
            pdg_id,
            max_events=max_events,
            status=status,
            ignore_self_decays=ignore_self_decays,
        )
        return stats.summary()

    def plot_all(
        self,
        stats: ParticleStats,
        bins: int = 50,
        top_n_relations: int = 10,
    ) -> None:
        """Do all main plots."""
        self.plotter.plot_kinematics(stats, bins=bins)
        self.plotter.plot_relations(stats, top_n=top_n_relations)

if __name__ == "__main__":
    import os
    analyzer = MadGraphHepmcAnalyzer.from_file(os.path.join(os.path.dirname(__file__), "..", "..", "app", "TestFiles", "tag_1_pythia8_events.hepmc" ))

    stats = analyzer.analyze(
        pdg_id=35,
        max_events=None,  
        status=None, 
        ignore_self_decays=True, 
    )

    print(stats.summary())

    analyzer.plot_all(stats, bins=60, top_n_relations=15)