"""Small helper for the development MadGraph Docker image.

The host input directory is configured through ``SETANUBIS_MADGRAPH_INPUT_DIR``.
When unset it defaults to ``External_Integration/MadGraph/input_files`` in the
current checkout, avoiding machine-specific absolute paths.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import docker

DOCKER_IMAGE = os.environ.get("SETANUBIS_MADGRAPH_IMAGE", "ryudoro/madgraph-anubis")
CONTAINER_NAME = os.environ.get("SETANUBIS_MADGRAPH_CONTAINER", "madgraph-anubis")
DEFAULT_INPUT_DIR = Path(__file__).resolve().parent / "input_files"
HOST_FOLDER = Path(os.environ.get("SETANUBIS_MADGRAPH_INPUT_DIR", DEFAULT_INPUT_DIR)).expanduser().resolve()
CONTAINER_FOLDER = "/External_Integration/input_files"
MADGRAPH_SCRIPT = f"{CONTAINER_FOLDER}/jobscript_param_scan.txt"

client = docker.from_env()


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, text=True)


def build_image() -> None:
    print("Building the Docker image...")
    _run(["docker", "build", "-t", DOCKER_IMAGE, "."])


def push_image() -> None:
    print("Pushing the Docker image to Docker Hub...")
    _run(["docker", "push", DOCKER_IMAGE])


def pull_image() -> None:
    print("Pulling the Docker image from Docker Hub...")
    _run(["docker", "pull", DOCKER_IMAGE])


def install_gfortran() -> None:
    print(f"Checking if gfortran is already installed in container {CONTAINER_NAME}...")
    result = subprocess.run(
        ["docker", "exec", CONTAINER_NAME, "gfortran", "--version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        print("gfortran is already installed.")
        return

    print("gfortran not found. Installing it...")
    _run(
        [
            "docker",
            "exec",
            CONTAINER_NAME,
            "bash",
            "-lc",
            "dnf install -y gcc-gfortran && dnf clean all",
        ]
    )
    print("gfortran has been installed.")


def run_container() -> None:
    if not HOST_FOLDER.is_dir():
        raise FileNotFoundError(
            f"MadGraph input directory does not exist: {HOST_FOLDER}. "
            "Set SETANUBIS_MADGRAPH_INPUT_DIR to the directory containing the cards."
        )

    print(f"Checking if container {CONTAINER_NAME} is already running...")
    try:
        container = client.containers.get(CONTAINER_NAME)
        if container.status == "running":
            print(f"Container {CONTAINER_NAME} is already running.")
        else:
            print(f"Container {CONTAINER_NAME} exists but is not running. Starting it...")
            container.start()
    except docker.errors.NotFound:
        print(f"Container {CONTAINER_NAME} not found. Creating and starting it...")
        client.containers.run(
            DOCKER_IMAGE,
            name=CONTAINER_NAME,
            detach=True,
            tty=True,
            volumes={str(HOST_FOLDER): {"bind": CONTAINER_FOLDER, "mode": "rw"}},
            entrypoint="/bin/bash",
        )
        print(f"Container {CONTAINER_NAME} created and started.")


def copy_files() -> None:
    if not HOST_FOLDER.is_dir():
        raise FileNotFoundError(HOST_FOLDER)
    print(f"Copying files from {HOST_FOLDER} to {CONTAINER_FOLDER} in the container...")
    _run(["docker", "cp", f"{HOST_FOLDER}/.", f"{CONTAINER_NAME}:{CONTAINER_FOLDER}"])


def run_madgraph() -> None:
    print(f"Running MadGraph on {MADGRAPH_SCRIPT}...")
    _run(
        [
            "docker",
            "exec",
            CONTAINER_NAME,
            "/External_Integration/MG5_aMC/bin/mg5_aMC",
            MADGRAPH_SCRIPT,
        ]
    )


def check_and_pull_image() -> None:
    print(f"Checking if image {DOCKER_IMAGE} is already pulled...")
    try:
        client.images.get(DOCKER_IMAGE)
        print(f"Image {DOCKER_IMAGE} is already available locally.")
    except docker.errors.ImageNotFound:
        print(f"Image {DOCKER_IMAGE} not found locally. Pulling...")
        pull_image()


if __name__ == "__main__":
    check_and_pull_image()
    run_container()
    install_gfortran()
    run_madgraph()
