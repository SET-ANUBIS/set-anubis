from SetAnubis.examples.Pythia.dev_examples.main_test_pythia_refactor import (
    assert_cmnd_is_generic,
    build_generic_cmnd,
)
from SetAnubis.core.Pythia.adapters.input.PythiaRunInterface import PythiaRunInterface
from SetAnubis.examples.Pythia.example_pythia_cmnd import build_cmnd as build_hnl_example_cmnd


def test_generic_cmnd_generation_has_no_hardcoded_hnl_pid():
    pid = 42
    cmnd = build_generic_cmnd(pid)
    assert_cmnd_is_generic(cmnd, pid)


def test_pythia_run_interface_imports_without_compiled_binding(tmp_path):
    runner = PythiaRunInterface(str(tmp_path), new_particles=[42])
    diagnostic = runner.check_runtime()
    assert "available" in diagnostic
    assert diagnostic["available"] in {True, False}


def test_packaged_hnl_example_builds_complete_cmnd_without_running_pythia():
    cmnd = build_hnl_example_cmnd()
    assert "9900012:new N1 N1" in cmnd
    assert "4132:addChannel" in cmnd
    assert "9900012:addChannel" in cmnd
    assert "HardQCD::hardccbar = on" in cmnd
