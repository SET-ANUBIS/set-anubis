import argparse
from SetAnubis.core.Madgraph.app.CLI.run_madgraph import run_madgraph

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MadGraph CLI runner")
    parser.add_argument("--config", required=True, help="Path to the YAML config")
    parser.add_argument("--no-dry-run", action="store_true", help="Execute MadGraph for real")

    args = parser.parse_args()
    run_madgraph(args.config, dry_run=not args.no_dry_run)
