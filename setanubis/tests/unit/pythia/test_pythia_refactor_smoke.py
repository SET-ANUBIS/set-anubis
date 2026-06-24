from SetAnubis.examples.Pythia.main_test_pythia_refactor import (
    assert_cmnd_is_generic,
    build_generic_cmnd,
)
from SetAnubis.core.Pythia.adapters.input.PythiaRunInterface import PythiaRunInterface


def test_generic_cmnd_generation_has_no_hardcoded_hnl_pid():
    pid = 42
    cmnd = build_generic_cmnd(pid)
    assert_cmnd_is_generic(cmnd, pid)


def test_pythia_run_interface_imports_without_compiled_binding(tmp_path):
    runner = PythiaRunInterface(str(tmp_path), new_particles=[42])
    diagnostic = runner.check_runtime()
    assert "available" in diagnostic
    assert diagnostic["available"] in {True, False}
