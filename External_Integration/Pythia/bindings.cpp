#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <map>
#include <string>
#include "EventGeneratorFactory.h"

namespace py = pybind11;

#ifndef SETANUBIS_PYTHIA8_PREFIX
#define SETANUBIS_PYTHIA8_PREFIX "unknown"
#endif
#ifndef SETANUBIS_HEPMC3_PREFIX
#define SETANUBIS_HEPMC3_PREFIX "unknown"
#endif


PYBIND11_MODULE(pythia_sim, m) {
    m.doc() = "SetAnubis optional Pythia8/HepMC3 simulation binding";

    m.def("get_build_info", []() {
        return std::map<std::string, std::string>{
            {"pythia8_prefix", SETANUBIS_PYTHIA8_PREFIX},
            {"hepmc3_prefix", SETANUBIS_HEPMC3_PREFIX},
            {"cxx_standard", "C++14"}
        };
    }, "Return build-time paths for the optional native binding");

    py::class_<ParticleHardCut>(m, "ParticleHardCut")
        .def(py::init<>())
        .def_readwrite("pdg_id", &ParticleHardCut::pdgId)
        .def_readwrite("use_abs_id", &ParticleHardCut::useAbsId)
        .def_readwrite("final_only", &ParticleHardCut::finalOnly)
        .def_readwrite("min_pt", &ParticleHardCut::minPt)
        .def_readwrite("max_pt", &ParticleHardCut::maxPt)
        .def_readwrite("min_eta", &ParticleHardCut::minEta)
        .def_readwrite("max_eta", &ParticleHardCut::maxEta)
        .def_readwrite("min_energy", &ParticleHardCut::minEnergy)
        .def_readwrite("max_energy", &ParticleHardCut::maxEnergy)
        .def_readwrite("min_count", &ParticleHardCut::minCount)
        .def_readwrite("max_count", &ParticleHardCut::maxCount);

    py::class_<PythiaRunOptions>(m, "PythiaRunOptions")
        .def(py::init<>())
        .def_readwrite("settings", &PythiaRunOptions::settings)
        .def_readwrite("lifetimes", &PythiaRunOptions::lifetimes)
        .def_readwrite("widths", &PythiaRunOptions::widths)
        .def_readwrite("hard_cuts", &PythiaRunOptions::hardCuts)
        .def_readwrite("require_all_cuts", &PythiaRunOptions::requireAllCuts)
        .def_readwrite("max_trials", &PythiaRunOptions::maxTrials)
        .def_readwrite("fix_decay_masses", &PythiaRunOptions::fixDecayMasses);

    py::class_<EventGenerator, std::shared_ptr<EventGenerator>>(m, "EventGenerator")
        .def("generate_events", &EventGenerator::generateEvents,
             py::arg("particle_ids") = std::vector<int>{},
             py::arg("options") = PythiaRunOptions());

    m.def("create_pythia_generator", &EventGeneratorFactory::createPythiaGenerator,
          py::return_value_policy::automatic,
          py::arg("inFile"), py::arg("outFileNameLHE"), py::arg("outFileNameHepMC"),
          py::arg("outFileNameTxt"), py::arg("suffix"), py::arg("totalEvents"),
          "Create a Pythia Event Generator");
}
