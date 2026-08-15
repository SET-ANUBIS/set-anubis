from SetAnubis.resources import asset_path


def test_hnl_n2_marty_model_matches_runtime_ufo_convention():
    """Protect the N2 conventions needed by the MARTY decay-width pipeline."""
    source = asset_path("MARTY", "model", "hnl.h").read_text(encoding="utf-8")

    # The UFO HNL states are self-conjugate Majorana fermions.
    assert 'N->setSelfConjugate(true);' in source

    # The charged-current interaction uses W^- = conjugate(W^+).
    assert 'GetComplexConjugate(W({nu}))' in source

    # The implemented neutral-current convention has the same explicit
    # coupling sign as the charged-current term.
    assert 'VmuN1 * sm_input::e_em / (2 * sW * cW)' in source
    assert '- VmuN1 * sm_input::e_em / (2 * sW * cW)' not in source

    # PDG 9900014 is N_2. Its symbolic MARTY on-shell mass must therefore be
    # mN2, matching the mass written to partlist.csv for the numerical stage.
    assert 'mN2 = constant_s("mN2");' in source
    assert 'addFermionicMass(N, mN2);' in source
    assert 'addFermionicMass(N, mN1);' not in source
