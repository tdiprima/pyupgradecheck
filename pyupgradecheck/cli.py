import argparse
import json
import time

from halo import Halo

from .checker import check_environment, get_installed_packages


def main():
    p = argparse.ArgumentParser(
        prog="pyupgradecheck",
        description="Check installed packages for Python version compatibility.",
    )
    p.add_argument("target", help="Target Python version (e.g. 3.13)")
    p.add_argument("--packages", "-p", nargs="+", help="Specific packages to check")
    p.add_argument("--json", action="store_true", help="Emit json output")
    args = p.parse_args()

    # Get package count for time estimation
    if args.packages:
        num_packages = len(args.packages)
    else:
        pkgs = get_installed_packages()
        num_packages = len(pkgs)

    # Estimate time: ~0.5 seconds per package on average (can vary with network)
    estimated_seconds = num_packages * 0.5
    estimated_minutes = estimated_seconds / 60

    if estimated_minutes < 1:
        time_msg = f"~{int(estimated_seconds)} seconds"
    else:
        time_msg = f"~{estimated_minutes:.1f} minutes"

    # Show progress with spinner (only if not JSON output)
    spinner = None
    if not args.json:
        spinner = Halo(
            text=f"Checking {num_packages} packages (estimated time: {time_msg})...",
            spinner="dots"
        )
        spinner.start()

    start_time = time.time()
    report = check_environment(args.target, args.packages)
    elapsed_time = time.time() - start_time

    if spinner:
        spinner.succeed(f"Completed in {elapsed_time:.1f} seconds")

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for pkg, info in sorted(report.items()):
            print(f"{pkg} {info['version']}: {info['status']} ({info['details']})")


if __name__ == "__main__":
    main()
