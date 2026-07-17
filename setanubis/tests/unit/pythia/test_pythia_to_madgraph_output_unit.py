"""Tests for converting Pythia scan outputs into a run directory layout."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from SetAnubis.core.Pythia.domain.PythiaToMadgraphOutput import (
    ScanProcessor,
    example_param_info,
)


def _processor(tmp_path: Path, *, particle_id: int | None = 9900012) -> ScanProcessor:
    text_dir = tmp_path / "text"
    hepmc_dir = tmp_path / "hepmc"
    text_dir.mkdir(parents=True)
    hepmc_dir.mkdir(parents=True)
    return ScanProcessor(
        text_dir=text_dir,
        hepmc_dir=hepmc_dir,
        output_dir=tmp_path / "output",
        param_names=["mass", "coupling"],
        param_info_func=example_param_info,
        particle_id=particle_id,
    )


def test_scan_processor_initialises_header_and_parses_filename(tmp_path, caplog):
    processor = _processor(tmp_path)

    header = processor.scan_path.read_text(encoding="utf-8")
    assert header.startswith("#run_name")
    assert "mass#particle" in header
    assert "coupling#arb" in header
    assert "width#9900012" in header

    assert processor._extract_float("1p25e-3") == pytest.approx(1.25e-3)
    assert processor._extract_float("not-a-number") is None
    assert processor._parse_filename("sample_mass1p5_coupling-2e-3.txt") == {
        "mass": 1.5,
        "coupling": -2.0e-3,
    }

    with caplog.at_level(logging.WARNING):
        assert processor._parse_filename("sample_mass1p5.txt") is None
    assert "Parameter coupling is missing" in caplog.text


def test_text_parser_prefers_integrated_weight_and_selects_particle(tmp_path):
    processor = _processor(tmp_path)
    output = tmp_path / "result.txt"
    output.write_text(
        "Pythia sigmaGen: 2.0\n"
        "DECAY 25 1.0e-3\n"
        "Integrated weight: 3.5\n"
        "DECAY 9900012 4.2e-12\n",
        encoding="utf-8",
    )

    assert processor._parse_text_file(output) == pytest.approx((3.5, 4.2e-12))

    first_decay = _processor(tmp_path / "first", particle_id=None)
    first_output = tmp_path / "first-decay.txt"
    first_output.write_text(
        "Pythia sigmaGen: 1.25\nDECAY -25 8.0e-4\nDECAY 35 9.0e-4\n",
        encoding="utf-8",
    )
    assert first_decay._parse_text_file(first_output) == pytest.approx((1.25, 8e-4))


def test_text_parser_reports_invalid_or_missing_outputs(tmp_path, caplog):
    processor = _processor(tmp_path)
    malformed = tmp_path / "malformed.txt"
    malformed.write_text("Integrated weight: nope\n", encoding="utf-8")

    with caplog.at_level(logging.ERROR):
        assert processor._parse_text_file(malformed) == (0.0, 0.0)
        assert processor._parse_text_file(tmp_path / "missing.txt") == (0.0, 0.0)
    assert "Could not read file" in caplog.text


def test_process_all_creates_numbered_runs_and_skips_invalid_names(tmp_path, caplog):
    processor = _processor(tmp_path)
    valid_stem = "sample_mass1p5_coupling2e-3"
    second_stem = "sample_mass2p0_coupling3e-3"
    (processor.text_dir / f"{valid_stem}.txt").write_text(
        "Integrated weight: 5.0\nDECAY 9900012 1.0e-10\n",
        encoding="utf-8",
    )
    (processor.text_dir / f"{second_stem}.txt").write_text(
        "Pythia sigmaGen: 6.0\nDECAY 9900012 2.0e-10\n",
        encoding="utf-8",
    )
    (processor.text_dir / "invalid.txt").write_text("unused", encoding="utf-8")
    (processor.hepmc_dir / f"{valid_stem}.hepmc").write_text(
        "HepMC::Version 3\n", encoding="utf-8"
    )

    with caplog.at_level(logging.WARNING):
        processor.process_all()

    scan = processor.scan_path.read_text(encoding="utf-8")
    assert "run_01" in scan and "run_02" in scan
    assert "5.000000e+00" in scan and "2.000000e-10" in scan
    assert (processor.output_dir / "run_01" / "event.hepmc").read_text(
        encoding="utf-8"
    ) == "HepMC::Version 3\n"
    assert not (processor.output_dir / "run_02" / "event.hepmc").exists()
    assert "Missing HepMC file" in caplog.text
    assert "Parameter mass is missing" in caplog.text


def test_example_param_info_falls_back_to_unknown_units():
    assert example_param_info("mass") == ("mass", "particle")
    assert example_param_info("custom") == ("custom", "?")
