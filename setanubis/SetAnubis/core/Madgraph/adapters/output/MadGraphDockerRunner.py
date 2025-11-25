import os
import docker
import subprocess
from SetAnubis.core.Madgraph.ports.output.IMadGraphRunner import IMadGraphRunner

DOCKER_IMAGE = "ryudoro/madgraph-anubis"
CONTAINER_NAME = "madgraph-anubis"
CONTAINER_FOLDER = "/External_Integration/input_files/"
MG_EXEC_FOLDER = "/External_Integration/MG5_aMC"
MG_COMMAND = f"./bin/mg5_aMC {CONTAINER_FOLDER}jobscript_param_scan.txt"

class MadGraphDockerRunner(IMadGraphRunner):
    def __init__(self):
        """Initializes the MadGraphDockerRunner and sets up Docker.
        """
        self.docker_client = docker.from_env()
        
    def _ensure_container(self):
        """Ensures the Docker container is running; creates it if necessary."""
        try:
            container = self.docker_client.containers.get(CONTAINER_NAME)
            if container.status != "running":
                print(f"Container {CONTAINER_NAME} exists but is not running. Starting...")
                container.start()
        except docker.errors.NotFound:
            print(f"Container {CONTAINER_NAME} not found. Creating and starting...")
            self.docker_client.containers.run(
                DOCKER_IMAGE,
                name=CONTAINER_NAME,
                detach=True,
                tty=True,
                volumes={},  # no need to mount now
                entrypoint="/bin/bash",
            )

    def _write_string_to_container(self, filename, content: str):
        """Writes a string to a file in the Docker container.

        Args:
            filename (str): Name of the file to create inside the container.
            content (str): File content to write.

        Raises:
            RuntimeError: If file operations within Docker container fail.
        """
        path = f"/tmp/{filename}"
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        result_mkdir = subprocess.run(
            ["docker", "exec", CONTAINER_NAME, "mkdir", "-p", CONTAINER_FOLDER],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        if result_mkdir.returncode != 0:
            print("Erreur lors de la création du dossier dans le conteneur :")
            print(result_mkdir.stderr.decode())
            os.remove(path)
            return
    
        result_cp = subprocess.run(
            ["docker", "cp", path, f"{CONTAINER_NAME}:{CONTAINER_FOLDER}{filename}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        os.remove(path)
        
        if result_cp.returncode != 0:
            print("Erreur lors de la copie du fichier dans le conteneur :")
            print(result_cp.stderr.decode())
            return
    

    def inject_all_cards(self, jobscript, run_card, param_card, pythia_card, madspin_card):
        """Injects all necessary MadGraph cards into the Docker container."""
        print("Injecting cards into container...")

        self._write_string_to_container("jobscript_param_scan.txt", jobscript)
        self._write_string_to_container("param_card.dat", param_card)
        self._write_string_to_container("run_card.dat", run_card)

        if pythia_card:
            self._write_string_to_container("pythia8_card.dat", pythia_card)
        if madspin_card:
            self._write_string_to_container("madspin_card.dat", madspin_card)

    def run(self, jobscript, run_card, param_card, pythia_card, madspin_card):
        """Executes the MadGraph simulation inside the Docker container."""
        print("Preparing to run MadGraph...")

        self._ensure_container()
        self.inject_all_cards(jobscript, run_card, param_card, pythia_card, madspin_card)

        print("Launching MadGraph job...")
        subprocess.run([
            "docker", "exec", CONTAINER_NAME, "bash", "-c",
            f"cd {MG_EXEC_FOLDER} && {MG_COMMAND}"
        ], check=True)

        print("MadGraph execution completed.")

    def retrieve_events(self, output_dir="db/Temp/madgraph/Events", width_mode = False):
        """Retrieves simulation output events from the Docker container.

        Args:
            output_dir (str, optional): Directory to store retrieved events. Defaults to "db/Temp/madgraph/Events".
            width_mode (bool, optional): Whether to use width calculation mode. Defaults to False.
        """
        container_events_path = f"{MG_EXEC_FOLDER}/HNL_Condor_CCDY_qqe/Events"
        test = "/External_Integration/MG5_aMC/models/SM_HeavyN_CKM_AllMasses_LO/"
        
        os.makedirs(output_dir, exist_ok=True)

        print("Copying Events directory from the container...")
        if width_mode:
            subprocess.run([
                "docker", "cp",
                f"{CONTAINER_NAME}:{test}",
                output_dir
            ], check=True)
            print(f"Events copied to: {output_dir}")
            return
        
        subprocess.run([
            "docker", "cp",
            f"{CONTAINER_NAME}:{container_events_path}",
            output_dir
        ], check=True)

        print(f"Events copied to: {output_dir}")
