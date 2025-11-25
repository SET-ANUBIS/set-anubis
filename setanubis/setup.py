from setuptools import setup, find_packages

setup(
    name="SetAnubis",
    version="0.0.1",
    packages=find_packages(),
    install_requires=[
        "pandas",
        "numpy",
        "sympy",
        "matplotlib",
        "docker",
        "argparse",
        "fastjet",
        "seaborn",
        "sphinx",
        "sphinx_rtd_theme",
        "awkward",
        "particle",
        "pyhepmc"
    ],
    python_requires=">=3.9",
)
