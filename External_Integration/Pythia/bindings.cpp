#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "EventGeneratorFactory.h"

namespace py = pybind11;

PYBIND11_MODULE(pythia_sim, m) {
    m.doc() = "Pythia Simulation Module";

    py::class_<EventGenerator, std::shared_ptr<EventGenerator>>(m, "EventGenerator")
        .def("generate_events", &EventGenerator::generateEvents,
             py::arg("bsm_ids") = std::vector<int>{});

    m.def("create_pythia_generator", &EventGeneratorFactory::createPythiaGenerator,
          py::return_value_policy::automatic,
          py::arg("inFile"), py::arg("outFileNameLHE"), py::arg("outFileNameHepMC"),
          py::arg("outFileNameTxt"), py::arg("suffix"), py::arg("totalEvents"),
          "Create a Pythia Event Generator");
}
