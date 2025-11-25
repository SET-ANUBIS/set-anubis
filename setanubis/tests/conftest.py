import pytest

@pytest.fixture(scope="session")
def sample_ufo_path():
    return "db/HNL/UFO_HNL"
