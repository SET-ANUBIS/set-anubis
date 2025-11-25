import argparse
from SetAnubis.core.Pythia.app.CLI.run_simulation import run_simulation

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run HNL simulation via config YAML")
    parser.add_argument("--config", required=True, help="Path to the YAML config file")
    parser.add_argument("--param", action='append', help="Override parameter, e.g. VeN1=1e-2", default=[])
    
    args = parser.parse_args()
    run_simulation(args.config, args.param)
