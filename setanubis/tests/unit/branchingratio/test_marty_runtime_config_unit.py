from pathlib import Path

import pytest

from SetAnubis.core.BranchingRatio.domain.MartyRuntimeConfig import (
    MartyPathConfig,
    resolve_marty_install,
)
from SetAnubis.core.BranchingRatio.domain.MartyUtil import load_particle_mappings


def _fake_install(tmp_path: Path) -> Path:
    prefix = tmp_path / "external" / "MARTY_INSTALL"
    (prefix / "include").mkdir(parents=True)
    (prefix / "lib").mkdir()
    (prefix / "include" / "marty.h").write_text("// stub\n", encoding="utf-8")
    (prefix / "lib" / "libmarty.a").write_bytes(b"")
    return prefix


def _mapping_dir(tmp_path: Path) -> Path:
    mapping = tmp_path / "mapping"
    mapping.mkdir()
    (mapping / "sm_particle.json").write_text(
        '[{"name":"e", "pdg_code":"11"}]', encoding="utf-8"
    )
    (mapping / "model_particle.yaml").write_text(
        '- name: N_2\n  pdg_code: "9900014"\n', encoding="utf-8"
    )
    (mapping / "conversion_sm.json").write_text("[]", encoding="utf-8")
    (mapping / "conversion_model.yaml").write_text("[]\n", encoding="utf-8")
    (mapping / "hnl.h").write_text("// HNL model\n", encoding="utf-8")
    return mapping


def test_custom_mapping_directory_can_supply_n2(tmp_path):
    mapping = _mapping_dir(tmp_path)
    loaded = load_particle_mappings(mapping_dir=mapping)
    assert loaded["11"] == "e"
    assert loaded["9900014"] == "N_2"


def test_marty_install_accepts_prefix_parent_include_header_and_library(tmp_path):
    prefix = _fake_install(tmp_path)
    candidates = [
        prefix,
        prefix.parent,
        prefix / "include",
        prefix / "include" / "marty.h",
        prefix / "lib",
        prefix / "lib" / "libmarty.a",
    ]
    for candidate in candidates:
        assert resolve_marty_install(candidate).prefix == prefix.resolve()


def test_explicit_paths_take_precedence_and_are_reported(tmp_path):
    mapping = _mapping_dir(tmp_path)
    prefix = _fake_install(tmp_path)
    templates = tmp_path / "templates"
    templates.mkdir()
    workspace = tmp_path / "workspace"

    cfg = MartyPathConfig.resolve(
        "HNL",
        mapping_dir=mapping,
        model_path=mapping / "hnl.h",
        marty_path=prefix.parent,
        workspace_dir=workspace,
        template_dir=templates,
    )

    paths = cfg.as_dict()
    assert cfg.mapping_dir == mapping.resolve()
    assert cfg.model_path == (mapping / "hnl.h").resolve()
    assert cfg.workspace_dir == workspace.resolve()
    assert cfg.marty_install is not None
    assert cfg.marty_install.prefix == prefix.resolve()
    assert paths["marty_lib_dir"] == str((prefix / "lib").resolve())


def test_invalid_explicit_marty_path_fails_early(tmp_path):
    with pytest.raises(FileNotFoundError, match="Invalid MARTY installation path"):
        resolve_marty_install(tmp_path / "missing")
