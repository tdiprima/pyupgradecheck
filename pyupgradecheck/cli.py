import argparse
import json
import time

from halo import Halo

from .checker import check_environment, get_installed_packages, parse_requirements_file


def main():
    p = argparse.ArgumentParser(
        prog="pyupgradecheck",
        description="Check installed packages for Python version compatibility.",
    )
    p.add_argument("target", help="Target Python version (e.g. 3.13)")
    p.add_argument("--packages", "-p", nargs="+", help="Specific packages to check")
    p.add_argument(
        "--requirements", "-r", help="Path to requirements.txt file to check"
    )
    p.add_argument("--json", action="store_true", help="Emit json output")
    args = p.parse_args()

    # Handle mutually exclusive options
    if args.packages and args.requirements:
        p.error("Cannot specify both --packages and --requirements")

    # Parse requirements file if provided
    packages_to_check = None
    if args.requirements:
        try:
            packages_to_check = parse_requirements_file(args.requirements)
        except FileNotFoundError as e:
            p.error(str(e))
    elif args.packages:
        packages_to_check = args.packages

    # Get package count for time estimation
    if packages_to_check:
        num_packages = len(packages_to_check)
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
            spinner="dots",
        )
        spinner.start()

    try:
        start_time = time.time()
        report = check_environment(args.target, packages_to_check)
        elapsed_time = time.time() - start_time

        if spinner:
            spinner.succeed(f"Completed in {elapsed_time:.1f} seconds")

        if args.json:
            print(json.dumps(report, indent=2))
        else:
            for pkg, info in sorted(report.items()):
                print(f"{pkg} {info['version']}: {info['status']} ({info['details']})")
    except KeyboardInterrupt:
        if spinner:
            spinner.fail("Interrupted by user")
        print("\nOperation cancelled by user.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
