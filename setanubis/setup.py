from setuptools import find_packages, setup

CORE_REQUIRES = [
    "numpy",
    "pandas",
    "sympy",
    "matplotlib",
    "scipy",
    "pyyaml",
    "particle",
    "graphviz",
]

EXTRAS = {
    "pythia": ["pybind11", "pyhepmc"],
    "selection": ["pyhepmc", "fastjet", "awkward"],
    "madgraph": ["docker"],
    "app": ["streamlit", "dash", "plotly", "requests", "python-dotenv", "python-multipart"],
    "docs": ["sphinx", "sphinx_rtd_theme"],
    "dev": ["pytest", "build", "twine"],
}
EXTRAS["all"] = sorted({dep for deps in EXTRAS.values() for dep in deps})

setup(
    name="SetAnubis",
    version="0.0.1",
    description="SetAnubis physics simulation toolkit",
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    package_data={
        "SetAnubis.core.Pythia.bindings": ["*.so", "*.pyd", "*.dylib"],
        "SetAnubis": ["**/*.yaml", "**/*.yml", "**/*.json", "**/*.dat", "**/*.txt", "**/*.cmnd"],
    },
    install_requires=CORE_REQUIRES,
    extras_require=EXTRAS,
    python_requires=">=3.10",
)
