from SetAnubis.core.Pythia.adapters.input.pythia_run_interface import PythiaRunInterface
import os

if __name__ == "__main__":
    py_interface = PythiaRunInterface(os.path.join(os.path.dirname(__file__), "outputs"))

    output_lhe, output_hepmc = py_interface.ensure_directories(["lhe", "hepmc"])
    py_interface.process_file(
        config_file=os.path.join(os.path.dirname(__file__), "TestFiles", "test.cmnd"),
        output_lhe_dir=output_lhe,
        output_hepmc_dir=output_hepmc,
        num_events=2000,
        suffix="test",
        include_time=True
    )