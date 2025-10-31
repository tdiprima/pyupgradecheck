import argparse
import json
import time

from halo import Halo
from rich_argparse import RichHelpFormatter

from .checker import check_environment, get_installed_packages, parse_requirements_file


def main():
    p = argparse.ArgumentParser(
        prog="pyupgradecheck",
        description="Check installed packages for Python version compatibility.",
        formatter_class=RichHelpFormatter,
    )
    p.add_argument("target", help="Target Python version (e.g. 3.13)")
    p.add_argument("--packages", "-p", nargs="+", help="Specific packages to check")
    p.add_argument("--requirements", "-r", help="Path to requirements.txt file to check")
    p.add_argument("--json", action="store_true", help="Emit JSON output")
    p.add_argument("--strict", action="store_true", help="Require both PyPI + classifier agreement")
    p.add_argument("--simulate-install", action="store_true", help="(Future) actually attempt installs")
    args = p.parse_args()

    if args.packages and args.requirements:
        p.error("Cannot specify both --packages and --requirements")

    packages_to_check = None
    if args.requirements:
        try:
            packages_to_check = parse_requirements_file(args.requirements)
        except FileNotFoundError as e:
            p.error(str(e))
    elif args.packages:
        packages_to_check = args.packages

    pkgs = get_installed_packages() if not packages_to_check else {}
    num_packages = len(packages_to_check or pkgs)
    estimated_time = num_packages * 0.5
    time_msg = f"~{int(estimated_time)} seconds" if estimated_time < 60 else f"~{estimated_time/60:.1f} minutes"

    spinner = None
    if not args.json:
        spinner = Halo(
            text=f"Checking {num_packages} packages (estimated time: {time_msg})...",
            spinner="dots",
        )
        spinner.start()

    try:
        start_time = time.time()
        report = check_environment(args.target, packages_to_check, args.strict)
        elapsed = time.time() - start_time
        if spinner:
            spinner.succeed(f"Completed in {elapsed:.1f} seconds")

        if args.json:
            print(json.dumps(report, indent=2))
        else:
            for pkg, info in sorted(report.items()):
                print(
                    f"{pkg} {info['version']}: {info['status']} "
                    f"({info['details']}, source={info['source']})"
                )
    except KeyboardInterrupt:
        if spinner:
            spinner.fail("Interrupted by user")
        print("\nOperation cancelled by user.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
