import os
import subprocess
import docker

DOCKER_IMAGE = "ryudoro/madgraph-anubis"
CONTAINER_NAME = "madgraph-anubis"
HOST_FOLDER = "/home/cern/neo-set-anubis/db/Template/madgraph/."
CONTAINER_FOLDER = "/External_Integration/input_files/"
MADGRAPH_SCRIPT = "/External_Integration/input_files/jobscript_param_scan.txt"

client = docker.from_env()

def build_image():
    print("Building the Docker image...")
    subprocess.run(["docker", "build", "-t", DOCKER_IMAGE, "."])

def push_image():
    print("Pushing the Docker image to Docker Hub...")
    subprocess.run(["docker", "push", DOCKER_IMAGE])

def pull_image():
    print("Pulling the Docker image from Docker Hub...")
    subprocess.run(["docker", "pull", DOCKER_IMAGE])

def install_gfortran():
    print(f"Checking if gfortran is already installed in container {CONTAINER_NAME}...")
    try:
        # Check if gfortran is installed
        result = subprocess.run(
            ["docker", "exec", CONTAINER_NAME, "bash", "-c", "gfortran --version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode == 0:
            print("gfortran is already installed.")
        else:
            print("gfortran not found. Installing it...")
            subprocess.run([
                "docker", "exec", CONTAINER_NAME,
                "bash", "-c",
                "dnf install -y gcc-gfortran && dnf clean all"
            ])
            print("gfortran has been installed.")
    except Exception as e:
        print(f"Error while checking/installing gfortran: {e}")

def run_container():
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
            volumes={HOST_FOLDER: {"bind": CONTAINER_FOLDER, "mode": "rw"}},
            entrypoint="/bin/bash",
        )
        print(f"Container {CONTAINER_NAME} created and started.")

def copy_files():
    print(f"Copying files from {HOST_FOLDER} to {CONTAINER_FOLDER} in the container...")
    subprocess.run(["docker", "cp", HOST_FOLDER, f"{CONTAINER_NAME}:{CONTAINER_FOLDER}"])

def run_madgraph():
    print(f"Running MadGraph on {MADGRAPH_SCRIPT}...")
    subprocess.run(["docker", "exec", CONTAINER_NAME, "bash", "-c", f"cd /External_Integration/MG5_aMC && ./bin/mg5_aMC {MADGRAPH_SCRIPT}"])

def check_and_pull_image():
    print(f"Checking if image {DOCKER_IMAGE} is already pulled...")
    try:
        client.images.get(DOCKER_IMAGE)
        print(f"Image {DOCKER_IMAGE} is already available locally.")
    except docker.errors.ImageNotFound:
        print(f"Image {DOCKER_IMAGE} not found locally. Pulling...")
        pull_image()

if __name__ == "__main__":
    # build_image()
    # push_image()

    check_and_pull_image()
    
    run_container()
    install_gfortran()
    # copy_files()
    run_madgraph()
