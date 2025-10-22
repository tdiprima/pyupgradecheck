import argparse
import json

from .checker import check_environment


def main():
    p = argparse.ArgumentParser(
        prog="pyupgradecheck",
        description="Check installed packages for Python version compatibility.",
    )
    p.add_argument("target", help="Target Python version (e.g. 3.11)")
    p.add_argument("--packages", "-p", nargs="+", help="Specific packages to check")
    p.add_argument("--json", action="store_true", help="Emit json")
    args = p.parse_args()
    report = check_environment(args.target, args.packages)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for pkg, info in sorted(report.items()):
            print(f"{pkg} {info['version']}: {info['status']} ({info['details']})")


if __name__ == "__main__":
    main()
